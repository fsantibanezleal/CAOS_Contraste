// U16-F10d (fix round 4, the third capture review R3, batches c15 (C14) and c16 (C15)), on the committed documents and on the
// same documents as the 2.0.0 and 3.0.0 producers write them (the bilingual texts of pipeline/cases/c14 and c15): the Spanish views
// print the call-report provenance, the shock-shape reference, the slotting assumptions, the prioritised-bank reference and the
// formulas in Spanish (C14 B2, B3, B4; C15 B2, Q), a committed English string still renders, the tests table shows the segment of
// each row, and the minors of the views (C14 m5, m6, m9, n2, n4, n6; C15 m1, m9, m10, m15 wording).
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { IndexationView } from '../c15/RateViews';
import { FloorsView, ThresholdsView } from '../c15/FloorViews';
import { EveByLegView } from '../c15/LegViews';
import { defaultSel as defaultSel15, type C15Sel } from '../c15/selection';
import { ChangesView, kindAndSource } from './BehaviouralViews';
import { C14ContextView, IrrbbTestsTable, docText } from './C14Common';
import { GapView } from './NiiViews';
import { ShapesView } from './ShockViews';
import { cell, defaultSel, type C14Sel } from './selection';
import { committedDoc, fixtureData, html, setLang, visibleText } from './testkit';

type Any = Record<string, any>;
const clone = <T,>(x: T): T => structuredClone(x);
const models14 = committedDoc<ModelsArtifact>('C14', 'models-svb-2021-2022');
const doc14 = (name: string) => committedDoc<VariantArtifact>('C14', name);
const sel14 = (v: VariantArtifact, m: ModelsArtifact = models14): C14Sel => defaultSel(fixtureData('C14', v, m, { en: 'IRRBB', es: 'IRRBB' })) as C14Sel;
const models15 = committedDoc<ModelsArtifact>('C15', 'models-banco-andino-2026-09');
const doc15 = (name: string) => committedDoc<VariantArtifact>('C15', name);
const sel15 = (v: VariantArtifact): C15Sel => defaultSel15(fixtureData('C15', v, models15, { en: 'IRRBB', es: 'IRRBB' })) as C15Sel;
const view = (el: React.ReactElement, lang: 'en' | 'es') => { setLang(lang); return visibleText(html(el)); };

/** The C14 variant as the c14-outputs 2.0.0 producer writes it: the call-report source and the NMD slotting assumption bilingual. */
function rebaked14(name: string): VariantArtifact {
  const v = clone(doc14(name)) as Any;
  for (const r of v.outputs.data.call_reports) {
    const m = /^(\S+) \(file (\S+), sha256 (\w+), retrieved (\S+)\)$/.exec(r.source)!;
    r.source = { en: r.source, es: `${m[1]} (archivo ${m[2]}, sha256 ${m[3]}, obtenido el ${m[4]})` };
  }
  for (const i of v.outputs.balance_sheet.items) {
    if (i.behavioural_class.startsWith('nmd')) {
      i.slotting_assumption = {
        en: "behavioural: non-core overnight, core around the used maturity (the engine's NMD split, SRP31 Table 4 caps); contractual: overnight",
        es: 'conductual: la parte no estable a la vista y la estable en torno al plazo usado (la división NMD del motor, topes de la Tabla 4 de SRP31); contractual: a la vista',
      };
    }
  }
  return v as VariantArtifact;
}
function rebakedModels14(): ModelsArtifact {
  const m = clone(models14) as Any;
  m.fit.shock_shape.reference = { en: 'SRP31.91 to SRP31.92', es: 'SRP31.91 a SRP31.92' };
  return m as ModelsArtifact;
}
/** The C15 variant as the c15-outputs 3.0.0 producer writes it (pipeline/cases/c15/variant.py THRESHOLDS_REFERENCE, the formulas). */
function rebaked15(name: string): VariantArtifact {
  const v = clone(doc15(name)) as Any;
  v.outputs.thresholds.reference = { en: 'RAN 21-13 Annex 1 (banco priorizado, dossier 03 F.2)', es: 'RAN 21-13 Anexo 1 (banco priorizado, dossier 03 F.2)' };
  v.outputs.indexation_charge.formula = { en: 'charge = 0.025 × |PN_UR|, where PN_UR is the net UF position times the UF value', es: 'cargo = 0,025 × |PN_UR|, donde PN_UR es la posición neta en UF por el valor de la UF' };
  if (v.outputs.cpi_scenario) v.outputs.cpi_scenario.formula = { en: 'effect = −PN_UR × s / 100, positive is a loss, where PN_UR is the net UF position in CLP and s the CPI surprise in percentage points', es: 'efecto = −PN_UR × s / 100, positivo es una pérdida, donde PN_UR es la posición neta en UF en CLP y s la sorpresa de IPC en puntos porcentuales' };
  return v as VariantArtifact;
}

