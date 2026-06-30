from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import re

from bs4 import BeautifulSoup

from app.core.config import settings
from app.services.report_review import find_active_report_id_for_case, register_rendered_report

RESULT_COLOR_CLASSES = ("green-text", "red-text", "orange-text")
P17_STATUS_CLASSES = ("status-positive", "status-negative", "status-orange", "status-red", "status-purple")
P07_STATUS_CLASSES = ("ok-text", "green-text", "red-text", "orange-text", "status-high", "status-low")
P17_GOOD_KEYS = ("卷曲乳杆菌", "詹氏乳杆菌", "加氏乳杆菌", "惰性乳杆菌", "双歧杆菌", "good_bacteria")
P17_CONDITIONAL_KEYS = (
    "白假丝酵母菌",
    "光滑假丝酵母菌",
    "热带假丝酵母菌",
    "耳道假丝酵母菌",
    "克柔假丝酵母菌",
    "都柏林假丝酵母菌",
    "近平滑假丝酵母菌",
    "b族链球菌",
    "亨氏巴尔通体",
    "细小棒状杆菌",
    "衣氏放线菌",
    "阴道加德纳菌",
    "阴道阿托波氏菌",
    "纤毛菌",
    "微小脲原体",
    "解脲脲原体",
    "人型支原体",
    "conditional_pathogen",
)
P17_PATHOGEN_KEYS = (
    "阴道毛滴虫",
    "淋球菌",
    "杜克雷嗜血杆菌",
    "生殖支原体",
    "沙眼衣原体",
    "梅毒螺旋体",
    "阿米巴原虫",
    "单纯疱疹病毒",
    "人乳头瘤病毒",
    "pathogen",
)
P03_STATE_CLASSES = ("result-normal", "result-warning", "result-abnormal")
P04_STATUS_CLASSES = ("status-normal", "status-high", "status-low", "green-title", "orange-text", "red-text", "blue-title")
P06_STATUS_CLASSES = ("status-normal", "status-high", "status-low", "green-title", "orange-text", "red-text")
P08_STATUS_CLASSES = ("red", "green", "orange", "red-text", "green-text", "orange-text", "status-high", "status-normal", "status-low")
P09_STATUS_CLASSES = ("normal-pill", "warn-pill", "status-high", "status-normal", "status-low")
P10_STATUS_CLASSES = ("status-green", "status-orange", "status-blue", "status-red")
P11_PILL_CLASSES = ("pill-red", "pill-orange", "pill-green")
P11_FOCUS_STATUS_CLASSES = ("status-red", "status-orange", "status-green")
P12_STATUS_CLASSES = ("red", "green", "orange", "red-text", "green-text", "orange-text", "status-high", "status-normal", "status-low")
P03_INDICATOR_CODES = (
    "alb",
    "glucose",
    "gsp",
    "hba1c",
    "avg_glucose",
    "hba1",
    "hba1ab",
    "insulin",
    "c_peptide",
    "tg",
    "tch",
    "hdl_c",
    "ldl_c",
    "apo_a1",
    "apo_b",
    "apo_a1_b_ratio",
    "lp_a",
    "tg_hdl_ratio",
    "homa_ir",
    "non_hdl_c",
)
P03_STATE_TARGET_CLASSES = (
    "metric-card",
    "lipid-card",
    "value-card",
    "balance-card",
    "compact-balance",
    "range-bar",
    "semi-gauge",
    "risk-card",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def render_report(package_code: str, report_data: dict[str, Any]) -> dict[str, str]:
    report_data = _apply_package_fixed_render_values(package_code, report_data)
    case_id = str(report_data.get("case_id") or "")
    report_id = find_active_report_id_for_case(case_id=case_id, package_code=package_code) or f"report_{uuid.uuid4().hex[:12]}"
    target_dir = settings.cases_dir / report_id / "html"
    template_dir = settings.packages_dir / package_code / "templates" / "html"
    if not template_dir.exists():
        raise FileNotFoundError(f"Missing template directory for {package_code}")

    if target_dir.parent.exists():
        shutil.rmtree(target_dir.parent, ignore_errors=True)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template_dir, target_dir, dirs_exist_ok=True)
    (target_dir.parent / "report-data.json").write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for html_path in target_dir.glob("pages/*.html"):
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
        for node in soup.select("[data-field]"):
            key = node.get("data-field")
            value = _resolve(report_data, key or "")
            if value is not None:
                node.clear()
                text_value = str(value)
                node.append(text_value)
                _apply_fit_classes(soup, node, key or "", text_value)
                _apply_result_color_class(node, key or "", text_value)
        if package_code.upper() == "P01":
            _apply_p01_dynamic_styles(soup, report_data)
        if package_code.upper() == "P05":
            _apply_p05_dynamic_styles(soup, report_data)
        if package_code.upper() == "P03":
            _apply_p03_dynamic_styles(soup, report_data)
        if package_code.upper() == "P04":
            _apply_p04_dynamic_styles(soup)
        if package_code.upper() == "P06":
            _apply_p06_dynamic_styles(soup)
        if package_code.upper() == "P07":
            _apply_p07_dynamic_styles(soup)
        if package_code.upper() == "P08":
            _apply_p08_dynamic_styles(soup)
        if package_code.upper() == "P09":
            _apply_p09_dynamic_styles(soup, report_data)
        if package_code.upper() == "P10":
            _apply_p10_dynamic_styles(soup)
        if package_code.upper() == "P11":
            _apply_p11_dynamic_styles(soup, report_data)
        if package_code.upper() == "P12":
            _apply_p12_dynamic_styles(soup, report_data)
        if package_code.upper() == "P15":
            _apply_p15_dynamic_styles(soup, report_data)
        if package_code.upper() == "P17":
            _apply_p17_dynamic_styles(soup)
        html_path.write_text(str(soup), encoding="utf-8")

    relative_index = (target_dir / "index.html").relative_to(settings.storage_dir).as_posix()
    result = {
        "report_id": report_id,
        "html_path": str(target_dir / "index.html"),
        "html_url": f"/storage/{relative_index}",
        "created_at": now_iso(),
    }
    register_rendered_report(
        report_id=report_id,
        package_code=package_code,
        report_data=report_data,
        html_path=result["html_path"],
    )
    return result


def _apply_package_fixed_render_values(package_code: str, report_data: dict[str, Any]) -> dict[str, Any]:
    if package_code.upper() != "P10":
        return report_data

    sample = report_data.setdefault("sample", {})
    if isinstance(sample, dict):
        sample["type"] = "血清/EDTA抗凝血"

    report = report_data.setdefault("report", {})
    if isinstance(report, dict):
        report["method"] = "基因测序&化学发光&ELISA法"

    _apply_p10_render_values(report_data)
    return report_data


