// SHOW-F: the fixes after the viz review of the story and the C11 conformal views (F1 to F24). Each test reads the committed artifacts
// and states what the screen must say or must not say: the callout colour is one rule of its number, a model the confidence set never
// ranked is "not ranked", the exit carries the step's window and model, the recalibration is never read as a pass, the strings are
// right in both languages (feminine zone, singular counts, no raw window id), the narrow drawings keep their key, and the dated views
// can be zoomed and read as a table.
import { readdirSync, readFileSync } from 'node:fs';
import { beforeEach, describe, expect, it } from 'vitest';
import { CrisisView, FIRST_FULL_WINDOW } from './CrisisView';
import { DecisionView, setWords } from './DecisionView';
import { FlowView } from './FlowView';
import { CrisisPanel, DecisionPanel, InventoryPanel, LightPanel, RecalibrationPanel } from './Panels';
import { RecalibrationView, recalibrationGeometry } from './RecalibrationView';
import { TrafficLightView } from './TrafficLightView';
import { MIN_SPAN, easeInOut, fullRange, isFull, mixSeries, zoomRange } from './chart';
import { exitTarget, seedOfQuery } from './exit';
import { breachState, buildFlow, decision, recalibration, stressSpan, windowModel } from './model';
import { WINDOW_ID_PATTERN, entriesLabel, findingsLabel, headlineBacktest, headlineInventory, headlineRecalibration, windowWords, zoneAdjective } from './text';
import { WINDOWS, c11, findings, html, inventory, setLang, textOf } from './testkit';
import { MANUSCRIPT_URL, PASSES_HEADER, TESTS_TOO_EASY, VERDICT_LABEL } from '../workbench/c11/caveat';
import { WINDOW_TEXT, outputsOf } from '../workbench/c11/selection';

const SIZE = { width: 900, height: 520 };
const PHONE = { width: 360, height: 520 };
const fin = findings();
const flow = buildFlow(inventory(), fin);
const eq = () => c11('equity-2007-09');

beforeEach(() => setLang('en'));

describe('F2, F16: a callout colour is one rule of its number, the same on every step', () => {
  it('green at or below the expected count, amber above it, red above twice it', () => {
    expect(breachState(0, 5.04)).toBe('normal');
    expect(breachState(5, 5.04)).toBe('normal');
    expect(breachState(6, 5.04)).toBe('warning');
    expect(breachState(10, 5.04)).toBe('warning');
    expect(breachState(11, 5.04)).toBe('alarm');
    expect(breachState(19, 5.04)).toBe('alarm');
    expect(breachState(3, 0)).toBe('normal');
  });

  it('the recalibrated count of the default window is red: 11 against 5.04 expected is more than twice', () => {
    const r = recalibration(eq(), 'hs-250')!;
    expect(r.wrappedExceptions).toBe(11);
    expect(breachState(r.wrappedExceptions, r.expected)).toBe('alarm');
    expect(breachState(r.rawExceptions, r.expected)).toBe('alarm');
  });

  it('the state follows the number in every window and every wrapped model, never the direction of the move', () => {
    for (const id of WINDOWS) {
      const data = c11(id);
      for (const m of ['hs-250', 'garch-t', 'fhs']) {
        const r = recalibration(data, m)!;
        const ratio = r.wrappedExceptions / r.expected;
        expect(breachState(r.wrappedExceptions, r.expected), `${id} ${m}`).toBe(ratio > 2 ? 'alarm' : ratio > 1 ? 'warning' : 'normal');
      }
    }
    // a raw count of zero is not an amber one (the "without" callout was always amber)
    const calm = recalibration(c11('mixed-2023'), 'hs-250')!;
    if (calm.rawExceptions === 0) expect(breachState(calm.rawExceptions, calm.expected)).toBe('normal');
  });
});

