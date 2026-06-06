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
        merged["ai_outputs"] = {
            "status": "generated",
            "provider": DEFAULT_PROVIDER,
            "model": model,
            "output": ai_output,
        }
        merged.setdefault("version_lock", {})["ai_model"] = model
        return merged

    if package_code == "P01":
        _merge_p01_ai_output(merged, ai_output)
        merged["ai_outputs"] = {
            "status": "generated",
            "provider": DEFAULT_PROVIDER,
            "model": model,
            "output": ai_output,
        }
        merged.setdefault("version_lock", {})["ai_model"] = model
        return merged

    if package_code == "P03":
        _merge_p03_ai_output(merged, ai_output)
        merged["ai_outputs"] = {
            "status": "generated",
            "provider": DEFAULT_PROVIDER,
            "model": model,
            "output": ai_output,
        }
        merged.setdefault("version_lock", {})["ai_model"] = model
        return merged

    p02 = merged.setdefault("p02", {})
    indicator_interpretations = ai_output.get("indicator_interpretations", {})
    recommendations = ai_output.get("recommendations", {})

    if ai_output.get("overall_summary"):
        p02["overall_summary"] = _safe_report_text(str(ai_output["overall_summary"]))

    calprotectin_text = _pick_text(indicator_interpretations, ["calprotectin", "fecal_calprotectin", "钙卫蛋白"])
    if calprotectin_text:
        p02.setdefault("calprotectin", {})["interpretation"] = _safe_report_text(calprotectin_text)

    allergen_text = _pick_text(indicator_interpretations, ["allergen", "allergen_panel", "过敏原"])
    if allergen_text:
        p02.setdefault("allergen", {})["interpretation"] = _safe_report_text(allergen_text)

    total_ige_text = _pick_text(indicator_interpretations, ["total_ige", "ige", "IgE", "总IgE"])
    if total_ige_text:
        p02.setdefault("total_ige", {})["interpretation"] = _safe_report_text(total_ige_text)

    followup_advice = _pick_text(recommendations, ["followup_advice", "health_management", "summary", "advice"])
    if followup_advice:
        p02["followup_advice"] = _safe_report_text(followup_advice)

    immune_summary = _pick_text(recommendations, ["immune_system_summary", "immune", "immunity"])
    if immune_summary:
        p02["immune_system_summary"] = _safe_report_text(immune_summary)

    inflammation_advice = _pick_text(recommendations, ["inflammation_immune_advice", "inflammation", "anti_inflammation"])
    if inflammation_advice:
        p02["inflammation_immune_advice"] = _safe_report_text(inflammation_advice)

    merged["ai_outputs"] = {
        "status": "generated",
        "provider": DEFAULT_PROVIDER,
        "model": model,
        "output": ai_output,
    }
    merged.setdefault("version_lock", {})["ai_model"] = model
    return merged


def _merge_p05_ai_output(merged: dict[str, Any], ai_output: dict[str, Any]) -> None:
    p05 = merged.setdefault("p05", {})
    recommendations = ai_output.get("recommendations", {})

    if ai_output.get("overall_summary"):
        p05["overall_summary"] = _safe_report_text(str(ai_output["overall_summary"]))
    if ai_output.get("risk_assessment"):
        p05["risk_assessment"] = _safe_report_text(str(ai_output["risk_assessment"]))

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
        p01["overall_summary"] = _safe_report_text(str(ai_output["overall_summary"]), max_chars=70)
    if ai_output.get("risk_assessment"):
        p01["risk_assessment"] = _safe_report_text(str(ai_output["risk_assessment"]), max_chars=86)

    microbiome_text = _pick_text(
        indicator_interpretations,
        ["microbiome", "gut_microbiome", "microbiota", "intestinal_microbiome"],
    )
    if microbiome_text:
        p01["microbiome_interpretation"] = _safe_report_text(microbiome_text, max_chars=86)

    risk_text = _pick_text(indicator_interpretations, ["risk_assessment", "risks", "functional_risk"])
    if risk_text:
        p01["risk_assessment"] = _safe_report_text(risk_text, max_chars=86)

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
            max_chars = 72 if key == "management_priorities" else 80 if key == "followup_advice" else None
            p01[key] = _safe_report_text(text, max_chars=max_chars)

    _sync_p01_ui_fields(p01)


