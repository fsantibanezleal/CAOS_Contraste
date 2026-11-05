// U16-F10b (fix round 4, the R3 capture review of C02, batch c03), on the committed C02 documents in both languages. The
// producer writes the named parameter's unit and basis and the ladder's engine as bilingual texts (c02-outputs 3.0.0,
// c02-models 2.0.0), and the committed documents carry them since the integrator's re-bake; the English string form the
// schema still accepts is rendered on a copy of the committed documents with those fields put back to their English strings.
import { afterEach, describe, expect, it } from 'vitest';
import type { components } from '../../lib/contract.gen';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc } from '../c14/testkit';
import { fixtureData, html, setLang } from '../c20/testkit';
import { C02ContextView, ChallengerReadout, RungReadout } from './C02Common';
import { CalibrationView, RocCapView, StabilityView } from './DiscriminationViews';
import { TransferView, transferBars } from './HorizonViews';
import { defaultSel, type C02Sel } from './selection';

type Outputs = components['schemas']['c02Outputs'];
const title = { en: 'Corporate PD across horizons', es: 'PD corporativa a distintos horizontes' };
const h1 = committedDoc<VariantArtifact<Outputs>>('C02', 'h1');
const pooled = committedDoc<VariantArtifact<Outputs>>('C02', 'pooled');
const models = committedDoc<ModelsArtifact>('C02', 'models-polish-horizons');
const h2cells = () => committedDoc<VariantArtifact<Outputs>>('C02', 'h2').outputs.transfer.cells.filter((c) => c.model_id === h1.outputs.transfer.cells[0].model_id);

// the producer's texts (data-pipeline/pipeline/cases/c02/conventions.py parameters(), models.py ENGINE_TEXT)
const UNIT = { en: 'AUC points', es: 'puntos de AUC' };
const BASIS = {
  en: 'Train minus test AUC gap beyond which the overfit flag is raised (06 C.7 l.1016-1018 gives no value); about 1.5 to 3 standard errors of an AUC on the Polish holdouts (271 to 515 events per file), approved as a named convention',
  es: 'Brecha entre el AUC de entrenamiento y el de prueba sobre la cual se levanta la alerta de sobreajuste (06 C.7 l.1016-1018 no da un valor); entre 1,5 y 3 errores estándar de un AUC en las muestras reservadas polacas (271 a 515 eventos por archivo), aprobada como convención con nombre',
};
const ENGINE_ES: Record<string, string> = {
  own: 'propio',
  'own on optbinning': 'propio sobre optbinning',
  'scikit-learn trees and LogisticRegression, own rule extraction': 'árboles y regresión logística de scikit-learn, extracción de reglas propia',
};

/** The committed documents as they are (bilingual since the re-bake). */
function rebaked(): { v: VariantArtifact<Outputs>; m: ModelsArtifact } {
  return { v: h1, m: models };
}

/** The committed documents with the bilingual fields put back to their English strings, the form the schema still accepts. */
function stringForm(): { v: VariantArtifact<Outputs>; m: ModelsArtifact } {
  const en = (x: unknown) => (x !== null && typeof x === 'object' && 'en' in (x as object) ? (x as { en: string }).en : x);
  const v = structuredClone(h1);
  const params = (o: { parameters: unknown[] }) => o.parameters.map((p) => ({ ...(p as object), unit: en((p as { unit: unknown }).unit), basis: en((p as { basis: unknown }).basis) }));
  (v.outputs as unknown as { parameters: unknown[] }).parameters = params(v.outputs as unknown as { parameters: unknown[] });
  const m = structuredClone(models) as unknown as { fit: { ladder: Array<{ engine: unknown }>; parameters: unknown[] } };
  m.fit.ladder = m.fit.ladder.map((l) => ({ ...l, engine: en(l.engine) }));
  m.fit.parameters = params(m.fit);
  return { v, m: m as unknown as ModelsArtifact };
}

const selOf = (v: VariantArtifact<Outputs>, m: ModelsArtifact = models): C02Sel =>
  defaultSel(fixtureData('C02', v as unknown as VariantArtifact, m, title)) as C02Sel;
const text = (markup: string) => markup.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ');

