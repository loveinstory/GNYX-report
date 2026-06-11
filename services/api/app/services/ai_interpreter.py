from __future__ import annotations

import copy
import json
import urllib.error
import urllib.request
from typing import Any

from app.core.config import settings
from app.services.admin import get_latest_credential


DEFAULT_PROVIDER = "deepseek"
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"
LAYOUT_FIELD_LIMITS: dict[str, dict[str, int]] = {
    "P01": {
        "overall_summary": 180,
        "risk_assessment": 190,
        "indicator_interpretations.microbiome": 180,
        "indicator_interpretations.gmhi": 180,
        "indicator_interpretations.gut_age": 95,
        "indicator_interpretations.diversity": 95,
        "indicator_interpretations.enterotype": 95,
        "recommendations.management_priorities": 140,
        "recommendations.diet_advice": 180,
        "recommendations.lifestyle_advice": 160,
        "recommendations.followup_advice": 140,
    },
    "P02": {
        "overall_summary": 180,
        "indicator_interpretations.fecal_calprotectin": 150,
        "indicator_interpretations.allergen_panel": 160,
        "indicator_interpretations.total_ige": 150,
        "recommendations.followup_advice": 150,
        "recommendations.microbiome_advice": 150,
        "recommendations.barrier_leaky_gut_impact": 160,
        "recommendations.barrier_improvement_advice": 150,
        "recommendations.diet_gut_advice": 150,
        "recommendations.diet_personalized_advice": 160,
        "recommendations.stress_management_advice": 160,
        "recommendations.functional_medicine_advice": 160,
        "recommendations.immune_system_summary": 150,
        "recommendations.inflammation_immune_advice": 160,
    },
    "P03": {
        "overall_summary": 230,
        "indicator_interpretations.glucose_metabolism": 180,
        "indicator_interpretations.lipid_panel": 180,
        "indicator_interpretations.balance_indexes": 120,
        "risk_assessment": 220,
        "recommendations.diet_advice": 170,
        "recommendations.exercise_advice": 140,
        "recommendations.nutrition_advice": 140,
        "recommendations.followup_advice": 130,
    },
    "P04": {
        "overall_summary": 180,
        "risk_assessment": 220,
        "indicator_interpretations.microelements": 160,
        "indicator_interpretations.vitamin_excess": 160,
        "indicator_interpretations.vitamin_deficiency": 160,
        "indicator_interpretations.iron": 120,
        "indicator_interpretations.zinc": 120,
        "indicator_interpretations.calcium": 120,
        "indicator_interpretations.magnesium": 120,
        "indicator_interpretations.copper": 120,
        "indicator_interpretations.vitamin_a": 120,
        "indicator_interpretations.vitamin_d": 120,
        "indicator_interpretations.vitamin_e": 120,
        "recommendations.diet_advice": 180,
        "recommendations.lifestyle_advice": 160,
        "recommendations.supplement_advice": 150,
        "recommendations.followup_advice": 140,
    },
    "P05": {
        "overall_summary": 180,
        "risk_assessment": 210,
        "indicator_interpretations.stress_axis": 160,
        "indicator_interpretations.catecholamine": 160,
        "indicator_interpretations.neurotransmitter_metabolism": 160,
        "indicator_interpretations.sleep_status": 160,
        "indicator_interpretations.thyroid_metabolism": 160,
        "recommendations.diet_advice": 150,
        "recommendations.lifestyle_advice": 160,
        "recommendations.followup_advice": 140,
    },
    "P06": {
        "overall_summary": 180,
        "indicator_interpretations.immune_cell_activity": 180,
        "indicator_interpretations.cytokine_balance": 180,
        "recommendations.management_priorities": 120,
        "recommendations.followup_advice": 140,
        "recommendations.lifestyle_advice": 150,
    },
    "P07": {
        "overall_summary": 170,
        "risk_assessment": 140,
        "indicator_interpretations.liver_function": 120,
        "indicator_interpretations.fibrosis": 105,
        "indicator_interpretations.aldh2": 150,
        "indicator_interpretations.aldh2.interpretation": 150,
        "indicator_interpretations.aldh2.caution": 90,
        "indicator_interpretations.aldh2.short_interpretation": 48,
        "indicator_interpretations.aldh2.summary": 90,
        "indicator_interpretations.aldh2.comprehensive_interpretation": 80,
        "recommendations.management_priorities": 60,
        "recommendations.diet_advice": 100,
        "recommendations.lifestyle_advice": 90,
        "recommendations.alcohol_advice": 80,
        "recommendations.followup_advice": 100,
    },
    "P17": {
        "overall_summary": 210,
        "hpv_detail_summary": 150,
        "microbiome_detail_summary": 180,
        "barrier_immune_summary": 150,
        "good_bacteria_summary": 130,
        "conditional_pathogen_summary": 130,
        "pathogen_summary": 140,
        "recommendations.hpv": 140,
        "recommendations.microecology": 160,
        "recommendations.lifestyle.diet": 90,
        "recommendations.lifestyle.exercise": 90,
        "recommendations.lifestyle.routine": 90,
        "recommendations.followup_advice": 130,
    },
}


def get_ai_config() -> dict[str, Any]:
    credential = get_latest_credential(DEFAULT_PROVIDER)
    return {
        "provider": DEFAULT_PROVIDER,
        "default_base_url": DEFAULT_BASE_URL,
        "default_model": DEFAULT_MODEL,
        "has_credential": credential is not None,
        "credential_label": credential.get("label") if credential else "",
    }


def test_deepseek_connection(
    *,
    model: str | None = None,
    base_url: str | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    credential = get_latest_credential(DEFAULT_PROVIDER)
    if credential is None:
        return {
            "status": "missing_credential",
            "provider": DEFAULT_PROVIDER,
            "model": model or DEFAULT_MODEL,
            "message": "未配置DeepSeek API Key，请先在后台管理中保存凭据。",
        }

    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": "你是接口连通性测试助手，只返回JSON。"},
            {"role": "user", "content": "{\"ping\": true, \"return\": \"json\"}"},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "max_tokens": 1000,
    }
    response = _call_chat_completions(
        api_key=credential["value"],
        payload=payload,
        base_url=base_url or DEFAULT_BASE_URL,
        timeout_seconds=timeout_seconds,
    )
    return {
        "status": "succeeded",
        "provider": DEFAULT_PROVIDER,
        "model": payload["model"],
        "credential_label": credential["label"],
        "usage": response.get("usage", {}),
        "raw_content": _extract_message_content(response),
    }


def interpret_report_with_deepseek(
    *,
    package_code: str,
    ocr_result: dict[str, Any],
    report_data: dict[str, Any],
    model: str | None = None,
    base_url: str | None = None,
    dry_run: bool = False,
    timeout_seconds: int = 90,
) -> dict[str, Any]:
    selected_model = model or DEFAULT_MODEL
    messages = _build_messages(package_code, ocr_result, report_data)
    request_payload = {
        "model": selected_model,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "max_tokens": 6000,
    }

    if dry_run:
        return {
            "status": "dry_run",
            "provider": DEFAULT_PROVIDER,
            "model": selected_model,
            "request_preview": {
                "base_url": base_url or DEFAULT_BASE_URL,
                "payload": _redact_messages(request_payload),
            },
            "report_data": report_data,
        }

    credential = get_latest_credential(DEFAULT_PROVIDER)
    if credential is None:
        return {
            "status": "missing_credential",
            "provider": DEFAULT_PROVIDER,
            "model": selected_model,
            "message": "未配置DeepSeek API Key，请先在后台管理中保存凭据。",
            "report_data": report_data,
        }

    response = _call_chat_completions(
        api_key=credential["value"],
        payload=request_payload,
        base_url=base_url or DEFAULT_BASE_URL,
        timeout_seconds=timeout_seconds,
    )
    content = _extract_message_content(response)
    ai_output = _parse_ai_json(content)
    merged_report_data = merge_ai_output_into_report_data(report_data, ai_output, model=selected_model)
    return {
        "status": "succeeded",
        "provider": DEFAULT_PROVIDER,
        "model": selected_model,
        "credential_label": credential["label"],
        "ai_output": ai_output,
        "report_data": merged_report_data,
        "usage": response.get("usage", {}),
        "raw_content": content,
    }


