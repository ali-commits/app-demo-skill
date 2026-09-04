import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.manifest import ProductionManifest, load_manifest, save_manifest


FIXTURE = Path(__file__).parent / "fixtures" / "manifest.json"


def fixture_data() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_manifest_round_trip(tmp_path: Path):
    manifest = load_manifest(FIXTURE)
    destination = tmp_path / "nested" / "manifest.json"
    save_manifest(destination, manifest)
    restored = load_manifest(destination)
    assert [chapter.id for chapter in restored.chapters] == ["01-intro", "02-signup"]
    assert restored.locale == "id-ID"


def test_duplicate_chapter_ids_are_rejected():
    raw = fixture_data()
    raw["chapters"][1]["id"] = raw["chapters"][0]["id"]
    with pytest.raises(ValidationError, match="chapter IDs"):
        ProductionManifest.model_validate(raw)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda raw: raw["chapters"][0].update(narration=""), "narration"),
        (lambda raw: raw["chapters"][0].update(audio_path=""), "audio_path"),
        (
            lambda raw: raw["chapters"][0].update(
                cues=[
                    {"id": "later", "at_seconds": 1.0, "action": "Later"},
                    {"id": "earlier", "at_seconds": 0.5, "action": "Earlier"},
                ]
            ),
            "cue times",
        ),
    ],
)
def test_invalid_chapter_data_is_rejected(mutation, message):
    raw = fixture_data()
    mutation(raw)
    with pytest.raises(ValidationError, match=message):
        ProductionManifest.model_validate(raw)


def test_provider_settings_cannot_contain_credentials():
    raw = fixture_data()
    raw["voice"]["settings"] = {"api_key": "secret"}
    with pytest.raises(ValidationError, match="credential"):
        ProductionManifest.model_validate(raw)
