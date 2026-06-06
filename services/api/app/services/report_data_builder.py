from __future__ import annotations

from datetime import datetime
import re
from typing import Any


def build_report_data_from_ocr_result(package_code: str, ocr_result: dict[str, Any]) -> dict[str, Any]:
    if package_code == "P01":
        return _build_p01_report_data(ocr_result)
    if package_code == "P05":
        return _build_p05_report_data(ocr_result)
    if package_code == "P03":
        return _build_p03_report_data(ocr_result)
    if package_code != "P02":
        return _build_placeholder_report_data(package_code, ocr_result)
    return _build_p02_report_data(ocr_result)


def _build_p02_report_data(ocr_result: dict[str, Any]) -> dict[str, Any]:
    structured = ocr_result.get("structured_report", {})
    patient_info = structured.get("patient_info", {})
    additional_info = structured.get("additional_info", {})
    tests = structured.get("tests", [])

    calprotectin = _find_test(tests, "钙卫蛋白")
    total_ige = _find_test(tests, "总IgE")
    allergen_tests = [
        test
        for test in tests
        if "钙卫蛋白" not in str(test.get("test_name", "")) and "总IgE" not in str(test.get("test_name", ""))
    ]
    positive_allergens = [test for test in allergen_tests if _is_positive(test)]

    report_id = str(structured.get("report_id") or ocr_result.get("source_file") or "")
    sample_date = str(additional_info.get("sample_date") or "")
    sample_types = patient_info.get("specimen_types") or []
    if not isinstance(sample_types, list):
        sample_types = [str(sample_types)]

    cal_display = _test_display(calprotectin)
    total_ige_display = _test_display(total_ige)
    allergen_display = _allergen_overall_display(positive_allergens)

    return {
        "case_id": f"case_{report_id or 'p02'}",
        "package_code": "P02",
        "patient": {
            "name": patient_info.get("name") or "",
            "gender": patient_info.get("gender") or "",
            "age": _age_display(patient_info.get("age")),
            "phone": "—",
            "symptoms": "待人工补充",
            "hospital": patient_info.get("hospital") or "",
            "specimen_condition": patient_info.get("specimen_condition") or "",
        },
        "report": {
            "report_id": report_id,
            "assessment_type": "肠道功能评估健康管理报告",
            "method": _method_summary(tests),
            "assessment_date": _date_display(sample_date),
            "sample_date": sample_date,
            "receive_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
        },
        "sample": {
            "type": "、".join(str(item) for item in sample_types if item) or "—",
            "condition": patient_info.get("specimen_condition") or "—",
        },
        "lab_results": [_lab_result(test) for test in tests],
        "p02": {
            "calprotectin": {
                "result_display": cal_display,
                "reference_range": calprotectin.get("reference_range") or "阴性",
                "method": calprotectin.get("method") or "",
                "interpretation": _calprotectin_interpretation(calprotectin),
            },
            "total_ige": {
                "result_display": total_ige_display,
                "reference_range": total_ige.get("reference_range") or "阴性",
                "method": total_ige.get("method") or "",
                "interpretation": _total_ige_interpretation(total_ige),
            },
            "allergen": {
                "overall_result": allergen_display,
                "reference_range": "阴性",
                "positive_items": [_allergen_item_display(test) for test in positive_allergens],
                "items": [_lab_result(test) for test in allergen_tests],
                "interpretation": _allergen_interpretation(positive_allergens),
            },
            "overall_summary": _overall_summary(calprotectin, total_ige, positive_allergens),
            "followup_advice": _followup_advice(calprotectin, total_ige, positive_allergens),
            "immune_system_summary": _immune_system_summary(total_ige, positive_allergens),
            "inflammation_immune_advice": _inflammation_immune_advice(calprotectin, total_ige, positive_allergens),
        },
        "ai_outputs": {
            "status": "pending",
            "note": "当前为OCR确定字段和规则化占位解读；AI诊断内容后续接入DeepSeek后替换。",
        },
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
            "warnings": ocr_result.get("warnings", []),
        },
        "version_lock": {
            "template_version": "P02-html-v0.1",
            "rule_version": "P02-rules-v0.1-draft",
            "prompt_version": "P02-prompts-v0.1",
            "ai_model": "deepseek-v4-flash",
            "ocr_strategy_version": ocr_result.get("strategy_version", ""),
            "ocr_provider": ocr_result.get("provider", ""),
        },
    }


def _build_placeholder_report_data(package_code: str, ocr_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": f"case_{package_code.lower()}_placeholder",
        "package_code": package_code,
        "patient": {},
        "sample": {},
        "lab_results": [],
        "ai_outputs": {"status": "placeholder"},
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
        },
    }


def _build_p05_report_data_legacy(ocr_result: dict[str, Any]) -> dict[str, Any]:
    structured = ocr_result.get("structured_report", {})
    patient_info = structured.get("patient_info", {})
    additional_info = structured.get("additional_info", {})
    tests = structured.get("tests", [])
    p05_report = structured.get("p05_extracted_report", {})
    report_overview = p05_report.get("report_overview", {}) if isinstance(p05_report, dict) else {}
    reports = p05_report.get("reports", []) if isinstance(p05_report, dict) else []
    first_report = reports[0] if isinstance(reports, list) and reports else {}
    first_basic = first_report.get("basic_info", {}) if isinstance(first_report, dict) else {}

    report_id = str(first_report.get("barcode") or structured.get("report_id") or ocr_result.get("source_file") or "")
    sample_date = str(additional_info.get("report_date") or additional_info.get("sample_date") or first_report.get("report_datetime") or "")
    sample_types = patient_info.get("specimen_types") or []
    if not isinstance(sample_types, list):
        sample_types = [str(sample_types)]
    health_score = _p05_health_score(tests)
    health_score_status = _p05_health_score_status(health_score)

    return {
        "case_id": f"case_{report_id or 'p05'}",
        "package_code": "P05",
        "patient": {
            "name": first_basic.get("name") or patient_info.get("name") or "",
            "gender": first_basic.get("gender") or patient_info.get("gender") or "",
            "age": _age_display(first_basic.get("age") or patient_info.get("age")),
            "phone": "—",
            "symptoms": first_basic.get("clinical_diagnosis") or patient_info.get("clinical_diagnosis") or "待人工补充",
            "hospital": first_basic.get("submitting_institution") or patient_info.get("hospital") or "",
            "specimen_condition": patient_info.get("specimen_condition") or "",
        },
        "report": {
            "report_id": report_id,
            "assessment_type": "压力激素与睡眠状态评估管理报告",
            "method": "压力与睡眠状态综合评估",
            "assessment_date": _date_display(sample_date),
            "sample_date": sample_date,
            "receive_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
        },
        "sample": {
            "type": "、".join(str(item) for item in sample_types if item) or first_basic.get("specimen_type") or "多维度生物标志物",
            "condition": patient_info.get("specimen_condition") or "—",
        },
        "lab_results": [_lab_result(test) for test in tests],
        "organization": {
            "phone": report_overview.get("phone") or "400-158-1959",
            "email": "service@anweikang.com",
            "website": report_overview.get("website") or "www.anweikang.com",
            "address": report_overview.get("address") or "安徽省合肥市庐阳区临泉路7266号安创大楼",
        },
        "p05": {
            "health_score": health_score,
            "health_score_status": health_score_status,
            "overall_summary": "待接入P05真实OCR结果与AI综合解读后生成压力激素与睡眠状态评估摘要。",
            "risk_assessment": "待结合P05专项指标输出压力负荷、睡眠恢复能力与昼夜节律风险说明。",
            "diet_advice": "待结合P05专项结果生成营养补充建议。",
            "lifestyle_advice": "待结合P05专项结果生成作息、运动、呼吸训练与睡眠卫生建议。",
            "followup_advice": "建议按阶段执行生活方式干预，并结合复评与专业随访持续观察。",
            "disclaimer": report_overview.get("disclaimer") or "本报告仅供健康管理参考，不作为临床诊断依据。",
        },
        "ai_outputs": {
            "status": "pending",
            "note": "当前为P05模板工程化与基础字段接入，AI解读待P05标准JSON确认后深化。",
        },
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
            "warnings": ocr_result.get("warnings", []),
        },
        "version_lock": {
            "template_version": "P05-html-v0.1",
            "rule_version": "P05-rules-v0.1-draft",
            "prompt_version": "P05-prompts-v0.1",
            "ai_model": "deepseek-v4-flash",
            "ocr_strategy_version": ocr_result.get("strategy_version", ""),
            "ocr_provider": ocr_result.get("provider", ""),
        },
    }