def merge_ai_output_into_report_data(report_data: dict[str, Any], ai_output: dict[str, Any], *, model: str) -> dict[str, Any]:
    merged = copy.deepcopy(report_data)
    package_code = str(merged.get("package_code") or "")
    if package_code == "P05":
        _merge_p05_ai_output(merged, ai_output)
        merged["ai_outputs"] = _ai_output_meta(package_code, model, ai_output)
        merged.setdefault("version_lock", {})["ai_model"] = model
        return merged

    if package_code == "P01":
        _merge_p01_ai_output(merged, ai_output)
        merged["ai_outputs"] = _ai_output_meta(package_code, model, ai_output)
        merged.setdefault("version_lock", {})["ai_model"] = model
        return merged

    if package_code == "P03":
        _merge_p03_ai_output(merged, ai_output)
        merged["ai_outputs"] = _ai_output_meta(package_code, model, ai_output)
        merged.setdefault("version_lock", {})["ai_model"] = model
        return merged

    if package_code == "P04":
        _merge_p04_ai_output(merged, ai_output)
        merged["ai_outputs"] = _ai_output_meta(package_code, model, ai_output)
        merged.setdefault("version_lock", {})["ai_model"] = model
        return merged

    if package_code == "P06":
        _merge_p06_ai_output(merged, ai_output)
        merged["ai_outputs"] = _ai_output_meta(package_code, model, ai_output)
        merged.setdefault("version_lock", {})["ai_model"] = model
        return merged

    if package_code == "P07":
        _merge_p07_ai_output(merged, ai_output)
        merged["ai_outputs"] = _ai_output_meta(package_code, model, ai_output)
        merged.setdefault("version_lock", {})["ai_model"] = model
        return merged

    if package_code == "P17":
        _merge_p17_ai_output(merged, ai_output)
        merged["ai_outputs"] = _ai_output_meta(package_code, model, ai_output)
        merged.setdefault("version_lock", {})["ai_model"] = model
        return merged

    p02 = merged.setdefault("p02", {})
    indicator_interpretations = ai_output.get("indicator_interpretations", {})
    recommendations = ai_output.get("recommendations", {})

    if ai_output.get("overall_summary"):
        _merge_p02_text(p02, "overall_summary", str(ai_output["overall_summary"]))

    calprotectin_text = _pick_text(indicator_interpretations, ["calprotectin", "fecal_calprotectin", "钙卫蛋白"])
    if calprotectin_text:
        _merge_p02_text(p02, "calprotectin.interpretation", calprotectin_text)

    allergen_text = _pick_text(indicator_interpretations, ["allergen", "allergen_panel", "过敏原"])
    if allergen_text:
        _merge_p02_text(p02, "allergen.interpretation", allergen_text)

    total_ige_text = _pick_text(indicator_interpretations, ["total_ige", "ige", "IgE", "总IgE"])
    if total_ige_text:
        _merge_p02_text(p02, "total_ige.interpretation", total_ige_text)

    followup_advice = _pick_text(recommendations, ["followup_advice", "health_management", "summary", "advice"])
    if followup_advice:
        _merge_p02_text(p02, "followup_advice", followup_advice)

    for field_path, candidates in {
        "microbiome_advice": ["microbiome_advice", "microbiome", "gut_microbiome_advice", "肠道微生态"],
        "barrier.leaky_gut_impact": ["barrier_leaky_gut_impact", "barrier_summary", "leaky_gut_impact", "intestinal_barrier"],
        "barrier.improvement_advice": ["barrier_improvement_advice", "barrier_advice", "intestinal_barrier_advice"],
        "diet.gut_advice": ["diet_gut_advice", "diet_base_advice", "gut_diet_advice"],
        "diet.personalized_advice": ["diet_personalized_advice", "personalized_diet_advice", "diet_advice", "nutrition_advice"],
        "lifestyle.stress_management_advice": ["stress_management_advice", "lifestyle_advice", "stress_advice"],
        "nutrition.functional_medicine_advice": ["functional_medicine_advice", "nutrition_support_advice", "nutrition_advice"],
    }.items():
        text = _pick_text(recommendations, candidates)
        if text:
            _merge_p02_text(p02, field_path, text)

    immune_summary = _pick_text(recommendations, ["immune_system_summary", "immune", "immunity"])
    if immune_summary:
        _merge_p02_text(p02, "immune_system_summary", immune_summary)

    inflammation_advice = _pick_text(recommendations, ["inflammation_immune_advice", "inflammation", "anti_inflammation"])
    if inflammation_advice:
        _merge_p02_text(p02, "inflammation_immune_advice", inflammation_advice)

    merged["ai_outputs"] = _ai_output_meta(package_code or "P02", model, ai_output)
    merged.setdefault("version_lock", {})["ai_model"] = model
    return merged


def _ai_output_meta(package_code: str, model: str, ai_output: dict[str, Any]) -> dict[str, Any]:
    stored_output = _sanitize_ai_output_for_storage(ai_output)
    meta: dict[str, Any] = {
        "status": "generated",
        "provider": DEFAULT_PROVIDER,
        "model": model,
        "output": stored_output,
    }
    warnings = _layout_warnings_for_ai_output(package_code, stored_output)
    if warnings:
        meta["layout_warnings"] = warnings
    return meta