def _apply_p10_render_values(report_data: dict[str, Any]) -> None:
    p10 = report_data.setdefault("p10", {})
    if not isinstance(p10, dict):
        return
    indicators = p10.get("indicators", {})
    if not isinstance(indicators, dict):
        indicators = {}
    deep_dive = p10.get("deep_dive", {})
    if not isinstance(deep_dive, dict):
        deep_dive = {}

    display = p10.setdefault("display", {})
    if not isinstance(display, dict):
        display = {}
        p10["display"] = display

    psa = _p10_indicator(indicators, "psa")
    psa_free = _p10_indicator(indicators, "psa_free")
    psa_ratio = _p10_indicator(indicators, "psa_ratio")
    cyp1a1 = _p10_indicator(indicators, "cyp1a1")
    aldh2 = _p10_indicator(indicators, "aldh2")
    lct = _p10_indicator(indicators, "lct")
    cyp1a2 = _p10_indicator(indicators, "cyp1a2")

    display["psa_status"] = _p10_psa_status_label(psa, psa_free, psa_ratio)
    display["psa_result"] = _p10_join_display(
        f"总PSA {_p10_compact_indicator_value(psa)}",
        f"游离PSA {_p10_compact_indicator_value(psa_free)}",
        f"比值 {_p10_compact_indicator_value(psa_ratio)}",
    )

    display["smoking_status"] = _p10_gene_status_label("smoking", cyp1a1, _p10_summary(deep_dive, "smoking"))
    display["alcohol_status"] = _p10_gene_status_label("alcohol", aldh2, _p10_summary(deep_dive, "alcohol"))
    display["alcohol_note"] = _p10_alcohol_note(aldh2, _p10_summary(deep_dive, "alcohol"))
    display["lactose_status"] = _p10_gene_status_label("lactose", lct, _p10_summary(deep_dive, "lactose"))
    display["caffeine_status"] = _p10_gene_status_label("caffeine", cyp1a2, _p10_summary(deep_dive, "caffeine"))

    display["smoking_result"] = _p10_gene_result_label("CYP1A1", cyp1a1, display["smoking_status"])
    display["alcohol_result"] = _p10_gene_result_label("ALDH2", aldh2, display["alcohol_status"])
    display["lactose_result"] = _p10_gene_result_label("MCM6", lct, display["lactose_status"])
    display["caffeine_result"] = _p10_gene_result_label("CYP1A2", cyp1a2, display["caffeine_status"])
    display["lactose_heading_note"] = f"（{display['lactose_status']}）"
    display["caffeine_heading_note"] = f"（{display['caffeine_status']}）"
    display["metabolism_summary"] = _p10_join_display(
        f"CYP1A1 {_p10_gene_value(cyp1a1)}提示{display['smoking_status']}",
        f"ALDH2 {_p10_gene_value(aldh2)}提示{display['alcohol_status']}",
        f"MCM6 {_p10_gene_value(lct)}提示{display['lactose_status']}",
        f"CYP1A2 {_p10_gene_value(cyp1a2)}提示{display['caffeine_status']}",
    ) + "。"
    display["ai_insight_brief"] = _p10_ai_insight_brief(indicators, display)
    display["psa_summary_brief"] = _p10_psa_summary_brief(psa, psa_free, psa_ratio)
    display["metabolism_summary_brief"] = _p10_metabolism_summary_brief(
        cyp1a1,
        aldh2,
        lct,
        cyp1a2,
        display,
    )

    priorities = p10.get("priorities", {})
    if isinstance(priorities, dict):
        for index in range(1, 5):
            priority = priorities.get(f"priority_{index}", {})
            if isinstance(priority, dict):
                display[f"priority_{index}"] = _p10_priority_display(priority)


def _p10_indicator(indicators: dict[str, Any], code: str) -> dict[str, Any]:
    item = indicators.get(code, {})
    return item if isinstance(item, dict) else {}


def _p10_summary(deep_dive: dict[str, Any], code: str) -> str:
    bucket = deep_dive.get(code, {})
    if not isinstance(bucket, dict):
        return ""
    return str(bucket.get("summary") or "").strip()


def _p10_join_display(*parts: str) -> str:
    cleaned = [str(part or "").strip(" ；;") for part in parts if str(part or "").strip(" ；;")]
    return "；".join(cleaned)


def _p10_compact_indicator_value(indicator: dict[str, Any]) -> str:
    value = str(indicator.get("result_display") or indicator.get("result") or "").strip()
    value = value.replace("（↑）", "↑").replace("（↓）", "↓")
    value = value.replace("(↑)", "↑").replace("(↓)", "↓")
    value = re.sub(r"\s*ng/mL\b", "", value, flags=re.IGNORECASE)
    return value or "待识别"


def _p10_psa_status_label(*indicators: dict[str, Any]) -> str:
    text = " ".join(
        str(item.get(key) or "")
        for item in indicators
        for key in ("status", "result_display", "result")
    )
    if not text.strip() or "待识别" in text:
        return "待识别"
    if any(marker in text for marker in ("↑", "↓", "异常", "偏高", "偏低")):
        return "需关注"
    return "正常"


def _p10_gene_status_label(kind: str, indicator: dict[str, Any], summary: str) -> str:
    text = f"{indicator.get('gene_type') or ''} {indicator.get('result') or ''} {indicator.get('result_display') or ''} {indicator.get('status') or ''} {summary}"
    compact = "".join(text.split())
    if not compact or "待识别" in compact:
        return "待识别"
    if kind == "alcohol":
        if "风险低" in compact or "正常" in compact or "GG" in compact:
            return "代谢正常"
        if any(word in compact for word in ("弱", "较慢", "下降", "风险高", "乙醛堆积", "GA", "AA")):
            return "代谢较弱"
    if kind == "lactose":
        if "不耐受" in compact or "较低" in compact or "风险" in compact:
            return "不耐受风险"
        if "正常" in compact or "可正常" in compact or "耐受" in compact:
            return "耐受正常"
    if any(word in compact for word in ("中等", "一般", "中代谢")):
        return "中等代谢"
    if "快" in compact:
        return "代谢较快"
    if any(word in compact for word in ("慢", "较低", "较弱")):
        return "代谢较慢"
    return "已识别"


def _p10_alcohol_note(indicator: dict[str, Any], summary: str) -> str:
    text = f"{indicator.get('gene_type') or ''} {summary}"
    if "风险低" in text or "正常" in text or "GG" in text:
        return "乙醛风险低"
    if "风险" in text or "弱" in text or "GA" in text or "AA" in text:
        return "需控酒精"
    return ""


def _p10_gene_value(indicator: dict[str, Any]) -> str:
    return str(indicator.get("gene_type") or indicator.get("result_display") or indicator.get("result") or "待识别").strip()


def _p10_gene_result_label(name: str, indicator: dict[str, Any], status: str) -> str:
    value = _p10_gene_value(indicator)
    if value == "待识别":
        return f"{name} 待识别"
    if status and status not in {"已识别", "待识别"}:
        return f"{name} {value}（{status}）"
    return f"{name} {value}"


def _p10_priority_display(priority: dict[str, Any]) -> str:
    title = str(priority.get("title") or "").strip()
    body = str(priority.get("body") or "").strip()
    return _p10_compact_priority_text(title or body)


def _p10_compact_priority_text(text: str) -> str:
    cleaned = re.sub(r"\s+", "", str(text or "").strip())
    if not cleaned:
        return ""
    cleaned = re.split(r"[：:，,。；;、]", cleaned, maxsplit=1)[0]
    if len(cleaned) <= 12:
        return cleaned
    return cleaned[:12]


def _p10_ai_insight_brief(indicators: dict[str, Any], display: dict[str, Any]) -> str:
    focus_items: list[str] = []
    psa = _p10_indicator(indicators, "psa")
    psa_ratio = _p10_indicator(indicators, "psa_ratio")
    dhea = _p10_indicator(indicators, "dhea")
    inhibin_b = _p10_indicator(indicators, "inhibin_b")
    if display.get("psa_status") != "正常":
        focus_items.append(f"PSA/比值{_p10_compact_indicator_value(psa_ratio)}")
    if _p10_is_attention_indicator(dhea):
        focus_items.append(f"DHEA{_p10_compact_indicator_value(dhea)}")
    if _p10_is_attention_indicator(inhibin_b):
        focus_items.append(f"抑制素B{_p10_compact_indicator_value(inhibin_b)}")
    if focus_items:
        return f"本次重点关注：{'、'.join(focus_items[:3])}，建议结合生活方式与专业意见定期复评。"
    return "本次核心指标总体平稳，建议保持健康生活方式，并按计划定期复评。"


