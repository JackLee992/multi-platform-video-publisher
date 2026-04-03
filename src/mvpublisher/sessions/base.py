from dataclasses import dataclass
import re
from typing import Literal, Optional


_PLATFORM_NAME_PATTERN = re.compile(r"^[a-z0-9_]+$")
BrowserHint = Literal["browser_reuse", "playwright_persistent"]


@dataclass(frozen=True)
class PlatformSessionRequest:
    platform_name: str
    browser_hint: Optional[BrowserHint] = None

    def __post_init__(self) -> None:
        if not _PLATFORM_NAME_PATTERN.fullmatch(self.platform_name):
            raise ValueError("platform_name must be a safe lowercase path segment")