def _sanitize_ai_output_for_storage(value: Any) -> Any:
    if isinstance(value, str):
        return _safe_report_text(value)
    if isinstance(value, list):
        return [_sanitize_ai_output_for_storage(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_ai_output_for_storage(item) for key, item in value.items()}
    return value


def _merge_p02_text(p02: dict[str, Any], field_path: str, value: str) -> None:
    text = _safe_report_text(value)
    if not text or _p02_text_conflicts_with_results(p02, text):
        return
    _set_nested_value(p02, field_path, text)


def _set_nested_value(data: dict[str, Any], dotted_path: str, value: Any) -> None:
    current = data
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        next_value = current.setdefault(part, {})
        if not isinstance(next_value, dict):
            next_value = {}
            current[part] = next_value
        current = next_value
    current[parts[-1]] = value


def _p02_text_conflicts_with_results(p02: dict[str, Any], text: str) -> bool:
    normalized = "".join(str(text or "").split())
    total_ige = p02.get("total_ige") if isinstance(p02.get("total_ige"), dict) else {}
    total_ige_display = str(total_ige.get("result_display") or "")
    if _p02_result_is_negative(total_ige_display):
        total_ige_conflicts = (
            "鉴于总IgE阳性",
            "结合总IgE阳性",
            "总IgE阳性",
            "总IgE结果阳性",
            "总IgE结果为阳性",
            "总IgE呈阳性",
            "您的总IgE呈阳性",
            "总IgE升高",
            "总IgE增高",
            "总IgE偏高",
        )
        if any(phrase in normalized for phrase in total_ige_conflicts):
            return True

    allergen = p02.get("allergen") if isinstance(p02.get("allergen"), dict) else {}
    allergen_display = str(allergen.get("overall_result") or "")
    positive_items = allergen.get("positive_items") if isinstance(allergen, dict) else []
    has_positive_items = isinstance(positive_items, list) and bool(positive_items)
    if _p02_result_is_negative(allergen_display) and not has_positive_items:
        allergen_conflicts = (
            "阳性过敏原",
            "过敏原阳性项目",
            "过敏原检测发现",
            "本次发现过敏原阳性",
            "已确认过敏原阳性",
        )
        if any(phrase in normalized for phrase in allergen_conflicts):
            return True

    return False


def _p02_result_is_negative(value: str) -> bool:
    text = "".join(str(value or "").split())
    if not text or _p02_result_has_positive_signal(text):
        return False
    return "阴性" in text or "未见阳性" in text or "未发现阳性" in text or "无阳性" in text


def _p02_result_has_positive_signal(value: str) -> bool:
    text = "".join(str(value or "").split())
    if not text:
        return False
    if "↑" in text or "升高" in text:
        return True
    if "阳性" not in text and "弱阳" not in text:
        return False
    if any(phrase in text for phrase in ("阴性", "未见阳性", "未发现阳性", "无阳性", "均未见阳性", "均为阴性")):
        return text.startswith("阳性") or "弱阳性" in text or "阳性项目" in text
    return True


def _merge_p05_ai_output(merged: dict[str, Any], ai_output: dict[str, Any]) -> None:
    p05 = merged.setdefault("p05", {})
    indicator_interpretations = ai_output.get("indicator_interpretations", {})
    recommendations = ai_output.get("recommendations", {})

    if ai_output.get("overall_summary"):
        p05["overall_summary"] = _safe_report_text(str(ai_output["overall_summary"]))
    if ai_output.get("risk_assessment"):
        p05["risk_assessment"] = _safe_report_text(str(ai_output["risk_assessment"]))

    for section, candidates in {
        "hpa": ["stress_axis", "hpa_axis", "hpa", "cortisol_acth"],
        "catecholamine": ["catecholamine", "sympathetic_system", "neurotransmitter"],
        "metabolism": ["neurotransmitter_metabolism", "metabolites", "hva_vma"],
        "thyroid": ["thyroid_metabolism", "thyroid", "metabolism"],
        "sleep": ["sleep_status", "sleep", "circadian_rhythm"],
    }.items():
        text = _pick_text(indicator_interpretations, candidates)
        target = p05.get(section)
        if text and isinstance(target, dict):
            target["interpretation"] = _safe_report_text(text)

    for key, candidates in {
        "diet_advice": ["diet_advice", "diet", "nutrition_advice"],
        "lifestyle_advice": ["lifestyle_advice", "lifestyle", "exercise_advice"],
        "followup_advice": ["followup_advice", "followup", "health_management"],
    }.items():
        text = _pick_text(recommendations, candidates)
        if text:
            p05[key] = _safe_report_text(text)

    disclaimer = ai_output.get("safety", {}).get("disclaimer") if isinstance(ai_output.get("safety"), dict) else ""
    if disclaimer:
        p05["disclaimer"] = _safe_report_text(str(disclaimer))


def _merge_p01_ai_output(merged: dict[str, Any], ai_output: dict[str, Any]) -> None:
    p01 = merged.setdefault("p01", {})
    indicator_interpretations = ai_output.get("indicator_interpretations", {})
    recommendations = ai_output.get("recommendations", {})

    if ai_output.get("overall_summary"):
        p01["overall_summary"] = _safe_report_text(str(ai_output["overall_summary"]))
    if ai_output.get("risk_assessment"):
        p01["risk_assessment"] = _safe_report_text(str(ai_output["risk_assessment"]))

    microbiome_text = _pick_text(
        indicator_interpretations,
        ["microbiome", "gut_microbiome", "microbiota", "intestinal_microbiome"],
    )
    if microbiome_text:
        p01["microbiome_interpretation"] = _safe_report_text(microbiome_text)

    risk_text = _pick_text(indicator_interpretations, ["risk_assessment", "risks", "functional_risk"])
    if risk_text:
        p01["risk_assessment"] = _safe_report_text(risk_text)

    for section, candidates in {
        "gmhi": ["gmhi", "gut_microbiome_health_index"],
        "gut_age": ["gut_age", "intestinal_age"],
        "diversity": ["diversity", "microbiome_diversity"],
        "enterotype": ["enterotype", "gut_type"],
    }.items():
        text = _pick_text(indicator_interpretations, candidates)
        if text:
            p01.setdefault(section, {})["interpretation"] = _safe_report_text(text)

    for key, candidates in {
        "management_priorities": ["management_priorities", "key_actions", "priorities"],
        "diet_advice": ["diet_advice", "diet", "nutrition_advice"],
        "lifestyle_advice": ["lifestyle_advice", "lifestyle", "exercise_advice"],
        "followup_advice": ["followup_advice", "followup", "health_management"],
    }.items():
        text = _pick_text(recommendations, candidates)
        if text:
            p01[key] = _safe_report_text(text)

    _sync_p01_ui_fields(p01)


def _sync_p01_ui_fields(p01: dict[str, Any]) -> None:
    ui = p01.setdefault("ui", {})
    ui["overall_summary_brief"] = _safe_report_text(str(p01.get("overall_summary") or ""))
    ui["risk_assessment_brief"] = _safe_report_text(str(p01.get("risk_assessment") or ""))
    ui["management_priorities_brief"] = _safe_report_text(str(p01.get("management_priorities") or ""))
    ui["microbiome_brief"] = _safe_report_text(str(p01.get("microbiome_interpretation") or ""))
    ui["followup_brief"] = _safe_report_text(str(p01.get("followup_advice") or ""))
    enterotype = p01.get("enterotype") if isinstance(p01.get("enterotype"), dict) else {}
    ui["enterotype_display"] = str(enterotype.get("result_display") or ui.get("enterotype_display") or "普雷沃菌属型（ETP）")
    if not ui.get("diet_brief"):
        ui["diet_brief"] = _safe_report_text(str(p01.get("diet_advice") or ""))
    if not ui.get("lifestyle_brief"):
        ui["lifestyle_brief"] = _safe_report_text(str(p01.get("lifestyle_advice") or ""))


def _merge_p03_ai_output(merged: dict[str, Any], ai_output: dict[str, Any]) -> None:
    p03 = merged.setdefault("p03", {})
    indicator_interpretations = ai_output.get("indicator_interpretations", {})
    recommendations = ai_output.get("recommendations", {})

    if ai_output.get("overall_summary"):
        p03["overall_summary"] = _safe_report_text(str(ai_output["overall_summary"]))
    if ai_output.get("risk_assessment"):
        p03["risk_assessment"] = _safe_report_text(str(ai_output["risk_assessment"]))

    glucose_text = _pick_text(indicator_interpretations, ["glucose_metabolism", "glucose", "blood_glucose", "血糖代谢"])
    if glucose_text:
        p03.setdefault("glucose", {})["interpretation"] = _safe_report_text(glucose_text)

    lipid_text = _pick_text(indicator_interpretations, ["lipid_panel", "lipid", "blood_lipid", "血脂"])
    if lipid_text:
        p03["lipid"] = {"interpretation": _safe_report_text(lipid_text)}

    balance_text = _pick_text(indicator_interpretations, ["balance_indexes", "indexes", "metabolic_indexes", "关键代谢平衡指数"])
    if balance_text:
        balance_text = _safe_report_text(balance_text)
        p03["balance_index"] = {"interpretation": balance_text}
        for key in ["tg_hdl_ratio", "homa_ir", "non_hdl_c"]:
            if isinstance(p03.get(key), dict):
                p03[key]["interpretation"] = balance_text

    for key, candidates in {
        "diet_advice": ["diet_advice", "diet", "饮食"],
        "exercise_advice": ["exercise_advice", "lifestyle", "exercise", "运动"],
        "nutrition_advice": ["nutrition_advice", "nutrition", "营养"],
        "followup_advice": ["followup_advice", "followup", "health_management", "随访"],
    }.items():
        text = _pick_text(recommendations, candidates)
        if text:
            p03[key] = _safe_report_text(text)


def _merge_p04_ai_output(merged: dict[str, Any], ai_output: dict[str, Any]) -> None:
    p04 = merged.setdefault("p04", {})
    indicator_interpretations = ai_output.get("indicator_interpretations", {})
    recommendations = ai_output.get("recommendations", {})

    if ai_output.get("overall_summary"):
        p04["overall_summary"] = _safe_report_text(str(ai_output["overall_summary"]))
    if ai_output.get("risk_assessment"):
        p04["deep_overall_analysis"] = _safe_report_text(str(ai_output["risk_assessment"]))

    micro_text = _pick_text(indicator_interpretations, ["microelements", "minerals", "trace_elements", "微量元素"])
    if micro_text:
        p04["microelements_summary"] = _safe_report_text(micro_text)

    excess_text = _pick_text(indicator_interpretations, ["vitamin_excess", "excess", "high_vitamins", "偏高"])
    if excess_text:
        p04["excess_summary"] = _safe_report_text(excess_text)

    deficiency_text = _pick_text(indicator_interpretations, ["vitamin_deficiency", "deficiency", "low_vitamins", "不足", "缺乏"])
    if deficiency_text:
        p04["deficiency_summary"] = _safe_report_text(deficiency_text)

    nutrients = p04.get("nutrients")
    if isinstance(nutrients, dict):
        for code, candidates in {
            "iron": ["iron", "fe", "铁"],
            "zinc": ["zinc", "zn", "锌"],
            "calcium": ["calcium", "ca", "钙"],
            "magnesium": ["magnesium", "mg", "镁"],
            "copper": ["copper", "cu", "铜"],
            "vitamin_a": ["vitamin_a", "vita", "维生素A"],
            "vitamin_d2": ["vitamin_d2", "25ohd2", "25_hydroxy_vitamin_d2", "维生素D2"],
            "vitamin_d3": ["vitamin_d3", "25ohd3", "25_hydroxy_vitamin_d3", "维生素D3"],
            "vitamin_d": ["vitamin_d", "25ohd", "25_hydroxy_vitamin_d", "维生素D"],
            "vitamin_e": ["vitamin_e", "vite", "维生素E"],
            "vitamin_k1": ["vitamin_k1", "vitk1", "维生素K1"],
            "vitamin_b1": ["vitamin_b1", "vitb1", "维生素B1"],
            "vitamin_b2": ["vitamin_b2", "vitb2", "维生素B2"],
            "vitamin_b3_niacin": ["vitamin_b3_niacin", "niacin", "烟酸"],
            "vitamin_b3_nicotinamide": ["vitamin_b3_nicotinamide", "nicotinamide", "烟酰胺"],
            "vitamin_b5": ["vitamin_b5", "vitb5", "维生素B5"],
            "vitamin_b6": ["vitamin_b6", "vitb6", "维生素B6"],
            "vitamin_b7": ["vitamin_b7", "biotin", "维生素B7"],
            "vitamin_b9_5_mthf": ["vitamin_b9_5_mthf", "5_mthf", "folate", "叶酸"],
            "vitamin_b12_mma": ["vitamin_b12_mma", "mma", "维生素B12"],
        }.items():
            text = _pick_text(indicator_interpretations, candidates)
            target = nutrients.get(code)
            if text and isinstance(target, dict):
                target["interpretation"] = _safe_report_text(text)

    diet_text = _pick_text(recommendations, ["diet_advice", "diet", "nutrition_advice", "饮食"])
    if diet_text:
        diet = p04.setdefault("diet_advice", {})
        if isinstance(diet, dict):
            diet["balanced_text"] = _safe_report_text(diet_text)

    lifestyle_text = _pick_text(recommendations, ["lifestyle_advice", "lifestyle", "exercise_advice", "生活方式"])
    if lifestyle_text:
        lifestyle = p04.setdefault("lifestyle_advice", {})
        if isinstance(lifestyle, dict):
            lifestyle["exercise_text"] = _safe_report_text(lifestyle_text)

    supplement_text = _pick_text(recommendations, ["supplement_advice", "supplement", "补充"])
    if supplement_text:
        supplement = p04.setdefault("supplement", {})
        if isinstance(supplement, dict):
            supplement["need_summary"] = _safe_report_text(supplement_text)

    followup_text = _pick_text(recommendations, ["followup_advice", "followup", "health_management", "随访"])
    if followup_text:
        p04["followup_advice"] = _safe_report_text(followup_text)

    disclaimer = ai_output.get("safety", {}).get("disclaimer") if isinstance(ai_output.get("safety"), dict) else ""
    if disclaimer:
        p04["disclaimer"] = _safe_report_text(str(disclaimer))


def _merge_p06_ai_output(merged: dict[str, Any], ai_output: dict[str, Any]) -> None:
    p06 = merged.setdefault("p06", {})
    indicator_interpretations = ai_output.get("indicator_interpretations", {})
    recommendations = ai_output.get("recommendations", {})

    overall_summary = _pick_text(ai_output, ["overall_summary"])
    if overall_summary:
        text = _safe_report_text(overall_summary)
        p06["overall_summary"] = text
        insights = p06.setdefault("ai_insights", {})
        if isinstance(insights, dict):
            insights["paragraph_1"] = text

    immune_text = _pick_text(indicator_interpretations, ["immune_cell_activity", "immune_cells", "nk_ctl", "immune"])
    if immune_text:
        deep = p06.setdefault("deep_dive", {})
        if isinstance(deep, dict):
            immune = deep.setdefault("immune", {})
            if isinstance(immune, dict):
                immune["paragraph_1"] = _safe_report_text(immune_text)

    cytokine_text = _pick_text(indicator_interpretations, ["cytokine_balance", "cytokines", "inflammation", "il_8_tnf_alpha"])
    if cytokine_text:
        deep = p06.setdefault("deep_dive", {})
        if isinstance(deep, dict):
            cytokine = deep.setdefault("cytokine", {})
            if isinstance(cytokine, dict):
                cytokine["paragraph_1"] = _safe_report_text(cytokine_text)

    priorities = recommendations.get("management_priorities") if isinstance(recommendations, dict) else None
    if isinstance(priorities, list):
        target = p06.setdefault("management_priorities", {})
        if isinstance(target, dict):
            target.pop("priority_4", None)
            for index, item in enumerate(priorities[:3], start=1):
                text = _stringify_text(item)
                if text:
                    target[f"priority_{index}"] = _safe_report_text(text)

    lifestyle_text = _pick_text(recommendations, ["lifestyle_advice", "lifestyle", "diet_advice"])
    if lifestyle_text:
        insights = p06.setdefault("ai_insights", {})
        if isinstance(insights, dict):
            insights["paragraph_3"] = _safe_report_text(lifestyle_text)

    followup_text = _pick_text(recommendations, ["followup_advice", "followup", "health_management"])
    if followup_text:
        p06["followup_advice"] = _safe_report_text(followup_text)

    safety = ai_output.get("safety", {}) if isinstance(ai_output.get("safety"), dict) else {}
    disclaimer = _pick_text(safety, ["disclaimer", "statement"])
    if disclaimer:
        p06["disclaimer"] = _safe_report_text(disclaimer)

    review_note = _pick_text(ai_output, ["review_note"])
    if review_note:
        p06["review_note"] = _safe_report_text(review_note)

    _merge_p06_page_02_ai_insights(p06, ai_output)


def _merge_p06_page_02_ai_insights(p06: dict[str, Any], ai_output: dict[str, Any]) -> None:
    target = p06.setdefault("page_02_ai_insights", {})
    if not isinstance(target, dict):
        target = {}
        p06["page_02_ai_insights"] = target

    page_02_ai_insights = ai_output.get("page_02_ai_insights")
    if isinstance(page_02_ai_insights, dict):
        for key in ("paragraph_1", "paragraph_2", "paragraph_3"):
            text = _pick_text(page_02_ai_insights, [key])
            if text:
                target[key] = _safe_report_text(text)

    fallback = p06.get("ai_insights")
    if isinstance(fallback, dict):
        for key in ("paragraph_1", "paragraph_2", "paragraph_3"):
            if not str(target.get(key) or "").strip() and fallback.get(key):
                target[key] = _safe_report_text(str(fallback[key]))


def _merge_p07_ai_output(merged: dict[str, Any], ai_output: dict[str, Any]) -> None:
    p07 = merged.setdefault("p07", {})
    indicator_interpretations = ai_output.get("indicator_interpretations", {})
    recommendations = ai_output.get("recommendations", {})

    overall_summary = _pick_text(ai_output, ["overall_summary"])
    if overall_summary:
        p07["overall_summary"] = _safe_report_text(overall_summary)

    risk_assessment = _pick_text(ai_output, ["risk_assessment"])
    if risk_assessment:
        p07["risk_assessment"] = _safe_report_text(risk_assessment)

    liver_text = _pick_text(indicator_interpretations, ["liver_function", "liver", "hepatic_function", "肝功能"])
    if liver_text:
        liver = p07.setdefault("liver_function", {})
        if isinstance(liver, dict):
            liver["summary"] = _safe_report_text(liver_text)

    fibrosis_text = _pick_text(indicator_interpretations, ["fibrosis", "liver_fibrosis", "肝纤维化"])
    if fibrosis_text:
        fibrosis = p07.setdefault("fibrosis", {})
        if isinstance(fibrosis, dict):
            fibrosis["summary"] = _safe_report_text(fibrosis_text)

    gene = p07.setdefault("gene", {})
    aldh2 = gene.setdefault("aldh2", {}) if isinstance(gene, dict) else {}
    aldh2_payload = _pick_value(indicator_interpretations, ["aldh2", "gene", "rs671", "酒精代谢", "基因"])
    if isinstance(aldh2, dict) and aldh2_payload:
        if isinstance(aldh2_payload, dict):
            for target, candidates in {
                "interpretation": ["interpretation", "professional_interpretation", "专业解读"],
                "caution": ["caution", "risk_note", "注意事项"],
                "short_interpretation": ["short_interpretation", "brief", "短解读"],
                "summary": ["summary", "mechanism_summary", "摘要"],
                "comprehensive_interpretation": ["comprehensive_interpretation", "comprehensive", "综合解读"],
            }.items():
                text = _pick_text(aldh2_payload, candidates)
                if text:
                    aldh2[target] = _safe_report_text(text)
        else:
            text = _safe_report_text(_stringify_text(aldh2_payload))
            if text:
                aldh2["interpretation"] = text
                aldh2["comprehensive_interpretation"] = text

    priorities = recommendations.get("management_priorities") if isinstance(recommendations, dict) else None
    if isinstance(priorities, list):
        target = p07.setdefault("priorities", {})
        if isinstance(target, dict):
            for index, item in enumerate(priorities[:3], start=1):
                text = _stringify_text(item)
                if text:
                    target[f"priority_{index}"] = {"title": _safe_report_text(text)}

    for key, candidates in {
        "diet_advice": ["diet_advice", "diet", "nutrition_advice", "饮食"],
        "lifestyle_advice": ["lifestyle_advice", "lifestyle", "exercise_advice", "生活方式"],
        "alcohol_advice": ["alcohol_advice", "alcohol", "drinking", "饮酒"],
        "followup_advice": ["followup_advice", "followup", "review_plan", "health_management", "随访"],
    }.items():
        text = _pick_text(recommendations, candidates)
        if text:
            p07[key] = _safe_report_text(text)

    aldh2_advice = _pick_value(recommendations, ["aldh2_advice", "gene_advice", "alcohol_gene_advice", "基因建议"])
    if isinstance(aldh2, dict) and isinstance(aldh2_advice, list):
        for index, item in enumerate(aldh2_advice[:3], start=1):
            text = _stringify_text(item)
            if text:
                aldh2[f"advice_{index}"] = _safe_report_text(text)
    elif isinstance(aldh2, dict) and isinstance(aldh2_advice, dict):
        for target, candidates in {
            "advice_1": ["advice_1", "first", "适量饮酒"],
            "advice_2": ["advice_2", "second", "定期监测"],
            "advice_3": ["advice_3", "third", "健康生活"],
        }.items():
            text = _pick_text(aldh2_advice, candidates)
            if text:
                aldh2[target] = _safe_report_text(text)

    safety = ai_output.get("safety", {}) if isinstance(ai_output.get("safety"), dict) else {}
    disclaimer = _pick_text(safety, ["disclaimer", "statement"])
    if disclaimer:
        p07["disclaimer"] = _safe_report_text(disclaimer)

    review_note = _pick_text(ai_output, ["review_note"])
    if review_note:
        p07["review_note"] = _safe_report_text(review_note)


def _merge_p17_ai_output(merged: dict[str, Any], ai_output: dict[str, Any]) -> None:
    p17 = merged.setdefault("p17", {})
    indicator_interpretations = ai_output.get("indicator_interpretations", {})
    recommendations = ai_output.get("recommendations", {})

    for key in [
        "overall_summary",
        "hpv_overall_status",
        "microecology_overall_status",
        "overall_risk_level",
        "hpv_detail_summary",
        "microbiome_detail_summary",
        "barrier_immune_summary",
        "good_bacteria_summary",
        "conditional_pathogen_summary",
        "pathogen_summary",
        "hpv_management_current_status",
        "microecology_management_current_status",
        "review_note",
    ]:
        if ai_output.get(key):
            p17[key] = _safe_report_text(str(ai_output[key]))

    for key, candidates in {
        "hpv_detail_summary": ["hpv", "hpv_detail", "hpv_typing", "hpv_27"],
        "microbiome_detail_summary": ["microecology", "microbiome", "vaginal_microecology"],
        "barrier_immune_summary": ["barrier_immune", "immune_barrier", "local_immunity"],
        "good_bacteria_summary": ["good_bacteria", "beneficial_bacteria", "lactobacillus"],
        "conditional_pathogen_summary": ["conditional_pathogen", "opportunistic_pathogen"],
        "pathogen_summary": ["pathogen", "pathogenic_microbes", "infection_risk"],
    }.items():
        text = _pick_text(indicator_interpretations, candidates)
        if text:
            p17[key] = _safe_report_text(text)

    hpv_recommendations = recommendations.get("hpv") if isinstance(recommendations, dict) else None
    if isinstance(hpv_recommendations, list):
        for index, item in enumerate(hpv_recommendations[:4], start=1):
            text = _stringify_text(item)
            if text:
                p17[f"hpv_management_advice_{index}"] = _safe_report_text(text)

    micro_recommendations = recommendations.get("microecology") if isinstance(recommendations, dict) else None
    if isinstance(micro_recommendations, list):
        for index, item in enumerate(micro_recommendations[:4], start=1):
            text = _stringify_text(item)
            if text:
                p17[f"microecology_management_advice_{index}"] = _safe_report_text(text)

    lifestyle = recommendations.get("lifestyle") if isinstance(recommendations, dict) else {}
    if isinstance(lifestyle, dict):
        for target, candidates in {
            "lifestyle_advice_diet": ["diet", "diet_advice", "nutrition"],
            "lifestyle_advice_exercise": ["exercise", "exercise_advice", "movement"],
            "lifestyle_advice_routine": ["routine", "sleep", "work_rest"],
        }.items():
            text = _pick_text(lifestyle, candidates)
            if text:
                p17[target] = _safe_report_text(text)

    followup = _pick_text(recommendations, ["followup_advice", "followup", "health_management", "review_plan"])
    if followup:
        p17["followup_advice"] = _safe_report_text(followup)

    safety = ai_output.get("safety", {}) if isinstance(ai_output.get("safety"), dict) else {}
    for target, candidates in {
        "caution_note": ["caution_note", "caution", "note"],
        "disclaimer": ["disclaimer", "statement"],
    }.items():
        text = _pick_text(safety, candidates)
        if text:
            p17[target] = _safe_report_text(text)


def _build_messages(package_code: str, ocr_result: dict[str, Any], report_data: dict[str, Any]) -> list[dict[str, str]]:
    prompt_path = settings.packages_dir / package_code / "prompts" / "interpretation.md"
    rules_path = settings.packages_dir / package_code / "rules.json"
    prompt_text = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
    rules = json.loads(rules_path.read_text(encoding="utf-8")) if rules_path.exists() else {}

    system_prompt = (
        f"{prompt_text}\n\n"
        "请严格输出一个JSON对象，不要输出Markdown代码块。"
        "JSON顶层字段必须包含：overall_summary、risk_tags、indicator_interpretations、recommendations、safety。"
        "safety.requires_human_review 必须为 true。"
    )
    user_payload = {
        "package_code": package_code,
        "structured_report": ocr_result.get("structured_report", {}),
        "current_report_data": _sanitize_report_data_for_ai(report_data),
        "rules": rules,
        "generation_requirements": [
            "current_report_data中的AI待接入字段已置空，请根据structured_report和rules重新生成，不要照抄占位文案。",
            "每个indicator_interpretations字段需要结合本次实际结果、阳性项目、参考范围和健康管理视角。",
            "recommendations需要给出健康管理师可审查的草稿内容，避免临床诊断、处方、药物剂量和绝对化承诺。",
            "不要使用治疗、脱敏治疗、治疗方案、诊断为、确诊、药物剂量等临床诊疗措辞；如涉及医疗处理，只能提示咨询专业医生。",
            "如果输入未提供症状、病史或饮食记录，请明确说明需要人工补充，不得编造。",
            "请参考layout_constraints中的目标展示篇幅，系统不会在合并报告数据时截断过长文案。",
            "页面文案需要在专业完整和版式展示之间平衡：主解读字段允许2到3句，需包含指标依据、风险含义和健康管理动作；小卡片或列表字段保持1到2句。",
            "避免空泛短句，也避免重复科普背景；优先围绕本次异常指标、参考范围、组合风险和人工复核要点生成。",
        ],
        "output_contract": _output_contract(package_code),
        "layout_constraints": _layout_constraints(package_code),
    }
    if package_code == "P17":
        user_payload["generation_requirements"].append(
            "P17必须保持原始报告分类：微小脲原体、解脲脲原体、人型支原体属于定植/条件致病菌，不得归入致病菌组；致病菌组仅包含单纯疱疹病毒、淋球菌、杜克雷嗜血杆菌、生殖支原体、沙眼衣原体、梅毒螺旋体、阴道毛滴虫、阿米巴原虫等原始报告致病菌项目。"
        )
    if package_code == "P07":
        user_payload["generation_requirements"].append(
            "P07必须以原始报告项目为准：肝功能/生化仅包含15项（ALT、PAB、AST、AST/ALT、TP、ALB、GLB、A/G、TBIL、DBIL、IBIL、ALP、GGT、CHE、TBA），肝纤维化仅包含4项（PC-III、CIV、LN、HA）；不得新增MMP-2、TIMP-1、FIB-4或其他未识别项目。"
        )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]


