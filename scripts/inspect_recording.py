from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path
from typing import Any


class RecordingInspectionError(RuntimeError):
    pass


def probe(path: Path) -> dict[str, Any]:
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=codec_name,codec_type,width,height,duration:format=duration", "-of", "json", str(path),
    ], text=True, capture_output=True, check=False)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RecordingInspectionError("recording is not readable media") from error


def inspect_recording(
    recording: Path,
    timing_path: Path,
    *,
    output_dir: Path,
    expected_width: int = 1920,
    expected_height: int = 1080,
    duration_tolerance: float = 0.25,
) -> dict[str, Any]:
    payload = probe(recording)
    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    streams = payload.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    media_duration = float(payload.get("format", {}).get("duration", 0))
    expected_duration = float(timing["duration_seconds"])
    failures: list[str] = []
    if not video:
        failures.append("video stream is missing")
    elif video.get("codec_name") != "h264":
        failures.append("video codec must be h264")
    elif (video.get("width"), video.get("height")) != (expected_width, expected_height):
        failures.append(f"video dimensions must be {expected_width}x{expected_height}")
    if not audio:
        failures.append("audio stream is missing")
    elif audio.get("codec_name") != "aac":
        failures.append("audio codec must be aac")
    stream_durations = {}
    for name, stream in (("video", video), ("audio", audio)):
        if stream is None:
            continue
        try:
            seconds = float(stream.get("duration", "nan"))
        except (TypeError, ValueError):
            seconds = float("nan")
        if not math.isfinite(seconds) or seconds <= 0:
            failures.append(f"{name} stream duration is unavailable or invalid")
        else:
            stream_durations[name] = seconds
            if abs(seconds - expected_duration) > duration_tolerance:
                failures.append(f"{name} stream duration {seconds:.3f}s differs from narration duration {expected_duration:.3f}s")
    if len(stream_durations) == 2 and abs(stream_durations["video"] - stream_durations["audio"]) > duration_tolerance:
        failures.append("audio and video stream durations differ")
    if abs(media_duration - expected_duration) > duration_tolerance:
        failures.append(
            f"recording duration {media_duration:.3f}s differs from audio duration {expected_duration:.3f}s"
        )
    cues = [cue for chapter in timing.get("chapters", []) for cue in chapter.get("cues", [])]
    if any(float(cue["master_at_seconds"]) > media_duration for cue in cues):
        failures.append("a cue exceeds the recording duration")

    warnings: list[str] = []
    opening_blank = None
    if not failures:
        opening_blank = frame_is_blank(recording, 0.0)
        if opening_blank:
            warnings.append(
                "opening frame is blank: navigate and settle the page before the narration "
                "clock starts, then trim the pre-roll at mux time"
            )

    report = {
        "passed": not failures,
        "failures": failures,
        "warnings": warnings,
        "recording": str(recording),
        "duration_seconds": media_duration,
        "expected_duration_seconds": expected_duration,
        "stream_durations": stream_durations,
        "video_codec": video.get("codec_name") if video else None,
        "audio_codec": audio.get("codec_name") if audio else None,
        "width": video.get("width") if video else None,
        "height": video.get("height") if video else None,
        "opening_frame_blank": opening_blank,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "verification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    if failures:
        raise RecordingInspectionError("; ".join(failures))

    frames = output_dir / "frames"
    frames.mkdir(exist_ok=True)
    last = max(0, media_duration - 0.04)
    for chapter in timing.get("chapters", []):
        boundary = float(chapter["offset_seconds"])
        samples = [
            ("before", max(0, boundary - 1)),
            ("at", min(boundary, last)),
            ("after", min(boundary + 2, last)),
        ]
        # One frame shortly after every cue as well: chapter boundaries alone missed a
        # stale record opened mid-chapter, which only a per-action frame reveals.
        samples.extend(
            (cue["id"], min(float(cue["master_at_seconds"]) + CUE_FRAME_DELAY, last))
            for cue in chapter.get("cues", [])
        )
        for label, seconds in samples:
            extract_frame(recording, seconds, frames / f"{chapter['id']}-{label}.png")
    return report


CUE_FRAME_DELAY = 1.0


def extract_frame(recording: Path, seconds: float, destination: Path) -> None:
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-ss", str(seconds), "-i", str(recording),
        "-frames:v", "1", str(destination),
    ], check=True)


def frame_is_blank(recording: Path, seconds: float, *, threshold: float = 2.0) -> bool:
    """True when the frame has almost no luminance range — a white or black page."""
    result = subprocess.run([
        "ffmpeg", "-v", "info", "-ss", str(seconds), "-i", str(recording), "-frames:v", "1",
        "-vf", "signalstats,metadata=print:key=lavfi.signalstats.YMIN,metadata=print:key=lavfi.signalstats.YMAX",
        "-f", "null", "-",
    ], text=True, capture_output=True, check=False)
    values = {}
    for line in result.stderr.splitlines():
        for key in ("YMIN", "YMAX"):
            marker = f"lavfi.signalstats.{key}="
            if marker in line:
                values[key] = float(line.split(marker, 1)[1].strip())
    if "YMIN" not in values or "YMAX" not in values:
        return False
    return (values["YMAX"] - values["YMIN"]) <= threshold


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a completed narrated demo recording")
    parser.add_argument("recording", type=Path)
    parser.add_argument("--timing", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("artifacts/demo-review"))
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    args = parser.parse_args()
    report = inspect_recording(args.recording, args.timing, output_dir=args.output, expected_width=args.width, expected_height=args.height)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
