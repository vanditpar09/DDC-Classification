"""Transparent, bounded capture policy. These rules are experimental, not learned.

The policy separates recognition problems from lack of subject evidence. It
does not establish novelty, patentability, or deployment-grade confidence.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Policy:
    min_ocr_confidence: float = 55
    max_low_confidence_fraction: float = .30
    min_character_height: float = 18
    min_sharpness: float = 28
    min_model_score: float = .62
    min_margin: float = .18
    max_ocr_passes: int = 6


def normalized_text(text):
    # Combining marks are essential to Indian scripts; \w alone drops them.
    normalized = unicodedata.normalize("NFC", text).casefold()
    return " ".join("".join(c if c.isalnum() or unicodedata.category(c).startswith("M") else " " for c in normalized).split())


def combine_evidence(pages):
    """Only current, readable, non-duplicate evidence reaches the classifier.

    Keep the original script, remove duplicate lines across page types, and do
    not repeat a page when a repair/capture replaces it.
    """
    seen, texts = set(), []
    for page in sorted(pages, key=lambda p: {"cover": 0, "back_cover": 1, "contents": 2}[p["kind"]]):
        if not page["usable"] or page.get("duplicate"):
            continue
        for line in page["text"].splitlines():
            key = normalized_text(line)
            if key and key not in seen:
                seen.add(key)
                texts.append(line.strip())
    return "\n".join(texts)


def decide(pages, prediction, ocr_passes, policy=None):
    policy = policy or Policy()
    base = {"experimental": True, "thresholds": vars(policy)}

    def action(code, title, reason, **extra):
        return dict(base, action=code, title=title, reason=reason, **extra)

    if not pages:
        return action("capture_cover", "Start with the cover", "Capture a readable title and subtitle to establish the first evidence.", requested_page="cover")
    latest = max(pages, key=lambda p: p["sequence"])
    q = latest.get("quality") or {}
    if ocr_passes >= policy.max_ocr_passes:
        return action("human_review", "Stop and review", "The six-pass OCR budget is exhausted. More automatic retries could waste work or reinforce an incorrect reading.")
    if q.get("script_mismatch"):
        if latest["repairs"] >= 1:
            return action("recapture_region", "Capture with the matching language selected", "The script still does not match after the allowed repair. Select the matching OCR language and capture a clearer page, or enter a checked transcription.", requested_page=latest["kind"], region=q.get("region"), suggested_languages=q["suggested_languages"])
        return action("switch_language", "Choose the matching OCR language", "The detected script does not match the selected OCR pack. Reprocess this page with the appropriate language before requesting another page.", page_id=latest["id"], suggested_languages=q["suggested_languages"])
    if latest.get("duplicate"):
        existing = {p["kind"] for p in pages if p["usable"] and not p.get("duplicate")}
        missing = next((kind for kind in ("back_cover", "contents") if kind not in existing), None)
        if missing:
            return action("request_page", "Add different subject evidence", "This page repeats text already captured. It was not counted again. Capture a different page with descriptive content.", requested_page=missing)
        return action("human_review", "Review the available evidence", "All page types are present and the latest text repeats existing evidence.")
    if latest["source"] == "ocr" and not latest["usable"]:
        has_text = q.get("word_count", 0) >= 2
        too_small = 0 < q.get("median_character_height", 0) < policy.min_character_height
        fixable = q.get("sharpness", 0) >= policy.min_sharpness and has_text
        if latest["repairs"] == 0 and (too_small or fixable):
            return action("reprocess_region", "Try a local OCR repair", "Text was detected, but its recognition quality is insufficient. Try one bounded contrast/upscale pass before requesting another capture.", page_id=latest["id"], region=q.get("region"))
        return action("recapture_region", "Capture a clearer image", "The latest page is not reliable enough to classify. Improve focus, lighting and framing in the highlighted region; a different subject page would not fix this recognition problem.", page_id=latest["id"], requested_page=latest["kind"], region=q.get("region"))
    hierarchy = prediction.get("hierarchy") if prediction else None
    if prediction and prediction.get('catalog_match',{}).get('status') == 'matched':
        record = prediction['catalog_match']['record']
        return action('ready_for_review', 'Review the matched catalog code',
            'The title and author match '+record['title']+'. The displayed DDC code comes from a saved catalog record. Confirm the edition and assignment before accepting it.')
    if hierarchy:
        # Model coverage cannot be repaired by running OCR again. Preserve the
        # broader usable result and stop when a supported parent has no child.
        unsupported = next((p for p in hierarchy["path"] if not p["supported"]), None)
        if unsupported and not unsupported.get("score_abstention") and hierarchy["review_level"] >= unsupported["level"] - 1:
            return action("human_review", "Keep the broader suggestion for review", "The model lacks sufficient training support for this finer branch. More OCR cannot supply missing training examples; check the finer code against the book and catalog evidence.")
        if hierarchy["review_level"] == hierarchy["target_level"]:
            return action("ready_for_review", "A three-level suggestion is ready to review", "The class, division and section pass the experimental score checks. Confirm the full path against the book and catalog evidence; this is not automatic acceptance.")
    elif prediction and prediction["score"] >= policy.min_model_score and prediction["margin"] >= policy.min_margin:
        return action("ready_for_review", "A suggestion is ready to review", "Readable evidence supports a leading class under the prototype thresholds. Confirm it against the book and catalog evidence; this is not automatic acceptance.")
    existing = {p["kind"] for p in pages if p["usable"] and not p.get("duplicate")}
    for kind in ("back_cover", "contents"):
        if kind not in existing:
            reason = "The extracted text passed basic OCR checks, but subject evidence is insufficient or ambiguous. Check it against the photo, then add a descriptive page."
            if hierarchy and hierarchy["review_level"] > 0:
                reason = f"The suggestion is stable through level {hierarchy['review_level']}, but the finer classification remains uncertain. Add descriptive subject evidence instead of repeating OCR on the same text."
            return action("request_page", "Scan the " + ("back cover" if kind == "back_cover" else "contents page"), reason, requested_page=kind)
    return action("human_review", "Review this book manually", "All three page types have been considered, but the model still cannot separate the leading classes reliably.")