def _p10_psa_summary_brief(psa: dict[str, Any], psa_free: dict[str, Any], psa_ratio: dict[str, Any]) -> str:
    status = _p10_psa_status_label(psa, psa_free, psa_ratio)
    if status == "正常":
        return f"前列腺健康：总PSA {_p10_compact_indicator_value(psa)}，当前处于参考范围内，建议常规随访。"
    return (
        "前列腺健康："
        f"总PSA {_p10_compact_indicator_value(psa)}，"
        f"游离PSA {_p10_compact_indicator_value(psa_free)}，"
        f"比值 {_p10_compact_indicator_value(psa_ratio)}，建议动态监测。"
    )


def _p10_metabolism_summary_brief(
    cyp1a1: dict[str, Any],
    aldh2: dict[str, Any],
    lct: dict[str, Any],
    cyp1a2: dict[str, Any],
    display: dict[str, Any],
) -> str:
    return _p10_join_display(
        f"CYP1A1 {_p10_gene_value(cyp1a1)}（{display.get('smoking_status') or '已识别'}）",
        f"ALDH2 {_p10_gene_value(aldh2)}（{display.get('alcohol_status') or '已识别'}）",
        f"MCM6 {_p10_gene_value(lct)}（{display.get('lactose_status') or '已识别'}）",
        f"CYP1A2 {_p10_gene_value(cyp1a2)}（{display.get('caffeine_status') or '已识别'}）",
    ) + "。"


def _p10_is_attention_indicator(indicator: dict[str, Any]) -> bool:
    text = f"{indicator.get('status') or ''} {indicator.get('result_display') or ''} {indicator.get('result') or ''}"
    return any(marker in text for marker in ("↑", "↓", "异常", "偏高", "偏低", "低于", "高于"))


def _apply_p11_dynamic_styles(soup: BeautifulSoup, report_data: dict[str, Any]) -> None:
    p11 = report_data.get("p11", {}) if isinstance(report_data.get("p11"), dict) else {}
    _apply_p11_pill_styles(soup)
    _apply_p11_food_grid(soup, p11)
    _apply_p11_indicator_cards(soup, p11)
    _apply_p11_focus_cards(soup, p11)
    _apply_p11_diet_chips(soup, p11)
    _apply_p11_ai_progress(soup, p11)


def _apply_p11_pill_styles(soup: BeautifulSoup) -> None:
    for node in soup.select(".pill"):
        text = node.get_text("", strip=True)
        _remove_classes(node, P11_PILL_CLASSES)
        if any(word in text for word in ("未见", "阴性", "正常", "维持", "已识别")):
            _add_class(node, "pill-green")
        elif "弱阳" in text or "待" in text or "复核" in text or "补充" in text:
            _add_class(node, "pill-orange")
        elif "阳性" in text:
            _add_class(node, "pill-red")
        else:
            _add_class(node, "pill-green")


def _apply_p11_food_grid(soup: BeautifulSoup, p11: dict[str, Any]) -> None:
    food_results = p11.get("food_results", [])
    if not isinstance(food_results, list) or not food_results:
        return
    grid = soup.select_one(".results-grid")
    if grid is None:
        return
    grid.clear()
    for fallback_index, item in enumerate(food_results, start=1):
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "")
        row = soup.new_tag("div")
        row["class"] = ["result-item"]
        css_class = _p11_food_css_class(status)
        if css_class:
            _add_class(row, css_class)

        number = soup.new_tag("span")
        number["class"] = ["result-num"]
        number.string = str(item.get("index") or fallback_index)
        row.append(number)

        name = soup.new_tag("span")
        name["class"] = ["result-name", "editable"]
        name["contenteditable"] = "true"
        name.string = str(item.get("name") or "")
        row.append(name)

        dot = soup.new_tag("i")
        dot["class"] = ["status-dot", _p11_status_dot_class(status)]
        dot.string = str(item.get("sign") or _p11_status_sign(status))
        row.append(dot)

        grid.append(row)
    heading = soup.select_one(".results-head h2 strong")
    if heading is not None:
        heading.string = str(len([item for item in food_results if isinstance(item, dict)]))


def _apply_p11_indicator_cards(soup: BeautifulSoup, p11: dict[str, Any]) -> None:
    indicators = p11.get("indicators", {})
    if not isinstance(indicators, dict):
        return
    for code in ("igg1", "igg2", "igg3", "igg4"):
        indicator = indicators.get(code, {})
        if not isinstance(indicator, dict):
            continue
        for result_node in soup.select(f'[data-field="p11.indicators.{code}.result"]'):
            card = _find_ancestor_with_class(result_node, "igg-card")
            if card is None:
                continue
            unit = card.select_one(".metric-unit")
            if unit is not None:
                unit.clear()
                unit.append(str(indicator.get("unit") or "—"))

            status_node = card.select_one(f'[data-field="p11.indicators.{code}.status"]')
            if status_node is not None:
                _remove_classes(status_node, P11_PILL_CLASSES)
                _add_class(status_node, _p11_indicator_pill_class(str(indicator.get("status") or "")))

            marker = card.select_one(".range-marker")
            if marker is not None:
                _set_style_prop(marker, "left", str(indicator.get("marker_percent") or "50%"))

            extents = card.select(".range-extents span")
            if len(extents) >= 2:
                extents[0].clear()
                extents[0].append(str(indicator.get("range_low") or "—"))
                extents[1].clear()
                extents[1].append(str(indicator.get("range_high") or "—"))


def _apply_p11_focus_cards(soup: BeautifulSoup, p11: dict[str, Any]) -> None:
    focus_items = p11.get("focus_items", {})
    if not isinstance(focus_items, dict):
        return
    cards = soup.select(".focus-card")
    for index, card in enumerate(cards[:2], start=1):
        focus = focus_items.get(f"focus_{index}", {})
        if not isinstance(focus, dict):
            continue
        headline = card.select_one(".focus-headline")
        if headline is not None:
            spans = headline.select("span")
            if len(spans) >= 3:
                spans[0].clear()
                spans[0].append(f"重点关注 {index}")
                spans[1].clear()
                spans[1].append(str(focus.get("name") or ""))
                spans[2].clear()
                spans[2].append(str(focus.get("status_label") or f"（{focus.get('status') or ''}）"))
                _remove_classes(spans[2], P11_FOCUS_STATUS_CLASSES)
                _add_class(spans[2], _p11_focus_status_class(str(focus.get("status") or "")))
        _apply_p11_card_items(card, focus, "impact", ".impact-item", soup)
        _apply_p11_card_items(card, focus, "advice", ".suggest-item", soup)
        _apply_p11_card_items(card, focus, "caution", ".caution-item", soup)


def _apply_p11_card_items(card: Any, focus: dict[str, Any], group_key: str, selector: str, soup: BeautifulSoup) -> None:
    group = focus.get(group_key, {})
    if not isinstance(group, dict):
        return
    nodes = card.select(selector)
    for index, node in enumerate(nodes[:4], start=1):
        item = group.get(f"item_{index}", {})
        if not isinstance(item, dict):
            continue
        symbol = node.select_one(".impact-symbol, .suggest-symbol, .caution-symbol")
        title = node.select_one("h4")
        body = node.select_one("p")
        for target, value in (
            (symbol, item.get("symbol")),
            (title, item.get("title")),
            (body, item.get("body")),
        ):
            if target is not None and value is not None:
                target.clear()
                target.append(str(value))


