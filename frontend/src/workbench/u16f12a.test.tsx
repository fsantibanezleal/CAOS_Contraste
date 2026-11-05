// Fix round 5, unit U16-F12a (the shared table boxes and drawing floors, the tests tables, the names module, the engine-note rules
// and C01), from the fourth capture review (R4) on rc4, on the committed documents and in both languages. Each test names the row it
// closes and fails on its defect. What only a browser can measure (a box's cue, a plot's height at 1280 and 390) is measured by
// layout-probe.mjs on the built site; these tests hold the markup and the rules that the probe's measures rest on.
import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it } from 'vitest';
import { COMMITTED } from '../lib/policy';
import { C01WriteUp } from '../content/cases/C01';
import { committedData, render, textOf, variantIds, type Lang } from './c03/u16f2-kit';
import { setLang } from './c03/u6-testkit';
import { U6TestsTable, segmentLabels } from './c03/U6Shared';
import { U14TestsTable } from './c20/U14Common';
import { ContextView } from './ContextView';
import { FindingsView } from './FindingsView';
import { ImpactView } from './ImpactView';
import { CapitalView } from './CapitalView';
import { defaultChallenger } from './model';
import { EbmCategoriesView, EbmView, LadderView, ModelGroup, PenalisedView, ScorecardView } from './ModelViews';
import { VariantsTable } from './VariantsView';
import { ruleText } from './c01Text';
import { DESIGN_LIMITS, OUTPUT_BLOCKS, TEST_NAMES, segmentName } from './names';
import { caseLabel } from './caseLabels';
import { TEST_NOTE_RULES, localise } from './c14/localise';
import { noteText, platformText } from './c08/notes';
import { DEFAULT_PLOT_FLOOR, SCROLL_BOXES, cueText, toPx } from './layout';
// @ts-expect-error the probe is plain JavaScript, run by node with Playwright (src/workbench/layout-probe.mjs)
import { TARGETS, judge } from './layout-probe.mjs';

const LANGS: Lang[] = ['en', 'es'];
afterEach(() => setLang('en'));

