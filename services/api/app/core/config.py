from __future__ import annotations

import os
from pathlib import Path


class Settings:
    repo_root: Path = Path(__file__).resolve().parents[4]
    app_name: str = "AWK-report-gnyx API"
    api_host: str = os.getenv("AWK_API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("AWK_API_PORT", "8111"))
    api_public_base_url: str = os.getenv("AWK_API_PUBLIC_BASE_URL", f"http://{api_host}:{api_port}")
    frontend_port: int = int(os.getenv("AWK_FRONTEND_PORT", "5188"))
    forbidden_ports: tuple[str, ...] = ("5173", "8000-8010")
    storage_dir: Path = repo_root / os.getenv("AWK_STORAGE_DIR", "storage")
    database_path: Path = repo_root / os.getenv("AWK_DATABASE_PATH", "storage/app.db")
    packages_dir: Path = repo_root / "packages"
    p02_sample_dir: Path = repo_root / "packages/P02/tests/samples"
    export_dir: Path = storage_dir / "exports"
    backup_dir: Path = storage_dir / "backups"
    cases_dir: Path = storage_dir / "cases"
    import_dir: Path = storage_dir / "imports"


settings = Settings()
