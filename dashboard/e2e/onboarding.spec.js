const { test, expect } = require('@playwright/test');
const { spawnSync } = require('node:child_process');

const browserDepsReady = spawnSync('bash', ['-lc', 'ldconfig -p | grep libnspr4 >/dev/null']).status === 0;

async function expectOkJson(response) {
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json();
}

test.skip(!browserDepsReady, 'Missing browser system dependencies for Chromium');

test('real onboarding flow locks and unlocks dashboard', async ({ page, request }) => {
  const original = await expectOkJson(await request.get('/api/proxy/settings/operational'));
  const restore = {
    brand_name: original.brand_name,
    signature_name: original.signature_name,
  };

  try {
    const initialReadiness = await expectOkJson(await request.get('/api/proxy/setup/readiness'));
    expect(initialReadiness.dashboard_unlocked).toBeTruthy();

    await page.goto('/onboarding');
    await page.getByRole('button', { name: /Ejecutar/i }).first().click();
    await expect(page.getByText(/Podés volver a pedir readiness/i)).toBeVisible({ timeout: 15000 });

    await expectOkJson(
      await request.patch('/api/proxy/settings/operational', {
        data: { brand_name: null, signature_name: null },
      })
    );

    await page.goto('/');
    await page.waitForURL(/\/onboarding(\?|$)/, { timeout: 15000 });
    await expect(page.getByText(/Onboarding profesional/i)).toBeVisible();

    await page.goto('/settings');
    await expect(page.getByText(/Onboarding profesional pendiente/i)).toBeVisible();

    await page.goto('/onboarding');
    await page.getByPlaceholder('ej. BriarDev').fill(restore.brand_name ?? 'Scouter E2E');
    await page.getByPlaceholder('ej. Mateo').fill(restore.signature_name ?? 'Mateo E2E');
    await page.getByRole('button', { name: /^Guardar$/i }).click();

    await expect
      .poll(async () => {
        const readiness = await expectOkJson(await request.get('/api/proxy/setup/readiness'));
        return readiness.dashboard_unlocked;
      }, { timeout: 15000 })
      .toBeTruthy();

    await page.goto('/');
    await expect(page).toHaveURL('http://127.0.0.1:3000/');
    await expect(page.getByText(/Agente IA · Scouter/i)).toBeVisible({ timeout: 15000 });
  } finally {
    await expectOkJson(
      await request.patch('/api/proxy/settings/operational', {
        data: restore,
      })
    );
  }
});
