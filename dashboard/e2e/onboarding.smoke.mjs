import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const BASE_URL = 'http://127.0.0.1:3000';
const headers = { 'Content-Type': 'application/json' };

async function api(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers,
    cache: 'no-store',
    ...options,
  });
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status} ${res.statusText} :: ${text}`);
  }
  return data;
}

async function main() {
  const original = await api('/api/proxy/settings/operational');
  const restore = {
    brand_name: original.brand_name,
    signature_name: original.signature_name,
  };

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    const ready = await api('/api/proxy/setup/readiness');
    assert.equal(ready.overall, 'ready');

    await page.goto(`${BASE_URL}/onboarding`, { waitUntil: 'networkidle' });
    await page.getByRole('button', { name: /Ejecutar/i }).first().click();
    await page.waitForTimeout(750);
    await page.getByText(/Podés volver a pedir readiness/i).waitFor({ timeout: 10000 });

    await api('/api/proxy/settings/operational', {
      method: 'PATCH',
      body: JSON.stringify({ brand_name: null, signature_name: null }),
    });

    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
    await page.waitForURL(/\/onboarding(\?|$)/, { timeout: 10000 });
    await page.getByText(/Onboarding profesional/i).waitFor({ timeout: 10000 });
    await page.goto(`${BASE_URL}/settings`, { waitUntil: 'networkidle' });
    await page.getByText(/Onboarding profesional pendiente/i).waitFor({ timeout: 10000 });

    await page.goto(`${BASE_URL}/onboarding`, { waitUntil: 'networkidle' });
    await page.getByPlaceholder('ej. BriarDev').fill(restore.brand_name ?? 'Scouter E2E');
    await page.getByPlaceholder('ej. Mateo').fill(restore.signature_name ?? 'Mateo E2E');
    await page.getByRole('button', { name: /^Guardar$/i }).click();
    await page.waitForTimeout(1200);

    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
    assert.equal(new URL(page.url()).pathname, '/');
    await page.getByText(/Agente IA · Scouter/i).waitFor({ timeout: 10000 });

    const finalReadiness = await api('/api/proxy/setup/readiness');
    assert.equal(finalReadiness.dashboard_unlocked, true);

    console.log('E2E onboarding smoke: PASS');
  } finally {
    try {
      await api('/api/proxy/settings/operational', {
        method: 'PATCH',
        body: JSON.stringify(restore),
      });
    } catch (err) {
      console.error('restore failed', err);
    }
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
