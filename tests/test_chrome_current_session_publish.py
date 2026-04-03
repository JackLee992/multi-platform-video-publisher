from pathlib import Path
import subprocess

from mvpublisher.execution_modes import ExecutionMode
from mvpublisher.models.draft import PlatformName, PublishDraft
from mvpublisher.publishers.chrome_current_session import (
    run_current_session_publish_script,
)


def _build_draft(tmp_path: Path, execution_mode: ExecutionMode) -> PublishDraft:
    video = tmp_path / "video.mov"
    video.write_text("video", encoding="utf-8")
    cover = tmp_path / "cover.jpg"
    cover.write_text("cover", encoding="utf-8")
    return PublishDraft.new(source_video_path=video).model_copy(
        update={
            "selected_title": "测试标题",
            "selected_cover_path": cover,
            "summary": "测试摘要",
            "execution_mode": execution_mode,
        }
    )


def test_run_current_session_publish_script_builds_autopublish_command(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _build_draft(tmp_path, ExecutionMode.AUTOPUBLISH)
    captured: dict[str, object] = {}

    def fake_run(command, check):
        captured["command"] = command
        captured["check"] = check
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("mvpublisher.publishers.chrome_current_session.subprocess.run", fake_run)

    run_current_session_publish_script(
        draft=draft,
        platform_name=PlatformName.XIAOHONGSHU,
    )

    command = captured["command"]
    assert command[0].endswith("bash")
    assert command[1].endswith("scripts/chrome_current_session_publish.sh")
    assert Path(command[1]).exists()
    assert "--video" in command
    assert str(draft.source_video_path) in command
    assert "--title" in command
    assert draft.selected_title in command
    assert "--description" in command
    assert draft.summary in command
    assert "--platform" in command
    assert PlatformName.XIAOHONGSHU.value in command
    assert "--skip-publish" not in command
    assert captured["check"] is True


def test_run_current_session_publish_script_adds_skip_publish_for_autofill_only(
    tmp_path: Path, monkeypatch
) -> None:
    draft = _build_draft(tmp_path, ExecutionMode.AUTOFILL_ONLY)
    captured: dict[str, object] = {}

    def fake_run(command, check):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("mvpublisher.publishers.chrome_current_session.subprocess.run", fake_run)

    run_current_session_publish_script(
        draft=draft,
        platform_name=PlatformName.WECHAT_CHANNELS,
    )

    command = captured["command"]
    assert PlatformName.WECHAT_CHANNELS.value in command
    assert "--skip-publish" in command
