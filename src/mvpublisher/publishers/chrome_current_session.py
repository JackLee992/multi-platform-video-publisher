from pathlib import Path
import subprocess

from mvpublisher.execution_modes import ExecutionMode
from mvpublisher.models.draft import PlatformName, PublishDraft


def run_current_session_publish_script(
    *, draft: PublishDraft, platform_name: PlatformName
) -> None:
    script_path = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "chrome_current_session_publish.sh"
    )
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
    if draft.execution_mode is ExecutionMode.AUTOFILL_ONLY:
        command.append("--skip-publish")
    subprocess.run(command, check=True)
