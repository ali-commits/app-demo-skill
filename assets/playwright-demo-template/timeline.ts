export type Cue = { id: string; at: number; action: string };

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
    process.stdout.write(`\n[${cue.at.toFixed(2)}s] ${cue.action}`);
  }
}