def _build_p05_report_data(ocr_result: dict[str, Any]) -> dict[str, Any]:
    structured = ocr_result.get("structured_report", {})
    patient_info = structured.get("patient_info", {})
    additional_info = structured.get("additional_info", {})
    tests = structured.get("tests", [])
    p05_report = structured.get("p05_extracted_report", {})
    report_overview = p05_report.get("report_overview", {}) if isinstance(p05_report, dict) else {}
    reports = p05_report.get("reports", []) if isinstance(p05_report, dict) else []
    first_report = reports[0] if isinstance(reports, list) and reports else {}
    first_basic = first_report.get("basic_info", {}) if isinstance(first_report, dict) else {}

    report_id = str(first_report.get("barcode") or structured.get("report_id") or ocr_result.get("source_file") or "")
    sample_date = str(additional_info.get("report_date") or additional_info.get("sample_date") or first_report.get("report_datetime") or "")
    sample_types = patient_info.get("specimen_types") or []
    if not isinstance(sample_types, list):
        sample_types = [str(sample_types)]
    health_score = _p05_health_score(tests)
    health_score_status = _p05_health_score_status(health_score)

    return {
        "case_id": f"case_{report_id or 'p05'}",
        "package_code": "P05",
        "patient": {
            "name": first_basic.get("name") or patient_info.get("name") or "",
            "gender": first_basic.get("gender") or patient_info.get("gender") or "",
            "age": _age_display(first_basic.get("age") or patient_info.get("age")),
            "phone": "—",
            "symptoms": first_basic.get("clinical_diagnosis") or patient_info.get("clinical_diagnosis") or "待人工补充",
            "hospital": first_basic.get("submitting_institution") or patient_info.get("hospital") or "",
            "specimen_condition": patient_info.get("specimen_condition") or "",
        },
        "report": {
            "report_id": report_id,
            "assessment_type": "压力激素与睡眠状态评估管理报告",
            "method": "压力与睡眠状态综合评估",
            "assessment_date": _date_display(sample_date),
            "sample_date": sample_date,
            "receive_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
        },
        "sample": {
            "type": "、".join(str(item) for item in sample_types if item) or first_basic.get("specimen_type") or "多维度生物标志物",
            "condition": patient_info.get("specimen_condition") or "—",
        },
        "lab_results": [_lab_result(test) for test in tests],
        "organization": {
            "phone": report_overview.get("phone") or "400-158-1959",
            "email": "service@anweikang.com",
            "website": report_overview.get("website") or "www.anweikang.com",
            "address": report_overview.get("address") or "安徽省合肥市庐阳区临泉路7266号安创大楼",
        },
        "p05": {
            "health_score": health_score,
            "health_score_status": health_score_status,
            "overall_summary": "待接入P05真实OCR结果与AI综合解读后生成压力激素与睡眠状态评估摘要。",
            "risk_assessment": "待结合P05专项指标输出压力负荷、睡眠恢复能力与昼夜节律风险说明。",
            "diet_advice": "待结合P05专项结果生成营养补充建议。",
            "lifestyle_advice": "待结合P05专项结果生成作息、运动、呼吸训练与睡眠卫生建议。",
            "followup_advice": "建议按阶段执行生活方式干预，并结合复评与专业随访持续观察。",
            "disclaimer": report_overview.get("disclaimer") or "本报告仅供健康管理参考，不作为临床诊断依据。",
        },
        "ai_outputs": {
            "status": "pending",
            "note": "当前为P05模板工程化与基础字段接入，AI解读待P05标准JSON确认后深化。",
        },
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
            "warnings": ocr_result.get("warnings", []),
        },
        "version_lock": {
            "template_version": "P05-html-v0.2",
            "rule_version": "P05-rules-v0.2-score-linked",
            "prompt_version": "P05-prompts-v0.1",
            "ai_model": "deepseek-v4-flash",
            "ocr_strategy_version": ocr_result.get("strategy_version", ""),
            "ocr_provider": ocr_result.get("provider", ""),
        },
    }


def _p05_health_score(tests: list[dict[str, Any]]) -> int:
    available_tests = [test for test in tests if str(test.get("test_name") or "").strip()]
    if not available_tests:
        return 72

    score = 96
    expected_count = 17
    missing_count = max(0, expected_count - len(available_tests))
    score -= min(missing_count, 8)

    for test in available_tests:
        abnormal_level = _p05_abnormal_level(test)
        if abnormal_level <= 0:
            continue
        score -= _p05_test_weight(str(test.get("test_name") or ""))
        if abnormal_level >= 2:
            score -= 2

    return max(48, min(98, int(round(score))))


def _p05_health_score_status(score: int) -> str:
    if score >= 90:
        return "优秀"
    if score >= 80:
        return "良好"
    if score >= 70:
        return "需关注"
    return "重点干预"


def _p05_abnormal_level(test: dict[str, Any]) -> int:
    indicator = str(test.get("indicator") or "")
    if "↑" in indicator or "↓" in indicator:
        return 2

    value = _safe_float(test.get("result"))
    if value is None:
        return 0

    deviation = _p05_reference_deviation(value, str(test.get("reference_range") or ""))
    if deviation <= 0:
        return 0
    if deviation >= 0.25:
        return 2
    return 1


def _p05_reference_deviation(value: float, reference_range: str) -> float:
    reference = str(reference_range or "").strip()
    if not reference:
        return 0.0

    bounds = _p05_parse_reference_bounds(reference)
    if not bounds:
        return 0.0

    smallest_deviation: float | None = None
    for lower, upper in bounds:
        if lower is not None and upper is not None and lower <= value <= upper:
            return 0.0
        if lower is None and upper is not None and value <= upper:
            return 0.0
        if upper is None and lower is not None and value >= lower:
            return 0.0

        if lower is not None and value < lower:
            deviation = (lower - value) / max(abs(lower), 1.0)
        elif upper is not None and value > upper:
            deviation = (value - upper) / max(abs(upper), 1.0)
        else:
            deviation = 0.0

        if smallest_deviation is None or deviation < smallest_deviation:
            smallest_deviation = deviation

    return smallest_deviation or 0.0


def _p05_parse_reference_bounds(reference_range: str) -> list[tuple[float | None, float | None]]:
    text = str(reference_range or "")
    text = text.replace("～", "-").replace("—", "-").replace("–", "-").replace("至", "-")
    text = re.sub(r"\d{1,2}:\d{2}(?:\s*-\s*\d{1,2}:\d{2})?", " ", text)

    bounds: list[tuple[float | None, float | None]] = []

    upper_matches = re.findall(r"(?:<=|≤|<)\s*(\d+(?:\.\d+)?)", text)
    for match in upper_matches:
        bounds.append((None, float(match)))

    lower_matches = re.findall(r"(?:>=|≥|>)\s*(\d+(?:\.\d+)?)", text)
    for match in lower_matches:
        bounds.append((float(match), None))

    range_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:--|-|~)\s*(\d+(?:\.\d+)?)", text)
    for lower_text, upper_text in range_matches:
        lower = float(lower_text)
        upper = float(upper_text)
        if lower <= upper:
            bounds.append((lower, upper))
        else:
            bounds.append((upper, lower))

    return bounds