const c01Sel = (v: string) => {
  const data = committedData('C01', v);
  return { data, challenger: defaultChallenger(data.variant), alphas: COMMITTED, approval: 0.8, lgd: 0.5, applicant: 0 } as never;
};
const C01 = variantIds('C01');
const css = readFileSync(new URL('../styles/contraste.css', import.meta.url), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
/** The body rows of a markup's tables: [data-test, text of the row]. */
const testRows = (m: string) => [...m.matchAll(/<tr[^>]*data-test="([^"]+)"[^>]*>([\s\S]*?)<\/tr>/g)].map((r) => ({ test: r[1], html: r[2], text: textOf(r[2]) }));

describe('U16-F12a the shared boxes and floors (R4 ruling 8: c01 M1, M2, c11 M1, c13 M1, c19 M1, c20 M1, c23 M1, c26 M1, c27 M1)', () => {
  it('a stack gives its tables the room they need: no fixed share caps the table box (contraste.css:129 max-height 42 %)', () => {
    const rule = /\.ct-stack-table\s*\{([^}]*)\}/.exec(css)?.[1] ?? '';
    expect(rule).toMatch(/overflow:\s*auto/);
    expect(rule).not.toMatch(/max-height/);
    // nor does a case's own box cap it again (C12 68 %, C17 74 %, C21 60 %)
    expect(css).not.toMatch(/\.ct-stack-table\s*\{[^}]*max-height:\s*\d+%/);
  });
  it('the cue of a box with content below is drawn over its last visible line, at every width, from the measured text (contraste.css:156-163)', () => {
    // the earlier fade masked a blank gap at the box's bottom: nothing to see when the box ended on a row boundary
    expect(css).not.toMatch(/mask-image:\s*linear-gradient\(to bottom/);
    expect(css).toMatch(/\[data-more-y\]::after\s*\{[^}]*content:\s*attr\(data-more-text\)/);
    expect(css).toMatch(/\[data-more-y\]::after\s*\{[^}]*position:\s*sticky/);
    expect(css).toMatch(/\[data-more-x\]\s*\{[^}]*mask-image:\s*linear-gradient\(to right/);
    for (const box of ['.ct-stack-table', '.ct-stack-rest', '.ct-scroll', '.ct-panels-fill']) expect(SCROLL_BOXES).toContain(box);
  });
  it('the cue counts the rows below in the reader\'s language', () => {
    expect(cueText(3, 'en')).toBe('3 more rows below: scroll the box');
    expect(cueText(1, 'es')).toBe('1 fila más abajo: desplace el recuadro');
    expect(cueText(0, 'es')).toMatch(/^Hay más abajo/);
    expect(toPx('14rem', 16)).toBe(224);
    expect(toPx(DEFAULT_PLOT_FLOOR, 16)).toBeGreaterThanOrEqual(144);
  });
  it('a panel grid row grows with its panel, never a fixed 320 px row under a key of eight series (c26 M1, c27 M1)', () => {
    const grid = /\.ct-panels-fill\s*\{([^}]*)\}/.exec(css)?.[1] ?? '';
    expect(grid).not.toMatch(/minmax\(320px/);
    expect(grid).toMatch(/grid-auto-rows:\s*minmax\(auto, 1fr\)/);
  });
  it('the probe judges a box with rows below and no cue, a plot under its floor and a cut note, and visits every row of the R4 report', () => {
    const found = judge({
      boxes: [{ name: 'box', below: true, right: false, rows: 3, cue: '', fadeRight: false }, { name: 'ok', below: true, right: true, rows: 2, cue: '2 more rows below: scroll the box', fadeRight: true }],
      bodies: [{ name: 'body', over: 12 }],
      plots: [{ name: 'plot', h: 10, floor: 144, bars: false, scroll: 0 }, { name: 'bars', h: 300, floor: 144, bars: true, scroll: 11 }],
      notes: [{ name: 'note', over: 17 }],
    });
    expect(found).toHaveLength(5);
    const views = (TARGETS as Array<{ caseId: string; group: string; sub: string | null }>).map((t) => `${t.caseId} ${t.group}/${t.sub}`);
    for (const v of ['C01 model/scorecard', 'C01 compare/null', 'C01 impact/decision', 'C09 ccf/by-design', 'C10 capital/rungs', 'C16 compare/null', 'C18 capital/stack', 'C22 validation/p-values', 'C22 validation/power']) expect(views).toContain(v);
  });
});

describe('U16-F12a C01 (R4 c01 B1, M1 to M4, c02 M1, M2)', () => {
  it('B1: the Spanish equation of the write-up names its terms in Spanish; the English keeps its own', () => {
    const es = render(<C01WriteUp />, 'es');
    const en = render(<C01WriteUp />, 'en');
    expect(es).not.toMatch(/Points|Offset/);
    expect(es).toMatch(/Puntos/);
    expect(es).toMatch(/Desplazamiento/);
    expect(en).toMatch(/Points/);
    expect(en).toMatch(/Offset/);
  });
  for (const v of ['holdout', 'german-twin']) {
    it(`${v} M1 (c02 M1): the applicant's distribution keeps its plot's floor in its own part, the reasons scroll in theirs`, () => {
      for (const lang of LANGS) {
        const m = render(<ScorecardView sel={c01Sel(v)} />, lang);
        expect(m).toMatch(/<div class="ct-part" data-plot-floor="11rem" data-block="applicant-distribution"/);
        // the reasons' table sits in a scroll box of its card, so the column gives the drawing its floor and the table its cue
        const reasons = m.slice(m.indexOf(lang === 'es' ? 'razones principales' : 'principal reasons'));
        expect(reasons.indexOf('class="ct-scroll"')).toBeGreaterThan(-1);
        expect(reasons.indexOf('class="ct-scroll"')).toBeLessThan(reasons.indexOf('applicant-distribution'));
      }
    });
  }
  for (const v of C01) {
    it(`${v} M2 (c02 M2): the variants' table and its drawing sit side by side, the note names the table without "above"`, () => {
      for (const lang of LANGS) {
        const all = C01.map((id) => committedData('C01', id).variant);
        const m = render(<VariantsTable sel={c01Sel(v)} all={all} onPick={() => undefined} />, lang);
        expect(m).toMatch(/caos-views-row/);
        expect(textOf(m)).not.toMatch(/table above|tabla de arriba/);
      }
    });
  }
  for (const v of ['holdout', 'german-twin']) {
    it(`${v} M3 (n1, c02 m1): the pipeline table's columns carry the rung codes and the note names the models`, () => {
      for (const lang of LANGS) {
        const m = render(<ImpactView sel={c01Sel(v)} />, lang);
        const at = m.indexOf(lang === 'es' ? 'Campeón, luego retador' : 'Champion, then challenger');
        const head = m.slice(at, m.indexOf('</thead>', at));
        const cols = [...head.matchAll(/<th[^>]*>([^<]*)<\/th>/g)].map((c) => c[1]);
        expect(cols).toEqual(['P1', 'P4']);
      }
    });
  }
  it('M4: every variant shows at most six peer sub-views of the model; the German TabPFN is a card of the Ladder', () => {
    for (const v of C01) {
      for (const lang of LANGS) {
        const m = render(<ModelGroup sel={c01Sel(v)} />, lang);
        expect([...m.matchAll(/role="tab"/g)].length, `${v} ${lang}`).toBeLessThanOrEqual(6);
      }
    }
    const ladder = render(<LadderView sel={c01Sel('german-twin')} />, 'en');
    expect(ladder).toMatch(/TabPFN v2, research challenger/);
    expect(ladder).toMatch(/PriorLabs-TabPFN/);
    // in Spanish the licence reads in Spanish, the attribution quoted in its original (R4 ruling 6)
    const es = textOf(render(<LadderView sel={c01Sel('german-twin')} />, 'es'));
    expect(es).not.toMatch(/TabPFN v2 weights|plus attribution/);
    expect(es).toMatch(/pesos de TabPFN v2/);
    expect(es).toMatch(/«Built with PriorLabs-TabPFN»/);
  });
});

describe('U16-F12a C01 minors (R4 c01 n2, n3, n4, n12, n13, n16; c02 m8, m9, m10, m12)', () => {
  it('n2: the Spanish write-up and the PLTR rule header call the training split "partición", never "tramo"', () => {
    const es = textOf(render(<C01WriteUp />, 'es'));
    expect(es).not.toMatch(/tramo de (entrenamiento|calibración)/);
    expect(es).toMatch(/partición de calibración/);
    expect(textOf(render(<PenalisedView sel={c01Sel('holdout')} />, 'es'))).not.toMatch(/tramo de entrenamiento/);
  });
  it('n3: a percent is written with a no-break space before the sign, in both languages, as the shell writes it', () => {
    for (const lang of LANGS) {
      const t = textOf(render(<C01WriteUp />, lang));
      expect(t, lang).not.toMatch(/\d%/);
    }
    expect(textOf(render(<CapitalView sel={c01Sel('holdout')} />, 'en'))).not.toMatch(/\d%/);
    expect(textOf(render(<ImpactView sel={c01Sel('holdout')} />, 'en'))).not.toMatch(/\d%/);
  });
  it('n4 and c02 m8: the Spanish wording, and the capital sentence says it is the holdout\'s', () => {
    const es = textOf(render(<C01WriteUp />, 'es'));
    expect(es).not.toMatch(/pagaron todo los seis meses/);
    expect(es).toMatch(/En la muestra reservada, con 80/);
    expect(textOf(render(<C01WriteUp />, 'en'))).toMatch(/On the holdout, at 80/);
    // the licence class starts its sentence after a licence that ends with a full stop
    expect(textOf(render(<ContextView sel={c01Sel('holdout')} />, 'es'))).not.toMatch(/\. espejo permitido/);
  });
  it('n12 (c02 m10) and c02 m12: the EBM categories note parses, and a shape panel\'s series is the log-odds, not the x title', () => {
    expect(textOf(render(<EbmCategoriesView sel={c01Sel('holdout')} />, 'en'))).toMatch(/a code the codebook does not document is labelled undocumented/);
    const m = render(<EbmView sel={c01Sel('holdout')} />, 'en');
    expect(m).not.toMatch(/an input the codebook leaves/);
  });
  it('n13 and c02 m9: the evidence note writes 1E-16 as the product prints it, and the readout gives the committed p', () => {
    for (const v of ['holdout', 'label-noise']) {
      const en = textOf(render(<FindingsView sel={c01Sel(v)} />, 'en'));
      expect(en).not.toMatch(/1e-16/);
      expect(en).toMatch(/the readout gives its value/);
    }
  });
  it('n16: an English rule threshold of a thousand or more is grouped, as the Spanish one is', () => {
    expect(ruleText('LIMIT_BAL <= 145000', 'en')).toBe('LIMIT_BAL <= 145,000');
    expect(ruleText('LIMIT_BAL <= 145000', 'es')).toBe('LIMIT_BAL <= 145.000');
    expect(ruleText('EDUCATION > 0.0524', 'en')).toBe('EDUCATION > 0.0524');
  });
});

describe('U16-F12a the tests tables show the segment on every row (R4 ruling 3, c04 M1)', () => {
  it('C03: a portfolio row says "portfolio" / "cartera", every row of every variant', () => {
    for (const v of variantIds('C03')) {
      const d = committedData('C03', v);
      for (const lang of LANGS) {
        const rows = testRows(render(<U6TestsTable variant={d.variant} />, lang));
        expect(rows.length).toBe(d.variant.tests.length);
        const bare = rows.filter((r) => !/data-segment="/.test(r.html));
        expect(bare.map((r) => r.test), `${v} ${lang}`).toEqual([]);
        expect(rows.some((r) => r.text.includes(lang === 'es' ? 'cartera' : 'portfolio'))).toBe(true);
      }
    }
  });
  it('C02 and C20: the U14 tests table names the segment of every row, the portfolio too', () => {
    for (const [c, v] of [['C02', 'h1'], ['C02', 'pooled'], ['C20', 'leakage-planted']] as const) {
      const d = committedData(c, v);
      const rows = testRows(render(<U14TestsTable tests={d.variant.tests} caseId={c} models={d.variant.model} />, 'es'));
      expect(rows.filter((r) => !/data-segment="/.test(r.html)).map((r) => r.test), `${c} ${v}`).toEqual([]);
    }
    const labels = segmentLabels([{ test_id: 't', model_id: 'm', segment: 'portfolio' }], 'C03');
    expect(labels[0]).toEqual({ en: 'portfolio', es: 'cartera' });
  });
});

describe('U16-F12a the names module (R4 c03 NB3, c22 M1, c23 M2, c18 m11, c04 m12)', () => {
  it('NB3: the pooled horizon input of C02 is named, never "input horizon_years"', () => {
    const n = segmentName('characteristic:horizon_years', { caseId: 'C02' });
    expect(n).not.toBeNull();
    for (const lang of LANGS) expect(n![lang]).not.toMatch(/horizon_years/);
    const d = committedData('C02', 'pooled');
    const t = textOf(render(<U14TestsTable tests={d.variant.tests} caseId="C02" models={d.variant.model} />, 'en'));
    expect(t).not.toMatch(/horizon_years/);
  });
  it('c22 M1, c23 M2: the C18 design limit holds market and operational losses at their expected loss and keeps IRRBB out of the capital path', () => {
    const d = DESIGN_LIMITS['non-credit-losses-at-expected-loss'];
    expect(d.en).toBe('market and operational losses are held at their expected loss; IRRBB stays out of the capital path');
    expect(d.es).toBe('las pérdidas de mercado y operacional se fijan en su pérdida esperada; el IRRBB queda fuera de la trayectoria de capital');
    // the committed losses agree: no scenario carries an IRRBB loss
    for (const v of variantIds('C18').filter((x) => x !== 'reverse-stress')) {
      const losses = (committedData('C18', v).variant.outputs as { losses?: { scenario_losses?: Array<{ irrbb: number }> } }).losses?.scenario_losses ?? [];
      for (const s of losses) expect(s.irrbb, v).toBe(0);
    }
  });
  it('c18 m11: the C15 design limit names the three Annex 1 tests, and the Spanish says "reajustabilidad" as the case does', () => {
    expect(DESIGN_LIMITS['annex1-prioritised-bank-tests'].en).toMatch(/18 percent of the 12-month net interest and indexation margin/);
    expect(DESIGN_LIMITS['annex1-prioritised-bank-tests'].es).toMatch(/18 por ciento del margen de intereses y reajustabilidad de 12 meses/);
    expect(DESIGN_LIMITS['indexation-charge-is-a-standard-add-on'].es).toMatch(/reajustabilidad/);
    expect(DESIGN_LIMITS['indexation-charge-is-a-standard-add-on'].es).not.toMatch(/indexación/);
  });
  it('c04 m12: the C03 training window names the 2007 to 2009 recession as its title does', () => {
    expect(DESIGN_LIMITS['training-window-before-the-crisis'].en).toMatch(/2007 to 2009/);
    expect(DESIGN_LIMITS['training-window-before-the-crisis'].es).toMatch(/2007 a 2009/);
  });
});

describe('U16-F12a the engine-note rules (R4 c28 B1: the C11 reason in English on the Spanish Experiments page)', () => {
  it('the C11 producer\'s reasons read in Spanish through the shared notes', () => {
    expect(noteText('no model is eligible: every model fails at least one gate', 'es')).toBe('ningún modelo es elegible: cada modelo falla al menos una compuerta');
    expect(noteText('challenger only: it must enter the 75 percent MCS on FZ0 out of sample, and the published run does not train it', 'es')).toMatch(/^solo retador: debe entrar al MCS de 75 por ciento/);
    expect(noteText('no model is eligible: every model fails at least one gate', 'en')).toBe('no model is eligible: every model fails at least one gate');
  });
  it('every reason a committed C11 document writes has its Spanish', () => {
    for (const v of variantIds('C11')) {
      const doc = committedData('C11', v).variant as unknown as Record<string, unknown>;
      const reasons = new Set<string>();
      const walk = (o: unknown) => {
        if (Array.isArray(o)) return o.forEach(walk);
        if (!o || typeof o !== 'object') return;
        for (const [k, x] of Object.entries(o)) {
          if ((k === 'reason' || k === 'reason_if_null') && typeof x === 'string') reasons.add(x);
          else walk(x);
        }
      };
      walk(doc);
      for (const r of reasons) if (/^no model is eligible|^challenger only/.test(r)) expect(noteText(r, 'es'), r).not.toBe(r);
    }
  });
});

describe('U16-F12a the changes the other units named in these files (F12d D3 items 1 to 5, F12e D3)', () => {
  it('C12 B1: the Spanish case label and the swaption test names read "permutas" and "opción sobre permuta" (ruling 6)', () => {
    expect(caseLabel('C12', { en: 'x', es: 'x' }, 'es')).toBe('CVA de cartera de permutas');
    expect(TEST_NAMES['ccr.quantlib_swaption_payer'].es).toBe('Opción sobre permuta pagadora frente a QuantLib 1.44');
    expect(TEST_NAMES['ccr.quantlib_swaption_receiver'].es).toBe('Opción sobre permuta receptora frente a QuantLib 1.44');
    expect(platformText('open-source-risk-engine 1.8.17.0 wheel, CPython 3.13', 'es')).not.toMatch(/wheel/);
    expect(platformText('open-source-risk-engine 1.8.17.0 wheel, CPython 3.13', 'es')).toMatch(/paquete,/);
  });
  it('U16-F12g D3: a C11 tail level reads in words, and the Spanish test names carry no swap or benchmark', () => {
    expect(segmentName('alpha=0.025', { caseId: 'C11' })).toEqual({ en: '2.5\u00a0% tail (97.5\u00a0% VaR)', es: 'cola de 2,5\u00a0% (VaR al 97,5\u00a0%)' });
    expect(segmentName('alpha=0.01', { caseId: 'C11' })?.es).toBe('cola de 1\u00a0% (VaR al 99\u00a0%)');
    for (const id of ['ccr.ee_analytic_vs_simulated', 'oprisk.benchmark_reproduction', 'ccr.quantlib_swaption_payer']) expect(TEST_NAMES[id].es).not.toMatch(/swap|benchmark/i);
  });
  it('C15 n1, n2: the floors evidence block has a name, and the estimation-window note reads in Spanish through the IRRBB rules', () => {
    expect(OUTPUT_BLOCKS['floors.distances']).toEqual({ en: 'the distance of each leg and shock to its post-shock floor (Floors view)', es: 'la distancia de cada tramo y choque a su piso posterior al choque (vista de pisos)' });
    expect(localise('not evaluated: fewer than 3 estimation windows', 'es', TEST_NOTE_RULES)).toBe('no evaluada: menos de 3 ventanas de estimación');
  });
});
