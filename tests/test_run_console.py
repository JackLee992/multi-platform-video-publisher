from pathlib import Path

from mvpublisher.models.draft import PlatformName
from mvpublisher.web.run_console import (
    RunConsoleLogEntry,
    RunConsolePlatformResult,
    RunConsoleState,
    RunConsoleStore,
)


def test_run_console_store_writes_and_reads_latest_state(tmp_path: Path) -> None:
    store = RunConsoleStore(tmp_path)
    state = RunConsoleState(
        draft_id="d" * 32,
        status="running",
        execution_mode="autopublish",
        logs=[
            RunConsoleLogEntry(level="info", message="run started"),
        ],
        results=[
            RunConsolePlatformResult(
                platform_name=PlatformName.XIAOHONGSHU,
                status="submitted_for_verification",
                success_signal="xiaohongshu_submit_requested",
            )
        ],
    )

    store.save_latest(state)

    loaded = store.load_latest("d" * 32)
    assert loaded is not None
    assert loaded.status == "running"
    assert loaded.logs[0].message == "run started"
    assert loaded.results[0].platform_name == PlatformName.XIAOHONGSHU
