import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.transcribe_audio import transcribe


class FakeModel:
    """Stands in for faster_whisper.WhisperModel with a scripted transcript."""

    def __init__(self, words: list[tuple[str, float]], language: str = "ar"):
        self.words = words
        self.language = language

    def transcribe(self, _path: str, word_timestamps: bool):
        assert word_timestamps
        rows = [SimpleNamespace(start=at, end=at + 0.3, word=f" {word}") for word, at in self.words]
        segment = SimpleNamespace(
            start=rows[0].start, end=rows[-1].end,
            text=" ".join(word for word, _ in self.words), words=rows,
        )
        return iter([segment]), SimpleNamespace(language=self.language)


def manifest(tmp_path: Path, narration: str) -> Path:
    (tmp_path / "chapters").mkdir()
    (tmp_path / "chapters" / "01-intro.mp3").write_bytes(b"audio")
    path = tmp_path / "production.json"
    path.write_text(json.dumps({
        "title": "Fixture", "locale": "ar-SA",
        "voice": {"provider": "supplied", "model": "supplied", "voice_id": "n", "language": "ar"},
        "chapters": [{"id": "01-intro", "narration": narration, "audio_path": "chapters/01-intro.mp3"}],
        "master_audio_path": "master.mp3",
    }, ensure_ascii=False), encoding="utf-8")
    return path


def test_low_coverage_still_writes_the_transcript_and_names_missing_words(tmp_path: Path):
    path = manifest(tmp_path, "مرحبًا بك في رافد")
    model = FakeModel([("مرحبا", 0.0), ("بك", 0.4)])

    with pytest.raises(RuntimeError, match="coverage") as excinfo:
        transcribe(path, "01-intro", model_name="small", threshold=0.9, model=model)

    output = tmp_path / "chapters" / "01-intro.mp3.transcript.json"
    assert output.exists(), "the transcript must be kept so the failure can be inspected"
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["coverage"] == pytest.approx(0.5)
    assert payload["missing_words"] == ["في", "رافد"]
    assert "في" in str(excinfo.value)


def test_full_coverage_records_word_timestamps(tmp_path: Path):
    path = manifest(tmp_path, "مرحبًا بك")
    output = transcribe(path, "01-intro", model_name="small", threshold=0.9, model=FakeModel([("مرحبا", 0.0), ("بك", 0.4)]))
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["segments"][0]["words"][1]["start"] == pytest.approx(0.4)
    assert payload["audio_sha256"] == hashlib.sha256(b"audio").hexdigest()
