from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import Literal, Optional
import textwrap

from .browser_reuse import BrowserReuseHandle
from .base import PlatformSessionRequest

SessionMode = Literal["browser_reuse", "playwright_persistent"]


@dataclass(frozen=True)
class SessionResolution:
    mode: SessionMode
    state_dir: Path
    reuse_handle: Optional[BrowserReuseHandle] = None


def resolve_session(
    request: PlatformSessionRequest, state_root: Path, live_browser_available: bool
) -> SessionResolution:
    state_dir = Path(state_root) / request.platform_name

    if live_browser_available:
        return SessionResolution(
            mode="browser_reuse",
            state_dir=state_dir,
            reuse_handle=BrowserReuseHandle(
                platform_name=request.platform_name,
                attached=True,
            ),
        )

    state_dir.mkdir(parents=True, exist_ok=True)
    return SessionResolution(
        mode="playwright_persistent",
        state_dir=state_dir,
    )


def open_url_with_persistent_playwright(state_dir: Path, url: str) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    launcher_script = textwrap.dedent(
        f"""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir={str(state_dir)!r},
                headless=False,
            )
            page = context.new_page()
            page.goto({url!r}, wait_until="domcontentloaded")
            page.wait_for_timeout(600000)
            context.close()
        """
    )
    subprocess.Popen(
        [sys.executable, "-c", launcher_script],
        start_new_session=True,
    )
