from dataclasses import dataclass
import subprocess


@dataclass(frozen=True)
class BrowserReuseHandle:
    platform_name: str
    attached: bool


def open_url_in_google_chrome(url: str) -> None:
    subprocess.run(
        ["open", "-a", "Google Chrome", url],
        check=True,
    )