describe('U16-F10d C14 and C15', () => {
  afterEach(() => setLang('en'));

  it('C14 B2, B4, m9: the Spanish Context prints the provenance and the slotting in Spanish, the API as a named link', () => {
    const es = view(<C14ContextView sel={sel14(rebaked14('vd-2022-q4'))} />, 'es');
    expect(es).not.toMatch(/\(file |retrieved \d/);
    expect(es).toMatch(/\(archivo financials-cert24735-\S+, sha256 \w+, obtenido el 2026-10-14\)/);
    expect(es).not.toContain('nmd_split');
    expect(es).toContain('la división NMD del motor');
    const markup = html(<C14ContextView sel={sel14(rebaked14('vd-2022-q4'))} />);
    expect(markup).toMatch(/<a href="https:\/\/api\.fdic\.gov[^"]*"[^>]*>FDIC BankFind API<\/a>/);
    // a committed English string still renders
    expect(view(<C14ContextView sel={sel14(doc14('vd-2022-q4'))} />, 'en')).toContain('(file financials-cert24735');
  });

  it('C14 B3, n2: the Spanish shapes view prints the reference in Spanish and the forms as symbols with x', () => {
    const es = view(<ShapesView sel={sel14(doc14('vd-2022-q4'), rebakedModels14())} />, 'es');
    expect(es).toContain('SRP31.91 a SRP31.92');
    expect(es).not.toContain('SRP31.91 to');
    expect(es).toContain('exp(−t k / x)');
    expect(es).toContain('Constante de decaimiento x 4 años');
    expect(docText({ en: 'a', es: 'b' }, 'es')).toBe('b');
    expect(docText('plain', 'es')).toBe('plain');
  });

  it('C14 m5, m6, n4, n6: no "-0" cell, the gap rows before the duration read-out, the beta kind said once, dates kept whole', () => {
    expect(cell(-0, 'en')).toBe('0');
    expect(cell(-0.2, 'es')).toBe('0');
    expect(cell(-1234.6, 'en')).toBe('-1,235');
    const gap = html(<GapView sel={sel14(doc14('vd-2022-q4'))} />);
    expect(gap.indexOf('data-table="repricing-gap"')).toBeLessThan(gap.indexOf('data-table="duration-gap"'));
    expect(kindAndSource('Ajustado', 'Ajustado por fecha de valoración')).toBe('Ajustado por fecha de valoración');
    expect(kindAndSource('Fitted', 'fitted per date')).toBe('fitted per date');
    expect(kindAndSource('Declarado', 'Solicitud declarada')).toBe('Declarado: Solicitud declarada');
    const changes = html(<ChangesView sel={sel14(doc14('vd-2022-q4'))} />);
    expect(changes).toMatch(/<span style="white-space:nowrap">\d{4}-\d{2}-\d{2}<\/span>/);
  });

  for (const lang of ['en', 'es'] as const) {
    it(`C15 (${lang}): every tests row names its segment, so the two sum-of-parts rows are told apart`, () => {
      const v = doc15('long-uf');
      const markup = html(<IrrbbTestsTable variant={v} />);
      setLang(lang);
      const text = visibleText(html(<IrrbbTestsTable variant={v} />));
      expect((markup.match(/data-segment=/g) ?? []).length).toBe(v.tests.filter((t) => t.segment).length);
      expect(text).toContain(lang === 'en' ? 'CLP leg' : 'Tramo CLP');
      expect(text).toContain(lang === 'en' ? 'UR leg' : 'Tramo UR');
    });
  }

  it('C15 B2, Q, m15: the Spanish thresholds and formulas are Spanish, symbols with a legend, and the verdict says exceeded', () => {
    const t = view(<ThresholdsView sel={sel15(rebaked15('long-uf'))} />, 'es');
    expect(t).toContain('RAN 21-13 Anexo 1');
    expect(t).not.toContain('Annex');
    expect(t).not.toMatch(/es superada/);
    expect(t).toMatch(/ninguna prueba excede su umbral|al menos una prueba excede su umbral/);
    const f = view(<IndexationView sel={sel15(rebaked15('cpi-surprise'))} />, 'es');
    expect(f).toContain('efecto = −PN_UR × s / 100, positivo es una pérdida');
    expect(f).toContain('cargo = 0,025 × |PN_UR|');
    expect(f).not.toMatch(/pn_ur|surprise_pp/);
    // the committed formula (an English string) still goes through the Spanish rules
    expect(view(<IndexationView sel={sel15(doc15('cpi-surprise'))} />, 'es')).toContain('posición neta en UF');
  });

  it('C15 m1, m9, m7: an empty floor-effects table says why, "capital de nivel 1" in Spanish, the compared measure is the one with the offset', () => {
    expect(view(<FloorsView sel={sel15(doc15('long-uf'))} />, 'en')).toContain('The effects table is empty');
    const es = view(<EveByLegView sel={sel15(doc15('offset-on-off'))} />, 'es');
    expect(es).not.toContain('capital N1');
    expect(es).toContain('con la compensación (la regla se compara, activa contra inactiva)');
  });
});
