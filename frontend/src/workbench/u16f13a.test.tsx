// Fix round 6, unit U16-F13a (the shared layout of the fifth capture review, R5, and the rows of C01, C02 and C04), on the committed
// documents and in both languages. Each test names the row it closes and fails on its defect. What only a browser can measure (a
// cue's count against the rows a reader sees, a plot's height at 1280 and 390, a card body's clip) is measured by layout-probe.mjs on
// the built site; these tests hold the rules the cue and the floors rest on and the probe's own judgement of its measures.
import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it } from 'vitest';
import { COMMITTED } from '../lib/policy';
import type { components } from '../lib/contract.gen';
import type { CaseData } from '../api/artifacts';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../lib/contract.types';
import { committedData, render, textOf, variantIds, type Lang } from './c03/u16f2-kit';
import { setLang } from './c03/u6-testkit';
import { U6TestsTable, statText } from './c03/U6Shared';
import { committedDoc } from './c14/testkit';
import { fixtureData, html } from './c20/testkit';
import { C02ContextView } from './c02/C02Common';
import { TransferView } from './c02/HorizonViews';
import { defaultSel, type C02Sel } from './c02/selection';
import { FindingsView } from './FindingsView';
import { defaultChallenger } from './model';
import { BatteryView, DiscriminationView, StabilityView, bandText } from './ValidationViews';
import { ScorecardView } from './ModelViews';
import { C04FindingsView, findingsDrawing, findingsEvidence } from './c04/C04Common';
import { makeSel } from './c04/selection';
import { KIND_TEXT, rungLabel } from './c03/selection';
import { modelName, segmentName } from './names';
// @ts-expect-error the generator is plain JavaScript (frontend/scripts/gen-names.mjs)
import { VIEW_KIND_TEXT } from '../../scripts/gen-names.mjs';
import { CUE_BAND, NOTE_KEEP, SCROLL_BOXES, bodyRoom, rowHidden, rowsBelow, sizerOf, toPx } from './layout';
// @ts-expect-error the probe is plain JavaScript, run by node with Playwright (src/workbench/layout-probe.mjs)
import { BOXES, TARGETS, bandOpacity, cueCount, judge, unreadable } from './layout-probe.mjs';

