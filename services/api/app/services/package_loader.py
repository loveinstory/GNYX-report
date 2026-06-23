from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from app.core.config import settings


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def list_packages() -> list[dict[str, Any]]:
    packages: list[dict[str, Any]] = []
    for manifest in settings.packages_dir.glob("P*/manifest.json"):
        data = _read_json(manifest)
        packages.append(
            {
                "package_code": data["package_code"],
                "package_name": data["package_name"],
                "status": data.get("status", "placeholder"),
                "version": data.get("version", "0.1.0"),
                "page_count": len(data.get("pages", [])),
            }
        )
    return sorted(packages, key=lambda item: item["package_code"])


def get_package(package_code: str) -> dict[str, Any]:
    manifest = settings.packages_dir / package_code / "manifest.json"
    if not manifest.exists():
        raise FileNotFoundError(f"Package {package_code} is not configured")
    return _read_json(manifest)


def get_package_config(package_code: str) -> dict[str, Any]:
    package_dir = settings.packages_dir / package_code
    if not package_dir.exists():
        raise FileNotFoundError(f"Package {package_code} is not configured")

    return {
        "manifest": _read_optional_json(package_dir / "manifest.json"),
        "fields": _read_optional_json(package_dir / "fields.json"),
        "rules": _read_optional_json(package_dir / "rules.json"),
        "ocr_strategy": _read_optional_json(package_dir / "ocr-strategy.json"),
        "template_fields": list_template_fields(package_code),
    }


def list_template_fields(package_code: str) -> list[dict[str, Any]]:
    template_pages_dir = settings.packages_dir / package_code / "templates" / "html" / "pages"
    if not template_pages_dir.exists():
        return []

    fields: list[dict[str, Any]] = []
    for html_path in sorted(template_pages_dir.glob("*.html")):
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
        for node in soup.select("[data-field]"):
            key = str(node.get("data-field") or "")
            if not key:
                continue
            fields.append(
                {
                    "field_key": key,
                    "page": html_path.name,
                    "tag": node.name,
                    "sample_text": " ".join(node.get_text(" ", strip=True).split()),
                }
            )
    return fields


def list_samples(package_code: str) -> list[dict[str, Any]]:
    sample_dir = settings.packages_dir / package_code / "tests" / "samples"
    if not sample_dir.exists():
        return []
    samples = []
    for path in sorted(sample_dir.glob("*.pdf")):
        samples.append(
            {
                "name": path.name,
                "size": path.stat().st_size,
                "path": str(path),
            }
        )
    return samples


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _read_json(path)
