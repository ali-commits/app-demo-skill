from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from typing import Any
from pathlib import Path

from .manifest import load_manifest, save_manifest


ARABIC_VARIANTS = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
    "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي",
})
TATWEEL = "ـ"


def normalize_words(text: str) -> list[str]:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(
        char for char in decomposed
        if not unicodedata.category(char).startswith("M") and char != TATWEEL
    )
    normalized = unicodedata.normalize("NFKC", stripped).casefold().translate(ARABIC_VARIANTS)
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


def missing_words(approved: list[str], spoken: list[str]) -> list[str]:
    available = Counter(spoken)
    missing = []
    for token in approved:
        if available[token]:
            available[token] -= 1
        else:
            missing.append(token)
    return missing


def transcribe(
    manifest_path: Path,
    chapter_id: str,
    *,
    model_name: str,
    threshold: float,
    device: str = "cpu",
    compute_type: str = "int8",
    model: Any | None = None,
) -> Path:
    manifest = load_manifest(manifest_path)
    chapter = next((item for item in manifest.chapters if item.id == chapter_id), None)
    if chapter is None:
        raise ValueError(f"Unknown chapter: {chapter_id}")
    audio_path = manifest_path.resolve().parent / chapter.audio_path
    if model is None:
        from faster_whisper import WhisperModel

        model = WhisperModel(model_name, device=device, compute_type=compute_type)
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
    approved, spoken = normalize_words(chapter.narration), normalize_words(transcript)
    coverage = coverage_ratio(approved, spoken)
    missing = missing_words(approved, spoken)
    detected = info.language.lower()
    expected = manifest.voice.language.split("-")[0].lower()

    output = audio_path.with_suffix(audio_path.suffix + ".transcript.json")
    output.write_text(json.dumps({
        "chapter_id": chapter.id,
        "language": detected,
        "coverage": coverage,
        "missing_words": missing,
        "transcript": transcript,
        "segments": segment_rows,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if detected != expected:
        raise RuntimeError(f"detected language {detected!r}, expected {expected!r} (transcript kept at {output})")
    if coverage < threshold:
        raise RuntimeError(
            f"narration coverage {coverage:.1%} is below {threshold:.1%}; "
            f"missing: {' '.join(missing[:12])} (transcript kept at {output})"
        )
    chapter.transcript = transcript
    save_manifest(manifest_path, manifest)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe and verify one narration chapter")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--chapter", required=True)
    parser.add_argument("--model", default="small")
    parser.add_argument("--coverage", type=float, default=0.90)
    # `medium` and larger are many times slower than real time on CPU; `small` with the
    # diacritic-insensitive coverage check has been sufficient for cue anchoring.
    parser.add_argument("--device", default="cpu", help="cpu or cuda")
    parser.add_argument("--compute-type", default="int8", help="int8, float16, float32")
    args = parser.parse_args()
    print(transcribe(
        args.manifest, args.chapter,
        model_name=args.model, threshold=args.coverage,
        device=args.device, compute_type=args.compute_type,
    ))


if __name__ == "__main__":
    main()
