import { mkdir } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { chromium } from "playwright";
import { ffmpegArgs, resolveRecordingConfig, type ProductionManifest } from "./config";
import { installCursor } from "./cursor";
import { scenario } from "./scenario.example";
import { CueScheduler, validateCues } from "./timeline";

const config = resolveRecordingConfig();
if (!config.manifest) throw new Error(`Cannot read production manifest: ${config.manifestPath}`);
const manifest = config.manifest as ProductionManifest;
const duration = manifest.chapters.reduce((sum, chapter, index) => sum + chapter.duration_seconds + (index ? manifest.chapter_gap_seconds ?? 0.45 : 0), 0);
let offset = 0;
const cues = manifest.chapters.flatMap((chapter, index) => {
  if (index) offset += manifest.chapter_gap_seconds ?? 0.45;
  const rows = chapter.cues.map(cue => ({ id: cue.id, at: offset + cue.at_seconds, action: cue.action }));
  offset += chapter.duration_seconds;
  return rows;
});
validateCues(cues, duration);
await mkdir(config.outputDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ baseURL: config.appUrl, viewport: config.viewport, locale: config.locale, recordVideo: { dir: config.outputDir, size: config.viewport } });
const page = await context.newPage();
await scenario.initialize(page, manifest);
await installCursor(page);
const scheduler = new CueScheduler(config.timeScale);
let rawVideo = "";
try {
  await scenario.run(page, scheduler, manifest, config.timeScale);
  if (!config.fast) await scheduler.waitFor({ id: "recording-end", at: duration, action: "Finish recording" });
  const video = page.video();
  await page.close();
  rawVideo = (await video?.path()) ?? "";
} finally {
  await context.close();
  await browser.close();
}
if (!rawVideo) throw new Error("Playwright did not create a recording");
if (config.fast) {
  console.log(`Fast rehearsal passed: ${rawVideo}`);
} else {
  const audio = resolve(dirname(config.manifestPath), manifest.master_audio_path);
  const output = join(config.outputDir, "narrated-demo.mp4");
  const process = Bun.spawn(["ffmpeg", ...ffmpegArgs(rawVideo, audio, output)], { stdout: "inherit", stderr: "inherit" });
  if (await process.exited) throw new Error("ffmpeg failed to mux the recording");
  console.log(`Finished: ${output}`);
}
