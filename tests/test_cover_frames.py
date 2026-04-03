from pathlib import Path

from mvpublisher.media.cover_frames import build_cover_frame_command, default_cover_timestamps


def test_default_cover_timestamps_for_short_video():
    timestamps = default_cover_timestamps(4.5, count=3)

    assert timestamps == [0.9, 2.25, 3.6]


def test_build_cover_frame_command_uses_expected_ffmpeg_shape(tmp_path):
    command = build_cover_frame_command(
        ffmpeg_path="ffmpeg",
        video_path=tmp_path / "input.mov",
        timestamp=1.5,
        output_path=tmp_path / "frame-01.jpg",
    )

    assert command[0] == "ffmpeg"
    assert "-ss" in command
    assert str(tmp_path / "input.mov") in command
    assert str(tmp_path / "frame-01.jpg") in command
    assert "-frames:v" in command
    assert "1" in command
