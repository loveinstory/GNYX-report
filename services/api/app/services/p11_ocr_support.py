from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable


P11_FOOD_CODES: list[tuple[int, str, str]] = [
    (1, "玉米", "corn"),
    (2, "大米", "rice"),
    (3, "小麦", "wheat"),
    (4, "牛奶", "milk"),
    (5, "大豆", "soy"),
    (6, "螃蟹", "crab"),
    (7, "鳕鱼", "cod"),
    (8, "虾", "shrimp"),
    (9, "蘑菇", "mushroom"),
    (10, "西红柿", "tomato"),
    (11, "鸡蛋", "egg"),
    (12, "牛肉", "beef"),
    (13, "鸡肉", "chicken"),
    (14, "猪肉", "pork"),
    (15, "苹果", "apple"),
    (16, "香蕉", "banana"),
    (17, "芒果", "mango"),
    (18, "菠萝", "pineapple"),
    (19, "桃", "peach"),
    (20, "橘子", "orange"),
    (21, "西瓜", "watermelon"),
    (22, "哈密瓜", "cantaloupe"),
    (23, "猕猴桃", "kiwi"),
    (24, "西兰花", "broccoli"),
    (25, "胡萝卜", "carrot"),
    (26, "葡萄", "grape"),
    (27, "柚子", "grapefruit"),
    (28, "草莓", "strawberry"),
    (29, "龙虾", "lobster"),
    (30, "三文鱼", "salmon"),
    (31, "沙丁鱼", "sardine"),
    (32, "草鱼", "carp"),
    (33, "带鱼", "beltfish"),
    (34, "扇贝", "scallop"),
    (35, "蛤", "clam"),
    (36, "芝麻", "sesame"),
    (37, "菠菜", "spinach"),
    (38, "青豆", "green_pea"),
    (39, "火鸡", "turkey"),
    (40, "羊肉", "mutton"),
    (41, "腰果", "cashew"),
    (42, "花生", "peanut"),
]

P11_FOOD_INTOLERANCE_42_CODES: list[tuple[int, str, str]] = [
    (1, "玉米", "corn"),
    (2, "大米", "rice"),
    (3, "小麦", "wheat"),
    (4, "牛奶", "milk"),
    (5, "大豆", "soy"),
    (6, "蟹", "crab"),
    (7, "鳕鱼", "cod"),
    (8, "虾", "shrimp"),
    (9, "蘑菇", "mushroom"),
    (10, "西红柿", "tomato"),
    (11, "鸡蛋", "egg"),
    (12, "牛肉", "beef"),
    (13, "鸡肉", "chicken"),
    (14, "猪肉", "pork"),
    (15, "葡萄", "grape"),
    (16, "柚子", "grapefruit"),
    (17, "草莓", "strawberry"),
    (18, "龙虾", "lobster"),
    (19, "三文鱼", "salmon"),
    (20, "沙丁鱼", "sardine"),
    (21, "草鱼", "carp"),
    (22, "带鱼", "beltfish"),
    (23, "扇贝", "scallop"),
    (24, "蛤", "clam"),
    (25, "芝麻", "sesame"),
    (26, "菠菜", "spinach"),
    (27, "青豆", "green_pea"),
    (28, "火鸡", "turkey"),
    (29, "羊肉", "mutton"),
    (30, "腰果", "cashew"),
    (31, "花生", "peanut"),
    (32, "燕麦", "oat"),
    (33, "大麦", "barley"),
    (34, "菠萝", "pineapple"),
    (35, "香蕉", "banana"),
    (36, "苹果", "apple"),
    (37, "桃", "peach"),
    (38, "柠檬", "lemon"),
    (39, "杏", "apricot"),
    (40, "葵花籽", "sunflower_seed"),
    (41, "巧克力", "chocolate"),
    (42, "酵母", "yeast"),
]

P11_FOOD_ALIASES: dict[str, str] = {
    "蟹": "crab",
    "螃蟹": "crab",
    "番茄": "tomato",
    "西红柿": "tomato",
    "橄榄": "olive",
    "蓝莓": "blueberry",
    "榴莲": "durian",
    "火鸡肉": "turkey",
    "火鸡": "turkey",
    "贝类": "clam",
    "燕麦": "oat",
    "大麦": "barley",
    "柠檬": "lemon",
    "杏": "apricot",
    "葵花籽": "sunflower_seed",
    "巧克力": "chocolate",
    "酵母": "yeast",
}