def _apply_p11_diet_chips(soup: BeautifulSoup, p11: dict[str, Any]) -> None:
    diet = p11.get("diet", {})
    if not isinstance(diet, dict):
        return
    _replace_p11_chip_row(
        soup,
        ".food-chip.red",
        diet.get("avoid_foods", []),
        fallback_name="未见需规避",
        color="red",
    )
    _replace_p11_chip_row(
        soup,
        ".food-chip.green",
        diet.get("recommended_foods", []),
        fallback_name="结合饮食记录",
        color="green",
    )


def _replace_p11_chip_row(soup: BeautifulSoup, selector: str, foods: Any, *, fallback_name: str, color: str) -> None:
    existing = soup.select(selector)
    if not existing:
        return
    parent = existing[0].parent
    for node in existing:
        node.decompose()
    items = foods if isinstance(foods, list) else []
    normalized = [item for item in items if isinstance(item, dict) and str(item.get("name") or "").strip()]
    if not normalized:
        normalized = [{"name": fallback_name}]
    for item in normalized[:6]:
        name = str(item.get("name") or fallback_name).strip()
        chip = soup.new_tag("div")
        chip["class"] = ["food-chip", color]
        icon = soup.new_tag("div")
        icon["class"] = ["chip-icon"]
        icon.string = _p11_chip_icon(name)
        chip.append(icon)
        name_node = soup.new_tag("div")
        name_node["class"] = ["name", "editable"]
        name_node["contenteditable"] = "true"
        name_node.string = name
        chip.append(name_node)
        parent.append(chip)


def _apply_p11_ai_progress(soup: BeautifulSoup, p11: dict[str, Any]) -> None:
    panel = soup.select_one(".ai-progress-panel")
    if panel is None:
        return
    bar = panel.select_one(".progress-bar > span")
    if bar is not None:
        _set_style_prop(bar, "width", str(p11.get("ai_progress_percent") or "100%"))
    percent = panel.select_one("strong")
    if percent is not None:
        percent.clear()
        percent.append(str(p11.get("ai_progress_display") or p11.get("ai_progress_percent") or "已生成"))


def _p11_food_css_class(status: str) -> str:
    if status == "阳性":
        return "alert"
    if status == "弱阳性":
        return "warn"
    return ""


def _p11_status_dot_class(status: str) -> str:
    if status == "阳性":
        return "status-plus"
    if status == "弱阳性":
        return "status-weak"
    return "status-minus"


def _p11_status_sign(status: str) -> str:
    if status == "阳性":
        return "+"
    if status == "弱阳性":
        return "±"
    if status == "阴性":
        return "−"
    return "?"


def _p11_indicator_pill_class(status: str) -> str:
    if any(word in status for word in ("偏高", "阳性", "异常")):
        return "pill-red"
    if any(word in status for word in ("偏低", "待", "补充", "复核")):
        return "pill-orange"
    return "pill-green"


def _p11_focus_status_class(status: str) -> str:
    if status == "阳性":
        return "status-red"
    if "弱阳" in status or "待" in status or "复核" in status or "补充" in status:
        return "status-orange"
    return "status-green"


def _p11_chip_icon(name: str) -> str:
    text = str(name or "").strip()
    return text[:1] if text else "·"


def _set_style_prop(node: Any, name: str, value: str) -> None:
    if node is None:
        return
    declarations: list[str] = []
    for declaration in str(node.get("style") or "").split(";"):
        if ":" not in declaration:
            continue
        key, existing_value = declaration.split(":", 1)
        if key.strip() != name:
            declarations.append(f"{key.strip()}: {existing_value.strip()}")
    declarations.append(f"{name}: {value}")
    node["style"] = "; ".join(declarations)


def _resolve(data: dict[str, Any], dotted_key: str) -> Any:
    current: Any = data
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _apply_fit_classes(soup: BeautifulSoup, node: Any, field_key: str, value: str) -> None:
    length = len(value.strip())
    fit_class = _fit_class(length)
    _add_class(node, fit_class)
    node["data-fit-length"] = str(length)

    page = _find_ancestor_with_class(node, "report-page")
    card = _find_first_ancestor_with_any_class(node, ("result-card", "summary-card", "result-panel"))

    if length >= 70:
        _add_class(page, "has-dense-content")
        _add_class(card, "has-long-text")
    if length >= 130:
        _add_class(page, "has-very-dense-content")
        _add_class(card, "has-very-long-text")

    if field_key == "p02.allergen.overall_result" and length >= 26:
        _add_class(node, "fit-allergen-result")
        _add_class(card, "has-long-result")
        _add_class(page, "has-long-allergen-result")

    if field_key == "p02.calprotectin.interpretation" and length <= 45:
        _add_class(card, "is-short-interpretation")
        _add_class(page, "has-short-calprotectin")


def _apply_result_color_class(node: Any, field_key: str, value: str) -> None:
    if not _is_detection_result_field(field_key):
        return
    _remove_classes(node, RESULT_COLOR_CLASSES)
    color_class = _result_color_class(value)
    if not color_class:
        node.attrs.pop("data-result-color", None)
        return
    _add_class(node, color_class)
    node["data-result-color"] = color_class.replace("-text", "")


def _is_detection_result_field(field_key: str) -> bool:
    return field_key.endswith(".result_display") or field_key.endswith(".overall_result")


def _result_color_class(value: str) -> str:
    text = "".join(value.split())
    if not text:
        return ""
    if "阴性" in text and "阳性" not in text:
        return "green-text"
    if _is_orange_positive_result(text):
        return "orange-text"
    if "阳性" in text:
        return "red-text"
    return ""


def _is_orange_positive_result(text: str) -> bool:
    if "阳性" not in text or "↑" not in text:
        return False
    if text.startswith("阳性项目"):
        return False
    if "+" in text or "＋" in text:
        return False
    return "阳性（↑）" in text or "阳性(↑)" in text or "弱阳性（↑）" in text or "弱阳性(↑)" in text


def _apply_p01_dynamic_styles(soup: BeautifulSoup, report_data: dict[str, Any]) -> None:
    for index in range(1, 5):
        level_field_key = f"p01.risk_cards.primary_{index}.risk_level"
        score_field_key = f"p01.risk_cards.primary_{index}.score_display"
        for node in soup.select(f'[data-field="{level_field_key}"]'):
            state = _p01_risk_state_from_text(node.get_text(" ", strip=True))
            card = _find_ancestor_with_class(node, "primary-risk-card")
            score_row = _find_first_ancestor_with_any_class(node, ("risk-card-head",))
            score_box = None
            risk_meter = None
            if score_row is not None:
                sibling = getattr(score_row, "find_next_sibling", lambda *args, **kwargs: None)("div", class_="risk-score-row")
                score_box = sibling.select_one(".risk-score") if sibling is not None else None
                risk_meter = sibling.select_one(".risk-meter") if sibling is not None else None

            if card is not None:
                _remove_classes(card, ("risk-warn", "risk-stable"))
                _add_class(card, "risk-stable" if state == "stable" else "risk-warn")
            _remove_classes(node, ("risk-level-badge-warn", "risk-level-badge-stable"))
            _add_class(node, "risk-level-badge-stable" if state == "stable" else "risk-level-badge-warn")
            if score_box is not None:
                _remove_classes(score_box, ("risk-score-stable",))
                if state == "stable":
                    _add_class(score_box, "risk-score-stable")
            if risk_meter is not None:
                score_node = card.select_one(f'[data-field="{score_field_key}"]') if card is not None else None
                score_value = _parse_float(score_node.get_text(" ", strip=True) if score_node is not None else "")
                if score_value is not None:
                    _set_css_var(risk_meter, "--marker", f"{max(0.0, min(score_value, 100.0)):.0f}%")


