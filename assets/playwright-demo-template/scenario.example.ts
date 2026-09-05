import type { Page } from "playwright";
import type { ProductionManifest } from "./config";
import { clickWithCursor, moveCursorTo } from "./cursor";
import { assertLocale, expectAfter } from "./interactions";
import type { Cue, CueScheduler } from "./timeline";

export interface DemoScenario {
  /** Runs before navigation: force the application language and any test state. */
  initialize(page: Page, manifest: ProductionManifest): Promise<void>;
  /**
   * Navigate to the opening screen and wait until it is fully painted. The narration
   * clock starts only after this resolves, and the recorder trims everything before it.
   */
  prepare(page: Page, manifest: ProductionManifest): Promise<void>;
  /** The narrated journey. `cues` are already on the master timeline. */
  run(page: Page, scheduler: CueScheduler, cues: Cue[], scale: number): Promise<void>;
}

const demoData = { displayName: "Localized Example" };

function cue(cues: Cue[], id: string): Cue {
  const found = cues.find(item => item.id === id);
  if (!found) throw new Error(`Scenario references unknown cue "${id}"`);
  return found;
}

export const scenario: DemoScenario = {
  async initialize(page, manifest) {
    await page.addInitScript(locale => localStorage.setItem("application-language", locale), manifest.locale);
  },

  async prepare(page, manifest) {
    await page.goto("/", { waitUntil: "networkidle" });
    await page.getByRole("heading", { name: "Create profile" }).waitFor();
    await assertLocale(page, { dir: "ltr", lang: manifest.locale }, "opening frame");
  },

  async run(page, scheduler, cues, scale) {
    const enterName = cue(cues, "enter-name");
    const submit = cue(cues, "continue");

    await scheduler.waitFor(enterName);
    const name = page.getByLabel("Display name", { exact: true });
    await moveCursorTo(page, name, scale);
    await name.fill(demoData.displayName);
    await expectAfter(page, enterName);

    await scheduler.waitFor(submit);
    await clickWithCursor(page, page.getByRole("button", { name: "Continue" }), scale);
    await page.getByRole("heading", { name: "Complete" }).waitFor();
    await expectAfter(page, submit);
  },
};