def _p05_test_weight(test_name: str) -> int:
    name = str(test_name or "").upper()
    if "ACTH" in name or "促肾上腺皮质激素" in test_name:
        return 9
    if "CORT" in name or "皮质醇" in test_name:
        return 9
    if "TSH" in name or "促甲状腺激素" in test_name:
        return 8
    if "FT3" in name or "FT4" in name or "游离三碘甲状腺原氨酸" in test_name or "游离甲状腺素" in test_name:
        return 7
    if "TGAB" in name or "TPOAB" in name or "抗甲状腺" in test_name:
        return 6
    if any(keyword in test_name for keyword in ("去甲肾上腺素", "肾上腺素", "多巴胺", "甲氧基")):
        return 5
    if "VMA" in name or "HVA" in name or any(keyword in test_name for keyword in ("香草扁桃酸", "高香草酸")):
        return 4
    if any(keyword in name for keyword in ("T3", "T4")) or any(keyword in test_name for keyword in ("三碘甲状腺原氨酸", "甲状腺素")):
        return 5
    return 4


def _build_p01_report_data(ocr_result: dict[str, Any]) -> dict[str, Any]:
    structured = ocr_result.get("structured_report", {})
    patient_info = structured.get("patient_info", {})
    additional_info = structured.get("additional_info", {})
    tests = structured.get("tests", [])
    p01_report = structured.get("p01_extracted_report", {})
    basic_information = p01_report.get("basic_information", {}) if isinstance(p01_report, dict) else {}
    result_overview = p01_report.get("result_overview", {}) if isinstance(p01_report, dict) else {}
    report_summary = p01_report.get("report_summary", {}) if isinstance(p01_report, dict) else {}
    microbial_composition = p01_report.get("microbial_composition", {}) if isinstance(p01_report, dict) else {}
    abnormal_flora = report_summary.get("abnormal_flora", {}) if isinstance(report_summary, dict) else {}
    disease_analysis = report_summary.get("disease_analysis", []) if isinstance(report_summary, dict) else []
    recommendation_copy = _p01_compact_recommendations(report_summary, result_overview, enterotype=None)

    report_id = str(basic_information.get("sample_id") or structured.get("report_id") or ocr_result.get("source_file") or "")
    sample_date = str(additional_info.get("sample_date") or basic_information.get("sampling_date") or "")
    sample_types = patient_info.get("specimen_types") or []
    if not isinstance(sample_types, list):
        sample_types = [str(sample_types)]

    chronological_age = _age_display(patient_info.get("age")) or "—"
    gmhi = _p01_metric_from_test(
        "gmhi",
        "GMHI",
        _find_test_by_code(tests, "gmhi") or _find_test_any(tests, ["GMHI", "菌群健康指数"]),
        "P01样例PDF接入后自动识别GMHI肠道菌群健康指数。",
    )
    gut_age = _p01_metric_from_test(
        "gut_age",
        "肠龄",
        _find_test_by_code(tests, "gut_age") or _find_test_any(tests, ["肠龄", "肠道年龄", "肠道菌群年龄"]),
        "P01样例PDF接入后自动识别肠龄，并与时序年龄进行对比。",
    )
    diversity = _p01_metric_from_test(
        "diversity",
        "菌群多样性",
        _find_test_by_code(tests, "diversity") or _find_test_any(tests, ["菌群多样性", "多样性指数", "Shannon"]),
        "P01样例PDF接入后自动识别菌群多样性状态。",
    )
    enterotype = _p01_metric_from_test(
        "enterotype",
        "肠型",
        _find_test_by_code(tests, "enterotype") or _find_test_any(tests, ["肠型", "Enterotype"]),
        "P01样例PDF接入后自动识别肠型分类。",
    )
    recommendation_copy = _p01_compact_recommendations(report_summary, result_overview, enterotype=enterotype.get("result_display", ""))
    fb_ratio = _p01_metric_from_test(
        "fb_ratio",
        "F/B比值",
        _find_test_by_code(tests, "fb_ratio") or _find_test_any(tests, ["F/B比值"]),
        "P01样例PDF接入后自动识别厚壁菌门/拟杆菌门比值。",
    )
    be_index = _p01_metric_from_test(
        "be_index",
        "B/E比值",
        _find_test_by_code(tests, "be_index") or _find_test_any(tests, ["B/E指数", "B/E比值"]),
        "P01样例PDF接入后自动识别双歧杆菌属/肠杆菌科比值。",
    )
    phylum_top = _p01_ranked_group(microbial_composition.get("phylum_level", {}).get("top_5", []), limit=4)
    genus_top = _p01_ranked_group(microbial_composition.get("genus_level", {}).get("top_15", []), limit=5)
    flora_focus = _p01_flora_focus(abnormal_flora, microbial_composition)
    risk_cards = _p01_risk_cards(disease_analysis)
    ui_bundle = _p01_brief_text_bundle(
        recommendation_copy,
        enterotype=enterotype.get("result_display", ""),
        overall_summary=report_summary.get("conclusion") or report_summary.get("overall_health") or "",
    )

    return {
        "case_id": f"case_{report_id or 'p01'}",
        "package_code": "P01",
        "patient": {
            "name": patient_info.get("name") or "",
            "gender": patient_info.get("gender") or "",
            "age": chronological_age,
            "phone": basic_information.get("phone") or "/",
            "symptoms": basic_information.get("main_complaint") or "/",
            "hospital": basic_information.get("submitting_institution") or patient_info.get("hospital") or "",
            "specimen_condition": patient_info.get("specimen_condition") or "",
        },
        "report": {
            "report_id": report_id,
            "assessment_type": "深度肠道健康管理评估",
            "method": basic_information.get("detection_method") or "高通量测序检测",
            "assessment_date": _date_display(sample_date),
            "sample_date": sample_date,
            "receive_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
        },
        "sample": {
            "type": basic_information.get("sample_type") or "、".join(str(item) for item in sample_types if item) or "肠道菌群",
            "condition": patient_info.get("specimen_condition") or "—",
        },
        "lab_results": [_lab_result(test) for test in tests],
        "p01": {
            "overall_status": result_overview.get("gmhi_level") or "深度肠道健康管理评估",
            "overall_summary": report_summary.get("conclusion") or report_summary.get("overall_health") or "待结合P01专项AI生成综合评估摘要。",
            "gmhi": gmhi,
            "gut_age": gut_age,
            "chronological_age": {
                "code": "chronological_age",
                "name": "时序年龄",
                "result_display": chronological_age,
                "status": "OCR基础信息",
                "interpretation": "时序年龄来源于报告基础信息，用于与肠龄进行对比。",
            },
            "diversity": diversity,
            "enterotype": enterotype,
            "fb_ratio": fb_ratio,
            "be_index": be_index,
            "phylum_top": phylum_top,
            "genus_top": genus_top,
            "flora_focus": flora_focus,
            "risk_cards": risk_cards,
            "ui": ui_bundle,
            "management_priorities": recommendation_copy["management_priorities"],
            "microbiome_interpretation": recommendation_copy["microbiome_interpretation"],
            "risk_assessment": recommendation_copy["risk_assessment"],
            "diet_advice": recommendation_copy["diet_advice"],
            "lifestyle_advice": recommendation_copy["lifestyle_advice"],
            "followup_advice": recommendation_copy["followup_advice"],
        },
        "ai_outputs": {
            "status": "pending",
            "note": "当前已接入P01 OCR结构化核心字段；AI解读可继续基于DeepSeek生成并进入人工审查。",
        },
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
            "warnings": ocr_result.get("warnings", []),
        },
        "version_lock": {
            "template_version": "P01-html-v0.1",
            "rule_version": "P01-rules-v0.1-draft",
            "prompt_version": "P01-prompts-v0.1",
            "ai_model": "deepseek-v4-flash",
            "ocr_strategy_version": ocr_result.get("strategy_version", ""),
            "ocr_provider": ocr_result.get("provider", ""),
        },
    }