def _apply_p05_dynamic_styles(soup: BeautifulSoup, report_data: dict[str, Any]) -> None:
    p05 = report_data.get("p05", {})
    if not isinstance(p05, dict):
        return
    score = _parse_float(p05.get("health_score"))
    state = _p05_score_state(score)
    if not state:
        return
    for panel in soup.select(".score-panel"):
        _remove_classes(panel, ("score-excellent", "score-good", "score-attention", "score-high-risk"))
        _add_class(panel, f"score-{state}")


def _apply_p17_dynamic_styles(soup: BeautifulSoup) -> None:
    for node in soup.select("[data-field]"):
        field_key = str(node.get("data-field") or "")
        if not field_key.startswith("p17."):
            continue
        value = node.get_text(" ", strip=True)
        if field_key.endswith(".trend_display"):
            _remove_classes(node, ("trend-up",))
            if "↑" in value:
                _add_class(node, "trend-up")
            continue
        if not _p17_is_status_field(field_key):
            continue
        _remove_classes(node, P17_STATUS_CLASSES)
        status_class = _p17_status_class(field_key, value)
        if status_class:
            _add_class(node, status_class)


def _p17_is_status_field(field_key: str) -> bool:
    return (
        field_key.endswith(".result_display")
        or field_key.endswith("_status")
        or field_key.endswith("_risk_level")
        or field_key in {"p17.hpv_overall_status", "p17.microecology_overall_status"}
    )


def _p17_status_class(field_key: str, value: str) -> str:
    text = "".join(str(value or "").split())
    if not text:
        return ""
    if any(word in text for word in ("高风险", "需重视")):
        return "status-red"
    if any(word in text for word in ("需关注", "待复核", "未识别")):
        return "status-orange"
    if any(word in text for word in ("低风险", "良好", "稳定")):
        return "status-positive"
    if "阳性" in text or "弱阳" in text or "↑" in text:
        if "hpv_" in field_key or field_key == "p17.hpv_overall_status":
            return "status-red"
        if any(term in field_key for term in P17_GOOD_KEYS):
            return "status-positive"
        if any(term in field_key for term in P17_CONDITIONAL_KEYS):
            return "status-orange"
        if any(term in field_key for term in P17_PATHOGEN_KEYS):
            return "status-red"
        return "status-orange"
    if "阴性" in text or "全阴" in text or "未见" in text:
        if field_key == "p17.hpv_overall_status":
            return "status-purple"
        return "status-negative"
    return ""


def _apply_p10_dynamic_styles(soup: BeautifulSoup) -> None:
    for node in soup.select("[data-field]"):
        field_key = str(node.get("data-field") or "")
        if not field_key.startswith("p10.display."):
            continue
        if not _find_first_ancestor_with_any_class(node, ("judge-row", "result-line", "risk-result")):
            continue
        value = node.get_text(" ", strip=True)
        _remove_classes(node, P10_STATUS_CLASSES)
        status_class = _p10_status_class(value)
        if status_class:
            _add_class(node, status_class)


def _p10_status_class(value: str) -> str:
    text = "".join(str(value or "").split())
    if not text:
        return ""
    if any(word in text for word in ("待识别", "需关注", "风险", "异常", "偏高", "偏低")):
        return "status-orange"
    if any(word in text for word in ("不耐受", "较慢", "较弱")):
        return "status-red"
    if any(word in text for word in ("中等", "一般")):
        return "status-blue"
    if any(word in text for word in ("正常", "耐受正常", "风险低")):
        return "status-green"
    return ""


def _apply_p04_dynamic_styles(soup: BeautifulSoup) -> None:
    for node in soup.select("[data-field]"):
        field_key = str(node.get("data-field") or "")
        if not field_key.startswith("p04."):
            continue
        if not (field_key.endswith(".status") or field_key.endswith("_status") or field_key.endswith(".result_display")):
            continue
        _remove_classes(node, P04_STATUS_CLASSES)
        status_class = _p04_status_class(node.get_text(" ", strip=True))
        if not status_class:
            continue
        _add_class(node, status_class)
        if status_class == "status-normal":
            _add_class(node, "green-title")
        elif status_class == "status-high":
            _add_class(node, "red-text")
        elif status_class == "status-low":
            _add_class(node, "orange-text")


def _apply_p06_dynamic_styles(soup: BeautifulSoup) -> None:
    _remove_duplicate_p06_ai_paragraphs(soup)
    for node in soup.select("[data-field]"):
        field_key = str(node.get("data-field") or "")
        if not field_key.startswith("p06."):
            continue
        if not (field_key.endswith(".status") or field_key.endswith(".result") or field_key.endswith(".result_display")):
            continue
        _remove_classes(node, P06_STATUS_CLASSES)
        status_class = _p06_status_class(node.get_text(" ", strip=True))
        if not status_class:
            continue
        _add_class(node, status_class)
        if status_class == "status-normal":
            _add_class(node, "green-title")
        elif status_class == "status-high":
            _add_class(node, "red-text")
        elif status_class == "status-low":
            _add_class(node, "orange-text")


def _p06_status_class(value: str) -> str:
    text = "".join(str(value or "").split())
    if not text:
        return ""
    if any(word in text for word in ("正常", "稳定", "未见明显异常")):
        return "status-normal"
    if any(word in text for word in ("升高", "偏高", "异常", "↑")):
        return "status-high"
    if any(word in text for word in ("偏低", "降低", "↓")):
        return "status-low"
    return ""


def _apply_p07_dynamic_styles(soup: BeautifulSoup) -> None:
    for node in soup.select("[data-field]"):
        field_key = str(node.get("data-field") or "")
        if not field_key.startswith("p07."):
            continue
        if not field_key.endswith((".status", ".status_display", ".result_display")):
            continue
        _remove_classes(node, P07_STATUS_CLASSES)
        status_class = _p07_status_class(node.get_text(" ", strip=True))
        if status_class == "status-normal":
            _add_class(node, "ok-text")
        elif status_class == "status-high":
            _add_class(node, "red-text")
        elif status_class == "status-low":
            _add_class(node, "orange-text")


def _p07_status_class(value: str) -> str:
    text = "".join(str(value or "").split())
    if not text:
        return ""
    if any(word in text for word in ("偏高", "升高", "异常", "高风险", "↑")):
        return "status-high"
    if any(word in text for word in ("偏低", "降低", "需关注", "待复核", "未识别", "需复核", "↓")):
        return "status-low"
    if "正常" in text or text in {"GG"}:
        return "status-normal"
    return ""


def _apply_p08_dynamic_styles(soup: BeautifulSoup) -> None:
    for node in soup.select("[data-field]"):
        field_key = str(node.get("data-field") or "")
        if not field_key.startswith("p08."):
            continue
        if not field_key.endswith((".status", ".result", ".result_display", ".key_status", ".result_status")):
            continue
        value = node.get_text(" ", strip=True)
        status_class = _p08_status_class(value)
        if not status_class:
            continue
        color_class = {"status-high": "red", "status-normal": "green", "status-low": "orange"}[status_class]
        _remove_classes(node, P08_STATUS_CLASSES)
        if "tag" in list(node.get("class", [])):
            _add_class(node, color_class)
        else:
            _add_class(node, f"{color_class}-text")
        _add_class(node, status_class)

        card = _find_first_ancestor_with_any_class(node, ("result-card",))
        if card is not None:
            _remove_classes(card, ("red", "green", "orange"))
            _add_class(card, color_class)


