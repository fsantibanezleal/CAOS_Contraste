// The story smoke of Contraste (ADR-0082, SHOW-1; modelled on the template's check_story_mode.mjs): the five steps of
// /story/<step> on a built site. Every step is directly linked; the five views are distinct; the headline numbers equal the
// committed artifacts; the scene and the panel are one selection both ways; the day cursor and the model are kept from step to
// step; play stops on the reader's input; the window selector changes the data; the exit lands on the route it came from;
// reduced motion shortens the stage motion; the phone keeps the panel below the stage, three callouts and no horizontal overflow.
//   node scripts/check_story_mode.mjs [<base url>]     (without a URL it serves dist/ as GitHub Pages does)
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { createServer } from 'node:net';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const here = dirname(fileURLToPath(import.meta.url));
const derived = join(here, '..', '..', 'data', 'derived');
const read = (rel) => JSON.parse(readFileSync(join(derived, rel), 'utf8'));
const STEPS = ['inventory', 'backtest', 'crisis', 'recalibrate', 'decide'];
const VIEWS = { inventory: '[data-flow]', backtest: '[data-traffic-light]', crisis: '[data-crisis]', recalibrate: '[data-recalibration]', decide: '[data-decision]' };

// what the artifacts say, read here independently of the page
const findings = read('governance/findings.json');
const inventory = read('governance/inventory.json');
const window2007 = read('C11/equity-2007-09.json');
const hs = window2007.outputs.models.find((m) => m.model_id === 'hs-250').by_level.find((l) => l.alpha === 0.01);
const garch = window2007.outputs.models.find((m) => m.model_id === 'garch-t').by_level.find((l) => l.alpha === 0.01);
const wrapped = window2007.outputs.conformal.rows.find((r) => r.model_id === 'hs-250' && r.alpha === 0.01);
const mcs = window2007.outputs.comparison.mcs.find((s) => s.alpha === 0.01);
// the findings still carried: the register's rows not closed by validation (the inventory holds entries, not models)
const carried = (severity) => findings.rows.filter((r) => r.severity === severity && r.status !== 'validated_closed').length;
// the one colour rule of a breach count: against the count its level expects (green at or below it, amber above, red above twice it)
const breachState = (count, expectedCount) => { const ratio = expectedCount > 0 ? count / expectedCount : 0; return ratio > 2 ? 'alarm' : ratio > 1 ? 'warning' : 'normal'; };
const expected = {
  inventory: `${inventory.entries.length} inventory entries carry ${carried('S1')} critical and ${carried('S2')} significant findings`,
  backtest: `Historical simulation, 250 days: ${hs.traffic_light.final_rolling_exceedances} exceptions, ${hs.traffic_light.final_zone === 'amber' ? 'amber' : hs.traffic_light.final_zone} zone`,
  crisis: `Historical simulation, 250 days: ${hs.n_exceedances} VaR breaches in ${hs.n_scored} days`,
  recalibrate: `Recalibration cuts breaches from ${wrapped.unwrapped.n_exceedances} to ${wrapped.wrapped.n_exceedances}; ${Math.round(wrapped.wrapped.expected_exceedances)} were expected`,
  decide: `Gates pass ${window2007.impact.eligible_models.value} of ${window2007.outputs.models.length} models; the confidence set keeps ${mcs.members.filter((m) => m.in_set).length}`,
};

