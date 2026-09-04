from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from .manifest import load_manifest, save_manifest


def normalize_words(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)


def coverage_ratio(approved: list[str], spoken: list[str]) -> float:
    if not approved:
        return 1.0
    available = Counter(spoken)
    matched = 0
    for token in approved:
        if available[token]:
            available[token] -= 1
            matched += 1
    return matched / len(approved)


def transcribe(manifest_path: Path, chapter_id: str, *, model_name: str, threshold: float) -> Path:
    from faster_whisper import WhisperModel

    manifest = load_manifest(manifest_path)
    chapter = next((item for item in manifest.chapters if item.id == chapter_id), None)
    if chapter is None:
        raise ValueError(f"Unknown chapter: {chapter_id}")
    audio_path = manifest_path.resolve().parent / chapter.audio_path
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(audio_path), word_timestamps=True)
    segment_rows = []
    transcript_parts = []
    for segment in segments:
        transcript_parts.append(segment.text.strip())
        segment_rows.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "words": [
                {"start": word.start, "end": word.end, "word": word.word}
                for word in (segment.words or [])
            ],
        })
    transcript = " ".join(part for part in transcript_parts if part)
    coverage = coverage_ratio(normalize_words(chapter.narration), normalize_words(transcript))
    detected = info.language.lower()
    expected = manifest.voice.language.split("-")[0].lower()
    if detected != expected:
        raise RuntimeError(f"detected language {detected!r}, expected {expected!r}")
    if coverage < threshold:
        raise RuntimeError(f"narration coverage {coverage:.1%} is below {threshold:.1%}")
    chapter.transcript = transcript
    save_manifest(manifest_path, manifest)
    output = audio_path.with_suffix(audio_path.suffix + ".transcript.json")
    output.write_text(json.dumps({
        "chapter_id": chapter.id,
        "language": detected,
        "coverage": coverage,
        "transcript": transcript,
        "segments": segment_rows,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe and verify one narration chapter")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--chapter", required=True)
    parser.add_argument("--model", default="small")
    parser.add_argument("--coverage", type=float, default=0.90)
    args = parser.parse_args()
    print(transcribe(args.manifest, args.chapter, model_name=args.model, threshold=args.coverage))


if __name__ == "__main__":
    main()