def _p08_status_class(value: str) -> str:
    text = "".join(str(value or "").split())
    if not text:
        return ""
    if any(word in text for word in ("明显升高", "偏高", "升高", "增高", "过高", "异常", "高风险", "需关注", "↑")):
        return "status-high"
    if any(word in text for word in ("偏低", "降低", "减少", "待复核", "需复核", "未识别", "待补充", "↓")):
        return "status-low"
    if any(word in text for word in ("正常", "稳定", "平稳", "参考范围", "风险较低", "未见明显异常")):
        return "status-normal"
    return ""


def _apply_p09_dynamic_styles(soup: BeautifulSoup, report_data: dict[str, Any]) -> None:
    for node in soup.select("[data-field]"):
        field_key = str(node.get("data-field") or "")
        if not field_key.startswith("p09."):
            continue
        if not field_key.endswith((".status", ".status_display", ".range_status_display")):
            continue
        status_class = _p08_status_class(node.get_text(" ", strip=True))
        _remove_classes(node, P09_STATUS_CLASSES)
        if not status_class:
            continue
        _add_class(node, status_class)
        existing = list(node.get("class", []))
        if "status-pill" in existing:
            if status_class == "status-normal":
                node["style"] = "--status-color: #58b84d;"
            elif status_class == "status-high":
                node["style"] = "--status-color: #d65a24;"
            else:
                node["style"] = "--status-color: #2e9df2;"
        elif "range-chip" not in existing:
            _add_class(node, "normal-pill" if status_class == "status-normal" else "warn-pill")

    _apply_p09_metric_pointers(soup, report_data)


def _apply_p09_metric_pointers(soup: BeautifulSoup, report_data: dict[str, Any]) -> None:
    p09 = report_data.get("p09", {})
    if not isinstance(p09, dict):
        return
    indicators = p09.get("indicators", {})
    if not isinstance(indicators, dict):
        return

    metric_codes = ("e2", "lh", "fsh", "progesterone", "testosterone", "shbg")
    for code in metric_codes:
        item = indicators.get(code)
        if not isinstance(item, dict):
            continue
        point = _p09_metric_pointer_percent(item)
        if point is None:
            continue
        for node in soup.select(f'[data-field="p09.indicators.{code}.result"]'):
            value_wrap = _find_first_ancestor_with_any_class(node, ("metric-value",))
            if value_wrap is None:
                continue
            track = value_wrap.select_one(".range-track")
            if track is not None:
                _set_css_var(track, "--point", f"{point:.1f}%")


def _p09_metric_pointer_percent(item: dict[str, Any]) -> float | None:
    value = _safe_float_for_render(item.get("raw_value"))
    status = str(item.get("status") or item.get("status_display") or "")
    reference_text = str(item.get("reference_range") or item.get("reference_display") or "")
    if value is None:
        return _p09_pointer_from_status(status)

    bounds = _parse_numeric_bounds(reference_text)
    if not bounds:
        return _p09_pointer_from_status(status)

    low = min((lower for lower, _ in bounds if lower is not None), default=None)
    high = max((upper for _, upper in bounds if upper is not None), default=None)
    if low is None and high is None:
        return _p09_pointer_from_status(status)

    if low is not None and value < low:
        if low <= 0:
            severity = 1.0
        else:
            severity = min((low - value) / low, 1.0)
        return 6.0 + severity * 15.0

    if high is not None and value > high:
        span = None
        if low is not None and high > low:
            span = high - low
        if span and span > 0:
            excess_ratio = (value - high) / span
        elif high > 0:
            excess_ratio = (value - high) / high
        else:
            excess_ratio = 1.0
        if excess_ratio >= 0.5:
            return min(88.0 + min(excess_ratio, 1.5) / 1.5 * 10.0, 98.0)
        return 74.0 + max(excess_ratio, 0.0) / 0.5 * 12.0

    if low is not None and high is not None and high > low:
        normal_ratio = (value - low) / (high - low)
        return 22.0 + min(max(normal_ratio, 0.0), 1.0) * 51.0
    if high is not None and high > 0:
        return 22.0 + min(max(value / high, 0.0), 1.0) * 51.0
    return _p09_pointer_from_status(status)


def _p09_pointer_from_status(status: str) -> float:
    text = "".join(str(status or "").split())
    if any(word in text for word in ("偏低", "降低", "↓", "不足")):
        return 14.0
    if any(word in text for word in ("升高", "明显升高", "过高", "很高", "异常")):
        return 92.0
    if any(word in text for word in ("偏高",)):
        return 79.0
    return 48.0


def _apply_p12_dynamic_styles(soup: BeautifulSoup, report_data: dict[str, Any]) -> None:
    for node in soup.select("[data-field]"):
        field_key = str(node.get("data-field") or "")
        if not field_key.startswith("p12."):
            continue
        if not field_key.endswith((".status", ".status_display", ".warning_note")):
            continue
        status_class = _p12_status_class(node.get_text(" ", strip=True))
        _remove_classes(node, P12_STATUS_CLASSES)
        if not status_class:
            continue
        _add_class(node, status_class)
        existing = list(node.get("class", []))
        if "status-pill" in existing:
            if status_class == "status-normal":
                _add_class(node, "green")
            elif status_class == "status-high":
                _add_class(node, "red")
            else:
                _add_class(node, "orange")
        elif node.name in {"b", "td", "span", "p"}:
            if status_class == "status-normal":
                _add_class(node, "green-text")
            elif status_class == "status-high":
                _add_class(node, "red-text")
            else:
                _add_class(node, "orange-text")

        card = _find_first_ancestor_with_any_class(node, ("result-card", "judgement-card", "metric-item"))
        if card is not None:
            _remove_classes(card, ("red", "green", "orange"))
            if status_class == "status-normal":
                _add_class(card, "green")
            elif status_class == "status-high":
                _add_class(card, "red")
            else:
                _add_class(card, "orange")
    _apply_p12_nad_chart_marker(soup, report_data)