def build_p11_structured_report(
    *,
    source_file: str,
    full_text: str,
    page_texts: list[str],
    extract_report_id: Callable[[str], str],
    extract_patient_name: Callable[[str], str],
    extract_gender: Callable[[str], str],
    extract_age: Callable[[str], Any],
    extract_specimen_condition: Callable[[str], str],
    extract_specimen_types: Callable[[list[str]], list[str]],
    extract_hospital: Callable[[str], str],
    extract_date: Callable[[list[str], str], str],
    extract_staff: Callable[[str, list[str]], str],
) -> dict[str, Any]:
    payload = parse_p11_json_payload(full_text) or _extract_p11_payload_from_text(full_text, page_texts)
    text_food_items = _extract_food_result_rows("\n".join(page_texts) or full_text)
    if text_food_items:
        payload["food_items"] = text_food_items
        payload["mode"] = str(payload.get("mode") or "pdf-food-result-table")
    report_info = payload.get("report_info", {})
    if isinstance(payload.get("test_results"), list):
        normalized = _normalize_payload_test_results(payload)
        food_items = normalized["food_items"]
        igg_items = normalized["igg_items"]
        ige_items = normalized["ige_items"]
    else:
        food_items = payload.get("food_items", [])
        igg_items = payload.get("igg_items", [])
        ige_items = payload.get("ige_items", [])

    tests = [_food_item_to_test(item) for item in food_items]
    tests.extend(_immune_item_to_test(item, default_page=4) for item in igg_items)
    tests.extend(_immune_item_to_test(item, default_page=4) for item in ige_items)

    report_id = str(report_info.get("barcode") or extract_report_id(full_text) or Path(source_file).stem)
    specimen_type = str(report_info.get("specimen_type") or "")
    specimen_types = [specimen_type] if specimen_type else extract_specimen_types(page_texts)

    return {
        "report_id": report_id,
        "patient_info": {
            "name": str(report_info.get("patient_name") or extract_patient_name(full_text)),
            "gender": str(report_info.get("gender") or extract_gender(full_text)),
            "age": _parse_age(report_info.get("age")) or extract_age(full_text),
            "specimen_condition": str(report_info.get("specimen_status") or extract_specimen_condition(full_text)),
            "specimen_types": specimen_types,
            "hospital": str(report_info.get("submitter") or extract_hospital(full_text)),
            "submitting_unit": str(report_info.get("submitter") or extract_hospital(full_text)),
            "patient_number": str(report_info.get("patient_id") or ""),
            "bed_number": str(report_info.get("bed_no") or ""),
            "department": str(report_info.get("department") or ""),
            "doctor": str(report_info.get("doctor") or ""),
            "clinical_diagnosis": _normalize_diagnosis(str(report_info.get("clinical_diagnosis") or "")),
            "phone": "",
        },
        "tests": tests,
        "notes": str(payload.get("interpretation_text") or ""),
        "additional_info": {
            "sample_date": str(payload.get("sampling_time") or extract_date(page_texts, "采样时间") or extract_date(page_texts, "采样日期")),
            "receive_date": str(payload.get("receive_time") or extract_date(page_texts, "接收时间")),
            "report_date": str(payload.get("report_time_food") or payload.get("report_time_ige") or extract_date(page_texts, "报告时间")),
            "technician": str(payload.get("detector") or extract_staff(full_text, ["检测者", "检验者"])),
            "reviewer": str(payload.get("reviewer") or extract_staff(full_text, ["审核者", "复核者"])),
            "approver": str(payload.get("approver") or extract_staff(full_text, ["批准人", "批准者"])),
        },
        "p11_extracted_report": payload,
    }


def parse_p11_json_payload(full_text: str) -> dict[str, Any]:
    text = str(full_text or "").strip()
    if not text:
        return {}
    candidates = [text]
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidate = text[start : end + 1]
        if candidate not in candidates:
            candidates.append(candidate)
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if isinstance(payload.get("report_info"), dict):
            if (
                isinstance(payload.get("test_results"), list)
                or isinstance(payload.get("food_items"), list)
                or isinstance(payload.get("food_substitution_table"), list)
            ):
                return payload
        if _is_reportmeta_sections_payload(payload):
            return _normalize_reportmeta_sections_payload(payload)
        if _is_food_intolerance_payload(payload):
            return _normalize_food_intolerance_payload(payload)
    return {}


