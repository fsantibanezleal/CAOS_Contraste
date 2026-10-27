// Fix round 4, unit U16-F10a (the shared tables, the names module, the engine-note rules and C01), from the third capture
// review (R3) on rc3, on the committed documents and in both languages. Each test names the row it closes and fails on its
// defect. The rows: R3 c01 (B1 to B4, M1 to M3), c02 (B1 to B3), the tests tables' segment (c04 M1, c11 n3, c20 M3, c23 M1), the
// Spanish engine notes and named parameters (c03 B1, B2), the codebook names (c01 B4, c03 Q1, c20 B6, c23 B8), the Spanish test and
// design-limit names (c22 B5, c17 B1, c16 B1, c20 B7) and the engine-note rules (c12 B2, c13 m4, c15 B3, B4, c16 B2, Q, c17 B4, Q1,
// c18 B1, c20 m3, m14, c21 B6).
import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it } from 'vitest';
import { COMMITTED } from '../lib/policy';
import type { TestRow, VariantArtifact } from '../lib/contract.types';
import { committedData, render, textOf, variantIds, type Lang } from './c03/u16f2-kit';
import { setLang } from './c03/u6-testkit';
import { U6TestsTable } from './c03/U6Shared';
import { ParamTable, U14TestsTable } from './c20/U14Common';
import { ContextView } from './ContextView';
import { FindingsView, evidenceSeries } from './FindingsView';
import { ImpactView } from './ImpactView';
import { CapitalView } from './CapitalView';
import { defaultChallenger } from './model';
import { EbmCategoriesView, EbmView, GbmView, LadderView, PenalisedView, ScorecardView, ebmShapes } from './ModelViews';
import { CalibrationView, DiscriminationView, StabilityView, LightCell, BatteryView, GroupsView } from './ValidationViews';
import { VariantsView } from './VariantsView';
import { ruleText } from './c01Text';
import { CONTRACT_RULES, DESIGN_LIMITS, TEST_NAMES, inputName, modelName, ruleNames, segmentName, windowName } from './names';
import { noteText } from './c08/notes';
import { localise, IRRBB_SOURCE_RULES, TEST_REFERENCE_RULES } from './c14/localise';
import { es as c16es } from './c16/localise';
import { C15_SOURCE_RULES, formulaText } from './c15/localise';
import { es as c17es } from './c17/localise';
import { es as c20es } from './c20/localise';
import { es as c21es } from './c21/localise';
import type { EbmExport } from '../lib/contract.types';

const LANGS: Lang[] = ['en', 'es'];
afterEach(() => setLang('en'));

/** The English technical words a Spanish text may not carry (scripts/check_spanish_words.txt, the lines after a "!"). */
const RULED = readFileSync(new URL('../../../scripts/check_spanish_words.txt', import.meta.url), 'utf8')
  .split('\n')
  .filter((l) => l.startsWith('!'))
  .map((l) => l.slice(1).split(' ')[0]);
const ENGLISH_WORD = new RegExp(`(?<![A-Za-zÀ-ÿ0-9_./-])(?:${RULED.map((w) => w.replace(/[-]/g, '\\-')).join('|')})(?:s|es|ing|ed)?(?![A-Za-zÀ-ÿ0-9_/-])`, 'i');

const c01Sel = (v: string) => {
  const data = committedData('C01', v);
  return { data, challenger: defaultChallenger(data.variant), alphas: COMMITTED, approval: 0.8, lgd: 0.5, applicant: 0 } as never;
};
const C01 = variantIds('C01');