let serverProcess;
let base = process.argv[2] ? process.argv[2].replace(/\/+$/, '') : null;
if (!base) {
  const portServer = createServer();
  await new Promise((resolve, reject) => { portServer.once('error', reject); portServer.listen(0, '127.0.0.1', resolve); });
  const address = portServer.address();
  if (!address || typeof address === 'string') throw new Error('Could not allocate the story smoke server port');
  const port = address.port;
  await new Promise((resolve) => portServer.close(resolve));
  base = `http://127.0.0.1:${port}`;
  serverProcess = spawn(process.execPath, ['scripts/serve.mjs', '--port', String(port)], { cwd: process.cwd(), stdio: 'ignore' });
  let ready = false;
  for (let attempt = 0; attempt < 60; attempt += 1) {
    if (serverProcess.exitCode !== null) throw new Error(`Story smoke server exited with ${serverProcess.exitCode}`);
    try { const response = await fetch(base); if (response.ok) { ready = true; break; } } catch { /* wait for startup */ }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  if (!ready) { serverProcess.kill(); throw new Error('Story smoke server did not become ready'); }
}

const errors = [];
const browser = await chromium.launch({ headless: true });
const watch = (page) => {
  page.on('pageerror', (error) => errors.push(error.message));
  page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()); });
};
const headline = (page) => page.locator('[data-story-headline]').innerText();
const goStep = async (page, step) => {
  await page.locator(`[data-story-link="${step}"]`).click();
  await page.locator(`[data-story-step="${step}"]`).waitFor({ state: 'visible', timeout: 15000 });
  await page.locator(VIEWS[step]).waitFor({ state: 'visible', timeout: 15000 });
};
try {
  const desktop = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  watch(desktop);
  const from = '/app?case=C11&view=variants&focus=1';
  await desktop.goto(`${base}/story/inventory?window=equity-2007-09&model=hs-250&from=${encodeURIComponent(from)}`, { waitUntil: 'domcontentloaded' });
  await desktop.locator('[data-story-step="inventory"]').waitFor({ state: 'visible', timeout: 15000 });
  await desktop.locator(VIEWS.inventory).waitFor({ state: 'visible', timeout: 15000 });

  // every step directly linked, the views distinct, each headline the artifacts' number
  assert.equal(await desktop.locator('[data-story-link]').count(), 5, 'five directly linked story steps');
  for (const step of STEPS) {
    await goStep(desktop, step);
    for (const other of STEPS) assert.equal(await desktop.locator(VIEWS[other]).count(), other === step ? 1 : 0, `step ${step} draws its own view only (${other})`);
    assert.equal(await headline(desktop), expected[step], `the ${step} headline is the artifacts' number`);
    assert.equal(await desktop.locator('[data-caos-callout]').count(), 3, `${step} carries three anchored callouts`);
  }

  // the colour of a count is the one rule of its number: the recalibrated 11 against 5.04 expected is red, as the raw 19 is
  await goStep(desktop, 'recalibrate');
  assert.equal(await desktop.locator('[data-caos-callout="with"]').getAttribute('data-callout-state'), breachState(wrapped.wrapped.n_exceedances, wrapped.wrapped.expected_exceedances), 'the recalibrated count takes the colour of its ratio to the expected count');
  assert.equal(await desktop.locator('[data-caos-callout="without"]').getAttribute('data-callout-state'), breachState(wrapped.unwrapped.n_exceedances, wrapped.wrapped.expected_exceedances), 'the raw count takes the same rule');
  assert.equal(await desktop.locator('[data-caos-callout="with"]').getAttribute('data-callout-state'), 'alarm', 'eleven breaches against five expected are not green');
  const panelText = await desktop.locator('[data-panel="recalibration"]').innerText();
  assert.ok(!/equity-2007-09/.test(panelText), 'the panel names the window in words, never by its id');
  assert.ok(/accept recalibrated runs too easily/.test(panelText) && /upper bound/.test(panelText), 'the panel says the back-tests accept recalibrated runs too easily');
  assert.equal(await desktop.locator('[data-path="working-level"]').count(), 1, 'the working tail level is drawn');
  // a model that never entered the confidence set is not tested, never out
  await goStep(desktop, 'decide');
  const unranked = mcs ? window2007.outputs.models.filter((m) => !mcs.members.some((x) => x.model_id === m.model_id)).map((m) => m.model_id) : [];
  assert.ok(unranked.length >= 1, 'the window has models the set never ranked');
  for (const id of unranked) assert.equal(await desktop.locator(`[data-decision-row="${id}"] [data-set-state]`).getAttribute('data-set-state'), 'not-tested', `${id} is not tested by the set`);
  assert.ok(!/\bout\b/.test(await desktop.locator(`[data-decision-row="${unranked[0]}"]`).textContent()), 'a model the set never ranked is not marked out');

  // the scene and the panel are one selection, both ways (step 1: the families)
  await goStep(desktop, 'inventory');
  await desktop.locator('[data-linked-view="scene"][data-linked-id="family:scoring"]').click();
  assert.equal(await desktop.locator('[data-linked-view="panel"][data-linked-id="family:scoring"]').getAttribute('data-linked-selected'), 'true', 'a family chosen in the flow is chosen in the panel');
  assert.match(await desktop.locator('.story-evidence h2').innerText(), /PD scoring/);
  await desktop.locator('[data-linked-view="panel"][data-linked-id="family:liquidity"]').click();
  assert.equal(await desktop.locator('[data-linked-view="scene"][data-linked-id="family:liquidity"]').getAttribute('data-linked-selected'), 'true', 'a family chosen in the panel is chosen in the flow');
  const marketNode = await desktop.locator('[data-flow-node="family:market"]').textContent();
  assert.match(marketNode, /Red|Amber|Green/, 'the market node carries the Basel zone of the shared day');

  // the shared day cursor: set at the flow, kept by the light, the crisis and the recalibration
  const slider = desktop.getByRole('slider', { name: 'Move the shared day' });
  await slider.evaluate((el) => { const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; set.call(el, '123'); el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); });
  for (const step of ['backtest', 'crisis', 'recalibrate']) {
    await goStep(desktop, step);
    assert.equal(await desktop.getByRole('slider', { name: 'Move the shared day' }).inputValue(), '123', `the shared day is kept at ${step}`);
    const marks = await desktop.locator('[data-linked-cursor-marker]').evaluateAll((els) => els.map((el) => el.getAttribute('data-linked-cursor-position')));
    assert.ok(marks.length >= 1 && marks.every((m) => m === '123'), `every marker of ${step} sits on the shared day`);
  }

  // the model chosen in the panel is chosen in the scene, and kept to the next step
  await goStep(desktop, 'backtest');
  await desktop.locator('[data-linked-view="panel"][data-linked-id="model:garch-t"]').click();
  assert.equal(await desktop.locator('[data-linked-view="scene"][data-linked-id="model:garch-t"]').getAttribute('data-linked-selected'), 'true', 'a model chosen in the panel is chosen in the drawing');
  await goStep(desktop, 'crisis');
  assert.match(await desktop.locator('.story-evidence h2').innerText(), /GARCH/, 'the model is kept at the crisis');
  assert.equal(await headline(desktop), `GARCH(1,1): ${garch.n_exceedances} VaR breaches in ${garch.n_scored} days`);
  await desktop.locator('[data-linked-view="panel"][data-linked-id="model:hs-250"]').click();
  await goStep(desktop, 'decide');
  await desktop.locator('[data-linked-view="scene"][data-linked-id="model:ewma"]').click();
  assert.equal(await desktop.locator('[data-linked-view="panel"][data-linked-id="model:ewma"]').getAttribute('data-linked-selected'), 'true', 'a row chosen in the decision is chosen in the panel');

  // the window selector reaches every step: a window shorter than 250 days has no Basel light and says so
  await desktop.locator('.story-window select').selectOption('mixed-2023');
  await desktop.waitForURL((url) => url.searchParams.get('window') === 'mixed-2023');
  await goStep(desktop, 'backtest');
  assert.match(await desktop.locator('[data-traffic-light]').textContent(), /Not evaluated: the light needs 250 days, the window has 64/);
  await desktop.locator('.story-window select').selectOption('equity-2007-09');
  await desktop.waitForURL((url) => url.searchParams.get('window') === 'equity-2007-09');

  // play stops on the reader's input; reduced motion shortens the stage motion
  const play = desktop.locator('[data-story] button[aria-pressed]').first();
  await play.click();
  assert.equal(await play.getAttribute('aria-pressed'), 'true');
  await desktop.locator('[data-story-link="crisis"]').click();
  assert.equal(await desktop.locator('[data-story] button[aria-pressed]').first().getAttribute('aria-pressed'), 'false', 'reader interaction pauses playback');
  await desktop.emulateMedia({ reducedMotion: 'reduce' });
  await desktop.locator('[data-story-link="recalibrate"]').click();
  const motion = await desktop.evaluate(() => { const el = document.querySelector('[data-story-transition] > .caos-story-stage'); const s = el ? getComputedStyle(el) : null; return s ? { name: s.animationName, duration: s.animationDuration } : null; });
  assert.ok(!motion || motion.name === 'none' || Number.parseFloat(motion.duration) * (motion.duration.endsWith('ms') ? 1 : 1000) <= 150, 'reduced motion: no stage motion over 150 ms');
  assert.equal(await desktop.locator('.story-play').isDisabled(), true, 'reduced motion: the day player is off');
  await desktop.emulateMedia({ reducedMotion: 'no-preference' });

  // a change of model inside a step is an eased move: the path is still moving a few frames after the click and settled later
  await desktop.locator('[data-story-link="recalibrate"]').click();
  await desktop.locator('[data-path="recalibrated-var"]').waitFor({ state: 'visible', timeout: 15000 });
  const pathD = () => desktop.locator('[data-path="recalibrated-var"]').getAttribute('d');
  const before = await pathD();
  await desktop.locator('[data-linked-view="panel"][data-linked-id="model:garch-t"]').click();
  await desktop.waitForTimeout(60);
  const early = await pathD();
  await desktop.waitForTimeout(900);
  const late = await pathD();
  assert.notEqual(before, late, 'the recalibrated path changes with the model');
  assert.notEqual(early, late, 'the change of model is eased, not a cut');
  assert.equal(late, await pathD(), 'the eased move settles');
  await desktop.locator('[data-linked-view="panel"][data-linked-id="model:hs-250"]').click();
  await desktop.waitForTimeout(500);

  // the exit lands on the route the reader came from, with the window and the model of the step (ADR-0082 rule 3)
  const modelNow = await desktop.locator('[data-linked-view="panel"][aria-pressed="true"]').first().getAttribute('data-linked-id');
  assert.equal(modelNow, 'model:hs-250');
  await desktop.locator('.caos-story-exit').click();
  const wanted = new URL(from, 'https://x.test');
  wanted.searchParams.set('variant', 'equity-2007-09');
  wanted.searchParams.set('model', 'hs-250');
  await desktop.waitForURL((url) => url.pathname === wanted.pathname && [...wanted.searchParams].every(([k, v]) => url.searchParams.get(k) === v));
  await desktop.locator('[data-workbench], .caos-workbench, main').first().waitFor({ state: 'visible', timeout: 20000 });
  assert.match(await desktop.locator('body').innerText(), /Equity 2007 to 2009/, 'the App opens on the window of the step');
  // and with no route to return to, the exit goes to the C11 case with the same state
  await desktop.goto(`${base}/story/decide?window=fx-2008&model=garch-t`, { waitUntil: 'domcontentloaded' });
  await desktop.locator(VIEWS.decide).waitFor({ state: 'visible', timeout: 15000 });
  await desktop.locator('.caos-story-exit').click();
  await desktop.waitForURL((url) => url.pathname === '/app' && url.searchParams.get('case') === 'C11' && url.searchParams.get('variant') === 'fx-2008' && url.searchParams.get('model') === 'garch-t');
  assert.match(await desktop.locator('body').innerText(), /FX 2008/, 'the App opens on the window of the exit');

  // the phone: the panel below the stage, three callouts, no horizontal overflow, at every step
  const phone = await browser.newPage({ viewport: { width: 390, height: 844 } });
  watch(phone);
  for (const step of STEPS) {
    await phone.goto(`${base}/story/${step}?window=equity-2007-09&model=hs-250`, { waitUntil: 'domcontentloaded' });
    await phone.locator(VIEWS[step]).waitFor({ state: 'visible', timeout: 15000 });
    const geometry = await phone.evaluate(() => {
      const box = (el) => { const r = el.getBoundingClientRect(); return { top: r.top, right: r.right, bottom: r.bottom, left: r.left }; };
      return {
        width: document.documentElement.scrollWidth,
        viewport: innerWidth,
        stage: box(document.querySelector('[data-stage]')),
        panel: box(document.querySelector('[data-stage-panel]')),
        calls: [...document.querySelectorAll('[data-caos-callout]')].map(box),
      };
    });
    assert.ok(geometry.width <= geometry.viewport + 1, `${step}: no page-level horizontal overflow on the phone`);
    assert.equal(geometry.calls.length, 3, `${step}: three callouts on the phone`);
    assert.ok(geometry.panel.top >= geometry.stage.bottom - 1, `${step}: the panel sits below the stage on the phone`);
    assert.ok(geometry.calls.every((c) => c.left >= -1 && c.right <= geometry.viewport + 1), `${step}: the callouts stay inside the phone`);
  }
  assert.deepEqual(errors, [], 'no uncaught page errors or console errors');
  console.log('Five story steps with distinct views and the artifacts\' numbers, linked scene/panel selection both ways, the shared day and the model kept across steps, play paused by input, the window selector, reduced motion, the exit to its route and the phone geometry passed.');
} finally {
  await browser.close();
  serverProcess?.kill();
}
