import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.derive_cues import derive_cues
from scripts.manifest import Cue, load_manifest


def write_production(tmp_path: Path, narration: str, cues: list[dict], spoken: list[tuple[str, float]]) -> Path:
    (tmp_path / "chapters").mkdir()
    audio = tmp_path / "chapters" / "01-intro.mp3"
    audio.write_bytes(b"audio")
    words = [{"start": at, "end": at + 0.3, "word": f" {word}"} for word, at in spoken]
    Path(f"{audio}.transcript.json").write_text(json.dumps({
        "chapter_id": "01-intro", "language": "ar", "coverage": 1.0,
        "transcript": " ".join(word for word, _ in spoken),
        "segments": [{"start": 0, "end": words[-1]["end"], "text": "", "words": words}],
    }, ensure_ascii=False), encoding="utf-8")
    manifest = tmp_path / "production.json"
    manifest.write_text(json.dumps({
        "title": "Fixture", "locale": "ar-SA",
        "voice": {"provider": "supplied", "model": "supplied", "voice_id": "n", "language": "ar"},
        "chapters": [{"id": "01-intro", "narration": narration, "audio_path": "chapters/01-intro.mp3", "cues": cues}],
        "master_audio_path": "master.mp3",
    }, ensure_ascii=False), encoding="utf-8")
    return manifest


def test_cue_accepts_an_anchor_phrase_without_a_time():
    cue = Cue(id="school-name", anchor="في حقل الاسم الرسمي", action="Type the name")
    assert cue.at_seconds is None


def test_cue_requires_either_anchor_or_time():
    with pytest.raises(ValidationError, match="anchor"):
        Cue(id="school-name", action="Type the name")


def test_anchor_resolves_to_the_measured_start_of_its_first_word(tmp_path: Path):
    manifest = write_production(
        tmp_path,
        narration="مرحبًا بك. في حقل الاسم الرسمي اكتب الاسم.",
        cues=[{"id": "school-name", "anchor": "في حقل الاسم الرسمي", "action": "Type the name"}],
        spoken=[("مرحبا", 0.0), ("بك", 0.5), ("في", 1.2), ("حقل", 1.5), ("الاسم", 1.8), ("الرسمي", 2.1), ("اكتب", 2.6), ("الاسم", 2.9)],
    )
    derive_cues(manifest)
    chapter = load_manifest(manifest).chapters[0]
    assert chapter.cues[0].at_seconds == pytest.approx(1.2)


def test_anchor_survives_an_asr_slip_inside_the_phrase(tmp_path: Path):
    # Whisper heard «البكالوريوز» for «البكالوريوس»; alignment must still place the cue.
    manifest = write_production(
        tmp_path,
        narration="ونختار البكالوريوس في رياض الأطفال من الجامعة.",
        cues=[{"id": "qualification", "anchor": "ونختار البكالوريوس في رياض", "action": "Pick the degree"}],
        spoken=[("ونختار", 0.0), ("البكالوريوز", 0.4), ("في", 0.9), ("رياض", 1.1), ("الاطفال", 1.4), ("من", 1.8), ("الجامعة", 2.0)],
    )
    derive_cues(manifest)
    assert load_manifest(manifest).chapters[0].cues[0].at_seconds == pytest.approx(0.0)


def test_anchor_absent_from_the_approved_narration_is_an_error(tmp_path: Path):
    manifest = write_production(
        tmp_path,
        narration="مرحبًا بك.",
        cues=[{"id": "x", "anchor": "هذه العبارة غير موجودة", "action": "X"}],
        spoken=[("مرحبا", 0.0), ("بك", 0.5)],
    )
    with pytest.raises(ValueError, match="approved narration"):
        derive_cues(manifest)


def test_assembly_refuses_unresolved_anchors(tmp_path: Path):
    from scripts.assemble_audio import assemble

    manifest = write_production(
        tmp_path,
        narration="مرحبًا بك.",
        cues=[{"id": "open", "anchor": "مرحبًا", "action": "Open"}],
        spoken=[("مرحبا", 0.0)],
    )
    with pytest.raises(ValueError, match="derive_cues"):
        assemble(manifest)


def test_explicit_times_are_left_alone_and_order_is_enforced(tmp_path: Path):
    manifest = write_production(
        tmp_path,
        narration="أولًا افتح الصفحة. ثانيًا اضغط الزر.",
        cues=[
            {"id": "open", "at_seconds": 0.05, "action": "Open"},
            {"id": "press", "anchor": "ثانيًا اضغط", "action": "Press"},
        ],
        spoken=[("اولا", 0.0), ("افتح", 0.3), ("الصفحة", 0.6), ("ثانيا", 1.2), ("اضغط", 1.5), ("الزر", 1.8)],
    )
    derive_cues(manifest)
    cues = load_manifest(manifest).chapters[0].cues
    assert [cue.at_seconds for cue in cues] == [pytest.approx(0.05), pytest.approx(1.2)]
