import { readFileSync } from "node:fs";
import { resolve } from "node:path";

export type ProductionManifest = {
  locale: string;
  master_audio_path: string;
  chapters: Array<{ id: string; duration_seconds: number; cues: Array<{ id: string; at_seconds: number; action: string }> }>;
  chapter_gap_seconds?: number;
};

function option(args: string[], name: string) {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : undefined;
}

export function ffmpegArgs(video: string, audio: string, output: string) {
  return ["-y", "-i", video, "-i", audio, "-c:v", "libx264", "-profile:v", "high", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", output];
}

export function resolveRecordingConfig(args = process.argv.slice(2), cwd = process.cwd()) {
  const manifestPath = resolve(cwd, option(args, "--manifest") ?? "production.json");
  const fast = args.includes("--fast");
  let manifest: ProductionManifest | undefined;
  try { manifest = JSON.parse(readFileSync(manifestPath, "utf8")); } catch { /* validated by record.ts */ }
  const locale = manifest?.locale ?? "en-US";
  return {
    appUrl: option(args, "--app-url") ?? "http://localhost:3000",
    manifestPath,
    outputDir: resolve(cwd, option(args, "--output") ?? "artifacts/demo-recording"),
    fast,
    timeScale: fast ? 0.01 : 1,
    viewport: { width: 1920, height: 1080 },
    locale,
    localeInitScript: `localStorage.setItem('demo-locale', ${JSON.stringify(locale)});`,
    manifest,
  };
}