describe('F3: a model the confidence set never ranked is not tested, never out', () => {
  const d = decision(eq(), windowModel(eq()))!;
  const NOT_RANKED = ['cf-rolling', 'caviar-sav', 'caviar-as'];

  it('the three models without an ES are not tested; the others are in or out by the set', () => {
    for (const id of NOT_RANKED) expect(d.rows.find((r) => r.id === id)!.setState, id).toBe('not-tested');
    const states = d.rows.filter((r) => !NOT_RANKED.includes(r.id)).map((r) => r.setState);
    expect(states.every((s) => s === 'in' || s === 'out')).toBe(true);
    expect(d.rows.filter((r) => r.setState === 'in')).toHaveLength(d.setSize!);
    expect(d.setOf).toBe(15);
    expect(d.setSize).toBe(13);
  });

  it('the drawing says "not ranked (no ES)" for them and never "out", in both languages', () => {
    const m = html(<DecisionView size={SIZE} d={d} alpha={0.01} selected="hs-250" onSelect={() => undefined} />);
    expect((m.match(/data-set-state="not-tested"/g) ?? []).length).toBe(3);
    expect(textOf(m)).toContain('not ranked (no ES)');
    for (const id of NOT_RANKED) {
      const row = m.slice(m.indexOf(`data-decision-row="${id}"`));
      const upToNext = row.slice(0, row.indexOf('</g>'));
      expect(upToNext).not.toMatch(/>out\s/);
    }
    setLang('es');
    expect(textOf(html(<DecisionView size={SIZE} d={d} alpha={0.01} selected="hs-250" onSelect={() => undefined} />))).toContain('sin ranking (sin ES)');
  });

  it('the panel does not call them left out', () => {
    const w = windowModel(eq())!;
    for (const id of NOT_RANKED) {
      const t = textOf(html(<DecisionPanel w={w} d={d} selected={id} onPick={() => undefined} reason={d.championReason} />));
      expect(t, id).toContain('Not ranked by the model confidence set');
      expect(t, id).not.toContain('Left out');
    }
  });

  it('words of the set state, with a mark on a phone', () => {
    expect(setWords('in', 'en')).toBe('in set');
    expect(setWords('out', 'es')).toBe('fuera');
    expect(setWords('not-tested', 'en', true)).toBe('–');
    expect(setWords(null, 'en')).toBe('·');
  });
});

describe('F4: the exit lands on the App with the step window and model', () => {
  it('without a route it goes to the C11 case with the window and the model', () => {
    expect(exitTarget(null, 'fx-2008', 'garch-t')).toBe('/app?case=C11&variant=fx-2008&model=garch-t');
  });

  it('a route the reader came from keeps its own parameters and gains the two', () => {
    const u = new URL(exitTarget('/app?case=C11&view=variants&focus=1', 'equity-2007-09', 'hs-250'), 'https://x.test');
    expect(u.pathname).toBe('/app');
    expect(Object.fromEntries(u.searchParams)).toEqual({ case: 'C11', view: 'variants', focus: '1', variant: 'equity-2007-09', model: 'hs-250' });
  });

  it('a route that is not an App route is dropped, and the step state replaces an older one', () => {
    expect(exitTarget('//evil.test/app', 'rates-2022', 'ewma')).toBe('/app?case=C11&variant=rates-2022&model=ewma');
    expect(exitTarget('/other', 'rates-2022', 'ewma')).toBe('/app?case=C11&variant=rates-2022&model=ewma');
    const u = new URL(exitTarget('/app?case=C11&variant=calm-2004-06&model=fhs', 'fx-2008', 'ewma'), 'https://x.test');
    expect(u.searchParams.get('variant')).toBe('fx-2008');
    expect(u.searchParams.get('model')).toBe('ewma');
  });

  it('the App reads them back, and drops a value that is not an id', () => {
    expect(seedOfQuery('?case=C11&variant=fx-2008&model=garch-t')).toEqual({ variant: 'fx-2008', model: 'garch-t' });
    expect(seedOfQuery('?case=C11')).toEqual({ variant: null, model: null });
    expect(seedOfQuery('?variant=../x&model=a b')).toEqual({ variant: null, model: null });
  });

  it('every window of the story is a variant id of the C11 manifest, so the App can open on it', () => {
    const manifest = JSON.parse(readFileSync(new URL('../../../data/derived/manifests/C11.json', import.meta.url), 'utf8')) as { artifacts: { role: string; variant_id: string }[] };
    const ids = manifest.artifacts.filter((a) => a.role === 'variant').map((a) => a.variant_id);
    for (const w of Object.keys(WINDOW_TEXT)) expect(ids).toContain(w);
  });

  it('F22: the story names each window as the App chip of the same window does, in both languages', () => {
    const manifest = JSON.parse(readFileSync(new URL('../../../data/derived/manifests/C11.json', import.meta.url), 'utf8')) as { artifacts: { role: string; variant_id: string; short_title: { en: string; es: string } }[] };
    for (const a of manifest.artifacts.filter((x) => x.role === 'variant')) expect(WINDOW_TEXT[a.variant_id], a.variant_id).toEqual(a.short_title);
  });
});

