import path from "node:path";
import { test } from "@playwright/test";
import { tourChapters } from "./chapters";
import { demoConfig } from "./demo.config";
import { DemoGuide } from "./support/DemoGuide";
import { appConfig } from "../src/config/app.config";

/**
 * The full tour of the app, start to finish, in one browser session:
 * every chapter builds on the records made by the ones before it.
 * Each step checks its result, so this is also the end-to-end test.
 */
test(`${appConfig.appName} - complete tour`, async ({ page }) => {
  const guide = await DemoGuide.start(page);

  for (const chapter of tourChapters) {
    await chapter(guide);
  }

  await guide.say(`That's the whole tour of ${appConfig.appName}. Thanks for watching!`);
  await guide.clearCaption();

  if (demoConfig.recordVideo) {
    const folder = path.resolve(__dirname, "..", demoConfig.outputDir);
    guide.writeGuides(folder, "digibooks-demo");
    const video = page.video();
    await page.close();
    await video?.saveAs(path.join(folder, "digibooks-demo.webm"));
  }
});