def extract_p11_fields(
    *,
    page_texts: list[str],
    structured_report: dict[str, Any],
    add_field: Callable[[list[dict[str, Any]], str, str, Any, float, int | None], None],
    find_page: Callable[[list[str], str], int | None],
) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    patient_info = structured_report.get("patient_info", {})
    additional_info = structured_report.get("additional_info", {})

    add_field(fields, "report.report_id", "报告编号", structured_report.get("report_id"), 0.9, find_page(page_texts, str(structured_report.get("report_id") or "")))
    add_field(fields, "patient.name", "姓名", patient_info.get("name"), 0.86, find_page(page_texts, str(patient_info.get("name") or "")))
    add_field(fields, "patient.gender", "性别", patient_info.get("gender"), 0.84, find_page(page_texts, str(patient_info.get("gender") or "")))
    if patient_info.get("age") not in ("", None):
        add_field(fields, "patient.age", "年龄", f"{patient_info.get('age')}岁", 0.84, find_page(page_texts, str(patient_info.get("age") or "")))
    add_field(fields, "patient.submitting_unit", "送检单位", patient_info.get("submitting_unit") or patient_info.get("hospital"), 0.86, None)
    add_field(fields, "patient.symptoms", "相关症状", patient_info.get("clinical_diagnosis") or "-", 0.82, None)
    add_field(fields, "sample.type", "样本信息", "空腹血清", 0.95, None)
    add_field(fields, "report.assessment_date", "评估日期", additional_info.get("report_date") or additional_info.get("sample_date"), 0.84, None)

    for test in structured_report.get("tests", []):
        code = str(test.get("item_code") or "")
        page = int(test.get("page") or 1)
        label = str(test.get("test_name") or code)
        if code.startswith("food_"):
            add_field(fields, f"p11.food.{code}.result", label, test.get("result"), 0.82, page)
            add_field(fields, f"p11.food.{code}.reference_range", label, test.get("reference_range"), 0.8, page)
            continue
        if code in {"igg1", "igg2", "igg3", "igg4", "total_ige"}:
            prefix = f"p11.indicators.{code}"
            add_field(fields, f"{prefix}.result", label, test.get("result"), 0.84, page)
            add_field(fields, f"{prefix}.reference_range", label, test.get("reference_range"), 0.82, page)
            add_field(fields, f"{prefix}.unit", label, test.get("unit"), 0.8, page)
            add_field(fields, f"{prefix}.method", label, test.get("method"), 0.8, page)
            if test.get("indicator"):
                add_field(fields, f"{prefix}.flag", label, test.get("indicator"), 0.8, page)
    return fields


def build_p11_warning_requirements() -> dict[str, str]:
    return {
        "patient.name": "姓名",
        "patient.gender": "性别",
        "patient.age": "年龄",
    }