describe('F6: the inventory headline counts entries and the findings still carried', () => {
  it('names entries, not models, and counts the rows not closed by validation', () => {
    const closed = fin.rows.filter((r) => r.status === 'validated_closed' && r.severity === 'S2').length;
    const s2 = fin.rows.filter((r) => r.severity === 'S2').length;
    expect(closed).toBeGreaterThan(0);
    expect(flow.carried.S2).toBe(s2 - closed);
    expect(flow.carried.S1).toBe(fin.rows.filter((r) => r.severity === 'S1' && r.status !== 'validated_closed').length);
    const h = headlineInventory(flow.entries, flow.carried.S1, flow.carried.S2);
    expect(h.en).toBe(`${inventory().entries.length} inventory entries carry ${flow.carried.S1} critical and ${flow.carried.S2} significant findings`);
    expect(h.es).toBe(`${inventory().entries.length} entradas del inventario acumulan ${flow.carried.S1} hallazgos críticos y ${flow.carried.S2} significativos`);
    expect(h.en).not.toMatch(/models/);
  });
});

describe('F1: the recalibration is never read as a pass', () => {
  const data = eq();
  const w = windowModel(data)!;
  const raw = w.models.find((m) => m.id === 'hs-250')!;
  const rec = recalibration(data, 'hs-250')!;
  const verdict = outputsOf({ data })!.conformal!.hypothesis.verdict.en;
  const panel = (lang: 'en' | 'es') => {
    setLang(lang);
    const v = outputsOf({ data })!.conformal!.hypothesis.verdict[lang];
    return html(<RecalibrationPanel w={w} raw={raw} rec={rec} wrapped={['hs-250', 'garch-t', 'fhs']} selected="hs-250" onPick={() => undefined} verdict={windowWords(v, lang)} usingFallback={false} />);
  };

  it('the headline states the move and the count expected, not a fix', () => {
    const h = headlineRecalibration(rec.rawExceptions, rec.wrappedExceptions, rec.expected);
    expect(h.en).toBe('Recalibration cuts breaches from 19 to 11; 5 were expected');
    expect(h.es).toBe('La recalibración baja las excedencias de 19 a 11; se esperaban 5');
    expect(headlineRecalibration(4, 9, 5.04).en).toBe('Recalibration raises breaches from 4 to 9; 5 were expected');
    expect(headlineRecalibration(5, 5, 5.04).en).toBe('Recalibration leaves breaches at 5; 5 were expected');
  });

  it('the panel marks the recalibrated p-value and zone as upper bounds and says the back-tests accept recalibrated runs too easily', () => {
    for (const lang of ['en', 'es'] as const) {
      const m = panel(lang);
      expect((m.match(/data-upper-bound=""/g) ?? []).length).toBe(2);
      const t = textOf(m);
      expect(t).toContain(TESTS_TOO_EASY[lang]);
      expect(t).toContain(VERDICT_LABEL[lang]);
      expect(m).toContain(`href="${MANUSCRIPT_URL}"`);
    }
  });

  it('the bake verdict is shown as its reading by the criterion, with the window named in words and never by its id', () => {
    const t = textOf(panel('en')).replace(/\p{Zs}/gu, ' ');
    expect(t).toContain(VERDICT_LABEL.en);
    expect(t).toContain(windowWords(verdict, 'en').replace(/\p{Zs}/gu, ' '));
    expect(t).not.toMatch(/equity-2007-09|equity-2020|rates-2022/);
    expect(textOf(panel('es'))).not.toMatch(/equity-2007-09/);
  });

  it('the caveat is number-free: no count of the manuscript is typed into a view', () => {
    for (const lang of ['en', 'es'] as const) expect(TESTS_TOO_EASY[lang]).not.toMatch(/\d/);
    expect(PASSES_HEADER.en).toContain('lenient');
  });
});

