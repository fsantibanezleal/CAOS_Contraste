// U16-F10b (fix round 4, the R3 capture review of C07, batch c08), on the committed C07 documents in both languages. The producer
// now writes the calibration sources as bilingual texts (c07-models 3.0.0); the committed documents carry the English strings until
// the integrator re-bakes, so the Context is rendered on both shapes.
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact } from '../../lib/contract.types';
import { setLang } from '../c03/u6-testkit';
import { committedData, view } from '../c08/spanish-testkit';
import { C07ContextView } from './C07Common';
import { SegmentsView, ThreeRegimeView, BridgeView } from './RegimeViews';
import { TablesView } from './ValidationViews';
import { defaultSel, type C07Sel } from './selection';
import { html } from '../c20/testkit';

const TITLE = { en: 'Chile provisions trilogy', es: 'Trilogía de provisiones de Chile' };
const at = (file: string) => defaultSel(committedData('C07', file, 'models-banco-andino.json', TITLE)) as C07Sel;
const ENGLISH_SOURCE = /\bpublished\b|\bcolumn \b|\bsection \d|includes loans|Desempeno|dias o mas|\bindice\b|\bcreditos\b|participacion/;

/** The models document with the bilingual sources the producer now writes (as tests/c07/test_c07_u16_f10b.py pins them). */
function rebaked(): C07Sel {
  const s = at('base.json');
  const m = structuredClone(s.data.models) as unknown as { fit: { bank: { calibration_source: unknown }; calibration_targets: Array<{ source: unknown }> } };
  m.fit.bank.calibration_source = { en: 'CMF Informe del Desempeño del Sistema Bancario y Cooperativas, 2026-08 (url), public web publication (the CMF Bancos API key is absent)', es: 'CMF Informe del Desempeño del Sistema Bancario y Cooperativas, 2026-08 (url), publicación web pública (falta la clave de la API de CMF Bancos)' };
  m.fit.calibration_targets = m.fit.calibration_targets.map((t, i) => ({ ...t, source: { en: `source ${i}, section 2.2`, es: `fuente ${i}, sección 2.2` } }));
  return { ...s, data: { ...s.data, models: m as unknown as ModelsArtifact } };
}

describe('U16-R3 c08 on the committed C07 documents', () => {
  afterEach(() => setLang('en'));

  it('B1: the Spanish Context prints the calibration sources in Spanish, with the report\'s accents (committed strings)', () => {
    setLang('es');
    const text = view(<C07ContextView sel={at('base.json')} />);
    expect(text).not.toMatch(ENGLISH_SOURCE);
    expect(text).toContain('Informe del Desempeño del Sistema Bancario y Cooperativas');
    expect(text).toContain('publicado el 2026-09-29');
    expect(text).toContain('Cuadro N° 1, columna Bancos');
    expect(text).toContain('morosidad de 90 días o más');
    expect(text).toContain('(incluye créditos a bancos)');
  });

  it('B1: the bilingual sources of a re-baked document are picked by language', () => {
    setLang('es');
    const es = view(<C07ContextView sel={rebaked()} />);
    expect(es).toContain('fuente 3, sección 2.2');
    expect(es).toContain('publicación web pública (falta la clave de la API de CMF Bancos)');
    expect(es).not.toMatch(ENGLISH_SOURCE);
    setLang('en');
    expect(view(<C07ContextView sel={rebaked()} />)).toContain('source 3, section 2.2');
  });

  it('M1: the Segments view gives the drawing and the gap table a card each, so neither is cut at 1280', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const markup = html(<SegmentsView sel={at('base.json')} />);
      expect([...markup.matchAll(/<figure[^>]*class="caos-plot/g)].length).toBe(2);
      expect(markup).not.toMatch(/ct-stack-table[\s\S]*data-table="segments"/); // the table is not squeezed under the drawing
      expect(markup).toContain('data-table="segments"');
    }
  });

  it('M2: the provision-by-segment drawing of the Three regimes view keeps a least height for 18 bars on a phone', () => {
    const markup = html(<ThreeRegimeView sel={at('base.json')} />);
    expect(markup).toMatch(/class="ct-map"[^>]*style="[^"]*min-height:\s*28rem/);
  });

  it('m1: the grouped and bridge notes keep the colour key and leave the pointer instruction to the shell', () => {
    for (const el of [<ThreeRegimeView sel={at('base.json')} />, <BridgeView sel={at('base.json')} />]) {
      for (const lang of ['en', 'es'] as const) {
        setLang(lang);
        const t = view(el);
        expect(t).not.toMatch(/to read it\.|para leerla\./);
      }
    }
    setLang('en');
    expect(view(<ThreeRegimeView sel={at('base.json')} />)).toContain('Blue is B-1, amber is IFRS 9');
  });

  it('m4, m5 and m13: a reason the whole table shares is said once, a column of one value is dropped, PE = PI × PDI', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const markup = html(<TablesView sel={at('base.json')} />);
      const t = view(<TablesView sel={at('base.json')} />);
      const reasons = (t.match(/la tabla no da PDI para esta celda|the table gives no PDI for this cell/g) ?? []).length;
      expect(reasons).toBe(0);
      expect(t).toMatch(lang === 'en' ? /gives no PDI for its cells/ : /no da PDI para sus celdas/);
      const individual = markup.match(/<table[^>]*data-table-id="individual-categories"[\s\S]*?<\/table>/)?.[0] ?? '';
      expect(individual).not.toMatch(/>(?:category|categoría)</);
      expect(t).toContain('PE = PI × PDI');
      expect(t).not.toContain('PE = PI x PDI');
    }
  });
});