/** The input ids of a C01 variant's data file: its model inputs and the columns it reads and leaves unused. */
function inputIds(v: string): string[] {
  const d = committedData('C01', v);
  const fit = d.models.fit as unknown as { features: Array<{ name: string }> };
  const ignored = Object.values(d.manifest.contract).flatMap((c) => c.ignored_columns);
  return [...fit.features.map((f) => f.name), ...ignored];
}
// an id that is a code (LIMIT_BAL, checking_status); an id that is a plain English word (savings, purpose) is also the codebook's word
const rawIn = (text: string, ids: string[]) => ids.filter((id) => /_|[A-Z]/.test(id) && new RegExp(`(?<![A-Za-z0-9_])${id}(?![A-Za-z0-9_])`).test(text));

/** The shell's lane labels ("Reproduce el resultado offline", "Solo offline"): a shell item of CAOS_APP_SHELL 0.19.3, not this product's. */
const withoutShell = (text: string) => text.replaceAll('Reproduce el resultado offline', ' ').replaceAll('Solo offline', ' ');

/** The document's own model titles and the case question (producer texts, renamed at the re-bake), taken out of a text before the English-word check. */
function withoutDocTitles(text: string, v: string, lang: Lang): string {
  const d = committedData('C01', v);
  // a finding's register id (F-CF-P1-scorecard) is its key (the 2026-10-27 ruling on R3 c01 Q1)
  const own = withoutShell(text).replaceAll(d.manifest.question[lang], ' ');
  return d.models.model.reduce((t, m) => t.replaceAll(m.title[lang], ' ').replaceAll(m.short_title[lang], ' '), own).replace(/F-[A-Z]+(?:-[A-Za-z0-9]+)*/g, ' ');
}