def extract_p11_warning_messages(structured_report: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    tests = structured_report.get("tests", [])
    food_tests = [test for test in tests if str(test.get("item_code") or "").startswith("food_")]
    extracted = structured_report.get("p11_extracted_report", {})
    mode = str(extracted.get("mode") or "")
    has_immune_source = any(str(test.get("item_code") or "") in {"igg1", "igg2", "igg3", "igg4", "total_ige"} for test in tests)
    if len(food_tests) < 42:
        warnings.append(f"P11 食物不耐受目标为42项，当前识别到 {len(food_tests)} 项，建议人工复核或升级OCR。")
    elif len({str(test.get("item_code") or "") for test in food_tests}) < 42:
        warnings.append("P11 食物不耐受42项存在项目编码重复，建议核对食物名称映射。")
    pending_food_tests = [test for test in food_tests if str(test.get("result") or "").strip() == "待复核"]
    if pending_food_tests:
        warnings.append(f"P11 食物不耐受项目中有 {len(pending_food_tests)} 项为待复核，建议核对原始报告或补录。")
    if has_immune_source and not any(str(test.get("item_code") or "") == "total_ige" for test in tests):
        warnings.append("P11 未识别到总IgE结果。")
    if mode == "food-intolerance-results" and len(food_tests) == 42 and not pending_food_tests:
        return warnings
    return warnings


def _is_reportmeta_sections_payload(payload: dict[str, Any]) -> bool:
    return isinstance(payload.get("reportMeta"), dict) and isinstance(payload.get("sections"), list)


def _is_food_intolerance_payload(payload: dict[str, Any]) -> bool:
    return isinstance(payload.get("reportMeta"), dict) and isinstance(payload.get("foodIntoleranceResults"), list)


def _normalize_food_intolerance_payload(payload: dict[str, Any]) -> dict[str, Any]:
    report_meta = payload.get("reportMeta", {}) if isinstance(payload.get("reportMeta"), dict) else {}
    result_items = payload.get("foodIntoleranceResults", []) if isinstance(payload.get("foodIntoleranceResults"), list) else []
    report_info = {
        "barcode": _text(report_meta.get("barcode")),
        "patient_name": _text(report_meta.get("patientName") or report_meta.get("name")),
        "gender": _text(report_meta.get("gender")),
        "age": _text(report_meta.get("age")),
        "specimen_status": _text(report_meta.get("sampleStatus")),
        "specimen_type": _text(report_meta.get("sampleType")),
        "submitter": _text(report_meta.get("labName")),
        "clinical_diagnosis": _normalize_diagnosis(_text(report_meta.get("clinicalDiagnosis") or report_meta.get("orderingPhysician"))),
    }

    food_items: list[dict[str, Any]] = []
    for fallback_index, item in enumerate(result_items, start=1):
        if not isinstance(item, dict):
            continue
        food_name = _text(item.get("food") or item.get("name") or item.get("testItem"))
        if not food_name:
            continue
        food_items.append(
            {
                "index": _parse_index(item.get("id")) or _parse_index(item.get("index")) or fallback_index,
                "name": food_name,
                "code": _food_code_from_name(food_name),
                "result": _normalize_food_result(_text(item.get("result"))),
                "reference": _text(item.get("referenceRange") or item.get("reference_range") or "阴性"),
                "flag": _text(item.get("flag")),
            }
        )

    return {
        "mode": "food-intolerance-results",
        "report_info": report_info,
        "igg_items": [],
        "ige_items": [],
        "food_items": food_items,
        "sampling_time": _text(report_meta.get("collectionTime") or report_meta.get("samplingTime")),
        "receive_time": _text(report_meta.get("receiptTime") or report_meta.get("receiveTime")),
        "report_time_food": _text(report_meta.get("reportTime")),
        "interpretation_text": _text(payload.get("interpretation")),
        "disclaimer": _text(payload.get("disclaimer")),
        "raw_report_meta": report_meta,
        "food_intolerance_results": result_items,
        "contact": {
            "website": _text(report_meta.get("labWebsite")),
            "phone": _text(report_meta.get("labPhone")),
            "address": _text(report_meta.get("labAddress")),
        },
    }


def _normalize_reportmeta_sections_payload(payload: dict[str, Any]) -> dict[str, Any]:
    report_meta = payload.get("reportMeta", {}) if isinstance(payload.get("reportMeta"), dict) else {}
    laboratory_info = payload.get("laboratoryInfo", {}) if isinstance(payload.get("laboratoryInfo"), dict) else {}
    sections = payload.get("sections", []) if isinstance(payload.get("sections"), list) else []

    report_info = {
        "barcode": _text(report_meta.get("barcode")),
        "patient_name": _text(report_meta.get("patientName") or report_meta.get("name")),
        "gender": _text(report_meta.get("gender")),
        "age": _text(report_meta.get("age")),
        "specimen_status": _text(laboratory_info.get("sampleStatus")),
        "specimen_type": _text(laboratory_info.get("sampleType")),
        "submitter": _text(report_meta.get("labName")),
        "clinical_diagnosis": _normalize_diagnosis(_text(report_meta.get("clinicalDiagnosis") or report_meta.get("reportSubtitle"))),
    }

    food_items: list[dict[str, Any]] = []
    igg_items: list[dict[str, Any]] = []
    ige_items: list[dict[str, Any]] = []
    appendix_items = payload.get("foodAppendix", {}).get("categories", []) if isinstance(payload.get("foodAppendix"), dict) else []
    collection_times: list[str] = []
    receipt_times: list[str] = []
    report_times: list[str] = []
    interpretation_texts: list[str] = []

    for section_index, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            continue
        section_name = _text(section.get("sectionName") or section.get("section"))
        section_type = _text(section.get("testType"))
        if section_type and not report_info["specimen_type"]:
            report_info["specimen_type"] = section_type
        if _text(section.get("sampleStatus")) and not report_info["specimen_status"]:
            report_info["specimen_status"] = _text(section.get("sampleStatus"))
        collection_times.append(_text(section.get("collectionTime")))
        receipt_times.append(_text(section.get("receiptTime")))
        report_times.append(_text(section.get("reportTime")))
        interpretation_texts.append(_text(section.get("interpretation") or section.get("note")))

        results = section.get("results", [])
        if not isinstance(results, list):
            continue
        if "食物不耐受" in section_name:
            for index, item in enumerate(results, start=1):
                if not isinstance(item, dict):
                    continue
                food_name = _text(item.get("food") or item.get("name") or item.get("testItem"))
                if not food_name:
                    continue
                food_items.append(
                    {
                        "index": index,
                        "name": food_name,
                        "code": _food_code_from_name(food_name),
                        "result": _normalize_food_result(_text(item.get("result"))),
                        "reference": _text(item.get("referenceRange") or item.get("reference_range") or "阴性"),
                        "flag": _text(item.get("flag")),
                    }
                )
            continue

        for item in results:
            if not isinstance(item, dict):
                continue
            test_name = _text(item.get("testItem") or item.get("test_name") or item.get("name"))
            if not test_name:
                continue
            target = igg_items if _immune_code(test_name) != "total_ige" else ige_items
            target.append(
                {
                    "test_name": test_name,
                    "result": _text(item.get("result")),
                    "flag": _text(item.get("flag") or item.get("indicator") or item.get("status")),
                    "reference_range": _text(item.get("referenceRange") or item.get("reference_range")),
                    "unit": _text(item.get("unit")),
                    "method": _text(item.get("method") or section.get("method")),
                    "page": section_index,
                    "section_name": section_name,
                }
            )

    return {
        "report_info": report_info,
        "igg_items": igg_items,
        "ige_items": ige_items,
        "food_items": food_items,
        "sampling_time": _first_nonempty(collection_times),
        "receive_time": _first_nonempty(receipt_times),
        "report_time_ige": _first_nonempty(report_times),
        "report_time_food": _last_nonempty(report_times),
        "interpretation_text": "\n".join(text for text in interpretation_texts if text),
        "raw_report_meta": report_meta,
        "sections": sections,
        "food_appendix": appendix_items,
        "laboratory_info": laboratory_info,
        "contact": {
            "website": _text(report_meta.get("labWebsite")),
            "phone": _text(report_meta.get("labPhone")),
            "address": _text(report_meta.get("labAddress")),
        },
    }


def _extract_p11_payload_from_text(full_text: str, page_texts: list[str]) -> dict[str, Any]:
    pages_joined = "\n".join(page_texts)
    immune_page = _find_p11_page(
        page_texts,
        lambda text: all(name in text for name in ["IgG1", "IgG2", "IgG3", "IgG4"]),
        fallback=page_texts[0] if page_texts else full_text,
    )
    ige_page = _find_p11_page(
        page_texts,
        lambda text: "总IgE" in text,
        fallback=page_texts[1] if len(page_texts) > 1 else full_text,
    )
    food_page = _find_p11_page(
        page_texts,
        lambda text: "食物不耐受检测42项报告单" in text or ("序号 项目名称 结果 参考范围" in text and "食物特异性IgG" in pages_joined),
        fallback=page_texts[2] if len(page_texts) > 2 else full_text,
    )
    food_report_text = "\n".join(
        page
        for page in page_texts
        if "食物不耐受检测42项报告单" in page
        or "食物特异性IgG" in page
        or re.search(r"(?:^|\s)(?:[1-9]|[1-3]\d|4[0-2])\s+[\u4e00-\u9fffA-Za-z（）()·]{1,18}\s+(?:弱阳性|阳性|阴性|[+＋\-－±])\s+(?:弱阳性|阳性|阴性|[+＋\-－±])", page)
    ) or pages_joined

    report_info = {
        "barcode": _first_match(food_page, [r"条形码[:：]?\s*([A-Z0-9]+)", r"条\s*形\s*码[:：]?\s*([A-Z0-9]+)"]) or _first_match(pages_joined, [r"条\s*形\s*码[:：]?\s*([A-Z0-9]+)", r"条形码[:：]?\s*([A-Z0-9]+)"]),
        "patient_name": _first_match(food_page, [r"姓\s*名[:：]?\s*([^\s]+)"]) or _first_match(pages_joined, [r"姓\s*名[:：]?\s*([^\s]+)"]),
        "gender": _first_match(food_page, [r"性\s*别[:：]?\s*([男女])"]) or _first_match(pages_joined, [r"性\s*别[:：]?\s*([男女])"]),
        "age": _first_match(food_page, [r"年\s*龄[:：]?\s*(\d{1,3})"]) or _first_match(pages_joined, [r"年\s*龄[:：]?\s*(\d{1,3})"]),
        "specimen_status": _first_match(food_page, [r"样本性状[:：]?\s*([^\s]+)", r"标本情况[:：]?\s*([^\s]+)"]) or _first_match(pages_joined, [r"样本性状[:：]?\s*([^\s]+)", r"标本情况[:：]?\s*([^\s]+)"]),
        "specimen_type": _first_match(food_page, [r"标本类型[:：]?\s*([^\s]+)"]) or _first_match(pages_joined, [r"标本类型[:：]?\s*([^\s]+)"]),
        "submitter": _first_match(food_page, [r"送检单位[:：]\s*([^\s]+)"]) or _first_match(pages_joined, [r"送检单位[:：]\s*([^\s]+)"]),
        "clinical_diagnosis": _normalize_diagnosis(_extract_between(food_page, "临床诊断", ["检测方法", "检测结果", "序号"]) or _extract_between(immune_page, "临床诊断", ["送检科室", "年龄", "标本类型"])),
    }
    payload = {
        "report_info": report_info,
        "igg_items": _extract_immune_items(immune_page, ["IgG1", "IgG2", "IgG3", "IgG4"]),
        "ige_items": _extract_immune_items(ige_page, ["总IgE"]),
        "food_items": _extract_food_items(pages_joined),
        "sampling_time": _first_match(food_page, [r"采样日期[:：]?\s*([0-9:\- ]+)"]) or _first_match(pages_joined, [r"采样日期[:：]?\s*([0-9:\- ]+)"]),
        "receive_time": _first_match(food_page, [r"接收时间[:：]?\s*([0-9:\- ]+)"]) or _first_match(pages_joined, [r"接收时间[:：]?\s*([0-9:\- ]+)"]),
        "report_time_ige": _first_match(ige_page, [r"报告时间[:：]?\s*([0-9:\- ]+)"]),
        "report_time_food": _last_match(food_report_text, [r"报告时间[:：]?\s*([0-9:\- ]+)"]),
        "detector": _first_match(food_page, [r"检测者[:：]?\s*([^\s]*)"]) or _first_match(immune_page, [r"检测者[:：]?\s*([^\s]*)"]),
        "reviewer": _first_match(food_page, [r"审核者[:：]?\s*([^\s]*)"]) or _first_match(immune_page, [r"审核者[:：]?\s*([^\s]*)"]),
        "approver": _first_match(food_page, [r"批准人[:：]?\s*([^\s]*)"]) or _first_match(immune_page, [r"批准人[:：]?\s*([^\s]*)"]),
        "interpretation_text": "",
    }
    return payload


def _find_p11_page(page_texts: list[str], predicate: Callable[[str], bool], *, fallback: str) -> str:
    for page_text in page_texts:
        if predicate(str(page_text or "")):
            return str(page_text or "")
    return fallback


def _normalize_payload_test_results(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    food_items: list[dict[str, Any]] = []
    igg_items: list[dict[str, Any]] = []
    ige_items: list[dict[str, Any]] = []
    for section in payload.get("test_results", []):
        if not isinstance(section, dict):
            continue
        section_name = str(section.get("section") or "")
        items = section.get("items", [])
        if not isinstance(items, list):
            continue
        if "IgG" in section_name:
            for item in items:
                if isinstance(item, dict):
                    igg_items.append(
                        {
                            "test_name": str(item.get("test_name") or ""),
                            "result": str(item.get("result") or ""),
                            "flag": str(item.get("flag") or ""),
                            "reference_range": str(item.get("reference_range") or ""),
                            "unit": str(item.get("unit") or ""),
                            "method": str(item.get("method") or ""),
                        }
                    )
        elif "IgE" in section_name or "总IgE" in section_name:
            for item in items:
                if isinstance(item, dict):
                    ige_items.append(
                        {
                            "test_name": str(item.get("test_name") or "总IgE"),
                            "result": str(item.get("result") or ""),
                            "flag": str(item.get("flag") or ""),
                            "reference_range": str(item.get("reference_range") or ""),
                            "unit": str(item.get("unit") or ""),
                            "method": str(item.get("method") or ""),
                        }
                    )
        elif "食物不耐受" in section_name:
            for item in items:
                if not isinstance(item, dict):
                    continue
                food_name = str(item.get("name") or "")
                code = _food_code_from_name(food_name)
                food_items.append(
                    {
                        "index": int(item.get("index") or 0),
                        "name": food_name,
                        "code": code,
                        "result": _normalize_food_result(str(item.get("result") or "")),
                        "reference": str(item.get("reference") or "阴性"),
                        "flag": str(item.get("flag") or ""),
                    }
                )
    if not food_items:
        food_items = _extract_food_items("")
    return {"food_items": food_items, "igg_items": igg_items, "ige_items": ige_items}


def _extract_immune_items(full_text: str, names: list[str]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for name in names:
        line_pattern = rf"{re.escape(name)}\s+([0-9.]+)\s*([↑↓\+\-]?)\s+([^\n]+)"
        line_match = re.search(line_pattern, full_text, re.IGNORECASE)
        if not line_match:
            continue
        tail = line_match.group(3)
        ref_match = re.search(r"([0-9.]+\s*(?:--|[-~—])+?\s*[0-9.]+)", tail)
        unit_match = re.search(r"(μg/mL|ug/mL|IU/mL|mIU/mL|ng/mL|pg/mL)", tail, re.IGNORECASE)
        method = tail.split()[0] if tail.split() else ""
        items.append(
            {
                "test_name": name,
                "result": line_match.group(1).strip(),
                "flag": (line_match.group(2) or "").strip(),
                "reference_range": ref_match.group(1).replace(" ", "") if ref_match else "",
                "unit": unit_match.group(1) if unit_match else "",
                "method": method,
            }
        )
    return items


def _extract_food_items(text: str) -> list[dict[str, Any]]:
    parsed_items = _extract_food_result_rows(text)
    if parsed_items:
        return parsed_items

    items: list[dict[str, Any]] = []
    normalized = text.replace("\r", "\n")
    for index, name, code in P11_FOOD_CODES:
        pattern = rf"{index}\s+{re.escape(name)}\s+([^\s]+)"
        match = re.search(pattern, normalized)
        result = _normalize_food_result(match.group(1)) if match else "待复核"
        items.append(
            {
                "index": index,
                "name": name,
                "code": code,
                "result": result,
                "reference": "阴性",
                "flag": "",
            }
        )
    return items


def _extract_food_result_rows(text: str) -> list[dict[str, Any]]:
    normalized = str(text or "").replace("\r", "\n")
    rows = _extract_food_result_row_matches(
        normalized,
        re.compile(
            r"(?m)^\s*(?P<index>[1-9]|[1-3]\d|4[0-2])\s+"
            r"(?P<name>[\u4e00-\u9fffA-Za-z（）()·]{1,18})\s+"
            r"(?P<result>弱阳性|阳性|阴性|[+＋\-－±])\s+"
            r"(?P<reference>弱阳性|阳性|阴性|[+＋\-－±]|[^\s]+)"
            r"(?:\s+(?P<flag>[↑↓+\-±＋－高低异常]*))?\s*$"
        ),
    )
    if len(rows) < 20:
        compact = re.sub(r"\s+", " ", normalized)
        rows = _extract_food_result_row_matches(
            compact,
            re.compile(
                r"(?:^|\s)(?P<index>[1-9]|[1-3]\d|4[0-2])\s+"
                r"(?P<name>[\u4e00-\u9fffA-Za-z（）()·]{1,18})\s+"
                r"(?P<result>弱阳性|阳性|阴性|[+＋\-－±])\s+"
                r"(?P<reference>弱阳性|阳性|阴性|[+＋\-－±])"
                r"(?=\s+(?:[1-9]|[1-3]\d|4[0-2])\s+|\s+注[:：]|\s+报告声明|\s+网址[:：]|$)"
            ),
        )
    if len(rows) >= 20:
        return [rows[index] for index in sorted(rows)]
    return []


def _extract_food_result_row_matches(text: str, row_pattern: re.Pattern[str]) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    for match in row_pattern.finditer(text):
        index = _parse_index(match.group("index"))
        if index < 1 or index > 42 or index in rows:
            continue
        name = _text(match.group("name"))
        result = _normalize_food_result(_text(match.group("result")))
        reference = _text(match.group("reference") or "阴性")
        if not name or result == "待复核":
            continue
        rows[index] = {
            "index": index,
            "name": name,
            "code": _food_code_from_name(name),
            "result": result,
            "reference": _normalize_food_result(reference) if reference else "阴性",
            "flag": _text(match.groupdict().get("flag")),
        }
    return rows


def _food_item_to_test(item: dict[str, Any]) -> dict[str, Any]:
    result = str(item.get("result") or "")
    return {
        "page": 3,
        "index": int(item.get("index") or 0),
        "item_code": f"food_{item.get('code')}",
        "test_name": str(item.get("name") or ""),
        "result": result,
        "indicator": result if result not in {"阴性", "正常", ""} else "",
        "reference_range": str(item.get("reference") or "阴性"),
        "unit": "",
        "method": "酶联免疫法",
    }


def _immune_item_to_test(item: dict[str, Any], *, default_page: int) -> dict[str, Any]:
    name = str(item.get("test_name") or "")
    return {
        "page": int(item.get("page") or default_page),
        "item_code": _immune_code(name),
        "test_name": name,
        "result": str(item.get("result") or ""),
        "indicator": str(item.get("flag") or ""),
        "reference_range": str(item.get("reference_range") or ""),
        "unit": str(item.get("unit") or ""),
        "method": str(item.get("method") or ""),
    }


def _immune_code(name: str) -> str:
    lowered = name.lower()
    if lowered == "igg1":
        return "igg1"
    if lowered == "igg2":
        return "igg2"
    if lowered == "igg3":
        return "igg3"
    if lowered == "igg4":
        return "igg4"
    if "ige" in lowered or "总" in name:
        return "total_ige"
    return re.sub(r"[^a-z0-9]+", "_", lowered).strip("_") or "unknown"


def _food_code_from_name(name: str) -> str:
    alias = P11_FOOD_ALIASES.get(str(name).strip())
    if alias:
        return alias
    for _, food_name, code in [*P11_FOOD_CODES, *P11_FOOD_INTOLERANCE_42_CODES]:
        if food_name == name:
            return code
    return re.sub(r"[^a-z0-9]+", "_", name.lower()) or "unknown"


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _first_nonempty(values: list[str]) -> str:
    for value in values:
        if str(value or "").strip():
            return str(value).strip()
    return ""


def _last_nonempty(values: list[str]) -> str:
    for value in reversed(values):
        if str(value or "").strip():
            return str(value).strip()
    return ""


def _normalize_food_result(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return "待复核"
    if any(token in text for token in ["阴", "-", "NEG", "neg"]):
        return "阴性"
    if any(token in text for token in ["弱阳", "±", "卤"]):
        return "弱阳性"
    if any(token in text for token in ["阳", "+"]):
        return "阳性"
    return text


def _parse_age(value: Any) -> int | None:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else None


def _parse_index(value: Any) -> int:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else 0


def _first_match(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def _last_match(text: str, patterns: list[str]) -> str:
    value = ""
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            value = match.group(1).strip()
    return value


def _extract_between(text: str, start_label: str, end_labels: list[str]) -> str:
    compact = str(text or "")
    start_match = re.search(rf"{re.escape(start_label)}[:：]?\s*", compact)
    if not start_match:
        return ""
    start = start_match.end()
    end = len(compact)
    for label in end_labels:
        match = re.search(rf"{re.escape(label)}[:：]?", compact[start:])
        if match:
            end = min(end, start + match.start())
    value = compact[start:end].strip(" :：/\n\r\t")
    value = re.sub(r"\s{2,}", " ", value).strip()
    return value


def _normalize_diagnosis(value: str) -> str:
    text = str(value or "").strip()
    if not text or text in {"/", "-", "—"}:
        return "-"
    return text
