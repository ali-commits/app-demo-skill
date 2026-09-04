import { describe, expect, test } from "bun:test";
import { CURSOR_INIT_SCRIPT } from "./cursor";
import { ffmpegArgs, resolveRecordingConfig } from "./config";
import { scaledDelay, validateCues } from "./timeline";

describe("recording template", () => {
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

  test("defaults to 1080p and compatible muxing", () => {
    const config = resolveRecordingConfig(["--manifest", "production.json"], "/demo");
    expect(config.viewport).toEqual({ width: 1920, height: 1080 });
    expect(config.localeInitScript).toContain("demo-locale");
    expect(ffmpegArgs("raw.webm", "master.wav", "final.mp4")).toEqual(expect.arrayContaining([
      "libx264", "yuv420p", "aac", "-shortest"
    ]));
  });
});
