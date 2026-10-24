// U16-F6 (the second fix round): the minors of the b02 to b05 reviews that belong to the views of C03 to C11, and the reference column
// of the tests tables, on the committed documents.
import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it } from 'vitest';
import { committedData, render, textOf } from './c03/u16f2-kit';
import { setLang } from './c03/u6-testkit';
import { C03ContextView, ModelReadout, VintageReadout } from './c03/C03Common';
import { StabilityView, psiBand } from './c03/VintageViews';
import { U6TestsTable, referenceText } from './c03/U6Shared';
import { defaultSel as sel03 } from './c03/selection';
import { NonLinearityView, SicrView } from './c06/TermViews';
import { C06VariantsTable } from './c06/C06Common';
import { TestRowsCard } from './c06/ValidationViews';
import { defaultSel as sel06 } from './c06/selection';
import { TablesView, calibrationSource } from './c07/ValidationViews';
import { BridgeView } from './c07/RegimeViews';
import { defaultSel as sel07 } from './c07/selection';
import { FloorsView } from './c09/EadViews';
import { defaultSel as sel09 } from './c09/selection';
import { LadderView } from './c10/ModelViews';
import { defaultSel as sel10, referenceNote } from './c10/selection';
import { TestsView as C11Tests } from './c11/BacktestViews';
import { defaultSel as sel11, unitFor } from './c11/selection';
import { provenanceOf } from './model';

const data = (c: string, v?: string) => committedData(c, v);
const source = (rel: string) => readFileSync(new URL(rel, import.meta.url), 'utf8');
afterEach(() => setLang('en'));

describe('U16-F6 C03 (b02)', () => {
  const s = () => sel03(data('C03'))!;
  it('m5: the Spanish context names the fiscal years as AF, not FY', () => {
    expect(textOf(render(<C03ContextView sel={s()} />, 'es'))).not.toMatch(/\bFY\d{4}\b/);
  });
  it('m9: the rail readouts that look values up in the replay document are chipped as replay', () => {
    for (const el of [<VintageReadout sel={s()} />, <ModelReadout sel={s()} />]) {
      const m = render(el, 'en');
      expect(m).toContain('data-lane="replay"');
      expect(m).not.toContain('data-lane="live"');
    }
  });
  it('m10: the stability table names the conventional PSI band of each vintage', () => {
    expect(psiBand(0.05).en).toBe('below 0.10');
    expect(psiBand(0.2).es).toBe('0,10 a 0,25');
    expect(psiBand(1.27).en).toBe('above 0.25');
    expect(textOf(render(<StabilityView sel={s()} />, 'es'))).toContain('sobre 0,25');
  });
  it('m11: the rung in focus opens on the champion, not on the constant anchor', () => {
    const sel = s();
    expect(sel.rung).toBe((sel.data.variant.outputs as unknown as { calibration: { rung_id: string } }).calibration.rung_id);
  });
});

describe('U16-F6 C05 and C04 (b02, b03)', () => {
  it('b03 m9, m2, m6: the change column states its unit, the chi-square column says from which width, the model readout has a Spanish reason', () => {
    const sp = source('./c05/SpViews.tsx');
    expect(sp).toContain("es: 'Cambio, puntos'");
    expect(sp).toContain('desde 1500 px de ancho');
    expect(sp).not.toMatch(/\}%<\/td>/);
    expect(source('./c05/C05Common.tsx')).toContain('la condición (4.6a) no se cumple');
  });
  it('b02 m5: no UI word where a table is meant, no segmented line, no "horneado" in the Spanish of C03 to C05', () => {
    for (const f of ['c04/AgencyTestsViews.tsx', 'c04/AgencyValidationViews.tsx', 'c04/C04Common.tsx', 'c04/FamilyViews.tsx', 'c04/LiveViews.tsx', 'c04/PublishedViews.tsx', 'c05/C05Common.tsx']) {
      expect(source(`./${f}`), f).not.toMatch(/pestaña|egmentad|horneado/);
    }
  });
  it('b02 m16 and m12: the headers say what they count, the generator note says the rail definition does not apply', () => {
    expect(source('./c04/LiveViews.tsx')).toContain("es: 'N efectivo'");
    expect(source('./c04/AgencyValidationViews.tsx')).toContain('Cohorte, tabla 2 de CEREP');
    expect(source('./c04/FamilyViews.tsx')).toContain("The rail's default definition does not apply");
  });
  it('b02 m8: the grade own risk weight is not drawn in the colour of the weighted generator', () => {
    expect(source('./c04/LiveViews.tsx')).toMatch(/color: '--color-fg-faint',\s*mode: 'points',\s*size: 13/);
  });
});

