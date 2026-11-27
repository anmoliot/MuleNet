import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: 'site.spec.js',
  outputDir: '../.tools/site-browser',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['json', { outputFile: '../reports/site-browser-tests.json' }]],
  use: {
    baseURL: process.env.SITE_BASE_URL || 'http://127.0.0.1:5174',
    browserName: 'chromium',
    channel: process.env.SITE_BROWSER_CHANNEL || undefined,
    reducedMotion: 'reduce',
    screenshot: 'only-on-failure',
    trace: 'off',
  },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1440, height: 1000 } } },
    { name: 'mobile', use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
    { name: 'narrow', use: { viewport: { width: 320, height: 740 }, isMobile: true, hasTouch: true } },
    { name: 'tablet', use: { viewport: { width: 768, height: 1024 } } },
    { name: 'wide', use: { viewport: { width: 1920, height: 1080 } } },
  ],
});
