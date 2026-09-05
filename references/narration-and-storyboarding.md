# Narration and Storyboarding

Read this after the demo specification is approved.

## Separate artifacts

Create a storyboard and a narration script. The storyboard includes screen state, visible data, cursor action, transition, loading preparation, and approximate duration. The narration contains only words intended for speech.

Give every semantic chapter a stable lowercase kebab-case identifier, normally prefixed by order:

```text
01-introduction
02-school-registration
03-dashboard
04-email
05-closing
```

Use the same IDs in filenames, the production manifest, generated audio, transcripts, cues, browser scenarios, and verification output.

## Writing rules

- Write for listening, not for reading documentation.
- Use natural target-locale wording; do not translate interface text literally.
- Match names, addresses, institutions, date formats, country codes, and writing direction to the locale.
- Describe an action as it begins or after its result is prepared, never while an unrelated loading state is visible.
- Budget time for cursor travel, typing, menus, validation, and route transitions.
- Avoid narrating every obvious click. Explain purpose, decisions, and results.
- Introduce sensitive fields generically unless the values are intentional demo data.

Chapters should be coherent scenes, not individual sentences. Aim for repairable sections of roughly 20–90 seconds unless the workflow naturally requires a different length.

## Anchor every action

For each browser action in the storyboard, name the exact phrase in the narration that introduces it — the words the viewer hears as the cursor moves. These become the `anchor` of each cue in the manifest and are resolved to measured times after the audio exists. Choose phrases that:

- Are unique within the chapter and quoted verbatim from the approved text.
- Begin at the moment the action should start, not at the end of the sentence.
- Describe purpose ("في حقل الاسم الرسمي…") rather than a bare verb that recurs.

Also name the on-screen text that proves the action worked (`expect_text`): the new step's heading, the record's name, the confirmation line.

## Duration discipline

Word counts mislead across languages. Treat pre-audition duration figures as rough, and expect to re-size the script once the first audition has measured the real delivery rate (see audio-production.md). Keep the approved ceiling in view when writing: every field-by-field sentence costs seconds the dense chapters cannot spare.

## Review package

Present:

1. Chapter list with estimated durations.
2. Storyboard table linking narration intent to visible actions.
3. Narration-only text ready for speech generation.
4. Total estimated duration and any timing risks.

Obtain approval for both storyboard and narration before requesting credentials, generating paid audio, or recording.
