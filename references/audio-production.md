# Audio Production

Read this only after narration approval or when validating supplied audio.

## Choose the source

Ask whether the user supplies final audio or wants generated speech. Supplied audio skips provider audition but still requires validation, transcription, language detection, and coverage checks.

For generated speech, support provider adapters rather than embedding provider logic in the workflow. The included implementation supports ElevenLabs and Gemini. Consult current official documentation before changing adapters:

- ElevenLabs: <https://elevenlabs.io/docs/api-reference/text-to-speech/convert>
- Gemini: <https://ai.google.dev/gemini-api/docs/speech-generation>

## Credentials and cost

Look for the selected provider's documented environment variable. If absent, ask the user to configure it; do not ask them to paste it into source files. Never echo, log, save, or commit a credential. Before full generation, report the estimated billable characters or provider cost when available.

## Voice audition

Generate two or three short samples using one representative passage. Change only the factor being compared: voice, dialect, or delivery. Label samples with safe provider, model, voice, language, and settings metadata. After selection, lock these values in the manifest.

## Chapter production

Generate one file per approved semantic chapter. Pass adjacent text as continuity context where the provider supports it. Keep narration text unchanged; use provider direction controls only for pace, tone, accent, and performance.

After every generation:

1. Probe the audio stream and duration.
2. Detect excessive leading or trailing silence.
3. Transcribe with word timestamps.
4. Confirm detected language.
5. Compare spoken coverage with approved narration.
6. Regenerate only the defective chapter after approval if credits will be consumed.

Never infer final timings from character count or estimated reading speed.

## Mastering

Normalize chapters to consistent loudness, trim only excessive boundary silence, retain natural breathing, insert the approved inter-chapter gap, and concatenate into one master audio file. Emit cumulative chapter and cue offsets. Keep the chapter sources so later corrections do not require regenerating the entire narration.
