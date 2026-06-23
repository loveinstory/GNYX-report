from __future__ import annotations

from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.core.config import settings
from app.db.database import ensure_storage_dirs, init_db
from app.services.admin import create_backup, list_credentials, save_credential
from app.services.ai_interpreter import get_ai_config, interpret_report_with_deepseek, test_deepseek_connection
from app.services.accounts import (
    create_user,
    delete_user,
    ensure_default_admin,
    list_users,
    login,
    revoke_session,
    token_from_request,
    update_user,
)
from app.services.authz import ADMIN, CUSTOMER_SERVICE, INSPECTOR, ROLE_LABELS, current_user, require_authenticated, require_role
from app.services.documents import (
    create_import_job_from_files,
    list_documents_for_ocr,
    list_imported_documents,
    mark_package_documents_completed,
)
from app.services.jobs import create_job, get_job, list_jobs, run_demo_job, update_job
from app.services.ocr_logs import (
    get_ocr_parse_log,
    list_ocr_parse_logs,
    list_pending_ocr_parse_logs,
    mark_ocr_logs_consumed,
)
from app.services.package_loader import get_package, get_package_config, list_packages, list_samples
from app.services.report_data_builder import build_report_data_from_ocr_result
from app.services.report_renderer import render_report
from app.services.report_review import (
    delete_review_report,
    export_report_pdf,
    get_report_page_content,
    get_review_report,
    list_review_reports,
    save_report_page_content,
    unlock_reviewed_report,
)


class BatchRequest(BaseModel):
    package_code: str = "P02"


class CredentialRequest(BaseModel):
    provider: str = Field(..., examples=["deepseek"])
    label: str = Field(..., examples=["DeepSeek V4"])
    value: str = Field(..., min_length=1)


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    display_name: str = ""
    password: str
    role: str = CUSTOMER_SERVICE
    is_active: bool = True


class UpdateUserRequest(BaseModel):
    display_name: str | None = None
    password: str | None = None
    role: str | None = None
    is_active: bool | None = None


class RenderRequest(BaseModel):
    package_code: str = "P02"
    report_data: dict[str, Any]


class RenderFromOcrRequest(BaseModel):
    package_code: str = "P02"
    log_id: str | None = None
    render_html: bool = True


class AiConnectionTestRequest(BaseModel):
    model: str | None = None
    base_url: str | None = None


class AiInterpretRequest(BaseModel):
    package_code: str = "P02"
    log_id: str | None = None
    model: str | None = None
    base_url: str | None = None
    dry_run: bool = False
    render_html: bool = True


class SaveReportPageRequest(BaseModel):
    html_content: str = Field(..., min_length=1)


app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5188",
        "http://localhost:5188",
        "http://192.168.20.243:5188",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
settings.storage_dir.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=settings.storage_dir), name="storage")


@app.on_event("startup")
def startup() -> None:
    ensure_storage_dirs()
    init_db()
    ensure_default_admin()


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "app": settings.app_name,
        "status": "healthy",
        "api_port": settings.api_port,
        "frontend_port": settings.frontend_port,
        "forbidden_ports": list(settings.forbidden_ports),
    }


@app.get("/auth/roles")
def auth_roles(request: Request) -> dict[str, Any]:
    user = None
    try:
        user = current_user(request)
    except HTTPException:
        user = None
    return {
        "current_role": user["role"] if user else "",
        "current_user": user,
        "roles": [{"key": key, "label": label} for key, label in ROLE_LABELS.items()],
    }


@app.post("/auth/login")
def auth_login(request_data: LoginRequest) -> dict[str, Any]:
    result = login(request_data.username, request_data.password)
    if result is None:
        raise HTTPException(status_code=401, detail="账号或密码错误。")
    return result


@app.post("/auth/logout")
def auth_logout(request: Request) -> dict[str, str]:
    revoke_session(token_from_request(request))
    return {"status": "succeeded"}


@app.get("/auth/me")
def auth_me(request: Request) -> dict[str, Any]:
    return current_user(request)


