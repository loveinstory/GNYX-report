from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.db.database import connect, dict_from_row


DEFAULT_STRATEGY_VERSION = "P02-ocr-strategy-v0.3-structured-json"
DEFAULT_PROVIDER = "demo-json-parser"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_demo_ocr_result(package_code: str, source_file: str, index: int) -> dict[str, Any]:
    file_stem = Path(source_file).stem
    structured_report = {
        "report_id": file_stem,
        "patient_info": {
            "name": file_stem,
            "gender": "",
            "age": "",
            "specimen_condition": "",
            "specimen_types": [],
            "hospital": "",
            "patient_number": "",
            "bed_number": "",
            "department": "",
            "doctor": "",
            "clinical_diagnosis": "",
        },
        "tests": [
            {
                "page": 1,
                "specimen_type": "",
                "test_name": "钙卫蛋白检测（Cal）",
                "result": "待真实OCR解析",
                "indicator": "",
                "reference_range": "阴性",
                "unit": "",
                "method": "",
            }
        ],
        "notes": "",
        "additional_info": {
            "sample_date": "",
            "receive_date": "",
            "report_date": "",
            "technician": "",
            "reviewer": "",
            "approver": "",
        },
    }
    fields = [
        {
            "field_key": "patient.name",
            "label": "姓名",
            "value": file_stem,
            "confidence": 0.82,
            "source": {"page": 1, "bbox": None},
        },
        {
            "field_key": "p02.calprotectin.result_display",
            "label": "粪便钙卫蛋白检测结果",
            "value": "待真实OCR解析",
            "confidence": 0.68,
            "source": {"page": 1, "bbox": None},
        },
    ]
    return {
        "schema_version": "1.0",
        "package_code": package_code,
        "source_file": source_file,
        "strategy_version": DEFAULT_STRATEGY_VERSION,
        "provider": DEFAULT_PROVIDER,
        "pages": [
            {
                "page_number": 1,
                "width": None,
                "height": None,
                "text_blocks": [
                    {
                        "text": f"{file_stem} OCR解析占位文本",
                        "confidence": 0.9,
                        "bbox": None,
                    }
                ],
            }
        ],
        "fields": fields,
        "indicators": {
            field["field_key"]: {
                "label": field["label"],
                "value": field["value"],
                "confidence": field["confidence"],
                "source": field["source"],
            }
            for field in fields
            if field["field_key"].startswith("p02.")
        },
        "structured_report": structured_report,
        "warnings": [
            "当前为模拟解析日志，用于验证OCR日志与统一JSON结构；接入云OCR后替换为真实解析结果。"
        ],
        "created_at": now_iso(),
        "debug": {
            "sample_index": index,
            "comparison_key": f"{package_code}:{source_file}:{DEFAULT_STRATEGY_VERSION}",
            "structured_test_count": len(structured_report["tests"]),
        },
    }


def create_ocr_parse_log(
    *,
    job_id: str,
    package_code: str,
    source_file: str,
    result_json: dict[str, Any],
    confidence: float,
    status: str = "succeeded",
    provider: str = DEFAULT_PROVIDER,
    strategy_version: str = DEFAULT_STRATEGY_VERSION,
    notes: str = "",
) -> dict[str, Any]:
    log_id = f"ocrlog_{uuid.uuid4().hex[:12]}"
    timestamp = now_iso()
    extracted_field_count = len(result_json.get("fields", []))
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO ocr_parse_logs (
              log_id, job_id, package_code, source_file, strategy_version, provider,
              status, confidence, extracted_field_count, result_json, notes, created_at, consumed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_id,
                job_id,
                package_code,
                source_file,
                strategy_version,
                provider,
                status,
                confidence,
                extracted_field_count,
                json.dumps(result_json, ensure_ascii=False),
                notes,
                timestamp,
                None,
            ),
        )
    return get_ocr_parse_log(log_id)


def get_ocr_parse_log(log_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM ocr_parse_logs WHERE log_id = ?", (log_id,)).fetchone()
    log = dict_from_row(row)
    if log is None:
        raise KeyError(log_id)
    log["result_json"] = json.loads(log["result_json"])
    return log


def list_ocr_parse_logs(package_code: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    sql = "SELECT * FROM ocr_parse_logs"
    params: list[Any] = []
    if package_code:
        sql += " WHERE package_code = ?"
        params.append(package_code)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    logs: list[dict[str, Any]] = []
    for row in rows:
        log = dict_from_row(row) or {}
        log["result_json"] = json.loads(log["result_json"])
        logs.append(log)
    return logs


def list_pending_ocr_parse_logs(package_code: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    sql = "SELECT * FROM ocr_parse_logs WHERE consumed_at IS NULL"
    params: list[Any] = []
    if package_code:
        sql += " AND package_code = ?"
        params.append(package_code)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    logs: list[dict[str, Any]] = []
    for row in rows:
        log = dict_from_row(row) or {}
        log["result_json"] = json.loads(log["result_json"])
        logs.append(log)
    return logs


def mark_ocr_logs_consumed(log_ids: list[str]) -> None:
    unique_ids = [str(log_id) for log_id in dict.fromkeys(log_ids) if log_id]
    if not unique_ids:
        return
    placeholders = ",".join("?" for _ in unique_ids)
    with connect() as conn:
        conn.execute(
            f"UPDATE ocr_parse_logs SET consumed_at = ? WHERE log_id IN ({placeholders})",
            (now_iso(), *unique_ids),
        )
