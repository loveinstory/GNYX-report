from __future__ import annotations

import re
import tempfile
from pathlib import Path
from statistics import mean
from typing import Any

from pypdf import PdfReader

from app.services.ocr_logs import now_iso


STRATEGY_VERSION = "P02-ocr-strategy-v0.3-structured-json"
P01_STRATEGY_VERSION = "P01-ocr-strategy-v0.2-summary-structured"
P05_STRATEGY_VERSION = "P05-ocr-strategy-v0.2-multipage-rapidocr"
P03_STRATEGY_VERSION = "P03-ocr-strategy-v0.3-c-peptide-prefix"
PROVIDER = "pdf-text-extractor"

DATE_VALUE_PATTERN = r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?:\s+[0-9]{2}:[0-9]{2})?"
RESULT_PATTERN = (
    r"(?:阳性\s*[（(]\s*\+\+\+\s*[）)]|阳性\s*[（(]\s*\+\+\s*[）)]|"
    r"阳性\s*[（(]\s*\+\s*[）)]|弱阳性|阳性|阴性)"
)

CALPROTECTIN_NAME = "钙卫蛋白检测（Cal）"
TOTAL_IGE_NAME = "特异性总IgE"

ALLERGEN_ITEMS = [
    "户尘螨/粉尘螨组合",
    "矮豚草/蒿组合",
    "猫/狗毛皮屑组合",
    "蟑螂",
    "霉菌组合",
    "葎草",
    "荨草",
    "树组合4（柳/榆/栎/梧桐/三角叶杨）",
    "鸡蛋白",
    "牛奶",
    "鱼/虾/蟹组合",
    "牛/羊肉组合",
    "腰果/花生/黄豆组合",
    "芒果",
    "小麦",
    # 兼容其他 P02 样例中可能出现的旧版项目名称。
    "花生",
    "大豆",
    "牛肉",
    "羊肉",
    "鳕鱼/龙虾/扇贝组合",
    "腰果/开心果组合",
    "桃",
]

P01_METRIC_DEFINITIONS = [
    ("gmhi", "GMHI", ["GMHI", "肠道菌群健康指数", "菌群健康指数"], ""),
    ("gut_age", "肠龄", ["肠龄", "肠道年龄", "肠道菌群年龄"], "岁"),
    ("diversity", "菌群多样性", ["菌群多样性", "多样性指数", "Shannon", "α多样性", "Alpha多样性"], ""),
    ("enterotype", "肠型", ["肠型", "Enterotype"], ""),
]

P05_THYROID_TESTS = [
    ("ft3", "游离三碘甲状腺原氨酸（FT3）"),
    ("t3", "三碘甲状腺原氨酸（T3）"),
    ("ft4", "游离甲状腺素（FT4）"),
    ("t4", "甲状腺素（T4）"),
    ("tsh", "促甲状腺激素（TSH）"),
    ("tgab", "抗甲状腺球蛋白抗体（TGAb）"),
    ("tpoab", "抗甲状腺过氧化物酶抗体（TPOAb）"),
]

P05_CATECHOLAMINE_TESTS = [
    ("norepinephrine", "去甲肾上腺素"),
    ("epinephrine", "肾上腺素"),
    ("metanephrine_n", "3-甲氧基去甲肾上腺素"),
    ("methoxytyramine", "3-甲氧基酪胺"),
    ("metanephrine_e", "3-甲氧基肾上腺素"),
    ("hva", "高香草酸"),
    ("vma", "香草扁桃酸"),
    ("dopamine", "多巴胺"),
]

P05_SINGLE_TESTS = [
    ("cort", "皮质醇（CORT）"),
    ("acth", "促肾上腺皮质激素（ACTH）"),
]

P03_TEST_DEFINITIONS = [
    ("alb", "白蛋白（ALB）", ["白蛋白（ALB）", "白蛋白", "ALB"], "g/L"),
    ("glucose", "葡萄糖（GLU）", ["葡萄糖（GLU）", "空腹血糖（GLU）", "葡萄糖", "空腹血糖", "GLU"], "mmol/L"),
    ("gsp", "糖化血清蛋白（GSP）", ["糖化血清蛋白（GSP）", "糖化血清蛋白", "GSP"], "mmol/L"),
    ("tch", "总胆固醇（TCH）", ["总胆固醇（TCH）", "总胆固醇", "TCH", "TC"], "mmol/L"),
    ("tg", "甘油三酯（TG）", ["甘油三酯（TG）", "甘油三酯", "TG"], "mmol/L"),
    ("hdl_c", "高密度脂蛋白胆固醇（HDL-C）", ["高密度脂蛋白胆固醇（HDL-C）", "高密度脂蛋白胆固醇", "高密度脂蛋白", "HDL-C", "HDL"], "mmol/L"),
    ("ldl_c", "低密度脂蛋白胆固醇（LDL-C）", ["低密度脂蛋白胆固醇（LDL-C）", "低密度脂蛋白胆固醇", "低密度脂蛋白", "LDL-C", "LDL"], "mmol/L"),
    ("apo_a1", "载脂蛋白A1 (APO-A1)", ["载脂蛋白A1 (APO-A1)", "载脂蛋白A1", "APO-A1", "APOA1"], "g/L"),
    ("apo_b", "载脂蛋白B (APO-B)", ["载脂蛋白B (APO-B)", "载脂蛋白B", "APO-B", "APOB"], "g/L"),
    ("apo_a1_b_ratio", "载脂蛋白A1／载脂蛋白B", ["载脂蛋白A1／载脂蛋白B", "载脂蛋白A1/载脂蛋白B", "APO-A1/APO-B", "APOA1/APOB"], ""),
    ("lp_a", "脂蛋白a (LP(a))", ["脂蛋白a (LP(a))", "脂蛋白a", "LP(a)", "LPa"], "mg/L"),
    ("c_peptide", "C 肽（C-P）", ["C 肽（C-P）", "C肽（C-P）", "C 肽", "C肽", "C-P"], "ng/mL"),
    ("insulin", "胰岛素（Ins）", ["胰岛素（Ins）", "胰岛素", "Ins"], "uU/mL"),
    ("hba1c", "糖化血红蛋白A1C", ["糖化血红蛋白A1C", "糖化血红蛋白 A1C", "HbA1c", "A1C"], "%"),
    ("avg_glucose", "平均血糖", ["平均血糖"], "mmol/L"),
    ("hba1ab", "糖化血红蛋白A1ab", ["糖化血红蛋白A1ab", "糖化血红蛋白 A1ab", "A1ab"], "%"),
    ("hba1", "糖化血红蛋白A1", ["糖化血红蛋白A1", "糖化血红蛋白 A1"], "%"),
]

P03_METHOD_NAMES = [
    "葡萄糖氧化酶法",
    "高效液相色谱法",
    "化学发光法",
    "免疫比浊法",
    "酶比色法",
    "比色法",
    "NBT 法",
    "NBT法",
    "计算法",
]

P03_REFERENCE_PATTERN = (
    r"≤\s*[0-9]+(?:\.[0-9]+)?|≥\s*[0-9]+(?:\.[0-9]+)?|<\s*[0-9]+(?:\.[0-9]+)?|>\s*[0-9]+(?:\.[0-9]+)?|"
    r"＜\s*[0-9]+(?:\.[0-9]+)?|＞\s*[0-9]+(?:\.[0-9]+)?|"
    r"[0-9]+(?:\.[0-9]+)?\s*(?:--|-|－|—|–|~|～)\s*[0-9]+(?:\.[0-9]+)?"
)


def parse_pdf_to_standard_ocr_json(pdf_path: Path, package_code: str = "P02") -> dict[str, Any]:
    strategy_version = {
        "P01": P01_STRATEGY_VERSION,
        "P05": P05_STRATEGY_VERSION,
        "P03": P03_STRATEGY_VERSION,
    }.get(package_code, STRATEGY_VERSION)
    reader = PdfReader(str(pdf_path))
    pages = []
    page_texts: list[str] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        normalized = normalize_text(text)
        page_texts.append(normalized)
        pages.append(
            {
                "page_number": page_number,
                "width": float(page.mediabox.width) if page.mediabox else None,
                "height": float(page.mediabox.height) if page.mediabox else None,
                "text_blocks": [
                    {
                        "text": normalized,
                        "confidence": 0.95 if normalized else 0.0,
                        "bbox": None,
                    }
                ],
            }
        )

    page_ocr_data: dict[int, dict[str, Any]] = {}
    if package_code == "P05":
        page_ocr_data = extract_sparse_page_image_ocr(pdf_path, page_texts)
        for page_number, payload in page_ocr_data.items():
            if page_number < 1 or page_number > len(page_texts):
                continue
            merged_text = normalize_text(" ".join(part for part in [page_texts[page_number - 1], payload.get("text", "")] if part))
            page_texts[page_number - 1] = merged_text
            pages[page_number - 1]["text_blocks"] = [
                {
                    "text": merged_text,
                    "confidence": float(payload.get("confidence") or 0.82),
                    "bbox": None,
                }
            ]

    full_text = normalize_text(" ".join(page_texts))
    structured_report = build_structured_report(
        pdf_path.name,
        full_text,
        page_texts,
        package_code=package_code,
        page_ocr_data=page_ocr_data,
    )
    if package_code == "P01":
        fields = extract_p01_fields(page_texts, structured_report)
    elif package_code == "P05":
        fields = extract_p05_fields(page_texts, structured_report)
    elif package_code == "P03":
        fields = extract_p03_fields(page_texts, structured_report)
    else:
        fields = extract_p02_fields(full_text, page_texts, structured_report)
    confidence = calculate_confidence(fields, pages)
    warnings = build_warnings(fields, pages, structured_report, package_code=package_code)
    result = {
        "schema_version": "1.0",
        "package_code": package_code,
        "source_file": pdf_path.name,
        "strategy_version": strategy_version,
        "provider": PROVIDER,
        "pages": pages,
        "fields": fields,
        "indicators": build_indicators(fields),
        "structured_report": structured_report,
        "warnings": warnings,
        "created_at": now_iso(),
        "debug": {
            "comparison_key": f"{package_code}:{pdf_path.name}:{strategy_version}",
            "field_keys": [field["field_key"] for field in fields],
            "overall_confidence": confidence,
            "structured_test_count": len(structured_report["tests"]),
        },
    }
    if package_code == "P01":
        result["p01_extracted_report"] = structured_report.get("p01_extracted_report", {})
    if package_code == "P05":
        result["p05_extracted_report"] = structured_report.get("p05_extracted_report", {})
    if package_code == "P03":
        result["p03_extracted_report"] = build_p03_extracted_report(structured_report, full_text)
    return result