describe('F8: a window id in a document sentence is named in words, in both languages', () => {
  it('the pattern holds a word boundary, not a control character', () => {
    expect(WINDOW_ID_PATTERN.source).toContain('\\b');
    expect(WINDOW_ID_PATTERN.source).not.toContain(String.fromCharCode(8));
  });

  it('replaces every id of every window, whole', () => {
    for (const [id, name] of Object.entries(WINDOW_TEXT)) {
      expect(windowWords(`fails in ${id}.`, 'en')).toBe(`fails in ${name.en}.`);
      expect(windowWords(`falla en ${id}.`, 'es')).toBe(`falla en ${name.es}.`);
    }
    // an id that only contains another is not cut in two
    expect(windowWords('equity-2007-09-extra', 'en')).toBe(`${WINDOW_TEXT['equity-2007-09']!.en}-extra`);
  });

  it('no story source carries a backspace character where a word boundary was meant', () => {
    const dirs = ['.', '../pages'];
    const files: string[] = [];
    for (const d of dirs) for (const f of readdirSync(new URL(d, import.meta.url))) if (/\.(tsx?|css)$/.test(f) && (d === '.' || f === 'Story.tsx' || f === 'story.css')) files.push(new URL(`${d}/${f}`, import.meta.url).pathname);
    expect(files.length).toBeGreaterThan(8);
    for (const f of files) expect(readFileSync(decodeURIComponent(f.replace(/^\/([A-Za-z]:)/, '$1')), 'utf8').includes(String.fromCharCode(8)), f).toBe(false);
  });
});

describe('F9, F10: the Spanish zone is feminine and a count of one is singular', () => {
  it('"zona roja", never "zona rojo"', () => {
    expect(zoneAdjective('red', 'es')).toBe('roja');
    expect(zoneAdjective('amber', 'es')).toBe('ámbar');
    expect(zoneAdjective('green', 'es')).toBe('verde');
    expect(headlineBacktest({ en: 'HS', es: 'SH' }, 10, 'red', 19, 504).es).toBe('SH: 10 excepciones, zona roja');
    expect(headlineBacktest({ en: 'HS', es: 'SH' }, 10, 'red', 19, 504).en).toBe('HS: 10 exceptions, red zone');
    setLang('es');
    const d = eq();
    const w = windowModel(d)!;
    const t = textOf(html(<LightPanel w={w} m={w.models.find((m) => m.id === 'hs-250')!} cursor={326} selected="hs-250" onPick={() => undefined} />));
    expect(t).not.toMatch(/zona rojo|zona verde\b.*zona rojo/);
    expect(t).toMatch(/zona (roja|ámbar|verde)/);
    const c = textOf(html(<CrisisPanel w={w} m={w.models.find((m) => m.id === 'hs-250')!} cursor={326} selected="hs-250" onPick={() => undefined} />));
    expect(c).not.toMatch(/zona rojo/);
  });

  it('1 entry, 1 finding, 5 entries; never "1 entries"', () => {
    expect(entriesLabel(1, 'en')).toBe('1 entry');
    expect(entriesLabel(1, 'es')).toBe('1 entrada');
    expect(entriesLabel(5, 'en')).toBe('5 entries');
    expect(entriesLabel(0, 'es')).toBe('0 entradas');
    expect(findingsLabel(1, 'en')).toBe('1 finding');
    expect(findingsLabel(1, 'es')).toBe('1 hallazgo');
    expect(findingsLabel(2, 'es')).toBe('2 hallazgos');
  });

  it('the flow draws no "1 entries" or "1 entradas" in any size or language', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      for (const size of [SIZE, PHONE]) {
        const m = textOf(html(<FlowView size={size} flow={flow} selected="family:market" entryExposure={null} market={null} dates={null} cursor={0} onSelect={() => undefined} />));
        expect(m).not.toMatch(/\b1 (entries|entradas)\b/);
      }
    }
    const single = flow.exposures.filter((n) => n.entries.length === 1);
    expect(single.length).toBeGreaterThan(0);
    setLang('en');
    expect(textOf(html(<FlowView size={SIZE} flow={flow} selected="family:market" entryExposure={null} market={null} dates={null} cursor={0} onSelect={() => undefined} />))).toContain('1 entry');
  });

  it('the inventory panel says "1 inventory entry" for a family of one entry', () => {
    const one = flow.families.find((f) => f.entries.length === 1);
    expect(one).toBeTruthy();
    const t = textOf(html(<InventoryPanel flow={flow} fin={fin} selected={`family:${one!.id}`} finding={null} onPick={() => undefined} onFinding={() => undefined} />));
    expect(t).toMatch(/\b1 inventory entry\b/);
  });
});

