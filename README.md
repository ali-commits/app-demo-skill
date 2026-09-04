# App Demo Skill

An Agentic AI skill compatible with Codex and Claude Code for producing polished, narrated application demos and tutorials. It guides the complete workflow from discovery and specification through narration, voice generation, browser automation, recording, synchronization, and final quality checks.

## Features

- Structured discovery for audience, language, duration, format, and demo goals
- Reviewable specifications, narration scripts, and synchronized storyboards
- ElevenLabs and Gemini text-to-speech integrations
- Voice-sample generation before committing credits to a full narration
- Single-file and segmented audio production workflows
- Playwright-based browser recording with visible cursor movement
- Audio validation, assembly, transcription, and recording inspection tools
- Multilingual and right-to-left workflow guidance
- Credential-free automated tests and reusable fixtures

## How the workflow works

1. Clarify the purpose, audience, language, target duration, and application state.
2. Write and approve a concise demo specification.
3. Draft, review, and approve the narration transcript.
4. Rehearse the application flow and create a timed storyboard.
5. Use supplied audio or generate voice samples and the approved narration.
6. Automate and record the browser interaction against the final application state.
7. Align narration and visuals, then inspect the finished recording for timing and UI issues.

The skill deliberately uses review checkpoints before paid audio generation and final recording.

## Requirements

- Codex or Claude Code with local skill support
- Python 3.11 or newer
- FFmpeg and `ffprobe`
- Bun
- Playwright Chromium
- An ElevenLabs or Gemini API key only when generating audio with that provider

## Installation

```bash
git clone git@github.com:ali-commits/app-demo-skill.git ~/projects/app-demo-skill

mkdir -p ~/.codex/skills ~/.claude/skills
ln -s ~/projects/app-demo-skill ~/.codex/skills/narrated-app-demo
ln -s ~/projects/app-demo-skill ~/.claude/skills/narrated-app-demo

python -m pip install -r ~/projects/app-demo-skill/requirements.txt

cd ~/projects/app-demo-skill/assets/playwright-demo-template
bun install
bunx playwright install chromium
```

Install only the symlink for the agent you use, or install both to share one checkout between Codex and Claude Code. Restart the agent after installation if the skill does not appear immediately.

## Provider credentials

Set the environment variable for the provider you intend to use:

```bash
export ELEVENLABS_API_KEY="your-key"
export GEMINI_API_KEY="your-key"
```

Never commit API keys, generated secrets, or populated `.env` files. Provider calls can consume paid credits. The repository test suite does not make live provider calls.

## Production manifest

Audio production is driven by a JSON manifest. It records the provider, voice, model, language, output settings, and either a complete script or a list of timed segments. See the schemas and examples in [`references/audio-production.md`](references/audio-production.md).

The production commands load and validate the manifest before doing work. Start with sample generation so provider settings can be reviewed before producing full chapters.

## Audio commands

Run these commands from the repository root:

```bash
python -m scripts.generate_audio --manifest production.json --chapter 01-introduction --sample
python -m scripts.generate_audio --manifest production.json --chapter 01-introduction
python -m scripts.validate_audio chapters/01-introduction.mp3
python -m scripts.transcribe_audio --manifest production.json --chapter 01-introduction
python -m scripts.assemble_audio --manifest production.json
```

Use `--help` with any command for its complete options. The references explain sample generation, segmented narration, retry behavior, validation, and alignment tradeoffs.

## Browser recording

The template in [`assets/playwright-demo-template`](assets/playwright-demo-template) provides a visible mouse cursor, deterministic actions, timing controls, recording, and muxing hooks. Copy the template into a demo workspace, configure its manifest and scenario, then rehearse before recording.

```bash
cd assets/playwright-demo-template
bun run rehearse.ts
bun run record.ts
```

See [`references/browser-recording.md`](references/browser-recording.md) for application readiness, viewport selection, cursor behavior, and production guidance.

## Verification

Inspect the rendered result rather than relying only on command success:

```bash
python -m scripts.inspect_recording path/to/demo.mp4 \
  --timing path/to/master.mp3.timing.json \
  --output artifacts/demo-review
```

The inspection workflow checks duration, stream metadata, frame samples, and audiovisual alignment. The full verification checklist is in [`references/verification.md`](references/verification.md).

## Development

Install the dependencies, then run both test suites:

```bash
python -m pytest tests

cd assets/playwright-demo-template
bun test
```

The tests use local fixtures and mocked providers. They do not require credentials or invoke paid APIs.

## Security

- Keep provider credentials in environment variables or a secret manager.
- Use test accounts and non-sensitive data in recordings.
- Review browser tabs, notifications, autofill, and desktop content before capture.
- Inspect generated artifacts before sharing them externally.

## License

Licensed under the [MIT License](LICENSE).
