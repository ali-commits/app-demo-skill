import { mkdir } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { chromium } from "playwright";
import { ffmpegArgs, resolveRecordingConfig } from "./config";
import { installCursor } from "./cursor";
import { scenario } from "./scenario.example";
import { CueScheduler, masterDuration, resolveCues, validateCues } from "./timeline";

/** Seconds to hold the final frame after the narration ends, before closing the page. */
const TAIL_HOLD_SECONDS = 2;

const config = resolveRecordingConfig();
const manifest = config.manifest;
const duration = masterDuration(manifest);
const cues = resolveCues(manifest);
validateCues(cues, duration);
await mkdir(config.outputDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  baseURL: config.appUrl,
  viewport: config.viewport,
  locale: config.locale,
  recordVideo: { dir: config.outputDir, size: config.viewport },
});
const page = await context.newPage();
const captureStartedAt = performance.now();
await scenario.initialize(page, manifest);
await installCursor(page);

let rawVideo = "";
let prerollSeconds = 0;
try {
  // Settle the opening screen BEFORE the narration clock starts. The capture already
  // contains these frames; they are trimmed at mux time so the video opens on a
  // painted page instead of a blank one.
  await scenario.prepare(page, manifest);
  prerollSeconds = (performance.now() - captureStartedAt) / 1000;

  const scheduler = new CueScheduler(config.timeScale);
  await scenario.run(page, scheduler, cues, config.timeScale);
  await scheduler.waitFor({ id: "recording-end", at: duration, action: "End of narration" });
  // Playwright stops capturing the instant the page closes; without this hold the
  // picture ends before the audio does and the final words would be cut.
  await Bun.sleep(Math.max(50, Math.round(TAIL_HOLD_SECONDS * 1000 * config.timeScale)));

  const video = page.video();
  await page.close();
  rawVideo = (await video?.path()) ?? "";
} finally {
  await context.close();
  await browser.close();
}
if (!rawVideo) throw new Error("Playwright did not create a recording");

if (config.fast) {
  console.log(`\nFast rehearsal passed: ${rawVideo}`);
} else {
  const audio = resolve(dirname(config.manifestPath), manifest.master_audio_path);
  const output = join(config.outputDir, "narrated-demo.mp4");
  const args = ffmpegArgs(rawVideo, audio, output, {
    trimSeconds: prerollSeconds,
    durationSeconds: duration,
  });
  const process = Bun.spawn(["ffmpeg", ...args], { stdout: "inherit", stderr: "inherit" });
  if (await process.exited) throw new Error("ffmpeg failed to mux the recording");
  console.log(`\nFinished: ${output}`);
}
