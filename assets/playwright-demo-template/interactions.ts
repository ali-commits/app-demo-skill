import type { Locator, Page } from "playwright";
import { clickWithCursor, moveCursorTo } from "./cursor";
import type { Cue } from "./timeline";

/**
 * Shared, cursor-aware interactions. Every helper prefers accessible roles and labels,
 * and none of them pick `.last()` from a text match: in any list that can hold data
 * from earlier runs, the last match is the oldest one.
 */

export async function fillField(page: Page, label: string, value: string, scale: number, exact = false) {
  const field = page.getByLabel(label, { exact });
  await moveCursorTo(page, field, scale);
  await field.fill(value);
  await Bun.sleep(Math.max(8, Math.round(180 * scale)));
}

/** Pick an option from a native-style listbox (e.g. Radix Select) by its visible text. */
export async function choose(page: Page, label: string, option: string, scale: number) {
  await clickWithCursor(page, page.getByLabel(label, { exact: true }), scale);
  await clickWithCursor(page, page.getByRole("option", { name: option }).first(), scale);
}

/**
 * Pick from a searchable combobox (cmdk-style): the option list is filtered by a search
 * box, so the value has to be typed before its option exists to click.
 */
export async function chooseSearchable(
  page: Page,
  label: string,
  query: string,
  scale: number,
  searchPlaceholder: string | RegExp = /search/i
) {
  await clickWithCursor(page, page.getByLabel(label, { exact: true }), scale);
  const search = page.getByPlaceholder(searchPlaceholder);
  await search.waitFor();
  await search.fill(query);
  await clickWithCursor(page, page.getByRole("option", { name: new RegExp(query) }).first(), scale);
}

export async function clickButton(page: Page, name: string | RegExp, scale: number) {
  await clickWithCursor(page, page.getByRole("button", { name, exact: typeof name === "string" }), scale);
}

/** First *visible* match — pages often render a hidden mobile duplicate of desktop nav. */
export async function firstVisible(locator: Locator): Promise<Locator | null> {
  const count = await locator.count();
  for (let index = 0; index < count; index += 1) {
    const candidate = locator.nth(index);
    if (await candidate.isVisible().catch(() => false)) return candidate;
  }
  return null;
}

export async function clickVisibleText(page: Page, text: string, scale: number) {
  const target = await firstVisible(page.getByText(text, { exact: true }));
  if (!target) throw new Error(`No visible element with text "${text}"`);
  await clickWithCursor(page, target, scale);
}

export type LocaleState = { dir: string; lang: string };
export type LocaleExpectation = { dir: "ltr" | "rtl"; lang: string };

/** Pure comparison so the rule is unit-testable; `assertLocale` reads the page for it. */
export function checkLocale(state: LocaleState, expected: LocaleExpectation): string | null {
  if (state.dir !== expected.dir) return `expected dir="${expected.dir}" but found "${state.dir}"`;
  if (!state.lang.toLowerCase().startsWith(expected.lang.toLowerCase())) {
    return `expected lang starting with "${expected.lang}" but found "${state.lang}"`;
  }
  return null;
}

/**
 * Abort rather than record a wrong-language frame. Call it on the opening frame and
 * after every route change; a single LTR or wrong-language frame ruins a localized demo.
 */
export async function assertLocale(page: Page, expected: LocaleExpectation, where: string) {
  const state = await page.evaluate(() => ({
    dir: document.documentElement.dir || "ltr",
    lang: document.documentElement.lang,
  }));
  const problem = checkLocale(state, expected);
  if (problem) throw new Error(`${where}: ${problem}`);
}

/**
 * After a cue's action, prove the expected screen appeared. A rehearsal that only proves
 * selectors resolve will happily open a stale record or the wrong tab.
 */
export async function expectAfter(page: Page, cue: Cue, timeoutMs = 10_000) {
  if (!cue.expectText) return;
  const target = page.getByText(cue.expectText, { exact: false });
  try {
    await target.first().waitFor({ timeout: timeoutMs });
  } catch {
    throw new Error(`${cue.name ?? cue.id}: expected "${cue.expectText}" on screen after the action`);
  }
}
