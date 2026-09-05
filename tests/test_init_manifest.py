import json
from pathlib import Path

from scripts.init_manifest import init_manifest
from scripts.manifest import load_manifest

NARRATION = """# Narration

Voice direction: calm.

---

## 01-introduction

مرحبًا بك في رافد.

نبدأ من صفحة التسجيل.

---

## 02-institution

في حقل الاسم الرسمي، اكتب الاسم.
"""


def test_markdown_chapters_become_manifest_chapters(tmp_path: Path):
    source = tmp_path / "narration.md"
    source.write_text(NARRATION, encoding="utf-8")
    destination = tmp_path / "production.json"

    init_manifest(source, destination, title="Rafid demo", locale="ar-SA", provider="elevenlabs", model="eleven_multilingual_v2", voice_id="v1", language="ar")

    manifest = load_manifest(destination)
    assert [chapter.id for chapter in manifest.chapters] == ["01-introduction", "02-institution"]
    assert manifest.chapters[0].narration == "مرحبًا بك في رافد.\n\nنبدأ من صفحة التسجيل."
    assert manifest.chapters[1].audio_path == "chapters/02-institution.mp3"
    assert manifest.voice.voice_id == "v1"
    assert json.loads(destination.read_text(encoding="utf-8"))["title"] == "Rafid demo"


def test_preamble_before_the_first_chapter_is_not_narration(tmp_path: Path):
    source = tmp_path / "narration.md"
    source.write_text(NARRATION, encoding="utf-8")
    init_manifest(source, tmp_path / "production.json", title="T", locale="ar-SA", provider="supplied", model="supplied", voice_id="v", language="ar")
    manifest = load_manifest(tmp_path / "production.json")
    assert all("Voice direction" not in chapter.narration for chapter in manifest.chapters)
