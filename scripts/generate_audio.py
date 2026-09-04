from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from .manifest import load_manifest, save_manifest
from .providers import provider_for


def generate(manifest_path: Path, chapter_id: str, *, sample: bool, force: bool) -> Path:
    manifest = load_manifest(manifest_path)
    try:
        index = next(i for i, item in enumerate(manifest.chapters) if item.id == chapter_id)
    except StopIteration as error:
        raise ValueError(f"Unknown chapter: {chapter_id}") from error
    chapter = manifest.chapters[index]
    root = manifest_path.resolve().parent
    output = (
        root / "auditions" / f"{chapter.id}-{manifest.voice.voice_id}"
        if sample
        else root / chapter.audio_path
    )
    existing = list(output.parent.glob(f"{output.name}.*")) if sample else [output] if output.exists() else []
    if existing and not force:
        raise FileExistsError(f"Refusing to overwrite {existing[0]}; pass --force to regenerate")
    provider = provider_for(manifest.voice)
    previous_text = manifest.chapters[index - 1].narration if index else ""
    next_text = manifest.chapters[index + 1].narration if index + 1 < len(manifest.chapters) else ""
    generated = provider.generate(
        chapter.narration,
        manifest.voice,
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
    parser.add_argument("--chapter", required=True)
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    print(generate(args.manifest, args.chapter, sample=args.sample, force=args.force))


if __name__ == "__main__":
    main()