describe('U16-F10a C01 (R3 c01, c02)', () => {
  for (const v of C01) {
    it(`${v}: the Context names the contract rules, never C01-EDU-CODE or C01-PAY-CODE (c01 B1, c02 B1)`, () => {
      for (const lang of LANGS) {
        const t = textOf(render(<ContextView sel={c01Sel(v)} />, lang));
        expect(t, lang).not.toMatch(/C01-(EDU|PAY)-CODE/);
      }
    });
    it(`${v}: no input id of the data file in the Scorecard, EBM, GBM, L1 and PLTR, Stability and Context views (c01 B2, B4, c02 B2)`, () => {
      const ids = inputIds(v);
      for (const lang of LANGS) {
        for (const [name, el] of [
          ['scorecard', <ScorecardView sel={c01Sel(v)} />],
          ['ebm', <EbmView sel={c01Sel(v)} />],
          ['ebm-categories', <EbmCategoriesView sel={c01Sel(v)} />],
          ['gbm', <GbmView sel={c01Sel(v)} />],
          ['penalised', <PenalisedView sel={c01Sel(v)} />],
          ['stability', <StabilityView sel={c01Sel(v)} />],
          ['context', <ContextView sel={c01Sel(v)} />],
        ] as const) {
          const t = textOf(render(el, lang));
          expect(rawIn(t.slice(0, name === 'context' ? t.indexOf(lang === 'es' ? 'Desarrollo' : 'Write-up') : undefined), ids), `${v} ${name} ${lang}`).toEqual([]);
        }
      }
    });
    it(`${v}: the Spanish views carry none of the ruled English words (the ruling of 2026-10-27; c01 m11)`, () => {
      for (const el of [
        <LadderView sel={c01Sel(v)} />, <ScorecardView sel={c01Sel(v)} />, <EbmView sel={c01Sel(v)} />, <EbmCategoriesView sel={c01Sel(v)} />, <GbmView sel={c01Sel(v)} />,
        <PenalisedView sel={c01Sel(v)} />, <BatteryView sel={c01Sel(v)} />, <CalibrationView sel={c01Sel(v)} />, <DiscriminationView sel={c01Sel(v)} />,
        <StabilityView sel={c01Sel(v)} />, <GroupsView sel={c01Sel(v)} />, <ImpactView sel={c01Sel(v)} />, <CapitalView sel={c01Sel(v)} />,
        <FindingsView sel={c01Sel(v)} />, <VariantsView sel={c01Sel(v)} onPick={() => undefined} />,
      ]) {
        const t = withoutDocTitles(textOf(render(el, 'es')), v, 'es');
        expect(t.match(ENGLISH_WORD)?.[0] ?? null, v).toBeNull();
      }
      const ctx = textOf(render(<ContextView sel={c01Sel(v)} />, 'es'));
      expect(withoutDocTitles(ctx.slice(0, ctx.indexOf('Desarrollo')), v, 'es').match(ENGLISH_WORD)?.[0] ?? null).toBeNull();
    });
    it(`${v}: the reader notes say what to do, not a pixel width (c01 m16)`, () => {
      for (const lang of LANGS) {
        expect(textOf(render(<LadderView sel={c01Sel(v)} />, lang))).not.toMatch(/\d+ px/);
        expect(textOf(render(<CalibrationView sel={c01Sel(v)} />, lang))).not.toMatch(/\d+ px/);
      }
    });
    it(`${v}: the Spanish training split is "partición", the bins "tramos" (c01 m17)`, () => {
      for (const el of [<ScorecardView sel={c01Sel(v)} />, <StabilityView sel={c01Sel(v)} />, <ContextView sel={c01Sel(v)} />, <BatteryView sel={c01Sel(v)} />]) {
        const t = textOf(render(el, 'es'));
        // the Context's write-up (content/cases/C01.tsx) is the pages unit's text
        expect(t.slice(0, t.includes('Desarrollo') ? t.indexOf('Desarrollo') : undefined)).not.toMatch(/tramo de entrenamiento/);
      }
    });
    it(`${v}: Findings print an underflowed p as below 1E-300, the severity policy names every family, the policy is "versionada" (c01 m2, m3, m15)`, () => {
      const en = textOf(render(<FindingsView sel={c01Sel(v)} />, 'en'));
      const es = textOf(render(<FindingsView sel={c01Sel(v)} />, 'es'));
      expect(en).not.toMatch(/: p 0,/);
      expect(es).not.toMatch(/: p 0(?![,.\d])/);
      expect(en).toMatch(/stability/);
      expect(en).toMatch(/discrimination/);
      expect(es).toMatch(/estabilidad/);
      expect(es).not.toMatch(/con la comprometida/);
    });
  }

  it('german-twin: the EBM, GBM and dropped-input texts name the inputs, and the stated P0 feature (c01 B2)', () => {
    const t = textOf(render(<ContextView sel={c01Sel('german-twin')} />, 'en'));
    expect(t).toMatch(/Single variable \(Status of the existing checking account\)/);
    const es = textOf(render(<ContextView sel={c01Sel('german-twin')} />, 'es'));
    expect(es).toMatch(/sin usar: Edad, /);
  });

  it('the EBM categorical panels are bars named by the codebook: the German categories and the Taiwan education codes (c01 B3, c02 B3)', () => {
    const german = committedData('C01', 'german-twin');
    const ex = (german.models.model.find((m) => m.id === 'P3-ebm')!.details as { export: EbmExport }).export;
    const cats = ebmShapes(ex, german.models.fit as never, 'categorical');
    // every categorical main effect has its bars, and the shape grid holds the continuous ones only
    expect(cats.length).toBe(ex.terms.filter((t) => t.features.length === 1 && ex.features[t.features[0]].levels[0].kind !== 'continuous').length);
    expect(ebmShapes(ex, german.models.fit as never, 'continuous').every((s) => !s.categorical)).toBe(true);
    expect(cats.length).toBeGreaterThan(0);
    for (const s of cats) {
      expect(s.categories?.length, s.name).toBe(s.y.length);
      for (const c of s.categories ?? []) {
        expect(c.label.en, s.name).not.toMatch(/^A\d+$|^\d+$/);
        expect(c.label.es).not.toBe('');
      }
      expect(s.xLabel.en).not.toMatch(/\(code\)/);
    }
    const taiwan = committedData('C01', 'holdout');
    const tx = (taiwan.models.model.find((m) => m.id === 'P3-ebm')!.details as { export: EbmExport }).export;
    const edu = ebmShapes(tx, taiwan.models.fit as never).find((s) => s.name === 'EDUCATION')!;
    expect(edu.categories?.map((c) => c.label.en)).toEqual(expect.arrayContaining(['graduate school', 'university', 'high school', 'others', 'undocumented code 0']));
    expect(edu.categories?.map((c) => c.label.es)).toEqual(expect.arrayContaining(['posgrado', 'universidad', 'secundaria', 'otros']));
  });

  it('holdout at 390: the Discrimination row shows its 95 % intervals on every width (c01 M1)', () => {
    for (const lang of LANGS) {
      const m = render(<DiscriminationView sel={c01Sel('holdout')} />, lang);
      expect(m).not.toMatch(/<span class="ct-wide-only">\(/);
      expect(textOf(m)).toMatch(/\(0[.,]7461 - 0[.,]7714\)/);
    }
  });

  for (const v of ['prior-shift', 'small-sample', 'drift-moderate', 'label-noise']) {
    it(`${v}: with no scored applicant the reasons card is a replay of four rows and the distribution chart fills its card (c01 M2, m8, c02 m1 to m3)`, () => {
      for (const lang of LANGS) {
        const m = render(<ScorecardView sel={c01Sel(v)} />, lang);
        const t = textOf(m);
        expect(t).not.toMatch(/the applicant fell furthest|el solicitante quedó/);
        expect(t).not.toMatch(/Highlighted: the applicant|Destacados: los tramos del solicitante/);
        expect(t).not.toMatch(/resamples the holdout|remuestrea la muestra reservada/);
        const iv = m.slice(m.indexOf('data-table="iv"'));
        expect((iv.slice(0, iv.indexOf('</table>')).match(/<tr>/g) ?? []).length).toBe(5);
        // two filling cards in the second column: the reasons replay does not fill, the chart's card fills
        expect((m.match(/class="caos-plot fill"/g) ?? []).length).toBe(2);
      }
    });
  }

  it('german-twin at 1280: the characteristic column of the points table wraps, so the Points column stays in the card (c01 M3)', () => {
    const m = render(<ScorecardView sel={c01Sel('german-twin')} />, 'en');
    expect(m).toMatch(/<td class="ct-text">Status of the existing checking account<\/td>/);
  });

  it('german-twin: the GBM title counts the features it draws (c01 m10)', () => {
    const t = textOf(render(<GbmView sel={c01Sel('german-twin')} />, 'en'));
    expect(t).not.toMatch(/the six strongest constrained features/);
  });

  it('a PLTR rule on a WoE-encoded input says so and rounds its threshold (c01 m14)', () => {
    expect(ruleNames(ruleText('PAY_3 <= 0.5 and EDUCATION > 0.0523532', 'en', ['EDUCATION']), 'en')).toBe('Repayment status, July 2005 <= 0.5 and Education (WoE) > 0.0524');
    expect(ruleNames(ruleText('PAY_3 <= 0.5 and EDUCATION > 0.0523532', 'es', ['EDUCATION']), 'es')).toBe('Estado de pago, julio de 2005 <= 0,5 y Educación (WoE) > 0,0524');
  });

  it('a p-value just under a threshold is not printed as the threshold (c02 m5: PAY_5 0.049876 "0.05 amber")', () => {
    const row = { test_id: 'stability.csi', model_id: null, segment: 'characteristic:PAY_5', statistic: null, p_value: 0.049876, light: 'amber', notes: '', reference: '', extras: {} } as unknown as TestRow;
    const m = render(<table><tbody><tr><LightCell row={row} alphas={COMMITTED} /></tr></tbody></table>, 'en');
    expect(textOf(m)).not.toMatch(/0\.05 /);
    expect(textOf(m)).toMatch(/0\.0499/);
  });

  it('small-sample: the Context says the models were fitted on 2,000 of the training rows (c02 m8)', () => {
    expect(textOf(render(<ContextView sel={c01Sel('small-sample')} />, 'en'))).toMatch(/fitted on 2,000 of the 16,800 training rows/);
  });

  it('the Findings chart carries no padding points: the x range gives the room (c02 m19)', () => {
    const s = evidenceSeries([1e-5, 0.02, 0]);
    expect(s.x).toEqual([1, 2, 3]);
    expect(s.values).toEqual([1e-5, 0.02, 1e-16]);
    expect(s.range).toEqual([0.5, 3.5]);
  });
});

describe('U16-F10a the names module (c01 B4, c03 Q1, c20 B6, c23 B8, M1, c11 n3, c20 B1, M1, M3)', () => {
  it('names every Taiwan column from the UCI codebook, both languages', () => {
    expect(inputName('LIMIT_BAL')).toEqual({ en: 'Given credit', es: 'Crédito otorgado' });
    expect(inputName('PAY_0')).toEqual({ en: 'Repayment status, September 2005', es: 'Estado de pago, septiembre de 2005' });
    expect(inputName('PAY_6')?.en).toBe('Repayment status, April 2005');
    expect(inputName('BILL_AMT3')?.en).toBe('Bill statement, July 2005');
    expect(inputName('PAY_AMT6')?.es).toBe('Monto pagado, abril de 2005');
    for (const c of ['EDUCATION', 'SEX', 'MARRIAGE', 'AGE']) expect(inputName(c), c).not.toBeNull();
  });
  it('names the three German columns the case leaves unused', () => {
    for (const c of ['age_years', 'foreign_worker', 'personal_status_sex']) expect(inputName(c), c).not.toBeNull();
  });
  it('names every Polish ratio Attr1 to Attr64 from the UCI codebook, the code beside its words', () => {
    for (let i = 1; i <= 64; i += 1) {
      const n = inputName(`Attr${i}`);
      expect(n, `Attr${i}`).not.toBeNull();
      expect(n!.en).toMatch(new RegExp(`\\(Attr${i}\\)$`));
      expect(n!.es).toMatch(new RegExp(`\\(Attr${i}\\)$`));
      expect(n!.es).not.toBe(n!.en);
    }
    expect(inputName('Attr27')!.en).toBe('profit on operating activities / financial expenses (Attr27)');
    expect(segmentName('characteristic:Attr27_missing', { caseId: 'C02' })!.en).toBe('profit on operating activities / financial expenses (Attr27), missing-value indicator');
  });
  it('a rule names its Taiwan and Polish inputs', () => {
    expect(ruleNames('PAY_0 <= 1.5 and LIMIT_BAL <= 145000', 'en')).toBe('Repayment status, September 2005 <= 1.5 and Given credit <= 145000');
    expect(ruleNames('Attr39 > 0.1', 'es')).toMatch(/^utilidad sobre ventas \/ ventas \(Attr39\) > 0.1$/);
  });
  it('names the grade of a C01 test row and the vintage of a C03 row, so a tests table can tell them apart (c23 M1, c04 M1)', () => {
    expect(segmentName('G08', { caseId: 'C01' })).toEqual({ en: 'grade G08', es: 'grado G08' });
    expect(segmentName('fy2008', { caseId: 'C03' })).toEqual({ en: 'the fiscal year 2008 vintage', es: 'la cosecha del año fiscal 2008' });
  });
  it('names the level and measure of a C10 Euler row (c11 n3)', () => {
    expect(segmentName('var-0.99', { caseId: 'C10' })).toEqual({ en: 'VaR at 99%', es: 'VaR al 99 %' });
    expect(segmentName('es-0.999', { caseId: 'C10' })).toEqual({ en: 'ES at 99.9%', es: 'ES al 99,9 %' });
  });
  it('names the C20 shifts of the flips view and puts the multiple first (c20 B1, M1)', () => {
    expect(windowName('fed-higher-risk-x0.25').en).toBe('0.25 times the Fed higher-risk drift');
    expect(windowName('fed-higher-risk-x0.25').es).toBe('0,25 veces la deriva de mayor riesgo de la Fed');
    expect(segmentName('noise-0.05', { caseId: 'C20' })).toEqual({ en: 'input noise at 0.05 standard deviations', es: 'ruido en las entradas de 0,05 desviaciones estándar' });
    expect(segmentName('seed-42', { caseId: 'C20' })).toEqual({ en: 'retraining seed 42', es: 'semilla de reentrenamiento 42' });
    expect(segmentName('decision-time-leak-unavailable', { caseId: 'C20' })?.en).toBe('at decision time, without the leak');
    expect(segmentName('slices-of-PAY_0', { caseId: 'C20' })?.en).toBe('slices of Repayment status, September 2005');
    expect(segmentName('100-bootstrap-refits', { caseId: 'C20' })?.es).toBe('100 reajustes por remuestreo');
  });
  it('names the planted-leak model apart from the clean one (c20 M3)', () => {
    const d = committedData('C20', 'leakage-planted');
    const a = modelName('P4-lightgbm-taiwan-planted-leak', { caseId: 'C20', models: d.variant.model });
    const b = modelName('P4-lightgbm-taiwan', { caseId: 'C20', models: d.variant.model });
    expect(a?.en).not.toBe(b?.en);
    expect(a?.es).not.toBe(b?.es);
    expect(a?.en).toMatch(/planted leak/);
  });
  it('names the scorecard rung in Spanish, never "Scorecard" (the 2026-10-27 ruling, routed by F10p)', () => {
    const d = committedData('C01');
    expect(modelName('P1-scorecard', { caseId: 'C01', models: d.variant.model })).toEqual({ en: 'P1 Scorecard', es: 'P1 Tarjeta de puntuación' });
    expect(modelName('P1-scorecard', { caseId: 'C01' })?.es).toBe('P1 Tarjeta de puntuación');
  });
  it('the contract rules read as words (c01 B1)', () => {
    for (const r of Object.values(CONTRACT_RULES)) for (const lang of LANGS) expect(r[lang]).not.toMatch(/EDUCATION|PAY_0/);
  });
  it('no Spanish test name, design limit or segment name carries a ruled English word (c22 B5, c17 B1, c16 B1, c20 B7)', () => {
    const bad = [...Object.values(TEST_NAMES), ...Object.values(DESIGN_LIMITS)].map((t) => t.es).filter((s) => ENGLISH_WORD.test(s));
    expect(bad).toEqual([]);
    expect(TEST_NAMES['rating.momentum'].es).toMatch(/impulso/);
    expect(TEST_NAMES['market.desk_backtest'].es).toMatch(/prueba retrospectiva/i);
  });
});

describe('U16-F10a the shared tests tables (c04 M1, c03 B1, B2, c20 M3, m3)', () => {
  it('C03: every row of the U6 tests table shows its segment, so the vintages can be told apart (c04 M1)', () => {
    const d = committedData('C03');
    for (const lang of LANGS) {
      const m = render(<U6TestsTable variant={d.variant} />, lang);
      const rows = [...m.matchAll(/<tr[^>]*data-test="([^"]+)"[^>]*>([\s\S]*?)<\/tr>/g)].map((r) => textOf(r[2]));
      expect(rows.length).toBe(d.variant.tests.length);
      const seen = new Map<string, number>();
      for (const r of rows) seen.set(r, (seen.get(r) ?? 0) + 1);
      // rows that read the same must hold the same numbers too: count the distinct (test, model, segment) against the distinct texts
      const keys = new Set(d.variant.tests.map((t) => `${t.test_id}|${t.model_id}|${t.segment}`));
      expect(seen.size, lang).toBeGreaterThanOrEqual(keys.size);
      expect(m).toMatch(lang === 'es' ? /cosecha del año fiscal 2008/ : /fiscal year 2008 vintage/);
    }
  });
  it('C02 in Spanish: the U14 tests table reads the engine notes in Spanish and the reference where the note is empty (c03 B1, m11)', () => {
    const d = committedData('C02', 'h1');
    const t = textOf(render(<U14TestsTable tests={d.variant.tests} caseId="C02" models={d.variant.model} />, 'es'));
    expect(t).not.toMatch(/assumes independent defaults/);
    expect(t).not.toMatch(/conventional band/);
    expect(t).toMatch(/supone incumplimientos independientes/);
  });
  it('C20 leakage-planted: the two leakage-screen rows read apart (c20 M3)', () => {
    const d = committedData('C20', 'leakage-planted');
    const rows = d.variant.tests.filter((t) => t.test_id.startsWith('ml.leakage_screen'));
    const m = render(<U14TestsTable tests={rows} caseId="C20" models={d.variant.model} />, 'en');
    // the test and the model cells of each row: the light is not what tells two rows apart
    const labels = [...m.matchAll(/<tr[^>]*data-test="[^"]+"[^>]*>([\s\S]*?)<\/tr>/g)].map((r) => [...r[1].matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].slice(0, 2).map((c) => textOf(c[1]).trim()).join(' | '));
    expect(labels.length).toBe(rows.length);
    expect(new Set(labels).size, labels.join(' / ')).toBe(labels.length);
  });
  it('the named parameters: the unit in Spanish, a bilingual basis picked, the score name not followed by its unit (c03 B2, c20 m3)', () => {
    const params = [
      { name: 'overfit_tolerance', value: 0.05, unit: 'AUC points', label: 'convention', basis: { en: 'The English basis.', es: 'La base en español.' } },
      { name: 'shift_score', value: 'resemblance-classifier-probability', unit: 'name of the score', label: 'convention', basis: 'A plain basis.' },
    ];
    const t = textOf(render(<ParamTable params={params as never} />, 'es'));
    expect(t).toMatch(/0,05 puntos de AUC/);
    expect(t).toMatch(/La base en español\./);
    expect(t).not.toMatch(/The English basis/);
    expect(t).not.toMatch(/nombre del puntaje|name of the score/);
    expect(textOf(render(<ParamTable params={params as never} />, 'en'))).toMatch(/0\.05 AUC points/);
  });
});

describe('U16-F10a the engine-note rules (raw ids, tags and English left in Spanish)', () => {
  it('C11: "the U8 bake" is no reader text in either language (c12 B2)', () => {
    const n = 'challenger only: it must enter the 90 percent MCS on FZ0 out of sample, and the U8 bake does not train it';
    for (const lang of LANGS) expect(noteText(n, lang)).not.toMatch(/U8/);
  });
  it('C11: the decision tag of the traffic-light note is dropped (c17 Q1 ruling)', () => {
    const n = 'fewer than 250 forecast days (120): the Basel traffic light of MAR32.9 is defined on 250 observations and the window has no lead-in (decision D3)';
    for (const lang of LANGS) expect(noteText(n, lang)).not.toMatch(/D3|decisi/);
  });
  it('C12: the W^2 horizon reads "1 mes", never "1 meses", and the horizon code is named (c13 m4, BL1)', () => {
    const es = noteText('W^2 is above the simulated 95 percent critical value the book at the 1m horizon', 'es');
    expect(es).toMatch(/horizonte de 1 mes\b/);
    expect(noteText('W^2 is above the simulated 95 percent critical value the book at the 10bd horizon', 'en')).not.toMatch(/10bd/);
  });
  it('C11: FZ0 takes one gender (c12 m16)', () => {
    expect(noteText('the model forecasts no ES: FZ0 is not defined', 'es')).toMatch(/FZ0 no está definido$/);
  });
  it('C14: the shock shapes reference and the slotting cell read in Spanish, with no engine function (c15 B3, B4)', () => {
    expect(localise('SRP31.91 to SRP31.92', 'es', [...IRRBB_SOURCE_RULES, ...TEST_REFERENCE_RULES])).toBe('SRP31.91 a SRP31.92');
    const slot = 'behavioural: non-core overnight, core around the used maturity (nmd_split, SRP31 Table 4 caps); contractual: overnight';
    expect(localise(slot, 'es', IRRBB_SOURCE_RULES)).not.toMatch(/nmd_split/);
    expect(localise('par yields bootstrapped to continuously compounded zero rates (the engine\'s zero-curve bootstrap, semiannual bond-equivalent, simple interest up to six months); linear in tenor and flat outside the grid at the 19 midpoints', 'es', IRRBB_SOURCE_RULES)).not.toMatch(/bootstrap/i);
  });
  it('C15: "Annex 1" is "Anexo 1" and the CPI formula writes symbols with a legend, never an engine key (c16 B2, Q)', () => {
    expect(localise('RAN 21-13 Annex 1', 'es', C15_SOURCE_RULES)).toBe('RAN 21-13 Anexo 1');
    for (const lang of LANGS) {
      const f = formulaText('effect = -pn_ur x surprise_pp / 100 (loss-positive)', lang);
      expect(f, lang).not.toMatch(/pn_ur|surprise_pp/);
      expect(f, lang).toMatch(lang === 'es' ? /PN_UR.*posición neta en UF/ : /PN_UR.*net UF position/);
    }
  });
  it('C16: the fast-run note reads as a sentence, never "far = 35", and the decision tags are dropped (c17 B4, Q1)', () => {
    for (const lang of LANGS) {
      const t = c16es('not evaluated: the horizon of 5 days is shorter than far = 35', lang);
      expect(t).not.toMatch(/far = |lejos = /);
    }
    const tag = "dossier 08 lines 566 to 568 and dossier 06 lines 971 to 973: a Basel outflow assumption back-tested against the observed run rate (BCBS d555 Box A, Table A.1, https://www.bis.org/bcbs/publ/d555.htm); a descriptive score on the real event, one observation, no p-value (decision Q5)";
    for (const lang of LANGS) expect(c16es(tag, lang)).not.toMatch(/Q5/);
    expect(c16es(tag, 'es')).not.toMatch(ENGLISH_WORD);
  });
  it('C17: the authors keep their published names, Böcker and Wüthrich (c18 m7)', () => {
    expect(c17es('dossier 05 F.5, Shevchenko and Wuthrich (2006)', 'es')).toBe('dossier 05 F.5, Shevchenko y Wüthrich (2006)');
    expect(c17es('dossier 05 F.4: the form is not checked against Bocker and Sprittulla (2006) or Degen (2010)', 'es')).toMatch(/Böcker y Sprittulla/);
  });
  it('C20: "dosier" in prose, no bootstrap and no decision tag in Spanish (c20 m14, B7, m4)', () => {
    expect(c20es('bootstrap refits', 'es')).not.toMatch(/bootstrap/);
    expect(c20es("The dossier's example is the worst 10 percent (06 C.7 l.1013-1014).", 'es')).toMatch(/dosier/);
    for (const lang of LANGS) expect(c20es('The cut-off is the baseline score quantile that declines this share; held fixed under every shift (decision Q10).', lang)).not.toMatch(/Q10/);
  });
  it('C21: the situation-testing note names the amber share, never extras.thresholds (c21 B6)', () => {
    const d = committedData('C21');
    const note = (d.variant as VariantArtifact).tests.find((t) => t.test_id === 'fair.situation_testing')?.notes ?? '';
    expect(note).toMatch(/extras\.thresholds/);
    for (const lang of LANGS) expect(c21es(note, lang)).not.toMatch(/extras\.thresholds/);
  });
});
