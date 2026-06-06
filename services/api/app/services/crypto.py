from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet

from app.core.config import settings


def _key_path() -> Path:
    return settings.storage_dir / "master.key"


def get_fernet() -> Fernet:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    path = _key_path()
    if not path.exists():
        path.write_bytes(Fernet.generate_key())
    return Fernet(path.read_bytes())


def encrypt_secret(value: str) -> str:
    return get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    return get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")