const LANGS: Lang[] = ['en', 'es'];
afterEach(() => setLang('en'));
const strip = (s: string) => s.replace(/\/\*[\s\S]*?\*\//g, '');
const css = strip(readFileSync(new URL('../styles/contraste.css', import.meta.url), 'utf8'));
const notesCss = strip(readFileSync(new URL('./c04/c04-notes.css', import.meta.url), 'utf8'));
const REM = 16;
const BAND = toPx(CUE_BAND, REM);

/** A box of `n` rows of `h` px from `top`, as layout.ts reads it (querySelectorAll of its body rows). */
const fakeBox = (n: number, top: number, h: number) => ({
  querySelectorAll: () => Array.from({ length: n }, (_, i) => ({ closest: () => null, getBoundingClientRect: () => ({ top: top + i * h, bottom: top + (i + 1) * h, height: h }) })),
}) as unknown as Pick<Element, 'querySelectorAll'>;

describe('U16-F13a the scroll cue counts the rows a reader cannot read (R5 c06 B1, c22 m2, c01 n3, c05 n5, c02 n2)', () => {
  it('c06 B1: the S&P By year box, 26 cohorts of 33 px, 7 read above the band: "19 more rows below", never 20', () => {
    // measured on the base build (C04 sp, 1280 light English): the box's visible bottom at 531 px, the 2005 row from 434 to 467 px
    const box = fakeBox(26, 434 - 5 * 33, 33);
    expect(rowsBelow(box, 531, BAND)).toBe(19);
    // the 2006 row (467 to 500) ends in the band's clear top: it is read
    expect(rowHidden({ top: 467, bottom: 500, height: 33 }, 531, BAND)).toBe(false);
    expect(rowHidden({ top: 500, bottom: 533, height: 33 }, 531, BAND)).toBe(true);
  });
  it('c22 m2: a whole row whose bottom border ends a pixel inside the band is read; a row under the band is not', () => {
    expect(rowHidden({ top: 440, bottom: 470, height: 30 }, 500, BAND)).toBe(false);
    expect(rowHidden({ top: 480, bottom: 510, height: 30 }, 500, BAND)).toBe(true);
    expect(rowHidden({ top: 480, bottom: 480, height: 0 }, 500, BAND)).toBe(false);
  });
  it('c27 n5: the band reaches the box\'s real bottom where the box keeps a gap under its last row', () => {
    expect(css).toMatch(/@media \(min-width: 901px\)\s*\{\s*:is\(\.ct-stack-table, \.ct-stack-rest, \.ct-stack-fill, \.ct-scroll, \.ct-fade-scroll\)\[data-more-y\]::after\s*\{\s*bottom:\s*-0\.5rem;/);
    expect(css).toMatch(/\.ct-stack-table, \.ct-stack-rest, \.ct-stack-fill, \.ct-scroll, \.ct-fade-scroll \{ padding-bottom: 0\.5rem; \}/);
  });
});

describe('U16-F13a the boxes layout.ts marks (R5 c27 M1) and the floors of a plot with no holder (R5 c05 M1, M3)', () => {
  it('c27 M1: the C21 evidence card, which scrolls as a whole, is a marked box with the cue; so is a filling card\'s note', () => {
    for (const box of ['.ct-stack[data-block="finding-evidence"]', '.caos-plot.fill > .caos-plot-note']) {
      expect(SCROLL_BOXES).toContain(box);
      // the cue's band and the right fade are drawn on it
      const rules = [...css.matchAll(/:is\(([^{]*)\)\[data-more-(y|x)\]/g)].map((m) => m[1]).filter((r) => r.includes('.ct-panels-fill'));
      expect(rules.length).toBe(2);
      for (const r of rules) expect(r).toContain(box);
    }
    // the probe measures the very boxes layout.ts marks
    expect(BOXES).toBe(SCROLL_BOXES);
  });
  it('c05 M1, M3: a plot with no floor holder is sized by its card\'s body, a holder first', () => {
    const body = { tag: 'body' };
    const holder = { tag: 'holder' };
    const plot = (withHolder: boolean) => ({ closest: (sel: string) => (sel.includes('data-plot-floor') ? (withHolder ? holder : null) : sel.includes('caos-plot-body') ? body : null) });
    expect(sizerOf(plot(false) as never)).toBe(body);
    expect(sizerOf(plot(true) as never)).toBe(holder);
    expect(sizerOf({ closest: () => null } as never)).toBeNull();
    // a plot inside a box that scrolls in its card (a panel grid) grows its own drawing, which the box then scrolls
    const host = { tag: 'host' };
    expect(sizerOf({ parentElement: host, closest: (sel: string) => (sel.includes('ct-panels-fill') ? { tag: 'grid' } : sel.includes('caos-plot-body') ? body : null) } as never)).toBe(host);
  });
  it('c05 M1: a body grown in a card of a fixed height leaves the note its first lines; a card that flows takes what it needs', () => {
    const keep = toPx(NOTE_KEEP, REM);
    expect(bodyRoom({ inner: 500, others: [40], note: 300, flows: false }, REM)).toBe(500 - 40 - keep);
    // a short note keeps its whole height
    expect(bodyRoom({ inner: 500, others: [40], note: 30, flows: false }, REM)).toBe(430);
    expect(bodyRoom({ inner: 500, others: [40], note: null, flows: false }, REM)).toBe(460);
    expect(bodyRoom({ inner: 500, others: [40], note: 300, flows: true }, REM)).toBe(Number.POSITIVE_INFINITY);
  });
  it('c05 M1: a C04 note gives way to the drawing\'s floor on a wide screen (it scrolls with the cue), never takes the plot\'s height', () => {
    expect(notesCss).not.toMatch(/flex:\s*0 0 auto/);
    expect(notesCss).toMatch(/@media \(min-width: 901px\)\s*\{[^}]*flex:\s*0 1 auto;[^}]*overflow-y:\s*auto/);
  });
});

describe('U16-F13a the probe counts on its own (R5 c06 B1: it computed the cue\'s rule) and sees what R5 found it blind to', () => {
  it('reads a row by its glyphs under the band as drawn, and judges the cue\'s count exactly', () => {
    // the band of 36.8 px, its fade to the surface at 55 %: half opaque 10.1 px under its top
    expect(bandOpacity(0, BAND, 0.55)).toBe(0);
    expect(bandOpacity(BAND * 0.55, BAND, 0.55)).toBe(1);
    const band = { top: 494.2, height: BAND, stop: 0.55, visibleBottom: 531 };
    expect(unreadable({ top: 477, bottom: 490 }, band)).toBe(false);
    expect(unreadable({ top: 510, bottom: 523 }, band)).toBe(true);
    expect(cueCount('20 more rows below: scroll the box')).toBe(20);
    expect(cueCount('1 fila más abajo: desplace el recuadro')).toBe(1);
    expect(cueCount('Hay más abajo: desplace el recuadro')).toBe(0);
    const found = judge({
      boxes: [
        { name: 'by-year', below: true, right: false, rows: 19, cue: '20 more rows below: scroll the box', gap: 0, fadeRight: false },
        { name: 'gap', below: true, right: false, rows: 2, cue: '2 more rows below: scroll the box', gap: 8, fadeRight: false },
        { name: 'ok', below: true, right: false, rows: 2, cue: '2 more rows below: scroll the box', gap: 0, fadeRight: false },
        // "2" is in "12": the earlier `includes` passed it
        { name: 'twelve', below: true, right: false, rows: 2, cue: '12 more rows below: scroll the box', gap: 0, fadeRight: false },
      ],
      bodies: [{ name: 'transfer', over: 389 }],
      plots: [{ name: 'plot', h: 55, floor: 144, bars: false, holder: false, scroll: 0 }],
      notes: [{ name: 'cued', over: 40, cue: true }, { name: 'cut', over: 40, cue: false }],
      unlisted: [{ name: 'finding-evidence', over: 400 }],
    });
    expect(found.map((f: string) => f.split(':')[0])).toEqual(['by-year', 'gap', 'twelve', 'finding-evidence', 'transfer', 'cut', 'plot']);
  });
  it('visits the views of the R5 rows', () => {
    const views = (TARGETS as Array<{ caseId: string; variant: string | null; group: string; sub: string | null }>).map((t) => `${t.caseId}/${t.variant} ${t.group}/${t.sub}`);
    for (const v of ['C04/sp validation/by-year', 'C04/sp validation/tests', 'C04/sp validation/lifetime', 'C04/null validation/pd-by-grade', 'C04/null validation/semesters', 'C04/markov validation/estimators', 'C04/thin validation/overlap', 'C02/h1 horizons/transfer', 'C02/h1 context/null', 'C21/null findings/null', 'C16/list-adverse sensitivity/share', 'C01/holdout model/penalised']) expect(views).toContain(v);
  });
});

// C02 (R5 c03 M1, M2)
type C02Outputs = components['schemas']['c02Outputs'];
const C02_TITLE = { en: 'Corporate PD across horizons', es: 'PD corporativa a distintos horizontes' };
const c02Models = committedDoc<ModelsArtifact>('C02', 'models-polish-horizons');
const c02Sel = (id: string): C02Sel => defaultSel(fixtureData('C02', committedDoc<VariantArtifact<C02Outputs>>('C02', id) as unknown as VariantArtifact, c02Models, C02_TITLE)) as C02Sel;

describe('U16-F13a C02 (R5 c03)', () => {
  for (const id of ['h1', 'h3', 'h5']) {
    it(`${id} M2: the 25 transfer bars scroll in their own box under the matrix (a marked box with the cue), never past the card body`, () => {
      for (const lang of LANGS) {
        setLang(lang);
        const m = html(<TransferView sel={c02Sel(id)} />);
        const at = m.indexOf('data-block="transfer-bars"');
        expect(at, `${id} ${lang}`).toBeGreaterThan(-1);
        // the box is one layout.ts marks, and the drawing box sits in it, after the matrix
        expect(m.slice(m.lastIndexOf('<div', at), at)).toMatch(/class="ct-stack-rest"/);
        expect(m.indexOf('class="ct-stack-chart"', at)).toBeGreaterThan(at);
        expect(m.indexOf('data-table="transfer"')).toBeLessThan(at);
      }
    });
  }
  it('M1: the split keeps each count whole and may break between them; the holdout count is whole in both languages', () => {
    for (const lang of LANGS) {
      setLang(lang);
      const m = html(<C02ContextView sel={c02Sel('h1')} />);
      const dd = /<dl class="ct-defs" data-table="c02-split"><dt>[^<]*<\/dt><dd([^>]*)>([\s\S]*?)<\/dd>/.exec(m);
      expect(dd).not.toBeNull();
      expect(dd![1]).not.toMatch(/nowrap/);
      expect([...dd![2].matchAll(/<span style="white-space:nowrap">([^<]*)<\/span>/g)].map((x) => x[1])).toEqual(lang === 'es' ? ['3.309', '828', '1.773'] : ['3,309', '828', '1,773']);
    }
  });
});

// C01 (R5 c01 M1, M3)
const c01Sel = (v: string) => {
  const data = committedData('C01', v);
  return { data, challenger: defaultChallenger(data.variant), alphas: COMMITTED, approval: 0.8, lgd: 0.5, applicant: 0 } as never;
};
/** The body rows of a table of a markup: the cells' text of each row. */
const bodyRows = (m: string, from: string) => {
  const at = m.indexOf(from);
  const t = m.slice(m.indexOf('<tbody>', at), m.indexOf('</tbody>', at));
  return [...t.matchAll(/<tr[^>]*>([\s\S]*?)<\/tr>/g)].map((r) => r[1]);
};

describe('U16-F13a C01 (R5 c01 M1, M3; ruling 2 on every tests table)', () => {
  for (const v of variantIds('C01')) {
    it(`${v} M3: every row of the battery names its segment, the PSI and DeLong rows too; Jeffreys no longer alone`, () => {
      for (const lang of LANGS) {
        const word = lang === 'es' ? 'cartera' : 'portfolio';
        const battery = render(<BatteryView sel={c01Sel(v)} />, lang);
        const rows = bodyRows(battery, 'ct-battery');
        expect(rows.length).toBe(14);
        for (const r of rows) expect(r, `${v} ${lang}`).toMatch(new RegExp(`<span class="ct-row-detail" data-segment="portfolio">${word}</span>`));
        expect(textOf(battery)).not.toMatch(/Jeffreys, (cartera|portfolio)/);
        const psi = bodyRows(render(<StabilityView sel={c01Sel(v)} />, lang), lang === 'es' ? 'Estabilidad poblacional' : 'Population stability');
        expect(psi.length).toBeGreaterThan(0);
        for (const r of psi) expect(r).toMatch(/class="ct-row-detail" data-segment="portfolio"/);
        const dl = bodyRows(render(<DiscriminationView sel={c01Sel(v)} />, lang), lang === 'es' ? 'AUC fuera de muestra' : 'Held-out AUC');
        for (const r of dl) expect(r).toMatch(/class="ct-row-detail" data-segment="portfolio"/);
      }
    });
  }
  for (const v of ['drift-moderate', 'drift-severe', 'prior-shift', 'small-sample']) {
    it(`${v} M1: every CSI evidence line of a red-row finding prints the input's p and light, in both languages`, () => {
      for (const lang of LANGS) {
        const m = render(<FindingsView sel={c01Sel(v)} />, lang);
        const label = lang === 'es' ? 'CSI de cada variable (' : 'CSI of each input (';
        const lines = [...m.matchAll(/<li>([\s\S]*?)<\/li>/g)].map((x) => textOf(x[1])).filter((l) => l.includes(label));
        const csi = committedData('C01', v).variant.findings.filter((f) => f.status === 'open').flatMap((f) => f.evidence).filter((e) => e.startsWith('stability.csi@'));
        if (csi.length === 0) continue;
        expect(lines.length, `${v} ${lang}`).toBe(csi.length);
        for (const l of lines) expect(l, `${v} ${lang}`).toMatch(lang === 'es' ? /: p (< )?\S+, (rojo|ámbar|verde)$/ : /: p (< )?\S+, (red|amber|green)$/);
      }
    });
  }
});

describe('U16-F13a a tests row of no segment names its scope in words (R5 ruling 2)', () => {
  for (const v of variantIds('C09')) {
    it(`C09 ${v}: the U6 tests table says "whole portfolio" / "toda la cartera" on a row whose document gives no segment`, () => {
      const d = committedData('C09', v);
      const none = d.variant.tests.filter((t) => t.segment === null).length;
      for (const lang of LANGS) {
        const m = render(<U6TestsTable variant={d.variant} />, lang);
        expect((m.match(/data-segment="none">[^<]*</g) ?? []).map((s) => s.slice(20, -1)).filter((s) => s === (lang === 'es' ? 'toda la cartera' : 'whole portfolio')).length).toBe(none);
        expect(m).not.toMatch(/data-segment="null"/);
      }
    });
  }
});

// The minors of the R5 rows fixed in this unit's files
const src = (rel: string) => readFileSync(new URL(rel, import.meta.url), 'utf8');
const c04Manifest = JSON.parse(readFileSync(new URL('../../../data/derived/manifests/C04.json', import.meta.url), 'utf8')) as CaseManifest;
const c04Data = (id: string): CaseData => {
  const e = c04Manifest.artifacts.find((a) => a.role === 'variant' && a.variant_id === id)!;
  const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(`../../../data/derived/${rel}`, import.meta.url), 'utf8')) as T;
  return { manifest: c04Manifest, variant: read<VariantArtifact>(e.path), models: read<ModelsArtifact>(e.models_ref as string) };
};

describe('U16-F13a the minors of the R5 rows', () => {
  it('c01 n1, c02 n3: the C01 severity note states the red-row findings\' severities, in both languages', () => {
    for (const lang of LANGS) {
      const t = textOf(render(<FindingsView sel={c01Sel('holdout')} />, lang));
      expect(t).toContain(lang === 'es' ? 'S3 para una prueba de ajuste o una comparación de DeLong, S2 para cualquier otra prueba de cualquier peldaño' : 'S3 for a fit test or a DeLong comparison, S2 for any other test of any rung');
    }
  });
  it('c01 n4, c02 n1: the reasons\' card keeps its own height; the distribution takes the rest above its floor', () => {
    for (const v of ['holdout', 'label-noise']) {
      const m = render(<ScorecardView sel={c01Sel(v)} />, 'es');
      const card = m.indexOf(v === 'holdout' ? 'razones principales' : 'Las cuatro características más fuertes');
      expect(m.lastIndexOf('<div class="ct-part" style="flex:0 0 auto">', card), v).toBeGreaterThan(-1);
      expect(m.lastIndexOf('<div class="ct-part"', card)).toBe(m.lastIndexOf('<div class="ct-part" style="flex:0 0 auto">', card));
    }
  });
  it('sweep: the conventional PSI band of the Stability table reads in Spanish, never the engine\'s English words', () => {
    expect(bandText('little change', 'es')).toBe('cambio pequeño');
    expect(bandText('significant change', 'es')).toBe('cambio significativo');
    expect(bandText('little change', 'en')).toBe('little change');
    for (const v of variantIds('C01')) expect(textOf(render(<StabilityView sel={c01Sel(v)} />, 'es')), v).not.toMatch(/little change|significant change|moderate change/);
  });
  it('c03 n8: the By horizon interval stays on one line, its header spaced', () => {
    for (const lang of LANGS) {
      setLang(lang);
      const m = html(<C02ContextView sel={c02Sel('h1')} />);
      void m;
    }
    expect(src('./c02/C02Common.tsx')).toMatch(/style=\{\{ whiteSpace: 'nowrap' \}\}>\{r \? span\(f3\(r\.discrimination\.auc_ci\.lo/);
    expect(src('./c02/C02Common.tsx')).not.toContain("'95% interval'");
  });
  it('c05 n4: the Markov Findings evidence names test 3 as its Size table does, "Against the reference matrix"', () => {
    for (const lang of LANGS) {
      setLang(lang);
      const t = textOf(html(<C04FindingsView sel={makeSel(c04Data('markov'))} />));
      expect(t).toContain(lang === 'es' ? 'Contra la matriz de referencia' : 'Against the reference matrix');
      expect(t).not.toMatch(/Cohort against the pooled matrix|Cohorte contra la matriz agrupada/);
    }
  });
  it('c05 n2: the evidence charts draw the cited points only, the room each side an axis range', () => {
    for (const id of ['sp', 'markov']) {
      const v = c04Data(id).variant;
      const ev = findingsEvidence(v);
      const d = findingsDrawing(v, ev, 6);
      expect(d, id).not.toBeNull();
      const n = d!.chart.x.values.length;
      expect(d!.chart.x.values[0]).toBe(1);
      expect(d!.chart.x.range).toEqual([0.5, n + 0.5]);
      for (const s of d!.chart.series) expect(s.values.length).toBe(n);
    }
  });
  it('c06 q3, q4, c24 n2: "N\u2020" throughout the Papers views, "Year from the start" on the drift axis, "Computed beforehand from"', () => {
    // the code's text, not its comments
    const code = src('./c04/PublishedViews.tsx').split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*\*)/.test(l)).join('\n');
    expect(code).not.toMatch(/N dagger|N daga/);
    expect(src('./c04/LiveViews.tsx')).not.toContain("'Years from the start'");
    expect(src('./c04/C04Common.tsx')).not.toContain('Computed in the bake');
    expect(src('./names/index.ts')).not.toContain('Computed in the bake');
  });
});

describe('U16-F13a the coordinator\'s items: the scope words of `all`, the C03 model names of the findings (R5 ruling 2, c04 N1)', () => {
  it('ruling 2: the generic `all` segment is the whole portfolio; C12\'s counterparty book alone is the whole book', () => {
    expect(segmentName('all', { caseId: 'C06' })).toEqual({ en: 'whole portfolio', es: 'toda la cartera' });
    expect(segmentName('all', { caseId: 'C01' })).toEqual({ en: 'whole portfolio', es: 'toda la cartera' });
    expect(segmentName('all', { caseId: 'C12' })).toEqual({ en: 'whole book', es: 'toda la cartera' });
  });
  it('c04 N1: the names module names the C03 rungs as the C03 views do (rungLabel, by the kind the models artifact gives)', () => {
    expect(VIEW_KIND_TEXT.C03).toEqual(KIND_TEXT);
    const sel = { data: committedData('C03', variantIds('C03')[0]) } as never;
    const gen = JSON.parse(readFileSync(new URL('./names/models.gen.json', import.meta.url), 'utf8')) as { models: Record<string, Record<string, unknown>> };
    for (const id of ['P0-constant', 'P1-scorecard', 'P2a-l1', 'P2b-pltr', 'P3-ebm', 'P4-lightgbm']) {
      expect(gen.models.C03[id], id).toEqual(rungLabel(sel, id));
      expect(modelName(id, { caseId: 'C03' }), id).toEqual(rungLabel(sel, id));
    }
  });
});

describe('U16-F13a the items of U16-F13c and U16-F13d in this unit\'s files', () => {
  it('c13 N1: the C10 Euler level prints "99.9 %" with the no-break space, in both languages', () => {
    expect(segmentName('var-0.999', { caseId: 'C10' })).toEqual({ en: 'VaR at 99.9\u00a0%', es: 'VaR al 99,9\u00a0%' });
  });
  it('c11 n3: the U6 tests table keeps a statistic\'s trailing zeros at four significant digits', () => {
    expect(statText(0.12, 'en')).toBe('0.1200');
    expect(statText(0.12, 'es')).toBe('0,1200');
    expect(statText(12.5, 'en')).toBe('12.50');
    expect(statText(3, 'en')).toBe('3.000');
  });
});
