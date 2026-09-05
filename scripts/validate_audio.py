from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


class AudioValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class AudioInfo:
    codec_name: str
    duration_seconds: float
    sample_rate: int
    channels: int
    leading_silence_seconds: float = 0
    trailing_silence_seconds: float = 0


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def probe_audio(path: str | Path) -> AudioInfo:
    source = Path(path)
    result = _run([
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=codec_name,sample_rate,channels:format=duration",
        "-of", "json", str(source),
    ])
    try:
        payload = json.loads(result.stdout)
        stream = payload["streams"][0]
        duration = float(payload["format"]["duration"])
        return AudioInfo(
            codec_name=stream["codec_name"],
            duration_seconds=duration,
            sample_rate=int(stream["sample_rate"]),
            channels=int(stream["channels"]),
        )
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise AudioValidationError(f"{source} is not readable audio") from error


def boundary_silence(path: str | Path, duration: float) -> tuple[float, float]:
    result = _run([
        "ffmpeg", "-hide_banner", "-i", str(path), "-af",
        "silencedetect=noise=-45dB:d=0.15", "-f", "null", "-",
    ])
    starts = [float(value) for value in re.findall(r"silence_start: ([0-9.]+)", result.stderr)]
    ends = [float(value) for value in re.findall(r"silence_end: ([0-9.]+)", result.stderr)]
    leading = ends[0] if starts and ends and starts[0] <= 0.02 else 0.0
    trailing = 0.0
    if starts and (len(starts) > len(ends) or starts[-1] > (ends[-1] if ends else -1)):
        trailing = max(0.0, duration - starts[-1])
    elif starts and ends and ends[-1] >= duration - 0.05:
        trailing = max(0.0, duration - starts[-1])
    return leading, trailing


def validate_audio(
    path: str | Path,
    *,
    max_boundary_silence: float = 1.0,
    min_duration: float = 0.1,
) -> AudioInfo:
    info = probe_audio(path)
    if info.duration_seconds < min_duration:
        raise AudioValidationError(f"audio is shorter than {min_duration:g} seconds")
    leading, trailing = boundary_silence(path, info.duration_seconds)
    if leading > max_boundary_silence:
        raise AudioValidationError(f"leading silence is {leading:.2f} seconds")
    if trailing > max_boundary_silence:
        raise AudioValidationError(f"trailing silence is {trailing:.2f} seconds")
    return AudioInfo(**{**asdict(info), "leading_silence_seconds": leading, "trailing_silence_seconds": trailing})


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate one narration audio file")
    parser.add_argument("audio", type=Path)
    parser.add_argument("--max-boundary-silence", type=float, default=1.0)
    parser.add_argument("--min-duration", type=float, default=0.1)
    args = parser.parse_args()
    print(json.dumps(asdict(validate_audio(args.audio, max_boundary_silence=args.max_boundary_silence, min_duration=args.min_duration)), indent=2))


if __name__ == "__main__":
    main()
