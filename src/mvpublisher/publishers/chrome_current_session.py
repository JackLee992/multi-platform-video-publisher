from pathlib import Path
import subprocess

from mvpublisher.execution_modes import ExecutionMode
from mvpublisher.models.draft import PlatformName, PublishDraft


def _find_current_session_publish_script() -> Path:
    candidate_roots = [Path.cwd(), *Path.cwd().parents, *Path(__file__).resolve().parents]
    for root in candidate_roots:
        script_path = root / "scripts" / "chrome_current_session_publish.sh"
        if script_path.exists():
            return script_path
    raise FileNotFoundError("Could not locate scripts/chrome_current_session_publish.sh")


def run_current_session_publish_script(
    *, draft: PublishDraft, platform_name: PlatformName
) -> None:
    script_path = _find_current_session_publish_script()
    description = draft.summary or draft.selected_title or ""
    command = [
        "/bin/bash",
        str(script_path),
        "--video",
        str(draft.source_video_path),
        "--title",
        draft.selected_title or "",
        "--description",
        description,
        "--platform",
        platform_name.value,
    ]
    if draft.selected_cover_path is not None:
        command.extend(["--cover", str(draft.selected_cover_path)])
    if draft.execution_mode is ExecutionMode.AUTOFILL_ONLY:
        command.append("--skip-publish")
    subprocess.run(command, check=True)
