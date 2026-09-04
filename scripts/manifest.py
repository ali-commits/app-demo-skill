from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SECRET_PARTS = ("api_key", "apikey", "authorization", "credential", "secret", "token")


class VoiceConfig(BaseModel):
    provider: Literal["elevenlabs", "gemini", "supplied"]
    model: str = Field(min_length=1)
    voice_id: str = Field(min_length=1)
    language: str = Field(min_length=1)
    settings: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @field_validator("settings")
    @classmethod
    def settings_are_credential_free(cls, value: dict[str, Any]) -> dict[str, Any]:
        unsafe = [key for key in value if any(part in key.lower() for part in SECRET_PARTS)]
        if unsafe:
            raise ValueError("provider settings must not contain credentials")
        return value


class Cue(BaseModel):
    id: str
    at_seconds: float = Field(ge=0)
    action: str = Field(min_length=1)

    @field_validator("id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        if not ID_PATTERN.fullmatch(value):
            raise ValueError("cue id must use lowercase kebab-case")
        return value


class Chapter(BaseModel):
    id: str
    narration: str = Field(min_length=1)
    audio_path: str = Field(min_length=1)
    duration_seconds: float | None = Field(default=None, ge=0)
    transcript: str | None = None
    narration_sha256: str | None = None
    generation_metadata: dict[str, str] = Field(default_factory=dict)
    cues: list[Cue] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        if not ID_PATTERN.fullmatch(value):
            raise ValueError("chapter id must use lowercase kebab-case")
        return value

    @model_validator(mode="after")
    def ordered_cues(self) -> "Chapter":
        times = [cue.at_seconds for cue in self.cues]
        if times != sorted(times) or len(times) != len(set(times)):
            raise ValueError("cue times must be strictly increasing")
        if self.duration_seconds is not None and any(
            cue.at_seconds > self.duration_seconds for cue in self.cues
        ):
            raise ValueError("cue times must not exceed chapter duration")
        return self


class ProductionManifest(BaseModel):
    title: str = Field(min_length=1)
    locale: str = Field(min_length=1)
    voice: VoiceConfig
    chapters: list[Chapter] = Field(min_length=1)
    master_audio_path: str = Field(min_length=1)
    chapter_gap_seconds: float = Field(default=0.45, ge=0, le=5)

    @model_validator(mode="after")
    def unique_chapter_ids(self) -> "ProductionManifest":
        ids = [chapter.id for chapter in self.chapters]
        if len(ids) != len(set(ids)):
            raise ValueError("chapter IDs must be unique")
        return self


def load_manifest(path: str | Path) -> ProductionManifest:
    return ProductionManifest.model_validate_json(Path(path).read_text(encoding="utf-8"))


def save_manifest(path: str | Path, manifest: ProductionManifest) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = manifest.model_dump_json(indent=2) + "\n"
    descriptor, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
