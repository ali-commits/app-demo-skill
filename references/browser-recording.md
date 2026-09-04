# Browser Automation and Recording

Read after the master audio and timestamp data pass validation.

## Adapt the template

Copy `assets/playwright-demo-template/` into the target project. Replace the example scenario with project-specific interactions and keep localized data in a separate module. Preserve the cue scheduler, non-blocking cursor, recording configuration, and muxing contract unless a documented application requirement demands a change.

Use accessible roles and labels first. Use durable test IDs when accessibility selectors are ambiguous. Avoid layout-dependent selectors and fixed sleeps for application readiness.

## Prepare the visible state

- Set language and locale before the first navigation or visible frame.
- Use realistic, internally consistent data native to that locale.
- Reset or uniquely suffix data when repeated submissions must coexist.
- Verify required services and email preview tools before starting.
- Preload slow views when narration expects an immediately complete screen.
- Keep secrets, developer tooling, notifications, and unrelated tabs out of frame.

## Map actual audio to actions

Assign action cues to transcribed phrases that describe or naturally precede them. Account for cursor travel, typing, menu selection, animation, validation, network work, and page loading. When a sequence has more UI operations than narration time allows, revise the storyboard or narration instead of accelerating actions until they look unnatural.

## Two execution passes

First run compressed rehearsal mode. It must exercise every selector, transition, submission, and external dependency while preserving cue order. Fix all failures before the real-time run.

Then record against the full master audio. Use a visible 1080p cursor unless the specification requires another format. Close the recorded page cleanly before muxing so Playwright flushes its video. Produce H.264 High-profile video, `yuv420p`, AAC audio, and a broadly playable MP4.

Browser access does not broaden authorization. Do not submit to production, send real emails, or mutate third-party systems unless the user explicitly placed those effects in scope.
