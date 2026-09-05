import json
import subprocess
from pathlib import Path

import pytest

from scripts.inspect_recording import RecordingInspectionError, inspect_recording


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


@pytest.fixture
def media(tmp_path: Path) -> tuple[Path, Path]:
    valid = tmp_path / "valid.mp4"
    silent = tmp_path / "silent.mp4"
    ffmpeg(
        "-f", "lavfi", "-i", "color=c=white:s=320x240:d=1",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(valid),
    )
    ffmpeg("-f", "lavfi", "-i", "color=c=white:s=320x240:d=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(silent))
    return valid, silent


def timing(tmp_path: Path, duration: float = 1.0, cue: float = 0.5) -> Path:
    path = tmp_path / "timing.json"
    path.write_text(json.dumps({
        "duration_seconds": duration,
        "chapters": [{"id": "01-intro", "offset_seconds": 0, "duration_seconds": duration, "cues": [{"id": "open", "master_at_seconds": cue}]}]
    }), encoding="utf-8")
    return path


def test_inspection_accepts_matching_media_and_extracts_frames(tmp_path: Path, media):
    report = inspect_recording(media[0], timing(tmp_path), output_dir=tmp_path / "review", expected_width=320, expected_height=240)
    assert report["passed"] is True
    assert report["video_codec"] == "h264"
    assert report["audio_codec"] == "aac"
    assert (tmp_path / "review" / "verification.json").exists()
    assert list((tmp_path / "review" / "frames").glob("*.png"))


def test_inspection_extracts_a_frame_after_every_cue(tmp_path: Path, media):
    inspect_recording(media[0], timing(tmp_path, cue=0.3), output_dir=tmp_path / "review", expected_width=320, expected_height=240)
    names = {path.name for path in (tmp_path / "review" / "frames").glob("*.png")}
    assert "01-intro-open.png" in names, "each cue needs its own frame, not only chapter boundaries"


def test_inspection_flags_a_blank_opening_frame(tmp_path: Path):
    blank = tmp_path / "blank.mp4"
    ffmpeg(
        "-f", "lavfi", "-i", "color=c=white:s=320x240:d=1",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(blank),
    )
    report = inspect_recording(blank, timing(tmp_path), output_dir=tmp_path / "review", expected_width=320, expected_height=240)
    assert report["opening_frame_blank"] is True
    assert any("opening frame" in warning for warning in report["warnings"])


def test_inspection_rejects_missing_audio(tmp_path: Path, media):
    with pytest.raises(RecordingInspectionError, match="audio"):
        inspect_recording(media[1], timing(tmp_path), output_dir=tmp_path / "review", expected_width=320, expected_height=240)


def test_inspection_rejects_dimensions_duration_and_late_cues(tmp_path: Path, media):
    with pytest.raises(RecordingInspectionError, match="dimensions"):
        inspect_recording(media[0], timing(tmp_path), output_dir=tmp_path / "a", expected_width=1920, expected_height=1080)
    with pytest.raises(RecordingInspectionError, match="duration"):
        inspect_recording(media[0], timing(tmp_path, duration=2), output_dir=tmp_path / "b", expected_width=320, expected_height=240)
    with pytest.raises(RecordingInspectionError, match="cue"):
        inspect_recording(media[0], timing(tmp_path, cue=2), output_dir=tmp_path / "c", expected_width=320, expected_height=240)
