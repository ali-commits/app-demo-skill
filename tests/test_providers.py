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
