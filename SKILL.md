---
name: narrated-app-demo
description: Create, repair, or quality-review narrated application demos and tutorials. Use this skill whenever a user asks for a product walkthrough, screen tutorial, demo video, narrated onboarding, localized voice-over, ElevenLabs or Gemini speech generation, Playwright recording, visible mouse automation, or synchronization of narration with browser actions. Covers discovery, specification, scripts, storyboards, optional TTS, timestamped recording, and verification; ordinary E2E tests and unrelated media edits remain outside its scope.
license: MIT
metadata:
  version: "1.2.0"
  compatibility: "Codex and Claude Code; requires filesystem and command execution, Python 3.11+, Bun, Playwright Chromium, and FFmpeg/ffprobe"
---

# Narrated App Demo

Produce a verified demo through explicit approval gates:

1. Inspect the in-scope application and read [discovery-and-spec.md](references/discovery-and-spec.md).
2. Ask one material question at a time, then obtain approval for a written demo specification.
3. Read [narration-and-storyboarding.md](references/narration-and-storyboarding.md), write the storyboard and chaptered narration with an anchor phrase for every action, and obtain approval.
4. Ask whether audio is supplied or should be generated. Before paid generation, read [audio-production.md](references/audio-production.md): build the manifest with `init_manifest`, report billable characters with `--estimate`, audition two or three comparable voices, **project the total duration from the audition's measured rate and trim the script if it overruns**, then obtain approval.
5. Validate and transcribe the actual audio, then run `derive_cues` so every cue carries the measured start time of its anchor phrase. Never derive final cues from estimated reading speed.
6. Read [browser-recording.md](references/browser-recording.md), adapt the Playwright template or the project's existing harness to the template's contract, and pass its compressed rehearsal before recording.
7. Read [verification.md](references/verification.md), inspect the real-time output, and report every limitation.

Never store or commit provider credentials. Never call an incomplete recording complete. Preserve stable chapter identifiers across scripts, audio, timestamps, and browser cues.

## Runtime requirements

Use this skill in Codex or Claude Code with local filesystem and command execution. The bundled workflow requires Python 3.11 or newer, Bun, Playwright Chromium, and FFmpeg with `ffprobe`. Live speech generation additionally requires the selected provider credential; all planning, supplied-audio, browser, and verification stages remain usable without a TTS credential.

## Included tools

Run scripts from the skill root as modules. Use `python -m scripts.<name> --help` for their exact options.

- `init_manifest.py`: build the production manifest from the approved narration markdown.
- `generate_audio.py`: estimate billable characters, audition a voice (`--sample --voice`), or generate one approved chapter.
- `validate_audio.py`: inspect media structure and boundary silence.
- `transcribe_audio.py`: create word-level timestamps and verify narration coverage (diacritic-insensitive; the transcript is always kept for inspection).
- `derive_cues.py`: resolve every anchored cue to the measured start of its phrase in the audio.
- `assemble_audio.py`: normalize and concatenate approved chapters; refuses unresolved cues.
- `inspect_recording.py`: verify the final recording, flag a blank opening frame, and extract a frame at every chapter boundary and after every cue.

## Recording harness contract

`assets/playwright-demo-template/` is the reference implementation. Copy it into a greenfield project, or — when the project already has a recorder — adapt that recorder to the same contract rather than starting over. Whichever you use, these properties are not optional:

- Language and locale are forced before the first navigation, and `assertLocale` runs on the opening frame and after every route change.
- The opening screen is navigated and settled **before** the narration clock starts; that pre-roll is trimmed at mux time.
- The page is held open ≥2 s after the last cue, and the mux uses `-t <audio duration>`, never `-shortest`.
- Cues come from `resolveCues(manifest)` (measured times), the cursor is visible and non-blocking, and `expectAfter` asserts each cue's `expect_text`.
- Helpers never select `.last()` from a text match; anything that can hold prior-run data is matched by the run's unique identifier.
