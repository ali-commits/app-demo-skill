# Recording Verification

Read after every real-time render and when repairing an existing demo.

## Structural checks

Use `inspect_recording.py` and verify:

- File is readable and duration is nonzero.
- Video and audio streams exist.
- Dimensions match the specification.
- H.264/AAC output is used unless another approved target requires different codecs.
- Audio and video durations agree within tolerance. A recording that is a few hundred milliseconds shorter than the narration has clipped the closing words — the fix is the tail hold and `-t` mux in the harness, not a wider tolerance.
- Every cue and chapter fits inside the recording.
- `opening_frame_blank` is false. A blank first frame means the narration clock started before the page was painted.

## Visual review

The inspector writes a frame before, at, and after every chapter boundary, **and one frame shortly after every cue**. Chapter boundaries alone will not reveal a stale record opened mid-chapter; the per-cue frames will. Inspect for:

- Correct language from the opening frame onward
- Locale-appropriate data and text direction
- Data belonging to **this run** (unique identifiers), not to an earlier rehearsal
- Loading skeletons, blank views, or stale content
- Open menus, dropdowns, dialogs, and tooltips at unintended times
- Focus rings, clipped controls, horizontal overflow, or obscured content
- Cursor location and click feedback
- Secrets, personal data, console windows, and debug artifacts
- Incorrect email, dashboard, mobile, or responsive state

Review moving playback around transitions when static frames cannot establish smoothness.

## Narration review

Confirm that the spoken text matches the approved narration, chapter boundaries sound natural, loudness is consistent, and every recorded scene has narration coverage. A truncated audio file cannot support silently appended scenes. When coverage was below threshold, cite the transcript's `missing_words` and state whether each was misheard or absent.

## Delivery report

Provide paths to the specification, storyboard, narration, manifest, chapter audio, master audio, timing data, automation, final MP4, and verification report. State tests performed, every defect verification found and how it was fixed, and any known limitation (third-party UI locale, visible tokens, inbox contents). Do not describe the result as complete while a required scene, language, data set, or narration section is missing.
