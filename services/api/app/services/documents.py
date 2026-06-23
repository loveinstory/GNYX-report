from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO

from app.core.config import settings
from app.db.database import connect, dict_from_row
from app.services.jobs import create_job, get_job, update_job


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_import_job_from_files(
    *,
    package_code: str,
    files: list[tuple[str, bytes]],
) -> dict[str, Any]:
    document_files = [
        (name, content)
        for name, content in files
        if Path(name).suffix.lower() in {".pdf", ".json"}
    ]
    if not document_files:
        job = create_job(
            job_type="import_documents",
            package_code=package_code,
            payload={"file_names": [name for name, _ in files]},
            total=0,
        )
        update_job(job["job_id"], status="failed", message="未选择PDF或JSON文件，请重新导入。")
        return {"job": get_job(job["job_id"]), "documents": []}

    job = create_job(
        job_type="import_documents",
        package_code=package_code,
        payload={"file_names": [name for name, _ in document_files]},
        total=len(document_files),
    )
    update_job(job["job_id"], status="running", message="正在保存导入文件")

    documents: list[dict[str, Any]] = []
    for index, (original_name, content) in enumerate(document_files, start=1):
        documents.append(_save_imported_document(job["job_id"], package_code, original_name, content))
        update_job(
            job["job_id"],
            progress=int((index / len(document_files)) * 100),
            succeeded=index,
            failed=0,
            message=f"已导入 {index}/{len(document_files)} 个文件",
        )

    update_job(job["job_id"], status="succeeded", progress=100, message=f"已导入 {len(document_files)} 个文件")
    return {"job": get_job(job["job_id"]), "documents": documents}


def list_imported_documents(package_code: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    where = "WHERE status <> 'completed'"
    params: list[Any] = []
    if package_code:
        where += " AND package_code = ?"
        params.append(package_code)
    params.append(limit)
    with connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM imported_documents {where} ORDER BY created_at DESC LIMIT ?",
            params,
        ).fetchall()
    return [dict_from_row(row) or {} for row in rows]


def list_documents_for_ocr(package_code: str) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM imported_documents
             WHERE package_code = ? AND status = 'imported'
             ORDER BY created_at ASC
            """,
            (package_code,),
        ).fetchall()
    return [dict_from_row(row) or {} for row in rows]


def update_document_status(document_id: str, status: str) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE imported_documents SET status = ?, updated_at = ? WHERE document_id = ?",
            (status, now_iso(), document_id),
        )


def mark_package_documents_completed(package_code: str) -> int:
    timestamp = now_iso()
    with connect() as conn:
        cursor = conn.execute(
            """
            UPDATE imported_documents
               SET status = 'completed', updated_at = ?
             WHERE package_code = ? AND status <> 'completed'
            """,
            (timestamp, package_code),
        )
    return int(cursor.rowcount or 0)


def _save_imported_document(job_id: str, package_code: str, original_name: str, content: bytes) -> dict[str, Any]:
    timestamp = now_iso()
    document_id = f"doc_{uuid.uuid4().hex[:12]}"
    safe_name = _safe_filename(original_name)
    stored_name = f"{document_id}_{safe_name}"
    target_dir = settings.import_dir / package_code / job_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / stored_name
    target_path.write_bytes(content)

    with connect() as conn:
        conn.execute(
            """
            INSERT INTO imported_documents (
              document_id, import_job_id, package_code, original_name, stored_name,
              stored_path, size, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                job_id,
                package_code,
                original_name,
                stored_name,
                str(target_path),
                len(content),
                "imported",
                timestamp,
                timestamp,
            ),
        )

    return get_imported_document(document_id)


def get_imported_document(document_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM imported_documents WHERE document_id = ?", (document_id,)).fetchone()
    document = dict_from_row(row)
    if document is None:
        raise KeyError(document_id)
    return document


def _safe_filename(name: str) -> str:
    cleaned = Path(name).name.strip() or "document.pdf"
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", cleaned)
    if Path(cleaned).suffix.lower() not in {".pdf", ".json"}:
        cleaned = f"{cleaned}.pdf"
    return cleaned[:160]