def _apply_p12_nad_chart_marker(soup: BeautifulSoup, report_data: dict[str, Any]) -> None:
    p12 = report_data.get("p12", {}) if isinstance(report_data.get("p12"), dict) else {}
    indicators = p12.get("indicators", {}) if isinstance(p12.get("indicators"), dict) else {}
    nad = indicators.get("nad", {}) if isinstance(indicators.get("nad"), dict) else {}
    value = _safe_float_for_render(nad.get("raw_value") or nad.get("result") or nad.get("result_display"))
    if value is None:
        return
    marker_text = str(p12.get("nad_chart_marker") or nad.get("result_display") or "").strip() or "未识别"
    patient = report_data.get("patient", {}) if isinstance(report_data.get("patient"), dict) else {}
    age = _safe_float_for_render(patient.get("age"))
    if age is None:
        x = 300.0
    else:
        x = 58.0 + (min(max(age, 20.0), 80.0) - 20.0) / 60.0 * 550.0
    y = 300.0 - min(max(value, 0.0), 120.0) / 120.0 * 260.0
    y = min(max(y, 44.0), 292.0)
    bubble_y = max(y - 44.0, 40.0)
    label_y = bubble_y + 22.0
    pointer_y = bubble_y + 35.0
    bubble_padding = 18.0
    bubble_width = max(74.0, min(160.0, len(marker_text) * 9.2 + bubble_padding * 2.0))
    bubble_left = min(max(x + 12.0, 70.0), 608.0 - bubble_width - 10.0)
    bubble_tip = bubble_left
    bubble_text_x = bubble_left + bubble_width / 2.0
    bubble_right = bubble_left + bubble_width
    bubble_inner_left = bubble_left + 14.0
    for node in soup.select(".nad-marker-line"):
        node["y1"] = f"{y:.1f}"
        node["y2"] = f"{y:.1f}"
    for node in soup.select(".nad-marker-stem"):
        node["x1"] = f"{x:.1f}"
        node["x2"] = f"{x:.1f}"
        node["y1"] = f"{y:.1f}"
    for node in soup.select(".nad-marker-dot"):
        node["cx"] = f"{x:.1f}"
        node["cy"] = f"{y:.1f}"
    for node in soup.select(".nad-marker-bubble"):
        node["d"] = (
            f"M{bubble_tip:.1f} {pointer_y:.1f} L{bubble_inner_left:.1f} {bubble_y:.1f} L{bubble_right:.1f} {bubble_y:.1f} "
            f"Q{bubble_right + 8:.1f} {bubble_y:.1f} {bubble_right + 8:.1f} {bubble_y + 8:.1f} "
            f"L{bubble_right + 8:.1f} {bubble_y + 27:.1f} Q{bubble_right + 8:.1f} {bubble_y + 35:.1f} {bubble_right:.1f} {bubble_y + 35:.1f} "
            f"L{bubble_inner_left - 8:.1f} {bubble_y + 35:.1f} Z"
        )
    for node in soup.select(".nad-marker-label"):
        node.string = marker_text
        node["x"] = f"{bubble_text_x:.1f}"
        node["y"] = f"{label_y:.1f}"
    for node in soup.select(".nad-age-label"):
        node["x"] = f"{x - 5.0:.1f}"


def _apply_p15_dynamic_styles(soup: BeautifulSoup, report_data: dict[str, Any]) -> None:
    p15 = report_data.get("p15", {}) if isinstance(report_data.get("p15"), dict) else {}
    exposure_index = p15.get("exposure_index", {}) if isinstance(p15.get("exposure_index"), dict) else {}
    level = str(exposure_index.get("level") or "")

    for node in soup.select("[data-field]"):
        field_key = str(node.get("data-field") or "")
        if not field_key.startswith("p15.results.") or not field_key.endswith(".status"):
            continue
        status_text = node.get_text(" ", strip=True)
        status_class = _p08_status_class(status_text)
        if status_class == "status-normal":
            _add_class(node, "green-text")
        elif status_class == "status-high":
            _add_class(node, "red-text")
        elif status_class == "status-low":
            _add_class(node, "orange-text")

        status_wrap = _find_first_ancestor_with_any_class(node, ("status-wrap",))
        if status_wrap is None:
            continue
        bar = status_wrap.select_one(".bar")
        if bar is None:
            continue
        if status_class == "status-high":
            _add_class(bar, "redbar")
        else:
            _remove_classes(bar, ("redbar",))

    needle = soup.select_one(".gauge-needle")
    icon = soup.select_one(".gauge-icon")
    if needle is not None:
        rotation = "-34"
        if "中度" in level:
            rotation = "6"
        elif "高度" in level or "高风险" in level:
            rotation = "34"
        elif "平稳" in level or "低风险" in level:
            rotation = "-62"
        needle["transform"] = f"rotate({rotation} 380 300)"
    if icon is not None:
        icon.string = "!" if "预警" in level else "✓"


def _p12_status_class(value: str) -> str:
    text = "".join(str(value or "").split())
    if not text:
        return ""
    if any(word in text for word in ("严重不足", "中度耗竭", "偏低", "偏高", "异常", "需重点关注", "不足")):
        return "status-high"
    if any(word in text for word in ("轻度失衡", "建议干预", "待复核", "待补录", "未识别")):
        return "status-low"
    if any(word in text for word in ("正常", "良好", "平衡", "理想", "水平良好", "整体平稳")):
        return "status-normal"
    return ""


