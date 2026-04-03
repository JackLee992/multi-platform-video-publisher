from mvpublisher.sessions.base import PlatformSessionRequest
from mvpublisher.sessions.browser_reuse import BrowserReuseHandle
from mvpublisher.sessions.playwright_fallback import (
    SessionResolution,
    resolve_session,
)
import pytest


def test_resolve_session_prefers_browser_reuse_when_live_browser_available(tmp_path):
    request = PlatformSessionRequest(platform_name="douyin")
    state_root = tmp_path / "state"

    result: SessionResolution = resolve_session(
        request=request,
        state_root=state_root,
        live_browser_available=True,
    )

    assert result.mode == "browser_reuse"
    assert result.state_dir == state_root / "douyin"
    assert result.reuse_handle == BrowserReuseHandle(
        platform_name="douyin",
        attached=True,
    )


def test_resolve_session_falls_back_to_playwright_when_live_browser_unavailable(tmp_path):
    request = PlatformSessionRequest(platform_name="douyin")
    state_root = tmp_path / "state"
    expected_state_dir = state_root / "douyin"
    assert not expected_state_dir.exists()

    result: SessionResolution = resolve_session(
        request=request,
        state_root=state_root,
        live_browser_available=False,
    )

    assert result.mode == "playwright_persistent"
    assert result.state_dir == expected_state_dir
    assert result.reuse_handle is None
    assert expected_state_dir.exists()
    assert expected_state_dir.is_dir()


def test_platform_session_request_rejects_unsafe_platform_name():
    with pytest.raises(ValueError, match="platform_name"):
        PlatformSessionRequest(platform_name="../shared")
