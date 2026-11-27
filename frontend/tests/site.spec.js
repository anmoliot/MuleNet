import { test, expect } from '@playwright/test';
import { APCAcontrast, sRGBtoY } from 'apca-w3';
import { writeFile, mkdir, readFile } from 'node:fs/promises';

async function ready(page) {
  await page.goto('/');
  await expect(page.locator('.hero-proof .metrics')).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
}

test('complete page, source-derived metrics, font/assets, layout and screenshots', async ({ page }, info) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await ready(page);
  await expect(page).toHaveTitle('MuleNet | Follow the evidence');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('MuleNet');
  const evidence = await (await page.request.get('/evidence.json')).json();
  expect(evidence.data_provenance).toBe('synthetic');
  expect(evidence).toEqual(JSON.parse(await readFile(new URL('../../reports/site-evidence.json', import.meta.url), 'utf8')));
  await expect(page.locator('.hero-proof .metric').first()).toContainText(evidence.paysim.pr_auc.value.toFixed(4));
  expect(await page.locator('main > section').count()).toBe(8);
  expect(await page.locator('.stack-marks > span').count()).toBe(6);
  expect(await page.locator('.feature-row').count()).toBe(3);
  expect(await page.locator('.questions details').count()).toBe(6);
  const geometry = await page.evaluate(() => ({
    page: document.documentElement.scrollWidth,
    viewport: innerWidth,
    fonts: document.fonts.check('500 72px "IBM Plex Sans"') && document.fonts.check('400 16px "IBM Plex Mono"'),
    images: [...document.images].filter(image => image.getBoundingClientRect().width > 0).map(image => ({ loaded: image.complete && image.naturalWidth > 0, shown: image.width, native: image.naturalWidth })),
    overflowing: [...document.querySelectorAll('h1,h2,h3,.action,.metric,.wordmark,.section-heading,.stack-marks > span')].filter(node => node.scrollWidth > node.clientWidth + 1).map(node => node.textContent),
    heroCollision: (() => { const a = document.querySelector('.hero-copy').getBoundingClientRect(); const b = document.querySelector('.hero-graph').getBoundingClientRect(); return a.right > b.left + 2 && a.top < b.bottom && b.top < a.bottom; })(),
  }));
  expect(geometry.page).toBeLessThanOrEqual(geometry.viewport + 1);
  expect(geometry.fonts).toBe(true);
  expect(geometry.images.every(image => image.loaded && image.shown <= image.native)).toBe(true);
  expect(geometry.overflowing).toEqual([]);
  expect(geometry.heroCollision).toBe(false);
  expect(errors).toEqual([]);
  await page.screenshot({ path: info.outputPath('opening.png'), fullPage: false });
  await page.screenshot({ path: info.outputPath('full-page.png'), fullPage: true });
});

