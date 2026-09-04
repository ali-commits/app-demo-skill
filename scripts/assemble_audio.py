from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from .manifest import load_manifest, save_manifest
from .validate_audio import probe_audio, validate_audio


def assemble(manifest_path: Path) -> tuple[Path, Path]:
    manifest = load_manifest(manifest_path)
    root = manifest_path.resolve().parent
    sources = [root / chapter.audio_path for chapter in manifest.chapters]
    infos = [validate_audio(source) for source in sources]
    inputs: list[str] = []
    filters: list[str] = []
    labels: list[str] = []
    for index, source in enumerate(sources):
        inputs.extend(["-i", str(source)])
        label = f"chapter{index}"
        filters.append(
            f"[{index}:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,aformat=sample_fmts=s16:channel_layouts=mono[{label}]"
        )
        labels.append(f"[{label}]")
        if index < len(sources) - 1:
            gap = f"gap{index}"
            filters.append(f"anullsrc=r=48000:cl=mono:d={manifest.chapter_gap_seconds}[{gap}]")
            labels.append(f"[{gap}]")
    filters.append(f"{''.join(labels)}concat=n={len(labels)}:v=0:a=1[out]")
    output = root / manifest.master_audio_path
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", *inputs,
        "-filter_complex", ";".join(filters), "-map", "[out]", str(output),
    ], check=True)
    offset = 0.0
    chapters = []
    for chapter, info in zip(manifest.chapters, infos, strict=True):
        chapter.duration_seconds = info.duration_seconds
        chapters.append({
            "id": chapter.id,
            "offset_seconds": round(offset, 6),
            "duration_seconds": info.duration_seconds,
            "cues": [
                {**cue.model_dump(), "master_at_seconds": round(offset + cue.at_seconds, 6)}
                for cue in chapter.cues
            ],
        })
        offset += info.duration_seconds + manifest.chapter_gap_seconds
    save_manifest(manifest_path, manifest)
    timing = output.with_suffix(output.suffix + ".timing.json")
    timing.write_text(json.dumps({
        "master_audio": str(output),
        "duration_seconds": probe_audio(output).duration_seconds,
        "chapters": chapters,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output, timing


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize and assemble narration chapters")
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    output, timing = assemble(args.manifest)
    print(output)
    print(timing)


if __name__ == "__main__":
    main()