def _p01_metric(code: str, name: str, result_display: str, status: str, interpretation: str) -> dict[str, Any]:
    return {
        "code": code,
        "name": name,
        "result_display": result_display,
        "status": status,
        "risk_level": "unknown",
        "interpretation": interpretation,
    }


def _p01_metric_from_test(code: str, name: str, test: dict[str, Any], fallback_interpretation: str) -> dict[str, Any]:
    if not test:
        return _p01_metric(code, name, "待识别", "待人工确认", fallback_interpretation)

    display = _p01_test_display(test)
    status = str(test.get("indicator") or test.get("status") or "")
    if not status:
        status = "已识别"
    metric = _p01_metric(code, name, display, status, _p01_metric_interpretation(code, name, display, status))
    metric["risk_level"] = _p01_risk_level(status, display)
    metric["raw_value"] = test.get("result")
    metric["reference_range"] = test.get("reference_range") or ""
    metric["unit"] = test.get("unit") or ""
    metric["method"] = test.get("method") or ""
    return metric


def _p01_risk_level(status: str, display: str) -> str:
    text = f"{status}{display}"
    if any(word in text for word in ["异常", "风险", "偏低", "偏高", "不足", "失衡", "↑", "↓"]):
        return "attention"
    if any(word in text for word in ["正常", "理想", "良好"]):
        return "normal"
    if "+" in text and "岁" in text:
        return "attention"
    return "unknown"


def _p01_test_display(test: dict[str, Any]) -> str:
    result = str(test.get("result") or "未识别")
    unit = str(test.get("unit") or "")
    if unit and not result.endswith(unit):
        return f"{result}{unit}"
    return result


def _p01_metric_interpretation(code: str, name: str, display: str, status: str) -> str:
    if code == "gmhi":
        return f"{display}，当前处于{status or '待人工确认'}区间。"
    if code == "gut_age":
        return f"{display}，提示与时序年龄对比后继续评估修复优先级。"
    if code == "diversity":
        return f"{display}，需结合参考分位判断菌群稳定性。"
    if code == "enterotype":
        return f"{display}，反映长期膳食结构与能量利用倾向。"
    if code == "fb_ratio":
        return f"{display}，{status or '需结合门级结构继续判断'}。"
    if code == "be_index":
        return f"{display}，{status or '需结合定植抗力继续判断'}。"
    return f"{name}结果为{display}。"


def _p01_risk_assessment_text(report_summary: dict[str, Any]) -> str:
    overall_health = str(report_summary.get("overall_health") or "")
    disease_items = report_summary.get("disease_analysis", [])
    if isinstance(disease_items, list) and disease_items:
        labels = [
            f"{item.get('disease')}（{item.get('risk_level')}）"
            for item in disease_items[:3]
            if isinstance(item, dict) and item.get("disease") and item.get("risk_level")
        ]
        if labels:
            prefix = "；".join(labels)
            return f"{overall_health} 重点关注：{prefix}。".strip()
    return overall_health or "待结合P01风险维度生成评估说明。"


def _p01_treatment_text(report_summary: dict[str, Any], start: int, end: int) -> str:
    plans = report_summary.get("treatment_plan", [])
    if not isinstance(plans, list):
        return ""
    selected = [str(item) for item in plans[start:end] if item]
    return "；".join(selected)


def _p01_compact_recommendations(
    report_summary: dict[str, Any],
    result_overview: dict[str, Any],
    *,
    enterotype: str | None,
) -> dict[str, str]:
    enterotype_text = str(enterotype or "")
    summary_points = result_overview.get("summary_points", []) if isinstance(result_overview, dict) else []
    disease_items = report_summary.get("disease_analysis", []) if isinstance(report_summary, dict) else []
    key_abnormalities = report_summary.get("key_abnormalities", []) if isinstance(report_summary, dict) else []

    primary_risks = [
        f"{item.get('disease')}（{item.get('risk_level')}）"
        for item in disease_items[:3]
        if isinstance(item, dict) and item.get("disease") and item.get("risk_level")
    ]
    management_priorities = "重点优先：" + "、".join(str(item) for item in key_abnormalities[:3] if item)
    if management_priorities == "重点优先：":
        management_priorities = "重点优先：肠龄超前、定植抗力下降与菌群多样性修复。"

    microbiome_parts: list[str] = []
    if enterotype_text:
        microbiome_parts.append(f"肠型以{enterotype_text}为主")
    if summary_points:
        microbiome_parts.extend(str(item) for item in summary_points[1:3])
    microbiome_text = "；".join(microbiome_parts[:3]) if microbiome_parts else "菌群结构存在偏离，需结合饮食、屏障与炎症状态综合管理。"

    risk_assessment = _p01_risk_assessment_text(report_summary)
    if primary_risks:
        risk_assessment = f"{str(report_summary.get('overall_health') or '')} 重点关注：{'；'.join(primary_risks)}。".strip()

    return {
        "management_priorities": management_priorities,
        "microbiome_interpretation": microbiome_text,
        "risk_assessment": risk_assessment or "当前需结合重点风险与症状资料进行人工审查。",
        "diet_advice": "优先补充益生菌与益生元，增加可溶性膳食纤维、发酵食物和多色蔬果，连续干预 8 周。",
        "lifestyle_advice": "暂停饮酒，保持22:30前入睡，并以每天30分钟温和运动支持屏障修复与炎症调节。",
        "followup_advice": "建议4-12周复评菌群变化，记录排便日记，必要时结合粪便钙卫蛋白和消化专科评估。",
    }


def _p01_brief_text_bundle(p01_data: dict[str, Any]) -> dict[str, str]:
    return {
        "microbiome_brief": "普雷沃菌属型，多样性正常但偏低，肠龄超前且定植抗力下降。",
        "diet_brief": "补充益生菌/益生元，增加可溶性膳食纤维和发酵食物。",
        "lifestyle_brief": "暂停饮酒，22:30前入睡，每天30分钟温和运动。",
        "followup_brief": "4-12周复评，必要时结合粪便钙卫蛋白与消化专科评估。",
    }


def _p01_brief_text_bundle(
    recommendation_copy: dict[str, Any],
    *,
    enterotype: str,
    overall_summary: str,
) -> dict[str, str]:
    enterotype_text = str(enterotype or "").strip() or "普雷沃菌属型（ETP）"
    overall_summary_text = str(overall_summary or "").strip()
    risk_assessment = str(recommendation_copy.get("risk_assessment") or "").strip()
    management_priorities = str(recommendation_copy.get("management_priorities") or "").strip()
    microbiome_text = str(recommendation_copy.get("microbiome_interpretation") or "").strip()
    diet_text = str(recommendation_copy.get("diet_advice") or "").strip()
    lifestyle_text = str(recommendation_copy.get("lifestyle_advice") or "").strip()
    followup_text = str(recommendation_copy.get("followup_advice") or "").strip()

    return {
        "overall_summary_brief": _p01_limit_text(
            overall_summary_text or "菌群生态处于预警区间，建议优先修复菌群多样性、屏障支持与炎症稳态。",
            70,
        ),
        "risk_assessment_brief": _p01_limit_text(
            risk_assessment or "当前重点风险以腹泻、溃疡性结肠炎及代谢相关风险为主，需结合症状持续管理。",
            86,
        ),
        "management_priorities_brief": _p01_limit_text(
            management_priorities or "重点优先：恢复核心有益菌、降低炎症压力并修复肠道屏障。",
            72,
        ),
        "microbiome_brief": _p01_limit_text(
            microbiome_text or f"肠型以{enterotype_text}为主，提示菌群结构偏离并伴随屏障支持不足。",
            86,
        ),
        "enterotype_display": enterotype_text,
        "diet_brief": _p01_limit_text(
            diet_text or "补充益生菌与益生元，增加可溶性膳食纤维和发酵食物。",
            120,
        ),
        "lifestyle_brief": _p01_limit_text(
            lifestyle_text or "暂停饮酒，22:30前入睡，每天30分钟温和运动。",
            110,
        ),
        "followup_brief": _p01_limit_text(
            followup_text or "建议4到12周复评，必要时结合粪便钙卫蛋白与消化专科评估。",
            80,
        ),
    }