def _sync_p01_ui_fields(p01: dict[str, Any]) -> None:
    ui = p01.setdefault("ui", {})
    ui["overall_summary_brief"] = _safe_report_text(str(p01.get("overall_summary") or ""), max_chars=70)
    ui["risk_assessment_brief"] = _safe_report_text(str(p01.get("risk_assessment") or ""), max_chars=86)
    ui["management_priorities_brief"] = _safe_report_text(str(p01.get("management_priorities") or ""), max_chars=72)
    ui["microbiome_brief"] = _safe_report_text(str(p01.get("microbiome_interpretation") or ""), max_chars=86)
    ui["followup_brief"] = _safe_report_text(str(p01.get("followup_advice") or ""), max_chars=80)
    enterotype = p01.get("enterotype") if isinstance(p01.get("enterotype"), dict) else {}
    ui["enterotype_display"] = str(enterotype.get("result_display") or ui.get("enterotype_display") or "普雷沃菌属型（ETP）")
    if not ui.get("diet_brief"):
        ui["diet_brief"] = _safe_report_text(str(p01.get("diet_advice") or ""), max_chars=120)
    if not ui.get("lifestyle_brief"):
        ui["lifestyle_brief"] = _safe_report_text(str(p01.get("lifestyle_advice") or ""), max_chars=110)


def _merge_p03_ai_output(merged: dict[str, Any], ai_output: dict[str, Any]) -> None:
    p03 = merged.setdefault("p03", {})
    indicator_interpretations = ai_output.get("indicator_interpretations", {})
    recommendations = ai_output.get("recommendations", {})

    if ai_output.get("overall_summary"):
        p03["overall_summary"] = _safe_report_text(str(ai_output["overall_summary"]), max_chars=170)
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
        limited_balance_text = _safe_report_text(balance_text, max_chars=110)
        p03["balance_index"] = {"interpretation": limited_balance_text}
        for key in ["tg_hdl_ratio", "homa_ir", "non_hdl_c"]:
            if isinstance(p03.get(key), dict):
                p03[key]["interpretation"] = limited_balance_text

    for key, candidates in {
        "diet_advice": ["diet_advice", "diet", "饮食"],
        "exercise_advice": ["exercise_advice", "lifestyle", "exercise", "运动"],
        "nutrition_advice": ["nutrition_advice", "nutrition", "营养"],
        "followup_advice": ["followup_advice", "followup", "health_management", "随访"],
    }.items():
        text = _pick_text(recommendations, candidates)
        if text:
            max_chars = 290 if key == "followup_advice" else None
            p03[key] = _safe_report_text(text, max_chars=max_chars)


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
        ],
        "output_contract": _output_contract(package_code),
    }
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
            "immune_system_summary",
            "inflammation_immune_advice",
        ]:
            if key in p02:
                p02[key] = ""
    return sanitized


def _output_contract(package_code: str) -> dict[str, Any]:
    if package_code == "P05":
        return {
            "overall_summary": "用于p05.overall_summary",
            "risk_assessment": "用于p05.risk_assessment",
            "indicator_interpretations": {
                "stress_axis": "用于P05压力轴相关解读",
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
    return {
        "overall_summary": "用于p02.overall_summary",
        "indicator_interpretations": {
            "fecal_calprotectin": "用于p02.calprotectin.interpretation",
            "allergen_panel": "用于p02.allergen.interpretation",
            "total_ige": "用于p02.total_ige.interpretation",
        },
        "recommendations": {
            "followup_advice": "用于p02.followup_advice",
            "immune_system_summary": "用于p02.immune_system_summary",
            "inflammation_immune_advice": "用于p02.inflammation_immune_advice",
        },
        "safety": {
            "disclaimer": "健康管理报告免责声明",
            "requires_human_review": True,
        },
    }


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
    if isinstance(data, str):
        return data
    if not isinstance(data, dict):
        return ""
    for key in keys:
        if key in data:
            return _stringify_text(data[key])
    normalized = {str(key).lower(): value for key, value in data.items()}
    for key in keys:
        value = normalized.get(key.lower())
        if value is not None:
            return _stringify_text(value)
    return ""


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


def _safe_report_text(value: str, max_chars: int | None = None) -> str:
    replacements = {
        "脱敏治疗咨询": "由专业医生评估是否需要进一步处理",
        "脱敏治疗": "专业医生进一步评估",
        "治疗方案": "健康管理方案",
        "治疗建议": "健康管理建议",
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
    return _limit_visible_chars(text, max_chars) if max_chars else text


def _limit_visible_chars(value: str, max_chars: int | None) -> str:
    if not max_chars or max_chars <= 0:
        return value
    compact_count = 0
    result: list[str] = []
    for char in value:
        if not char.isspace():
            compact_count += 1
        if compact_count > max_chars:
            break
        result.append(char)
    text = "".join(result).strip()
    return text


def _redact_messages(payload: dict[str, Any]) -> dict[str, Any]:
    preview = copy.deepcopy(payload)
    for message in preview.get("messages", []):
        content = message.get("content", "")
        if len(content) > 1200:
            message["content"] = f"{content[:1200]}...<truncated>"
    return preview
