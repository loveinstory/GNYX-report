from __future__ import annotations

from typing import Any, Callable


def merge_p11_ai_output(
    merged: dict[str, Any],
    ai_output: dict[str, Any],
    pick_text: Callable[[Any, list[str]], str],
    stringify_text: Callable[[Any], str],
    safe_report_text: Callable[[str], str],
) -> None:
    p11 = merged.setdefault("p11", {})
    indicator_interpretations = ai_output.get("indicator_interpretations", {}) if isinstance(ai_output.get("indicator_interpretations"), dict) else {}
    recommendations = ai_output.get("recommendations", {}) if isinstance(ai_output.get("recommendations"), dict) else {}

    overall_summary = pick_text(ai_output, ["overall_summary"])
    if overall_summary:
        p11["overall_summary"] = safe_report_text(overall_summary)

    focus_items = p11.get("focus_items")
    if isinstance(focus_items, dict):
        for key, candidates in {
            "focus_1": ["focus_1_summary", "food_focus_1"],
            "focus_2": ["focus_2_summary", "food_focus_2"],
        }.items():
            bucket = focus_items.get(key)
            if isinstance(bucket, dict):
                text = pick_text(indicator_interpretations, candidates)
                if text:
                    bucket["summary"] = safe_report_text(text)

    immune_summary = pick_text(indicator_interpretations, ["immune_summary", "food_intolerance_summary", "immune"])
    if immune_summary:
        p11["ai_insight"] = safe_report_text(immune_summary)

    diagnosis = pick_text(ai_output, ["ai_assisted_diagnosis", "diagnosis", "health_management_diagnosis"])
    if not diagnosis:
        diagnosis = pick_text(indicator_interpretations, ["ai_assisted_diagnosis", "diagnosis", "food_diagnosis"])
    if diagnosis:
        p11["ai_assisted_diagnosis"] = safe_report_text(diagnosis)

    priorities = recommendations.get("management_priorities")
    if isinstance(priorities, list):
        target = p11.setdefault("priorities", {})
        if isinstance(target, dict):
            for index, item in enumerate(priorities[:4], start=1):
                bucket = target.setdefault(f"priority_{index}", {})
                if not isinstance(bucket, dict):
                    continue
                if isinstance(item, dict):
                    title = pick_text(item, ["title", "name", "priority"])
                    body = pick_text(item, ["body", "description", "advice", "text"])
                else:
                    title = stringify_text(item)
                    body = ""
                if title:
                    bucket["title"] = safe_report_text(title)
                if body:
                    bucket["body"] = safe_report_text(body)

    followup = pick_text(recommendations, ["followup_advice", "followup", "review_plan", "health_management"])
    if followup:
        p11["followup_advice"] = safe_report_text(followup)

    diet = p11.setdefault("diet", {})
    if isinstance(diet, dict):
        avoid_note = pick_text(recommendations, ["avoid_note", "avoid_food_note", "avoid_foods"])
        recommended_note = pick_text(recommendations, ["recommended_note", "recommended_food_note", "recommended_foods"])
        avoid_attention = pick_text(recommendations, ["avoid_attention", "avoid_caution"])
        recommended_attention = pick_text(recommendations, ["recommended_attention", "diet_attention"])
        if avoid_note:
            diet["avoid_note"] = safe_report_text(avoid_note)
        if recommended_note:
            diet["recommended_note"] = safe_report_text(recommended_note)
        if avoid_attention:
            diet["avoid_attention"] = safe_report_text(avoid_attention)
        if recommended_attention:
            diet["recommended_attention"] = safe_report_text(recommended_attention)

    safety = ai_output.get("safety", {}) if isinstance(ai_output.get("safety"), dict) else {}
    disclaimer = pick_text(safety, ["disclaimer", "statement"])
    if disclaimer:
        p11["disclaimer"] = safe_report_text(disclaimer)

    review_note = pick_text(ai_output, ["review_note"])
    if review_note:
        p11["review_note"] = safe_report_text(review_note)


def sanitize_p11_ai_fields(sanitized: dict[str, Any]) -> None:
    p11 = sanitized.get("p11")
    if not isinstance(p11, dict):
        return

    for key in ["overall_summary", "ai_insight", "ai_assisted_diagnosis", "followup_advice", "disclaimer", "review_note"]:
        if key in p11:
            p11[key] = ""

    focus_items = p11.get("focus_items")
    if isinstance(focus_items, dict):
        for section in ["focus_1", "focus_2"]:
            bucket = focus_items.get(section)
            if isinstance(bucket, dict) and "summary" in bucket:
                bucket["summary"] = ""

    priorities = p11.get("priorities")
    if isinstance(priorities, dict):
        for item in priorities.values():
            if isinstance(item, dict):
                if "title" in item:
                    item["title"] = ""
                if "body" in item:
                    item["body"] = ""

    diet = p11.get("diet")
    if isinstance(diet, dict):
        for key in ["avoid_note", "recommended_note", "avoid_attention", "recommended_attention"]:
            if key in diet:
                diet[key] = ""
