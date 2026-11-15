// Reference identifiers in running text (a paragraph, section or table number, an arXiv id, a software version) are
// marked translate="no" so the gate's Spanish-number check (G11) reads them as identifiers; a decimal is never marked.
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { markRefs } from './refs';

const html = (text: string, lang: 'en' | 'es' = 'es') => renderToStaticMarkup(<>{markRefs(text, lang)}</>);
const marked = (text: string, lang: 'en' | 'es' = 'es') => [...html(text, lang).matchAll(/<span translate="no">([^<]*)<\/span>/g)].map((m) => m[1]);

describe('markRefs: identifiers', () => {
  it('marks a section, chapter, table and paragraph number after its word, in both languages', () => {
    expect(marked('Hampel (1986) sección 4.2, como')).toEqual(['4.2']);
    expect(marked('Hampel (1986) section 4.2, as', 'en')).toEqual(['4.2']);
    expect(marked('secciones 2.1 y 2.2')).toEqual(['2.1 y 2.2']);
    expect(marked('Capítulo 3.1 del compendio')).toEqual(['3.1']);
    expect(marked('Tabla 3.3, otros depósitos')).toEqual(['3.3']);
    expect(marked('ECB LiST Table 2.1: the haircut order', 'en')).toEqual(['2.1']);
    expect(marked('párrafo 7.4 de la nota')).toEqual(['7.4']);
    expect(marked('principio 3.3(b)(iii); guía')).toEqual(['3.3(b)(iii)']);
  });

  it('marks a number in parentheses after an equation word', () => {
    expect(marked('ecuación (3.1)')).toEqual(['3.1']);
    expect(marked('Anderson and Goodman (1957), equation (3.1)', 'en')).toEqual(['3.1']);
  });

  it('marks every further number of the list the word starts, and no number of another shape', () => {
    expect(marked('Tablas 3.2 y 3.3, Adverso')).toEqual(['3.2 y 3.3']);
    expect(marked('LiST paras 114 to 118 and 7.5 million', 'en')).toEqual(['114 to 118']);
    expect(marked('Table 3.2, 3.3 and 3.4 of the note', 'en')).toEqual(['3.2, 3.3 and 3.4']);
    expect(marked('tabla 3.2 y 4 casos de 2.5 millones')).toEqual(['3.2']);
  });

  it('marks a standard paragraph, a package version, a licence version, a v prefix and an arXiv id', () => {
    expect(marked('IFRS 9 5.5 está excluida')).toEqual(['5.5']);
    expect(marked('NIIF 9 5.5.17 y la NIC 39 6.4.1')).toEqual(['5.5.17', '6.4.1']);
    expect(marked('contra QuantLib 1.44 en')).toEqual(['1.44']);
    expect(marked('CC0 1.0 Universal')).toEqual(['1.0']);
    expect(marked('versión 2.0.0 (C.7)')).toEqual(['2.0.0']);
    expect(marked('release v0.05 of the package', 'en')).toEqual(['0.05']);
    expect(marked('Tasche (2008), arXiv 0708.2542 (asignación)')).toEqual(['0708.2542']);
    expect(marked('Brigo et al., arXiv:0812.4210, ecuaciones 55 a 57')).toEqual(['0812.4210', '55 a 57']);
    expect(marked('Wald de una cola, ecuación (10) de arXiv 2502.01267')).toEqual(['2502.01267']);
  });

  it('marks two identifiers in one text, one at the start and one at the end', () => {
    expect(marked('Sección 2.2: indicador; sección 2.1')).toEqual(['2.2', '2.1']);
    expect(marked('línea 237 y línea 480 (Tabla 3.3)')).toEqual(['3.3']);
  });

  it('reads accented and unaccented spellings and either case', () => {
    expect(marked('seccion 4.2 y SECCIÓN 4.3')).toEqual(['4.2', '4.3']);
    expect(marked('parrafo 7.4')).toEqual(['7.4']);
  });

  it('does not mark a lone whole number, which no reader takes for a decimal', () => {
    expect(marked('línea 237 y la nota 3 de la tabla 12')).toEqual([]);
    expect(html('Annex 3 is N/A', 'en')).toBe('Annex 3 is N/A');
  });

  it('keeps the Spanish preposition para out of the reference words, and keeps para in English', () => {
    expect(marked('un cupo para 2.5 millones de cuentas')).toEqual([]);
    expect(marked('see para 7.4 of the note', 'en')).toEqual(['7.4']);
  });
});