def _parse_numeric_bounds(reference_text: str) -> list[tuple[float | None, float | None]]:
    text = str(reference_text or "")
    if not text:
        return []
    compact = text.replace("参考范围：", " ").replace("参考值：", " ")
    compact = compact.replace("--", "-").replace("—", "-").replace("–", "-").replace("~", "-")
    compact = compact.replace("＜", "<").replace("＞", ">")

    bounds: list[tuple[float | None, float | None]] = []
    for lower, upper in re.findall(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", compact):
        bounds.append((float(lower), float(upper)))
    for upper in re.findall(r"<\s*(\d+(?:\.\d+)?)", compact):
        bounds.append((None, float(upper)))
    for lower in re.findall(r">\s*(\d+(?:\.\d+)?)", compact):
        bounds.append((float(lower), None))
    return bounds


def _safe_float_for_render(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip()
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _remove_duplicate_p06_ai_paragraphs(soup: BeautifulSoup) -> None:
    for insight in soup.select(".page-04 .ai-insight"):
        seen: set[str] = set()
        for paragraph in list(insight.select("p")):
            text = "".join(paragraph.get_text(" ", strip=True).split())
            if not text:
                continue
            if text in seen:
                paragraph.decompose()
                continue
            seen.add(text)


def _p04_status_class(value: str) -> str:
    text = "".join(str(value or "").split())
    if not text:
        return ""
    if any(word in text for word in ("未见", "正常", "良好", "平稳")):
        return "status-normal"
    if any(word in text for word in ("偏高", "升高", "过高", "↑")):
        return "status-high"
    if any(word in text for word in ("不足", "缺乏", "偏低", "降低", "↓")):
        return "status-low"
    if any(word in text for word in ("未识别", "待补充", "需复核", "待评估")):
        return "status-low"
    return ""


def _p05_score_state(score: float | None) -> str:
    if score is None:
        return ""
    if score >= 90:
        return "excellent"
    if score >= 80:
        return "good"
    if score >= 70:
        return "attention"
    return "high-risk"


def _p01_risk_state_from_text(value: str) -> str:
    text = "".join(str(value).split())
    if any(word in text for word in ("低风险", "稳定", "正常")):
        return "stable"
    return "warn"


def _apply_p03_dynamic_styles(soup: BeautifulSoup, report_data: dict[str, Any]) -> None:
    p03 = report_data.get("p03", {})
    if not isinstance(p03, dict):
        return

    for code in P03_INDICATOR_CODES:
        item = p03.get(code)
        if not isinstance(item, dict):
            continue
        state = _p03_state_from_item(item)
        if not state:
            continue
        for suffix in ("result_display", "status", "interpretation"):
            _apply_p03_field_state(soup, f"p03.{code}.{suffix}", state)

    _apply_p03_range_pointer(soup, p03)
    _apply_p03_homa_gauge(soup, p03)
    _apply_p03_non_hdl_chart(soup, p03)
    _apply_p03_risk_card(soup, "p03.cardiovascular_risk", str(p03.get("cardiovascular_risk") or ""))
    _apply_p03_risk_card(soup, "p03.metabolic_risk", str(p03.get("metabolic_risk") or ""))


def _apply_p03_field_state(soup: BeautifulSoup, field_key: str, state: str) -> None:
    for node in soup.select(f'[data-field="{field_key}"]'):
        _apply_p03_state_class(node, state)
        if field_key.endswith((".result_display", ".status")):
            _apply_p03_text_color_class(node, state)
        _apply_p03_state_to_related_blocks(node, state)


def _apply_p03_state_to_related_blocks(node: Any, state: str) -> None:
    current = getattr(node, "parent", None)
    while current is not None:
        classes = current.get("class", []) if hasattr(current, "get") else []
        if current.name == "tr" or any(class_name in classes for class_name in P03_STATE_TARGET_CLASSES):
            _remove_classes(current, ("red", "green") + P03_STATE_CLASSES)
            _apply_p03_state_class(current, state)
        current = getattr(current, "parent", None)


def _apply_p03_range_pointer(soup: BeautifulSoup, p03: dict[str, Any]) -> None:
    item = p03.get("tg_hdl_ratio", {})
    if not isinstance(item, dict):
        return
    state = _p03_state_from_item(item)
    value = _p03_item_value(item)
    for node in soup.select('[data-field="p03.tg_hdl_ratio.result_display"]'):
        marker = getattr(node, "parent", None)
        if marker is None or marker.name != "i":
            continue
        _set_css_var(marker, "--pos", f"{_p03_range_position(value):.1f}%")
        _apply_p03_state_class(marker, state)
        _apply_p03_state_to_related_blocks(marker, state)


def _apply_p03_homa_gauge(soup: BeautifulSoup, p03: dict[str, Any]) -> None:
    item = p03.get("homa_ir", {})
    if not isinstance(item, dict):
        return
    state = _p03_state_from_item(item)
    value = _p03_item_value(item)
    for node in soup.select('[data-field="p03.homa_ir.result_display"]'):
        gauge = _find_ancestor_with_class(node, "semi-gauge")
        if gauge is None:
            continue
        _set_css_var(gauge, "--needle-rotation", f"{_p03_gauge_rotation(value):.1f}deg")
        _apply_p03_state_class(gauge, state)
        _apply_p03_state_class(node, state)
        _apply_p03_text_color_class(node, state)
        _apply_p03_state_to_related_blocks(gauge, state)


def _apply_p03_non_hdl_chart(soup: BeautifulSoup, p03: dict[str, Any]) -> None:
    item = p03.get("non_hdl_c", {})
    if not isinstance(item, dict):
        return
    state = _p03_state_from_item(item)
    if state == "normal":
        key_items = [p03.get("tg_hdl_ratio", {}), p03.get("homa_ir", {})]
        if any(_p03_state_from_item(item) != "normal" for item in key_items if isinstance(item, dict)):
            state = "warning"
    for node in soup.select('[data-field="p03.non_hdl_c.result_display"]'):
        _apply_p03_state_class(node, state)
        value_bar = getattr(node, "parent", None)
        if value_bar is not None and value_bar.name == "span":
            _apply_p03_state_class(value_bar, state)
        _apply_p03_text_color_class(node, state)
        _apply_p03_state_to_related_blocks(node, state)


def _apply_p03_risk_card(soup: BeautifulSoup, field_key: str, value: str) -> None:
    state = _p03_state_from_text(value)
    if not state:
        return
    for node in soup.select(f'[data-field="{field_key}"]'):
        _apply_p03_state_class(node, state)
        _apply_p03_text_color_class(node, state)
        card = _find_ancestor_with_class(node, "risk-card")
        _apply_p03_state_class(card, state)
        if card is not None:
            stars = card.select_one(".risk-stars")
            _apply_p03_state_class(stars, state)


def _p03_state_from_item(item: dict[str, Any]) -> str:
    risk_level = str(item.get("risk_level") or "").lower()
    if risk_level == "attention":
        return "abnormal"
    if risk_level == "warning":
        return "warning"
    if risk_level == "normal":
        return "normal"
    return _p03_state_from_text(f"{item.get('status') or ''} {item.get('result_display') or ''}")


def _p03_state_from_text(value: str) -> str:
    text = "".join(str(value).split())
    if not text:
        return ""
    if any(word in text for word in ("高风险", "异常", "升高", "偏高", "偏低", "超标")):
        return "abnormal"
    if any(word in text for word in ("临界", "需关注", "观察")):
        return "warning"
    if any(word in text for word in ("正常", "整体平稳", "理想")):
        return "normal"
    return ""


def _apply_p03_state_class(node: Any, state: str) -> None:
    if node is None or state not in {"normal", "warning", "abnormal"}:
        return
    _remove_classes(node, P03_STATE_CLASSES)
    _add_class(node, f"result-{state}")


def _apply_p03_text_color_class(node: Any, state: str) -> None:
    color_class = {
        "normal": "green-text",
        "warning": "orange-text",
        "abnormal": "red-text",
    }.get(state)
    if not color_class:
        return
    _remove_classes(node, RESULT_COLOR_CLASSES)
    _add_class(node, color_class)
    node["data-result-color"] = color_class.replace("-text", "")


def _p03_item_value(item: dict[str, Any]) -> float | None:
    value = item.get("raw_value")
    if value in (None, ""):
        value = item.get("result_display")
    return _parse_float(value)


def _parse_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    number = ""
    for char in str(value).replace(",", ""):
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


def _p03_range_position(value: float | None) -> float:
    if value is None:
        return 50.0
    if value < 2:
        return max(8.0, min(31.0, 8.0 + (value / 2.0) * 23.0))
    if value <= 3:
        return max(39.0, min(63.0, 39.0 + (value - 2.0) * 24.0))
    return max(72.0, min(93.0, 72.0 + min((value - 3.0) / 2.0, 1.0) * 21.0))


def _p03_gauge_rotation(value: float | None) -> float:
    if value is None:
        return 0.0
    if value < 1:
        return max(-66.0, min(-26.0, -66.0 + value * 40.0))
    if value < 2:
        return max(-24.0, min(12.0, -24.0 + (value - 1.0) * 36.0))
    if value <= 3:
        return max(16.0, min(52.0, 16.0 + (value - 2.0) * 36.0))
    return max(56.0, min(88.0, 56.0 + min((value - 3.0) / 2.0, 1.0) * 32.0))


def _set_css_var(node: Any, name: str, value: str) -> None:
    if node is None:
        return
    declarations: list[str] = []
    for declaration in str(node.get("style") or "").split(";"):
        if ":" not in declaration:
            continue
        key, existing_value = declaration.split(":", 1)
        if key.strip() != name:
            declarations.append(f"{key.strip()}: {existing_value.strip()}")
    declarations.append(f"{name}: {value}")
    node["style"] = "; ".join(declarations)


def _fit_class(length: int) -> str:
    if length <= 45:
        return "fit-short"
    if length <= 90:
        return "fit-medium"
    if length <= 150:
        return "fit-long"
    if length <= 240:
        return "fit-very-long"
    return "fit-ultra-long"


def _add_class(node: Any, class_name: str) -> None:
    if node is None:
        return
    classes = list(node.get("class", []))
    if class_name not in classes:
        classes.append(class_name)
        node["class"] = classes


def _remove_classes(node: Any, class_names: tuple[str, ...]) -> None:
    if node is None:
        return
    classes = [class_name for class_name in list(node.get("class", [])) if class_name not in class_names]
    if classes:
        node["class"] = classes
    else:
        node.attrs.pop("class", None)


def _find_ancestor_with_class(node: Any, class_name: str) -> Any:
    current = getattr(node, "parent", None)
    while current is not None:
        classes = current.get("class", []) if hasattr(current, "get") else []
        if class_name in classes:
            return current
        current = getattr(current, "parent", None)
    return None


def _find_first_ancestor_with_any_class(node: Any, class_names: tuple[str, ...]) -> Any:
    current = getattr(node, "parent", None)
    while current is not None:
        classes = current.get("class", []) if hasattr(current, "get") else []
        if any(class_name in classes for class_name in class_names):
            return current
        current = getattr(current, "parent", None)
    return None
