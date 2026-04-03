from pathlib import Path
import base64

from fastapi.testclient import TestClient

from mvpublisher.models.draft import PlatformName, PublishDraft
from mvpublisher.storage.drafts import DraftRepository
from mvpublisher.web.app import create_app


def test_index_route_renders(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MVPUBLISHER_HOME", str(tmp_path / "runtime"))
    repository = DraftRepository((tmp_path / "runtime") / "drafts")
    draft = _build_draft(tmp_path)
    repository.save(draft)

    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "Drafts" in response.text
    assert "本地多平台发布工作台" in response.text
    assert draft.draft_id in response.text
    assert "<title>Drafts</title>" in response.text
    assert response.headers["content-type"].startswith("text/html")


def test_draft_detail_template_contains_expected_heading() -> None:
    template_path = Path(__file__).resolve().parents[1] / "src" / "mvpublisher" / "web" / "templates" / "draft_detail.html"

    content = template_path.read_text(encoding="utf-8")

    assert "最终标题" in content
    assert "最终封面" in content
    assert "立即发布" in content
    assert "Draft Detail" in content


def test_draft_detail_shows_real_draft_confirmation_fields(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MVPUBLISHER_HOME", str(tmp_path / "runtime"))
    repository = DraftRepository((tmp_path / "runtime") / "drafts")
    draft = repository.save(_build_draft(tmp_path))

    client = TestClient(create_app())

    response = client.get(f"/drafts/{draft.draft_id}")

    assert response.status_code == 200
    assert "最终标题" in response.text
    assert "最终封面" in response.text
    assert "立即发布" in response.text
    assert draft.summary in response.text
    assert draft.title_suggestions[0] in response.text


def test_approval_api_persists_selected_values(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MVPUBLISHER_HOME", str(tmp_path / "runtime"))
    repository = DraftRepository((tmp_path / "runtime") / "drafts")
    draft = repository.save(_build_draft(tmp_path))
    cover = tmp_path / "selected-cover.jpg"
    cover.write_text("cover", encoding="utf-8")
    client = TestClient(create_app())

    response = client.post(
        f"/api/drafts/{draft.draft_id}/approval",
        json={
            "selected_title": "最终标题",
            "selected_cover_path": str(cover),
            "selected_platforms": ["xiaohongshu", "douyin"],
            "publish_now": True,
        },
    )

    assert response.status_code == 200
    reloaded = repository.load(draft.draft_id)
    assert reloaded.selected_title == "最终标题"
    assert reloaded.selected_cover_path == cover
    assert reloaded.selected_platforms == [
        PlatformName.XIAOHONGSHU,
        PlatformName.DOUYIN,
    ]
    assert reloaded.approval_status.value == "approved"
    assert reloaded.publish_mode == "immediate"


def test_cover_upload_api_writes_uploaded_cover(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MVPUBLISHER_HOME", str(tmp_path / "runtime"))
    repository = DraftRepository((tmp_path / "runtime") / "drafts")
    draft = repository.save(_build_draft(tmp_path))
    client = TestClient(create_app())

    response = client.post(
        f"/api/drafts/{draft.draft_id}/cover-upload",
        json={
            "filename": "manual.png",
            "content_base64": base64.b64encode(b"png-bytes").decode("ascii"),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["cover_path"].endswith("manual-cover.png")
    assert Path(payload["cover_path"]).exists()


def _build_draft(tmp_path: Path) -> PublishDraft:
    video = tmp_path / "video.mp4"
    cover = tmp_path / "frame-01.jpg"
    video.write_text("video", encoding="utf-8")
    cover.write_text("cover", encoding="utf-8")
    return PublishDraft.new(source_video_path=video).model_copy(
        update={
            "summary": "这是一个真实草稿摘要",
            "title_suggestions": ["一条视频发三端"],
            "cover_suggestions": ["多平台自动发布"],
            "cover_candidate_paths": [cover],
        }
    )
