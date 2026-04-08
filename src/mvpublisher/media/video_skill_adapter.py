import json
import subprocess
import sys
from pathlib import Path


class VideoSkillAdapter:
    def __init__(
        self,
        process_video_script: Path,
        *,
        language: str = "zh",
        whisperkit_profile: str = "quality",
    ):
        self.process_video_script = Path(process_video_script)
        self.language = language
        self.whisperkit_profile = whisperkit_profile

    def run(self, source_video_path: Path, output_root: Path) -> dict:
        output_root = Path(output_root)
        if not output_root.exists():
            output_root.mkdir(parents=True, exist_ok=True)

        before = {
            path: (path.stat().st_mtime_ns, path.stat().st_size)
            for path in output_root.glob("*/pipeline_summary.json")
        }
        command = [
            sys.executable,
            str(self.process_video_script),
            "--video-path",
            str(source_video_path),
            "--output-root",
            str(output_root),
            "--review-only",
            "--overwrite",
            "--language",
            self.language,
            "--whisperkit-profile",
            self.whisperkit_profile,
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(message or "Video skill pipeline failed")

        summaries = [
            path
            for path in output_root.glob("*/pipeline_summary.json")
            if path not in before or (path.stat().st_size, path.stat().st_mtime_ns)
            != before[path]
        ]
        if not summaries:
            summaries = sorted(output_root.glob("*/pipeline_summary.json"))
            if not summaries:
                raise RuntimeError(f"Missing pipeline summary under {output_root}")
        if not summaries:
            raise RuntimeError(f"Missing pipeline summary under {output_root}")

        latest = max(summaries, key=lambda path: path.stat().st_mtime_ns)
        return json.loads(latest.read_text(encoding="utf-8"))
