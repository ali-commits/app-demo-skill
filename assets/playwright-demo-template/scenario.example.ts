import type { Page } from "playwright";
import type { ProductionManifest } from "./config";
import { clickWithCursor, moveCursorTo } from "./cursor";
import type { CueScheduler } from "./timeline";

export interface DemoScenario {
  initialize(page: Page, manifest: ProductionManifest): Promise<void>;
  run(page: Page, scheduler: CueScheduler, manifest: ProductionManifest, scale: number): Promise<void>;
}

const demoData = { displayName: "Localized Example" };

export const scenario: DemoScenario = {
  async initialize(page, manifest) {
    await page.addInitScript(locale => localStorage.setItem("application-language", locale), manifest.locale);
  },
  async run(page, scheduler, manifest, scale) {
    const cues = manifest.chapters.flatMap((chapter, chapterIndex) => {
      const before = manifest.chapters.slice(0, chapterIndex);
      const offset = before.reduce((sum, item) => sum + item.duration_seconds + (manifest.chapter_gap_seconds ?? 0.45), 0);
      return chapter.cues.map(cue => ({ id: cue.id, at: offset + cue.at_seconds, action: cue.action }));
    });
    await page.goto("/");
    await scheduler.waitFor(cues[0]);
    const name = page.getByLabel("Display name", { exact: true });
    await moveCursorTo(page, name, scale);
    await name.fill(demoData.displayName);
    await scheduler.waitFor(cues[1]);
    await clickWithCursor(page, page.getByRole("button", { name: "Continue" }), scale);
    await page.getByRole("heading", { name: "Complete" }).waitFor();
  },
};
