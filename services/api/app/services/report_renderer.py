from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from app.core.config import settings
from app.services.report_review import find_active_report_id_for_case, register_rendered_report

RESULT_COLOR_CLASSES = ("green-text", "red-text", "orange-text")
P03_STATE_CLASSES = ("result-normal", "result-warning", "result-abnormal")
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
