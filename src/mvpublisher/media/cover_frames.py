from pathlib import Path
import subprocess


def default_cover_timestamps(duration_seconds: float, count: int = 3) -> list[float]:
    if duration_seconds <= 0:
        return []
    if count <= 1:
        return [round(duration_seconds / 2, 3)]
    start_ratio = 0.2
    end_ratio = 0.8
    gap = (end_ratio - start_ratio) / (count - 1)
    return [
        round(duration_seconds * (start_ratio + gap * index), 3)
        for index in range(count)
    ]


def build_cover_frame_command(
    ffmpeg_path: str,
    video_path: Path,
    timestamp: float,
    output_path: Path,
) -> list[str]:
    return [
        ffmpeg_path,
        "-y",
        "-ss",
        f"{timestamp:.3f}",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        str(output_path),
    ]


def extract_cover_frames(
    video_path: Path,
    output_dir: Path,
    *,
    ffmpeg_path: str = "ffmpeg",
    ffprobe_path: str = "ffprobe",
    count: int = 3,
) -> list[Path]:
    duration_seconds = probe_duration_seconds(video_path, ffprobe_path=ffprobe_path)
    timestamps = default_cover_timestamps(duration_seconds, count=count)
    if not timestamps:
        return []

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    created_paths: list[Path] = []
    for index, timestamp in enumerate(timestamps, start=1):
        output_path = output_dir / f"frame-{index:02d}.jpg"
        command = build_cover_frame_command(
            ffmpeg_path=ffmpeg_path,
            video_path=video_path,
            timestamp=timestamp,
            output_path=output_path,
        )
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode == 0 and output_path.exists():
            created_paths.append(output_path)
    return created_paths


def probe_duration_seconds(video_path: Path, *, ffprobe_path: str = "ffprobe") -> float:
    completed = subprocess.run(
        [
            ffprobe_path,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return 0.0
    try:
        return max(0.0, float((completed.stdout or "").strip()))
    except ValueError:
        return 0.0
