from dataclasses import dataclass
from pathlib import Path

MAX_SUMMARY_LENGTH = 56


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

    lead = ""
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        text = _normalize_text(str(segment.get("text", "")), max_length=MAX_SUMMARY_LENGTH)
        if text:
            lead = text
            break
    summary = lead or _normalize_text(full_text, max_length=MAX_SUMMARY_LENGTH) or _video_stem(source_video_path)

    keyword_source = f"{full_text} {summary}"
    keywords = [
        keyword
        for keyword in ("多平台", "视频发布", "自动化", "效率")
        if keyword in keyword_source
    ]

    title_base = f"{summary}"

    return SuggestionBundle(
        title_suggestions=[
            f"{title_base}，一套流程发三端",
            f"{_video_stem(source_video_path)}：多平台自动发布怎么做",
            "一次准备，多平台稳定发布",
        ],
        description_suggestions=[
            f"{summary}。这条内容聚焦{('、'.join(keywords) or '视频分发')}，适合做统一发布草稿。",
        ],
        cover_suggestions=[
            "一条视频发三端",
            "多平台自动发布",
            "减少重复上传",
        ],
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
