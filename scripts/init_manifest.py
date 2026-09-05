"""Bootstrap a production manifest from an approved narration markdown file.

The narration document uses one `## <chapter-id>` heading per chapter with the speech
text beneath it. Everything before the first heading (title, voice direction, revision
notes) is documentation, not narration, and is ignored.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from .manifest import Chapter, ProductionManifest, VoiceConfig, save_manifest

CHAPTER_HEADING = re.compile(r"^## +([a-z0-9]+(?:-[a-z0-9]+)*)\s*$", re.M)


def parse_chapters(markdown: str) -> list[tuple[str, str]]:
    matches = list(CHAPTER_HEADING.finditer(markdown))
    chapters: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        body = markdown[match.end():end]
        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", body)
            if paragraph.strip() and paragraph.strip() != "---"
        ]
        if paragraphs:
            chapters.append((match.group(1), "\n\n".join(paragraphs)))
    return chapters


def init_manifest(
    source: Path,
    destination: Path,
    *,
    title: str,
    locale: str,
    provider: str,
    model: str,
    voice_id: str,
    language: str,
    audio_dir: str = "chapters",
    extension: str = ".mp3",
) -> ProductionManifest:
    chapters = parse_chapters(source.read_text(encoding="utf-8"))
    if not chapters:
        raise ValueError(f"{source} has no '## <chapter-id>' headings")
    manifest = ProductionManifest(
        title=title,
        locale=locale,
        voice=VoiceConfig(provider=provider, model=model, voice_id=voice_id, language=language),
        chapters=[
            Chapter(id=chapter_id, narration=narration, audio_path=f"{audio_dir}/{chapter_id}{extension}")
            for chapter_id, narration in chapters
        ],
        master_audio_path=f"master{extension}",
    )
    save_manifest(destination, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a production manifest from narration markdown")
    parser.add_argument("narration", type=Path)
    parser.add_argument("--output", type=Path, default=Path("production.json"))
    parser.add_argument("--title", required=True)
    parser.add_argument("--locale", required=True, help="BCP 47 tag, e.g. ar-SA")
    parser.add_argument("--provider", choices=["elevenlabs", "gemini", "supplied"], required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--voice-id", required=True)
    parser.add_argument("--language", required=True, help="provider language code, e.g. ar")
    args = parser.parse_args()
    manifest = init_manifest(
        args.narration, args.output,
        title=args.title, locale=args.locale, provider=args.provider,
        model=args.model, voice_id=args.voice_id, language=args.language,
    )
    total = sum(len(chapter.narration) for chapter in manifest.chapters)
    for chapter in manifest.chapters:
        print(f"{chapter.id:40s} {len(chapter.narration):5d} characters")
    print(f"{'total':40s} {total:5d} characters -> {args.output}")


if __name__ == "__main__":
    main()