describe('F11: the working tail level is drawn against its target and its floor', () => {
  const data = eq();
  const w = windowModel(data)!;
  const raw = w.models.find((m) => m.id === 'hs-250')!;
  const rec = recalibration(data, 'hs-250')!;

  it('the model carries the target and the floor of the band from the document', () => {
    const o = outputsOf({ data })!;
    expect(rec.target).toBe(0.01);
    expect(rec.levelMin).toBe(o.conformal!.method.level_min);
    expect(rec.workingLevel.length).toBe(w.n);
  });

  it('draws the path of the working level, the target line and the floor line', () => {
    const m = html(<RecalibrationView size={SIZE} w={w} raw={raw} rec={rec} cursor={100} onCursor={() => undefined} />);
    expect(m).toContain('data-path="working-level"');
    expect(m).toContain('data-level-target=""');
    expect(m).toContain('data-level-floor=""');
    expect(textOf(m)).toMatch(/Working tail level/);
    expect(textOf(m)).toMatch(/target 1(\.0)?\s?%/);
    expect(textOf(m)).toMatch(/floor 0\.1\s?%/);
  });

  it('the track sits between the VaR panel and the count panel and keeps a height at both sizes', () => {
    for (const size of [SIZE, PHONE]) {
      const g = recalibrationGeometry(size, w, raw, rec);
      expect(g.tL).toBeGreaterThan(g.b1);
      expect(g.bL - g.tL).toBeGreaterThanOrEqual(30);
      expect(g.t2).toBeGreaterThan(g.bL);
      expect(g.b2).toBeGreaterThan(g.t2 + 40);
    }
  });
});

