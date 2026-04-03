from typer.testing import CliRunner

from mvpublisher.cli import app
import mvpublisher.cli as cli_module
from mvpublisher.storage.drafts import DraftRepository


def test_cli_shows_create_command() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "create-draft" in result.stdout
    assert "publish-draft" in result.stdout
    assert "serve-review" in result.stdout


def test_cli_create_draft_command_invokes(tmp_path, monkeypatch) -> None:
    video = tmp_path / "demo.mp4"
    script = tmp_path / "process_video.py"
    video.write_text("video", encoding="utf-8")
    script.write_text("# stub", encoding="utf-8")

    class FakeDraft:
        draft_id = "a" * 32

    monkeypatch.setattr(cli_module, "_find_video_skill_script", lambda: script)
    monkeypatch.setattr(
        cli_module,
        "create_draft_from_video",
        lambda source_video_path, repository, skill_runner: FakeDraft(),
    )
    monkeypatch.setenv("MVPUBLISHER_HOME", str(tmp_path / "runtime"))

    runner = CliRunner()
    result = runner.invoke(app, ["create-draft", str(video)])

    assert result.exit_code == 0
    assert "draft_id:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in result.stdout
    assert "draft_path:" in result.stdout


def test_cli_publish_draft_command_invokes(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MVPUBLISHER_HOME", str(tmp_path / "runtime"))

    class FakeDraft:
        draft_id = "b" * 32

    class FakeResult:
        platform_name = "xiaohongshu"
        status = "paused_for_manual_completion"
        result_url = "https://creator.xiaohongshu.com/publish/publish"

    monkeypatch.setattr(
        cli_module,
        "publish_draft_from_repository",
        lambda draft_id, repository, publishers, session_factory: (
            FakeDraft(),
            [FakeResult()],
        ),
    )
    runner = CliRunner()
    result = runner.invoke(app, ["publish-draft", "b" * 32])

    assert result.exit_code == 0
    assert "draft_id:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" in result.stdout
    assert "xiaohongshu:paused_for_manual_completion:" in result.stdout


def test_list_ids_filters_invalid_json_stems(tmp_path) -> None:
    drafts_root = tmp_path / "drafts"
    drafts_root.mkdir()
    valid_id = "a" * 32
    (drafts_root / f"{valid_id}.json").write_text("{}", encoding="utf-8")
    (drafts_root / "notes.json").write_text("{}", encoding="utf-8")
    (drafts_root / "ABC.json").write_text("{}", encoding="utf-8")

    repo = DraftRepository(drafts_root)

    assert repo.list_ids() == [valid_id]


def test_cli_serve_review_opens_google_chrome(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MVPUBLISHER_HOME", str(tmp_path / "runtime"))
    opened: dict[str, str] = {}
    uvicorn_calls: dict[str, object] = {}

    monkeypatch.setattr(
        cli_module,
        "_open_review_url_in_google_chrome",
        lambda url: opened.setdefault("url", url),
    )

    class FakeUvicorn:
        @staticmethod
        def run(app, host, port):
            uvicorn_calls["host"] = host
            uvicorn_calls["port"] = port

    monkeypatch.setitem(__import__("sys").modules, "uvicorn", FakeUvicorn)

    runner = CliRunner()
    result = runner.invoke(app, ["serve-review", "a" * 32, "--host", "127.0.0.1", "--port", "8123"])

    assert result.exit_code == 0
    assert opened["url"] == "http://127.0.0.1:8123/drafts/" + ("a" * 32)
    assert uvicorn_calls == {"host": "127.0.0.1", "port": 8123}