def _sanitize_report_data_for_ai(report_data: dict[str, Any]) -> dict[str, Any]:
    sanitized = copy.deepcopy(report_data)
    p05 = sanitized.get("p05")
    if isinstance(p05, dict):
        for key in [
            "overall_summary",
            "risk_assessment",
            "diet_advice",
            "lifestyle_advice",
            "followup_advice",
            "disclaimer",
        ]:
            if key in p05:
                p05[key] = ""

    p01 = sanitized.get("p01")
    if isinstance(p01, dict):
        for section, field in [
            ("gmhi", "interpretation"),
            ("gut_age", "interpretation"),
            ("diversity", "interpretation"),
            ("enterotype", "interpretation"),
        ]:
            if isinstance(p01.get(section), dict):
                p01[section][field] = ""
        for key in [
            "overall_summary",
            "microbiome_interpretation",
            "risk_assessment",
            "management_priorities",
            "diet_advice",
            "lifestyle_advice",
            "followup_advice",
        ]:
            if key in p01:
                p01[key] = ""

    p03 = sanitized.get("p03")
    if isinstance(p03, dict):
        for section, field in [
            ("glucose", "interpretation"),
            ("lipid", "interpretation"),
            ("balance_index", "interpretation"),
            ("tg_hdl_ratio", "interpretation"),
            ("homa_ir", "interpretation"),
            ("non_hdl_c", "interpretation"),
        ]:
            if isinstance(p03.get(section), dict):
                p03[section][field] = ""
        for key in [
            "overall_summary",
            "risk_assessment",
            "diet_advice",
            "exercise_advice",
            "nutrition_advice",
            "followup_advice",
        ]:
            if key in p03:
                p03[key] = ""

    p06 = sanitized.get("p06")
    if isinstance(p06, dict):
        for key in ["overall_summary", "followup_advice", "disclaimer", "review_note"]:
            if key in p06:
                p06[key] = ""
        for section, keys in {
            "ai_insights": ["paragraph_1", "paragraph_2", "paragraph_3"],
            "page_02_ai_insights": ["paragraph_1", "paragraph_2", "paragraph_3"],
            "management_priorities": ["priority_1", "priority_2", "priority_3", "priority_4"],
        }.items():
            if isinstance(p06.get(section), dict):
                for key in keys:
                    if key in p06[section]:
                        p06[section][key] = ""
        deep_dive = p06.get("deep_dive")
        if isinstance(deep_dive, dict):
            for section in ["immune", "cytokine"]:
                target = deep_dive.get(section)
                if isinstance(target, dict):
                    for key in ["subtitle", "paragraph_1", "paragraph_2", "paragraph_3", "warning"]:
                        if key in target:
                            target[key] = ""

    p17 = sanitized.get("p17")
    if isinstance(p17, dict):
        for key in [
            "overall_summary",
            "hpv_detail_summary",
            "hpv_risk_tip",
            "hpv_followup_tip",
            "microbiome_detail_summary",
            "barrier_immune_summary",
            "good_bacteria_summary",
            "conditional_pathogen_summary",
            "pathogen_summary",
            "hpv_management_current_status",
            "microecology_management_current_status",
            "followup_advice",
            "caution_note",
            "disclaimer",
            "review_note",
        ]:
            if key in p17:
                p17[key] = ""

    p07 = sanitized.get("p07")
    if isinstance(p07, dict):
        for key in [
            "overall_summary",
            "risk_assessment",
            "management_summary",
            "diet_advice",
            "lifestyle_advice",
            "alcohol_advice",
            "followup_advice",
            "disclaimer",
            "review_note",
        ]:
            if key in p07:
                p07[key] = ""
        liver = p07.get("liver_function")
        if isinstance(liver, dict):
            liver["summary"] = ""
        fibrosis = p07.get("fibrosis")
        if isinstance(fibrosis, dict):
            fibrosis["summary"] = ""
        gene = p07.get("gene")
        aldh2 = gene.get("aldh2") if isinstance(gene, dict) else None
        if isinstance(aldh2, dict):
            for key in [
                "interpretation",
                "caution",
                "short_interpretation",
                "summary",
                "comprehensive_interpretation",
                "advice_1",
                "advice_2",
                "advice_3",
            ]:
                if key in aldh2:
                    aldh2[key] = ""
        priorities = p07.get("priorities")
        if isinstance(priorities, dict):
            for item in priorities.values():
                if isinstance(item, dict) and "title" in item:
                    item["title"] = ""

    p02 = sanitized.get("p02")
    if isinstance(p02, dict):
        for section, field in [
            ("calprotectin", "interpretation"),
            ("allergen", "interpretation"),
            ("total_ige", "interpretation"),
        ]:
            if isinstance(p02.get(section), dict):
                p02[section][field] = ""
        for key in [
            "overall_summary",
            "followup_advice",
            "microbiome_advice",
            "immune_system_summary",
            "inflammation_immune_advice",
        ]:
            if key in p02:
                p02[key] = ""
        for section, keys in {
            "barrier": ["leaky_gut_impact", "improvement_advice"],
            "diet": ["gut_advice", "personalized_advice"],
            "lifestyle": ["stress_management_advice"],
            "nutrition": ["functional_medicine_advice"],
        }.items():
            if isinstance(p02.get(section), dict):
                for key in keys:
                    if key in p02[section]:
                        p02[section][key] = ""
    return sanitized


