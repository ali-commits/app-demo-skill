from __future__ import annotations

import base64
import os
import wave
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Protocol

import httpx

from .manifest import VoiceConfig


class MissingCredentialError(RuntimeError):
    """Raised when a selected paid provider has no configured credential."""


@dataclass(frozen=True)
class GeneratedAudio:
    content: bytes
    extension: str
    metadata: dict[str, str]


class SpeechProvider(Protocol):
    def generate(
        self,
        text: str,
        voice: VoiceConfig,
        *,
        previous_text: str = "",
        next_text: str = "",
    ) -> GeneratedAudio: ...


def _required_key(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise MissingCredentialError(f"Set {name} before generating paid audio")
    return value


class ElevenLabsProvider:
    def __init__(self, *, client: httpx.Client | None = None):
        self._api_key = _required_key("ELEVENLABS_API_KEY")
        self._client = client or httpx.Client(timeout=120)

    def generate(
        self,
        text: str,
        voice: VoiceConfig,
        *,
        previous_text: str = "",
        next_text: str = "",
    ) -> GeneratedAudio:
        body: dict[str, Any] = {
            "text": text,
            "model_id": voice.model,
            "language_code": voice.language,
        }
        if previous_text:
            body["previous_text"] = previous_text
        if next_text:
            body["next_text"] = next_text
        if voice.settings:
            body["voice_settings"] = voice.settings
        response = self._client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice.voice_id}",
            params={"output_format": "mp3_44100_128"},
            headers={"xi-api-key": self._api_key, "Content-Type": "application/json"},
            json=body,
        )
        response.raise_for_status()
        metadata = {
            key: value
            for key, value in {
                "request_id": response.headers.get("request-id"),
                "character_cost": response.headers.get("character-cost"),
            }.items()
            if value is not None
        }
        return GeneratedAudio(response.content, ".mp3", metadata)


def _pcm_to_wav(pcm: bytes, *, rate: int = 24_000) -> bytes:
    output = BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(pcm)
    return output.getvalue()


class GeminiProvider:
    def __init__(self, *, client: Any | None = None):
        api_key = _required_key("GEMINI_API_KEY")
        if client is None:
            from google import genai

            client = genai.Client(api_key=api_key)
        self._client = client

    def generate(
        self,
        text: str,
        voice: VoiceConfig,
        *,
        previous_text: str = "",
        next_text: str = "",
    ) -> GeneratedAudio:
        direction = str(voice.settings.get("direction", "Read the text exactly as written."))
        prompt = f"{direction}\n\n{text}"
        result = self._client.interactions.create(
            model=voice.model,
            input=prompt,
            response_format={"type": "audio"},
            generation_config={
                "speech_config": [{"voice": voice.voice_id, "language": voice.language}]
            },
        )
        raw = result.output_audio
        if isinstance(raw, str):
            raw = base64.b64decode(raw)
        elif hasattr(raw, "data"):
            raw = raw.data
            if isinstance(raw, str):
                raw = base64.b64decode(raw)
        if not isinstance(raw, bytes):
            raise RuntimeError("Gemini did not return PCM audio")
        return GeneratedAudio(_pcm_to_wav(raw), ".wav", {})


def provider_for(voice: VoiceConfig) -> SpeechProvider:
    if voice.provider == "elevenlabs":
        return ElevenLabsProvider()
    if voice.provider == "gemini":
        return GeminiProvider()
    raise ValueError("Supplied audio does not use a generation provider")
