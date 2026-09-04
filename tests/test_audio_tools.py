import json
import subprocess
from pathlib import Path

import pytest

from scripts.assemble_audio import assemble
from scripts.transcribe_audio import coverage_ratio, normalize_words
from scripts.validate_audio import AudioValidationError, probe_audio, validate_audio


def run_ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


@pytest.fixture
def tones(tmp_path: Path) -> tuple[Path, Path]:
    first = tmp_path / "first.wav"
    second = tmp_path / "second.wav"
    run_ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=0.5", str(first))
    run_ffmpeg("-f", "lavfi", "-i", "sine=frequency=660:duration=0.7", str(second))
    return first, second


def test_probe_and_validate_audio(tones):
    info = probe_audio(tones[0])
    assert info.codec_name == "pcm_s16le"
    assert info.duration_seconds == pytest.approx(0.5, abs=0.05)
    assert info.sample_rate == 44_100
    assert validate_audio(tones[0]).duration_seconds == pytest.approx(0.5, abs=0.05)


def test_validation_rejects_empty_file(tmp_path: Path):
    empty = tmp_path / "empty.wav"
    empty.touch()
    with pytest.raises(AudioValidationError, match="readable audio"):
        validate_audio(empty)


def test_validation_detects_excessive_trailing_silence(tmp_path: Path):
    audio = tmp_path / "trailing.wav"
    run_ffmpeg(
        "-f", "lavfi", "-i", "sine=frequency=440:duration=0.4",
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono:d=0.8",
        "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1",
        str(audio),
    )
    with pytest.raises(AudioValidationError, match="trailing silence"):
        validate_audio(audio, max_boundary_silence=0.5)


def test_normalized_transcript_coverage():
    approved = normalize_words("Halo, sekolah Cakrawala!")
    spoken = normalize_words("halo sekolah cakrawala")
    assert coverage_ratio(approved, spoken) == 1.0
    assert coverage_ratio(approved, normalize_words("halo")) < 0.5


def test_assembly_adds_gap_and_writes_timing(tmp_path: Path, tones):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "title": "Audio fixture",
        "locale": "en-US",
        "voice": {"provider": "supplied", "model": "supplied", "voice_id": "narrator", "language": "en"},
        "chapters": [
            {"id": "01-first", "narration": "First", "audio_path": tones[0].name, "duration_seconds": 0.5},
            {"id": "02-second", "narration": "Second", "audio_path": tones[1].name, "duration_seconds": 0.7}
        ],
        "master_audio_path": "master.wav",
        "chapter_gap_seconds": 0.25
    }), encoding="utf-8")
    output, timing = assemble(manifest_path)
    assert probe_audio(output).duration_seconds == pytest.approx(1.45, abs=0.12)
    payload = json.loads(timing.read_text(encoding="utf-8"))
    assert payload["chapters"][0]["offset_seconds"] == 0
    assert payload["chapters"][1]["offset_seconds"] == pytest.approx(0.75, abs=0.06)
