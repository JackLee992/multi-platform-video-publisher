from dataclasses import dataclass
from pathlib import Path
import re

MAX_SUMMARY_LENGTH = 56
PENDING_REVIEW_SUMMARY = "视频内容待确认"
CAMERA_STEM_PATTERN = re.compile(
    r"^(img|vid|pxl|mvimg|dsc|mov|video|wx_camera)[_-]?\d+$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SuggestionBundle:
    title_suggestions: list[str]
    description_suggestions: list[str]
    cover_suggestions: list[str]
    keywords: list[str]
    summary: str


def build_suggestions(source_video_path: Path, transcript_payload: dict) -> SuggestionBundle:
    payload = transcript_payload if isinstance(transcript_payload, dict) else {}
    full_text = _normalize_text(
        str(payload.get("full_text", "") or payload.get("text", "")),
        max_length=MAX_SUMMARY_LENGTH * 2,
    )
    segments = payload.get("segments", payload.get("utterances", []))
    if not isinstance(segments, list):
        segments = []
    if not segments and payload.get("utterances") and not payload.get("segments"):
        segments = payload.get("utterances") if isinstance(payload.get("utterances"), list) else []

    lead = _pick_summary_from_segments(segments)
    summary = lead or _normalize_text(full_text, max_length=MAX_SUMMARY_LENGTH) or _video_stem(source_video_path)
    reliable_summary = _transcript_looks_reliable(payload=payload, summary=summary, full_text=full_text)
    if not reliable_summary:
        summary = _fallback_summary(source_video_path)

    keyword_source = f"{full_text} {summary}"
    keywords = [
        keyword
        for keyword in ("多平台", "视频发布", "自动化", "效率")
        if keyword in keyword_source
    ]
    if reliable_summary:
        title_suggestions = _build_title_suggestions(summary)
        description_suggestions = [
            f"{summary}。发布前建议人工确认标题、简介和封面。",
        ]
        cover_suggestions = _build_cover_suggestions(summary)
    else:
        title_suggestions = _build_review_needed_title_suggestions(summary)
        description_suggestions = [
            "自动识别结果暂不可靠，建议先人工确认标题、简介和封面。",
        ]
        cover_suggestions = [
            "待确认内容",
            "人工确认封面",
            "发布前复核",
        ]

    return SuggestionBundle(
        title_suggestions=title_suggestions,
        description_suggestions=description_suggestions,
        cover_suggestions=cover_suggestions,
        keywords=keywords,
        summary=summary,
    )


def _normalize_text(value: str, max_length: int = MAX_SUMMARY_LENGTH) -> str:
    normalized = " ".join(str(value).split())
    return normalized[:max_length]


def _video_stem(source_video_path: Path) -> str:
    try:
        return Path(source_video_path).stem
    except Exception:
        return "video"


def _transcript_looks_reliable(payload: dict, summary: str, full_text: str) -> bool:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    language_detected = str(metadata.get("language_detected", "")).strip().lower()
    normalized = _normalize_text(full_text or summary, max_length=MAX_SUMMARY_LENGTH * 2)
    if not normalized:
        return True

    if language_detected.startswith(("zh", "ja", "ko")):
        if re.search(r"[A-Za-z]", normalized) and not re.search(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", normalized):
            return False

    return True


def _pick_summary_from_segments(segments: list[dict]) -> str:
    candidates: list[tuple[float, int, str]] = []
    first_non_empty = ""

    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            continue
        text = _normalize_text(str(segment.get("text", "")), max_length=MAX_SUMMARY_LENGTH)
        if not text:
            continue
        if not first_non_empty:
            first_non_empty = text

        confidence = _segment_confidence(segment)
        if confidence is None:
            continue
        candidates.append((confidence * min(max(len(text), 1), 4), -index, text))

    if candidates:
        return max(candidates, key=lambda item: (item[0], item[1]))[2]
    return first_non_empty


def _segment_confidence(segment: dict) -> float | None:
    words = segment.get("words")
    if isinstance(words, list):
        confidences = [
            float(word.get("confidence"))
            for word in words
            if isinstance(word, dict) and isinstance(word.get("confidence"), (int, float))
        ]
        if confidences:
            return sum(confidences) / len(confidences)

    confidence = segment.get("confidence")
    if isinstance(confidence, (int, float)) and 0 <= confidence <= 1:
        return float(confidence)
    return None


def _fallback_summary(source_video_path: Path) -> str:
    meaningful_stem = _meaningful_video_stem(source_video_path)
    return meaningful_stem or PENDING_REVIEW_SUMMARY


def _meaningful_video_stem(source_video_path: Path) -> str:
    stem = _video_stem(source_video_path).strip()
    if not stem:
        return ""
    if CAMERA_STEM_PATTERN.match(stem):
        return ""
    return stem


def _build_title_suggestions(summary: str) -> list[str]:
    return _dedupe_non_empty(
        [
            summary,
            f"{summary}｜视频记录",
            f"{summary}｜内容片段",
        ]
    )


def _build_review_needed_title_suggestions(summary: str) -> list[str]:
    if summary == PENDING_REVIEW_SUMMARY:
        return [
            PENDING_REVIEW_SUMMARY,
            "标题待人工确认",
            "先确认内容再发布",
        ]
    return _dedupe_non_empty(
        [
            summary,
            f"{summary}｜待人工确认",
            "先确认内容再发布",
        ]
    )


def _build_cover_suggestions(summary: str) -> list[str]:
    return _dedupe_non_empty(
        [
            _truncate_copy(summary, 8),
            _truncate_copy(summary, 12),
            "视频记录",
        ]
    )


def _truncate_copy(value: str, max_length: int) -> str:
    return _normalize_text(value, max_length=max_length)


def _dedupe_non_empty(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = _normalize_text(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result
