from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Callable


P11_REPORT_NAME = "食物敏感/免疫相关评估健康管理报告"
P11_ASSESSMENT_TYPE = "食物敏感/免疫相关评估"
P11_SAMPLE_TYPE = "血清"
P11_METHOD = "酶联免疫法&流式荧光发光法&化学发光法"
P11_TEMPLATE_VERSION = "P11-html-v0.2-ocr-42-dynamic-binding"
P11_RULE_VERSION = "P11-rules-v0.2-food-42-render"
P11_PROMPT_VERSION = "P11-prompts-v0.2-food-42-ai-diagnosis"
P11_ORGANIZATION_ADDRESS = "安徽省合肥市庐阳区临泉路7266号研发中心楼5层"


def build_p11_report_data(
    *,
    ocr_result: dict[str, Any],
    age_display: Callable[[Any], str],
    date_display: Callable[[str], str],
    lab_result_builder: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    structured = ocr_result.get("structured_report", {}) if isinstance(ocr_result.get("structured_report"), dict) else {}
    patient_info = structured.get("patient_info", {}) if isinstance(structured.get("patient_info"), dict) else {}
    additional_info = structured.get("additional_info", {}) if isinstance(structured.get("additional_info"), dict) else {}
    extracted = structured.get("p11_extracted_report", {}) if isinstance(structured.get("p11_extracted_report"), dict) else {}
    raw_meta = extracted.get("raw_report_meta", {}) if isinstance(extracted.get("raw_report_meta"), dict) else {}
    contact = extracted.get("contact", {}) if isinstance(extracted.get("contact"), dict) else {}
    tests = structured.get("tests", []) if isinstance(structured.get("tests"), list) else []

    report_id = str(structured.get("report_id") or ocr_result.get("source_file") or "")
    assessment_date_raw = str(additional_info.get("report_date") or additional_info.get("sample_date") or "")
    indicators = {
        "igg1": _indicator_test(tests, "igg1", ["igg1"]),
        "igg2": _indicator_test(tests, "igg2", ["igg2"]),
        "igg3": _indicator_test(tests, "igg3", ["igg3"]),
        "igg4": _indicator_test(tests, "igg4", ["igg4"]),
        "total_ige": _indicator_test(tests, "total_ige", ["total_ige", "总ige", "ige"]),
    }
    food_results = _food_results(tests)
    food_summary = _food_result_summary(food_results)
    focus_items = _focus_items(food_summary, indicators)
    priorities = _priorities(food_summary)
    diet = _diet_plan(food_summary)

    return {
        "case_id": f"case_{report_id or 'p11'}",
        "package_code": "P11",
        "patient": {
            "name": patient_info.get("name") or "",
            "gender": patient_info.get("gender") or "",
            "age": age_display(patient_info.get("age")),
            "submitting_unit": patient_info.get("submitting_unit") or patient_info.get("hospital") or "—",
            "symptoms": patient_info.get("clinical_diagnosis") or "-",
        },
        "report": {
            "report_id": report_id,
            "assessment_type": P11_ASSESSMENT_TYPE,
            "method": P11_METHOD,
            "assessment_date": date_display(assessment_date_raw),
            "sample_date": additional_info.get("sample_date") or "",
            "receive_date": additional_info.get("receive_date") or "",
            "report_date": additional_info.get("report_date") or "",
            "generated_at": f"报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        },
        "sample": {
            "type": P11_SAMPLE_TYPE,
            "condition": patient_info.get("specimen_condition") or raw_meta.get("sampleStatus") or "—",
        },
        "lab_results": [lab_result_builder(test) for test in tests],
        "organization": {
            "phone": _first_text(contact.get("phone"), raw_meta.get("labPhone"), "400-158-1959"),
            "email": "service@anweikang.com",
            "website": _first_text(contact.get("website"), raw_meta.get("labWebsite"), "www.anweikang.com"),
            "address": _first_text(contact.get("address"), raw_meta.get("labAddress"), P11_ORGANIZATION_ADDRESS),
        },
        "p11": {
            "report_title": P11_REPORT_NAME,
            "management_focus": report_id or "—",
            "food_results": food_results,
            "food_summary": food_summary,
            "focus_items": focus_items,
            "priorities": priorities,
            "diet": diet,
            "indicators": indicators,
            "overall_summary": _overall_summary(food_summary, indicators),
            "ai_insight": _ai_insight(food_summary, indicators),
            "overall_summary_brief": _overall_summary_brief(food_summary, indicators),
            "ai_insight_brief": _ai_insight_brief(food_summary, indicators),
            "ai_assisted_diagnosis": _ai_assisted_diagnosis(food_summary, indicators),
            "ai_progress_display": "已生成",
            "ai_progress_percent": "100%",
            "followup_advice": _followup_advice(food_summary),
            "disclaimer": _first_text(
                extracted.get("disclaimer"),
                "本报告仅供健康管理参考，不作为临床诊断依据。",
            ),
            "review_note": "建议结合原始检测结果、症状记录和专业人员意见进行人工复核。",
        },
        "ai_outputs": {
            "status": "pending",
            "note": "P11已根据OCR结果生成规则兜底诊断；AI解读完成后将覆盖综合结论、重点说明和建议。",
        },
        "ocr_snapshot": {
            "source_file": ocr_result.get("source_file", ""),
            "strategy_version": ocr_result.get("strategy_version", ""),
            "provider": ocr_result.get("provider", ""),
            "warnings": ocr_result.get("warnings", []),
        },
        "version_lock": {
            "template_version": P11_TEMPLATE_VERSION,
            "rule_version": P11_RULE_VERSION,
            "prompt_version": P11_PROMPT_VERSION,
            "ai_model": "deepseek-v4-flash",
            "ocr_strategy_version": ocr_result.get("strategy_version", ""),
            "ocr_provider": ocr_result.get("provider", ""),
        },
    }


def _sample_type(patient_info: dict[str, Any], raw_meta: dict[str, Any]) -> str:
    specimen_types = patient_info.get("specimen_types")
    if isinstance(specimen_types, list):
        joined = "、".join(str(item).strip() for item in specimen_types if str(item or "").strip())
    else:
        joined = ""
    return _first_text(joined, raw_meta.get("sampleType"), P11_SAMPLE_TYPE)


def _method_summary(tests: list[dict[str, Any]]) -> str:
    methods: list[str] = []
    for test in tests:
        method = str(test.get("method") or "").strip()
        if method and method not in methods:
            methods.append(method)
    return "、".join(methods) or P11_METHOD


def _indicator_test(tests: list[dict[str, Any]], code: str, keywords: list[str]) -> dict[str, Any]:
    test = _find_test(tests, keywords)
    result = str((test or {}).get("result") or "").strip()
    unit = str((test or {}).get("unit") or "").strip()
    reference_raw = str((test or {}).get("reference_range") or "").strip()
    flag = str((test or {}).get("indicator") or "").strip()
    low, high = _parse_reference_range(reference_raw)
    value = _parse_number(result)
    status = _indicator_status(result, flag, low, high)
    reference_display = _reference_display(reference_raw, unit)
    range_low_display = _compact_number(low) if low is not None else "—"
    range_high_display = _compact_number(high) if high is not None else "—"
    return {
        "code": code,
        "name": _indicator_name(code),
        "result": result or "未识别",
        "reference_range": reference_display,
        "reference_raw": reference_raw,
        "range_low": range_low_display,
        "range_high": range_high_display,
        "unit": unit or "—",
        "status": status,
        "range_note": _range_note(result, reference_raw, status),
        "marker_percent": _marker_percent(value, low, high),
        "flag": flag,
    }


def _find_test(tests: list[dict[str, Any]], keywords: list[str]) -> dict[str, Any] | None:
    for test in tests:
        haystack = " ".join(str(test.get(key) or "") for key in ("item_code", "test_name", "indicator", "short_name")).lower()
        if any(keyword.lower() in haystack for keyword in keywords):
            return test
    return None


def _food_results(tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for fallback_index, test in enumerate(tests, start=1):
        item_code = str(test.get("item_code") or "")
        if not item_code.startswith("food_"):
            continue
        name = str(test.get("test_name") or test.get("indicator") or "").strip()
        if not name:
            continue
        status = _food_status(str(test.get("result") or ""))
        index = _parse_int(test.get("index")) or len(results) + 1
        results.append(
            {
                "index": index,
                "code": item_code.removeprefix("food_"),
                "name": name,
                "result": str(test.get("result") or "").strip() or "待复核",
                "status": status,
                "status_label": f"（{status}）",
                "sign": _food_sign(status),
                "reference_range": str(test.get("reference_range") or "阴性").strip(),
                "flag": str(test.get("indicator") or "").strip(),
                "method": str(test.get("method") or "").strip(),
                "css_class": _food_css_class(status),
                "status_class": _food_status_class(status),
                "sort_index": index or fallback_index,
            }
        )
    return sorted(results, key=lambda item: (int(item.get("sort_index") or 0), str(item.get("name") or "")))


def _food_result_summary(food_results: list[dict[str, Any]]) -> dict[str, Any]:
    positive = [item for item in food_results if item.get("status") == "阳性"]
    weak = [item for item in food_results if item.get("status") == "弱阳性"]
    negative = [item for item in food_results if item.get("status") == "阴性"]
    pending = [item for item in food_results if item.get("status") not in {"阳性", "弱阳性", "阴性"}]
    attention = positive + weak
    recommended = negative[:6]
    return {
        "total_count": len(food_results),
        "positive_count": len(positive),
        "weak_positive_count": len(weak),
        "negative_count": len(negative),
        "pending_count": len(pending),
        "positive_foods": positive,
        "weak_positive_foods": weak,
        "attention_foods": attention,
        "avoid_foods": attention[:6],
        "recommended_foods": recommended,
        "pending_foods": pending,
        "attention_names_display": _names_display(attention, "未见阳性或弱阳性食物"),
        "positive_names_display": _names_display(positive, "未见阳性食物"),
        "weak_names_display": _names_display(weak, "未见弱阳性食物"),
        "recommended_names_display": _names_display(recommended, "待结合饮食记录补充"),
        "overview": _food_overview(len(food_results), len(positive), len(weak), len(negative), len(pending)),
    }


def _focus_items(food_summary: dict[str, Any], indicators: dict[str, Any]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for item in food_summary.get("attention_foods", []):
        if isinstance(item, dict):
            candidates.append(_food_focus_item(item))
    if not candidates:
        if int(food_summary.get("negative_count") or 0) and not int(food_summary.get("pending_count") or 0):
            candidates.append(
                _make_focus_item(
                    "食物不耐受42项",
                    "未见阳性",
                    f"本次{food_summary.get('total_count') or 0}项食物不耐受结果均为阴性，未见需要优先规避的阳性食物。",
                    "negative",
                )
            )
        else:
            candidates.append(
                _make_focus_item(
                    "食物不耐受结果",
                    "需人工复核",
                    "当前OCR结果存在缺失或待复核项目，建议结合原始报告逐项确认后再制定饮食计划。",
                    "pending",
                )
            )

    immune_focus = _immune_focus(indicators)
    if immune_focus:
        candidates.append(immune_focus)
    if len(candidates) < 2:
        candidates.append(
            _make_focus_item(
                "饮食管理",
                "维持观察",
                "建议保持多样化饮食，持续记录饮食与症状变化，后续按需复评。",
                "maintenance",
            )
        )
    return {"focus_1": candidates[0], "focus_2": candidates[1]}


def _food_focus_item(item: dict[str, Any]) -> dict[str, Any]:
    name = str(item.get("name") or "")
    status = str(item.get("status") or "需关注")
    return _make_focus_item(name, status, _food_summary(name, status), "food")


def _make_focus_item(name: str, status: str, summary: str, kind: str) -> dict[str, Any]:
    detail = _focus_detail_cards(name, status, kind)
    return {
        "name": name,
        "status": status,
        "status_label": f"（{status}）",
        "status_class": _food_status_class(status),
        "summary": summary,
        **detail,
    }


def _focus_detail_cards(name: str, status: str, kind: str) -> dict[str, Any]:
    if kind == "food":
        return {
            "impact": _numbered_cards(
                [
                    ("胃", "消化不适", "可结合腹胀、腹泻、腹痛等症状记录观察。"),
                    ("肤", "皮肤反应", "关注皮疹、瘙痒、湿疹样改变与摄入时间关系。"),
                    ("疲", "疲劳负担", "记录食用后疲劳、困倦或精神状态波动。"),
                    ("炎", "慢性刺激", "持续摄入可能增加个体炎症或不适负担。"),
                ]
            ),
            "advice": _numbered_cards(
                [
                    ("停", "阶段规避", f"建议阶段性减少或暂停{name}摄入。"),
                    ("签", "查看标签", f"注意加工食品中是否含有{name}相关成分。"),
                    ("替", "选择替代", "用阴性且耐受良好的食物补足同类营养来源。"),
                    ("记", "症状记录", "记录摄入量、时间与症状变化，便于复评。"),
                ]
            ),
            "caution": _numbered_cards(
                [
                    ("症", "观察症状", f"关注摄入{name}后的消化、皮肤或疲劳反应。"),
                    ("控", "控制频率", "按结果等级降低摄入频率，避免连续暴露。"),
                    ("记", "保留记录", "保留饮食与症状记录，供后续人工评估。"),
                    ("复", "阶段复评", "执行一段时间后结合症状决定是否复查。"),
                ]
            ),
        }
    if kind == "negative":
        return {
            "impact": _numbered_cards(
                [
                    ("阴", "未见阳性", "本次42项均为阴性，当前未提示明确食物不耐受。"),
                    ("衡", "保持均衡", "维持多样化饮食结构，避免不必要的长期忌口。"),
                    ("记", "记录变化", "如有不适，继续记录饮食、作息与症状。"),
                    ("复", "按需复评", "症状持续或变化时再结合专业意见复核。"),
                ]
            ),
            "advice": _numbered_cards(
                [
                    ("多", "多样饮食", "在自身耐受基础上保持谷物、蛋白、蔬果均衡。"),
                    ("鲜", "优先新鲜", "选择新鲜、少加工食物，减少隐性添加影响。"),
                    ("稳", "稳定节律", "保持规律进餐与睡眠，降低胃肠波动。"),
                    ("查", "症状复核", "如症状明显，建议结合其他检查寻找原因。"),
                ]
            ),
            "caution": _numbered_cards(
                [
                    ("辨", "不盲目忌口", "阴性结果不支持随意扩大规避食物范围。"),
                    ("记", "记录诱因", "关注压力、睡眠、加工食品等非食物不耐受因素。"),
                    ("调", "个体调整", "按个人体验微调高频食物摄入。"),
                    ("询", "专业咨询", "持续不适时咨询医生或营养师。"),
                ]
            ),
        }
    if kind == "maintenance":
        return {
            "impact": _numbered_cards(
                [
                    ("稳", "维持稳定", "当前未见明确食物不耐受阳性线索，以稳定饮食为主。"),
                    ("衡", "营养均衡", "保持蛋白、谷物、蔬果和脂肪来源合理搭配。"),
                    ("记", "记录体验", "如有不适，记录具体食物、时间和症状变化。"),
                    ("调", "个体调整", "根据个人耐受度微调高频食物和加工食品摄入。"),
                ]
            ),
            "advice": _numbered_cards(
                [
                    ("鲜", "优先天然", "选择新鲜少加工食物，减少添加剂和高糖高油负担。"),
                    ("轮", "适度轮替", "常吃食物可适度轮替，避免长期单一饮食。"),
                    ("动", "规律作息", "配合睡眠、运动和压力管理支持肠道状态。"),
                    ("询", "必要咨询", "持续不适时结合医生或营养师意见进一步评估。"),
                ]
            ),
            "caution": _numbered_cards(
                [
                    ("忌", "避免过度忌口", "阴性结果不支持自行扩大长期禁食范围。"),
                    ("观", "观察变化", "新发症状应结合饮食、作息、压力等因素分析。"),
                    ("标", "关注标签", "减少高加工食品和不明配料带来的干扰。"),
                    ("复", "按需复评", "症状持续或明显变化时再考虑复查。"),
                ]
            ),
        }
    return {
        "impact": _numbered_cards(
            [
                ("核", "结果复核", "结合原始报告确认缺失或异常项目。"),
                ("记", "症状记录", "记录饮食、作息与不适发生时间。"),
                ("衡", "均衡饮食", "在确认前避免过度限制食物种类。"),
                ("复", "阶段复评", "必要时按专业意见进行复查。"),
            ]
        ),
        "advice": _numbered_cards(
            [
                ("补", "补充资料", "补齐缺失结果、参考范围和单位信息。"),
                ("查", "人工核对", "由专业人员核对OCR识别结果。"),
                ("稳", "维持稳定", "暂以稳定、清淡、多样饮食为主。"),
                ("询", "专业意见", "结合症状和既往史制定下一步方案。"),
            ]
        ),
        "caution": _numbered_cards(
            [
                ("核", "先核实", "结果未完整确认前不做绝对化判断。"),
                ("控", "避免极端", "不建议自行大范围长期忌口。"),
                ("记", "持续记录", "保留饮食与症状变化供复核使用。"),
                ("复", "必要复查", "如症状明显，按专业建议复查。"),
            ]
        ),
    }


def _numbered_cards(items: list[tuple[str, str, str]]) -> dict[str, dict[str, str]]:
    return {
        f"item_{index}": {"symbol": symbol, "title": title, "body": body}
        for index, (symbol, title, body) in enumerate(items, start=1)
    }


def _immune_focus(indicators: dict[str, Any]) -> dict[str, Any] | None:
    ordered_codes = ["total_ige", "igg1", "igg2", "igg3", "igg4"]
    for code in ordered_codes:
        indicator = indicators.get(code, {})
        if not isinstance(indicator, dict):
            continue
        status = str(indicator.get("status") or "")
        result = str(indicator.get("result") or "")
        if result in {"", "未识别"}:
            continue
        if status not in {"正常", "待补充"}:
            return _make_focus_item(
                str(indicator.get("name") or code.upper()),
                status,
                f"{indicator.get('name') or code.upper()}结果为{result}，提示免疫相关指标需结合参考范围与症状记录复核。",
                "pending",
            )
    if any(isinstance(item, dict) and str(item.get("result") or "") not in {"", "未识别"} for item in indicators.values()):
        return _make_focus_item("免疫指标", "已识别", "已识别免疫相关指标，建议结合食物不耐受结果和症状记录综合判断。", "maintenance")
    return None


def _priorities(food_summary: dict[str, Any]) -> dict[str, dict[str, str]]:
    if int(food_summary.get("positive_count") or 0) or int(food_summary.get("weak_positive_count") or 0):
        return {
            "priority_1": {"title": "规避重点食物", "body": "优先暂停阳性食物摄入，减少持续免疫刺激。"},
            "priority_2": {"title": "执行轮替饮食", "body": "采用4天轮替策略，降低重复暴露负担。"},
            "priority_3": {"title": "支持肠道屏障", "body": "关注肠道菌群平衡、消化吸收和黏膜支持。"},
            "priority_4": {"title": "记录症状变化", "body": "同步记录饮食、作息与症状，为后续复评提供依据。"},
        }
    if int(food_summary.get("pending_count") or 0):
        return {
            "priority_1": {"title": "人工复核结果", "body": "先核对待复核食物项目，避免误判。"},
            "priority_2": {"title": "保留饮食记录", "body": "同步记录进食、症状和作息变化。"},
            "priority_3": {"title": "维持均衡饮食", "body": "在确认前避免过度限制食物种类。"},
            "priority_4": {"title": "按需阶段复评", "body": "症状持续时结合专业意见复查。"},
        }
    return {
        "priority_1": {"title": "维持多样饮食", "body": "42项未见阳性，保持均衡饮食结构。"},
        "priority_2": {"title": "记录症状变化", "body": "如有不适，记录饮食与发生时间。"},
        "priority_3": {"title": "优化生活方式", "body": "规律作息、适量运动，支持肠道状态。"},
        "priority_4": {"title": "按需复核评估", "body": "症状持续时结合专业意见进一步评估。"},
    }


def _diet_plan(food_summary: dict[str, Any]) -> dict[str, Any]:
    avoid_foods = [item for item in food_summary.get("avoid_foods", []) if isinstance(item, dict)]
    recommended_foods = [item for item in food_summary.get("recommended_foods", []) if isinstance(item, dict)]
    if avoid_foods:
        avoid_note = "以下食物在本次结果中提示阳性或弱阳性，建议阶段性减少或暂停摄入。"
        avoid_attention = "注意：避免食用上述食物及其加工制品，仔细阅读食品标签，防止隐性摄入。"
    else:
        avoid_note = "本次食物不耐受结果未见阳性或弱阳性项目，暂不生成重点规避清单。"
        avoid_attention = "注意：不建议因本次阴性结果而盲目扩大忌口范围，如有不适请结合症状记录复核。"
    return {
        "avoid_foods": avoid_foods,
        "recommended_foods": recommended_foods,
        "avoid_note": avoid_note,
        "recommended_note": "以下为本次结果中阴性的食物，可结合个人耐受情况作为日常饮食选择。",
        "avoid_attention": avoid_attention,
        "recommended_attention": "建议：选择新鲜、天然的食物，采用蒸、煮、炖等健康烹饪方式，保持食物营养。",
        "avoid_foods_display": _names_display(avoid_foods, "未见需规避食物"),
        "recommended_foods_display": _names_display(recommended_foods, "待结合饮食记录补充"),
    }


def _food_status(result: str) -> str:
    text = str(result or "").strip()
    lowered = text.lower()
    if not text:
        return "待复核"
    if any(token in text for token in ["弱阳", "卤", "±"]) or "weak" in lowered:
        return "弱阳性"
    if any(token in text for token in ["阳", "+"]) or "positive" in lowered:
        return "阳性"
    if any(token in text for token in ["阴", "-", "正常"]) or "negative" in lowered:
        return "阴性"
    return text


def _food_summary(name: str, status: str) -> str:
    if status == "阳性":
        return f"{name}当前提示明确反应，建议优先暂停摄入并观察症状变化。"
    if status == "弱阳性":
        return f"{name}当前提示轻度反应，建议减少摄入频率并结合症状记录复核。"
    return f"{name}当前结果需结合原始报告与实际症状进一步确认。"


def _overall_summary(food_summary: dict[str, Any], indicators: dict[str, Any]) -> str:
    total = int(food_summary.get("total_count") or 0)
    positive = int(food_summary.get("positive_count") or 0)
    weak = int(food_summary.get("weak_positive_count") or 0)
    pending = int(food_summary.get("pending_count") or 0)
    immune_attention = _immune_attention_names(indicators)
    if positive or weak:
        names = str(food_summary.get("attention_names_display") or "")
        return f"本次共识别{total}项食物不耐受结果，其中{positive}项阳性、{weak}项弱阳性，重点关注{_names_safe(names)}。建议结合症状记录执行阶段性规避与轮替饮食。"
    if pending:
        return f"本次共识别{total}项食物不耐受结果，其中{pending}项仍需人工复核，建议先核对原始报告后再形成最终饮食管理方案。"
    suffix = f"；同时关注{immune_attention}" if immune_attention else ""
    return f"本次{total}项食物不耐受结果均为阴性，未见需优先规避的阳性食物{suffix}。建议保持多样化饮食，并结合症状记录动态观察。"


def _ai_insight(food_summary: dict[str, Any], indicators: dict[str, Any]) -> str:
    immune_attention = _immune_attention_names(indicators)
    if int(food_summary.get("positive_count") or 0) or int(food_summary.get("weak_positive_count") or 0):
        return f"AI提示：建议围绕{food_summary.get('attention_names_display')}进行阶段性规避、标签核查和症状记录，8-12周后结合体验复评。"
    if int(food_summary.get("pending_count") or 0):
        return "AI提示：当前存在待复核食物项目，建议先完成OCR与原始报告核对，再输出最终饮食规避建议。"
    if immune_attention:
        return f"AI提示：食物不耐受42项未见阳性，建议把管理重点放在症状记录、生活方式稳定性以及{immune_attention}的人工复核。"
    return "AI提示：本次42项食物不耐受结果均为阴性，可维持均衡饮食；如仍有不适，建议从作息、压力、胃肠状态和其他检查线索综合排查。"


def _overall_summary_brief(food_summary: dict[str, Any], indicators: dict[str, Any]) -> str:
    total = int(food_summary.get("total_count") or 0)
    positive = int(food_summary.get("positive_count") or 0)
    weak = int(food_summary.get("weak_positive_count") or 0)
    pending = int(food_summary.get("pending_count") or 0)
    immune_attention = _immune_attention_names(indicators)
    if positive or weak:
        return f"本次{total}项食物不耐受中阳性{positive}项、弱阳性{weak}项，建议围绕{food_summary.get('attention_names_display')}进行阶段性饮食管理。"
    if pending:
        return f"本次{total}项食物结果中有{pending}项需复核，建议先核对原始报告后再形成饮食方案。"
    suffix = f"；{immune_attention}需结合症状复核" if immune_attention else ""
    return f"本次{total}项食物不耐受均为阴性，未见需优先规避食物{suffix}。"


def _ai_insight_brief(food_summary: dict[str, Any], indicators: dict[str, Any]) -> str:
    immune_attention = _immune_attention_names(indicators)
    if int(food_summary.get("positive_count") or 0) or int(food_summary.get("weak_positive_count") or 0):
        return "AI提示：执行规避与轮替饮食，记录症状变化，8-12周后按需复评。"
    if int(food_summary.get("pending_count") or 0):
        return "AI提示：先完成待复核项目确认，避免基于不完整结果扩大忌口。"
    if immune_attention:
        return f"AI提示：食物结果平稳，重点关注{immune_attention}及症状记录。"
    return "AI提示：维持均衡饮食和规律作息，如仍不适再结合其他线索评估。"


def _ai_assisted_diagnosis(food_summary: dict[str, Any], indicators: dict[str, Any]) -> str:
    total = int(food_summary.get("total_count") or 0)
    positive = int(food_summary.get("positive_count") or 0)
    weak = int(food_summary.get("weak_positive_count") or 0)
    pending = int(food_summary.get("pending_count") or 0)
    if positive or weak:
        return f"AI辅助诊断：本次{total}项食物不耐受中，{positive}项阳性、{weak}项弱阳性，建议优先围绕{food_summary.get('attention_names_display')}进行阶段性饮食管理，并结合症状记录人工复核。"
    if pending:
        return f"AI辅助诊断：本次识别到{total}项食物结果，其中{pending}项需人工复核，暂不建议基于未确认项目扩大忌口范围。"
    immune_attention = _immune_attention_names(indicators)
    suffix = f"；免疫相关指标方面需关注{immune_attention}" if immune_attention else ""
    return f"AI辅助诊断：本次{total}项食物不耐受结果均为阴性，未提示明确食物IgG相关不耐受反应{suffix}。"


def _followup_advice(food_summary: dict[str, Any]) -> str:
    if int(food_summary.get("positive_count") or 0) or int(food_summary.get("weak_positive_count") or 0):
        return "建议按8-12周计划执行饮食调整与生活方式干预，并记录症状、进食种类和复评变化。"
    if int(food_summary.get("pending_count") or 0):
        return "建议先完成人工复核；如症状持续，再结合专业意见补充检查或阶段复评。"
    return "建议维持均衡饮食和规律生活方式，如出现持续不适，结合饮食症状记录与专业意见进一步评估。"


def _indicator_status(result: str, flag: str, low: float | None, high: float | None) -> str:
    text = f"{result} {flag}".strip()
    if not str(result or "").strip():
        return "待补充"
    if any(token in text for token in ["↑", "偏高", "高于", "升高"]):
        return "偏高"
    if any(token in text for token in ["↓", "偏低", "低于", "降低"]):
        return "偏低"
    value = _parse_number(result)
    if value is not None and low is not None and value < low:
        return "偏低"
    if value is not None and high is not None and value > high:
        return "偏高"
    if any(token in text for token in ["阳性", "+"]):
        return "阳性"
    if low is not None or high is not None:
        return "正常"
    return "已识别"


def _range_note(result: str, reference: str, status: str) -> str:
    if not result:
        return "当前OCR未识别到该指标结果，建议人工核对原始报告。"
    if not reference:
        return "当前未识别到稳定参考范围，建议人工复核。"
    if status == "正常":
        return "结果处于本次识别参考范围内，请结合原始报告综合判断。"
    return f"结果提示{status}，请结合原始参考范围、症状和专业意见复核。"


def _indicator_name(code: str) -> str:
    return {"igg1": "IgG1", "igg2": "IgG2", "igg3": "IgG3", "igg4": "IgG4", "total_ige": "总IgE"}.get(code, code.upper())


def _parse_reference_range(reference: str) -> tuple[float | None, float | None]:
    numbers = [_parse_number(match.group(0)) for match in re.finditer(r"\d+(?:\.\d+)?", str(reference or ""))]
    cleaned = [number for number in numbers if number is not None]
    if len(cleaned) < 2:
        return None, None
    low, high = cleaned[0], cleaned[1]
    if low > high:
        low, high = high, low
    return low, high


def _parse_number(value: Any) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _parse_int(value: Any) -> int:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else 0


def _reference_display(reference: str, unit: str) -> str:
    if not reference:
        return "待补充"
    if unit and unit not in reference:
        return f"{reference} {unit}"
    return reference


def _marker_percent(value: float | None, low: float | None, high: float | None) -> str:
    if value is None or low is None or high is None or high <= low:
        return "50%"
    if value <= low:
        return "8%"
    if value >= high:
        return "92%"
    percent = 8 + ((value - low) / (high - low)) * 84
    return f"{max(8, min(92, percent)):.0f}%"


def _compact_number(value: float | None) -> str:
    if value is None:
        return "—"
    return str(int(value)) if value.is_integer() else f"{value:g}"


def _food_sign(status: str) -> str:
    if status == "阳性":
        return "+"
    if status == "弱阳性":
        return "±"
    if status == "阴性":
        return "−"
    return "?"


def _food_css_class(status: str) -> str:
    if status == "阳性":
        return "alert"
    if status == "弱阳性":
        return "warn"
    return ""


def _food_status_class(status: str) -> str:
    if status == "阳性":
        return "red"
    if status == "弱阳性":
        return "orange"
    if status in {"阴性", "未见阳性", "维持观察", "已识别", "正常"}:
        return "green"
    return "orange"


def _names_display(items: list[dict[str, Any]], fallback: str) -> str:
    names = [str(item.get("name") or "").strip() for item in items if isinstance(item, dict) and str(item.get("name") or "").strip()]
    return "、".join(names) if names else fallback


def _food_overview(total: int, positive: int, weak: int, negative: int, pending: int) -> str:
    if positive or weak:
        return f"共{total}项，阳性{positive}项，弱阳性{weak}项，阴性{negative}项。"
    if pending:
        return f"共{total}项，阴性{negative}项，待复核{pending}项。"
    return f"共{total}项，全部为阴性。"


def _immune_attention_names(indicators: dict[str, Any]) -> str:
    names: list[str] = []
    for item in indicators.values():
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "")
        result = str(item.get("result") or "")
        if result in {"", "未识别"}:
            continue
        if status not in {"正常", "待补充", "已识别"}:
            names.append(f"{item.get('name')} {status}")
    return "、".join(names)


def _first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text and text not in {"/", "-", "—", "None"}:
            return text
    return ""


def _names_safe(value: str) -> str:
    return value or "识别到的重点食物"
