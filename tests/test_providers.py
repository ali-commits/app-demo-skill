import json
import wave
from io import BytesIO

import httpx
import pytest

from scripts.generate_audio import generate
from scripts.manifest import VoiceConfig
from scripts.providers import ElevenLabsProvider, GeminiProvider, MissingCredentialError


def voice(provider: str, **settings) -> VoiceConfig:
    return VoiceConfig(
        provider=provider,
        model="model-1",
        voice_id="voice-1",
        language="id",
        settings=settings,
    )


def test_elevenlabs_requires_its_environment_key(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    with pytest.raises(MissingCredentialError, match="ELEVENLABS_API_KEY"):
        ElevenLabsProvider()


def test_elevenlabs_sends_context_and_returns_safe_metadata(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "do-not-leak")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["xi-api-key"] == "do-not-leak"
        body = json.loads(request.content)
        assert body["previous_text"] == "Before"
        assert body["next_text"] == "After"
        assert body["language_code"] == "id"
        return httpx.Response(
            200,
            content=b"mp3-bytes",
            headers={"request-id": "req-1", "character-cost": "42"},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = ElevenLabsProvider(client=client).generate(
        "Narration", voice("elevenlabs", stability=0.5), previous_text="Before", next_text="After"
    )
    assert result.content == b"mp3-bytes"
    assert result.extension == ".mp3"
    assert result.metadata == {"request_id": "req-1", "character_cost": "42"}
    assert "do-not-leak" not in repr(result)


def test_gemini_requires_its_environment_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(MissingCredentialError, match="GEMINI_API_KEY"):
        GeminiProvider()


def test_gemini_wraps_pcm_as_mono_24khz_wav(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-secret")

    class Result:
        output_audio = b"\x00\x00" * 24

    class Interactions:
        def create(self, **kwargs):
            assert kwargs["model"] == "model-1"
            assert kwargs["generation_config"]["speech_config"][0]["voice"] == "voice-1"
            return Result()

    class Client:
        interactions = Interactions()

    result = GeminiProvider(client=Client()).generate("Halo", voice("gemini"))
    with wave.open(BytesIO(result.content), "rb") as audio:
        assert audio.getnchannels() == 1
        assert audio.getframerate() == 24_000
        assert audio.getsampwidth() == 2
    assert result.extension == ".wav"


def two_chapter_manifest(tmp_path):
    manifest = tmp_path / "production.json"
    manifest.write_text(json.dumps({
        "title": "Fixture", "locale": "ar-SA",
        "voice": {"provider": "elevenlabs", "model": "model-1", "voice_id": "voice-1", "language": "ar"},
        "chapters": [
            {"id": "01-intro", "narration": "مرحبًا بك", "audio_path": "audio/intro.mp3"},
            {"id": "02-form", "narration": "اكتب الاسم الرسمي", "audio_path": "audio/form.mp3"},
        ],
        "master_audio_path": "audio/master.mp3"
    }, ensure_ascii=False), encoding="utf-8")
    return manifest


def test_regeneration_invalidates_derived_timing(monkeypatch, tmp_path):
    from scripts.manifest import load_manifest, save_manifest, Cue
    from scripts.providers import GeneratedAudio
    from types import SimpleNamespace

    path = two_chapter_manifest(tmp_path)
    manifest = load_manifest(path)
    chapter = manifest.chapters[0]
    chapter.duration_seconds = 10
    chapter.transcript = "old transcript"
    chapter.cues = [Cue(id="open", anchor="مرحبًا", at_seconds=1, action="Open")]
    save_manifest(path, manifest)
    monkeypatch.setattr("scripts.generate_audio.provider_for", lambda _: SimpleNamespace(generate=lambda *args, **kwargs: GeneratedAudio(b"new audio", ".mp3", {})))
    generate(path, chapter.id, sample=False, force=True)
    updated = load_manifest(path).chapters[0]
    assert updated.duration_seconds is None
    assert updated.transcript is None
    assert updated.cues[0].at_seconds is None


def test_estimate_reports_billable_characters_without_calling_the_provider(monkeypatch, tmp_path):
    from scripts.generate_audio import estimate

    def forbidden(_voice):
        raise AssertionError("estimating must not create a provider")

    monkeypatch.setattr("scripts.generate_audio.provider_for", forbidden)
    report = estimate(two_chapter_manifest(tmp_path))
    assert report["chapters"] == {"01-intro": 9, "02-form": 17}
    assert report["total_characters"] == 26


def test_estimate_projects_duration_from_a_measured_audition(monkeypatch, tmp_path):
    from scripts.generate_audio import estimate

    # A 9-character audition that measured 1.5 s implies 6 chars/s for the whole script.
    report = estimate(two_chapter_manifest(tmp_path), audition_characters=9, audition_seconds=1.5)
    assert report["projected_seconds"] == pytest.approx(26 / 6, abs=0.01)


def test_sample_can_audition_a_different_voice_without_editing_the_manifest(monkeypatch, tmp_path):
    from scripts import generate_audio

    seen = {}

    class Provider:
        def generate(self, text, voice, *, previous_text="", next_text=""):
            seen["voice_id"] = voice.voice_id
            return generate_audio.GeneratedAudio(b"mp3", ".mp3", {})

    monkeypatch.setattr("scripts.generate_audio.provider_for", lambda _voice: Provider())
    manifest = two_chapter_manifest(tmp_path)
    output = generate_audio.generate(manifest, "01-intro", sample=True, force=False, voice_id="other-voice")
    assert seen["voice_id"] == "other-voice"
    assert output.name == "01-intro-other-voice.mp3"
    # The manifest's own voice must not be touched by an audition.
    assert json.loads(manifest.read_text())["voice"]["voice_id"] == "voice-1"


def test_generation_refuses_existing_output_before_calling_provider(monkeypatch, tmp_path):
    manifest = tmp_path / "production.json"
    manifest.write_text(json.dumps({
        "title": "Fixture", "locale": "id-ID",
        "voice": {"provider": "elevenlabs", "model": "model-1", "voice_id": "voice-1", "language": "id"},
        "chapters": [{"id": "01-intro", "narration": "Halo", "audio_path": "audio/intro.mp3"}],
        "master_audio_path": "audio/master.mp3"
    }), encoding="utf-8")
    output = tmp_path / "audio" / "intro.mp3"
    output.parent.mkdir()
    output.write_bytes(b"existing")

    def forbidden(_voice):
        raise AssertionError("provider must not be created when output exists")

    monkeypatch.setattr("scripts.generate_audio.provider_for", forbidden)
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        generate(manifest, "01-intro", sample=False, force=False)