def _output_contract(package_code: str) -> dict[str, Any]:
    if package_code == "P05":
        return {
            "overall_summary": "用于p05.overall_summary",
            "risk_assessment": "用于p05.risk_assessment",
            "indicator_interpretations": {
                "stress_axis": "用于P05压力轴相关解读",
                "catecholamine": "用于P05儿茶酚胺与交感神经相关解读",
                "neurotransmitter_metabolism": "用于P05 HVA/VMA代谢产物相关解读",
                "sleep_status": "用于P05睡眠状态相关解读",
                "thyroid_metabolism": "用于P05甲状腺与代谢相关解读",
            },
            "recommendations": {
                "diet_advice": "用于p05.diet_advice",
                "lifestyle_advice": "用于p05.lifestyle_advice",
                "followup_advice": "用于p05.followup_advice",
            },
            "safety": {
                "disclaimer": "用于p05.disclaimer",
                "requires_human_review": True,
            },
        }

    if package_code == "P01":
        return {
            "overall_summary": "用于p01.overall_summary",
            "risk_assessment": "用于p01.risk_assessment",
            "indicator_interpretations": {
                "microbiome": "用于p01.microbiome_interpretation",
                "gmhi": "用于p01.gmhi.interpretation",
                "gut_age": "用于p01.gut_age.interpretation",
                "diversity": "用于p01.diversity.interpretation",
                "enterotype": "用于p01.enterotype.interpretation",
                "risk_assessment": "用于p01.risk_assessment",
            },
            "recommendations": {
                "management_priorities": "用于p01.management_priorities",
                "diet_advice": "用于p01.diet_advice",
                "lifestyle_advice": "用于p01.lifestyle_advice",
                "followup_advice": "用于p01.followup_advice",
            },
            "safety": {
                "disclaimer": "健康管理报告免责声明",
                "requires_human_review": True,
            },
        }

    if package_code == "P03":
        return {
            "overall_summary": "用于p03.overall_summary",
            "risk_assessment": "用于p03.risk_assessment",
            "indicator_interpretations": {
                "glucose_metabolism": "用于p03.glucose.interpretation",
                "lipid_panel": "用于p03.lipid.interpretation",
                "balance_indexes": "用于p03.balance_index.interpretation及关键计算指标解读",
            },
            "recommendations": {
                "diet_advice": "用于p03.diet_advice",
                "exercise_advice": "用于p03.exercise_advice",
                "nutrition_advice": "用于p03.nutrition_advice",
                "followup_advice": "用于p03.followup_advice",
            },
            "safety": {
                "disclaimer": "健康管理报告免责声明",
                "requires_human_review": True,
            },
        }

    if package_code == "P04":
        return {
            "overall_summary": "用于p04.overall_summary",
            "risk_assessment": "用于p04.deep_overall_analysis",
            "indicator_interpretations": {
                "microelements": "用于p04.microelements_summary",
                "vitamin_excess": "用于p04.excess_summary",
                "vitamin_deficiency": "用于p04.deficiency_summary",
                "iron": "用于p04.nutrients.iron.interpretation",
                "zinc": "用于p04.nutrients.zinc.interpretation",
                "calcium": "用于p04.nutrients.calcium.interpretation",
                "magnesium": "用于p04.nutrients.magnesium.interpretation",
                "copper": "用于p04.nutrients.copper.interpretation",
                "vitamin_a": "用于p04.nutrients.vitamin_a.interpretation",
                "vitamin_d2": "用于p04.nutrients.vitamin_d2.interpretation",
                "vitamin_d3": "用于p04.nutrients.vitamin_d3.interpretation",
                "vitamin_d": "用于p04.nutrients.vitamin_d.interpretation",
                "vitamin_e": "用于p04.nutrients.vitamin_e.interpretation",
                "vitamin_k1": "用于p04.nutrients.vitamin_k1.interpretation",
                "vitamin_b1": "用于p04.nutrients.vitamin_b1.interpretation",
                "vitamin_b2": "用于p04.nutrients.vitamin_b2.interpretation",
                "vitamin_b3_niacin": "用于p04.nutrients.vitamin_b3_niacin.interpretation",
                "vitamin_b3_nicotinamide": "用于p04.nutrients.vitamin_b3_nicotinamide.interpretation",
                "vitamin_b5": "用于p04.nutrients.vitamin_b5.interpretation",
                "vitamin_b6": "用于p04.nutrients.vitamin_b6.interpretation",
                "vitamin_b7": "用于p04.nutrients.vitamin_b7.interpretation",
                "vitamin_b9_5_mthf": "用于p04.nutrients.vitamin_b9_5_mthf.interpretation",
                "vitamin_b12_mma": "用于p04.nutrients.vitamin_b12_mma.interpretation",
            },
            "recommendations": {
                "diet_advice": "用于p04.diet_advice.balanced_text",
                "lifestyle_advice": "用于p04.lifestyle_advice.exercise_text",
                "supplement_advice": "用于p04.supplement.need_summary",
                "followup_advice": "用于p04.followup_advice",
            },
            "safety": {
                "disclaimer": "用于p04.disclaimer",
                "requires_human_review": True,
            },
        }

    if package_code == "P06":
        return {
            "overall_summary": "用于p06.overall_summary",
            "page_02_ai_insights": {
                "paragraph_1": "仅用于第02页AI健康管理洞察，三段合计250个中文可见字符以内",
                "paragraph_2": "仅用于第02页AI健康管理洞察，三段合计250个中文可见字符以内",
                "paragraph_3": "仅用于第02页AI健康管理洞察，三段合计250个中文可见字符以内",
            },
            "indicator_interpretations": {
                "immune_cell_activity": "用于p06.deep_dive.immune.paragraph_1",
                "cytokine_balance": "用于p06.deep_dive.cytokine.paragraph_1",
            },
            "recommendations": {
                "management_priorities": "仅输出3条管理优先级，用于p06.management_priorities.priority_1到priority_3",
                "lifestyle_advice": "用于p06.ai_insights.paragraph_3",
                "followup_advice": "用于p06.followup_advice",
            },
            "safety": {
                "disclaimer": "用于p06.disclaimer",
                "requires_human_review": True,
            },
            "review_note": "用于p06.review_note",
        }

    if package_code == "P07":
        return {
            "overall_summary": "用于第02页 p07.overall_summary，170个中文可见字符以内",
            "risk_assessment": "用于内部审查和后续页风险摘要，140个中文可见字符以内",
            "indicator_interpretations": {
                "liver_function": "用于第03/05页 p07.liver_function.summary；必须基于原始报告15项肝功能/生化指标：ALT、PAB、AST、AST/ALT、TP、ALB、GLB、A/G、TBIL、DBIL、IBIL、ALP、GGT、CHE、TBA；120字以内",
                "fibrosis": "用于第03/05页 p07.fibrosis.summary；必须基于原始报告4项肝纤维化指标：PC-III、CIV、LN、HA；不得新增MMP-2、TIMP-1、FIB-4；105字以内",
                "aldh2": {
                    "interpretation": "用于第04页 p07.gene.aldh2.interpretation；150字以内",
                    "caution": "用于第04页 p07.gene.aldh2.caution；90字以内",
                    "short_interpretation": "用于第05页 p07.gene.aldh2.short_interpretation；48字以内",
                    "summary": "用于第05页 p07.gene.aldh2.summary；90字以内",
                    "comprehensive_interpretation": "用于第05页 p07.gene.aldh2.comprehensive_interpretation；80字以内",
                },
            },
            "recommendations": {
                "management_priorities": "仅输出3条短标题，每条18字以内，用于第02页 p07.priorities.priority_1到priority_3",
                "diet_advice": "用于p07.diet_advice，100字以内",
                "lifestyle_advice": "用于第03页 p07.lifestyle_advice，90字以内",
                "alcohol_advice": "用于p07.alcohol_advice，80字以内",
                "followup_advice": "用于p07.followup_advice，100字以内",
                "aldh2_advice": "输出3条，每条36字以内，依次用于第04页 p07.gene.aldh2.advice_1到advice_3",
            },
            "safety": {
                "disclaimer": "用于第02页 p07.disclaimer，60字以内",
                "requires_human_review": True,
            },
            "review_note": "用于p07.review_note，80字以内",
        }

    if package_code == "P17":
        return {
            "overall_summary": "用于p17.overall_summary",
            "hpv_overall_status": "用于p17.hpv_overall_status",
            "microecology_overall_status": "用于p17.microecology_overall_status",
            "overall_risk_level": "用于p17.overall_risk_level",
            "hpv_detail_summary": "用于p17.hpv_detail_summary",
            "microbiome_detail_summary": "用于p17.microbiome_detail_summary",
            "barrier_immune_summary": "用于p17.barrier_immune_summary",
            "good_bacteria_summary": "用于p17.good_bacteria_summary",
            "conditional_pathogen_summary": "用于p17.conditional_pathogen_summary",
            "pathogen_summary": "用于p17.pathogen_summary",
            "indicator_interpretations": {
                "hpv": "用于HPV 27型别综合解读",
                "microecology": "用于阴道微生态核酸检测结果解读",
                "barrier_immune": "用于局部屏障与免疫稳态解读",
                "good_bacteria": "用于有益菌分析",
                "conditional_pathogen": "用于条件致病菌分析",
                "pathogen": "用于致病菌风险分析",
            },
            "recommendations": {
                "hpv": "HPV管理建议列表，最多4条",
                "microecology": "微生态管理建议列表，最多4条",
                "lifestyle": {
                    "diet": "用于p17.lifestyle_advice_diet",
                    "exercise": "用于p17.lifestyle_advice_exercise",
                    "routine": "用于p17.lifestyle_advice_routine",
                },
                "followup_advice": "用于p17.followup_advice",
            },
            "safety": {
                "caution_note": "用于p17.caution_note",
                "disclaimer": "用于p17.disclaimer",
                "requires_human_review": True,
            },
            "review_note": "用于p17.review_note",
        }
    return {
        "overall_summary": "用于p02.overall_summary",
        "indicator_interpretations": {
            "fecal_calprotectin": "用于p02.calprotectin.interpretation",
            "allergen_panel": "用于p02.allergen.interpretation",
            "total_ige": "用于p02.total_ige.interpretation",
        },
        "recommendations": {
            "followup_advice": "用于p02.followup_advice",
            "microbiome_advice": "用于p02.microbiome_advice",
            "barrier_leaky_gut_impact": "用于p02.barrier.leaky_gut_impact",
            "barrier_improvement_advice": "用于p02.barrier.improvement_advice",
            "diet_gut_advice": "用于p02.diet.gut_advice",
            "diet_personalized_advice": "用于p02.diet.personalized_advice",
            "stress_management_advice": "用于p02.lifestyle.stress_management_advice",
            "functional_medicine_advice": "用于p02.nutrition.functional_medicine_advice",
            "immune_system_summary": "用于p02.immune_system_summary",
            "inflammation_immune_advice": "用于p02.inflammation_immune_advice",
        },
        "safety": {
            "disclaimer": "健康管理报告免责声明",
            "requires_human_review": True,
        },
    }


