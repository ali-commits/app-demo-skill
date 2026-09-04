# Recording Verification

Read after every real-time render and when repairing an existing demo.

## Structural checks

Use `inspect_recording.py` and verify:

- File is readable and duration is nonzero.
- Video and audio streams exist.
- Dimensions match the specification.
- H.264/AAC output is used unless another approved target requires different codecs.
- Audio and video durations agree within tolerance.
- Every cue and chapter fits inside the recording.

## Visual review

Sample frames before, at, and after every chapter boundary, plus every important submission and route transition. Inspect for:

- Correct language from the opening frame onward
- Locale-appropriate data and text direction
- Loading skeletons, blank views, or stale content
- Open menus, dropdowns, dialogs, and tooltips at unintended times
- Focus rings, clipped controls, horizontal overflow, or obscured content
- Cursor location and click feedback
- Secrets, personal data, console windows, and debug artifacts
- Incorrect email, dashboard, mobile, or responsive state

Review moving playback around transitions when static frames cannot establish smoothness.

## Narration review

Confirm that the spoken text matches the approved narration, chapter boundaries sound natural, loudness is consistent, and every recorded scene has narration coverage. A truncated audio file cannot support silently appended scenes.

## Delivery report

Provide paths to the specification, storyboard, narration, manifest, chapter audio, master audio, timing data, automation, final MP4, and verification report. State tests performed and any known limitation. Do not describe the result as complete while a required scene, language, data set, or narration section is missing.