describe('markRefs: what is not an identifier', () => {
  it('never marks a bare decimal, a decimal after other words, or a Spanish thousands group', () => {
    for (const text of ['la tasa fue 2.5 por ciento', 'el valor 0.62 del índice', 'son 27.345 cuentas', 'razón de 11.0 a 1', 'promedio 3.3 en 2025']) {
      expect(marked(text)).toEqual([]);
      expect(html(text)).toBe(text);
    }
  });

  it('returns the text itself when it has no identifier, and an empty text as it is', () => {
    expect(markRefs('sin identificadores 2026-09-29', 'es')).toBe('sin identificadores 2026-09-29');
    expect(markRefs('', 'es')).toBe('');
    expect(markRefs(undefined, 'es')).toBe('');
    expect(markRefs(null, 'en')).toBe('');
  });

  it('keeps every character of the text around the marked identifiers', () => {
    const text = 'Informe, agosto 2026; sección 2.2: indicador 2,56 %; https://x.cl/a_1.pdf';
    expect(html(text).replace(/<\/?span[^>]*>/g, '')).toBe(text);
  });

  it('does not wrap a number inside a longer word or code token', () => {
    expect(marked('tabla3.3 y v1x.2')).toEqual([]);
  });
});

// The full texts of the 30 failures of the Spanish pass of release 1.00.001 (every case, 1280x800, light): no dotted number of the
// gate's G11 pattern is left outside a marked identifier.
const G11 = /(?<![\w.,/:@#])(\d+)\.(\d+)(?:[eE][-+]?\d+)?(?![\w/@]|\.\d)/g;
const unmarked = (text: string, lang: 'en' | 'es'): string[] => {
  const outside = html(text, lang).replace(/<span translate="no">[^<]*<\/span>/g, ' ').replace(/&[a-z#0-9]+;/g, ' ');
  // the gate lets a Spanish thousands group through ("2.346", "171.500")
  return [...outside.matchAll(G11)].filter((m) => !(m[1].length <= 3 && m[2].length === 3)).map((m) => m[0]);
};
const FAILURES: Array<[string, string]> = [
  ['C02 overfit', 'dossier 06 (gestión del riesgo de modelo y validación) C.7 validación de ML/IA e I.1, el catálogo de pruebas del motor de validación; la interfaz documentada de validación de ML del motor, versión 2.0.0 (C.7 l.1041-1044, I.1 l.1196); SS1/23 principio 3.3(b)(iii); guía del BCE párrafo 60'],
  ['C06 context', 'EBA (2023), IFRS 9 implementation by EU institutions, 2023 Monitoring report, EBA/Rep/2023/36, doi:10.2853/269836, párrafo 97; Anderson y Goodman (1957), doi:10.1214/aoms/1177707039, ecuación (3.1)'],
  ['C07 regimes', 'IFRS 9 5.5 está excluida para los créditos bancarios en Chile: esto es una comparación, no la provisión que constituyen los bancos chilenos.'],
  ['C07 validation', 'Comercial de evaluación individual. CMF CNCB Capítulo B-1 (Circular 2.346), dossier 03 sección D.3; leído con las provisiones B-1 del motor (sección 2.1 de B-1)'],
  ['C07 context dd', 'La provisión estatutaria sobre créditos en Chile: IFRS 9 5.5 está excluida para créditos en el compendio de la CMF.'],
  ['C07 context 2.2', 'CMF, Informe del Desempeño del Sistema Bancario y Cooperativas, agosto 2026 (publicado el 2026-09-29); sección 2.2: indicador de provisiones comercial 2,56 %; https://www.cmfchile.cl/portal/estadisticas/617/articles-113863_recurso_1.pdf'],
  ['C07 context 2.1', 'CMF, Informe del Desempeño del Sistema Bancario y Cooperativas, agosto 2026 (publicado el 2026-09-29); sección 2.1: créditos en cuotas, producto con la mayor participación en consumo (53,38 %)'],
  ['C10 capital', 'Tasche (2008), Capital allocation to business units and sub-portfolios: the Euler principle, arXiv 0708.2542 (asignación completa); dossier 05 G.5 (pruebas de validación)'],
  ['C11 context', 'Fissler y Ziegel 2016, Ann. Statist. 44(4); Patton, Ziegel y Chen 2019; arXiv 2606.04576 (preimpresión; solo retador)'],
  ['C11 context 2', 'Gibbs and Candes 2021, NeurIPS 34, arXiv 2106.00170; Christoffersen 1998, Int. Econ. Rev. 39(4); Acerbi and Szekely 2014, Risk; Fissler and Ziegel 2016, Ann. Statist. 44(4)'],
  ['C12 tests 1', 'adenda de investigación R4: el ajuste de theta revalora la curva de hoy, así que los precios descontados de bonos son martingalas (QuantLib 1.44 hullwhite.hpp)'],
  ['C12 tests 2', 'QuantLib 1.44 hullwhite.cpp discountBondOption (adenda R4); umbral de diferencia relativa 1e-6'],
  ['C12 tests 3', 'Opción sobre permuta pagadora frente a QuantLib 1.44'],
  ['C12 tests 4', 'QuantLib 1.44 jamshidianswaptionengine.cpp (adenda R4); umbral de diferencia relativa 1e-6'],
  ['C12 estimator', 'AR(1) exacto por MCO sobre la tasa cero más corta del Tesoro (Brigo et al., arXiv 0812.4210, ecuaciones 55 a 57)'],
  ['C12 limits', 'Las derivaciones de revista de las formas cerradas de Hull-White (Hull y White 1990 y 1994, Jamshidian 1989) no se leyeron como artículos; la opción sobre bono y la opción sobre permuta del motor se concilian numéricamente con QuantLib 1.44.'],
  ['C16 tests 1', 'dossier 05 E.1 línea 237 (capitalización diaria constante sobre días relevantes, Tabla 3.3 y párrafo 107 de la nota de LiST) y la fila de aceptación del SDD'],
  ['C16 tests 2', 'dossier 05 E.1 línea 238 y línea 480 (nota de LiST párrafo 74, Tabla 2.1: el orden de los recortes, la tabla de acciones, 30 y 50 por ciento)'],
  ['C16 context', 'Nota metodológica LiST 2019 del BCE, Tablas 3.2 y 3.3, Adverso y Extremo'],
  ['C17 model 1', 'riskvalidation.oprisk.robust.sla_var_mean_adjusted, la forma de arXiv 1607.02319 (Degen 2010); el texto primario de Opdyke y Cavallo (2012) no se leyó'],
  ['C17 model 2', 'Hampel, Ronchetti, Rousseeuw y Stahel (1986) sección 4.2, como lo usan Opdyke y Cavallo (2012)'],
  ['C18 tests', 'Tasche (2008), Capital allocation to business units and sub-portfolios: the Euler principle, arXiv 0708.2542 (asignación completa)'],
  ['C21 situation', 'Wald de una cola, ecuación (10) de arXiv 2502.01267'],
  ['C21 context', 'Como obra del Gobierno de Estados Unidos, este paquete (salvo las excepciones listadas abajo) es de dominio público dentro de Estados Unidos. Además, renunciamos a los derechos de autor y derechos conexos sobre la obra en todo el mundo mediante la dedicación de dominio público CC0 1.0 Universal.'],
];

describe('markRefs: the texts of the release 1.00.001 Spanish pass', () => {
  for (const [where, text] of FAILURES) {
    it(`${where}: every dotted number is a marked identifier`, () => {
      expect(unmarked(text, 'es')).toEqual([]);
    });
  }

  it('the same texts in English are marked the same way, and a decimal beside an identifier stays visible to the gate', () => {
    expect(unmarked('Tables 3.2 and 3.3 of the note; the rate was 2.5 percent', 'en')).toEqual(['2.5']);
    expect(unmarked('sección 4.2: una tasa de 7.5 por ciento', 'es')).toEqual(['7.5']);
  });
});