describe('U16-R3 c03 on the committed C02 documents', () => {
  afterEach(() => setLang('en'));

  it('B2: the Spanish named parameters print the unit and the basis in Spanish once the documents carry them', () => {
    const { v, m } = rebaked();
    setLang('es');
    for (const markup of [html(<C02ContextView sel={selOf(v, m)} />), html(<StabilityView sel={selOf(v, m)} />)]) {
      const t = text(markup);
      expect(t).toContain('0,05 puntos de AUC');
      expect(t).toContain('aprobada como convención con nombre');
      expect(t).not.toContain('AUC points');
      expect(t).not.toContain('Train minus');
    }
    setLang('en');
    expect(text(html(<C02ContextView sel={selOf(v, m)} />))).toContain('0.05 AUC points');
  });

  it('B2: the English string form still renders, in both languages', () => {
    const { v, m } = stringForm();
    setLang('en');
    expect(text(html(<C02ContextView sel={selOf(v, m)} />))).toContain('0.05 AUC points');
    setLang('es');
    expect(text(html(<C02ContextView sel={selOf(v, m)} />))).toContain('0,05');
  });

  it('B2 and B3: the committed documents carry the bilingual texts of the producer', () => {
    const p = (h1.outputs as unknown as { parameters: Array<{ unit: unknown; basis: unknown }> }).parameters[0];
    expect(p.unit).toEqual(UNIT);
    expect(p.basis).toEqual(BASIS);
    const ladder = (models as unknown as { fit: { ladder: Array<{ engine: { en: string; es: string } }> } }).fit.ladder;
    for (const l of ladder) if (l.engine.en in ENGINE_ES) expect(l.engine.es).toBe(ENGINE_ES[l.engine.en]);
  });

  it('B3: the Spanish ladder prints its engine in Spanish, the library names as published', () => {
    const { v, m } = rebaked();
    setLang('es');
    const t = text(html(<C02ContextView sel={selOf(v, m)} />));
    expect(t).toContain('propio sobre optbinning');
    expect(t).toContain('árboles y regresión logística de scikit-learn, extracción de reglas propia');
    expect(t).not.toMatch(/\bown\b/);
    expect(t).not.toContain('rule extraction');
    setLang('en');
    expect(text(html(<C02ContextView sel={selOf(v, m)} />))).toContain('own on optbinning');
  });

  it('M1: the transfer matrix comes first and the 25 bars scroll in a drawing of bounded height', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const markup = html(<TransferView sel={selOf(h1)} />);
      const table = markup.indexOf('data-table="transfer"');
      const drawing = markup.indexOf('ct-stack-chart');
      expect(table).toBeGreaterThan(-1);
      expect(drawing).toBeGreaterThan(table); // the matrix is above the drawing, never clipped under it
      const min = /ct-stack-chart" style="min-height:([\d.]+)rem/.exec(markup);
      expect(min, 'the drawing declares its least height').not.toBeNull();
      expect(Number(min?.[1])).toBeLessThanOrEqual(14);
    }
  });

  it('m13 and m14: the transfer bars in fitted and scored order, the Spanish labels in years', () => {
    // the committed order: the loaded file's row first, then the others as they load (h2 began "Fitted on 2y")
    const cells = [...h2cells(), ...h1.outputs.transfer.cells];
    const bars = transferBars(cells);
    const order = bars.map((b) => b.id);
    expect(order).toEqual([...order].sort());
    expect(bars[0].label).toEqual({ en: 'Fitted on 1 year, scored on 1 year', es: 'Ajustado en 1 año, puntuado en 1 año' });
    expect(bars.find((b) => b.id === '1-2')?.label).toEqual({ en: 'Fitted on 1 year, scored on 2 years', es: 'Ajustado en 1 año, puntuado en 2 años' });
    for (const b of bars) expect(b.label.es).not.toMatch(/\d+a\b/);
  });

  it('m5: the pooled scorecard gap of -0.000002 prints as 0.000, never "-0.000"', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      expect(text(html(<StabilityView sel={selOf(pooled)} />))).not.toMatch(/-0[.,]000\b/);
    }
  });

  it('m9: the rail read-outs are replays of the bake, not live', () => {
    const s = selOf(h1);
    for (const markup of [html(<RungReadout sel={s} />), html(<ChallengerReadout sel={s} />)]) {
      expect(markup).toContain('data-lane="replay"');
      expect(markup).not.toContain('data-lane="live"');
    }
  });

  it('m4: the Spanish calibration note says dashed and above, as the English does', () => {
    setLang('es');
    const t = text(html(<CalibrationView sel={selOf(h1)} />));
    expect(t).toContain('En la línea discontinua una PD está calibrada; por encima de ella');
    expect(t).not.toContain('punteada');
  });

  it('m7: the ladder says the constant PD is fitted and carries no test battery', () => {
    setLang('en');
    expect(text(html(<C02ContextView sel={selOf(h1)} />))).toContain('The constant PD is fitted and recorded, but it has no risk groups');
    setLang('es');
    expect(text(html(<C02ContextView sel={selOf(h1)} />))).toContain('La PD constante se ajusta y se registra, pero no tiene grupos de riesgo');
  });

  it('m10: the split names its slices in its label, the value keeps the numbers', () => {
    setLang('es');
    const t = text(html(<C02ContextView sel={selOf(h1)} />));
    expect(t).toContain('Partición (entrenamiento / calibración / reservada)');
    expect(t).not.toContain('1.773 (entrenamiento');
  });

  it('m1 and m12: the notes say what a light reads (DeLong two-sided; PSI and CSI by their p-value)', () => {
    setLang('en');
    expect(text(html(<RocCapView sel={selOf(h1)} />))).toContain('a red DeLong row says the two rungs differ, not that the challenger is worse');
    expect(text(html(<StabilityView sel={selOf(h1)} />))).toContain('the light of a PSI or CSI row is its chi-square p-value');
    setLang('es');
    expect(text(html(<RocCapView sel={selOf(h1)} />))).toContain('una fila DeLong roja dice que los dos peldaños difieren, no que el retador sea peor');
    expect(text(html(<StabilityView sel={selOf(h1)} />))).toContain('la luz de una fila de PSI o CSI es su valor p de chi cuadrado');
  });
});
