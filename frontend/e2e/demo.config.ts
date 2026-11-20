/**
 * Central settings for the end-to-end tour and demo video.
 * Every value can be changed with an environment variable - nothing else in e2e/ is hardcoded.
 */

const env = process.env;
// "npm run demo:video" (or DEMO_VIDEO=1) records the slow, captioned video; "npm run e2e" just tests.
const videoMode = env.DEMO_VIDEO === "1" || env.npm_lifecycle_event === "demo:video";

export const demoConfig = {
  // Where the app runs. Docker: http://localhost:3000 and http://localhost:8000/api/v1
  baseUrl: env.E2E_BASE_URL || "http://localhost:3000",
  apiUrl: env.E2E_API_URL || "http://localhost:8000/api/v1",

  // Video mode is slow and captioned for people to watch; test mode runs fast.
  recordVideo: videoMode,
  slowMoMs: Number(env.DEMO_SLOWMO_MS ?? (videoMode ? 250 : 0)),
  // Captions stay on screen this long per word (plus a minimum), so viewers can read them.
  readingMsPerWord: Number(env.DEMO_READING_MS_PER_WORD ?? (videoMode ? 330 : 0)),
  minReadingMs: Number(env.DEMO_MIN_READING_MS ?? (videoMode ? 1800 : 0)),
  chapterCardMs: Number(env.DEMO_CHAPTER_CARD_MS ?? (videoMode ? 2600 : 0)),
  // Delay between typed characters, so typing is visible in the video.
  typingDelayMs: Number(env.DEMO_TYPING_DELAY_MS ?? (videoMode ? 35 : 0)),
  viewport: { width: Number(env.DEMO_WIDTH ?? 1440), height: Number(env.DEMO_HEIGHT ?? 900) },

  // Only run chapters from this number on (for working on one chapter). The earlier ones still run, fast.
  watchFromChapter: Number(env.DEMO_WATCH_FROM ?? 1),

  testTimeoutMs: Number(env.E2E_TIMEOUT_MS ?? (videoMode ? 90 : 20) * 60 * 1000),
  expectTimeoutMs: Number(env.E2E_EXPECT_TIMEOUT_MS ?? 15000),

  // Where the finished video, chapter list and subtitles are saved.
  outputDir: env.DEMO_OUTPUT_DIR || "../demo-video",

  // The demo company. A new account is created on every run (the email gets a timestamp).
  company: {
    owner: "Sam Rivera",
    name: "Greenleaf Landscaping",
    emailDomain: env.DEMO_EMAIL_DOMAIN || "example.com",
    phone: "(555) 010-2030",
    address: "120 Maple Street\nSpringfield, IL 62701",
    website: "https://greenleaf.example.com",
  },
};
