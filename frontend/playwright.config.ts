import { defineConfig } from "@playwright/test";
import { demoConfig } from "./e2e/demo.config";

/**
 * End-to-end tests. The demo tour (e2e/demo.spec.ts) walks through every
 * part of Ledgerly in a real browser, checks the results, and records a video.
 *
 *   npm run e2e          - run the tour (needs the app running, e.g. docker compose up -d)
 *   npm run demo:video   - same, slowed down with captions, and saves the video
 */
export default defineConfig({
  testDir: "e2e",
  outputDir: "e2e-results/artifacts",
  timeout: demoConfig.testTimeoutMs,
  expect: { timeout: demoConfig.expectTimeoutMs },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: demoConfig.baseUrl,
    viewport: demoConfig.viewport,
    video: demoConfig.recordVideo ? { mode: "on", size: demoConfig.viewport } : "off",
    actionTimeout: demoConfig.expectTimeoutMs,
    navigationTimeout: demoConfig.expectTimeoutMs * 2,
    screenshot: "only-on-failure",
    // A trace of a 20-minute recording is huge, so traces are only kept in test mode.
    trace: demoConfig.recordVideo ? "off" : "retain-on-failure",
    launchOptions: { slowMo: demoConfig.slowMoMs },
  },
});
