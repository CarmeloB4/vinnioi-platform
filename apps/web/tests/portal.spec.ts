import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { readFileSync, existsSync, mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
const towns = JSON.parse(readFileSync('src/data/municipalities.json', 'utf8'));
const slug = (s: string) =>
  s
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-');
test('navigazione, ricerca comune e filtri', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Modalità demo.', { exact: true })).toBeVisible();
  await page.getByLabel('Cerca un comune', { exact: true }).fill('Canicattì');
  await page.getByRole('button', { name: 'Cerca', exact: true }).click();
  await expect(page.locator('#town-list a:visible')).toHaveCount(1);
  await page.locator('#town-list a:visible').click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Canicattì');
  await page.goto('/dashboard/');
  await page.getByLabel('Comune', { exact: true }).selectOption('084041');
  await expect(page.locator('[data-event-id]:visible')).toHaveCount(1);
  await page.getByLabel('Fonte', { exact: true }).selectOption('siciliacque');
  await expect(page.locator('#filter-empty')).toBeVisible();
  await page.getByRole('button', { name: 'Azzera filtri' }).click();
  await expect(page.locator('[data-event-id]:visible')).toHaveCount(3);
});
test('tutti i 43 percorsi comunali sono presenti nella build', async ({ request }) => {
  for (const town of towns) {
    const response = await request.get('/comuni/' + slug(town.municipality) + '/');
    expect(response.status()).toBe(200);
    expect(await response.text()).toContain(town.municipality_istat_code);
  }
});
test('schede distinguono previsti, lavori completati e ripristini dichiarati', async ({ page }) => {
  await page.goto('/eventi/demo-programmato-sciacca/');
  await expect(page.getByText('Ripristino previsto', { exact: true })).toBeVisible();
  await page.goto('/interventi/demo-lavoro-completato-agrigento/');
  await expect(page.getByText(/Stato del lavoro: COMPLETATO/)).toBeVisible();
});
test('produzione senza dati non include fixture o download demo', async ({ page, request }) => {
  await page.goto('http://127.0.0.1:4174/');
  await expect(page.locator('body')).toHaveAttribute('data-mode', 'production');
  await expect(page.getByText('Stiamo preparando i primi dati pubblicabili')).toBeVisible();
  expect(await page.content()).not.toContain('Ripristino sintetico');
  expect(existsSync('dist/api/demo-events.json')).toBe(false);
  expect(existsSync('dist/eventi/demo-programmato-sciacca/index.html')).toBe(false);
  const sitemap = await request.get('http://127.0.0.1:4174/sitemap.xml');
  expect((await sitemap.text()).match(/\/comuni\//g)?.length).toBe(44);
});
test('mappa: selezione accessibile e caricamento senza servizi esterni', async ({ page }) => {
  await page.goto('/mappa/');
  await page.getByLabel('Seleziona un comune').selectOption('084021');
  await expect(page.locator('#map-status')).toContainText('Licata');
  await page.getByRole('button', { name: 'Attiva mappa interattiva' }).click();
  await expect(page.locator('#map-status')).not.toContainText('Caricamento della mappa…', {
    timeout: 15000,
  });
  await expect(page.locator('#map canvas')).toBeVisible();
  await expect(page.locator('#map-status')).toContainText('Licata');
  await expect(page.locator('#map-alternative a')).toHaveCount(43);
});
test('accessibilità automatica sui percorsi principali', async ({ page }) => {
  for (const path of [
    '/',
    '/dashboard/',
    '/comuni/',
    '/comuni/licata/',
    '/mappa/',
    '/opendata/',
    '/metodologia/',
  ]) {
    await page.goto(path);
    const result = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'])
      .analyze();
    expect(result.violations, JSON.stringify(result.violations, null, 2)).toEqual([]);
  }
});
test('mobile, tastiera e screenshot', async ({ page }) => {
  const folder = resolve('../../docs/screenshots');
  mkdirSync(folder, { recursive: true });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('/');
  await page.screenshot({ path: resolve(folder, 'phase4-demo-desktop.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Menu', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Menu', exact: true }).click();
  await expect(page.getByRole('link', { name: 'Dashboard', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Menu', exact: true }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: resolve(folder, 'phase4-demo-mobile.png'), fullPage: true });
  await page.goto('http://127.0.0.1:4174/');
  await page.screenshot({ path: resolve(folder, 'phase4-production-mobile.png'), fullPage: true });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: resolve(folder, 'phase4-production-desktop.png'), fullPage: true });
  await page.goto('/');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Vai al contenuto' })).toBeFocused();
});

test('errore geometrie conserva elenco e possibilità di riprovare', async ({ page }) => {
  await page.route('**/data/municipalities.geojson', (route) =>
    route.fulfill({ status: 503, body: '' }),
  );
  await page.goto('/mappa/');
  await page.getByRole('button', { name: 'Attiva mappa interattiva' }).click();
  await expect(page.locator('#map-status')).toContainText('non è disponibile');
  await expect(page.getByRole('button', { name: 'Riprova a caricare la mappa' })).toBeEnabled();
  await expect(page.locator('#map-alternative a')).toHaveCount(43);
});
