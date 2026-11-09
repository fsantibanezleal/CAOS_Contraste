// SHOW-1: the six views and the panels, rendered on the server from the committed artifacts, in both languages. What each shows is
// read against the document it cites: the numbers on the screen equal the numbers of the artifact; the scene and the panel carry
// the same linked ids; a window without a number says so; a headline states a finding in at most 12 words with a digit.
import { readFileSync } from 'node:fs';
import { beforeEach, describe, expect, it } from 'vitest';
import { formatNumber } from '@fasl-work/caos-app-shell';
import { CrisisView } from './CrisisView';
import { DecisionView } from './DecisionView';
import { FlowView } from './FlowView';
import { CrisisPanel, DecisionPanel, InventoryPanel, LightPanel, ModelList, RecalibrationPanel, Unavailable } from './Panels';
import { RecalibrationView } from './RecalibrationView';
import { TrafficLightView } from './TrafficLightView';
import { clampCursor, decision, defaultCursor, recalibration, windowModel, zoneOf, buildFlow, findingsOfFamily } from './model';
import {
  STEP_IDS, headlineBacktest, headlineCrisis, headlineDecision, headlineInventory, headlineRecalibration, words, zoneBi,
} from './text';
import { WINDOWS, c11, findings, html, inventory, setLang, textOf } from './testkit';

