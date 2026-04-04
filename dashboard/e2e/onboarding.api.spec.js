const { test, expect } = require('@playwright/test');

async function expectOkJson(response) {
  expect(response.ok(), await response.text()).toBeTruthy();
  return response.json();
}

test('request-level onboarding flow locks and unlocks dashboard', async ({ request }) => {
  const original = await expectOkJson(await request.get('/api/proxy/settings/operational'));
  const restore = {
    brand_name: original.brand_name,
    signature_name: original.signature_name,
  };

  try {
    const initial = await expectOkJson(await request.get('/api/proxy/setup/readiness'));
    expect(initial.dashboard_unlocked).toBeTruthy();

    await expectOkJson(
      await request.patch('/api/proxy/settings/operational', {
        data: { brand_name: null, signature_name: null },
      })
    );

    const locked = await expectOkJson(await request.get('/api/proxy/setup/readiness'));
    expect(locked.dashboard_unlocked).toBeFalsy();
    expect(locked.overall).toBe('config_required');
    expect(locked.wizard_steps).toContain('brand');

    await expectOkJson(
      await request.patch('/api/proxy/settings/operational', {
        data: restore,
      })
    );

    await expect
      .poll(async () => {
        const restored = await expectOkJson(await request.get('/api/proxy/setup/readiness'));
        return restored.dashboard_unlocked;
      }, { timeout: 15000 })
      .toBeTruthy();
  } finally {
    await expectOkJson(
      await request.patch('/api/proxy/settings/operational', {
        data: restore,
      })
    );
  }
});
