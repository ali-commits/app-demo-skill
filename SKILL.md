---
name: narrated-app-demo
description: Create or repair narrated application demos and tutorials, including discovery, specification, localized narration, optional TTS, timestamped browser automation, recording, and verification. Do not use for ordinary E2E testing or standalone audio/video editing.
---

# Narrated App Demo

Produce a verified demo through explicit approval gates:

1. Inspect the in-scope application and read [discovery-and-spec.md](references/discovery-and-spec.md).
2. Ask one material question at a time, then obtain approval for a written demo specification.
3. Read [narration-and-storyboarding.md](references/narration-and-storyboarding.md), write the storyboard and chaptered narration, and obtain approval.
4. Ask whether audio is supplied or should be generated. Before paid generation, read [audio-production.md](references/audio-production.md), estimate cost where possible, audition two or three comparable samples, and obtain approval.
5. Validate and transcribe the actual audio. Never derive final cues from estimated reading speed.
6. Read [browser-recording.md](references/browser-recording.md), adapt the Playwright template, and pass its compressed rehearsal before recording.
7. Read [verification.md](references/verification.md), inspect the real-time output, and report every limitation.

Never store or commit provider credentials. Never call an incomplete recording complete. Preserve stable chapter identifiers across scripts, audio, timestamps, and browser cues.

## Included tools

Run scripts from the skill root as modules. Use `python -m scripts.<name> --help` for their exact options.

- `generate_audio.py`: generate an audition or one approved narration chapter.
- `validate_audio.py`: inspect media structure and boundary silence.
- `transcribe_audio.py`: create word-level timestamps and verify narration coverage.
- `assemble_audio.py`: normalize and concatenate approved chapters.
- `inspect_recording.py`: verify the final recording and extract transition frames.

Copy `assets/playwright-demo-template/` into the target project and adapt only its scenario and localized data. Keep the shared cursor, scheduler, recorder, and media checks intact unless the application requires a documented change.
