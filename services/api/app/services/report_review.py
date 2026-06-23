from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from pypdf import PdfReader, PdfWriter

from app.core.config import settings
from app.db.database import connect, dict_from_row
from app.services.package_loader import get_package


REVIEW_ACTIVE_STATUSES = ("pending_review", "edited")
REVIEW_LOCKED_STATUSES = ("reviewed", "exported")
CHROME_CANDIDATES = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def register_rendered_report(
    *,
    report_id: str,
    package_code: str,
    report_data: dict[str, Any],
    html_path: str,
    status: str = "pending_review",
) -> dict[str, Any]:
    manifest = _package_manifest(package_code)
    version_lock = report_data.get("version_lock", {}) if isinstance(report_data.get("version_lock"), dict) else {}
    snapshot = _build_snapshot(report_data, html_path)
    timestamp = now_iso()
    template_version = str(version_lock.get("template_version") or manifest.get("template_version") or "")
    rule_version = str(version_lock.get("rule_version") or manifest.get("rule_version") or "")
    prompt_version = str(version_lock.get("prompt_version") or manifest.get("prompt_version") or "")
    ai_model = str(version_lock.get("ai_model") or manifest.get("default_ai_model") or "")
    case_id = str(report_data.get("case_id") or report_id)

    with connect() as conn:
        existing = conn.execute("SELECT report_id, status FROM reports WHERE report_id = ?", (report_id,)).fetchone()
        if existing:
            current_status = str(existing["status"])
            next_status = current_status if current_status in REVIEW_LOCKED_STATUSES else status
            conn.execute(
                """
                UPDATE reports
                   SET case_id = ?, package_code = ?, status = ?, template_version = ?,
                       rule_version = ?, prompt_version = ?, ai_model = ?, snapshot_json = ?,
                       updated_at = ?
                 WHERE report_id = ?
                """,
                (
                    case_id,
                    package_code,
                    next_status,
                    template_version,
                    rule_version,
                    prompt_version,
                    ai_model,
                    json.dumps(snapshot, ensure_ascii=False),
                    timestamp,
                    report_id,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO reports (
                  report_id, case_id, package_code, status, template_version, rule_version,
                  prompt_version, ai_model, snapshot_json, export_path, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    case_id,
                    package_code,
                    status,
                    template_version,
                    rule_version,
                    prompt_version,
                    ai_model,
                    json.dumps(snapshot, ensure_ascii=False),
                    None,
                    timestamp,
                    timestamp,
                ),
            )
    return get_review_report(report_id)


def find_active_report_id_for_case(*, case_id: str, package_code: str) -> str:
    if not case_id:
        return ""
    with connect() as conn:
        row = conn.execute(
            f"""
            SELECT report_id
              FROM reports
             WHERE case_id = ?
               AND package_code = ?
               AND status IN ({','.join('?' for _ in REVIEW_ACTIVE_STATUSES)})
             ORDER BY updated_at DESC
             LIMIT 1
            """,
            (case_id, package_code, *REVIEW_ACTIVE_STATUSES),
        ).fetchone()
    report = dict_from_row(row)
    return str(report.get("report_id") or "") if report else ""


def list_review_reports(package_code: str | None = None, status: str = "pending_review") -> list[dict[str, Any]]:
    sync_existing_case_reports()
    where: list[str] = []
    params: list[Any] = []
    if package_code:
        where.append("package_code = ?")
        params.append(package_code)
    if status == "pending_review":
        where.append(f"status IN ({','.join('?' for _ in REVIEW_ACTIVE_STATUSES)})")
        params.extend(REVIEW_ACTIVE_STATUSES)
    elif status and status != "all":
        where.append("status = ?")
        params.append(status)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    with connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM reports {where_sql} ORDER BY updated_at DESC LIMIT 200",
            params,
        ).fetchall()
    reports: list[dict[str, Any]] = []
    for row in rows:
        try:
            reports.append(_report_row_to_summary(row))
        except FileNotFoundError:
            continue
    return reports


