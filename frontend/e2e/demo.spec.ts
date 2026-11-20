import path from "node:path";
import { test } from "@playwright/test";
import { tourChapters } from "./chapters";
import { demoConfig } from "./demo.config";
import { DemoGuide } from "./support/DemoGuide";

/**
 * The full tour of Ledgerly, start to finish, in one browser session:
 * every chapter builds on the records made by the ones before it.
 * Each step checks its result, so this is also the end-to-end test.
 */
test("Ledgerly - complete tour", async ({ page }) => {
  const guide = await DemoGuide.start(page);

  for (const chapter of tourChapters) {
    await chapter(guide);
  }

  await guide.say("That's the whole tour of Ledgerly. Thanks for watching!");
  await guide.clearCaption();

  if (demoConfig.recordVideo) {
    const folder = path.resolve(__dirname, "..", demoConfig.outputDir);
    guide.writeGuides(folder, "ledgerly-demo");
    const video = page.video();
    await page.close();
    await video?.saveAs(path.join(folder, "ledgerly-demo.webm"));
  }
});
