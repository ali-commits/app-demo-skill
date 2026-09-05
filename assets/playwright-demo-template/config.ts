import { readFileSync } from "node:fs";
import { resolve } from "node:path";

export type ManifestCue = {
  id: string;
  at_seconds: number | null;
  action: string;
  expect_text?: string | null;
};

export type ProductionManifest = {
  locale: string;
  master_audio_path: string;
  chapters: Array<{ id: string; duration_seconds: number; cues: ManifestCue[] }>;
  chapter_gap_seconds?: number;
};

function option(args: string[], name: string) {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : undefined;
}

export type MuxOptions = {
  /** Seconds of capture to drop from the front: the page-settling pre-roll. */
  trimSeconds?: number;
  /** Length of the master narration; the output is cut to exactly this. */
  durationSeconds?: number;
};

export function ffmpegArgs(video: string, audio: string, output: string, options: MuxOptions = {}) {
  const { trimSeconds = 0, durationSeconds } = options;
  return [
    "-y",
    ...(trimSeconds > 0 ? ["-ss", trimSeconds.toFixed(3)] : []),
    "-i", video,
    "-i", audio,
    "-c:v", "libx264", "-profile:v", "high", "-crf", "18", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k",
    // Never `-shortest`: a capture that ends a few hundred milliseconds early would
    // silently clip the final words. The picture is held on its last frame instead.
    ...(durationSeconds ? ["-t", durationSeconds.toFixed(3)] : []),
    output,
  ];
}

export function loadManifest(path: string): ProductionManifest {
  let raw: string;
  try {
    raw = readFileSync(path, "utf8");
  } catch (error) {
    throw new Error(`Cannot read production manifest at ${path}: ${error}`);
  }
  try {
    return JSON.parse(raw) as ProductionManifest;
  } catch (error) {
    throw new Error(`Production manifest at ${path} is not valid JSON: ${error}`);
  }
}

export function resolveRecordingConfig(args = process.argv.slice(2), cwd = process.cwd()) {
  const manifestPath = resolve(cwd, option(args, "--manifest") ?? "production.json");
  const manifest = loadManifest(manifestPath);
  const fast = args.includes("--fast");
  return {
    appUrl: option(args, "--app-url") ?? "http://localhost:3000",
    manifestPath,
    outputDir: resolve(cwd, option(args, "--output") ?? "artifacts/demo-recording"),
    fast,
    timeScale: fast ? 0.01 : 1,
    viewport: { width: 1920, height: 1080 },
    locale: manifest.locale,
    localeInitScript: `localStorage.setItem('demo-locale', ${JSON.stringify(manifest.locale)});`,
    manifest,
  };
}
