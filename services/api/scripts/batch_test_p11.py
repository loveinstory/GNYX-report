from __future__ import annotations

import json
from pathlib import Path

from app.services.ocr_engine import parse_pdf_to_standard_ocr_json


TARGET_DIR = Path(r"D:\AWK-OCR\功能医学检测报告模板（2026.4.3）\P12-1\原始报告")


def main() -> None:
    rows: list[dict[str, object]] = []
    for pdf_path in sorted(TARGET_DIR.glob("*.pdf")):
        result = parse_pdf_to_standard_ocr_json(pdf_path=pdf_path, package_code="P11")
        tests = result.get("structured_report", {}).get("tests", [])
        food_tests = [item for item in tests if str(item.get("item_code") or "").startswith("food_")]
        immune_tests = [item for item in tests if str(item.get("item_code") or "") in {"igg1", "igg2", "igg3", "igg4", "total_ige"}]
        rows.append(
            {
                "file": pdf_path.name,
                "structured_test_count": len(tests),
                "food_count": len(food_tests),
                "immune_count": len(immune_tests),
                "warnings": result.get("warnings", []),
            }
        )
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
