from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db.database import connect, dict_from_row
from pathlib import Path

from app.services.ocr_engine import parse_pdf_to_standard_ocr_json
from app.services.ocr_logs import create_ocr_parse_log


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(
    job_type: str,
    package_code: str,
    payload: dict[str, Any] | None = None,
    total: int | None = None,
) -> dict[str, Any]:
    task_total = 1 if total is None else max(total, 0)
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    timestamp = now_iso()
    with connect() as conn:
      conn.execute(
          """
          INSERT INTO jobs (
            job_id, job_type, package_code, status, progress, total, succeeded, failed,
            message, payload, created_at, updated_at, completed_at
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          """,
          (
              job_id,
              job_type,
              package_code,
              "queued",
              0,
              task_total,
              0,
              0,
              "任务已创建",
              json.dumps(payload or {}, ensure_ascii=False),
              timestamp,
              timestamp,
              None,
          ),
      )
    return get_job(job_id)


def get_job(job_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    job = dict_from_row(row)
    if job is None:
        raise KeyError(job_id)
    job["payload"] = json.loads(job["payload"])
    return job


def list_jobs() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 15").fetchall()
    jobs = []
    for row in rows:
        job = dict_from_row(row) or {}
        job["payload"] = json.loads(job["payload"])
        jobs.append(job)
    return jobs


def update_job(job_id: str, **updates: Any) -> None:
    allowed = {"status", "progress", "total", "succeeded", "failed", "message", "completed_at"}
    fields = [key for key in updates if key in allowed]
    status = str(updates.get("status") or "")
    if status in {"succeeded", "failed", "cancelled"} and "completed_at" not in updates:
        updates["completed_at"] = now_iso()
        fields.append("completed_at")
    if not fields:
        return
    updates["updated_at"] = now_iso()
    fields.append("updated_at")
    assignments = ", ".join(f"{field} = ?" for field in fields)
    values = [updates[field] for field in fields]
    values.append(job_id)
    with connect() as conn:
        conn.execute(f"UPDATE jobs SET {assignments} WHERE job_id = ?", values)


def run_demo_job(job_id: str) -> None:
    job = get_job(job_id)
    if job["job_type"] == "ocr_documents":
        _run_ocr_job(job)
        return
    if job["job_type"] == "generate_ai_report":
        _run_ai_report_job(job)
        return

    total = int(job["total"])
    if total <= 0:
        update_job(job_id, status="failed", progress=0, message="任务没有可处理的数据")
        return

    update_job(job_id, status="running", message="任务执行中")
    for index in range(total):
        time.sleep(0.55)
        progress = int(((index + 1) / total) * 100)
        update_job(
            job_id,
            progress=progress,
            succeeded=index + 1,
            failed=0,
            message=f"已处理 {index + 1}/{total}",
        )
    update_job(job_id, status="succeeded", progress=100, message="任务完成")


def _run_ocr_job(job: dict[str, Any]) -> None:
    from app.services.documents import list_documents_for_ocr, update_document_status

    documents = list_documents_for_ocr(job["package_code"])
    total = len(documents)
    if total == 0:
        update_job(
            job["job_id"],
            status="failed",
            progress=0,
            succeeded=0,
            failed=0,
            message="未找到已导入PDF或JSON，请先点击“导入文件任务”选择文件。",
        )
        return

    update_job(job["job_id"], status="running", total=total, message="OCR解析任务执行中")
    failed = 0
    for index, document in enumerate(documents, start=1):
        source_file = str(document["original_name"])
        try:
            sample_path = Path(str(document["stored_path"]))
            result_json = parse_pdf_to_standard_ocr_json(sample_path, package_code=job["package_code"])
            confidence = float(result_json.get("debug", {}).get("overall_confidence", 0.0))
            create_ocr_parse_log(
                job_id=job["job_id"],
                package_code=job["package_code"],
                source_file=source_file,
                result_json=result_json,
                confidence=confidence,
                provider=str(result_json.get("provider") or "pdf-text-extractor"),
                strategy_version=str(result_json.get("strategy_version") or ""),
                notes="基于用户导入文件的OCR解析结果；JSON会作为完整识别结果直接归一化，PDF会读取文本层。",
            )
            update_document_status(str(document["document_id"]), "parsed")
        except Exception:
            failed += 1
            update_document_status(str(document["document_id"]), "failed")

        succeeded = index - failed
        update_job(
            job["job_id"],
            progress=int((index / total) * 100),
            succeeded=succeeded,
            failed=failed,
            message=f"已解析 {index}/{total} 个文件",
        )

    update_job(
        job["job_id"],
        status="failed" if failed == total else "succeeded",
        progress=100,
        message=f"OCR解析完成：成功 {total - failed} 个，失败 {failed} 个",
    )


def _run_ai_report_job(job: dict[str, Any]) -> None:
    from app.services.ai_interpreter import interpret_report_with_deepseek
    from app.services.documents import mark_package_documents_completed
    from app.services.ocr_logs import (
        get_ocr_parse_log,
        list_pending_ocr_parse_logs,
        mark_ocr_logs_consumed,
    )
    from app.services.report_data_builder import build_report_data_from_ocr_result
    from app.services.report_renderer import render_report

    payload = job.get("payload") or {}
    log_ids = payload.get("ocr_log_ids")
    if isinstance(log_ids, list) and log_ids:
        logs = []
        for log_id in log_ids:
            try:
                logs.append(get_ocr_parse_log(str(log_id)))
            except KeyError:
                continue
    else:
        logs = list_pending_ocr_parse_logs(package_code=job["package_code"], limit=200)

    logs = list(reversed(logs))
    total = len(logs)
    if total == 0:
        update_job(
            job["job_id"],
            status="failed",
            progress=0,
            total=0,
            succeeded=0,
            failed=0,
            message="未找到OCR解析日志，请先执行OCR解析任务。",
        )
        return

    update_job(job["job_id"], status="running", total=total, message="AI输出任务执行中")
    failed = 0
    rendered = 0
    consumed_log_ids: list[str] = []
    for index, log in enumerate(logs, start=1):
        try:
            report_data = build_report_data_from_ocr_result(job["package_code"], log["result_json"])
            result = interpret_report_with_deepseek(
                package_code=job["package_code"],
                ocr_result=log["result_json"],
                report_data=report_data,
            )
            if result.get("status") != "succeeded" or "report_data" not in result:
                raise RuntimeError(str(result.get("message") or "AI输出失败"))
            render_report(job["package_code"], result["report_data"])
            rendered += 1
            consumed_log_ids.append(str(log["log_id"]))
        except Exception as exc:
            failed += 1
            update_job(
                job["job_id"],
                progress=int((index / total) * 100),
                succeeded=rendered,
                failed=failed,
                message=f"AI输出失败：{log.get('source_file', '')}，{exc}",
            )
            continue

        update_job(
            job["job_id"],
            progress=int((index / total) * 100),
            succeeded=rendered,
            failed=failed,
            message=f"已生成 {index}/{total} 份AI报告",
        )

    if consumed_log_ids:
        mark_ocr_logs_consumed(consumed_log_ids)
    completed_documents = mark_package_documents_completed(job["package_code"]) if failed == 0 else 0
    update_job(
        job["job_id"],
        status="failed" if failed == total else "succeeded",
        progress=100,
        succeeded=rendered,
        failed=failed,
        message=f"AI输出完成：生成 {rendered} 份待审报告，失败 {failed} 份，已清理 {completed_documents} 个导入文件记录",
    )
