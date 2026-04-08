from pathlib import Path
import subprocess

from mvpublisher.execution_modes import ExecutionMode
from mvpublisher.models.draft import PlatformName, PublishDraft
from mvpublisher.publishers.chrome_current_session import (
    _find_current_session_publish_script,
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
    assert "--cover" in command
    assert str(draft.selected_cover_path) in command
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


def test_find_current_session_publish_script_falls_back_to_repo_root_when_installed(
    monkeypatch,
) -> None:
    installed_module = Path(
        "/tmp/venv/lib/python3.11/site-packages/mvpublisher/publishers/chrome_current_session.py"
    )
    repo_root = Path(__file__).resolve().parents[1]

    monkeypatch.setattr(
        "mvpublisher.publishers.chrome_current_session.__file__",
        str(installed_module),
    )
    monkeypatch.chdir(repo_root)

    script_path = _find_current_session_publish_script()

    assert script_path == repo_root / "scripts" / "chrome_current_session_publish.sh"
    assert script_path.exists()


def test_current_session_script_ensures_platform_tab_exists() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
    content = script_path.read_text(encoding="utf-8")

    assert "ensure_platform_tab()" in content
    assert "wait_for_platform_tab()" in content
    assert "ensure_platform_tab \"$platform_name\"" in content
    assert "wait_for_platform_tab \"$platform_name\"" in content
    assert "wait_for_upload_input()" in content
    assert "wait_for_fill_target()" in content


def test_current_session_script_focuses_platform_before_automation_steps() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
    content = script_path.read_text(encoding="utf-8")

    assert 'focus_platform_tab "$platform_name" >/dev/null' in content
    assert content.count('focus_platform_tab "$platform_name" >/dev/null') >= 2


def test_current_session_script_uses_inputevent_for_xiaohongshu_title_fill() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
    content = script_path.read_text(encoding="utf-8")

    assert "new InputEvent('input'" in content
    assert "new Event('blur'" in content


def test_current_session_script_handles_douyin_resume_branch() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
    content = script_path.read_text(encoding="utf-8")

    assert "handle_douyin_resume_prompt()" in content
    assert "继续编辑" in content
    assert "继续编辑？" in content
    assert "handle_douyin_resume_prompt" in content


def test_current_session_script_handles_wechat_dialogs_and_current_placeholder() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
    content = script_path.read_text(encoding="utf-8")

    assert "handle_wechat_channels_dialogs()" in content
    assert "将此次编辑保留?" in content
    assert "概括视频主要内容，字数建议6-16个字符" in content
    assert "你还不能发表视频" in content


def test_current_session_script_supports_cover_and_description_fill_paths() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
    content = script_path.read_text(encoding="utf-8")

    assert "--cover PATH" in content
    assert "fill_xiaohongshu_description" in content
    assert "apply_xiaohongshu_cover" in content
    assert "fill_wechat_channels_description" in content
    assert "apply_wechat_channels_cover" in content


def test_current_session_script_uses_custom_cover_upload_for_xiaohongshu() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
    content = script_path.read_text(encoding="utf-8")

    assert "image/png, image/jpeg, image/*" in content
    assert "missing xiaohongshu cover input" in content
    assert "custom_cover_uploaded" in content


def test_current_session_script_verifies_wechat_cover_after_upload() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
    content = script_path.read_text(encoding="utf-8")

    assert "verify_wechat_channels_cover" in content
    assert ".cover-preview-wrap .vertical-img-size.cover-img-vertical" in content
    assert "cover_verified" in content


def test_current_session_script_waits_for_wechat_publish_ready() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
    content = script_path.read_text(encoding="utf-8")

    assert "wait_for_wechat_channels_publish_ready()" in content
    assert "上传中" in content
    assert "处理中" in content
    assert "生成中" in content


def test_current_session_script_supports_douyin_cover_modal_flow() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
    content = script_path.read_text(encoding="utf-8")

    assert "apply_douyin_cover" in content
    assert "设置横封面" in content
    assert "semi-upload upload-BvM5FF" in content
    assert "douyin_cover_uploaded" in content


def test_current_session_script_verifies_douyin_cover_after_upload() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
    content = script_path.read_text(encoding="utf-8")

    assert "verify_douyin_cover" in content
    assert "横/竖双封面缺失" in content
    assert "douyin_cover_verified" in content


def test_current_session_script_dismisses_douyin_horizontal_cover_prompt() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
    content = script_path.read_text(encoding="utf-8")

    assert "设置横封面获更多流量" in content
    assert "暂不设置" in content


def test_current_session_script_retries_video_fetch_with_localhost_fallback() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
    content = script_path.read_text(encoding="utf-8")

    assert "fetchAssetBlob" in content
    assert "http://localhost:${PORT}/' + name" in content
    assert "attempt <= 3" in content


def test_current_session_script_starts_cors_enabled_asset_server() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
    asset_server_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_asset_server.py"
    )
    content = script_path.read_text(encoding="utf-8")
    asset_server_content = asset_server_path.read_text(encoding="utf-8")

    assert "chrome_current_session_asset_server.py" in content
    assert "python3 \"$ASSET_SERVER_SCRIPT\"" in content
    assert "Access-Control-Allow-Origin" in asset_server_content


def test_current_session_script_has_native_file_picker_fallback_for_video_upload() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
    content = script_path.read_text(encoding="utf-8")

    assert "upload_via_native_file_picker" in content
    assert "tell application \"System Events\"" in content
    assert "keystroke \"g\" using {command down, shift down}" in content


def test_current_session_script_focuses_tabs_by_window_reference() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
    content = script_path.read_text(encoding="utf-8")

    assert "set matchedWindow to missing value" in content
    assert "set active tab index of matchedWindow" in content


def test_current_session_script_targets_semantic_publish_button_for_xiaohongshu() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
    content = script_path.read_text(encoding="utf-8")
    publish_section = content.split("publish_xiaohongshu() {", 1)[1].split(
        "check_xiaohongshu_result() {", 1
    )[0]

    assert 'document.querySelectorAll(\'button\')' in publish_section
    assert "trim() === '发布'" in publish_section
    assert "button,div,span" not in publish_section


def test_current_session_script_waits_for_xiaohongshu_publish_button_ready() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
    content = script_path.read_text(encoding="utf-8")
    publish_section = content.split("publish_xiaohongshu() {", 1)[1].split(
        "check_xiaohongshu_result() {", 1
    )[0]

    assert "repeat 25 times" in publish_section
    assert "delay 1" in publish_section


def test_current_session_script_keeps_douyin_applescript_return_unescaped() -> None:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
    content = script_path.read_text(encoding="utf-8")
    publish_section = content.split("publish_douyin() {", 1)[1].split(
        "check_douyin_result() {", 1
    )[0]

    assert 'return "NOT_FOUND"' in publish_section
    assert '\\"NOT_FOUND\\"' not in publish_section