@app.get("/admin/users")
def admin_user_list(request: Request) -> list[dict[str, Any]]:
    require_role(request, {ADMIN})
    return list_users()


@app.post("/admin/users")
def admin_user_create(request_data: CreateUserRequest, request: Request) -> dict[str, Any]:
    require_role(request, {ADMIN})
    try:
        return create_user(
            username=request_data.username,
            display_name=request_data.display_name,
            password=request_data.password,
            role=request_data.role,
            is_active=request_data.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/admin/users/{user_id}")
def admin_user_update(user_id: str, request_data: UpdateUserRequest, request: Request) -> dict[str, Any]:
    actor = current_user(request)
    if actor["role"] != ADMIN:
        raise HTTPException(status_code=403, detail="当前角色无权限执行该操作，允许角色：管理员")
    try:
        return update_user(
            user_id,
            actor_user_id=actor["user_id"],
            display_name=request_data.display_name,
            password=request_data.password,
            role=request_data.role,
            is_active=request_data.is_active,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="User not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/admin/users/{user_id}")
def admin_user_delete(user_id: str, request: Request) -> dict[str, str]:
    actor = current_user(request)
    if actor["role"] != ADMIN:
        raise HTTPException(status_code=403, detail="当前角色无权限执行该操作，允许角色：管理员")
    try:
        return delete_user(user_id, actor_user_id=actor["user_id"])
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="User not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/packages")
def packages(request: Request) -> list[dict[str, Any]]:
    require_authenticated(request)
    return list_packages()


@app.get("/packages/{package_code}")
def package_detail(package_code: str, request: Request) -> dict[str, Any]:
    require_authenticated(request)
    try:
        return get_package(package_code)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/packages/{package_code}/config")
def package_config(package_code: str, request: Request) -> dict[str, Any]:
    require_authenticated(request)
    try:
        return get_package_config(package_code)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/packages/{package_code}/samples")
def package_samples(package_code: str, request: Request) -> list[dict[str, Any]]:
    require_authenticated(request)
    return list_samples(package_code)


@app.get("/jobs")
def jobs(request: Request) -> list[dict[str, Any]]:
    require_authenticated(request)
    return list_jobs()


@app.get("/jobs/{job_id}")
def job_detail(job_id: str, request: Request) -> dict[str, Any]:
    require_authenticated(request)
    try:
        return get_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc


