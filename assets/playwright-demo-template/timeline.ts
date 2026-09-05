import type { ProductionManifest } from "./config";

export type Cue = {
  id: string;
  at: number;
  action: string;
  /** Chapter-qualified label used in scheduler logs. */
  name?: string;
  /** Text that must be visible after the action; asserted by `expectAfter`. */
  expectText?: string;
};

export const DEFAULT_CHAPTER_GAP = 0.45;

/**
 * Flatten chapter-relative cue times onto the master narration timeline. This is the
 * one place that knows about chapter offsets and gaps; scenarios consume the result.
 */
export function resolveCues(manifest: ProductionManifest): Cue[] {
  const gap = manifest.chapter_gap_seconds ?? DEFAULT_CHAPTER_GAP;
  let offset = 0;
  return manifest.chapters.flatMap((chapter, index) => {
    if (index) offset += gap;
    const rows = chapter.cues.map(cue => {
      if (cue.at_seconds === null || cue.at_seconds === undefined) {
        throw new Error(`${chapter.id}/${cue.id} has no time: run derive_cues before recording`);
      }
      return {
        id: cue.id,
        at: offset + cue.at_seconds,
        action: cue.action,
        name: `${chapter.id}/${cue.id} — ${cue.action}`,
        expectText: cue.expect_text ?? undefined,
      };
    });
    offset += chapter.duration_seconds;
    return rows;
  });
}

export function masterDuration(manifest: ProductionManifest): number {
  const gap = manifest.chapter_gap_seconds ?? DEFAULT_CHAPTER_GAP;
  return manifest.chapters.reduce(
    (sum, chapter, index) => sum + chapter.duration_seconds + (index ? gap : 0),
    0
  );
}

export function validateCues(cues: Cue[], durationSeconds: number): true {
  let previous = -1;
  for (const cue of cues) {
    if (cue.at <= previous) throw new Error(`Cue timestamps must be strictly increasing: ${cue.id}`);
    if (cue.at > durationSeconds) throw new Error(`Cue exceeds audio duration: ${cue.id}`);
    previous = cue.at;
  }
  return true;
}

export function scaledDelay(previous: number, next: number, scale: number): number {
  return Math.max(0, Math.round((next - previous) * 1000 * scale));
}

export class CueScheduler {
  private readonly startedAt = performance.now();

  constructor(private readonly timeScale: number) {}

  async waitFor(cue: Cue): Promise<void> {
    const remaining = cue.at * 1000 * this.timeScale - (performance.now() - this.startedAt);
    if (remaining > 0) await Bun.sleep(Math.round(remaining));
    process.stdout.write(`\n[${cue.at.toFixed(2)}s] ${cue.name ?? cue.action}`);
  }

  /** Seconds elapsed on the (unscaled) narration timeline. */
  elapsed(): number {
    return (performance.now() - this.startedAt) / 1000 / this.timeScale;
  }
}