describe('F13: the dated views zoom and carry their data as a table', () => {
  const w = windowModel(eq())!;
  const raw = w.models.find((m) => m.id === 'hs-250')!;
  const rec = recalibration(eq(), 'hs-250')!;
  const views = (range?: [number, number]) => ({
    light: <TrafficLightView size={SIZE} w={w} selected="hs-250" cursor={300} onSelect={() => undefined} onCursor={() => undefined} range={range} onRange={() => undefined} />,
    crisis: <CrisisView size={SIZE} w={w} modelId="hs-250" cursor={300} onCursor={() => undefined} range={range} onRange={() => undefined} />,
    recalibration: <RecalibrationView size={SIZE} w={w} raw={raw} rec={rec} cursor={300} onCursor={() => undefined} range={range} onRange={() => undefined} />,
  });

  it('each dated view has a visually hidden table of its series, one row per day', () => {
    for (const [id, el] of Object.entries(views())) {
      const m = html(el);
      expect(m, id).toContain(`data-data-table="${id}"`);
      const body = m.slice(m.indexOf(`data-data-table="${id}"`));
      expect((body.slice(0, body.indexOf('</table>')).match(/<tr>/g) ?? []).length - 1, id).toBe(w.n);
    }
  });

  it('the decision view has a table of its rows', () => {
    const d = decision(eq(), w)!;
    const m = html(<DecisionView size={SIZE} d={d} alpha={0.01} selected="hs-250" onSelect={() => undefined} />);
    expect(m).toContain('data-data-table="decision"');
    expect(textOf(m)).toContain('Confidence set');
  });

  it('a zoomed view carries the buttons of the zoom and a whole one says so', () => {
    const whole = html(views(fullRange(w.n)).light);
    expect(whole).toContain('data-zoom="full"');
    const zoomed = html(views([100, 200]).light);
    expect(zoomed).toContain('data-zoom="100-200"');
    expect(zoomed).toContain('aria-label="Show the whole window"');
  });

  it('zoom keeps the shared day marker only while the day is inside the range', () => {
    expect(html(views([100, 200]).light)).not.toContain('data-linked-cursor-marker');
    expect(html(views([250, 350]).light)).toContain('data-linked-cursor-position="300"');
  });

  it('the range arithmetic halves, doubles and stays inside the window', () => {
    expect(isFull(fullRange(504), 504)).toBe(true);
    const half = zoomRange(fullRange(504), 504, 0.5, 300);
    expect(half[1] - half[0]).toBe(252);
    expect(half[0]).toBeGreaterThanOrEqual(0);
    expect(half[1]).toBeLessThanOrEqual(503);
    const tight = zoomRange([0, 20], 504, 0.1, 5);
    expect(tight[1] - tight[0]).toBeGreaterThanOrEqual(MIN_SPAN);
    expect(zoomRange(half, 504, 2, 300)).toEqual([0, 503]);
    const edge = zoomRange(fullRange(504), 504, 0.5, 503);
    expect(edge[1]).toBe(503);
  });
});