@app.get("/documents")
def documents(request: Request, package_code: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    require_role(request, {ADMIN, CUSTOMER_SERVICE})
    return list_imported_documents(package_code=package_code, limit=limit)


@app.post("/documents/import")
async def documents_import(
    request: Request,
    package_code: str = Form("P02"),
    files: list[UploadFile] = File(...),
) -> dict[str, Any]:
    require_role(request, {ADMIN, CUSTOMER_SERVICE})
    file_payload: list[tuple[str, bytes]] = []
    for upload in files:
        file_payload.append((upload.filename or "document.pdf", await upload.read()))
    return create_import_job_from_files(package_code=package_code, files=file_payload)


@app.get("/ocr/logs")
def ocr_logs(
    request: Request,
    package_code: str | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    require_authenticated(request)
    return list_ocr_parse_logs(package_code=package_code, page=page, page_size=page_size)


@app.get("/ocr/logs/{log_id}")
def ocr_log_detail(log_id: str, request: Request) -> dict[str, Any]:
    require_authenticated(request)
    try:
        return get_ocr_parse_log(log_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="OCR log not found") from exc


def _start_batch(job_type: str, request: BatchRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    job = create_job(job_type=job_type, package_code=request.package_code, payload=request.model_dump())
    background_tasks.add_task(run_demo_job, job["job_id"])
    return job


@app.post("/batch/import")
def batch_import(request_data: BatchRequest, request: Request, background_tasks: BackgroundTasks) -> dict[str, Any]:
    require_role(request, {ADMIN, CUSTOMER_SERVICE})
    job = create_job(
        job_type="import_documents",
        package_code=request_data.package_code,
        payload=request_data.model_dump(),
        total=0,
    )
    update_job(job["job_id"], status="failed", message="请通过“导入PDF任务”选择PDF文件上传。")
    return get_job(job["job_id"])


@app.post("/batch/ocr")
def batch_ocr(request_data: BatchRequest, request: Request, background_tasks: BackgroundTasks) -> dict[str, Any]:
    require_role(request, {ADMIN, CUSTOMER_SERVICE})
    documents = list_documents_for_ocr(request_data.package_code)
    job = create_job(
        job_type="ocr_documents",
        package_code=request_data.package_code,
        payload={**request_data.model_dump(), "document_count": len(documents)},
        total=len(documents),
    )
    background_tasks.add_task(run_demo_job, job["job_id"])
    return job


@app.post("/batch/interpret")
def batch_interpret(request_data: BatchRequest, request: Request, background_tasks: BackgroundTasks) -> dict[str, Any]:
    require_role(request, {ADMIN, CUSTOMER_SERVICE})
    imported_documents = list_imported_documents(request_data.package_code)
    active_source_files = {
        str(item.get("original_name") or "").strip()
        for item in imported_documents
        if str(item.get("original_name") or "").strip()
    }
    candidate_logs = list_pending_ocr_parse_logs(package_code=request_data.package_code, limit=200)
    if active_source_files:
        candidate_logs = [
            log for log in candidate_logs if str(log.get("source_file") or "").strip() in active_source_files
        ]
    logs = _dedupe_latest_ocr_logs(candidate_logs)
    log_ids = [str(log["log_id"]) for log in logs]
    job = create_job(
        job_type="generate_ai_report",
        package_code=request_data.package_code,
        payload={**request_data.model_dump(), "ocr_log_ids": log_ids, "ocr_log_count": len(log_ids)},
        total=len(log_ids),
    )
    background_tasks.add_task(run_demo_job, job["job_id"])
    return job


def _dedupe_latest_ocr_logs(logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for log in logs:
        structured = log.get("result_json", {}).get("structured_report", {})
        report_id = str(structured.get("report_id") or "")
        key = f"{log.get('package_code', '')}:{report_id or log.get('source_file', '')}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(log)
    return deduped


@app.post("/batch/export")
def batch_export(request_data: BatchRequest, request: Request, background_tasks: BackgroundTasks) -> dict[str, Any]:
    require_role(request, {ADMIN})
    return _start_batch("export_pdf", request_data, background_tasks)


@app.post("/admin/credentials")
def admin_credentials(request_data: CredentialRequest, request: Request) -> dict[str, str]:
    require_role(request, {ADMIN})
    return save_credential(request_data.provider, request_data.label, request_data.value)


@app.get("/admin/credentials")
def admin_credential_list(request: Request) -> list[dict[str, str]]:
    require_role(request, {ADMIN})
    return list_credentials()


@app.post("/admin/backups")
def admin_backups(request: Request) -> dict[str, str]:
    require_role(request, {ADMIN})
    return create_backup()


@app.post("/reports/render")
def reports_render(request_data: RenderRequest, request: Request) -> dict[str, str]:
    require_role(request, {ADMIN, CUSTOMER_SERVICE})
    try:
        return render_report(request_data.package_code, request_data.report_data)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/reports")
def reports(request: Request, package_code: str | None = None, status: str = "pending_review") -> list[dict[str, Any]]:
    require_role(request, {ADMIN, INSPECTOR})
    return list_review_reports(package_code=package_code, status=status)


@app.get("/reports/{report_id}")
def report_detail(report_id: str, request: Request) -> dict[str, Any]:
    require_role(request, {ADMIN, INSPECTOR})
    try:
        return get_review_report(report_id)
    except (KeyError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail="Report not found") from exc


@app.get("/reports/{report_id}/pages/{page_name}")
def report_page(report_id: str, page_name: str, request: Request) -> dict[str, str]:
    require_role(request, {ADMIN, INSPECTOR})
    try:
        return get_report_page_content(report_id, page_name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Report page not found") from exc


@app.post("/reports/{report_id}/pages/{page_name}")
def report_page_save(report_id: str, page_name: str, request_data: SaveReportPageRequest, request: Request) -> dict[str, Any]:
    require_role(request, {ADMIN, INSPECTOR})
    try:
        return save_report_page_content(report_id, page_name, request_data.html_content)
    except (KeyError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail="Report page not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc


@app.post("/reports/{report_id}/export")
def report_export(report_id: str, request: Request) -> dict[str, Any]:
    require_role(request, {ADMIN, INSPECTOR})
    try:
        return export_report_pdf(report_id)
    except (KeyError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail="Report not found") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc


@app.post("/reports/{report_id}/unlock")
def report_unlock(report_id: str, request: Request) -> dict[str, Any]:
    require_role(request, {ADMIN})
    try:
        return unlock_reviewed_report(report_id)
    except (KeyError, FileNotFoundError) as exc:
        raise HTTPException(status_code=404, detail="Report not found") from exc


@app.delete("/reports/{report_id}")
def report_delete(report_id: str, request: Request) -> dict[str, Any]:
    require_role(request, {ADMIN, INSPECTOR})
    try:
        return delete_review_report(report_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Report not found") from exc


@app.post("/reports/render-from-ocr")
def reports_render_from_ocr(request_data: RenderFromOcrRequest, request: Request) -> dict[str, Any]:
    require_role(request, {ADMIN, CUSTOMER_SERVICE})
    try:
        if request_data.log_id:
            log = get_ocr_parse_log(request_data.log_id)
        else:
            logs = list_pending_ocr_parse_logs(package_code=request_data.package_code, limit=1)
            if not logs:
                raise KeyError("latest")
            log = logs[0]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="OCR log not found") from exc

    report_data = build_report_data_from_ocr_result(request_data.package_code, log["result_json"])
    response: dict[str, Any] = {
        "log_id": log["log_id"],
        "source_file": log["source_file"],
        "package_code": request_data.package_code,
        "report_data": report_data,
    }
    if request_data.render_html:
        try:
            response["render_result"] = render_report(request_data.package_code, report_data)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return response


@app.get("/ai/config")
def ai_config(request: Request) -> dict[str, Any]:
    require_authenticated(request)
    return get_ai_config()


@app.post("/ai/test-connection")
def ai_test_connection(request_data: AiConnectionTestRequest, request: Request) -> dict[str, Any]:
    require_role(request, {ADMIN})
    try:
        return test_deepseek_connection(model=request_data.model, base_url=request_data.base_url)
    except RuntimeError as exc:
        return {
            "status": "failed",
            "message": str(exc),
            "model": request_data.model,
            "base_url": request_data.base_url,
        }


@app.post("/ai/interpret")
def ai_interpret(request_data: AiInterpretRequest, request: Request) -> dict[str, Any]:
    require_role(request, {ADMIN, CUSTOMER_SERVICE})
    try:
        if request_data.log_id:
            log = get_ocr_parse_log(request_data.log_id)
        else:
            logs = list_pending_ocr_parse_logs(package_code=request_data.package_code, limit=1)
            if not logs:
                raise KeyError("latest")
            log = logs[0]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="OCR log not found") from exc

    report_data = build_report_data_from_ocr_result(request_data.package_code, log["result_json"])
    try:
        result = interpret_report_with_deepseek(
            package_code=request_data.package_code,
            ocr_result=log["result_json"],
            report_data=report_data,
            model=request_data.model,
            base_url=request_data.base_url,
            dry_run=request_data.dry_run,
        )
    except RuntimeError as exc:
        return {
            "status": "failed",
            "message": str(exc),
            "package_code": request_data.package_code,
            "source_file": log["source_file"],
            "report_data": report_data,
        }

    response = {
        "log_id": log["log_id"],
        "source_file": log["source_file"],
        "package_code": request_data.package_code,
        **result,
    }
    if request_data.render_html and "report_data" in result:
        try:
            response["render_result"] = render_report(request_data.package_code, result["report_data"])
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    if result.get("status") == "succeeded" and not request_data.dry_run:
        mark_ocr_logs_consumed([str(log["log_id"])])
        response["cleared_documents"] = mark_package_documents_completed(request_data.package_code)
    return response
