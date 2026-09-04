import type { Locator, Page } from "playwright";

export const CURSOR_INIT_SCRIPT = String.raw`
(() => {
  const install = () => {
    if (document.getElementById('narrated-demo-cursor')) return;
    const style = document.createElement('style');
    style.textContent = '#narrated-demo-cursor{position:fixed;left:0;top:0;width:25px;height:32px;z-index:2147483647;pointer-events:none;opacity:0;transform:translate(-3px,-3px);transition:left .42s cubic-bezier(.2,.8,.2,1),top .42s cubic-bezier(.2,.8,.2,1),opacity .18s ease;filter:drop-shadow(0 2px 2px rgba(0,0,0,.35))}.narrated-demo-ripple{position:fixed;width:10px;height:10px;border:3px solid rgba(12,125,69,.8);border-radius:999px;z-index:2147483646;pointer-events:none;transform:translate(-50%,-50%);animation:narrated-ripple .55s ease-out forwards}@keyframes narrated-ripple{to{width:54px;height:54px;opacity:0}}';
    document.documentElement.appendChild(style);
    const cursor = document.createElement('div');
    cursor.id = 'narrated-demo-cursor';
    cursor.innerHTML = '<svg viewBox="0 0 24 30"><path d="M2 1.5v23.8l6.2-5.2 4.2 8.2 4-2-4.2-8.1 7.8-.7L2 1.5Z" fill="#fff" stroke="#17212b" stroke-width="1.8"/></svg>';
    document.documentElement.appendChild(cursor);
    window.__narratedDemoCursor = {
      move(x, y) { cursor.style.left = x + 'px'; cursor.style.top = y + 'px'; cursor.style.opacity = '1'; },
      click(x, y) { const ripple = document.createElement('div'); ripple.className = 'narrated-demo-ripple'; ripple.style.left = x + 'px'; ripple.style.top = y + 'px'; document.documentElement.appendChild(ripple); setTimeout(() => ripple.remove(), 650); }
    };
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, { once: true }); else install();
})();`;

export async function installCursor(page: Page): Promise<void> {
  await page.addInitScript({ content: CURSOR_INIT_SCRIPT });
  await page.evaluate(CURSOR_INIT_SCRIPT);
}

export async function moveCursorTo(page: Page, locator: Locator, scale: number) {
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  if (!box) throw new Error("Cursor target is not visible");
  const point = { x: box.x + box.width / 2, y: box.y + box.height / 2 };
  await page.evaluate(({ x, y }) => (window as any).__narratedDemoCursor?.move(x, y), point);
  await Bun.sleep(Math.max(5, Math.round(480 * scale)));
  return point;
}

export async function clickWithCursor(page: Page, locator: Locator, scale: number) {
  const point = await moveCursorTo(page, locator, scale);
  await page.evaluate(({ x, y }) => (window as any).__narratedDemoCursor?.click(x, y), point);
  await locator.click();
  await Bun.sleep(Math.max(5, Math.round(260 * scale)));
}
