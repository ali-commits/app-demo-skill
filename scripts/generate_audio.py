from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from .manifest import load_manifest, save_manifest
from .providers import GeneratedAudio, provider_for

__all__ = ["GeneratedAudio", "estimate", "generate"]


def estimate(
    manifest_path: Path,
    *,
    audition_characters: int | None = None,
    audition_seconds: float | None = None,
) -> dict:
    """Billable characters per chapter, plus a duration projection from a measured audition.

    Providers bill per character, so this is the cost figure to report before full
    generation. The projection is deliberately derived from a real audition's measured
    rate — it exists to catch a script that will overrun its ceiling *before* credits are
    spent, and it is never used to time browser cues.
    """
    manifest = load_manifest(manifest_path)
    chapters = {chapter.id: len(chapter.narration) for chapter in manifest.chapters}
    report: dict = {"chapters": chapters, "total_characters": sum(chapters.values())}
    if audition_characters and audition_seconds:
        rate = audition_characters / audition_seconds
        speech = report["total_characters"] / rate
        gaps = manifest.chapter_gap_seconds * max(0, len(manifest.chapters) - 1)
        report.update({
            "measured_characters_per_second": round(rate, 3),
            "projected_seconds": round(speech, 3),
            "projected_seconds_with_gaps": round(speech + gaps, 3),
        })
    return report


def generate(
    manifest_path: Path,
    chapter_id: str,
    *,
    sample: bool,
    force: bool,
    voice_id: str | None = None,
) -> Path:
    manifest = load_manifest(manifest_path)
    try:
        index = next(i for i, item in enumerate(manifest.chapters) if item.id == chapter_id)
    except StopIteration as error:
        raise ValueError(f"Unknown chapter: {chapter_id}") from error
    chapter = manifest.chapters[index]
    root = manifest_path.resolve().parent
    # An audition may try another voice without editing the manifest; the manifest's
    # own voice is only ever changed deliberately, after a voice is approved.
    voice = manifest.voice.model_copy(update={"voice_id": voice_id}) if voice_id else manifest.voice
    if voice_id and not sample:
        raise ValueError("--voice is for auditions only; set the manifest voice for full generation")
    output = (
        root / "auditions" / f"{chapter.id}-{voice.voice_id}"
        if sample
        else root / chapter.audio_path
    )
    existing = list(output.parent.glob(f"{output.name}.*")) if sample else [output] if output.exists() else []
    if existing and not force:
        raise FileExistsError(f"Refusing to overwrite {existing[0]}; pass --force to regenerate")
    provider = provider_for(voice)
    previous_text = manifest.chapters[index - 1].narration if index else ""
    next_text = manifest.chapters[index + 1].narration if index + 1 < len(manifest.chapters) else ""
    generated = provider.generate(
        chapter.narration,
        voice,
        previous_text=previous_text,
        next_text=next_text,
    )
    output = output.with_suffix(generated.extension)
    if output.exists() and not force:
        raise FileExistsError(f"Refusing to overwrite {output}; pass --force to regenerate")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(generated.content)
    if not sample:
        chapter.audio_path = str(output.relative_to(root))
        chapter.narration_sha256 = hashlib.sha256(chapter.narration.encode("utf-8")).hexdigest()
        chapter.generation_metadata = generated.metadata
        save_manifest(manifest_path, manifest)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate one approved narration chapter")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--chapter", help="chapter id to generate (omit with --estimate)")
    parser.add_argument("--sample", action="store_true", help="write an audition instead of the chapter")
    parser.add_argument("--voice", help="audition a different voice id without editing the manifest")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--estimate", action="store_true", help="report billable characters and exit")
    parser.add_argument("--audition-characters", type=int, help="characters of a measured audition")
    parser.add_argument("--audition-seconds", type=float, help="measured duration of that audition")
    args = parser.parse_args()
    if args.estimate:
        report = estimate(
            args.manifest,
            audition_characters=args.audition_characters,
            audition_seconds=args.audition_seconds,
        )
        for chapter_id, characters in report["chapters"].items():
            print(f"{chapter_id:40s} {characters:6d} characters")
        print(f"{'total billable characters':40s} {report['total_characters']:6d}")
        if "projected_seconds_with_gaps" in report:
            seconds = report["projected_seconds_with_gaps"]
            print(f"projected duration from measured audition: {seconds:.1f}s ({int(seconds // 60)}:{seconds % 60:04.1f})")
        return
    if not args.chapter:
        parser.error("--chapter is required unless --estimate is given")
    output = generate(args.manifest, args.chapter, sample=args.sample, force=args.force, voice_id=args.voice)
    print(output)
    if not args.sample:
        cost = load_manifest(args.manifest).chapters
        chapter = next(item for item in cost if item.id == args.chapter)
        billed = chapter.generation_metadata.get("character_cost")
        if billed:
            print(f"billed characters: {billed}")


if __name__ == "__main__":
    main()