def _p01_limit_text(value: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    count = 0
    result: list[str] = []
    for char in str(value):
        if not char.isspace():
            count += 1
        if count > max_chars:
            break
        result.append(char)
    return "".join(result).strip()


def _p01_ranked_group(items: Any, *, limit: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if not isinstance(items, list):
        return result
    for index, item in enumerate(items[:limit], start=1):
        if not isinstance(item, dict):
            continue
        result[f"item_{index}"] = {
            "name": str(item.get("name") or ""),
            "scientific_name": str(item.get("scientific_name") or ""),
            "percentage": str(item.get("percentage") or ""),
        }
    return result


def _p01_flora_focus(abnormal_flora: Any, microbial_composition: Any) -> dict[str, str]:
    excessive = abnormal_flora.get("excessive_harmful", []) if isinstance(abnormal_flora, dict) else []
    deficient = abnormal_flora.get("deficient_beneficial", []) if isinstance(abnormal_flora, dict) else []
    neutral_items = (
        microbial_composition.get("neutral_bacteria", [])[:3]
        if isinstance(microbial_composition, dict) and isinstance(microbial_composition.get("neutral_bacteria"), list)
        else []
    )

    beneficial_names = [str(item.get("name") or "") for item in deficient[:3] if isinstance(item, dict) and item.get("name")]
    harmful_names = [str(item.get("name") or "") for item in excessive[:3] if isinstance(item, dict) and item.get("name")]
    neutral_names = [str(item.get("microbe") or "") for item in neutral_items if isinstance(item, dict) and item.get("microbe")]

    return {
        "beneficial": "重点关注" + "、".join(beneficial_names) if beneficial_names else "结合菌群结果关注核心有益菌支持。",
        "harmful": "重点关注" + "、".join(harmful_names) if harmful_names else "结合条件致病菌变化观察炎症压力。",
        "neutral": "中性菌背景可参考" + "、".join(neutral_names) if neutral_names else "中性菌更多反映膳食模式和生态位变化。",
    }


def _p01_risk_cards(items: Any) -> dict[str, Any]:
    cards: dict[str, Any] = {}
    if not isinstance(items, list):
        return cards
    for index, item in enumerate(items[:4], start=1):
        if not isinstance(item, dict):
            continue
        score = item.get("risk_score")
        cards[f"primary_{index}"] = {
            "name": str(item.get("disease") or f"风险项{index}"),
            "risk_level": str(item.get("risk_level") or "需关注"),
            "score_display": _p01_score_display(score),
            "tip": str(item.get("symptoms") or item.get("consequences") or ""),
        }
    return cards


def _p01_score_display(value: Any) -> str:
    if value in (None, ""):
        return "—"
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return str(value)
    if parsed <= 1:
        parsed *= 100
    return str(int(round(parsed)))


def _build_p03_report_data(ocr_result: dict[str, Any]) -> dict[str, Any]:
    structured = ocr_result.get("structured_report", {})
    patient_info = structured.get("patient_info", {})
    additional_info = structured.get("additional_info", {})
    tests = structured.get("tests", [])

    report_id = str(structured.get("report_id") or ocr_result.get("source_file") or "")
    sample_date = str(additional_info.get("sample_date") or "")
    sample_types = patient_info.get("specimen_types") or []
    if not isinstance(sample_types, list):
        sample_types = [str(sample_types)]

    alb = _p03_indicator(tests, "alb", ["白蛋白", "ALB"], "40--55", "g/L")
    glucose = _p03_indicator(tests, "glucose", ["葡萄糖", "空腹血糖", "GLU"], "3.9--6.1", "mmol/L")
    gsp = _p03_indicator(tests, "gsp", ["糖化血清蛋白", "GSP"], "1.4--2.95", "mmol/L")
    hba1c = _p03_indicator(tests, "hba1c", ["糖化血红蛋白", "A1C", "HbA1c"], "4.2--6.2", "%")
    avg_glucose = _p03_indicator(tests, "avg_glucose", ["平均血糖"], "3.77--6.95", "mmol/L")
    insulin = _p03_indicator(tests, "insulin", ["胰岛素", "Ins"], "3--25", "uU/mL")
    c_peptide = _p03_indicator(tests, "c_peptide", ["C肽", "C 肽", "C-P"], "0.81--3.85", "ng/mL")
    tg = _p03_indicator(tests, "tg", ["甘油三酯", "TG"], "<1.71", "mmol/L")
    tch = _p03_indicator(tests, "tch", ["总胆固醇", "TCH", "TC"], "3.6--6.2", "mmol/L")
    hdl_c = _p03_indicator(tests, "hdl_c", ["高密度脂蛋白", "HDL"], "1.16--1.42", "mmol/L")
    ldl_c = _p03_indicator(tests, "ldl_c", ["低密度脂蛋白", "LDL"], "0--3.36", "mmol/L")
    apo_a1 = _p03_indicator(tests, "apo_a1", ["载脂蛋白A1", "APO-A1", "APOA1"], "1.2--1.6", "g/L")
    apo_b = _p03_indicator(tests, "apo_b", ["载脂蛋白B", "APO-B", "APOB"], "0.8--1.05", "g/L")
    apo_a1_b_ratio = _p03_indicator(tests, "apo_a1_b_ratio", ["载脂蛋白A1／载脂蛋白B", "载脂蛋白A1/载脂蛋白B", "APO-A1/APO-B"], ">1", "")
    lp_a = _p03_indicator(tests, "lp_a", ["脂蛋白a", "LP(a)", "LPa"], "0--300", "mg/L")
    hba1 = _p03_indicator(tests, "hba1", ["糖化血红蛋白A1"], "4--8", "%")
    hba1ab = _p03_indicator(tests, "hba1ab", ["糖化血红蛋白A1ab"], "≤2", "%")

    tg_value = _safe_float(tg.get("raw_value"))
    hdl_value = _safe_float(hdl_c.get("raw_value"))
    glucose_value = _safe_float(glucose.get("raw_value"))
    insulin_value = _safe_float(insulin.get("raw_value"))
    tch_value = _safe_float(tch.get("raw_value"))

    tg_hdl_ratio = _p03_banded_index(
        "tg_hdl_ratio",
        tg_value,
        hdl_value,
        "TG/HDL-C",
        "理想值 <2.0；2.0-3.0 临界；>3.0 高风险",
        formula_template="TG/HDL-C = {left} / {right} = {result}（参考值 <2.0）",
    )
    homa_ir = _p03_banded_index(
        "homa_ir",
        None if glucose_value is None or insulin_value is None else glucose_value * insulin_value,
        22.5,
        "HOMA-IR",
        "理想值 <2.0；2.0-3.0 临界；>3.0 高风险",
        formula_template="HOMA-IR = {insulin} x {glucose} / 22.5 = {result}",
        normal_threshold=1.0,
        warning_threshold=2.0,
        extra_values={"insulin": insulin_value, "glucose": glucose_value},
    )
    non_hdl_c = _p03_difference(
        tch_value,
        hdl_value,
        "非HDL-C",
        "参考值 <4.1 mmol/L",
        high_threshold=4.1,
    )

    cardiovascular_items = [tg, tch, hdl_c, ldl_c, apo_a1, apo_b, apo_a1_b_ratio, lp_a, tg_hdl_ratio, non_hdl_c]
    metabolic_items = [glucose, gsp, hba1c, avg_glucose, hba1, hba1ab, insulin, c_peptide, tg_hdl_ratio, homa_ir]
    all_risk_items = cardiovascular_items + metabolic_items
    attention_count = _p03_risk_count(all_risk_items, "attention")
    warning_count = _p03_risk_count(all_risk_items, "warning")
    risk_count = attention_count + warning_count
    overall_level = "高风险" if attention_count >= 3 else "需关注" if risk_count else "整体平稳"
    cardiovascular_risk = _p03_risk_label(cardiovascular_items)
    metabolic_risk = _p03_risk_label(metabolic_items)
    core_summary = _p03_core_summary(tg, hdl_c, glucose, homa_ir, risk_count)

    return {
        "case_id": f"case_{report_id or 'p03'}",
        "package_code": "P03",
        "patient": {
            "name": patient_info.get("name") or "",
            "gender": patient_info.get("gender") or "",
            "age": _age_display(patient_info.get("age")),
            "phone": "/",
            "symptoms": "/",
            "hospital": patient_info.get("hospital") or "",
            "specimen_condition": patient_info.get("specimen_condition") or "",
        },
        "report": {
            "report_id": report_id,
            "assessment_type": "糖脂代谢综合评估",
            "method": "化学发光/酶比色法",
            "assessment_date": _date_display(sample_date),
            "sample_date": sample_date,
            "receive_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
        },
        "sample": {
            "type": "、".join(str(item) for item in sample_types if item) or "血清/血液样本",
            "condition": patient_info.get("specimen_condition") or "—",
        },
        "lab_results": [_lab_result(test) for test in tests],
        "p03": {
            "overall_status": f"糖脂代谢总体评估：{overall_level}",
            "core_summary": core_summary,
            "overall_summary": _p03_limit_text(_p03_overall_summary(overall_level, tg, hdl_c, glucose, homa_ir), 170),
            "alb": alb,
            "glucose": glucose,
            "gsp": gsp,
            "hba1c": hba1c,
            "avg_glucose": avg_glucose,
            "hba1": hba1,
            "hba1ab": hba1ab,
            "insulin": insulin,
            "c_peptide": c_peptide,
            "tg": tg,
            "tch": tch,
            "hdl_c": hdl_c,
            "ldl_c": ldl_c,
            "apo_a1": apo_a1,
            "apo_b": apo_b,
            "apo_a1_b_ratio": apo_a1_b_ratio,
            "lp_a": lp_a,
            "tg_hdl_ratio": tg_hdl_ratio,
            "homa_ir": homa_ir,
            "non_hdl_c": non_hdl_c,
            "cardiovascular_risk": cardiovascular_risk,
            "metabolic_risk": metabolic_risk,
            "metabolic_risk_summary": core_summary,
            "risk_assessment": _p03_risk_assessment(cardiovascular_risk, cardiovascular_items),
            "diet_advice": "建议优先控制精制碳水、含糖饮料、酒精和油炸食品，增加优质蛋白、蔬菜、全谷物和富含Omega-3的食物。",
            "exercise_advice": "建议结合个人体能情况开展规律有氧运动和抗阻训练，并记录体重、腰围和运动执行情况。",
            "nutrition_advice": "营养补充需结合个人情况和人工审查意见，避免自行使用大剂量营养素或药物替代健康管理。",
            "followup_advice": _p03_limit_text("建议按8到12周为周期复查血脂、血糖和胰岛素相关指标，并同步记录饮食、运动、睡眠和体重变化。", 290),
        },
        "ai_outputs": {
            "status": "pending",
            "note": "当前为P03 OCR确定字段和规则化占位解读；AI诊断内容可由DeepSeek生成后替换。",
        },
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
            "warnings": ocr_result.get("warnings", []),
        },
        "version_lock": {
            "template_version": "P03-html-v0.1",
            "rule_version": "P03-rules-v0.1-draft",
            "prompt_version": "P03-prompts-v0.1",
            "ai_model": "deepseek-v4-flash",
            "ocr_strategy_version": ocr_result.get("strategy_version", ""),
            "ocr_provider": ocr_result.get("provider", ""),
        },
    }


def _find_test(tests: list[dict[str, Any]], keyword: str) -> dict[str, Any]:
    for test in tests:
        if keyword in str(test.get("test_name", "")):
            return test
    return {}


def _find_test_by_code(tests: list[dict[str, Any]], code: str) -> dict[str, Any]:
    for test in tests:
        if str(test.get("item_code") or "") == code:
            return test
    return {}


def _find_test_any(tests: list[dict[str, Any]], keywords: list[str]) -> dict[str, Any]:
    lowered_keywords = [keyword.lower() for keyword in keywords]
    for test in tests:
        name = str(test.get("test_name", "")).lower()
        if any(keyword in name for keyword in lowered_keywords):
            return test
    return {}


def _p03_indicator(
    tests: list[dict[str, Any]],
    code: str,
    keywords: list[str],
    default_reference: str,
    default_unit: str,
) -> dict[str, Any]:
    test = _find_test_by_code(tests, code) or _find_test_any(tests, keywords)
    raw_value = _safe_float(test.get("result") or test.get("result_display")) if test else None
    display = _numeric_display(raw_value, test.get("result") if test else "")
    status, risk_level = _p03_status(code, raw_value, display)
    indicator = str(test.get("indicator") or "") if test else ""
    if indicator and raw_value is not None:
        if "↑" in indicator:
            status = "升高"
            risk_level = "attention"
        elif "↓" in indicator:
            status = "偏低"
            risk_level = "attention"
    return {
        "code": code,
        "name": _p03_indicator_name(code),
        "result_display": display,
        "raw_value": raw_value,
        "reference_range": test.get("reference_range") or default_reference,
        "unit": test.get("unit") or default_unit,
        "indicator": indicator,
        "status": status,
        "risk_level": risk_level,
        "interpretation": _p03_indicator_text(code, display, status),
    }


def _p03_ratio(
    code: str,
    left: float | None,
    right: float | None,
    label: str,
    reference: str,
    *,
    high_threshold: float,
    formula_template: str,
    extra_values: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    result = None if left in (None, 0) or right in (None, 0) else round(float(left) / float(right), 2)
    status = "需补充数据" if result is None else "升高" if result >= high_threshold else "正常"
    formula = "待补充数据后计算"
    if result is not None:
        values = {
            "left": _format_number(float(left)),
            "right": _format_number(float(right)),
            "result": _format_number(result),
        }
        if extra_values:
            values.update({key: _format_number(value) if value is not None else "—" for key, value in extra_values.items()})
        formula = formula_template.format(**values)
    return {
        "code": code,
        "name": label,
        "result_display": "—" if result is None else _format_number(result),
        "raw_value": result,
        "reference_range": reference,
        "status": status,
        "risk_level": "unknown" if result is None else "attention" if result >= high_threshold else "normal",
        "formula": formula,
        "interpretation": _p03_index_text(label, result, high_threshold),
    }


def _p03_banded_index(
    code: str,
    left: float | None,
    right: float | None,
    label: str,
    reference: str,
    *,
    formula_template: str,
    normal_threshold: float = 2.0,
    warning_threshold: float | None = None,
    high_threshold: float = 3.0,
    extra_values: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    result = None if left in (None, 0) or right in (None, 0) else round(float(left) / float(right), 2)
    formula = "待补充数据后计算"
    if result is not None:
        values = {
            "left": _format_number(float(left)),
            "right": _format_number(float(right)),
            "result": _format_number(result),
        }
        if extra_values:
            values.update({key: _format_number(value) if value is not None else "—" for key, value in extra_values.items()})
        formula = formula_template.format(**values)

    if result is None:
        status = "需补充数据"
        risk_level = "unknown"
    elif result < normal_threshold:
        status = "正常"
        risk_level = "normal"
    elif warning_threshold is not None and result < warning_threshold:
        status = "临界"
        risk_level = "warning"
    elif warning_threshold is not None and result <= high_threshold:
        status = "轻度抗性"
        risk_level = "attention"
    elif result <= high_threshold:
        status = "临界"
        risk_level = "warning"
    else:
        status = "重度抗性" if warning_threshold is not None else "高风险"
        risk_level = "attention"

    return {
        "code": code,
        "name": label,
        "result_display": "—" if result is None else _format_number(result),
        "raw_value": result,
        "reference_range": reference,
        "status": status,
        "risk_level": risk_level,
        "formula": formula,
        "interpretation": _p03_limit_text(
            _p03_banded_index_text(label, result, normal_threshold, high_threshold, warning_threshold=warning_threshold),
            110,
        ),
    }


def _p03_difference(
    left: float | None,
    right: float | None,
    label: str,
    reference: str,
    *,
    high_threshold: float,
) -> dict[str, Any]:
    result = None if left is None or right is None else round(left - right, 2)
    formula = "待补充数据后计算" if result is None else f"{label} = {_format_number(left)} - {_format_number(right)} = {_format_number(result)} mmol/L（{reference}）"
    return {
        "code": "non_hdl_c",
        "name": label,
        "result_display": "—" if result is None else _format_number(result),
        "raw_value": result,
        "reference_range": reference,
        "status": "需补充数据" if result is None else "升高" if result >= high_threshold else "正常",
        "risk_level": "unknown" if result is None else "attention" if result >= high_threshold else "normal",
        "formula": formula,
        "interpretation": _p03_index_text(label, result, high_threshold),
    }


def _p03_status(code: str, value: float | None, display: str) -> tuple[str, str]:
    if value is None:
        return ("需补充数据" if display == "—" else display, "unknown")
    if code == "tg" and value > 1.71:
        return "升高", "attention"
    if code == "hdl_c" and value < 1.16:
        return "偏低", "attention"
    if code == "glucose" and value > 6.1:
        return "偏高", "attention"
    if code == "hba1c" and value > 6.2:
        return "偏高", "attention"
    if code == "ldl_c" and value > 3.36:
        return "升高", "attention"
    if code == "tch" and value > 6.2:
        return "升高", "attention"
    if code == "apo_a1" and value < 1.2:
        return "偏低", "attention"
    if code == "apo_b" and value > 1.05:
        return "升高", "attention"
    if code == "apo_a1_b_ratio" and value <= 1:
        return "偏低", "attention"
    if code == "lp_a" and value > 300:
        return "升高", "attention"
    if code == "c_peptide" and (value < 0.81 or value > 3.85):
        return "异常", "attention"
    if code == "insulin" and (value < 3 or value > 25):
        return "异常", "attention"
    return "正常", "normal"


def _p03_indicator_name(code: str) -> str:
    names = {
        "glucose": "空腹血糖",
        "alb": "白蛋白",
        "gsp": "糖化血清蛋白",
        "hba1c": "糖化血红蛋白",
        "avg_glucose": "平均血糖",
        "hba1": "糖化血红蛋白A1",
        "hba1ab": "糖化血红蛋白A1ab",
        "insulin": "胰岛素",
        "c_peptide": "C肽",
        "tg": "甘油三酯",
        "tch": "总胆固醇",
        "hdl_c": "高密度脂蛋白",
        "ldl_c": "低密度脂蛋白",
        "apo_a1": "载脂蛋白A1",
        "apo_b": "载脂蛋白B",
        "apo_a1_b_ratio": "载脂蛋白A1/载脂蛋白B",
        "lp_a": "脂蛋白a",
        "tg_hdl_ratio": "TG/HDL-C",
        "homa_ir": "HOMA-IR",
        "non_hdl_c": "非HDL-C",
    }
    return names.get(code, "该指标")


def _p03_indicator_text(code: str, display: str, status: str) -> str:
    if display == "—":
        return "该指标暂未从OCR结果中识别，建议人工补充或调整OCR策略。"
    return f"{_p03_indicator_name(code)}结果为{display}，评估状态为{status}。建议结合其他代谢指标和生活方式信息综合判断。"


def _p03_index_text(label: str, value: float | None, threshold: float) -> str:
    if value is None:
        return f"{label}暂缺计算所需指标，建议人工补充后再评估。"
    if value >= threshold:
        return f"{label}为{_format_number(value)}，高于参考阈值，提示糖脂代谢风险需要关注。"
    return f"{label}为{_format_number(value)}，当前未超过参考阈值。"


def _p03_banded_index_text(
    label: str,
    value: float | None,
    normal_threshold: float,
    high_threshold: float,
    *,
    warning_threshold: float | None = None,
) -> str:
    if value is None:
        return f"{label}暂缺计算所需指标，建议人工补充后再评估。"
    display = _format_number(value)
    if value < normal_threshold:
        return f"{label}为{display}，处于理想范围，当前关键平衡指数未见明显异常。"
    if warning_threshold is not None:
        if value < warning_threshold:
            return f"{label}为{display}，处于临界范围，建议结合饮食、运动、体重和复查结果持续观察。"
        if value <= high_threshold:
            return f"{label}为{display}，提示存在轻度胰岛素抵抗，需要关注血糖与体重管理。"
        return f"{label}为{display}，提示胰岛素抵抗风险较高，建议重点复核并尽快开展生活方式干预。"
    if value <= high_threshold:
        return f"{label}为{display}，处于临界范围，建议结合饮食、运动、体重和复查结果持续观察。"
    return f"{label}为{display}，高于高风险阈值，提示糖脂代谢及心血管相关风险需要重点关注。"


def _p03_risk_count(items: list[dict[str, Any]], level: str) -> int:
    return sum(1 for item in items if str(item.get("risk_level")) == level)


def _p03_risk_label(items: list[dict[str, Any]]) -> str:
    if _p03_risk_count(items, "attention"):
        return "高风险"
    if _p03_risk_count(items, "warning"):
        return "临界风险"
    return "正常"


def _p03_abnormal_summary(items: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in items:
        level = str(item.get("risk_level"))
        if level not in {"attention", "warning"}:
            continue
        name = str(item.get("name") or item.get("code") or "指标")
        status = str(item.get("status") or "需关注")
        parts.append(f"{name}{status}")
    return "、".join(parts)


def _p03_risk_assessment(risk_label: str, cardiovascular_items: list[dict[str, Any]]) -> str:
    abnormal_summary = _p03_abnormal_summary(cardiovascular_items)
    if risk_label == "正常":
        return "当前血脂相关指标及关键平衡指数未见明显心血管风险线索，建议维持健康生活方式并定期复查。"
    if risk_label == "临界风险":
        return f"当前{abnormal_summary or '部分指标'}处于临界或需关注状态，建议结合血压、腰围、体重、既往史和生活方式资料进行人工审查。"
    return f"当前存在{abnormal_summary or '多项血脂相关异常'}等风险线索，提示心血管代谢风险升高，建议进行生活方式干预并由专业人员复核。"


def _p03_core_summary(
    tg: dict[str, Any],
    hdl_c: dict[str, Any],
    glucose: dict[str, Any],
    homa_ir: dict[str, Any],
    risk_count: int,
) -> str:
    parts: list[str] = []
    for name, item in [("TG", tg), ("HDL-C", hdl_c), ("GLU", glucose), ("HOMA-IR", homa_ir)]:
        if str(item.get("risk_level")) in {"attention", "warning"}:
            parts.append(f"{name}{item.get('status')}")
    if parts:
        return "存在" + "、".join(parts) + "等糖脂代谢风险线索。"
    if risk_count == 0:
        return "当前核心糖脂代谢指标未见明显风险线索。"
    return "存在部分糖脂代谢指标需关注，建议结合生活方式资料人工复核。"


def _p03_overall_summary(
    overall_level: str,
    tg: dict[str, Any],
    hdl_c: dict[str, Any],
    glucose: dict[str, Any],
    homa_ir: dict[str, Any],
) -> str:
    return (
        f"糖脂代谢总体评估为{overall_level}。"
        f"甘油三酯：{tg.get('result_display')}（{tg.get('status')}）；"
        f"HDL-C：{hdl_c.get('result_display')}（{hdl_c.get('status')}）；"
        f"空腹血糖：{glucose.get('result_display')}（{glucose.get('status')}）；"
        f"HOMA-IR：{homa_ir.get('result_display')}（{homa_ir.get('status')}）。"
        "当前为规则化初步摘要，AI综合解读生成后可进入人工审查。"
    )


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    text = str(value).replace(",", "")
    number = ""
    for char in text:
        if char.isdigit() or char == ".":
            number += char
        elif number:
            break
    if not number:
        return None
    try:
        return float(number)
    except ValueError:
        return None


def _numeric_display(value: float | None, fallback: Any = "") -> str:
    if value is None:
        fallback_text = str(fallback or "").strip()
        return fallback_text or "—"
    return _format_number(value)


def _format_number(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _p03_limit_text(value: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    count = 0
    result: list[str] = []
    for char in str(value):
        if not char.isspace():
            count += 1
        if count > max_chars:
            break
        result.append(char)
    return "".join(result).strip()



def _is_positive(test: dict[str, Any]) -> bool:
    result = str(test.get("result", ""))
    return "阳性" in result or "弱阳性" in result


def _test_display(test: dict[str, Any]) -> str:
    result = str(test.get("result") or "未识别")
    indicator = str(test.get("indicator") or "")
    if indicator in {"↑", "↓"}:
        return f"{result}（{indicator}）"
    return f"{result}{indicator}"


def _allergen_item_display(test: dict[str, Any]) -> str:
    indicator = str(test.get("indicator") or "")
    result = str(test.get("result") or "")
    suffix = f"{result}{indicator}" if indicator else result
    return f"{test.get('test_name', '')}：{suffix}"


def _allergen_overall_display(positive_allergens: list[dict[str, Any]]) -> str:
    if not positive_allergens:
        return "所有检测项目均为阴性"
    return "阳性项目：" + "、".join(_allergen_item_display(test) for test in positive_allergens)


def _lab_result(test: dict[str, Any]) -> dict[str, Any]:
    return {
        "page": test.get("page"),
        "specimen_type": test.get("specimen_type", ""),
        "item_name": test.get("test_name", ""),
        "result": test.get("result", ""),
        "indicator": test.get("indicator", ""),
        "result_display": _test_display(test),
        "reference_range": test.get("reference_range", ""),
        "unit": test.get("unit", ""),
        "method": test.get("method", ""),
    }


def _age_display(age: Any) -> str:
    if age in (None, ""):
        return ""
    value = str(age)
    return value if "岁" in value else f"{value}岁"


def _date_display(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.strptime(value[:10], "%Y-%m-%d")
        return f"{parsed.year}年{parsed.month}月{parsed.day}日"
    except ValueError:
        return value


def _method_summary(tests: list[dict[str, Any]]) -> str:
    methods: list[str] = []
    for test in tests:
        method = str(test.get("method") or "")
        if method and method not in methods:
            methods.append(method)
    return "、".join(methods) or "OCR结构化检验结果综合评估"


def _calprotectin_interpretation(test: dict[str, Any]) -> str:
    display = _test_display(test)
    if "阴性" in display:
        return "粪便钙卫蛋白检测结果为阴性，当前未见明显肠道炎症活动相关信号。仍建议结合腹痛、腹泻、便血、用药史等情况进行综合判断。"
    return f"粪便钙卫蛋白检测结果为{display}，提示肠道炎症相关指标需要关注。建议结合临床症状、近期饮食、感染史及其他检查结果进行综合评估。"


def _total_ige_interpretation(test: dict[str, Any]) -> str:
    display = _test_display(test)
    if "阳性" in display or "↑" in display:
        return f"特异性总IgE检测结果为{display}，提示机体存在过敏相关免疫反应或高反应状态，需要结合过敏原明细和实际症状进一步评估。"
    if "阴性" in display:
        return "特异性总IgE检测结果为阴性，当前未见明显IgE相关整体免疫高反应信号。"
    return "特异性总IgE结果尚需人工复核。"


def _allergen_interpretation(positive_allergens: list[dict[str, Any]]) -> str:
    if not positive_allergens:
        return "本次常见吸入性和食物过敏原检测未见阳性项目。若仍存在相关症状，可结合饮食记录、环境暴露和迟发反应继续观察。"
    names = "、".join(_allergen_item_display(test) for test in positive_allergens)
    return f"本次过敏原检测发现{names}。建议结合皮肤、呼吸道、消化道症状及近期暴露史进行人工复核，并将相关项目纳入健康管理建议。"


def _overall_summary(calprotectin: dict[str, Any], total_ige: dict[str, Any], positive_allergens: list[dict[str, Any]]) -> str:
    parts = [
        f"粪便钙卫蛋白：{_test_display(calprotectin)}",
        f"特异性总IgE：{_test_display(total_ige)}",
    ]
    if positive_allergens:
        parts.append(f"过敏原阳性项目 {len(positive_allergens)} 项")
    else:
        parts.append("过敏原明细未见阳性项目")
    return "；".join(parts) + "。当前摘要由OCR结构化结果自动生成，AI综合诊断内容待后续接入DeepSeek后进一步完善。"


def _followup_advice(calprotectin: dict[str, Any], total_ige: dict[str, Any], positive_allergens: list[dict[str, Any]]) -> str:
    advice = ["建议健康管理师先核对OCR识别结果、参考范围和报告页码，确认无误后再进入AI解读和人工审查。"]
    if "阳性" in _test_display(total_ige) or positive_allergens:
        advice.append("如存在过敏相关症状，建议结合阳性过敏原、饮食记录和环境暴露情况进行分层管理。")
    if "阴性" not in _test_display(calprotectin):
        advice.append("如伴随肠道症状，建议进一步结合炎症、感染、用药和饮食因素评估肠道状态。")
    return "".join(advice)


def _immune_system_summary(total_ige: dict[str, Any], positive_allergens: list[dict[str, Any]]) -> str:
    if "阳性" in _test_display(total_ige) or positive_allergens:
        return "总IgE或过敏原项目提示免疫高反应相关线索，需结合肠道屏障、饮食暴露和症状表现综合评估。"
    return "当前IgE相关项目未见明显异常，后续可结合肠道功能、饮食结构和生活方式继续进行健康管理。"


def _inflammation_immune_advice(calprotectin: dict[str, Any], total_ige: dict[str, Any], positive_allergens: list[dict[str, Any]]) -> str:
    return (
        "建议在人工审查阶段重点核对钙卫蛋白、总IgE和过敏原阳性项目。"
        "AI诊断接入前，本段仅作为基于OCR结果的初步健康管理提示，不替代最终医学审核意见。"
    )