def get_review_report(report_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM reports WHERE report_id = ?", (report_id,)).fetchone()
    report = dict_from_row(row)
    if report is None:
        raise KeyError(report_id)
    summary = _report_dict_to_summary(report)
    summary["pages"] = list_report_pages(report_id)
    return summary


def get_report_page_content(report_id: str, page_name: str, public_base_url: str | None = None) -> dict[str, str]:
    page_path = _resolve_page_path(report_id, page_name)
    resolved_public_base_url = (public_base_url or settings.api_public_base_url).rstrip("/")
    base_url = f"{resolved_public_base_url}/storage/{page_path.parent.relative_to(settings.storage_dir).as_posix()}/"
    page_url = f"/storage/{page_path.relative_to(settings.storage_dir).as_posix()}"
    return {
        "report_id": report_id,
        "page_name": page_path.name,
        "html_content": page_path.read_text(encoding="utf-8"),
        "base_url": base_url,
        "page_url": page_url,
    }


def save_report_page_content(report_id: str, page_name: str, html_content: str) -> dict[str, Any]:
    report = get_review_report(report_id)
    if report["status"] in REVIEW_LOCKED_STATUSES:
        raise PermissionError("报告已审并锁定，如需编辑请由管理员先解审核。")

    page_path = _resolve_page_path(report_id, page_name)
    cleaned_html = _repair_common_mojibake(html_content)
    soup = BeautifulSoup(cleaned_html, "html.parser")
    for script in soup.select("script"):
        script.decompose()
    page_path.write_text(str(soup), encoding="utf-8")

    timestamp = now_iso()
    with connect() as conn:
        conn.execute(
            "UPDATE reports SET status = ?, updated_at = ? WHERE report_id = ?",
            ("edited", timestamp, report_id),
        )
        conn.execute(
            """
            INSERT INTO audit_logs (audit_id, actor, action, target_type, target_id, detail_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"audit_{uuid.uuid4().hex[:12]}",
                "local_user",
                "save_report_page",
                "report",
                report_id,
                json.dumps({"page_name": page_path.name, "encoding_repaired": cleaned_html != html_content}, ensure_ascii=False),
                timestamp,
            ),
        )
    return get_review_report(report_id)


def export_report_pdf(report_id: str) -> dict[str, Any]:
    report = get_review_report(report_id)
    if report["status"] in REVIEW_LOCKED_STATUSES:
        raise PermissionError("报告已审并锁定，如需重新导出请由管理员先解审核。")

    html_dir = _report_html_dir(report_id)
    pages = [html_dir / "pages" / item["page_name"] for item in report["pages"]]
    if not pages:
        raise FileNotFoundError(f"Report {report_id} has no HTML pages")

    asset_summary = prepare_print_assets(html_dir)
    chrome_path = _find_chrome()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = settings.export_dir / f"{report_id}_{timestamp}.pdf"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=f"{report_id}_pdf_") as temp_name:
        temp_dir = Path(temp_name)
        page_pdfs: list[Path] = []
        print_dir = html_dir / "__print"
        if print_dir.exists():
            shutil.rmtree(print_dir)
        print_dir.mkdir(parents=True, exist_ok=True)
        try:
            for index, page_path in enumerate(pages, start=1):
                print_html = print_dir / page_path.name
                page_html = _repair_page_file_if_needed(page_path)
                print_html.write_text(_inject_print_export_assets(page_html), encoding="utf-8")
                page_pdf = temp_dir / f"{index:02d}-{page_path.stem}.pdf"
                _print_html_to_pdf(chrome_path, print_html, page_pdf)
                page_pdfs.append(page_pdf)
            _merge_pdfs(page_pdfs, output_path)
        finally:
            shutil.rmtree(print_dir, ignore_errors=True)

    timestamp_iso = now_iso()
    with connect() as conn:
        conn.execute(
            "UPDATE reports SET status = ?, export_path = ?, updated_at = ? WHERE report_id = ?",
            ("reviewed", str(output_path), timestamp_iso, report_id),
        )
        conn.execute(
            """
            INSERT INTO audit_logs (audit_id, actor, action, target_type, target_id, detail_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"audit_{uuid.uuid4().hex[:12]}",
                "local_user",
                "export_report_pdf",
                "report",
                report_id,
                json.dumps({"pdf_path": str(output_path), "page_count": len(page_pdfs), "asset_summary": asset_summary}, ensure_ascii=False),
                timestamp_iso,
            ),
        )

    return {
        "status": "succeeded",
        "report_id": report_id,
        "pdf_path": str(output_path),
        "pdf_url": _storage_url(output_path),
        "page_count": len(page_pdfs),
        "asset_dpi": 300,
        "asset_summary": asset_summary,
    }


def unlock_reviewed_report(report_id: str) -> dict[str, Any]:
    report = get_review_report(report_id)
    if report["status"] not in REVIEW_LOCKED_STATUSES:
        return report

    timestamp = now_iso()
    with connect() as conn:
        conn.execute(
            "UPDATE reports SET status = ?, export_path = NULL, updated_at = ? WHERE report_id = ?",
            ("edited", timestamp, report_id),
        )
        conn.execute(
            """
            INSERT INTO audit_logs (audit_id, actor, action, target_type, target_id, detail_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"audit_{uuid.uuid4().hex[:12]}",
                "admin",
                "unlock_reviewed_report",
                "report",
                report_id,
                json.dumps(
                    {
                        "previous_status": report["status"],
                        "previous_export_path": report.get("export_path", ""),
                    },
                    ensure_ascii=False,
                ),
                timestamp,
            ),
        )
    return get_review_report(report_id)


def delete_review_report(report_id: str) -> dict[str, Any]:
    safe_report_id = Path(report_id).name
    with connect() as conn:
        row = conn.execute("SELECT * FROM reports WHERE report_id = ?", (safe_report_id,)).fetchone()
    report = dict_from_row(row)
    if report is None:
        raise KeyError(report_id)

    snapshot = json.loads(report.get("snapshot_json") or "{}")
    paths_to_delete = [settings.cases_dir / safe_report_id]
    export_path = str(report.get("export_path") or "").strip()
    if export_path:
        paths_to_delete.append(Path(export_path))

    deleted_paths: list[str] = []
    skipped_paths: list[str] = []
    allowed_roots = (settings.cases_dir, settings.export_dir, settings.storage_dir)
    for path in paths_to_delete:
        resolved = _normalize_delete_target(path)
        if not _is_inside_any(resolved, allowed_roots):
            skipped_paths.append(str(resolved))
            continue
        if resolved.is_dir():
            shutil.rmtree(resolved)
            deleted_paths.append(str(resolved))
        elif resolved.is_file():
            resolved.unlink()
            deleted_paths.append(str(resolved))

    timestamp = now_iso()
    with connect() as conn:
        conn.execute("DELETE FROM reports WHERE report_id = ?", (safe_report_id,))
        conn.execute(
            """
            INSERT INTO audit_logs (audit_id, actor, action, target_type, target_id, detail_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"audit_{uuid.uuid4().hex[:12]}",
                "local_user",
                "delete_review_report",
                "report",
                safe_report_id,
                json.dumps(
                    {
                        "package_code": report.get("package_code", ""),
                        "status": report.get("status", ""),
                        "case_id": report.get("case_id", ""),
                        "patient_name": snapshot.get("patient_name", ""),
                        "report_no": snapshot.get("report_no", ""),
                        "deleted_paths": deleted_paths,
                        "skipped_paths": skipped_paths,
                    },
                    ensure_ascii=False,
                ),
                timestamp,
            ),
        )

    return {
        "status": "deleted",
        "report_id": safe_report_id,
        "deleted_paths": deleted_paths,
        "skipped_paths": skipped_paths,
    }


def sync_existing_case_reports() -> None:
    if not settings.cases_dir.exists():
        return
    with connect() as conn:
        existing = {
            str(row["report_id"])
            for row in conn.execute("SELECT report_id FROM reports").fetchall()
        }
    try:
        case_dirs = sorted(settings.cases_dir.glob("report_*"), key=lambda path: path.stat().st_mtime, reverse=True)
    except FileNotFoundError:
        case_dirs = []
    for case_dir in case_dirs:
        if case_dir.name in existing:
            continue
        data_path = case_dir / "report-data.json"
        index_path = case_dir / "html" / "index.html"
        if not data_path.exists() or not index_path.exists():
            continue
        try:
            report_data = json.loads(data_path.read_text(encoding="utf-8"))
            package_code = str(report_data.get("package_code") or "P02")
            register_rendered_report(
                report_id=case_dir.name,
                package_code=package_code,
                report_data=report_data,
                html_path=str(index_path),
            )
        except Exception:
            continue


def list_report_pages(report_id: str) -> list[dict[str, Any]]:
    pages_dir = _report_html_dir(report_id) / "pages"
    if not pages_dir.exists():
        return []
    pages: list[dict[str, Any]] = []
    for html_path in sorted(pages_dir.glob("page-*.html")):
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else html_path.stem
        pages.append(
            {
                "page_name": html_path.name,
                "title": title,
                "page_no": len(pages) + 1,
                "page_url": f"/storage/{html_path.relative_to(settings.storage_dir).as_posix()}",
            }
        )
    return pages


def prepare_print_assets(html_dir: Path) -> dict[str, Any]:
    image_dir = html_dir / "assets" / "images"
    if not image_dir.exists():
        return {"status": "no_images", "asset_count": 0}
    try:
        from PIL import Image
    except ImportError:
        return {"status": "pillow_missing", "asset_count": 0}

    prepared = 0
    skipped = 0
    for image_path in image_dir.iterdir():
        if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            continue
        try:
            with Image.open(image_path) as image:
                target_format = _print_image_format(image, image_path)
                prepared_image = image
                save_kwargs: dict[str, Any] = {"dpi": (300, 300)}
                if target_format == "JPEG":
                    save_kwargs.update({"quality": 95, "subsampling": 0})
                    if image.mode not in {"RGB", "L"}:
                        prepared_image = image.convert("RGB")

                temp_path = image_path.with_name(f".{image_path.name}.tmp")
                try:
                    prepared_image.save(temp_path, format=target_format, **save_kwargs)
                    if temp_path.exists() and temp_path.stat().st_size > 0:
                        temp_path.replace(image_path)
                    else:
                        skipped += 1
                        continue
                finally:
                    if temp_path.exists():
                        temp_path.unlink(missing_ok=True)
            prepared += 1
        except Exception:
            skipped += 1
    return {"status": "prepared", "asset_count": prepared, "skipped": skipped, "dpi": 300}


def _print_image_format(image: Any, image_path: Path) -> str:
    if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
        return "PNG"
    suffix = image_path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "JPEG"
    return (image.format or "PNG").upper()


def _repair_page_file_if_needed(page_path: Path) -> str:
    html = page_path.read_text(encoding="utf-8")
    repaired = _repair_common_mojibake(html)
    if repaired != html:
        page_path.write_text(repaired, encoding="utf-8")
    return repaired


def _repair_common_mojibake(text: str) -> str:
    if not _looks_like_utf8_mojibake(text):
        return text
    try:
        repaired = text.encode("latin1").decode("utf-8")
    except UnicodeError:
        return text
    return repaired if _repair_score(repaired) > _repair_score(text) else text


def _looks_like_utf8_mojibake(text: str) -> bool:
    c1_count = sum(1 for char in text if 0x80 <= ord(char) <= 0x9F)
    chinese_count = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    marker_count = sum(text.count(marker) for marker in ("Ã", "Â", "â", "ä", "å", "æ", "ç", "è", "é"))
    return c1_count >= 8 and marker_count >= 12 and chinese_count < marker_count


def _repair_score(text: str) -> int:
    chinese_count = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    c1_count = sum(1 for char in text if 0x80 <= ord(char) <= 0x9F)
    return chinese_count - c1_count * 3


def _package_manifest(package_code: str) -> dict[str, Any]:
    try:
        return get_package(package_code)
    except FileNotFoundError:
        return {}


def _build_snapshot(report_data: dict[str, Any], html_path: str) -> dict[str, Any]:
    path = Path(html_path)
    return {
        "report_data": report_data,
        "html_path": str(path),
        "html_url": _storage_url(path),
        "source_file": report_data.get("ocr_snapshot", {}).get("source_file", "") if isinstance(report_data.get("ocr_snapshot"), dict) else "",
        "patient_name": report_data.get("patient", {}).get("name", "") if isinstance(report_data.get("patient"), dict) else "",
        "report_no": report_data.get("report", {}).get("report_id", "") if isinstance(report_data.get("report"), dict) else "",
        "ai_status": report_data.get("ai_outputs", {}).get("status", "") if isinstance(report_data.get("ai_outputs"), dict) else "",
    }


def _report_row_to_summary(row: Any) -> dict[str, Any]:
    report = dict_from_row(row) or {}
    return _report_dict_to_summary(report)


def _report_dict_to_summary(report: dict[str, Any]) -> dict[str, Any]:
    snapshot = json.loads(report.get("snapshot_json") or "{}")
    export_path = report.get("export_path")
    html_path = snapshot.get("html_path") or str(_report_html_dir(str(report["report_id"])) / "index.html")
    pages = list_report_pages(str(report["report_id"]))
    return {
        "report_id": report["report_id"],
        "case_id": report["case_id"],
        "package_code": report["package_code"],
        "status": report["status"],
        "template_version": report["template_version"],
        "rule_version": report["rule_version"],
        "prompt_version": report["prompt_version"],
        "ai_model": report["ai_model"],
        "patient_name": snapshot.get("patient_name") or "未命名",
        "report_no": snapshot.get("report_no") or report["case_id"],
        "source_file": snapshot.get("source_file") or "",
        "ai_status": snapshot.get("ai_status") or "",
        "html_path": html_path,
        "html_url": snapshot.get("html_url") or _storage_url(Path(html_path)),
        "export_path": export_path or "",
        "export_url": _storage_url(Path(export_path)) if export_path else "",
        "page_count": len(pages),
        "created_at": report["created_at"],
        "updated_at": report["updated_at"],
    }


def _report_html_dir(report_id: str) -> Path:
    path = settings.cases_dir / report_id / "html"
    if not path.exists():
        raise FileNotFoundError(f"Report HTML directory not found: {report_id}")
    return path


def _resolve_page_path(report_id: str, page_name: str) -> Path:
    safe_name = Path(page_name).name
    html_dir = _report_html_dir(report_id)
    pages = {page["page_name"] for page in list_report_pages(report_id)}
    if safe_name not in pages:
        raise FileNotFoundError(f"Report page not found: {page_name}")
    return html_dir / "pages" / safe_name


def _normalize_delete_target(path: Path) -> Path:
    candidate = path if path.is_absolute() else settings.storage_dir / path
    return candidate.resolve()


def _is_inside_any(path: Path, roots: tuple[Path, ...]) -> bool:
    resolved_roots = [root.resolve() for root in roots]
    return any(path == root or root in path.parents for root in resolved_roots)


def _storage_url(path: Path) -> str:
    resolved = Path(path)
    try:
        relative = resolved.relative_to(settings.storage_dir).as_posix()
    except ValueError:
        relative = resolved.resolve().relative_to(settings.storage_dir.resolve()).as_posix()
    return f"/storage/{relative}"


def _find_chrome() -> Path:
    for candidate in CHROME_CANDIDATES:
        if candidate.exists():
            return candidate
    raise RuntimeError("未找到Chrome或Edge浏览器，无法导出PDF。")


def _inject_print_export_assets(html: str) -> str:
    export_style = """
<style id="awk-pdf-export-style">
@page { size: A4; margin: 0; }
@media print {
  html, body {
    width: 210mm !important;
    height: 297mm !important;
    margin: 0 !important;
    overflow: hidden !important;
    background: #fff !important;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  .page-shell {
    position: relative !important;
    display: block !important;
    width: 210mm !important;
    height: 297mm !important;
    min-height: 297mm !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
    background: #fff !important;
  }
  .report-page {
    position: absolute !important;
    left: 50% !important;
    top: 50% !important;
    transform: translate(-50%, -50%) scale(var(--awk-export-scale, 1)) !important;
    transform-origin: center center !important;
    box-shadow: none !important;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  .editable:focus {
    box-shadow: none !important;
    background: transparent !important;
  }
  img {
    max-width: 100%;
    height: auto;
    object-fit: contain;
    image-rendering: auto;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  .cover-visual {
    overflow: hidden !important;
  }
  .cover-visual img {
    inset: 0 !important;
    width: 100% !important;
    height: 100% !important;
    max-width: none !important;
    object-fit: cover !important;
  }
  .cover-brand img,
  .brand-lockup img,
  .header-logo,
  .large-header-logo {
    object-fit: contain !important;
  }
  .ai-card {
    background-size: 100% 100% !important;
    background-repeat: no-repeat !important;
  }
}
</style>
<script>
(() => {
  const A4_WIDTH_PX = 794;
  const A4_HEIGHT_PX = 1123;
  function setExportScale() {
    const page = document.querySelector(".report-page");
    if (!page) return;
    const width = page.offsetWidth || 794;
    const height = page.offsetHeight || 1123;
    const scale = Math.min(A4_WIDTH_PX / width, A4_HEIGHT_PX / height);
    page.style.setProperty("--awk-export-scale", String(scale));
  }
  setExportScale();
  window.addEventListener("load", () => {
    setExportScale();
    requestAnimationFrame(setExportScale);
  });
})();
</script>
"""
    if "</head>" in html:
        return html.replace("</head>", f"{export_style}\n</head>", 1)
    return f"{export_style}\n{html}"


def _print_html_to_pdf(chrome_path: Path, html_path: Path, output_path: Path) -> None:
    args = [
        str(chrome_path),
        "--headless=new",
        "--disable-gpu",
        "--disable-extensions",
        "--allow-file-access-from-files",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=1200",
        "--window-size=1800,2400",
        f"--print-to-pdf={output_path}",
        html_path.as_uri(),
    ]
    result = subprocess.run(args, capture_output=True, text=True, timeout=45, check=False)
    if result.returncode != 0 or not output_path.exists():
        raise RuntimeError(f"Chrome PDF导出失败：{result.stderr or result.stdout}")


def _merge_pdfs(page_pdfs: list[Path], output_path: Path) -> None:
    writer = PdfWriter()
    for page_pdf in page_pdfs:
        reader = PdfReader(str(page_pdf))
        for page in reader.pages:
            writer.add_page(page)
    with output_path.open("wb") as handle:
        writer.write(handle)