const SIZE = { width: 900, height: 520 };
const PHONE = { width: 360, height: 420 };
const BAD = /NaN|undefined|Infinity|\[object/;
const inv = inventory();
const fin = findings();
const flow = buildFlow(inv, fin);
const en = (n: number) => formatNumber(n, 'en', { decimals: 0 });

beforeEach(() => setLang('en'));

describe('V1: the flow shows the counts of the governance documents', () => {
  const dates = windowModel(c11('equity-2007-09'))!.dates;
  const draw = (size = SIZE, selected: string | null = 'family:market') =>
    html(<FlowView size={size} flow={flow} selected={selected} entryExposure={null} market={null} dates={dates} cursor={10} onSelect={() => undefined} />);

  it('draws every family as a selectable node with its findings and every entry once', () => {
    const m = draw();
    expect((m.match(/data-linked-view="scene"/g) ?? []).length).toBe(flow.families.length);
    for (const f of flow.families) {
      expect(m).toContain(`data-linked-id="family:${f.id}"`);
      expect(textOf(m)).toContain(`${en(f.entries.length)} ${f.entries.length === 1 ? 'entry' : 'entries'} · ${en(f.total)} ${f.total === 1 ? 'finding' : 'findings'}`);
    }
    expect(flow.families.reduce((a, f) => a + f.entries.length, 0)).toBe(34);
    expect(m).toMatch(/data-linked-id="family:market"[^>]*data-linked-selected="true"/);
    expect(m).not.toMatch(BAD);
  });

  it('carries the Basel zone of the shared day on the market node, from the window document', () => {
    const w = windowModel(c11('equity-2007-09'))!;
    const hs = w.models.find((x) => x.id === 'hs-250')!;
    const m = html(<FlowView size={SIZE} flow={flow} selected={null} entryExposure={null} market={{ label: hs.label, zone: zoneOf(hs.trailing[10]!, w.cuts), exceptions: hs.trailing[10]!, day: 10 }} dates={w.dates} cursor={10} onSelect={() => undefined} />);
    expect(m).toContain('data-linked-cursor-position="10"');
    expect(m).toContain('value="10"');
    expect(textOf(m)).toContain(`${zoneBi(zoneOf(hs.trailing[10]!, w.cuts)).en} · ${hs.trailing[10]}`);
  });

  it('keeps every node on the phone and says so in Spanish', () => {
    setLang('es');
    const m = draw(PHONE);
    expect((m.match(/data-flow-node=/g) ?? []).length).toBe(flow.exposures.length + flow.families.length + flow.outputs.length);
    expect(textOf(m)).toContain('FAMILIA DE MODELOS');
    expect(m).not.toMatch(BAD);
  });

  it('the panel lists the same family ids and opens the selected family by the three elements', () => {
    const m = html(<InventoryPanel flow={flow} fin={fin} selected="family:market" finding={null} onPick={() => undefined} onFinding={() => undefined} />);
    for (const f of flow.families) expect(m).toContain(`data-linked-id="family:${f.id}"`);
    expect(m).toMatch(/data-linked-id="family:market"[^>]*data-linked-view="panel"|data-linked-view="panel"[^>]*data-linked-id="family:market"/);
    const market = flow.families.find((f) => f.id === 'market')!;
    expect(textOf(m)).toContain(`${en(market.total)} findings`);
    for (const el of ['Conceptual soundness', 'Ongoing monitoring', 'Outcomes analysis']) expect(textOf(m)).toContain(el);
    const first = findingsOfFamily(flow, fin, 'market')[0]!;
    expect(textOf(m)).toContain(`${first.severity} `);
  });
});

describe('V3: the traffic light', () => {
  it('draws every model, the three zones with the cuts of the table and the count on the shared day, in each window', () => {
    for (const id of ['equity-2007-09', 'fx-2008', 'calm-2004-06']) {
      const w = windowModel(c11(id))!;
      const hs = w.models.find((x) => x.id === 'hs-250')!;
      const day = defaultCursor(hs, w.n);
      const m = html(<TrafficLightView size={SIZE} w={w} selected="hs-250" cursor={day} onSelect={() => undefined} onCursor={() => undefined} />);
      expect((m.match(/data-linked-view="scene"/g) ?? []).length).toBe(18);
      expect((m.match(/data-linked-selected="true"/g) ?? []).length).toBe(1);
      for (const z of ['Green · 0 to 4', 'Amber · 5 to 9', 'Red · 10 or more']) expect(textOf(m)).toContain(z);
      expect(textOf(m)).toContain(`${hs.trailing[day]} exceptions · ${zoneBi(zoneOf(hs.trailing[day]!, w.cuts)).en}`);
      expect(m).toContain(`data-linked-cursor-position="${day}"`);
      expect(m).toContain(`value="${day}"`);
      expect(m).not.toMatch(BAD);
    }
  });

  it('a window shorter than 250 days says the light is not evaluated and does not colour a verdict', () => {
    const w = windowModel(c11('mixed-2023'))!;
    const m = html(<TrafficLightView size={SIZE} w={w} selected="hs-250" cursor={0} onSelect={() => undefined} onCursor={() => undefined} />);
    expect(textOf(m)).toContain('Not evaluated: the light needs 250 days, the window has 64');
    expect(m).not.toContain('data-lead-in');
  });

  it('the panel states the tally of the document and lists the models with the same ids', () => {
    const w = windowModel(c11('equity-2007-09'))!;
    const hs = w.models.find((x) => x.id === 'hs-250')!;
    const m = html(<LightPanel w={w} m={hs} cursor={0} selected="hs-250" onPick={() => undefined} />);
    const t = textOf(m);
    expect(t).toContain(`peaks at ${hs.light!.max} and ends at ${hs.light!.final}`);
    expect(t).toContain(`${hs.light!.green} days green, ${hs.light!.amber} amber, ${hs.light!.red} red`);
    expect((m.match(/data-linked-view="panel"/g) ?? []).length).toBe(18);
    expect(m).toContain('https://www.bis.org/publ/bcbs22.htm');
  });
});

describe('V4: the crisis', () => {
  it('equity 2007 to 2009: the realised loss is withheld, the exceptions sit on the VaR with the reason', () => {
    const w = windowModel(c11('equity-2007-09'))!;
    const hs = w.models.find((x) => x.id === 'hs-250')!;
    const m = html(<CrisisView size={SIZE} w={w} modelId="hs-250" cursor={50} onCursor={() => undefined} />);
    expect((m.match(/data-exception-day=/g) ?? []).length).toBe(hs.exceedances.length);
    expect(m).toContain('data-loss-withheld');
    expect(m).not.toContain('data-realised-loss');
    expect(m).toContain('data-envelope');
    const p = html(<CrisisPanel w={w} m={hs} cursor={50} selected="hs-250" onPick={() => undefined} />);
    expect(textOf(p)).toContain(`${hs.exceedances.length} breaches of the 1% VaR in ${hs.n} days`);
    expect(textOf(p)).toMatch(/derived-only source/);
    expect(p).toContain('data-state="unavailable"');
  });

  it('FX 2008: the realised loss is drawn and the exceptions sit on it', () => {
    const w = windowModel(c11('fx-2008'))!;
    const m = html(<CrisisView size={SIZE} w={w} modelId="hs-250" cursor={50} onCursor={() => undefined} />);
    expect(m).toContain('data-realised-loss');
    expect(m).not.toContain('data-loss-withheld');
  });

  it('in Spanish the reason of the withheld loss is Spanish and no raw id shows', () => {
    setLang('es');
    const w = windowModel(c11('equity-2007-09'))!;
    const hs = w.models.find((x) => x.id === 'hs-250')!;
    const t = textOf(html(<CrisisPanel w={w} m={hs} cursor={50} selected="hs-250" onPick={() => undefined} />));
    expect(t).toContain('solo se versionan las salidas de los modelos');
    expect(t).not.toMatch(/\bhs-250\b/);
  });
});

describe('V5: the recalibration', () => {
  it('draws the raw path dashed and the recalibrated solid, with the exceptions of the document', () => {
    const data = c11('equity-2007-09');
    const w = windowModel(data)!;
    const raw = w.models.find((x) => x.id === 'hs-250')!;
    const rec = recalibration(data, 'hs-250')!;
    const m = html(<RecalibrationView size={SIZE} w={w} raw={raw} rec={rec} cursor={100} onCursor={() => undefined} />);
    expect((m.match(/data-raw-exception=/g) ?? []).length).toBe(rec.rawExceptions);
    expect((m.match(/data-recalibrated-exception=/g) ?? []).length).toBe(rec.wrappedExceptions);
    expect(m).toMatch(/stroke-dasharray="6 4"[^>]*data-path="raw-var"/);
    expect(m).not.toMatch(/data-path="recalibrated-var"[^>]*stroke-dasharray/);
    expect(m).toContain('aria-pressed="false"');
    expect(m).toContain('data-linked-cursor-position="100"');
    const p = html(<RecalibrationPanel w={w} raw={raw} rec={rec} wrapped={['hs-250', 'garch-t', 'fhs']} selected="hs-250" onPick={() => undefined} verdict={null} usingFallback={false} />);
    const t = textOf(p);
    expect(t).toContain(`Breaches ${rec.rawExceptions} ${rec.wrappedExceptions}`);
    expect((p.match(/data-linked-view="panel"/g) ?? []).length).toBe(3);
  });
});

describe('V6: the decision', () => {
  it('every model is a row, the gates and the champion are the document, in every window', () => {
    for (const id of WINDOWS) {
      const data = c11(id);
      const w = windowModel(data)!;
      const d = decision(data, w)!;
      const m = html(<DecisionView size={SIZE} d={d} alpha={0.01} selected="hs-250" onSelect={() => undefined} />);
      expect((m.match(/data-decision-row=/g) ?? []).length).toBe(18);
      expect((m.match(/>pass</g) ?? []).length).toBe(d.eligible);
      if (d.champion) expect(textOf(m)).toContain('★');
      else expect(m).toContain('data-no-champion');
      expect(m).not.toMatch(BAD);
      const p = html(<DecisionPanel w={w} d={d} selected="hs-250" onPick={() => undefined} reason={d.championReason} />);
      if (!d.champion) expect(textOf(p), id).toContain('no model is eligible');
    }
  });

  it('the interval brackets the rate of the selected model in the panel', () => {
    const data = c11('equity-2007-09');
    const w = windowModel(data)!;
    const d = decision(data, w)!;
    const row = d.rows.find((r) => r.id === 'hs-250')!;
    const t = textOf(html(<DecisionPanel w={w} d={d} selected="hs-250" onPick={() => undefined} reason={d.championReason} />));
    expect(t).toContain(`${row.exceptions} exceptions in ${row.n} days`);
  });
});

describe('the model list and the cursor', () => {
  it('lists the ladder with the same ids as the scene', () => {
    const w = windowModel(c11('equity-2007-09'))!;
    const m = html(<ModelList w={w} selected="garch-t" onPick={() => undefined} />);
    for (const x of w.models) expect(m).toContain(`data-linked-id="model:${x.id}"`);
    expect(m).toMatch(/aria-pressed="true"[^>]*data-linked-id="model:garch-t"|data-linked-id="model:garch-t"[^>]*aria-pressed="true"/);
  });

  it('the cursor of a window stays inside it when the window changes', () => {
    expect(clampCursor(503, 64, 3)).toBe(63);
  });
});

describe('the headlines state a finding with its number in at most 12 words', () => {
  it('every headline of every window and every model, in both languages, has its number in at most 12 words', () => {
    for (const id of WINDOWS) {
      const data = c11(id);
      const w = windowModel(data)!;
      const d = decision(data, w)!;
      const heads = [headlineInventory(34, flow.carried.S1, flow.carried.S2), headlineDecision(d)];
      for (const m of w.models) {
        heads.push(headlineBacktest(m.label, m.light ? m.light.final : null, m.light ? m.light.zone : null, m.exceedances.length, w.n), headlineCrisis(m.label, m.exceedances.length, m.n));
      }
      for (const mid of ['hs-250', 'garch-t', 'fhs']) {
        const r = recalibration(data, mid)!;
        heads.push(headlineRecalibration(r.rawExceptions, r.wrappedExceptions, r.expected));
      }
      for (const h of heads) {
        for (const lang of ['en', 'es'] as const) {
          expect(words(h, lang), h[lang]).toBeLessThanOrEqual(12);
          expect(h[lang], h[lang]).toMatch(/\d/);
        }
      }
    }
  });

  it('the inventory headline quotes the register', () => {
    const carried = (sev: string) => fin.rows.filter((r) => r.severity === sev && r.status !== 'validated_closed').length;
    expect(headlineInventory(flow.entries, flow.carried.S1, flow.carried.S2).en).toBe(`34 inventory entries carry ${carried('S1')} critical and ${carried('S2')} significant findings`);
    expect(STEP_IDS).toHaveLength(5);
  });
});

/** The linked ids of a markup on one side of the selection. */
const linkedIds = (markup: string, side: 'scene' | 'panel'): string[] =>
  [...markup.matchAll(/<[^>]*data-linked-id="([^"]+)"[^>]*>/g)].filter((m) => m[0].includes(`data-linked-view="${side}"`)).map((m) => m[1]!);
/** The scene objects that have no matching panel item: a selection that could only run one way. */
const unmatched = (scene: string, panel: string): string[] => {
  const have = new Set(linkedIds(panel, 'panel'));
  return linkedIds(scene, 'scene').filter((id) => !have.has(id));
};

describe('adversarial: the linked selection and the routes', () => {
  const w = windowModel(c11('equity-2007-09'))!;
  const d = decision(c11('equity-2007-09'), w)!;

  it('adversarial: a scene object with no panel item is found, and the shipped views have none', () => {
    const light = html(<TrafficLightView size={SIZE} w={w} selected="hs-250" cursor={3} onSelect={() => undefined} onCursor={() => undefined} />);
    const panel = html(<ModelList w={w} selected="hs-250" onPick={() => undefined} />);
    expect(unmatched(light, panel)).toEqual([]);
    const decided = html(<DecisionView size={SIZE} d={d} alpha={0.01} selected="hs-250" onSelect={() => undefined} />);
    expect(unmatched(decided, panel)).toEqual([]);
    const missing = panel.replace('data-linked-id="model:ewma"', 'data-linked-id="model:planted"');
    expect(unmatched(light, missing)).toEqual(['model:ewma']);
    const flowScene = html(<FlowView size={SIZE} flow={flow} selected="family:market" entryExposure={null} market={null} dates={w.dates} cursor={0} onSelect={() => undefined} />);
    const flowPanel = html(<InventoryPanel flow={flow} fin={fin} selected="family:market" finding={null} onPick={() => undefined} onFinding={() => undefined} />);
    expect(unmatched(flowScene, flowPanel)).toEqual([]);
    expect(unmatched(flowScene, flowPanel.replaceAll('data-linked-view="panel"', 'data-linked-view="none"')).length).toBe(flow.families.length);
  });

  it('adversarial: a selection shown on one side only is found, the selected id is marked on both', () => {
    const scene = html(<TrafficLightView size={SIZE} w={w} selected="garch-t" cursor={3} onSelect={() => undefined} onCursor={() => undefined} />);
    const panel = html(<ModelList w={w} selected="garch-t" onPick={() => undefined} />);
    expect(scene).toMatch(/data-linked-id="model:garch-t"[^>]*data-linked-selected="true"/);
    expect((panel.match(/data-linked-selected="true"/g) ?? []).length).toBe(1);
    expect(panel).toMatch(/aria-pressed="true"[^>]*data-linked-id="model:garch-t"|data-linked-id="model:garch-t"[^>]*aria-pressed="true"/);
    const other = html(<ModelList w={w} selected="fhs" onPick={() => undefined} />);
    expect(other).not.toBe(panel);
  });

  it('adversarial: a route list that drops a story step, or a static build that does not write it, is found', () => {
    // the story's routes are declared once, in product.json, and the gate runner and the static build read them (the base plants of those scripts are in tests/adversarial)
    const product = JSON.parse(readFileSync(new URL('../../../product.json', import.meta.url), 'utf8')) as { showcase?: { story_routes?: string[] } };
    const app = readFileSync(new URL('../App.tsx', import.meta.url), 'utf8');
    const declared = product.showcase?.story_routes ?? [];
    const missing = (routes: string[]) => STEP_IDS.filter((id) => !routes.includes(`/story/${id}`));
    expect(declared).toEqual(STEP_IDS.map((id) => `/story/${id}`));
    expect(missing(declared)).toEqual([]);
    expect(missing(declared.filter((route) => route !== '/story/crisis'))).toEqual(['crisis']);
    expect(missing(declared.map((route) => (route === '/story/decide' ? '/story/other' : route)))).toEqual(['decide']);
    expect(app).toContain('path="/story/:step"');
    expect(app).toContain("immersiveRoutes: ['/story']");
    expect(STEP_IDS).toHaveLength(5);
  });

  it('adversarial: a step that lacks its artifact says so with the reason and states no invented number', () => {
    const open = headlineBacktest({ en: 'A model', es: 'Un modelo' }, null, null, 5, 64);
    expect(open.en).toBe('A model: 5 exceptions in 64 days');
    const none = html(<Unavailable title="Window" reason="the pipeline did not write it" />);
    expect(none).toContain('data-state="unavailable"');
    expect(textOf(none)).toContain('the pipeline did not write it');
  });

  it('adversarial: the inventory headline changes with the register it reads, so it is not typed', () => {
    const extra = { ...fin.rows[0]!, key: 'planted', severity: 'S1' as const };
    const more = buildFlow(inv, { ...fin, rows: [...fin.rows, extra] });
    expect(headlineInventory(more.entries, more.sev.S1, more.sev.S2).en).toContain(`${flow.sev.S1 + 1} critical`);
    expect(headlineInventory(flow.entries, flow.sev.S1, flow.sev.S2).en).not.toBe(headlineInventory(more.entries, more.sev.S1, more.sev.S2).en);
  });

  it('adversarial: a window shorter than 250 days never draws a Basel verdict, whatever its counts', () => {
    const short = windowModel(c11('equity-2020'))!;
    expect(short.evaluated).toBe(false);
    const m = html(<TrafficLightView size={SIZE} w={short} selected="hs-250" cursor={short.n - 1} onSelect={() => undefined} onCursor={() => undefined} />);
    expect(m).toContain('data-not-evaluated');
    expect(m).not.toContain('data-lead-in');
    const hs = short.models.find((x) => x.id === 'hs-250')!;
    expect(hs.exceedances.length).toBeGreaterThan(0);
    expect(hs.light).toBeNull();
    const flowMarket = html(<FlowView size={SIZE} flow={flow} selected={null} entryExposure={null} market={{ label: hs.label, zone: null, exceptions: 3, day: 3 }} dates={short.dates} cursor={3} onSelect={() => undefined} />);
    expect(flowMarket).not.toContain('data-market-zone');
  });

  it('adversarial: the recalibrated exception moved in the document moves its marker in the drawing', () => {
    const data = c11('equity-2007-09');
    const ww = windowModel(data)!;
    const raw = ww.models.find((x) => x.id === 'hs-250')!;
    const rec = recalibration(data, 'hs-250')!;
    const moved = { ...rec, exceedances: rec.exceedances.map((e, i) => (i === 0 ? e + 100 : e)) };
    const a = html(<RecalibrationView size={SIZE} w={ww} raw={raw} rec={rec} cursor={100} onCursor={() => undefined} />);
    const b = html(<RecalibrationView size={SIZE} w={ww} raw={raw} rec={moved} cursor={100} onCursor={() => undefined} />);
    expect(a).not.toBe(b);
    expect(b).toContain(`data-recalibrated-exception="${rec.exceedances[0]! + 100}"`);
  });
});
