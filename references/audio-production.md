# Audio Production

Read this only after narration approval or when validating supplied audio.

## Choose the source

Ask whether the user supplies final audio or wants generated speech. Supplied audio skips provider audition but still requires validation, transcription, language detection, and coverage checks.

For generated speech, support provider adapters rather than embedding provider logic in the workflow. The included implementation supports ElevenLabs and Gemini. Consult current official documentation before changing adapters:

- ElevenLabs: <https://elevenlabs.io/docs/api-reference/text-to-speech/convert>
- Gemini: <https://ai.google.dev/gemini-api/docs/speech-generation>

## Build the manifest from the approved narration

```bash
python -m scripts.init_manifest narration.md --output production.json \
  --title "…" --locale ar-SA --provider elevenlabs \
  --model eleven_multilingual_v2 --voice-id <id> --language ar
```

One `## <chapter-id>` heading per chapter; everything before the first heading is documentation and is ignored. The command prints characters per chapter and the total.

## Credentials and cost

Look for the selected provider's documented environment variable. If absent, ask the user to configure it; do not ask them to paste it into source files. Never echo, log, save, or commit a credential.

Before full generation, run `python -m scripts.generate_audio --manifest production.json --estimate` and report the billable characters. Provider keys are often scoped to text-to-speech only, so quota and price may not be readable; report characters and, where the plan is known, the approximate cost.

## Voice audition

Generate two or three short samples using one representative passage. Change only the factor being compared. Audition alternative voices with `--sample --voice <id>` so the manifest's approved voice is never edited by an audition:

```bash
python -m scripts.generate_audio --manifest production.json --chapter 01-introduction --sample
python -m scripts.generate_audio --manifest production.json --chapter 01-introduction --sample --voice <other-id>
```

Label samples with safe provider, model, voice, language, and settings metadata. After selection, lock these values in the manifest.

## Project the duration before spending credits

An audition is also a measurement. Validate it, then project the whole script from its measured rate:

```bash
python -m scripts.generate_audio --manifest production.json --estimate \
  --audition-characters 224 --audition-seconds 20.5
```

If the projection overruns the approved ceiling, trim the narration **now** — a script that reads well at 5:40 on paper has run 6:30 in delivery. Re-approve any trimmed lines. This projection exists only to size the script; it is never used to time browser cues.

Expect the full delivery to run somewhat faster than the opening chapter suggests; introductions are typically the slowest passage.

## Chapter production

Generate one file per approved semantic chapter. Pass adjacent text as continuity context where the provider supports it. Keep narration text unchanged; use provider direction controls only for pace, tone, accent, and performance.

After every generation:

1. Probe the audio stream and duration.
2. Detect excessive leading or trailing silence.
3. Transcribe with word timestamps (`--model small` is fast and, with the diacritic-insensitive coverage check, accurate enough for anchoring; `medium` and larger are many times slower than real time on CPU — pass `--device cuda` if a GPU is available).
4. Confirm detected language.
5. Compare spoken coverage with approved narration. A coverage shortfall is **evidence, not a verdict**: the transcript is always written, with `missing_words`, so read it and decide whether the words are absent from the audio or merely misheard (e.g. «البكالوريوز» for «البكالوريوس»). Regenerate only for genuinely missing speech.
6. Regenerate only the defective chapter after approval if credits will be consumed.

Never infer final timings from character count or estimated reading speed.

## Resolve cues from the audio

Every action cue in the manifest carries an `anchor`: the phrase from the approved narration that introduces it. After transcription:

```bash
python -m scripts.derive_cues --manifest production.json
```

Use an anchor phrase that occurs exactly once in its chapter. Each anchor is aligned to the transcript's word stream and assigned a measured timestamp. ASR mistakes may require a neighboring word as a fallback; review every warning against the audio. Ambiguous phrases, distant alignments, and non-increasing cue times are rejected instead of silently adjusted.

Every run recomputes anchored cues, including previously resolved ones. Transcripts include the source audio's SHA-256 fingerprint; missing or mismatched fingerprints require re-transcription. After replacing audio, transcribe, derive cues, and assemble again. Older transcripts must be regenerated once to include this fingerprint.

## Mastering

Normalize chapters to consistent loudness, trim only excessive boundary silence, retain natural breathing, insert the approved inter-chapter gap, and concatenate into one master audio file. `assemble_audio` refuses to run while any anchored cue is unresolved, and emits cumulative chapter and cue offsets (`master_at_seconds`) that the recorder consumes. Keep the chapter sources so later corrections do not require regenerating the entire narration.