test('navigation, dialogs, feature boundary, evidence switch and independent FAQs', async ({ page }, info) => {
  await ready(page);
  if (info.project.use.viewport.width <= 800) {
    const toggle = page.locator('.menu-toggle');
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
    await page.getByRole('navigation').getByRole('link', { name: 'Product', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Open navigation', exact: true })).toHaveAttribute('aria-expanded', 'false');
  }
  await page.locator('.hero-actions').getByRole('button', { name: 'Explore the project' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(page.locator('.hero-actions button')).toBeFocused();
  await page.getByRole('button', { name: 'Expand illustrative evidence graph' }).click();
  if (info.project.use.viewport.width < 1000) {
    const diagram = page.getByRole('region', { name: 'Illustrative transfer graph' });
    expect(await diagram.evaluate(node => node.scrollWidth > node.clientWidth)).toBe(true);
    await diagram.focus();
    await page.keyboard.press('ArrowRight');
  }
  await page.getByRole('button', { name: 'Review', exact: true }).click();
  await expect(page.locator('.review-explanation')).toContainText('This illustration does not hold money');
  await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
  const slider = page.getByRole('slider', { name: 'As-of point' });
  await slider.focus();
  await page.keyboard.press('Home');
  await expect(page.locator('.is-future')).toHaveCount(2);
  await page.keyboard.press('End');
  await expect(page.locator('.is-future')).toHaveCount(0);
  await page.getByRole('button', { name: 'Account simulator', exact: true }).click();
  await expect(page.locator('.split-results')).toContainText('0.00%');
  await page.getByRole('button', { name: 'PaySim', exact: true }).click();
  await expect(page.locator('.evidence-tool .metric small').first()).toContainText('95% CI');
  await page.locator('.questions summary').nth(0).click();
  await page.locator('.questions summary').nth(1).click();
  await expect(page.locator('.questions details[open]')).toHaveCount(2);
  const brokenAnchors = await page.locator('a[href^="#"]').evaluateAll(links => links.map(link => link.getAttribute('href')).filter(href => href !== '#' && !document.getElementById(href.slice(1))));
  expect(brokenAnchors).toEqual([]);
});

test('evidence error does not substitute fabricated values, retry recovers', async ({ page }) => {
  await page.route('**/evidence.json', route => route.fulfill({ status: 503, body: 'Unavailable' }));
  await page.goto('/');
  await expect(page.locator('.hero-proof')).toContainText('No substitute metrics');
  await expect(page.locator('.hero-proof .metric')).toHaveCount(0);
  await expect(page.getByText('Evidence could not be loaded. No substitute figures are shown.')).toBeVisible();
  await page.unroute('**/evidence.json');
  await page.getByRole('button', { name: 'Retry loading' }).click();
  await expect(page.locator('.hero-proof .metrics')).toBeVisible();
});

test('rendered WCAG 2 and APCA pairings recorded separately', async ({ page }, info) => {
  await ready(page);
  const inspect = () => {
    const rgb = color => (color.match(/[\d.]+/g) || []).map(Number);
    const over = (fg, bg) => { const alpha = fg[3] ?? 1; return [0, 1, 2].map(i => fg[i] * alpha + bg[i] * (1 - alpha)); };
    const bgAt = node => {
      const chain = [];
      for (let current = node; current; current = current.parentElement) chain.unshift(current);
      return chain.reduce((bg, element) => over(rgb(getComputedStyle(element).backgroundColor), bg), [255, 255, 255]);
    };
    const result = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let text;
    while ((text = walker.nextNode())) {
      if (!text.textContent.trim()) continue;
      const parent = text.parentElement;
      if (['SCRIPT', 'STYLE'].includes(parent.tagName)) continue;
      if (document.querySelector('dialog[open]') && !parent.closest('dialog[open]')) continue;
      const range = document.createRange();
      range.selectNodeContents(text);
      if (!range.getBoundingClientRect().width || !range.getBoundingClientRect().height) continue;
      const style = getComputedStyle(parent);
      if (style.visibility === 'hidden') continue;
      const background = bgAt(parent);
      const foreground = over(rgb(style.color), background);
      result.push({ text: text.textContent.trim(), foreground, background, size: parseFloat(style.fontSize), weight: Number(style.fontWeight), control: !!parent.closest('a,button,summary,label,.tool-caption,.eyebrow,.sample-badge,.graph-legend,.path-label') });
    }
    return result;
  };
  const readings = (await page.evaluate(inspect)).map(reading => ({ ...reading, state: 'initial' }));
  const capture = async state => readings.push(...(await page.evaluate(inspect)).map(reading => ({ ...reading, state })));
  await page.locator('.hero-actions button').hover();
  await capture('primary-hover');
  await page.locator('.hero-actions button').click();
  await capture('setup-dialog');
  await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
  await page.getByRole('button', { name: 'Expand illustrative evidence graph' }).click();
  await page.getByRole('button', { name: 'Review', exact: true }).click();
  await capture('graph-review-dialog');
  await page.getByRole('button', { name: 'Close dialog', exact: true }).click();
  await page.getByRole('button', { name: 'Account simulator', exact: true }).click();
  await page.locator('.questions summary').first().click();
  await capture('simulator-and-expanded-faq');
  function luminance(rgb) {
    const [r, g, b] = rgb.map(value => { const c = value / 255; return c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4; });
    return .2126 * r + .7152 * g + .0722 * b;
  }
  const measured = readings.map(reading => {
    const a = luminance(reading.foreground), b = luminance(reading.background);
    const wcag = (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
    const apca = Math.abs(APCAcontrast(sRGBtoY(reading.foreground), sRGBtoY(reading.background)));
    const wcagFloor = reading.size >= 24 || reading.size >= 18.66 && reading.weight >= 700 ? 3 : 4.5;
    const apcaFloor = reading.size >= 40 ? 45 : reading.size >= 24 || reading.control ? 60 : 75;
    return { ...reading, wcag, wcagFloor, apca, apcaFloor, pass: wcag >= wcagFloor && apca >= apcaFloor };
  });
  await mkdir(new URL('../../reports/site-contrast/', import.meta.url), { recursive: true });
  const distinct = [...new Map(measured.map(reading => [JSON.stringify([reading.text, reading.foreground, reading.background, reading.size, reading.weight, reading.state]), reading])).values()];
  await writeFile(new URL(`../../reports/site-contrast/${info.project.name}.json`, import.meta.url), JSON.stringify({ instruments: ['WCAG 2 relative luminance ratio', 'APCA-W3 Lc absolute'], scope: 'Computed HTML text pairings on flat backgrounds in initial, hover, dialog, selected-evidence and expanded-FAQ states. Raster diagram labels are visually inspected, not contrast-certified. This is not a full accessibility certification.', measured: distinct }, null, 2));
  expect(measured.filter(reading => !reading.pass)).toEqual([]);
});