describe('F12: a change of selection is an eased move, instant under reduced motion', () => {
  it('mixes two series of one length and returns the target when the lengths differ', () => {
    expect(mixSeries([0, 10], [10, 20], 0.5)).toEqual([5, 15]);
    expect(mixSeries([0, 10], [10, 20], 1)).toEqual([10, 20]);
    expect(mixSeries([0], [1, 2], 0.5)).toEqual([1, 2]);
  });

  it('the easing starts and ends on the endpoints and never overshoots', () => {
    expect(easeInOut(0)).toBe(0);
    expect(easeInOut(1)).toBe(1);
    expect(easeInOut(0.5)).toBeCloseTo(0.5, 6);
    for (let k = 0; k <= 20; k++) {
      const v = easeInOut(k / 20);
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThanOrEqual(1);
    }
  });

  it('the flow carries a moving key whose speed is set by the entries a link carries', () => {
    const m = html(<FlowView size={SIZE} flow={flow} selected="family:market" entryExposure={null} market={null} dates={null} cursor={0} onSelect={() => undefined} />);
    const speeds = [...m.matchAll(/data-flow-speed="([0-9.]+)"/g)].map((x) => Number(x[1]));
    expect(speeds.length).toBe(flow.links.length);
    expect(new Set(speeds).size).toBeGreaterThan(1);
    const css = readFileSync(new URL('../pages/story.css', import.meta.url), 'utf8');
    expect(css).toMatch(/@keyframes story-flow-move/);
    expect(css).toMatch(/prefers-reduced-motion: reduce\) \{ \.story-flow-pulse \{ animation: none/);
  });
});

describe('F14: the narrow drawings keep their key', () => {
  const w = windowModel(eq())!;
  const raw = w.models.find((m) => m.id === 'hs-250')!;
  const rec = recalibration(eq(), 'hs-250')!;

  it('every dated view has a legend on a phone', () => {
    const light = html(<TrafficLightView size={PHONE} w={w} selected="hs-250" cursor={300} onSelect={() => undefined} onCursor={() => undefined} />);
    const crisis = html(<CrisisView size={PHONE} w={w} modelId="hs-250" cursor={300} onCursor={() => undefined} />);
    const recal = html(<RecalibrationView size={PHONE} w={w} raw={raw} rec={rec} cursor={300} onCursor={() => undefined} />);
    for (const m of [light, crisis, recal]) expect(m).toContain('data-legend=""');
    expect(textOf(recal)).toMatch(/Without/);
    expect(textOf(recal)).toMatch(/With/);
    expect(textOf(crisis)).toMatch(/VaR/);
    expect(textOf(crisis)).toMatch(/range/);
    expect(textOf(crisis)).toMatch(/breach/);
  });

  it('the decision view on a phone has no 3 % tick, no axis title, and a mark for the set', () => {
    const d = decision(eq(), w)!;
    const m = html(<DecisionView size={PHONE} d={d} alpha={0.01} selected="hs-250" onSelect={() => undefined} />);
    expect(textOf(m)).not.toMatch(/\b3\s?%/);
    expect(textOf(m)).not.toContain('Exception rate, with 95% interval');
    expect((m.match(/data-set-state="/g) ?? []).length).toBe(d.rows.length);
    expect(textOf(m)).toContain('Gates · set');
  });

  it('the output nodes of the flow on a phone drop the findings count that was cut at the stage edge', () => {
    const m = textOf(html(<FlowView size={PHONE} flow={flow} selected="family:market" entryExposure={null} market={null} dates={null} cursor={0} onSelect={() => undefined} />));
    expect(m).not.toMatch(/ent\. · \d+ hall\.\s+(Provisions|Capital|Liquidity|Decisions)/);
  });
});

describe('F19, F20, F24: the stretch, the market node and the readout', () => {
  const w = windowModel(eq())!;
  const hs = w.models.find((m) => m.id === 'hs-250')!;

  it('the amber or red stretch starts at the first complete Basel window, not in the days still filling', () => {
    expect(FIRST_FULL_WINDOW).toBe(249);
    const all = stressSpan(hs, w.cuts)!;
    const full = stressSpan(hs, w.cuts, FIRST_FULL_WINDOW)!;
    expect(all[0]).toBeLessThan(FIRST_FULL_WINDOW);
    expect(full[0]).toBeGreaterThanOrEqual(FIRST_FULL_WINDOW);
    expect(full[1]).toBe(all[1]);
  });

  it('the drawn stretch of the crisis view opens on or after day 249 for an evaluated window', () => {
    const m = html(<CrisisView size={SIZE} w={w} modelId="hs-250" cursor={300} onCursor={() => undefined} />);
    const x = Number(/data-stress-span=""[^>]*><rect x="([0-9.]+)"/.exec(m)?.[1]);
    const plotL = 54;
    const plotR = SIZE.width - 16;
    const first = plotL + (FIRST_FULL_WINDOW / (w.n - 1)) * (plotR - plotL);
    expect(x).toBeGreaterThanOrEqual(first - 1);
  });

  it('the market node names its model in its title', () => {
    const m = html(<FlowView size={SIZE} flow={flow} selected="family:market" entryExposure={null} market={{ label: { en: 'Historical simulation, 250 days', es: 'Simulación histórica, 250 días' }, zone: 'red', exceptions: 14, day: 326 }} dates={w.dates} cursor={326} onSelect={() => undefined} />);
    expect(m).toMatch(/<title>[^<]*Historical simulation, 250 days<\/title>/);
  });

  it('the crisis and the light views read out the day, the value and the unit at the cursor', () => {
    const crisis = textOf(html(<CrisisView size={SIZE} w={w} modelId="hs-250" cursor={326} onCursor={() => undefined} />));
    expect(crisis).toMatch(/Oct 15, 2008 · VaR 5\.76\s?%/);
    const light = textOf(html(<TrafficLightView size={SIZE} w={w} selected="hs-250" cursor={326} onSelect={() => undefined} onCursor={() => undefined} />));
    expect(light).toMatch(/Oct 15, 2008 · 14 exceptions · Red/);
  });
});

describe('F21, F23: the set is read against the models it ranked', () => {
  it('the decision carries the size of the comparison the set was drawn from', () => {
    const d = decision(eq(), windowModel(eq()))!;
    expect(d.setOf).toBe(outputsOf({ data: eq() })!.comparison.mcs.find((s) => s.alpha === 0.01)!.members.length);
    expect(d.setSize).toBeLessThan(d.setOf!);
  });
});
