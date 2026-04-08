import json
import subprocess
import sys

from mvpublisher.media.video_skill_adapter import VideoSkillAdapter
from mvpublisher.suggestions.generator import SuggestionBundle, build_suggestions


def test_build_suggestions_from_transcript_payload(tmp_path):
    payload = {
        "full_text": "今天聊如何做多平台视频分发，提高效率，减少重复操作。",
        "segments": [{"text": "今天聊如何做多平台视频分发"}],
    }

    bundle = build_suggestions(
        source_video_path=tmp_path / "demo.mp4",
        transcript_payload=payload,
    )

    assert isinstance(bundle, SuggestionBundle)
    assert bundle.title_suggestions
    assert bundle.description_suggestions
    assert bundle.cover_suggestions
    assert bundle.summary == "今天聊如何做多平台视频分发"
    assert "多平台" in bundle.keywords


def test_build_suggestions_uses_text_when_no_full_text(tmp_path):
    payload = {"text": "这是一条关于自动化工作流的视频。"}

    bundle = build_suggestions(
        source_video_path=tmp_path / "demo.mp4",
        transcript_payload=payload,
    )

    assert bundle.summary.startswith("这是一条关于自动化工作流的视频")
    assert "自动化" in bundle.keywords


def test_build_suggestions_fallback_to_video_stem_when_text_empty(tmp_path):
    bundle = build_suggestions(
        source_video_path=tmp_path / "fallback.mp4",
        transcript_payload={},
    )

    assert bundle.summary == "fallback"


def test_video_skill_adapter_runs_review_only_pipeline(tmp_path, monkeypatch):
    script = tmp_path / "process_video.py"
    output_root = tmp_path / "out"
    output_root.mkdir()
    expected = {"result": "ok"}
    summary_path = output_root / "20260403_demo" / "pipeline_summary.json"
    summary_path.parent.mkdir(parents=True)

    seen = {}

    def fake_run(command, capture_output, text, check):
        summary_path.write_text(json.dumps(expected, ensure_ascii=False), encoding="utf-8")
        seen["command"] = command

        class FakeCompleted:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return FakeCompleted()

    monkeypatch.setattr(subprocess, "run", fake_run)

    adapter = VideoSkillAdapter(process_video_script=script)
    result = adapter.run(source_video_path=tmp_path / "demo.mp4", output_root=output_root)

    assert result == expected
    assert seen["command"][0] == sys.executable
    assert seen["command"][1] == str(script)
    assert "--video-path" in seen["command"]
    assert "--output-root" in seen["command"]
    assert "--review-only" in seen["command"]
    assert "--overwrite" in seen["command"]
    assert "--language" in seen["command"]
    assert "zh" in seen["command"]
    assert "--whisperkit-profile" in seen["command"]
    assert "quality" in seen["command"]


def test_video_skill_adapter_selects_latest_summary_when_stale_roots_exist(tmp_path, monkeypatch):
    script = tmp_path / "process_video.py"
    output_root = tmp_path / "out"
    output_root.mkdir()

    stale_summary = output_root / "20220101_old" / "pipeline_summary.json"
    stale_summary.parent.mkdir(parents=True)
    stale_summary.write_text(json.dumps({"result": "old"}, ensure_ascii=False), encoding="utf-8")

    expected = {"result": "new"}
    new_summary_path = output_root / "20260403_demo" / "pipeline_summary.json"

    def fake_run(command, capture_output, text, check):
        new_summary_path.parent.mkdir(parents=True)
        new_summary_path.write_text(json.dumps(expected, ensure_ascii=False), encoding="utf-8")

        class FakeCompleted:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return FakeCompleted()

    monkeypatch.setattr(subprocess, "run", fake_run)

    adapter = VideoSkillAdapter(process_video_script=script)
    result = adapter.run(source_video_path=tmp_path / "demo.mp4", output_root=output_root)

    assert result == expected


def test_build_suggestions_handles_malformed_segments_payload(tmp_path):
    payload = {"full_text": "abc", "segments": None}

    bundle = build_suggestions(
        source_video_path=tmp_path / "demo.mp4",
        transcript_payload=payload,
    )

    assert bundle.summary == "abc"


def test_build_suggestions_normalizes_noisy_text(tmp_path):
    payload = {
        "full_text": "  这是\\n\\n一段带有\\n杂乱   空白\\n的  ASR 结果    \\n" * 20,
        "segments": [{"text": "第一行\\n第二行"}],
    }

    bundle = build_suggestions(
        source_video_path=tmp_path / "demo.mp4",
        transcript_payload=payload,
    )

    assert "\n" not in bundle.summary
    assert "\n" not in bundle.title_suggestions[0]
    assert "\n" not in bundle.description_suggestions[0]
    assert len(bundle.summary) <= 56


def test_build_suggestions_stays_content_neutral_for_general_video(tmp_path):
    payload = {
        "full_text": "今天和莉莉去海边看星星，顺便记录一路上的风景。",
        "segments": [{"text": "今天和莉莉去海边看星星"}],
    }

    bundle = build_suggestions(
        source_video_path=tmp_path / "demo.mp4",
        transcript_payload=payload,
    )

    combined = " ".join(
        [
            *bundle.title_suggestions,
            *bundle.description_suggestions,
            *bundle.cover_suggestions,
        ]
    )

    assert "多平台自动发布" not in combined
    assert "一套流程发三端" not in combined
    assert "视频分发" not in combined
    assert bundle.title_suggestions[0] == "今天和莉莉去海边看星星"


def test_build_suggestions_falls_back_when_transcript_metadata_disagrees(tmp_path):
    payload = {
        "text": "How to go down to the bottom of the mountain to see the sea",
        "utterances": [
            {
                "text": "How to go down to the bottom of the mountain to see the sea",
                "words": [
                    {"text": "How", "confidence": 0.12},
                    {"text": "sea", "confidence": 0.18},
                ],
            }
        ],
        "metadata": {"language_detected": "zh"},
    }

    bundle = build_suggestions(
        source_video_path=tmp_path / "IMG_0040.MOV",
        transcript_payload=payload,
    )

    assert bundle.summary == "视频内容待确认"
    assert bundle.title_suggestions[0] == "视频内容待确认"
    assert "How to go down" not in " ".join(bundle.title_suggestions)


def test_build_suggestions_prefers_more_confident_segment_for_summary(tmp_path):
    payload = {
        "text": "如何日到我按地和下土 谁知盘中餐",
        "utterances": [
            {
                "text": "如何日到我按地和下土",
                "words": [{"text": "如何日到我按地和下土", "confidence": 0.44}],
            },
            {
                "text": "谁知盘中餐",
                "words": [{"text": "谁知盘中餐", "confidence": 0.83}],
            },
        ],
    }

    bundle = build_suggestions(
        source_video_path=tmp_path / "demo.mp4",
        transcript_payload=payload,
    )

    assert bundle.summary == "谁知盘中餐"