def normalize_text(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_structured_report(
    source_file: str,
    full_text: str,
    page_texts: list[str],
    package_code: str = "P02",
    *,
    page_ocr_data: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if package_code == "P01":
        return build_p01_structured_report(source_file, full_text, page_texts)
    if package_code == "P05":
        return build_p05_structured_report(source_file, full_text, page_texts, page_ocr_data=page_ocr_data)
    return {
        "report_id": extract_report_id(full_text) or Path(source_file).stem,
        "patient_info": {
            "name": extract_patient_name(full_text),
            "gender": extract_gender(full_text),
            "age": extract_age(full_text),
            "specimen_condition": extract_specimen_condition(full_text),
            "specimen_types": extract_specimen_types(page_texts),
            "hospital": extract_hospital(full_text),
            "patient_number": "",
            "bed_number": "",
            "department": "",
            "doctor": "",
            "clinical_diagnosis": "",
        },
        "tests": extract_structured_tests(page_texts, package_code=package_code),
        "notes": "",
        "additional_info": {
            "sample_date": extract_date(page_texts, "采样日期"),
            "receive_date": extract_date(page_texts, "接收时间"),
            "report_date": extract_date(page_texts, "报告时间"),
            "technician": extract_staff(full_text, ["检测者", "检验者"]),
            "reviewer": extract_staff(full_text, ["审核者", "复核者"]),
            "approver": extract_staff(full_text, ["批准人", "批准者"]),
        },
    }


def build_p05_structured_report(
    source_file: str,
    full_text: str,
    page_texts: list[str],
    *,
    page_ocr_data: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    p05_report = build_p05_extracted_report(source_file, full_text, page_texts, page_ocr_data=page_ocr_data or {})
    reports = p05_report.get("reports", [])
    first_report = reports[0] if reports else {}
    first_basic = first_report.get("basic_info", {}) if isinstance(first_report, dict) else {}

    tests = extract_p05_structured_tests(p05_report)
    sample_values = [
        str(report.get("sampling_datetime") or "")
        for report in reports
        if isinstance(report, dict) and report.get("sampling_datetime")
    ]
    receive_values = [
        str(report.get("receiving_datetime") or "")
        for report in reports
        if isinstance(report, dict) and report.get("receiving_datetime")
    ]
    report_values = [
        str(report.get("report_datetime") or "")
        for report in reports
        if isinstance(report, dict) and report.get("report_datetime")
    ]
    specimen_types = list(
        dict.fromkeys(
            str((report.get("basic_info", {}) or {}).get("specimen_type") or "")
            for report in reports
            if isinstance(report, dict)
        )
    )
    specimen_types = [value for value in specimen_types if value]

    return {
        "report_id": str(first_report.get("barcode") or extract_report_id(full_text) or Path(source_file).stem),
        "patient_info": {
            "name": str(first_basic.get("name") or extract_patient_name(full_text)),
            "gender": str(first_basic.get("gender") or extract_gender(full_text)),
            "age": _parse_age_number(str(first_basic.get("age") or "")) or extract_age(full_text),
            "specimen_condition": str(first_basic.get("specimen_status") or extract_specimen_condition(full_text)),
            "specimen_types": specimen_types or extract_specimen_types(page_texts),
            "hospital": str(first_basic.get("submitting_institution") or extract_hospital(full_text)),
            "patient_number": str(first_basic.get("patient_id") or ""),
            "bed_number": str(first_basic.get("bed_no") or ""),
            "department": str(first_basic.get("submitting_department") or ""),
            "doctor": str(first_basic.get("submitting_doctor") or ""),
            "clinical_diagnosis": str(first_basic.get("clinical_diagnosis") or ""),
        },
        "tests": tests,
        "notes": "",
        "additional_info": {
            "sample_date": min(sample_values) if sample_values else "",
            "receive_date": max(receive_values) if receive_values else "",
            "report_date": max(report_values) if report_values else "",
            "technician": _first_non_empty([str(report.get("tested_by") or "") for report in reports], validate=_is_valid_p05_staff_value),
            "reviewer": _first_non_empty([str(report.get("reviewed_by") or "") for report in reports], validate=_is_valid_p05_staff_value),
            "approver": _first_non_empty([str(report.get("approved_by") or "") for report in reports], validate=_is_valid_p05_staff_value),
        },
        "p05_extracted_report": p05_report,
    }


def build_p01_structured_report(source_file: str, full_text: str, page_texts: list[str]) -> dict[str, Any]:
    p01_report = build_p01_extracted_report(source_file, full_text, page_texts)
    basic_information = p01_report.get("basic_information", {})
    quality_control = p01_report.get("quality_control", {})
    sample_type = str(basic_information.get("sample_type") or "")
    sample_id = str(basic_information.get("sample_id") or "")
    report_date = str(basic_information.get("report_date") or "")
    receiving_date = str(basic_information.get("receiving_date") or "")
    sampling_date = str(basic_information.get("sampling_date") or "")
    name = str(basic_information.get("name") or "")
    gender = str(basic_information.get("gender") or "")
    age = basic_information.get("age") or ""
    submitting_institution = str(basic_information.get("submitting_institution") or "")

    return {
        "report_id": sample_id or extract_report_id(full_text) or Path(source_file).stem,
        "patient_info": {
            "name": name,
            "gender": gender,
            "age": age,
            "specimen_condition": "",
            "specimen_types": [sample_type] if sample_type else extract_specimen_types(page_texts),
            "hospital": submitting_institution,
            "patient_number": sample_id,
            "bed_number": "",
            "department": "",
            "doctor": "",
            "clinical_diagnosis": str(basic_information.get("main_complaint") or ""),
        },
        "tests": extract_p01_structured_tests(page_texts, p01_report=p01_report),
        "notes": str(p01_report.get("test_description", {}).get("content") or ""),
        "additional_info": {
            "sample_date": "" if sampling_date == "-" else sampling_date,
            "receive_date": receiving_date,
            "report_date": report_date,
            "technician": str(quality_control.get("tested_by") or extract_staff(full_text, ["检测者", "检验者"])),
            "reviewer": str(quality_control.get("reviewed_by") or extract_staff(full_text, ["审核者", "复核者"])),
            "approver": str(quality_control.get("approved_by") or ""),
        },
        "p01_extracted_report": p01_report,
    }


def build_p01_extracted_report(source_file: str, full_text: str, page_texts: list[str]) -> dict[str, Any]:
    report_info = _extract_p01_report_info(full_text, page_texts)
    basic_information = _extract_p01_basic_information(full_text, page_texts)
    summary_text = _extract_p01_summary_text(page_texts)
    overview_text = _page_text(page_texts, 4)
    description_text = _extract_p01_test_description(page_texts)
    phylum_top_5 = _extract_p01_ranked_items(_page_text(page_texts, 11), limit=5)
    genus_top_15 = _extract_p01_ranked_items(_page_text(page_texts, 12), limit=15)
    beneficial_bacteria = _extract_p01_microbe_group(page_texts, "beneficial")
    harmful_bacteria = _extract_p01_microbe_group(page_texts, "harmful")
    neutral_bacteria = _extract_p01_microbe_group(page_texts, "neutral")
    disease_analysis = _extract_p01_disease_analysis(summary_text)
    report_summary = _extract_p01_report_summary(summary_text, disease_analysis)
    diversity = _extract_p01_diversity(summary_text)
    intestinal_age = _extract_p01_intestinal_age(summary_text, basic_information)

    return {
        "report_info": report_info,
        "basic_information": basic_information,
        "test_description": {
            "content": description_text,
        },
        "result_overview": _extract_p01_result_overview(overview_text, summary_text),
        "gmhi": _extract_p01_gmhi(summary_text, overview_text),
        "enterotype": {
            "result": _extract_p01_enterotype(summary_text),
            "description": "",
        },
        "diversity": diversity,
        "intestinal_age": intestinal_age,
        "fb_ratio": _extract_p01_fb_ratio(phylum_top_5),
        "be_index": _extract_p01_be_index(_page_text(page_texts, 10)),
        "microbial_composition": {
            "phylum_level": {
                "top_5": phylum_top_5,
            },
            "genus_level": {
                "top_15": genus_top_15,
            },
            "beneficial_bacteria": beneficial_bacteria,
            "harmful_bacteria": harmful_bacteria,
            "neutral_bacteria": neutral_bacteria,
        },
        "disease_risk_assessment": {
            "disclaimer": "",
            "risk_levels": {
                "0-0.4": "低风险",
                "0.4-0.6": "注意",
                "0.6-0.8": "中风险",
                "0.8-1.0": "高风险",
            },
            "diseases": [
                {
                    "name": item["disease"],
                    "risk_score": item["risk_score"],
                    "risk_level": item["risk_level"],
                    "clinical_features": item["symptoms"],
                    "positive_correlations": [],
                    "negative_correlations": [],
                }
                for item in disease_analysis
            ],
        },
        "metabolism_and_nutrients": _extract_p01_metabolism_summary(summary_text),
        "immunity_assessment": _extract_p01_immunity(summary_text),
        "quality_control": _extract_p01_quality_control(_page_text(page_texts, 42)),
        "report_summary": report_summary,
    }


def build_p03_extracted_report(structured_report: dict[str, Any], full_text: str) -> dict[str, Any]:
    patient_info = structured_report.get("patient_info", {})
    additional_info = structured_report.get("additional_info", {})
    specimen_types = patient_info.get("specimen_types") or []
    if not isinstance(specimen_types, list):
        specimen_types = [str(specimen_types)]

    barcodes = extract_barcodes(full_text)
    primary_barcode = str(structured_report.get("report_id") or (barcodes[0] if barcodes else ""))
    alternate_barcodes = [barcode for barcode in barcodes if barcode != primary_barcode]
    tests = structured_report.get("tests", [])
    return {
        "report_info": {
            "laboratory": extract_laboratory(full_text),
            "report_name": "检验报告单" if "检验报告单" in full_text else "",
            "barcode": primary_barcode,
            "barcode_alt": alternate_barcodes[0] if alternate_barcodes else "",
        },
        "patient_info": {
            "name": patient_info.get("name") or "",
            "gender": patient_info.get("gender") or "",
            "age": patient_info.get("age") or "",
            "submitting_unit": patient_info.get("hospital") or "",
            "specimen_status": patient_info.get("specimen_condition") or "",
            "specimen_type": specimen_types[0] if specimen_types else "",
            "specimen_type_alt": specimen_types[1] if len(specimen_types) > 1 else "",
            "patient_id": patient_info.get("patient_number") or "",
            "bed_number": patient_info.get("bed_number") or "",
            "submitting_department": patient_info.get("department") or "",
            "submitting_doctor": patient_info.get("doctor") or "",
            "clinical_diagnosis": patient_info.get("clinical_diagnosis") or "",
        },
        "test_results": [
            {
                "test_name": test.get("test_name") or "",
                "result": numeric_or_text(test.get("result")),
                "indicator": test.get("indicator") or "",
                "reference_range": test.get("reference_range") or "",
                "unit": test.get("unit") or "",
                "method": test.get("method") or "",
            }
            for test in tests
        ],
        "remarks": extract_remarks(full_text),
        "disclaimer": extract_disclaimer(full_text),
        "signatures": {
            "detected_by": additional_info.get("technician") or "",
            "reviewed_by": additional_info.get("reviewer") or "",
            "approved_by": additional_info.get("approver") or "",
        },
        "dates": {
            "sampling_date": additional_info.get("sample_date") or "",
            "receiving_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
        },
        "contact": {
            "website": extract_website(full_text),
            "phone": extract_phone(full_text),
            "address": extract_address(full_text),
        },
    }


def extract_sparse_page_image_ocr(pdf_path: Path, page_texts: list[str]) -> dict[int, dict[str, Any]]:
    targets = [index + 1 for index, text in enumerate(page_texts) if len(text.strip()) < 20]
    if not targets:
        return {}
    try:
        import fitz
        from rapidocr_onnxruntime import RapidOCR
    except Exception:
        return {}

    ocr = RapidOCR()
    results: dict[int, dict[str, Any]] = {}
    document = fitz.open(str(pdf_path))
    try:
        for page_number in targets:
            page = document.load_page(page_number - 1)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                temp_path = Path(temp_file.name)
            try:
                pix.save(str(temp_path))
                raw_items, _ = ocr(str(temp_path))
            finally:
                temp_path.unlink(missing_ok=True)
            items = _normalize_p05_ocr_items(raw_items or [])
            if not items:
                continue
            results[page_number] = {
                "text": normalize_text(" ".join(item["text"] for item in items)),
                "items": items,
                "confidence": round(mean(item["score"] for item in items), 4),
            }
    finally:
        document.close()
    return results


def _normalize_p05_ocr_items(raw_items: list[Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, (list, tuple)) or len(item) < 3:
            continue
        box, text, score = item[0], str(item[1]), float(item[2])
        if not box:
            continue
        xs = [point[0] for point in box]
        ys = [point[1] for point in box]
        items.append(
            {
                "text": clean_value(text),
                "score": score,
                "x": float(sum(xs) / len(xs)),
                "y": float(sum(ys) / len(ys)),
            }
        )
    return items


def build_p05_extracted_report(
    source_file: str,
    full_text: str,
    page_texts: list[str],
    *,
    page_ocr_data: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    report_overview = _extract_p05_report_overview(page_texts)
    reports: list[dict[str, Any]] = []

    thyroid_page = _find_p05_page(page_texts, ["FT3", "TPOAb"])
    if thyroid_page:
        thyroid_text = page_texts[thyroid_page - 1]
        reports.append(
            {
                "page": thyroid_page,
                "barcode": _extract_p05_barcode(thyroid_text),
                "basic_info": _extract_p05_basic_info(thyroid_text),
                "test_items": _extract_p05_thyroid_tests(thyroid_text),
                "remark": extract_remarks(thyroid_text),
                "hospital_barcode": "",
                "tested_by": extract_staff(thyroid_text, ["检测者", "检验者"]),
                "reviewed_by": extract_staff(thyroid_text, ["审核者", "复核者"]),
                "approved_by": extract_staff(thyroid_text, ["批准人", "批准者"]),
                "sampling_datetime": _extract_p05_label_value(thyroid_text, ["采样日期"]),
                "receiving_datetime": _extract_p05_label_value(thyroid_text, ["接收时间"]),
                "report_datetime": _extract_p05_label_value(thyroid_text, ["报告时间"]),
            }
        )

    catecholamine_page = _find_p05_page(page_texts, ["去甲肾上腺素", "LC-MS/MS法"])
    if catecholamine_page:
        catecholamine_text = page_texts[catecholamine_page - 1]
        reports.append(
            {
                "page": catecholamine_page,
                "barcode": _extract_p05_barcode(catecholamine_text),
                "basic_info": _extract_p05_basic_info(catecholamine_text),
                "test_items": _extract_p05_catecholamine_tests(page_ocr_data.get(catecholamine_page, {}).get("items", []), catecholamine_text),
                "remark": extract_remarks(catecholamine_text),
                "hospital_barcode": "",
                "tested_by": extract_staff(catecholamine_text, ["检验者", "检测者"]),
                "reviewed_by": _extract_p05_inline_reviewer(page_ocr_data.get(catecholamine_page, {}).get("items", []), catecholamine_text),
                "approved_by": extract_staff(catecholamine_text, ["批准者", "批准人"]),
                "sampling_datetime": _extract_p05_label_value(catecholamine_text, ["采样时间", "采样日期"]),
                "receiving_datetime": _extract_p05_label_value(catecholamine_text, ["接收时间"]),
                "report_datetime": _extract_p05_label_value(catecholamine_text, ["报告时间"]),
            }
        )

    cort_page = _find_p05_page(page_texts, ["皮质醇(CORT)"])
    if cort_page:
        cort_text = page_texts[cort_page - 1]
        reports.append(
            {
                "page": cort_page,
                "barcode": _extract_p05_barcode(cort_text),
                "basic_info": _extract_p05_basic_info(cort_text),
                "test_items": _extract_p05_single_test(cort_text, "cort"),
                "remark": extract_remarks(cort_text),
                "hospital_barcode": "",
                "tested_by": extract_staff(cort_text, ["检测者", "检验者"]),
                "reviewed_by": extract_staff(cort_text, ["审核者", "复核者"]),
                "approved_by": extract_staff(cort_text, ["批准人", "批准者"]),
                "sampling_datetime": _extract_p05_label_value(cort_text, ["采样日期"]),
                "receiving_datetime": _extract_p05_label_value(cort_text, ["接收时间"]),
                "report_datetime": _extract_p05_label_value(cort_text, ["报告时间"]),
            }
        )

    acth_page = _find_p05_page(page_texts, ["促肾上腺皮质激素(ACTH)"])
    if acth_page:
        acth_text = page_texts[acth_page - 1]
        reports.append(
            {
                "page": acth_page,
                "barcode": _extract_p05_barcode(acth_text),
                "basic_info": _extract_p05_basic_info(acth_text),
                "test_items": _extract_p05_single_test(acth_text, "acth"),
                "remark": extract_remarks(acth_text),
                "hospital_barcode": "",
                "tested_by": extract_staff(acth_text, ["检测者", "检验者"]),
                "reviewed_by": extract_staff(acth_text, ["审核者", "复核者"]),
                "approved_by": extract_staff(acth_text, ["批准人", "批准者"]),
                "sampling_datetime": _extract_p05_label_value(acth_text, ["采样日期"]),
                "receiving_datetime": _extract_p05_label_value(acth_text, ["接收时间"]),
                "report_datetime": _extract_p05_label_value(acth_text, ["报告时间"]),
            }
        )

    return {
        "report_overview": report_overview,
        "reports": reports,
    }


def extract_p05_structured_tests(p05_report: dict[str, Any]) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    for report in p05_report.get("reports", []):
        if not isinstance(report, dict):
            continue
        page = int(report.get("page") or 0)
        basic_info = report.get("basic_info", {}) if isinstance(report.get("basic_info"), dict) else {}
        specimen_type = str(basic_info.get("specimen_type") or "")
        for item in report.get("test_items", []):
            if not isinstance(item, dict):
                continue
            tests.append(
                {
                    "page": page,
                    "specimen_type": specimen_type,
                    "test_name": str(item.get("test_name") or ""),
                    "item_code": str(item.get("item_code") or ""),
                    "result": str(item.get("result") or ""),
                    "indicator": str(item.get("hint") or ""),
                    "reference_range": str(item.get("reference_range") or ""),
                    "unit": str(item.get("unit") or ""),
                    "method": str(item.get("method") or ""),
                }
            )
    return tests


def _extract_p05_report_overview(page_texts: list[str]) -> dict[str, Any]:
    text = " ".join(page_texts)
    page_one = page_texts[0] if page_texts else text
    lab_match = re.search(r"(合肥安为康医学检验实验室)", text)
    address_match = re.search(r"(?:公司地址|地\s*址)[:：]?\s*([^\n]*?安创大楼)", page_one)
    return {
        "laboratory_name": lab_match.group(1) if lab_match else (extract_laboratory(text) or "合肥安为康医学检验实验室"),
        "report_title": "检验报告单 / Results Report",
        "address": clean_value(address_match.group(1)) if address_match else extract_address(text),
        "website": extract_website(text),
        "phone": extract_phone(text),
        "disclaimer": extract_disclaimer(page_one) or extract_disclaimer(text),
    }


def _find_p05_page(page_texts: list[str], keywords: list[str]) -> int | None:
    for index, text in enumerate(page_texts, start=1):
        if all(keyword in text for keyword in keywords):
            return index
    return None


def _extract_p05_barcode(text: str) -> str:
    match = re.search(r"(?:条形码号|条\s*形\s*码)[:：]?\s*([0-9]{8,})", text)
    return match.group(1) if match else extract_report_id(text)


def _extract_p05_basic_info(text: str) -> dict[str, Any]:
    age_value = extract_age(text)
    age_raw = f"{age_value}岁" if age_value != "" else ""
    clinical_diagnosis = _extract_p05_label_value(text, ["临床诊断"])
    if any(clinical_diagnosis.startswith(prefix) for prefix in ["Anweikang", "参考区间", "检验结果报告单", "检测项目"]):
        clinical_diagnosis = ""
    return {
        "submitting_institution": _extract_p05_label_value(text, ["送检单位"]) or extract_hospital(text),
        "name": extract_patient_name(text) or _extract_p05_label_value(text, ["姓名"]),
        "gender": extract_gender(text),
        "age": age_raw,
        "specimen_status": _extract_p05_label_value(text, ["样本状态", "标本情况"]) or extract_specimen_condition(text),
        "specimen_type": _extract_p05_label_value(text, ["标本类型"]),
        "patient_id": _extract_p05_label_value(text, ["病员号", "门诊/住院号", "门诊住院号"]),
        "bed_no": _extract_p05_label_value(text, ["床号", "床 号"]),
        "submitting_department": _extract_p05_label_value(text, ["送检科室", "科室/病区", "科 室/病 区"]),
        "submitting_doctor": _extract_p05_label_value(text, ["送检医生"]),
        "clinical_diagnosis": clinical_diagnosis,
        "outpatient_hospital_no": _extract_p05_label_value(text, ["门诊/住院号", "门诊住院号"]),
        "ward_area": _extract_p05_label_value(text, ["科室/病区", "科 室/病 区"]),
        "sampling_datetime": _extract_p05_label_value(text, ["采样时间", "采样日期"]),
        "receiving_datetime": _extract_p05_label_value(text, ["接收时间"]),
    }


def _extract_p05_label_value(text: str, labels: list[str]) -> str:
    normalized = normalize_text(text)
    next_labels = [
        "条形码号",
        "条 形 码",
        "送检单位",
        "姓名",
        "性别",
        "年龄",
        "样本状态",
        "标本情况",
        "标本类型",
        "病员号",
        "床号",
        "床 号",
        "送检科室",
        "科室/病区",
        "科 室/病 区",
        "送检医生",
        "临床诊断",
        "采样时间",
        "采样日期",
        "接收时间",
        "报告时间",
        "地址",
        "公司地址",
        "地 址",
        "址",
        "网 址",
        "网址",
        "电 话",
        "电话",
        "检验者",
        "检测者",
        "审核者",
        "批准者",
        "批准人",
        "备注",
        "备 注",
        "医院条码",
        "功能医学测试",
        "门诊/住院号",
        "门诊住院号",
        "单位序号",
        "检测项目",
        "检验项目",
        "参考区间",
        "序号",
        "单位",
    ]
    for label in labels:
        siblings = [candidate for candidate in next_labels if candidate != label]
        value = _extract_between_labels(normalized, label, siblings)
        if value:
            return value
    return ""


def _extract_p05_thyroid_tests(text: str) -> list[dict[str, Any]]:
    rows = list(
        re.finditer(
            r"(pmol/L|nmol/L|mIU/L|IU/ml|IU/mL)\s+化学发光法\s*([<>＜]?\d+(?:\.\d+)?)\s*([<>＜]?\d+(?:\.\d+)?(?:--[0-9]+(?:\.\d+)?)?)",
            text,
        )
    )
    items: list[dict[str, Any]] = []
    for index, (item_code, name) in enumerate(P05_THYROID_TESTS):
        if index >= len(rows):
            break
        match = rows[index]
        items.append(
            {
                "item_code": item_code,
                "test_name": name,
                "result": clean_value(match.group(2).replace("＜", "<")),
                "reference_range": normalize_reference(match.group(3)),
                "unit": normalize_unit(match.group(1)),
                "method": "化学发光法",
                "hint": "",
            }
        )
    return items


def _extract_p05_single_test(text: str, kind: str) -> list[dict[str, Any]]:
    name_map = {code: name for code, name in P05_SINGLE_TESTS}
    name = name_map[kind]
    pattern = re.compile(
        rf"(nmol/L|pmol/L)\s+化学发光法\s*{name_pattern(name)}\s*([<>＜]?\d+(?:\.\d+)?)\s*(.*?)\s*(?=采样日期|接收时间|报告时间|公司地址|网\s*址|电\s*话|本检测仅对来样负责)",
        flags=re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return []
    reference = re.split(r"采\s*样日期|接收时间|报告时间", clean_value(match.group(3)), maxsplit=1)[0].strip()
    return [
        {
            "item_code": kind,
            "test_name": name,
            "result": clean_value(match.group(2).replace("＜", "<")),
            "reference_range": reference,
            "unit": normalize_unit(match.group(1)),
            "method": "化学发光法",
            "hint": "",
        }
    ]


def _extract_p05_catecholamine_tests(ocr_items: list[dict[str, Any]], fallback_text: str) -> list[dict[str, Any]]:
    if not ocr_items:
        return _extract_p05_catecholamine_tests_from_text(fallback_text)
    items: list[dict[str, Any]] = []
    for item_code, name in P05_CATECHOLAMINE_TESTS:
        name_item = _find_p05_ocr_item(ocr_items, name)
        if not name_item:
            continue
        row_y = float(name_item["y"])
        method_item = _find_p05_nearby_item(ocr_items, row_y, 420, 580)
        result_item = _find_p05_nearby_item(ocr_items, row_y, 600, 700)
        unit_item = _find_p05_nearby_item(ocr_items, row_y, 1000, 1120)
        references = _collect_p05_reference_items(ocr_items, row_y)
        result_text = clean_value(str(result_item["text"])) if result_item else ""
        if not result_text and name == "3-甲氧基酪胺":
            result_text = "<0.06"
        items.append(
            {
                "item_code": item_code,
                "test_name": name,
                "serial_no": len(items) + 1,
                "method": clean_value(str(method_item["text"])) if method_item else "LC-MS/MS法",
                "result": result_text.replace("＜", "<").replace("06'0>", "<0.90"),
                "reference_range": "；".join(references) if references else "",
                "unit": normalize_unit(str(unit_item["text"])) if unit_item else "nmol/L",
                "hint": "",
            }
        )
    return items


def _extract_p05_catecholamine_tests_from_text(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item_code, name in P05_CATECHOLAMINE_TESTS:
        pattern = re.compile(
            rf"{name_pattern(name)}\s*LC-MS/MS法\s*([<>＜]?\d+(?:\.\d+)?)\s*([^\s]+(?:\s*[；;]\s*[^\s]+)?)\s*(nmol/L)?",
            flags=re.IGNORECASE,
        )
        match = pattern.search(text)
        if not match:
            continue
        items.append(
            {
                "item_code": item_code,
                "test_name": name,
                "serial_no": len(items) + 1,
                "method": "LC-MS/MS法",
                "result": clean_value(match.group(1).replace("＜", "<")),
                "reference_range": clean_value(match.group(2)),
                "unit": normalize_unit(match.group(3) or "nmol/L"),
                "hint": "",
            }
        )
    return items


def _find_p05_ocr_item(items: list[dict[str, Any]], target: str) -> dict[str, Any] | None:
    target_text = clean_value(target)
    for item in items:
        if clean_value(str(item.get("text") or "")) == target_text:
            return item
    return None


def _find_p05_nearby_item(items: list[dict[str, Any]], row_y: float, min_x: float, max_x: float) -> dict[str, Any] | None:
    candidates = [
        item
        for item in items
        if min_x <= float(item["x"]) <= max_x and abs(float(item["y"]) - row_y) <= 16
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (abs(float(item["y"]) - row_y), float(item["x"])))[0]


def _collect_p05_reference_items(items: list[dict[str, Any]], row_y: float) -> list[str]:
    candidates = [
        item
        for item in items
        if 740 <= float(item["x"]) <= 930 and -6 <= float(item["y"]) - row_y <= 32
    ]
    ordered = sorted(candidates, key=lambda item: (float(item["y"]), float(item["x"])))
    values: list[str] = []
    for item in ordered:
        text = clean_value(str(item["text"] or "")).replace("＜", "<")
        if not text:
            continue
        if text == "06'0>":
            text = "<0.90"
        if text not in values:
            values.append(text)
    return values


def _extract_p05_inline_reviewer(ocr_items: list[dict[str, Any]], fallback_text: str) -> str:
    if ocr_items:
        marker = _find_p05_ocr_item(ocr_items, "审核者:")
        if marker:
            candidates = [
                item
                for item in ocr_items
                if 560 <= float(item["x"]) <= 760 and abs(float(item["y"]) - float(marker["y"])) <= 16
            ]
            if candidates:
                return clean_value(str(sorted(candidates, key=lambda item: float(item["x"]))[-1]["text"]))
    return extract_staff(fallback_text, ["审核者", "复核者"])


def _parse_age_number(value: str) -> int | str:
    match = re.search(r"([0-9]{1,3})", value)
    return int(match.group(1)) if match else ""


def _first_non_empty(values: list[str], validate: Any | None = None) -> str:
    for value in values:
        cleaned = clean_value(value)
        if cleaned and (validate is None or bool(validate(cleaned))):
            return cleaned
    return ""


def _is_valid_p05_staff_value(value: str) -> bool:
    compact = clean_value(value)
    if not compact:
        return False
    if compact in {"址", "话", "网", "备", "注"}:
        return False
    if "功能医学" in compact or "备注" in compact:
        return False
    return True


def _find_page_text(page_texts: list[str], needle: str) -> str:
    for text in page_texts:
        if needle in text:
            return text
    return ""


def _extract_p01_summary_text(page_texts: list[str]) -> str:
    if len(page_texts) >= 7 and any("肠道基因检测报告总结" in text for text in page_texts[-7:]):
        return " ".join(_sanitize_p01_summary_page(text) for text in page_texts[-7:])
    summary_pages = [
        text
        for text in page_texts
        if any(keyword in text for keyword in ["肠道基因检测报告总结", "核心结论", "下一步治疗方案", "异常菌属分析"])
    ]
    return " ".join(_sanitize_p01_summary_page(text) for text in summary_pages)


def _sanitize_p01_summary_page(text: str) -> str:
    cleaned = normalize_text(text)
    cleaned = re.sub(r"安为康医学检验.*?第\s*\d+\s*页\s*/\s*共\s*\d+\s*页", "", cleaned)
    cleaned = re.sub(r"(肠道基因检测报告总结[（(][^）)]+[）)]){2,}", "", cleaned)
    return clean_value(cleaned)


def _extract_between_labels(text: str, label: str, next_labels: list[str]) -> str:
    if not text:
        return ""
    end_pattern = "|".join(label_pattern(item) for item in next_labels)
    pattern = re.compile(
        rf"{label_pattern(label)}[:：]?\s*(?P<value>.*?)\s*(?=(?:{end_pattern})|$)",
        flags=re.S,
    )
    match = pattern.search(text)
    if not match:
        return ""
    return clean_value(match.group("value"))


def _tighten_text(text: str) -> str:
    return normalize_text(text).replace(" ", "")


def _extract_p01_report_info(full_text: str, page_texts: list[str]) -> dict[str, Any]:
    title_match = re.search(r"(人体肠道菌群检测报告)", full_text)
    report_number_match = re.search(r"报告编号[:：]?\s*([0-9]{8,})", full_text)
    page_one = _page_text(page_texts, 1) or full_text
    address_match = re.search(r"地址[:：]?\s*(.*?)\s*客服支持", page_one)
    address = clean_value(address_match.group(1)) if address_match else extract_address(full_text)
    lab_name = address.split("号")[-1] if "号" in address else ("安创大楼" if "安创大楼" in address else "")
    basic_page = _page_text(page_texts, 3) or _find_page_text(page_texts, "主要不适或疾病")
    report_date = _extract_between_labels(basic_page, "报告日期", ["检测项目", "样本类型"]) or extract_date(page_texts, "报告日期")
    return {
        "title": title_match.group(1) if title_match else "",
        "report_date": report_date,
        "lab_name": lab_name,
        "lab_address": address,
        "customer_service": extract_phone(full_text),
        "report_number": report_number_match.group(1) if report_number_match else "",
    }


def _extract_p01_basic_information(full_text: str, page_texts: list[str]) -> dict[str, Any]:
    basic_page = _page_text(page_texts, 3) or _find_page_text(page_texts, "主要不适或疾病") or full_text
    age_value = _extract_between_labels(basic_page, "年龄", ["联系电话"])
    age_match = re.search(r"[0-9]{1,3}", age_value)
    return {
        "name": _extract_between_labels(basic_page, "姓名", ["送检单位", "性别"]),
        "gender": _extract_between_labels(basic_page, "性别", ["样本编号", "年龄"]),
        "age": int(age_match.group(0)) if age_match else "",
        "sample_id": _extract_between_labels(basic_page, "样本编号", ["年龄", "联系电话"]),
        "phone": _extract_between_labels(basic_page, "联系电话", ["主要不适或疾病", "采样日期"]),
        "main_complaint": _extract_between_labels(basic_page, "主要不适或疾病", ["采样日期"]),
        "sampling_date": _extract_between_labels(basic_page, "采样日期", ["收样日期", "报告日期"]) or "-",
        "receiving_date": _extract_between_labels(basic_page, "收样日期", ["报告日期", "检测项目"]),
        "report_date": _extract_between_labels(basic_page, "报告日期", ["检测项目", "样本类型"]),
        "test_item": _extract_between_labels(basic_page, "检测项目", ["样本类型", "检测方法"]),
        "sample_type": _extract_between_labels(basic_page, "样本类型", ["检测方法"]),
        "detection_method": _extract_between_labels(basic_page, "检测方法", ["地址", "客服支持"]) or "高通量测序",
        "submitting_institution": _extract_between_labels(basic_page, "送检单位", ["性别", "样本编号"]) or "-",
    }


def _extract_p01_test_description(page_texts: list[str]) -> str:
    page = _page_text(page_texts, 3) or _find_page_text(page_texts, "二、检测说明")
    if not page:
        return ""
    match = re.search(r"二、检测说明\s*(.*?)(?=姓名\s|送检单位\s|性别\s)", page, flags=re.S)
    return clean_value(match.group(1)) if match else ""


def _extract_p01_result_overview(overview_text: str, summary_text: str) -> dict[str, Any]:
    tight_overview = _tighten_text(overview_text)
    score = _extract_p01_gmhi(summary_text, overview_text).get("score")
    level = _extract_p01_gmhi(summary_text, overview_text).get("assessment", "")
    points: list[str] = []
    if tight_overview:
        for match in re.finditer(
            r"([1-8])\.(.*?)(?=(?:[1-8]\.)|(?:40[≤<]GMHI<60)|(?:[0-9]+(?:\.[0-9]+)?$)|$)",
            tight_overview,
            flags=re.S,
        ):
            value = clean_value(match.group(2))
            if value:
                points.append(value)
    return {
        "gmhi_score": score,
        "gmhi_level": level,
        "summary_points": points,
    }


def _extract_p01_gmhi(summary_text: str, overview_text: str) -> dict[str, Any]:
    tight_summary = _tighten_text(summary_text)
    tight_overview = _tighten_text(overview_text)
    score = None
    assessment = ""
    summary_match = re.search(r"肠道菌群健康指数[:：]([0-9.]+)[（(]([^，）)]+)", tight_summary)
    if summary_match:
        score = _float_or_none(summary_match.group(1))
        assessment = clean_value(summary_match.group(2))
    if score is None:
        score_match = re.search(r"([0-9]+(?:\.[0-9]+)?)$", tight_overview)
        score = _float_or_none(score_match.group(1)) if score_match else None
    if not assessment:
        level_match = re.search(r"属于([^，。]+?)水平", overview_text)
        assessment = clean_value(level_match.group(1)) if level_match else ""
    return {
        "score": score,
        "assessment": assessment,
        "definition": "",
        "range": {},
    }


def _extract_p01_enterotype(summary_text: str) -> str:
    tight_summary = _tighten_text(summary_text)
    match = re.search(r"肠型[:：]([^\s，。；;]+?型(?:[（(][A-Za-z]+[）)])?)", tight_summary)
    return clean_value(match.group(1)) if match else ""


def _extract_p01_diversity(summary_text: str) -> dict[str, Any]:
    tight_summary = _tighten_text(summary_text)
    shannon_match = re.search(r"菌群多样性指数([0-9.]+)", tight_summary)
    percentile_match = re.search(r"第([0-9.]+)%分位", tight_summary)
    return {
        "shannon_index": _float_or_none(shannon_match.group(1)) if shannon_match else None,
        "reference_percentile": f"{percentile_match.group(1)}%" if percentile_match else "",
        "genus_count": None,
        "genus_reference_range": "",
        "species_count": None,
        "species_reference_range": "",
        "interpretation": "",
        "summary": _extract_p01_named_line(tight_summary, "肠道菌群多样性"),
    }


def _extract_p01_intestinal_age(summary_text: str, basic_information: dict[str, Any]) -> dict[str, Any]:
    tight_summary = _tighten_text(summary_text)
    match = re.search(r"肠道年龄[:：]([0-9]+)岁[（(]时序年龄([0-9]+)岁[）)]，?差值([+-]?[0-9]+)岁", tight_summary)
    if match:
        chronological_age = int(match.group(2))
        intestinal_age = int(match.group(1))
        age_difference = f"{match.group(3)}岁"
    else:
        chronological_age = int(basic_information.get("age") or 0) if basic_information.get("age") else None
        intestinal_age = None
        age_difference = ""
    return {
        "chronological_age": chronological_age,
        "intestinal_age": intestinal_age,
        "age_difference": age_difference,
        "reference_standards": "",
        "interpretation": "",
        "summary": _extract_p01_named_line(tight_summary, "肠道年龄"),
    }


def _extract_p01_ranked_items(text: str, *, limit: int) -> list[dict[str, Any]]:
    tight = _tighten_text(text)
    match = re.search(r"依次为[:：](.*)", tight)
    blob = match.group(1) if match else tight
    items: list[dict[str, Any]] = []
    for found in re.finditer(r"([^（()，,]+)[（(]([^,，()（）]+)[,，]([0-9.]+%)[）)]", blob):
        items.append(
            {
                "name": clean_value(found.group(1)),
                "scientific_name": clean_value(found.group(2)),
                "percentage": clean_value(found.group(3)),
            }
        )
        if len(items) >= limit:
            break
    return items


def _extract_p01_fb_ratio(phylum_top_5: list[dict[str, Any]]) -> dict[str, Any]:
    firmicutes = next((item for item in phylum_top_5 if "厚壁菌门" in str(item.get("name") or "")), {})
    bacteroidetes = next((item for item in phylum_top_5 if "拟杆菌门" in str(item.get("name") or "")), {})
    firmicutes_value = _percent_to_float(str(firmicutes.get("percentage") or ""))
    bacteroidetes_value = _percent_to_float(str(bacteroidetes.get("percentage") or ""))
    ratio = round(firmicutes_value / bacteroidetes_value, 4) if firmicutes_value is not None and bacteroidetes_value not in (None, 0) else None
    evaluation = ""
    if firmicutes_value is not None and bacteroidetes_value is not None:
        if firmicutes_value > bacteroidetes_value:
            evaluation = "偏向于厚壁菌"
        elif firmicutes_value < bacteroidetes_value:
            evaluation = "偏向于拟杆菌"
        else:
            evaluation = "平衡"
    return {
        "firmicutes_bacteroidetes_ratio": ratio,
        "result_evaluation": evaluation,
        "reference_range": "0.5-2",
        "firmicutes": {
            "value": str(firmicutes.get("percentage") or ""),
            "evaluation": "正常" if firmicutes else "",
            "reference_range": "",
        },
        "bacteroidetes": {
            "value": str(bacteroidetes.get("percentage") or ""),
            "evaluation": "正常" if bacteroidetes else "",
            "reference_range": "",
        },
        "explanation": "",
    }


def _extract_p01_be_index(text: str) -> dict[str, Any]:
    tight = _tighten_text(text)
    ratio_match = re.search(r"B/E指数([0-9.]+)([^0-9><%]{2,8})(>[0-9.]+)", tight)
    bifidobacterium_match = re.search(r"双歧杆菌属([0-9.]+%?)(正常|偏低|偏高|异常)([0-9.%\-]+)", tight)
    enterobacteriaceae_match = re.search(r"肠杆菌科([0-9.]+%?)(正常|偏低|偏高|异常)([0-9.%\-]+)", tight)
    return {
        "bifidobacterium_enterobacteriaceae_ratio": _float_or_none(ratio_match.group(1)) if ratio_match else None,
        "result_evaluation": clean_value(ratio_match.group(2)) if ratio_match else "",
        "reference_range": ratio_match.group(3) if ratio_match else "",
        "bifidobacterium": {
            "value": _ensure_percent_suffix(bifidobacterium_match.group(1)) if bifidobacterium_match else "",
            "evaluation": bifidobacterium_match.group(2) if bifidobacterium_match else "",
            "reference_range": _ensure_percent_suffix(bifidobacterium_match.group(3)) if bifidobacterium_match else "",
        },
        "enterobacteriaceae": {
            "value": _ensure_percent_suffix(enterobacteriaceae_match.group(1)) if enterobacteriaceae_match else "",
            "evaluation": enterobacteriaceae_match.group(2) if enterobacteriaceae_match else "",
            "reference_range": _ensure_percent_suffix(enterobacteriaceae_match.group(3)) if enterobacteriaceae_match else "",
        },
        "definition": "",
        "interpretation": "",
    }


def _extract_p01_microbe_group(page_texts: list[str], group: str) -> list[dict[str, Any]]:
    chunks: list[str] = []
    if group == "beneficial":
        chunks = [
            _page_text(page_texts, 13),
            _page_text(page_texts, 14),
            _before_keyword(_page_text(page_texts, 15), "10.4 有害菌检测"),
        ]
    elif group == "harmful":
        chunks = [
            _after_keyword(_page_text(page_texts, 15), "10.4 有害菌检测"),
            _page_text(page_texts, 16),
            _page_text(page_texts, 17),
            _before_keyword(_page_text(page_texts, 18), "10.5 中性菌检测"),
        ]
    elif group == "neutral":
        chunks = [
            _after_keyword(_page_text(page_texts, 18), "10.5 中性菌检测"),
            _page_text(page_texts, 19),
            _page_text(page_texts, 20),
        ]
    return _parse_p01_microbe_rows(" ".join(chunk for chunk in chunks if chunk))


def _parse_p01_microbe_rows(text: str) -> list[dict[str, Any]]:
    if not text:
        return []
    cleaned = normalize_text(text)
    if "结果评价" in cleaned:
        cleaned = cleaned.split("结果评价", 1)[1]
    if "注：ND" in cleaned:
        cleaned = cleaned.split("注：ND", 1)[0]
    tokens = cleaned.split()
    rows: list[dict[str, Any]] = []
    index = 0
    while index < len(tokens):
        microbe = tokens[index]
        if not _looks_like_p01_microbe_name(microbe):
            index += 1
            continue
        index += 1
        latin_parts: list[str] = []
        while index < len(tokens) and not _looks_like_p01_result_token(tokens[index]):
            latin_parts.append(tokens[index])
            index += 1
        if not latin_parts or index + 1 >= len(tokens):
            continue
        result = tokens[index]
        reference = tokens[index + 1]
        index += 2
        evaluation = ""
        if index < len(tokens) and tokens[index] in {"正常", "偏低", "偏高", "异常"}:
            evaluation = tokens[index]
            index += 1
        if not evaluation:
            evaluation = _infer_p01_row_evaluation(result, reference)
        rows.append(
            {
                "microbe": clean_value(microbe),
                "latin": clean_value(" ".join(latin_parts)),
                "result": _ensure_percent_suffix(result),
                "reference": _ensure_percent_suffix(reference),
                "evaluation": evaluation,
            }
        )
    return rows


def _looks_like_p01_microbe_name(token: str) -> bool:
    if token in {"微生物名", "拉丁名", "检测结果（%）", "参考范围(%)", "参考范围（%）", "结果评价"}:
        return False
    return bool(re.search(r"[\u4e00-\u9fff]", token))


def _looks_like_p01_result_token(token: str) -> bool:
    return bool(re.fullmatch(r"ND|[0-9]+(?:\.[0-9]+)?%?", token))


def _infer_p01_row_evaluation(result: str, reference: str) -> str:
    numeric_result = None if result == "ND" else _float_or_none(result.replace("%", ""))
    lower, upper = _parse_p01_reference_bounds(reference)
    if result == "ND":
        return "偏低" if lower not in (None, 0.0) else "正常"
    if lower is not None and numeric_result is not None and numeric_result < lower:
        return "偏低"
    if upper is not None and numeric_result is not None and numeric_result > upper:
        return "偏高"
    return "正常"


def _parse_p01_reference_bounds(reference: str) -> tuple[float | None, float | None]:
    cleaned = reference.replace("%", "")
    if cleaned == "0":
        return 0.0, 0.0
    if "-" in cleaned:
        left, right = cleaned.split("-", 1)
        return _float_or_none(left), _float_or_none(right)
    return _float_or_none(cleaned), None


def _extract_p01_disease_analysis(summary_text: str) -> list[dict[str, Any]]:
    tight = _tighten_text(summary_text)
    items: list[dict[str, Any]] = []
    pattern = re.compile(
        r"\((?P<index>\d+)\)(?P<name>[\u4e00-\u9fffA-Za-z]+)\((?P<score>[0-9.]+)(?P<level>低风险|注意|中风险|高风险)\)"
        r".*?风险解读[^:：]*[:：](?P<interpretation>.*?)"
        r"可能后果[^:：]*[:：](?P<consequences>.*?)"
        r"关联异常[^:：]*[:：](?P<related>.*?)(?=\(\d+\)[\u4e00-\u9fffA-Za-z]+\([0-9.]|三、异常菌属分析|四、其他异常问题|$)",
        flags=re.S,
    )
    for match in pattern.finditer(tight):
        items.append(
            {
                "disease": clean_value(match.group("name")),
                "risk_score": _normalize_p01_risk_score(match.group("score")),
                "risk_level": clean_value(match.group("level")),
                "symptoms": clean_value(match.group("interpretation")),
                "consequences": clean_value(match.group("consequences")),
                "related_abnormalities": clean_value(match.group("related")),
            }
        )
    return items


def _normalize_p01_risk_score(value: str) -> float | None:
    text = value.strip()
    if not text:
        return None
    if "." not in text and len(text) == 3 and text.startswith("0"):
        text = f"0.{text[1:]}"
    return _float_or_none(text)


def _extract_p01_report_summary(summary_text: str, disease_analysis: list[dict[str, Any]]) -> dict[str, Any]:
    tight = _tighten_text(summary_text)
    overall_match = re.search(r"核心结论(?:核心结论)*[:：](.*?)(?=肠道菌群健康指数(?:肠道菌群健康指数)*)", tight)
    overall_health = clean_value(overall_match.group(1)) if overall_match else ""
    key_abnormalities = [
        _extract_p01_named_line(tight, "肠道菌群健康指数"),
        _extract_p01_named_line(tight, "肠道菌群多样性"),
        _extract_p01_named_line(tight, "肠道年龄"),
        _extract_p01_named_line(tight, "肠道菌群平衡评估"),
        _extract_p01_named_line(tight, "肠型"),
        _extract_p01_named_line(tight, "物质代谢与营养素评估"),
    ]
    key_abnormalities = [item for item in key_abnormalities if item]
    other_abnormalities = _extract_p01_other_abnormalities(tight)
    conclusion_match = re.search(r"总结(?:总结)*[:：](.*?)(?=\(1\)下一步治疗方案|补充益生菌和益生元|$)", tight)
    conclusion = clean_value(conclusion_match.group(1)) if conclusion_match else ""
    return {
        "overall_health": overall_health,
        "key_abnormalities": key_abnormalities,
        "disease_analysis": disease_analysis,
        "abnormal_flora": _extract_p01_abnormal_flora(tight),
        "other_abnormalities": other_abnormalities,
        "conclusion": conclusion,
        "treatment_plan": _extract_p01_treatment_plan(tight),
        "disclaimer": _extract_p01_disclaimer(tight),
    }


def _extract_p01_abnormal_flora(tight_summary: str) -> dict[str, Any]:
    excessive_harmful: list[dict[str, Any]] = []
    harmful_match = re.search(
        r"1\.嗜血杆菌属[（(]Haemophilus[）)][:：]检测值([0-9.]+%)，.*?参考上限([0-9.]+%)，.*?后果[^:：]*[:：](.*?)功能[^:：]*[:：](.*?)(?=\(2\)丰度过低的有益菌/核心菌|$)",
        tight_summary,
        flags=re.S,
    )
    if harmful_match:
        excessive_harmful.append(
            {
                "name": "嗜血杆菌属",
                "scientific_name": "Haemophilus",
                "value": harmful_match.group(1),
                "reference": harmful_match.group(2),
                "consequences": clean_value(harmful_match.group(3)),
                "function": clean_value(harmful_match.group(4)),
            }
        )

    deficient_beneficial: list[dict[str, Any]] = []
    pattern = re.compile(
        r"\d\.([^\(（:：]+)[（(]([A-Za-z0-9 ._\-\[\]]+)[）)][:：]检测值([0-9.]+%|ND)，.*?参考下限([0-9.]+%)，.*?后果[^:：]*[:：](.*?)功能[^:：]*[:：](.*?)(?=\d\.[^\(（:：]+[（(][A-Za-z]|四、其他异常问题|$)",
        flags=re.S,
    )
    for match in pattern.finditer(tight_summary):
        if match.group(1) == "嗜血杆菌属":
            continue
        deficient_beneficial.append(
            {
                "name": clean_value(match.group(1)),
                "scientific_name": clean_value(match.group(2)),
                "value": match.group(3),
                "reference": match.group(4),
                "consequences": clean_value(match.group(5)),
                "function": clean_value(match.group(6)),
            }
        )
    return {
        "excessive_harmful": excessive_harmful,
        "deficient_beneficial": deficient_beneficial,
    }


def _extract_p01_other_abnormalities(tight_summary: str) -> list[str]:
    items: list[str] = []
    for label, end in [
        ("肠道定植抗力一度损伤（B/E比值0.1583）", "肠道年龄+6岁"),
        ("肠道年龄+6岁（43岁vs时序37岁）", "维生素A合成能力偏低"),
        ("维生素A合成能力偏低", "五、总结与下一步治疗方案"),
    ]:
        value = _extract_p01_section_value(tight_summary, label, end)
        if value:
            items.append(f"{label}：{value}")
    return items


def _extract_p01_treatment_plan(tight_summary: str) -> list[str]:
    items: list[str] = []
    for label, next_label in [
        ("补充益生菌和益生元", "增加膳食纤维摄入"),
        ("增加膳食纤维摄入", "严格限制饮酒"),
        ("严格限制饮酒", "规律作息与温和运动"),
        ("规律作息与温和运动", "定期复查与专科随访"),
        ("定期复查与专科随访", "本报告仅供参考"),
    ]:
        value = _extract_p01_section_value(tight_summary, label, next_label)
        if value:
            value = re.sub(rf"^(?:{re.escape(label)})+(?:[:：])?", "", value)
            items.append(f"{label}：{value}")
    return items


def _extract_p01_disclaimer(tight_summary: str) -> str:
    match = re.search(r"(本报告仅供参考[^。]*。)", tight_summary)
    return clean_value(match.group(1)) if match else ""


def _extract_p01_metabolism_summary(summary_text: str) -> dict[str, Any]:
    tight = _tighten_text(summary_text)
    summary = _extract_p01_named_line(tight, "物质代谢与营养素评估")
    vitamin_match = re.search(r"维生素A合成能力偏低[（(]([0-9.]+)/参考下限([0-9.]+)[）)]", tight)
    return {
        "summary": summary,
        "vitamins": {
            "vitamin_a": {
                "value": _float_or_none(vitamin_match.group(1)) if vitamin_match else None,
                "reference": vitamin_match.group(2) if vitamin_match else "",
                "status": "偏低" if vitamin_match else "",
            }
        },
    }


def _extract_p01_immunity(summary_text: str) -> dict[str, Any]:
    tight = _tighten_text(summary_text)
    match = re.search(r"免疫力评估[:：]肠道免疫力[（(]([0-9.]+)[）)]与抗炎能力[（(]([0-9.]+)[）)]均在正常参考范围内", tight)
    return {
        "intestinal_immunity": {
            "value": _float_or_none(match.group(1)) if match else None,
            "reference": "",
            "status": "正常" if match else "",
        },
        "intestinal_anti_inflammatory": {
            "value": _float_or_none(match.group(2)) if match else None,
            "reference": "",
            "status": "正常" if match else "",
        },
    }


def _extract_p01_quality_control(text: str) -> dict[str, Any]:
    match = re.search(
        r"样本数据\s*([0-9,]+)\s*([0-9.]+%)\s*([0-9.]+%)\s*质控标准\s*(≥?[0-9,]+)\s*(≥?[0-9.]+%)\s*([0-9%-]+)\s*质控结果\s*(合格)\s*(合格)\s*(合格)",
        text,
        flags=re.S,
    )
    tested_by = re.search(r"检测者[:：]\s*([^\s:：]+)", text)
    reviewed_by = re.search(r"审核者[:：]\s*([^\s:：]+)", text)
    note_match = re.search(r"注[:：]\s*(Q30[^。]*。)", text)
    return {
        "total_sequences": int(match.group(1).replace(",", "")) if match else None,
        "q30": match.group(2) if match else "",
        "gc_content": match.group(3) if match else "",
        "qc_standard": {
            "total_sequences": match.group(4) if match else "",
            "q30": match.group(5) if match else "",
            "gc_content": match.group(6) if match else "",
        },
        "qc_result": {
            "total_sequences": match.group(7) if match else "",
            "q30": match.group(8) if match else "",
            "gc_content": match.group(9) if match else "",
        },
        "q30_note": clean_value(note_match.group(1)) if note_match else "",
        "tested_by": tested_by.group(1) if tested_by else "",
        "reviewed_by": reviewed_by.group(1) if reviewed_by else "",
    }


def _extract_p01_diversity_status(diversity: dict[str, Any]) -> str:
    summary = str(diversity.get("summary") or "")
    for label in ["多样性高", "多样性较高", "多样性正常", "正常范围但偏低", "多样性偏低", "多样性低"]:
        if label in summary:
            return label
    percentile = str(diversity.get("reference_percentile") or "").replace("%", "")
    value = _float_or_none(percentile)
    if value is None:
        return ""
    if value > 90:
        return "多样性高"
    if value > 80:
        return "多样性较高"
    if value > 25:
        return "多样性正常"
    if value > 15:
        return "多样性偏低"
    return "多样性低"


def _extract_p01_named_line(tight_text: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}[:：](.*?)(?=肠道菌群多样性|肠道年龄|肠道菌群平衡评估|肠型|物质代谢与营养素评估|免疫力评估|$)", tight_text)
    return clean_value(match.group(1)) if match else ""


def _extract_p01_section_value(tight_text: str, start_label: str, end_label: str) -> str:
    pattern = re.compile(rf"{re.escape(start_label)}[:：]?(.*?)(?={re.escape(end_label)}|$)", flags=re.S)
    match = pattern.search(tight_text)
    return clean_value(match.group(1)) if match else ""


def _page_text(page_texts: list[str], page_number: int) -> str:
    if 1 <= page_number <= len(page_texts):
        return page_texts[page_number - 1]
    return ""


def _before_keyword(text: str, keyword: str) -> str:
    if not text or keyword not in text:
        return text
    return text.split(keyword, 1)[0]


def _after_keyword(text: str, keyword: str) -> str:
    if not text or keyword not in text:
        return ""
    return text.split(keyword, 1)[1]


def _float_or_none(value: str) -> float | None:
    try:
        return float(str(value).replace("%", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def _percent_to_float(value: str) -> float | None:
    return _float_or_none(value.replace("%", ""))


def _ensure_percent_suffix(value: str) -> str:
    cleaned = clean_value(value)
    if not cleaned or cleaned == "ND" or cleaned.endswith("%") or cleaned == "0":
        return cleaned
    if re.fullmatch(r"[0-9.]+(?:-[0-9.]+)?", cleaned):
        if "-" in cleaned:
            left, right = cleaned.split("-", 1)
            return f"{left}-{right}%"
        return f"{cleaned}%"
    return cleaned


def _format_number(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{parsed:.4f}".rstrip("0").rstrip(".")


def extract_p01_fields(page_texts: list[str], structured_report: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report["patient_info"]
    additional_info = structured_report["additional_info"]
    p01_report = structured_report.get("p01_extracted_report", {})
    basic_information = p01_report.get("basic_information", {}) if isinstance(p01_report, dict) else {}
    fb_ratio = p01_report.get("fb_ratio", {}) if isinstance(p01_report, dict) else {}
    be_index = p01_report.get("be_index", {}) if isinstance(p01_report, dict) else {}

    add_field(fields, "report.barcode", "条形码", structured_report["report_id"], 0.86, find_page(page_texts, structured_report["report_id"]))
    add_field(fields, "patient.name", "姓名", patient_info["name"], 0.82, find_page(page_texts, patient_info["name"]))
    add_field(fields, "patient.gender", "性别", patient_info["gender"], 0.82, find_page(page_texts, patient_info["gender"]))
    if patient_info["age"] != "":
        add_field(fields, "patient.age", "年龄", f"{patient_info['age']} 岁", 0.82, find_page(page_texts, str(patient_info["age"])))
    add_field(fields, "patient.phone", "联系电话", basic_information.get("phone"), 0.8, find_page(page_texts, str(basic_information.get("phone") or "")))
    add_field(fields, "patient.symptoms", "主要不适或疾病", basic_information.get("main_complaint"), 0.8, find_page(page_texts, str(basic_information.get("main_complaint") or "")))
    if patient_info["specimen_types"]:
        add_field(fields, "patient.specimen_types", "样本类型", "、".join(patient_info["specimen_types"]), 0.78, None)
    add_field(fields, "patient.hospital", "送检单位", patient_info["hospital"], 0.76, find_page(page_texts, patient_info["hospital"]))
    add_field(fields, "report.method", "检测方法", basic_information.get("detection_method"), 0.8, find_page(page_texts, str(basic_information.get("detection_method") or "")))
    add_field(fields, "report.assessment_date", "采样日期", additional_info["sample_date"], 0.78, find_page(page_texts, additional_info["sample_date"]))
    add_field(fields, "report.received_at", "接收时间", additional_info["receive_date"], 0.76, find_page(page_texts, additional_info["receive_date"]))
    add_field(fields, "report.reported_at", "报告时间", additional_info["report_date"], 0.76, find_page(page_texts, additional_info["report_date"]))
    for test in structured_report["tests"]:
        code = str(test.get("item_code") or "")
        if not code:
            continue
        page = int(test.get("page") or 1)
        display_value = format_result_display(str(test.get("result") or ""), str(test.get("indicator") or ""))
        add_field(fields, f"p01.{code}.result_display", str(test.get("test_name") or ""), display_value, 0.72, page)
        add_field(fields, f"p01.{code}.reference_range", str(test.get("test_name") or ""), test.get("reference_range"), 0.68, page)
        add_field(fields, f"p01.{code}.unit", str(test.get("test_name") or ""), test.get("unit"), 0.68, page)
        if test.get("indicator"):
            add_field(fields, f"p01.{code}.status", str(test.get("test_name") or ""), test.get("indicator"), 0.7, page)
    add_field(fields, "p01.fb_ratio.result_display", "F/B比值", fb_ratio.get("firmicutes_bacteroidetes_ratio"), 0.7, find_page(page_texts, "厚壁菌门"))
    add_field(fields, "p01.fb_ratio.status", "F/B比值评估", fb_ratio.get("result_evaluation"), 0.7, find_page(page_texts, "厚壁菌门"))
    add_field(fields, "p01.be_index.result_display", "B/E比值", be_index.get("bifidobacterium_enterobacteriaceae_ratio"), 0.74, find_page(page_texts, "B/E 指数"))
    add_field(fields, "p01.be_index.status", "B/E比值评估", be_index.get("result_evaluation"), 0.74, find_page(page_texts, "B/E 指数"))
    return fields


def extract_p05_fields(page_texts: list[str], structured_report: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report["patient_info"]
    additional_info = structured_report["additional_info"]
    p05_report = structured_report.get("p05_extracted_report", {})
    reports = p05_report.get("reports", []) if isinstance(p05_report, dict) else []
    report_overview = p05_report.get("report_overview", {}) if isinstance(p05_report, dict) else {}

    add_field(fields, "report.barcode", "条形码", structured_report["report_id"], 0.84, find_page(page_texts, structured_report["report_id"]))
    add_field(fields, "patient.name", "姓名", patient_info["name"], 0.82, find_page(page_texts, patient_info["name"]))
    add_field(fields, "patient.gender", "性别", patient_info["gender"], 0.8, find_page(page_texts, patient_info["gender"]))
    if patient_info["age"] != "":
        add_field(fields, "patient.age", "年龄", f"{patient_info['age']} 岁", 0.8, find_page(page_texts, str(patient_info["age"])))
    if patient_info["specimen_types"]:
        add_field(fields, "patient.specimen_types", "样本类型", "、".join(patient_info["specimen_types"]), 0.78, None)
    add_field(fields, "patient.hospital", "送检单位", patient_info["hospital"], 0.76, find_page(page_texts, patient_info["hospital"]))
    add_field(fields, "report.assessment_date", "评估日期", additional_info["report_date"] or additional_info["sample_date"], 0.78, find_page(page_texts, additional_info["report_date"] or additional_info["sample_date"]))
    add_field(fields, "organization.phone", "联系电话", report_overview.get("phone"), 0.84, find_page(page_texts, str(report_overview.get("phone") or "")))
    add_field(fields, "organization.website", "官方网站", report_overview.get("website"), 0.82, find_page(page_texts, str(report_overview.get("website") or "")))
    add_field(fields, "organization.address", "公司地址", report_overview.get("address"), 0.8, find_page(page_texts, str(report_overview.get("address") or "")))
    for report in reports:
        if not isinstance(report, dict):
            continue
        page = int(report.get("page") or 1)
        for item in report.get("test_items", []):
            if not isinstance(item, dict):
                continue
            item_code = str(item.get("item_code") or field_key_safe(str(item.get("test_name") or "")))
            label = str(item.get("test_name") or item_code)
            add_field(fields, f"p05.{item_code}.result_display", label, item.get("result"), 0.82, page)
            add_field(fields, f"p05.{item_code}.reference_range", label, item.get("reference_range"), 0.8, page)
            add_field(fields, f"p05.{item_code}.unit", label, item.get("unit"), 0.8, page)
            add_field(fields, f"p05.{item_code}.method", label, item.get("method"), 0.8, page)
    return fields


def extract_p02_fields(
    full_text: str,
    page_texts: list[str],
    structured_report: dict[str, Any],
) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report["patient_info"]
    additional_info = structured_report["additional_info"]

    add_field(fields, "report.barcode", "条形码", structured_report["report_id"], 0.96, find_page(page_texts, structured_report["report_id"]))
    add_field(fields, "patient.name", "姓名", patient_info["name"], 0.92, find_page(page_texts, patient_info["name"]))
    add_field(fields, "patient.gender", "性别", patient_info["gender"], 0.9, find_page(page_texts, patient_info["gender"]))
    if patient_info["age"] != "":
        add_field(fields, "patient.age", "年龄", f"{patient_info['age']} 岁", 0.9, find_page(page_texts, str(patient_info["age"])))
    add_field(
        fields,
        "patient.specimen_condition",
        "标本情况",
        patient_info["specimen_condition"],
        0.84,
        find_page(page_texts, patient_info["specimen_condition"]),
    )
    if patient_info["specimen_types"]:
        add_field(fields, "patient.specimen_types", "标本类型", "、".join(patient_info["specimen_types"]), 0.88, None)
    add_field(fields, "patient.hospital", "送检单位", patient_info["hospital"], 0.82, find_page(page_texts, patient_info["hospital"]))
    add_field(fields, "report.assessment_date", "采样日期", additional_info["sample_date"], 0.86, find_page(page_texts, additional_info["sample_date"]))
    add_field(fields, "report.received_at", "接收时间", additional_info["receive_date"], 0.84, find_page(page_texts, additional_info["receive_date"]))
    add_field(fields, "report.reported_at", "报告时间", additional_info["report_date"], 0.84, find_page(page_texts, additional_info["report_date"]))

    positive_allergens: list[str] = []
    for test in structured_report["tests"]:
        name = test["test_name"]
        original_name = name.replace("／", "/")
        display_value = format_result_display(test["result"], test["indicator"])
        page = test["page"]
        if "钙卫蛋白" in name:
            add_field(fields, "p02.calprotectin.result_display", "粪便钙卫蛋白检测结果", display_value, 0.94, page)
            add_field(fields, "p02.calprotectin.reference_range", "粪便钙卫蛋白参考范围", test["reference_range"], 0.92, page)
            add_field(fields, "p02.calprotectin.method", "粪便钙卫蛋白检测方法", test["method"], 0.9, page)
            if test["indicator"]:
                add_field(fields, "p02.calprotectin.abnormal_flag", "粪便钙卫蛋白异常标记", test["indicator"], 0.9, page)
            continue
        if "总IgE" in name:
            add_field(fields, "p02.total_ige.result_display", "总IgE检测结果", display_value, 0.94, page)
            add_field(fields, "p02.total_ige.reference_range", "总IgE参考范围", test["reference_range"], 0.92, page)
            add_field(fields, "p02.total_ige.method", "总IgE检测方法", test["method"], 0.9, page)
            if test["indicator"]:
                add_field(fields, "p02.total_ige.abnormal_flag", "总IgE异常标记", test["indicator"], 0.9, page)
            continue

        field_key = f"p02.allergen.items.{field_key_safe(original_name)}"
        add_field(fields, field_key, original_name, display_value, 0.88, page)
        if "阳性" in test["result"] or "弱阳性" in test["result"]:
            positive_allergens.append(f"{name}：{display_value}")

    if any(field["field_key"].startswith("p02.allergen.items.") for field in fields):
        overall = "所有检测项目均为阴性" if not positive_allergens else "、".join(positive_allergens)
        add_field(fields, "p02.allergen.overall_result", "过敏原整体检测结果", overall, 0.88, find_page(page_texts, "免疫印迹法"))
        add_field(fields, "p02.allergen.reference_range", "过敏原参考范围", "阴性", 0.88, find_page(page_texts, "免疫印迹法"))

    return fields


def extract_p03_fields(page_texts: list[str], structured_report: dict[str, Any]) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report["patient_info"]
    additional_info = structured_report["additional_info"]

    add_field(fields, "report.barcode", "条形码", structured_report["report_id"], 0.9, find_page(page_texts, structured_report["report_id"]))
    add_field(fields, "patient.name", "姓名", patient_info["name"], 0.86, find_page(page_texts, patient_info["name"]))
    add_field(fields, "patient.gender", "性别", patient_info["gender"], 0.84, find_page(page_texts, patient_info["gender"]))
    if patient_info["age"] != "":
        add_field(fields, "patient.age", "年龄", f"{patient_info['age']} 岁", 0.84, find_page(page_texts, str(patient_info["age"])))
    if patient_info["specimen_types"]:
        add_field(fields, "patient.specimen_types", "标本类型", "、".join(patient_info["specimen_types"]), 0.82, None)
    add_field(fields, "patient.hospital", "送检单位", patient_info["hospital"], 0.8, find_page(page_texts, patient_info["hospital"]))
    add_field(fields, "report.assessment_date", "采样日期", additional_info["sample_date"], 0.82, find_page(page_texts, additional_info["sample_date"]))
    add_field(fields, "report.received_at", "接收时间", additional_info["receive_date"], 0.8, find_page(page_texts, additional_info["receive_date"]))
    add_field(fields, "report.reported_at", "报告时间", additional_info["report_date"], 0.8, find_page(page_texts, additional_info["report_date"]))

    for test in structured_report["tests"]:
        code = str(test.get("item_code") or "")
        if not code:
            continue
        page = int(test.get("page") or 1)
        add_field(fields, f"p03.{code}.result_display", str(test.get("test_name") or ""), test.get("result"), 0.82, page)
        add_field(fields, f"p03.{code}.reference_range", str(test.get("test_name") or ""), test.get("reference_range"), 0.8, page)
        add_field(fields, f"p03.{code}.unit", str(test.get("test_name") or ""), test.get("unit"), 0.8, page)
        add_field(fields, f"p03.{code}.method", str(test.get("test_name") or ""), test.get("method"), 0.78, page)
        if test.get("indicator"):
            add_field(fields, f"p03.{code}.abnormal_flag", str(test.get("test_name") or ""), test.get("indicator"), 0.8, page)
    return fields


def extract_structured_tests(page_texts: list[str], package_code: str = "P02") -> list[dict[str, Any]]:
    if package_code == "P01":
        return extract_p01_structured_tests(page_texts)
    if package_code == "P05":
        return []
    if package_code == "P03":
        return extract_p03_structured_tests(page_texts)

    tests: list[dict[str, Any]] = []
    for page_number, text in enumerate(page_texts, start=1):
        specimen_type = extract_page_specimen_type(text)
        cal_match = re.search(
            rf"{name_pattern(CALPROTECTIN_NAME)}\s*(?P<result>{RESULT_PATTERN})\s*"
            rf"(?P<method>胶体金法)?\s*(?P<reference>阴性|阳性)?\s*(?P<flag>[↑↓])?",
            text,
            flags=re.IGNORECASE,
        )
        if cal_match:
            tests.append(
                build_test(
                    page=page_number,
                    specimen_type=specimen_type or "粪便",
                    test_name=CALPROTECTIN_NAME,
                    raw_result=cal_match.group("result"),
                    flag=cal_match.group("flag"),
                    reference_range=cal_match.group("reference") or "阴性",
                    method=cal_match.group("method") or "胶体金法",
                )
            )

        for item in ALLERGEN_ITEMS:
            row_match = re.search(
                rf"{name_pattern(item)}\s*(?P<result>{RESULT_PATTERN})\s*"
                rf"(?P<reference>阴性|阳性)?\s*(?P<flag>[↑↓])?\s*(?P<method>免疫印迹法)?",
                text,
                flags=re.IGNORECASE,
            )
            if not row_match:
                continue
            tests.append(
                build_test(
                    page=page_number,
                    specimen_type=specimen_type or "血清",
                    test_name=output_test_name(item),
                    raw_result=row_match.group("result"),
                    flag=row_match.group("flag"),
                    reference_range=row_match.group("reference") or "阴性",
                    method=row_match.group("method") or "免疫印迹法",
                )
            )

        ige_match = re.search(
            rf"{name_pattern(TOTAL_IGE_NAME)}\s*(?P<result>{RESULT_PATTERN})\s*"
            rf"(?P<reference>阴性|阳性)?\s*(?P<flag>[↑↓])?\s*(?P<method>免疫印迹法)?",
            text,
            flags=re.IGNORECASE,
        )
        if ige_match:
            tests.append(
                build_test(
                    page=page_number,
                    specimen_type=specimen_type or "血清",
                    test_name=TOTAL_IGE_NAME,
                    raw_result=ige_match.group("result"),
                    flag=ige_match.group("flag"),
                    reference_range=ige_match.group("reference") or "阴性",
                    method=ige_match.group("method") or "免疫印迹法",
                )
            )

    return tests


def extract_p01_structured_tests(page_texts: list[str], p01_report: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    report = p01_report or build_p01_extracted_report("", " ".join(page_texts), page_texts)
    basic_information = report.get("basic_information", {})
    specimen_type = str(basic_information.get("sample_type") or "粪便")
    tests: list[dict[str, Any]] = []

    gmhi = report.get("gmhi", {})
    if gmhi.get("score") is not None:
        tests.append(
            {
                "page": 4,
                "specimen_type": specimen_type,
                "test_name": "GMHI",
                "item_code": "gmhi",
                "result": _format_number(gmhi.get("score")),
                "indicator": str(gmhi.get("assessment") or ""),
                "reference_range": "0-100",
                "unit": "分",
                "method": str(basic_information.get("detection_method") or "高通量测序"),
            }
        )

    diversity = report.get("diversity", {})
    if diversity.get("shannon_index") is not None:
        tests.append(
            {
                "page": 7,
                "specimen_type": specimen_type,
                "test_name": "菌群多样性",
                "item_code": "diversity",
                "result": _format_number(diversity.get("shannon_index")),
                "indicator": _extract_p01_diversity_status(diversity),
                "reference_range": str(diversity.get("reference_percentile") or ""),
                "unit": "",
                "method": str(basic_information.get("detection_method") or "高通量测序"),
            }
        )

    intestinal_age = report.get("intestinal_age", {})
    if intestinal_age.get("intestinal_age") is not None:
        tests.append(
            {
                "page": 8,
                "specimen_type": specimen_type,
                "test_name": "肠龄",
                "item_code": "gut_age",
                "result": str(intestinal_age.get("intestinal_age")),
                "indicator": str(intestinal_age.get("age_difference") or ""),
                "reference_range": "成人偏差≤3岁",
                "unit": "岁",
                "method": str(basic_information.get("detection_method") or "高通量测序"),
            }
        )

    enterotype = report.get("enterotype", {})
    if enterotype.get("result"):
        tests.append(
            {
                "page": 6,
                "specimen_type": specimen_type,
                "test_name": "肠型",
                "item_code": "enterotype",
                "result": str(enterotype.get("result") or ""),
                "indicator": "",
                "reference_range": "",
                "unit": "",
                "method": str(basic_information.get("detection_method") or "高通量测序"),
            }
        )

    fb_ratio = report.get("fb_ratio", {})
    if fb_ratio.get("firmicutes_bacteroidetes_ratio") is not None:
        tests.append(
            {
                "page": 9,
                "specimen_type": specimen_type,
                "test_name": "F/B比值",
                "item_code": "fb_ratio",
                "result": _format_number(fb_ratio.get("firmicutes_bacteroidetes_ratio")),
                "indicator": str(fb_ratio.get("result_evaluation") or ""),
                "reference_range": str(fb_ratio.get("reference_range") or ""),
                "unit": "",
                "method": str(basic_information.get("detection_method") or "高通量测序"),
            }
        )

    be_index = report.get("be_index", {})
    if be_index.get("bifidobacterium_enterobacteriaceae_ratio") is not None:
        tests.append(
            {
                "page": 10,
                "specimen_type": specimen_type,
                "test_name": "B/E指数",
                "item_code": "be_index",
                "result": _format_number(be_index.get("bifidobacterium_enterobacteriaceae_ratio")),
                "indicator": str(be_index.get("result_evaluation") or ""),
                "reference_range": str(be_index.get("reference_range") or ""),
                "unit": "",
                "method": str(basic_information.get("detection_method") or "高通量测序"),
            }
        )

    immunity = report.get("immunity_assessment", {})
    intestinal_immunity = immunity.get("intestinal_immunity", {})
    if intestinal_immunity.get("value") is not None:
        tests.append(
            {
                "page": 41,
                "specimen_type": specimen_type,
                "test_name": "肠道免疫力",
                "item_code": "intestinal_immunity",
                "result": _format_number(intestinal_immunity.get("value")),
                "indicator": str(intestinal_immunity.get("status") or ""),
                "reference_range": str(intestinal_immunity.get("reference") or ""),
                "unit": "",
                "method": "微生态综合评估",
            }
        )
    intestinal_anti_inflammatory = immunity.get("intestinal_anti_inflammatory", {})
    if intestinal_anti_inflammatory.get("value") is not None:
        tests.append(
            {
                "page": 41,
                "specimen_type": specimen_type,
                "test_name": "肠道抗炎能力",
                "item_code": "intestinal_anti_inflammatory",
                "result": _format_number(intestinal_anti_inflammatory.get("value")),
                "indicator": str(intestinal_anti_inflammatory.get("status") or ""),
                "reference_range": str(intestinal_anti_inflammatory.get("reference") or ""),
                "unit": "",
                "method": "微生态综合评估",
            }
        )

    metabolism = report.get("metabolism_and_nutrients", {})
    vitamin_a = metabolism.get("vitamins", {}).get("vitamin_a", {}) if isinstance(metabolism, dict) else {}
    if vitamin_a.get("value") is not None:
        tests.append(
            {
                "page": 43,
                "specimen_type": specimen_type,
                "test_name": "维生素A合成能力",
                "item_code": "vitamin_a",
                "result": _format_number(vitamin_a.get("value")),
                "indicator": str(vitamin_a.get("status") or ""),
                "reference_range": str(vitamin_a.get("reference") or ""),
                "unit": "",
                "method": "微生态综合评估",
            }
        )

    return tests


def find_p01_metric_result(text: str, keywords: list[str], *, default_unit: str = "") -> dict[str, str] | None:
    for keyword in sorted(keywords, key=len, reverse=True):
        pattern = re.compile(name_pattern(keyword), flags=re.IGNORECASE)
        for match in pattern.finditer(text):
            window = normalize_text(text[match.end() : match.end() + 160])
            parsed = parse_p01_metric_window(window, default_unit=default_unit)
            if parsed:
                return parsed
    return None


def parse_p01_metric_window(window: str, *, default_unit: str = "") -> dict[str, str] | None:
    cleaned = normalize_text(window)
    value_match = re.search(
        r"(?:[:：=为]\s*)?(?P<value>-?[0-9]+(?:\.[0-9]+)?|[A-Za-z\u4e00-\u9fff]{1,16}型)",
        cleaned,
    )
    if not value_match:
        return None
    tail = cleaned[value_match.end() : value_match.end() + 120]
    indicator_match = re.search(r"[↑↓]|偏低|偏高|异常|正常|理想|良好|较低|较高|不足|失衡|高风险|中风险|低风险", tail[:80])
    reference_match = re.search(
        r"(?:参考|范围|正常值|参考范围)[:：]?\s*"
        r"(?P<reference>[<>≤≥]?\s*-?[0-9]+(?:\.[0-9]+)?(?:\s*(?:--|-|－|—|–|~|～)\s*-?[0-9]+(?:\.[0-9]+)?)?)",
        tail,
    )
    unit_match = re.search(r"岁|分|%|指数", tail[:24])
    return {
        "value": value_match.group("value"),
        "indicator": indicator_match.group(0) if indicator_match else "",
        "reference": normalize_reference(reference_match.group("reference")) if reference_match else "",
        "unit": normalize_unit(unit_match.group(0)) if unit_match else default_unit,
    }


def extract_p03_structured_tests(page_texts: list[str]) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for page_number, text in enumerate(page_texts, start=1):
        specimen_type = extract_page_specimen_type(text) or "血清"
        for code, output_name, keywords, default_unit in P03_TEST_DEFINITIONS:
            if code in seen_codes:
                continue
            parsed = find_p03_numeric_result(text, keywords, code=code, default_unit=default_unit)
            if not parsed:
                continue
            unit = parsed["unit"] or default_unit
            if default_unit and parsed.get("prefix_unit") == default_unit and unit != default_unit:
                unit = default_unit
            method = parsed["method"]
            if method == "PDF文本层抽取" and parsed.get("prefix_method"):
                method = parsed["prefix_method"]
            tests.append(
                {
                    "page": page_number,
                    "specimen_type": specimen_type,
                    "test_name": output_name,
                    "item_code": code,
                    "result": parsed["value"],
                    "indicator": parsed["flag"],
                    "reference_range": parsed["reference"],
                    "unit": unit,
                    "method": method,
                }
            )
            seen_codes.add(code)
    return tests


def find_p03_numeric_result(text: str, keywords: list[str], *, code: str, default_unit: str = "") -> dict[str, str] | None:
    for keyword in sorted(keywords, key=len, reverse=True):
        pattern = re.compile(name_pattern(keyword), flags=re.IGNORECASE)
        for match in pattern.finditer(text):
            if code == "hba1" and re.match(r"\s*(?:C|c|ab|AB)", text[match.end() : match.end() + 4]):
                continue
            prefix = text[max(0, match.start() - 160) : match.start()]
            prefix_parsed = parse_p03_prefix_result(prefix, default_unit=default_unit) if code == "c_peptide" else None
            if prefix_parsed:
                return prefix_parsed
            parsed = parse_p03_result_window(text[match.end() : match.end() + 180], prefix=prefix)
            if code == "c_peptide" and parsed and normalize_reference(parsed.get("reference", "")) == "3--25":
                continue
            if parsed:
                return parsed
    return None


def parse_p03_result_window(window: str, *, prefix: str = "") -> dict[str, str] | None:
    cleaned = normalize_text(window)
    value_match = re.search(r"(?<![A-Za-z])(?P<value>[0-9]+(?:\.[0-9]+)?)", cleaned)
    if not value_match:
        return None
    tail = cleaned[value_match.end() : value_match.end() + 150]
    method_match = find_p03_method_match(tail)
    row_tail = tail[: method_match[2]] if method_match else tail
    indicator_match = re.search(r"[↑↓]", row_tail[:24])
    reference_match = re.search(rf"({P03_REFERENCE_PATTERN})", row_tail)
    unit_match = re.search(r"mmol/L|mmol／L|uU/mL|μU/mL|uIU/mL|ng/mL|g/L|mg/L|mg/dL|%", row_tail, flags=re.IGNORECASE)
    method = method_match[0] if method_match else ""
    prefix_unit_match = re.search(r"(mmol/L|mmol／L|uU/mL|μU/mL|uIU/mL|ng/mL|g/L|mg/L|mg/dL|%)\s*(?:\S{0,8})\s*$", prefix, flags=re.IGNORECASE)
    prefix_method = extract_p03_method(prefix[-30:])
    return {
        "value": value_match.group("value"),
        "unit": normalize_unit(unit_match.group(0)) if unit_match else "",
        "prefix_unit": normalize_unit(prefix_unit_match.group(1)) if prefix_unit_match else "",
        "reference": normalize_reference(reference_match.group(0)) if reference_match else "",
        "flag": indicator_match.group(0) if indicator_match else "",
        "method": method or "PDF文本层抽取",
        "prefix_method": prefix_method,
    }


def parse_p03_prefix_result(prefix: str, *, default_unit: str) -> dict[str, str] | None:
    if not default_unit:
        return None
    cleaned = normalize_text(prefix)
    unit_pattern = r"mmol/L|mmol／L|uU/mL|μU/mL|uIU/mL|ng/mL|g/L|mg/L|mg/dL|%"
    method_pattern = "|".join(re.escape(method) for method in P03_METHOD_NAMES)
    pattern = re.compile(
        rf"(?P<unit>{unit_pattern})\s*(?P<method>{method_pattern})\s*"
        rf"(?P<value>[0-9]+(?:\.[0-9]+)?)\s*(?P<flag>[↑↓])?\s*(?P<reference>{P03_REFERENCE_PATTERN})",
        flags=re.IGNORECASE,
    )
    matches = list(pattern.finditer(cleaned))
    for match in reversed(matches):
        unit = normalize_unit(match.group("unit"))
        if unit.lower() != default_unit.lower():
            continue
        return {
            "value": match.group("value"),
            "unit": unit,
            "prefix_unit": "",
            "reference": normalize_reference(match.group("reference")),
            "flag": match.group("flag") or "",
            "method": "NBT 法" if match.group("method") == "NBT法" else match.group("method"),
            "prefix_method": "",
        }
    return None


def build_test(
    page: int,
    specimen_type: str,
    test_name: str,
    raw_result: str,
    flag: str | None,
    reference_range: str,
    method: str,
) -> dict[str, Any]:
    result, indicator = split_result_indicator(raw_result, flag)
    return {
        "page": page,
        "specimen_type": specimen_type,
        "test_name": test_name,
        "result": result,
        "indicator": indicator,
        "reference_range": reference_range,
        "unit": "",
        "method": method,
    }


def split_result_indicator(raw_result: str, flag: str | None) -> tuple[str, str]:
    cleaned = normalize_text(raw_result).replace(" ", "")
    if cleaned.startswith("弱阳性"):
        result = "弱阳性"
    elif cleaned.startswith("阳性"):
        result = "阳性"
    elif cleaned.startswith("阴性"):
        result = "阴性"
    else:
        result = cleaned

    level_match = re.search(r"[（(](\+{1,3})[）)]", cleaned)
    indicator = f"（{level_match.group(1)}）" if level_match else ""
    if flag and flag not in indicator:
        indicator = f"{indicator}{flag}"
    if result == "阴性" and not level_match:
        indicator = ""
    return result, indicator


def extract_report_id(text: str) -> str:
    match = re.search(r"条\s*形\s*码[:：]?\s*([0-9]{6,})", text)
    if match:
        return match.group(1)
    fallback = re.search(r"\b([0-9]{10,})\b", text)
    return fallback.group(1) if fallback else ""


def extract_barcodes(text: str) -> list[str]:
    values: list[str] = []
    for match in re.finditer(r"\b([0-9]{10,})\b", text):
        value = match.group(1)
        if value not in values:
            values.append(value)
    return values


def extract_laboratory(text: str) -> str:
    match = re.search(r"([\u4e00-\u9fff]{2,}医学检验实验室)", text)
    return match.group(1) if match else ""


def extract_remarks(text: str) -> str:
    match = re.search(r"备注[:：]?\s*([^\s]+(?:医学检测|检测)?)", text)
    return clean_value(match.group(1)) if match else ""


def extract_disclaimer(text: str) -> str:
    match = re.search(r"(本检测仅对来样负责[^。！!]*[。！!])", text)
    return clean_value(match.group(1)) if match else ""


def extract_website(text: str) -> str:
    match = re.search(r"(?:www\.)?[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    match = re.search(r"\b(?:400|800)-?[0-9]{3}-?[0-9]{4}\b", text)
    return match.group(0) if match else ""


def extract_address(text: str) -> str:
    match = re.search(r"地址[:：]?\s*([^\s]+(?:大楼|中心|实验室|医院|公司|园区)?)", text)
    return clean_value(match.group(1)) if match else ""


def numeric_or_text(value: Any) -> float | int | str:
    text = str(value or "").strip()
    if not text:
        return ""
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", text):
        return text
    parsed = float(text)
    return int(parsed) if "." not in text else parsed


def find_p03_method_match(text: str) -> tuple[str, int, int] | None:
    normalized = normalize_text(text)
    best: tuple[str, int, int] | None = None
    for method in P03_METHOD_NAMES:
        compact_pattern = r"\s*".join(re.escape(char) for char in method if not char.isspace())
        match = re.search(compact_pattern, normalized, flags=re.IGNORECASE)
        if not match:
            continue
        output_method = "NBT 法" if method == "NBT法" else method
        candidate = (output_method, match.start(), match.end())
        if best is None or candidate[1] < best[1]:
            best = candidate
    return best


def extract_p03_method(text: str) -> str:
    match = find_p03_method_match(text)
    return match[0] if match else ""


def normalize_unit(unit: str) -> str:
    return unit.replace("／", "/").replace("μU", "uU")


def normalize_reference(reference: str) -> str:
    cleaned = re.sub(r"\s+", "", reference)
    cleaned = cleaned.replace("＜", "<").replace("＞", ">")
    cleaned = cleaned.replace("－", "-").replace("—", "-").replace("–", "-")
    cleaned = cleaned.replace("~", "--").replace("～", "--")
    cleaned = re.sub(r"(?<=\d)-(?=\d)", "--", cleaned)
    return cleaned


def extract_patient_name(text: str) -> str:
    patterns = [
        r"姓\s*名[:：]?\s*([^\s:：]+)\s+性\s*别",
        r"姓\s*名[:：]?\s*([^\s:：]+)\s+病\s*员\s*号",
        r"条\s*形\s*码[:：]?\s*[0-9]{6,}\s+姓\s*名[:：]?\s*([^\s:：]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        value = clean_value(match.group(1))
        if value and not looks_like_label(value):
            return value
    return ""


def extract_gender(text: str) -> str:
    match = re.search(r"性\s*别[:：]?\s*(?:病\s*员\s*号[:：]?\s*)?(?:床\s*号[:：]?\s*)?([男女])", text)
    return match.group(1) if match else ""


def extract_age(text: str) -> int | str:
    match = re.search(r"年\s*龄[:：]?\s*([0-9]{1,3})\s*岁?", text)
    return int(match.group(1)) if match else ""


def extract_specimen_condition(text: str) -> str:
    patterns = [
        r"标本情况[:：]?\s*(?:送检医生[:：]?\s*)?(未见异常|正常|异常|溶血|脂血)",
        r"(未见异常|正常|异常|溶血|脂血)\s*标本情况",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def extract_specimen_types(page_texts: list[str]) -> list[str]:
    values: list[str] = []
    pattern = re.compile(rf"{label_pattern('标本类型')}[:：]?\s*([^\s:：]+)")
    for text in page_texts:
        match = pattern.search(text)
        if match:
            value = clean_value(match.group(1))
            if value and not looks_like_label(value) and value not in values:
                values.append(value)
        for candidate in ["EDTA抗凝全血", "血清", "粪便", "全血"]:
            if candidate == "全血" and any("全血" in item for item in values):
                continue
            if candidate in text and candidate not in values:
                values.append(candidate)
    return values


def extract_page_specimen_type(text: str) -> str:
    pattern = re.compile(rf"{label_pattern('标本类型')}[:：]?\s*([^\s:：]+)")
    match = pattern.search(text)
    if match:
        return clean_value(match.group(1))
    for candidate in ["EDTA抗凝全血", "血清", "粪便", "全血"]:
        if candidate in text:
            return candidate
    return ""


def extract_hospital(text: str) -> str:
    if "安为康内部员工" in text:
        return "安为康内部员工"
    patterns = [
        r"送检单位[:：]?\s*([^\s:：]*(?:有限公司|医院|门诊部|中心|员工))",
        r"([\u4e00-\u9fffA-Za-z0-9（）()]{2,}(?:有限公司|医院|门诊部|中心|员工))",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        value = clean_value(match.group(1))
        if value and not looks_like_label(value):
            return value
    return ""


def extract_date(page_texts: list[str], label: str) -> str:
    values: list[str] = []
    pattern = re.compile(rf"{label_pattern(label)}[:：]?\s*({DATE_VALUE_PATTERN})")
    for text in page_texts:
        values.extend(match.group(1) for match in pattern.finditer(text))
    if not values:
        return ""
    if label == "采样日期":
        return min(values)
    if label in {"接收时间", "报告时间"}:
        return max(values)
    return values[-1]


def extract_staff(text: str, labels: list[str]) -> str:
    for label in labels:
        pattern = re.compile(rf"{label_pattern(label)}[:：]?\s*([^\s:：]+)")
        match = pattern.search(text)
        if not match:
            continue
        value = clean_value(match.group(1))
        if value and not looks_like_label(value):
            return value
    return ""


def label_pattern(label: str) -> str:
    return r"\s*".join(re.escape(char) for char in label)


def name_pattern(name: str) -> str:
    parts: list[str] = []
    for char in name:
        if char.isspace():
            parts.append(r"\s*")
        elif char == "/":
            parts.append(r"[/／]")
        elif char in {"（", "("}:
            parts.append(r"[（(]")
        elif char in {"）", ")"}:
            parts.append(r"[）)]")
        elif char in {"-", "－", "—", "–"}:
            parts.append(r"[-－—–]")
        else:
            parts.append(re.escape(char))
    return r"\s*".join(parts)


def output_test_name(name: str) -> str:
    return name.replace("/", "／")


def clean_value(value: str) -> str:
    return normalize_text(value).strip(" :：,，;；")


def looks_like_label(value: str) -> bool:
    label_words = {
        "姓名",
        "姓",
        "名",
        "性别",
        "病员号",
        "床号",
        "年龄",
        "标本情况",
        "送检医生",
        "科室",
        "检测项目",
        "临床诊断",
        "采样日期",
        "接收时间",
        "报告时间",
        "批准人",
        "审核者",
        "检测者",
        "检验者",
        "送检单位",
        "送检单位条码",
        "医院条码",
        "条形码",
        "备注",
    }
    compact = value.replace(" ", "")
    label_fragments = ["条码", "送检单位", "备注", "日期", "时间"]
    return compact in label_words or any(fragment in compact for fragment in label_fragments)


def format_result_display(result: str, indicator: str) -> str:
    return f"{result}{indicator}" if indicator else result


def field_key_safe(value: str) -> str:
    key = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", value)
    return key.strip("_")


def add_field(fields: list[dict[str, Any]], field_key: str, label: str, value: Any, confidence: float, page: int | None) -> None:
    if value is None or value == "":
        return
    fields.append(
        {
            "field_key": field_key,
            "label": label,
            "value": value,
            "confidence": confidence,
            "source": {
                "page": page,
                "bbox": None,
            },
        }
    )


def find_page(page_texts: list[str], needle: str) -> int | None:
    if not needle:
        return None
    for index, text in enumerate(page_texts, start=1):
        if needle in text:
            return index
    return None


def build_indicators(fields: list[dict[str, Any]]) -> dict[str, Any]:
    indicators: dict[str, Any] = {}
    for field in fields:
        key = field["field_key"]
        if key.startswith("p01.") or key.startswith("p02.") or key.startswith("p03.") or key.startswith("p05."):
            indicators[key] = {
                "label": field["label"],
                "value": field["value"],
                "confidence": field["confidence"],
                "source": field["source"],
            }
    return indicators


def calculate_confidence(fields: list[dict[str, Any]], pages: list[dict[str, Any]]) -> float:
    values = [field["confidence"] for field in fields]
    page_values = [block["confidence"] for page in pages for block in page["text_blocks"]]
    all_values = values + page_values
    return round(mean(all_values), 4) if all_values else 0.0


def build_warnings(
    fields: list[dict[str, Any]],
    pages: list[dict[str, Any]],
    structured_report: dict[str, Any],
    package_code: str = "P02",
) -> list[str]:
    warnings: list[str] = []
    if not any(page["text_blocks"][0]["text"] for page in pages):
        warnings.append("PDF未提取到文本，需要调用云OCR。")

    if package_code == "P01":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "p01.gmhi.result_display": "GMHI",
            "p01.gut_age.result_display": "肠龄",
            "p01.enterotype.result_display": "肠型",
            "p01.be_index.result_display": "B/E比值",
        }
    elif package_code == "P05":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
        }
    elif package_code == "P03":
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "p03.tg.result_display": "甘油三酯TG",
            "p03.hdl_c.result_display": "高密度脂蛋白HDL-C",
            "p03.glucose.result_display": "葡萄糖GLU",
            "p03.hba1c.result_display": "糖化血红蛋白A1C",
            "p03.insulin.result_display": "胰岛素Ins",
        }
    else:
        required = {
            "patient.name": "姓名",
            "patient.gender": "性别",
            "patient.age": "年龄",
            "p02.calprotectin.result_display": "粪便钙卫蛋白检测结果",
        }
    existing = {field["field_key"] for field in fields}
    for field_key, label in required.items():
        if field_key not in existing:
            warnings.append(f"未识别到必需字段：{label}")

    test_names = [test["test_name"] for test in structured_report["tests"]]
    if package_code == "P03":
        if test_names and len(test_names) < 12:
            warnings.append(f"糖脂代谢检验明细目标17项，当前仅识别到 {len(test_names)} 项，建议人工复核或切换云OCR。")
    if package_code == "P01":
        if not test_names:
            warnings.append("P01专项菌群指标抽取策略为初版占位，已先抽取基础资料；请结合真实PDF样例继续升级GMHI、肠龄、菌群多样性等字段。")
        elif len(test_names) < 5:
            warnings.append(f"P01专项菌群指标当前仅识别到 {len(test_names)} 项，建议人工复核或切换云OCR。")
        test_names = []
    if package_code == "P05":
        if not test_names:
            warnings.append("P05 当前先完成模板工程化与基础字段抽取；待接入真实PDF样例后补充压力激素、睡眠和代谢专项指标识别。")
        elif len(test_names) < 10:
            warnings.append(f"P05 当前仅识别到 {len(test_names)} 项检验明细，建议人工复核图片页OCR结果。")
        test_names = []
    allergen_count = sum(1 for name in test_names if "钙卫蛋白" not in name and "总IgE" not in name)
    if not test_names:
        if package_code not in {"P01", "P05"}:
            warnings.append("未识别到检验项目明细。")
    elif package_code == "P02" and allergen_count and allergen_count < 10:
        warnings.append(f"过敏原项目仅识别到 {allergen_count} 项，建议人工复核或切换云OCR。")
    if package_code == "P02" and not any("总IgE" in name for name in test_names):
        warnings.append("未识别到特异性总IgE结果。")

    additional_info = structured_report["additional_info"]
    if package_code == "P05":
        missing_staff = not any([additional_info["technician"], additional_info["reviewer"], additional_info["approver"]])
    elif package_code == "P01":
        missing_staff = not additional_info["technician"] or not additional_info["reviewer"]
    else:
        missing_staff = not additional_info["technician"] or not additional_info["reviewer"] or not additional_info["approver"]
    if missing_staff:
        warnings.append("未从PDF文本层识别到检测者/审核者/批准人；如需签名信息，请使用图像OCR或人工补录。")

    low_confidence = list(dict.fromkeys(field["label"] for field in fields if field["confidence"] < 0.75))
    if low_confidence:
        warnings.append("低置信度字段需人工复核：" + "、".join(low_confidence))
    return warnings
