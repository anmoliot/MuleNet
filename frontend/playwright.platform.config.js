import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testMatch: "platform.spec.js",
  workers: 1,
  retries: 0,
  timeout: 60000,
  outputDir: "../.tools/platform-browser",
  reporter: [
    ["list"],
    ["json", { outputFile: "../reports/frontend-browser-tests.json" }],
  ],
  use: {
    baseURL: process.env.PLATFORM_UI_URL,
    browserName: "chromium",
    channel: process.env.PLATFORM_BROWSER_CHANNEL || undefined,
    screenshot: "only-on-failure",
    trace: "off",
    reducedMotion: "reduce",
  },
  projects: [
    { name: "desktop", use: { viewport: { width: 1440, height: 1000 } } },
    {
      name: "mobile",
      use: {
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
});
