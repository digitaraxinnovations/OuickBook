import { expect, Locator, Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { appConfig } from "../../src/config/app.config";
import { demoConfig } from "../demo.config";

interface Caption {
  at: number;
  title: string;
  text: string;
}

interface ChapterMark {
  at: number;
  num: number;
  title: string;
}

function escapeRegex(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** A field label, with or without the "*" the app adds to required fields. */
export function labelPattern(label: string): RegExp {
  return new RegExp("^\\s*" + escapeRegex(label) + "(\\s*\\*)?\\s*$");
}

/**
 * Drives the browser for the demo tour: captions, chapter cards, navigation
 * and form filling, with pauses so people watching can follow along.
 * In test mode (no DEMO_VIDEO) all pauses are zero and it simply runs fast.
 */
export class DemoGuide {
  readonly page: Page;
  private readonly startedAt = Date.now();
  private readonly captions: Caption[] = [];
  private readonly chapters: ChapterMark[] = [];
  private chapterNo = 0;
  private chapterTitle = "";
  /** Earlier chapters run without pauses while working on a later one (DEMO_WATCH_FROM). */
  private fast = false;

  constructor(page: Page) {
    this.page = page;
  }

  /** What to type when the app asks a question (e.g. the closing-date password). */
  promptAnswer = "";

  static async start(page: Page): Promise<DemoGuide> {
    await page.addInitScript({ path: path.join(__dirname, "overlay.js") });
    const guide = new DemoGuide(page);
    // Say yes to "Are you sure?" boxes, and answer prompts with promptAnswer.
    page.on("dialog", async (dialog) => {
      await guide.page.waitForTimeout(guide.fast ? 0 : 900);
      if (dialog.type() === "prompt") {
        await dialog.accept(guide.promptAnswer);
      } else {
        await dialog.accept();
      }
    });
    return guide;
  }

  /** Fills a date field (dates are always filled, not typed, because typing depends on the locale). */
  async setDate(label: string, isoDate: string, within?: Locator): Promise<void> {
    await this.field(label, within).fill(isoDate);
    await this.pause(300);
  }

  // ---------- timing ----------

  private elapsed(): number {
    return Date.now() - this.startedAt;
  }

  async pause(ms: number): Promise<void> {
    if (!this.fast && ms > 0) {
      await this.page.waitForTimeout(ms);
    }
  }

  // ---------- captions ----------

  async chapter(title: string, subtitle: string): Promise<void> {
    this.chapterNo += 1;
    this.chapterTitle = title;
    this.fast = this.chapterNo < demoConfig.watchFromChapter;
    this.chapters.push({ at: this.elapsed(), num: this.chapterNo, title });
    await this.settle();
    await this.page.evaluate(([num, t, s]) => (window as any).__demoCard?.(num, t, s), ["Chapter " + this.chapterNo, title, subtitle]);
    await this.pause(demoConfig.chapterCardMs);
    await this.page.evaluate(() => (window as any).__demoCard?.("", "", ""));
  }

  /** Shows a caption and waits long enough to read it. */
  async say(text: string): Promise<void> {
    this.captions.push({ at: this.elapsed(), title: this.chapterTitle, text });
    await this.page.evaluate(([t, x]) => (window as any).__demoCaption?.(t, x), [this.chapterTitle, text]);
    // Move the pointer off the caption so it stays readable (it fades when the pointer is near).
    if (!this.fast && (await this.page.evaluate(() => (window as any).__demoCursorNearCaption?.()))) {
      const { width, height } = demoConfig.viewport;
      await this.page.mouse.move(width * 0.62, height * 0.45, { steps: 12 });
      await this.page.evaluate(() => {
        const box = document.getElementById("demo-caption");
        if (box) box.style.opacity = "1";
      });
    }
    const words = text.split(/\s+/).length;
    await this.pause(Math.max(demoConfig.minReadingMs, words * demoConfig.readingMsPerWord));
  }

  async clearCaption(): Promise<void> {
    await this.page.evaluate(() => (window as any).__demoCaption?.("", ""));
  }

  // ---------- navigation ----------

  /** Waits until the page has finished loading its data. */
  async settle(): Promise<void> {
    await this.page.waitForLoadState("domcontentloaded");
    // Let the page's data requests finish (short limit: some pages keep polling).
    await this.page.waitForLoadState("networkidle", { timeout: 5000 }).catch(() => undefined);
    await this.page
      .waitForFunction(() => !document.querySelector("main")?.textContent?.includes("Loading..."), null, { timeout: 15000 })
      .catch(() => undefined);
  }

  /** Opens a page from the sidebar, the way a person would. */
  async nav(group: string | null, link: string): Promise<void> {
    await this.clearCaption();
    const sidebar = this.page.locator("aside");
    const target = sidebar.getByRole("link", { name: link, exact: true });
    if (group) {
      // The sidebar restores its open groups just after loading, so check again before each try.
      const toggle = sidebar.getByRole("button", { name: group, exact: true });
      for (let attempt = 0; attempt < 4 && !(await target.isVisible()); attempt++) {
        await this.page.waitForTimeout(300);
        if (!(await target.isVisible())) {
          await toggle.click();
          await this.page.waitForTimeout(300);
        }
      }
    }
    // The sidebar can shift while it scrolls, so make sure we arrived where the link points.
    const href = (await target.getAttribute("href")) || "";
    for (let attempt = 0; attempt < 3; attempt++) {
      await target.click();
      const arrived = await this.page
        .waitForURL((url) => url.pathname === href, { timeout: 5000 })
        .then(() => true)
        .catch(() => false);
      if (arrived) {
        break;
      }
    }
    // Last resort on a very busy machine: open the address the link points to.
    if (new URL(this.page.url()).pathname !== href) {
      await this.page.goto(href);
    }
    await this.settle();
  }

  async open(url: string): Promise<void> {
    await this.clearCaption();
    await this.page.goto(url);
    await this.settle();
  }

  /** Clicks an item in the "+ New" menu. */
  async newMenu(item: string): Promise<void> {
    await this.clearCaption();
    await this.page.locator("aside").getByRole("button", { name: "New", exact: true }).click();
    await this.pause(700);
    await this.page.getByRole("link", { name: item, exact: true }).click();
    await this.settle();
  }

  // ---------- forms ----------

  dialog(name?: string): Locator {
    return name ? this.page.getByRole("dialog", { name }) : this.page.getByRole("dialog");
  }

  /** The input, select or text area under a form label (the app's Field component). */
  field(label: string, within?: Locator): Locator {
    const scope = within ?? this.page.locator("body");
    const heading = this.page.locator(":scope > span", { hasText: labelPattern(label) });
    return scope.locator("label").filter({ has: heading }).locator("input, select, textarea").first();
  }

  /** A checkbox next to its text, e.g. "This customer is tax exempt". */
  checkbox(text: string | RegExp, within?: Locator): Locator {
    return (within ?? this.page.locator("body")).locator("label", { hasText: text }).locator('input[type="checkbox"]').first();
  }

  async type(label: string, value: string, within?: Locator): Promise<void> {
    await this.typeInto(this.field(label, within), value);
  }

  async typeInto(input: Locator, value: string): Promise<void> {
    await input.click();
    await input.fill("");
    if (this.fast || demoConfig.typingDelayMs === 0 || value.length > 60) {
      await input.fill(value);
    } else {
      await input.pressSequentially(value, { delay: demoConfig.typingDelayMs });
    }
  }

  async choose(label: string, option: string | RegExp, within?: Locator): Promise<void> {
    await this.chooseIn(this.field(label, within), option);
  }

  /** Picks an option by its exact text, or by a pattern (e.g. /Checking/ matches "1000 · Checking"). */
  async chooseIn(select: Locator, option: string | RegExp): Promise<void> {
    if (typeof option === "string") {
      await select.selectOption({ label: option });
    } else {
      const readOptions = () =>
        select.locator("option").evaluateAll((items) => items.map((o) => ({ value: (o as HTMLOptionElement).value, text: o.textContent || "" })));
      // The list may still be loading - wait for a matching option (placeholders have no value).
      await expect.poll(async () => (await readOptions()).some((o) => o.value !== "" && option.test(o.text))).toBe(true);
      const options = await readOptions();
      const match = options.find((o) => o.value !== "" && option.test(o.text));
      if (!match) {
        throw new Error("No option matching " + option + " in: " + options.map((o) => o.text).join(", "));
      }
      await select.selectOption(match.value);
    }
    await this.pause(250);
  }

  /** The select on the page that has an option with this text (for selects without a label). */
  selectWithOption(text: string, within?: Locator): Locator {
    return (within ?? this.page.locator("main")).locator("select", { has: this.page.locator("option", { hasText: text }) }).first();
  }

  /** The id at the end of the current address, e.g. 12 for /sales/invoices/12. */
  idFromUrl(): number {
    return Number(new URL(this.page.url()).pathname.split("/").pop());
  }

  async click(name: string, within?: Locator): Promise<void> {
    await (within ?? this.page.locator("body")).getByRole("button", { name, exact: true }).first().click();
    await this.settle();
  }

  async clickLink(name: string | RegExp, within?: Locator): Promise<void> {
    await (within ?? this.page.locator("main")).getByRole("link", { name, exact: typeof name === "string" }).first().click();
    await this.settle();
  }

  /** A row of a line-items table (0 = first). */
  lineRow(index: number, within?: Locator): Locator {
    return (within ?? this.page.locator("main")).locator("table tbody tr").nth(index);
  }

  /** Fills one line of a sales or purchase line-items table: item, then quantity and rate. */
  async fillLine(index: number, item: string | null, quantity?: string, rate?: string, within?: Locator): Promise<void> {
    const row = this.lineRow(index, within);
    if (item) {
      await this.chooseIn(row.locator("select").first(), item);
    }
    const numbers = row.locator('input[type="number"]');
    if (quantity !== undefined) {
      await this.typeInto(numbers.nth(0), quantity);
    }
    if (rate !== undefined) {
      await this.typeInto(numbers.nth(1), rate);
    }
  }

  async expectText(text: string | RegExp): Promise<void> {
    await expect(this.page.locator("main").getByText(text).first()).toBeVisible();
  }

  async scrollTo(locator: Locator): Promise<void> {
    await locator.scrollIntoViewIfNeeded();
    await this.pause(400);
  }

  async scrollPage(pixels: number): Promise<void> {
    await this.page.mouse.wheel(0, pixels);
    await this.pause(600);
  }

  // ---------- API (for adding many records quickly) ----------

  async api<T = any>(method: "GET" | "POST" | "PUT" | "DELETE", url: string, body?: unknown): Promise<T> {
    const token = await this.page.evaluate((key) => localStorage.getItem(key), appConfig.tokenStorageKey);
    const send = () =>
      this.page.request.fetch(demoConfig.apiUrl + url, {
        method,
        data: body,
        headers: { Authorization: "Bearer " + token },
        timeout: demoConfig.expectTimeoutMs * 4,
      });
    // One retry: reads can always be repeated; writes only when the connection was dropped
    // before the request got through (Docker's port forwarding on Windows sometimes resets one).
    const response = await send().catch((error: Error) => {
      if (method === "GET" || /ECONNRESET|ECONNREFUSED|socket hang up/.test(error.message)) {
        return send();
      }
      throw error;
    });
    if (!response.ok()) {
      throw new Error(method + " " + url + " failed: " + response.status() + " " + (await response.text()));
    }
    return response.status() === 204 ? (undefined as T) : ((await response.json()) as T);
  }

  // ---------- output ----------

  /** Writes the chapter list and a subtitle file next to the video. */
  writeGuides(folder: string, baseName: string): void {
    fs.mkdirSync(folder, { recursive: true });
    const pad = (n: number, w = 2) => String(n).padStart(w, "0");
    const stamp = (ms: number, withMs: boolean) => {
      const total = Math.max(0, ms);
      const h = Math.floor(total / 3600000);
      const m = Math.floor((total % 3600000) / 60000);
      const s = Math.floor((total % 60000) / 1000);
      return pad(h) + ":" + pad(m) + ":" + pad(s) + (withMs ? "." + pad(total % 1000, 3) : "");
    };

    const chapterLines = this.chapters.map((c) => stamp(c.at, false) + "  Chapter " + c.num + " - " + c.title);
    fs.writeFileSync(path.join(folder, baseName + "-chapters.txt"), chapterLines.join("\n") + "\n");

    const cues = ["WEBVTT", ""];
    this.captions.forEach((caption, i) => {
      const end = i + 1 < this.captions.length ? this.captions[i + 1].at : caption.at + 5000;
      cues.push(stamp(caption.at, true) + " --> " + stamp(end, true), caption.text, "");
    });
    fs.writeFileSync(path.join(folder, baseName + ".vtt"), cues.join("\n"));
  }
}