def _layout_constraints(package_code: str) -> dict[str, int]:
    return dict(LAYOUT_FIELD_LIMITS.get(package_code.upper(), LAYOUT_FIELD_LIMITS["P02"]))


def _call_chat_completions(
    *,
    api_key: str,
    payload: dict[str, Any],
    base_url: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    request = urllib.request.Request(
        _chat_url(base_url),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DeepSeek调用失败：HTTP {exc.code} {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"DeepSeek调用失败：{exc.reason}") from exc


def _chat_url(base_url: str) -> str:
    cleaned = base_url.rstrip("/")
    if cleaned.endswith("/chat/completions"):
        return cleaned
    return f"{cleaned}/chat/completions"


def _extract_message_content(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        raise RuntimeError("DeepSeek响应缺少choices。")
    choice = choices[0]
    message = choice.get("message") or {}
    content = message.get("content")
    if not content:
        finish_reason = choice.get("finish_reason", "")
        reasoning = message.get("reasoning_content", "")
        if finish_reason == "length" or reasoning:
            raise RuntimeError("DeepSeek响应未生成最终content，可能是max_tokens不足或模型仍在推理阶段。")
        raise RuntimeError("DeepSeek响应缺少message.content。")
    return str(content)


def _parse_ai_json(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"DeepSeek返回内容不是合法JSON：{exc}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("DeepSeek返回JSON不是对象。")
    return parsed


def _pick_text(data: Any, keys: list[str]) -> str:
    value = _pick_value(data, keys)
    return _stringify_text(value) if value is not None else ""


def _pick_value(data: Any, keys: list[str]) -> Any:
    if isinstance(data, str):
        return data
    if not isinstance(data, dict):
        return None
    for key in keys:
        if key in data:
            return data[key]
    normalized = {str(key).lower(): value for key, value in data.items()}
    for key in keys:
        value = normalized.get(key.lower())
        if value is not None:
            return value
    return None


def _stringify_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "；".join(_stringify_text(item) for item in value if _stringify_text(item))
    if isinstance(value, dict):
        for key in ("interpretation", "summary", "advice", "text", "content", "recommendation"):
            if key in value:
                return _stringify_text(value[key])
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _layout_warnings_for_ai_output(package_code: str, ai_output: dict[str, Any]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    for path, limit in _layout_constraints(package_code).items():
        value = _resolve_path(ai_output, path)
        if value in (None, ""):
            continue
        text = _stringify_text(value)
        length = _visible_char_count(text)
        if length > limit:
            warnings.append(
                {
                    "field": path,
                    "max_chars": limit,
                    "actual_chars": length,
                    "message": f"{path} 超出建议展示字数，已保留原文，请在AI提示词或人工审查中精简。",
                }
            )
    if package_code.upper() == "P06":
        page_02_ai_insights = ai_output.get("page_02_ai_insights")
        if isinstance(page_02_ai_insights, dict):
            total_length = sum(
                _visible_char_count(_stringify_text(page_02_ai_insights.get(key, "")))
                for key in ("paragraph_1", "paragraph_2", "paragraph_3")
            )
            if total_length > 250:
                warnings.append(
                    {
                        "field": "page_02_ai_insights",
                        "max_chars": 250,
                        "actual_chars": total_length,
                        "message": "第02页AI健康管理洞察超出250个中文可见字符，已保留原文，请通过P06提示词重新生成更凝练的完整短句。",
                    }
                )
    return warnings


def _resolve_path(data: dict[str, Any], dotted_path: str) -> Any:
    current: Any = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _visible_char_count(value: str) -> int:
    return sum(1 for char in str(value) if not char.isspace())


def _safe_report_text(value: str) -> str:
    replacements = {
        "脱敏治疗咨询": "由专业医生评估是否需要进一步处理",
        "脱敏治疗": "专业医生进一步评估",
        "治疗方案": "健康管理方案",
        "治疗建议": "健康管理建议",
        "是否需要治疗": "是否需要进一步处理",
        "规范治疗": "在专业医生指导下处理",
        "针对性治疗": "针对性处理",
        "治疗": "处理",
        "临床诊断": "专业医学判断",
        "诊断": "医学判断",
        "确诊": "确认",
        "IgE介导的过敏反应": "IgE相关过敏倾向",
        "IgE介导": "IgE相关",
        "Th2型免疫反应偏亢": "免疫反应偏高",
        "Th2型免疫反应活跃": "免疫反应较活跃",
        "临床症状": "实际症状",
        "阳性反应": "阳性结果",
        "切勿自行使用药物或专业医生进一步评估": "切勿自行使用药物，进一步干预需咨询专业医生",
    }
    text = value
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.strip()


def _redact_messages(payload: dict[str, Any]) -> dict[str, Any]:
    preview = copy.deepcopy(payload)
    for message in preview.get("messages", []):
        content = message.get("content", "")
        if len(content) > 1200:
            message["content"] = f"{content[:1200]}...<truncated>"
    return preview