describe('U16-F6 C06 (b03)', () => {
  const s = () => sel06(data('C06', 'rd-2020-06'))!;
  it('m1 and m3: a factor and a multiplier are written with the language decimal sign', () => {
    expect(textOf(render(<NonLinearityView sel={s()} />, 'es'))).not.toMatch(/\d\.\d{4,}/);
    expect(textOf(render(<SicrView sel={s()} />, 'es'))).not.toMatch(/\d\.\d veces/);
  });
  it('m10: the lines of the SICR rule are not drawn above 100%', () => {
    expect(source('./c06/TermViews.tsx')).toContain('reachable(multiplierAt(o, x) * x)');
  });
  it('m4: the reporting dates table scales its amounts and names the unit', () => {
    const d = s().data;
    const v = { id: d.variant.variant_id, title: { en: 'x', es: 'x' }, v: d.variant as never };
    const m = textOf(render(<C06VariantsTable variants={[v]} onPick={() => undefined} current={v.id} />, 'en'));
    expect(m).toMatch(/ECL Stage 1 \((?:bn|m) USD\)/);
    expect(m).not.toMatch(/\d{1,3},\d{3},\d{3},\d{3}/);
  });
  it('b04 m11: the tests card names a test in words and shows the metric where there is no statistic', () => {
    const d = s().data;
    const es = textOf(render(<TestRowsCard variant={d.variant} prov={provenanceOf(d.variant.provenance.truth_status)} />, 'es'));
    expect(es).toContain('Backtest de la PCE a 12 meses');
    expect(es).toContain('Estadístico o métrica');
  });
});

describe('U16-F6 C07 (b04)', () => {
  const s = () => sel07(data('C07'))!;
  it('m4: the B-1 tables say days past due and the guarantee ratio in words', () => {
    const t = textOf(render(<TablesView sel={s()} />, 'es'));
    expect(t).toContain('1 a 29 días de mora');
    expect(t).toContain('préstamo sobre el valor de la garantía: hasta 40 %');
    expect(t).not.toMatch(/pvg<=|ptvg</);
  });
  it('m1: the bridge caption never claims where the axis starts', () => {
    expect(textOf(render(<BridgeView sel={s()} />, 'en'))).not.toContain('does not start at zero');
  });
  it('m12: the calibration source reads in Spanish', () => {
    expect(calibrationSource('x public web publication (the CMF Bancos API key is absent); generator g; parameters sha256 h', 'es')).toBe(
      'x publicación web pública (falta la clave de la API de CMF Bancos); generador g; parámetros sha256 h',
    );
  });
  it('m2: the regime of the rail and the regime tab are one choice', () => {
    expect(source('./c07/instrument.tsx')).toContain('REGIME_TAB[sel.regime]');
  });
});

describe('U16-F6 C08 to C11 (b04, b05)', () => {
  it('b04 m10: the small-undrawn threshold carries its currency', () => {
    expect(textOf(render(<FloorsView sel={sel09(data('C09'))!} />, 'en'))).toMatch(/Threshold [\d.,]+ USD/);
  });
  it('b05 m8: an analytic rung says so in the scenarios column', () => {
    expect(textOf(render(<LadderView sel={sel10(data('C10'))!} />, 'en'))).toContain('Analytic: no scenarios.');
  });
  it('b05: the ladder remarks are in Spanish and the citation is as published', () => {
    expect(referenceNote('Gordy and Lutkebohmert (2013), eq. 15 and eq. 16 (dossier 04 H.5)', 'es')).toBe('Gordy and Lutkebohmert (2013), ecs. 15 y 16 (dossier 04 H.5)');
    expect(referenceNote('unknown', 'es')).toBe('unknown');
  });
  it('b05 m4: a unit of one is singular', () => {
    expect(unitFor('days', 1).en).toBe('day');
    expect(unitFor('days', 5).es).toBe('días');
  });
  it('b05 m6 and m9: the bars follow the ranking, the Z2 null is drawn as points', () => {
    expect(source('./c11/ComparisonViews.tsx')).toContain('lowest average FZ0 first');
    expect(source('./c11/BacktestViews.tsx')).toContain("mode: 'points', size: 7");
  });
  it('b04 m7 and m9: the captions say what the table says', () => {
    expect(source('./c08/ModelViews.tsx')).toContain('predicted mean lies below the interval of the realised mean');
    expect(source('./c09/C09Common.tsx')).not.toContain('drifts from the truth');
  });
});

describe('U16-F6 the reference column in Spanish', () => {
  it('prefers the producer bilingual reference and falls back to the engine string', () => {
    expect(referenceText({ reference: 'only English', extras: {} } as never, 'es')).toBe('only English');
    const u = { reference: 'en', extras: { reference_text: { en: 'en', es: 'es' } } } as never;
    expect(referenceText(u, 'es')).toBe('es');
    expect(referenceText(u, 'en')).toBe('en');
  });
  for (const c of ['C03', 'C08', 'C09']) {
    it(`${c}: a test with no note prints the Spanish of its reference`, () => {
      const d = data(c);
      const m = textOf(render(<U6TestsTable variant={d.variant} />, 'es'));
      const quiet = d.variant.tests.filter((t) => !t.notes);
      expect(quiet.length).toBeGreaterThan(0);
      for (const t of quiet.slice(0, 20)) {
        const es = (t.extras as { reference_text?: { es: string } }).reference_text?.es;
        expect(es, t.test_id).toBeTruthy();
        expect(m).toContain(es!.slice(0, 60));
      }
    });
  }
  it('C11: the tests table prints the Spanish reference', () => {
    const d = data('C11');
    const m = textOf(render(<C11Tests sel={sel11(d)!} />, 'es'));
    expect(d.variant.tests[0].extras).toHaveProperty('reference_text');
    expect(m).not.toContain('primary text not retrieved');
  });
});
