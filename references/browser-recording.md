# Browser Automation and Recording

Read after the master audio and timestamp data pass validation.

## Adapt the template — or the project's existing harness

Copy `assets/playwright-demo-template/` into a greenfield project. When the project already has a recorder, adapt it to the template's contract instead of replacing it; the contract is listed in `SKILL.md`. Replace the example scenario with project-specific interactions and keep localized data in a separate module. Preserve the cue scheduler, non-blocking cursor, recording configuration, and muxing contract unless a documented application requirement demands a change.

Use accessible roles and labels first. Use durable test IDs when accessibility selectors are ambiguous. Avoid layout-dependent selectors and fixed sleeps for application readiness.

## Prepare the visible state

- Set language and locale before the first navigation, and call `assertLocale` on the opening frame and after every route change. A single wrong-direction or wrong-language frame ruins a localized demo; abort rather than record it.
- Navigate and settle the opening screen in `scenario.prepare` **before** the narration clock starts. The recorder measures that pre-roll and trims it at mux time, so the first frame is a painted page.
- Use realistic, internally consistent data native to that locale.
- Suffix every run's data with a unique identifier (a timestamp in the email addresses, for instance). Repeated rehearsals and takes coexist in the same database and inbox, and the identifier is what keeps a stale record from an earlier run out of frame.
- Verify required services and email preview tools before starting.
- Preload slow views when narration expects an immediately complete screen.
- Keep secrets, developer tooling, notifications, and unrelated tabs out of frame.

## Map actual audio to actions

Cues arrive from `resolveCues(manifest)` already on the master timeline, each with the measured time of its anchor phrase. Account for cursor travel, typing, menu selection, animation, validation, network work, and page loading. When a sequence has more UI operations than narration time allows, revise the storyboard or narration instead of accelerating actions until they look unnatural. Unnarrated filler (an address step nobody mentions) belongs in the tail of the preceding chapter, so the next cue lands on a freshly opened step.

Give every cue that changes the screen an `expect_text`, and call `expectAfter` once the action completes. A rehearsal that only proves selectors resolve will happily open a stale record, the wrong tab, or last week's email.

Choose an `expect_text` the page can actually show. Most cues fill a field, and an input's **value is not DOM text**: `expectAfter` therefore reads form-control values as well as rendered text. Where neither is available — a read-only summary tab, a checkbox that looks the same either way — assert a line that only that screen renders, such as its help text, rather than a label present before the action.

## Selection rules learned the hard way

- **Never take `.last()` from a text match.** In any list that can hold previous runs (inboxes, teacher lists, audit logs), the last match is the oldest one. Match on the run's unique identifier and verify what opened.
- **Prefer `getByRole("tab" | "option" | "button")` over `getByText`.** Pages often render a hidden mobile navigation that duplicates every desktop label; `firstVisible` exists for the cases where text is the only handle.
- **Searchable comboboxes need typing.** cmdk-style selects render no options until the search box is filled; use `chooseSearchable`.
- **i18n renders short names.** A country list shows «السعودية», not the official long form the narration uses. Read the option label from the app, not from the script.
- **Locale changes digits.** Under `ar-SA`, `Intl` renders Arabic-Indic digits; match dates and years with a pattern that accepts both digit sets.
- **Date pickers keep the displayed month when the year changes.** Step through months until the target day is actually on the grid, and pick a birth date whose month is not the current one to prove it works.
- **Email preview tools are third-party UIs.** Mailpit and similar have no locale; their chrome stays English and LTR while the message bodies follow the app's locale. Disclose this as a limitation in the report instead of implying the whole recording is localized.
- **A freshly mounted step is not visible yet.** `isVisible()` does not retry, so a single scan races a wizard step that is still animating in and reports a control plainly on screen as missing. `firstVisible` polls to a timeout; never replace it with a bare `isVisible()` check.
- **Browser permissions that the app needs must be granted.** A "Copied" confirmation depends on `navigator.clipboard`, which headless Chromium denies by default; grant `clipboard-read`/`clipboard-write` on the context. When an assertion fails on a state the application controls, ask what the browser is withholding before doubting the selector.
- **A read-only tab may not carry the label its section is named after.** Verify the assertion text against the running application, not against the interface strings file: a key can exist for an edit mode the demo never enters.

## Two execution passes

First run compressed rehearsal mode. It must exercise every selector, transition, submission, external dependency and `expect_text` assertion while preserving cue order. Expect it to fail several times on application details the storyboard could not know; fix each in the automation, never by weakening an assertion.

Make those failures diagnosable. Playwright reports what was missing, never what was on screen instead, so a failing cue should also capture a screenshot and a slice of the page's visible text — the difference between "the selector is wrong" and "the previous step never submitted" is usually one line of that dump.

Then record against the full master audio. Use a visible 1080p cursor unless the specification requires another format. Hold the final frame at least two seconds after the last cue before closing the page, mux with `-t <audio duration>` rather than `-shortest`, and produce H.264 High-profile video, `yuv420p`, AAC audio, and a broadly playable MP4.

Browser access does not broaden authorization. Do not submit to production, send real emails, or mutate third-party systems unless the user explicitly placed those effects in scope.
