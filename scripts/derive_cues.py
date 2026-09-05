"""Resolve anchored cues to measured word timestamps.

Each anchored cue names a phrase from the *approved narration*. The phrase is located in
that text (which we control exactly), the approved tokens are aligned to the transcript's
word stream with a fuzzy sequence match, and the cue takes the measured start time of the
aligned word. Anchoring to the approved text rather than to the transcript means an ASR
slip such as «البكالوريوز» for «البكالوريوس» cannot move or lose a cue.

Cue times are never estimated from character counts or reading speed.
"""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path

from .manifest import Chapter, load_manifest, save_manifest
from .transcribe_audio import normalize_words

MAX_ALIGNMENT_DRIFT = 3


def _phrase_index(approved: list[str], phrase: list[str]) -> int | None:
    for start in range(len(approved) - len(phrase) + 1):
        if approved[start : start + len(phrase)] == phrase:
            return start
    return None


def _alignment(approved: list[str], spoken: list[str]) -> dict[int, int]:
    matcher = difflib.SequenceMatcher(a=approved, b=spoken, autojunk=False)
    mapping: dict[int, int] = {}
    for a_start, b_start, size in matcher.get_matching_blocks():
        for offset in range(size):
            mapping[a_start + offset] = b_start + offset
    return mapping


def _nearest_aligned(mapping: dict[int, int], index: int, limit: int) -> tuple[int, int] | None:
    """Return (spoken index, distance) for the aligned approved token nearest `index`."""
    for distance in range(limit + 1):
        for candidate in (index + distance, index - distance):
            if candidate in mapping:
                return mapping[candidate], distance
    return None


def resolve_chapter(chapter: Chapter, transcript: dict) -> list[str]:
    """Fill `at_seconds` for every anchored cue; return human-readable warnings."""
    words = [word for segment in transcript["segments"] for word in segment["words"]]
    spoken: list[str] = []
    starts: list[float] = []
    for word in words:
        tokens = normalize_words(word["word"])
        if tokens:
            spoken.append(tokens[0])
            starts.append(float(word["start"]))
    approved = normalize_words(chapter.narration)
    mapping = _alignment(approved, spoken)
    warnings: list[str] = []

    for cue in chapter.cues:
        if cue.anchor is None:
            continue
        index = _phrase_index(approved, normalize_words(cue.anchor))
        if index is None:
            raise ValueError(
                f"{chapter.id}/{cue.id}: anchor {cue.anchor!r} is not in the approved narration"
            )
        aligned = _nearest_aligned(mapping, index, len(approved))
        if aligned is None:
            raise ValueError(f"{chapter.id}/{cue.id}: no transcript word aligns with the anchor")
        spoken_index, distance = aligned
        if distance > MAX_ALIGNMENT_DRIFT:
            warnings.append(
                f"{chapter.id}/{cue.id}: nearest aligned word is {distance} tokens away; check the transcript"
            )
        cue.at_seconds = round(starts[spoken_index], 3)

    # Times must stay strictly increasing for the scheduler; nudge exact ties apart.
    previous = -1.0
    for cue in chapter.cues:
        if cue.at_seconds is None:
            continue
        if cue.at_seconds <= previous:
            cue.at_seconds = round(previous + 0.05, 3)
        previous = cue.at_seconds
    return warnings


def derive_cues(manifest_path: Path) -> list[str]:
    manifest = load_manifest(manifest_path)
    root = manifest_path.resolve().parent
    warnings: list[str] = []
    for chapter in manifest.chapters:
        if not chapter.unresolved_cues:
            continue
        transcript_path = root / f"{chapter.audio_path}.transcript.json"
        if not transcript_path.exists():
            raise FileNotFoundError(
                f"{chapter.id}: transcribe the chapter before deriving cues ({transcript_path})"
            )
        transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
        warnings.extend(resolve_chapter(chapter, transcript))
    # Re-validate ordering now that every cue carries a time.
    manifest = manifest.model_validate(manifest.model_dump())
    save_manifest(manifest_path, manifest)
    return warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve anchored cues to measured word timestamps")
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    warnings = derive_cues(args.manifest)
    manifest = load_manifest(args.manifest)
    for chapter in manifest.chapters:
        cues = ", ".join(f"{cue.id}@{cue.at_seconds:.2f}" for cue in chapter.cues)
        print(f"{chapter.id}: {cues}")
    for line in warnings:
        print(f"warning: {line}")


if __name__ == "__main__":
    main()
