import { describe, expect, test } from "bun:test";
import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { CURSOR_INIT_SCRIPT } from "./cursor";
import { ffmpegArgs, resolveRecordingConfig } from "./config";
import { checkLocale, firstVisible, matchesExpectation } from "./interactions";
import { resolveCues, scaledDelay, validateCues } from "./timeline";

describe("recording template", () => {
  test("mux really extends a short video to the narration duration", async () => {
    const dir = await mkdtemp(join(tmpdir(), "demo-padding-"));
    const video = join(dir, "short.mp4");
    const audio = join(dir, "audio.wav");
    const output = join(dir, "result.mp4");
    const run = async (args: string[]) => {
      const process = Bun.spawn(args, { stdout: "pipe", stderr: "pipe" });
      const [stdout, stderr, code] = await Promise.all([new Response(process.stdout).text(), new Response(process.stderr).text(), process.exited]);
      if (code !== 0) throw new Error(stderr);
      return stdout;
    };
    await run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x240:d=0.5", "-c:v", "libx264", video]);
    await run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=duration=2", audio]);
    await run(["ffmpeg", ...ffmpegArgs(video, audio, output, { durationSeconds: 2 })]);
    const probe = JSON.parse(await run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "json", output]));
    expect(probe.streams).toHaveLength(2);
    for (const stream of probe.streams) expect(Math.abs(Number(stream.duration) - 2)).toBeLessThan(0.1);
  });
  test("rejects unordered and out-of-duration cues", () => {
    expect(() => validateCues([{ id: "b", at: 2, action: "B" }, { id: "a", at: 1, action: "A" }], 3)).toThrow();
    expect(() => validateCues([{ id: "late", at: 4, action: "Late" }], 3)).toThrow();
  });

  test("fast mode scales waits without changing authored cues", () => {
    const cue = { id: "open", at: 10, action: "Open" };
    expect(scaledDelay(2, cue.at, 0.01)).toBe(80);
    expect(cue.at).toBe(10);
  });

  test("cursor cannot intercept application input", () => {
    expect(CURSOR_INIT_SCRIPT).toContain("pointer-events:none");
  });

  test("defaults to 1080p and takes the locale from the manifest", async () => {
    const dir = await mkdtemp(join(tmpdir(), "demo-"));
    await writeFile(join(dir, "production.json"), JSON.stringify({
      locale: "ar-SA", master_audio_path: "master.mp3", chapters: [],
    }));
    const config = resolveRecordingConfig(["--manifest", "production.json"], dir);
    expect(config.viewport).toEqual({ width: 1920, height: 1080 });
    expect(config.locale).toBe("ar-SA");
    expect(config.localeInitScript).toContain("demo-locale");
  });

  test("muxing trims the pre-roll and pads to the audio length instead of cutting to the shorter stream", () => {
    const args = ffmpegArgs("raw.webm", "master.wav", "final.mp4", { trimSeconds: 1.25, durationSeconds: 317.63 });
    expect(args).toEqual(expect.arrayContaining(["libx264", "yuv420p", "aac"]));
    // -ss must precede the video input so the blank pre-roll is dropped from the picture only.
    expect(args.indexOf("-ss")).toBeLessThan(args.indexOf("raw.webm"));
    expect(args[args.indexOf("-ss") + 1]).toBe("1.250");
    // `-shortest` silently clipped the last words of narration whenever the capture
    // ended a few hundred milliseconds early; the output must run the audio's length.
    expect(args).not.toContain("-shortest");
    expect(args[args.indexOf("-t") + 1]).toBe("317.630");
  });

  test("resolves chapter-relative cues to master offsets once, including the gap", () => {
    const cues = resolveCues({
      locale: "ar-SA",
      master_audio_path: "master.mp3",
      chapter_gap_seconds: 0.5,
      chapters: [
        { id: "01-a", duration_seconds: 10, cues: [{ id: "one", at_seconds: 2, action: "One" }] },
        { id: "02-b", duration_seconds: 5, cues: [{ id: "two", at_seconds: 1, action: "Two", expect_text: "Done" }] },
      ],
    });
    expect(cues.map(cue => [cue.id, cue.at])).toEqual([["one", 2], ["two", 11.5]]);
    expect(cues[1].expectText).toBe("Done");
    expect(cues[1].name).toContain("02-b");
  });

  test("an unreadable manifest fails immediately with its path", () => {
    expect(() => resolveRecordingConfig(["--manifest", "missing.json"], "/nowhere")).toThrow(/missing\.json/);
  });

  test("locale check requires both direction and language to match", () => {
    expect(checkLocale({ dir: "rtl", lang: "ar-SA" }, { dir: "rtl", lang: "ar" })).toBeNull();
    expect(checkLocale({ dir: "ltr", lang: "ar" }, { dir: "rtl", lang: "ar" })).toMatch(/dir/);
    expect(checkLocale({ dir: "rtl", lang: "en-US" }, { dir: "rtl", lang: "ar" })).toMatch(/lang/);
  });
});

describe("post-action expectation", () => {
  test("accepts a value typed into a field, which carries no DOM text", () => {
    // Most cues prove themselves by what was typed, and an input's value is not DOM
    // text: a text-only assertion passes happily on an empty form, so `expect_text` on
    // every filled field was silently a no-op.
    expect(
      matchesExpectation(
        { text: "Official institution name", values: ["Al-Manarah International Kindergarten"] },
        "Al-Manarah International Kindergarten"
      )
    ).toBe(true);
  });

  test("still matches rendered text, case-insensitively, and rejects absent content", () => {
    expect(matchesExpectation({ text: "SUBMITTED", values: [] }, "submitted")).toBe(true);
    expect(matchesExpectation({ text: "Overview", values: ["12"] }, "Sarah Mansour")).toBe(false);
  });
});

describe("visible-match search", () => {
  test("waits for a match instead of sampling once", async () => {
    // `isVisible()` does not retry, so a single scan races a wizard step that is still
    // mounting and reports a control that is plainly on screen as missing.
    let visible = false;
    setTimeout(() => {
      visible = true;
    }, 120);
    const locator = {
      count: async () => 1,
      nth: () => ({ isVisible: async () => visible }),
    } as unknown as Parameters<typeof firstVisible>[0];
    expect(await firstVisible(locator, 2_000)).not.toBeNull();
  });

  test("gives up at the timeout rather than hanging", async () => {
    const locator = {
      count: async () => 1,
      nth: () => ({ isVisible: async () => false }),
    } as unknown as Parameters<typeof firstVisible>[0];
    expect(await firstVisible(locator, 150)).toBeNull();
  });
});
