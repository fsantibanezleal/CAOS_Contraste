// The Spanish of the English-only plain strings of the C18 bake that a view prints (U16-R2, b09 B1): the unit of a named parameter or of a
// path, the formula of the internal target, the document line of a source, the reference of a test. The bilingual texts of the document
// are written in Spanish by the producer (pipeline/cases/c18/spanish.py); these strings are not bilingual in the contract. A reference
// keeps the titles of the papers it cites as published. A string without an entry is printed as it is; r2.test.tsx fails on an English word.
const UNIT: Record<string, string> = {
  'CLP per EUR': 'CLP por EUR',
  'CLP millions': 'millones de CLP',
  'Banco Andino assets over the assets of the C17 bank': 'activos de Banco Andino sobre los activos del banco de C17',
  correlation: 'correlación',
  'degrees of freedom': 'grados de libertad',
  'fee income over NII': 'ingresos por comisiones sobre NII',
  "multiplier on C11's 99 percent one-day measure": 'multiplicador sobre la medida a un día al 99 por ciento de C11',
  'multiplier on a one-day measure, sqrt(250)': 'multiplicador sobre una medida a un día, raíz(250)',
  'operating cost over (NII + fee income)': 'costo operacional sobre (NII + ingresos por comisiones)',
  'ratio of normal quantiles z_0.999 / z_0.99': 'razón de cuantiles normales z_0.999 / z_0.99',
  'share of RWA': 'parte de los APR',
  percent: 'por ciento',
  'percent, annualised': 'por ciento, anualizado',
  'percentage points': 'puntos porcentuales',
  probability: 'probabilidad',
  year: 'año',
  years: 'años',
  lags: 'rezagos',
  'Abs. difference': 'diferencia absoluta',
  '% difference,  2017 PPP ; US$ Bn': '% de diferencia, PPA 2017; miles de millones de US$',
};

/** The Spanish of a unit written in English by the bake. */
export const unitEs = (unit: string, lang: 'en' | 'es'): string => (lang === 'es' ? UNIT[unit] ?? unit : unit);

const PHRASES: Array<[string, string]> = [
  // the EBA workbook keeps its published English title; the locator Contraste adds after it is Spanish (R3 c19 B3)
  [', United States rows', ', filas de Estados Unidos'],
  // the paper's title stays as published; the annotation after it is Contraste's and Spanish (U16-R4 c22 B2)
  [' (full allocation)', ' (asignación completa)'],
  ['dossier 05 G.5 (validation tests of an economic capital model: benchmark the aggregation against the simple sum and the variance-covariance formula, the copula-choice sensitivity, worst-case bounds, the correlation stress, the sign of every diversification benefit, one horizon and confidence level)',
    'dossier 05 G.5 (pruebas de validación de un modelo de capital económico: contrastar la agregación con la suma simple y con la fórmula de varianza-covarianza, la sensibilidad a la elección de cópula, las cotas del peor caso, el estrés de correlación, el signo de todo beneficio de diversificación, un horizonte y un nivel de confianza)'],
  ['dossier 05 G.5 (validation tests of an economic capital model: check the allocation sums to the total, the sensitivity checks)',
    'dossier 05 G.5 (pruebas de validación de un modelo de capital económico: verificar que la asignación suma el total, las verificaciones de sensibilidad)'],
  ['(one horizon and one confidence level for the aggregation)', '(un horizonte y un nivel de confianza para la agregación)'],
  ['(the aggregation ladder: simple sum, variance-covariance, copulas)', '(la escalera de agregación: suma simple, varianza-covarianza, cópulas)'],
  ['(VaR is not subadditive; worst-case VaR bounds by the rearrangement algorithm of Embrechts, Puccetti and Ruschendorf 2013,',
    '(el VaR no es subaditivo; cotas del VaR en el peor caso por el algoritmo de reordenamiento de Embrechts, Puccetti y Rüschendorf 2013,'],
  ['Rosenberg and Schuermann', 'Rosenberg y Schuermann'],
  ['(static balance sheet: constant total, no cure of stage 3)', '(balance estático: total constante, sin recuperación de la etapa 3)'],
  ['EBA 2025 EU-wide stress test, Methodological Note of 2025-01-20, paras 33, 34 and 90', 'Prueba de estrés de la UE 2025 de la EBA, Nota metodológica del 2025-01-20, párrafos 33, 34 y 90'],
  ['dossier 01 J.4 and dossier 05 H.5 and H.7: the reverse stress solution, the minimum Mahalanobis distance scenario',
    'dossier 01 J.4 y dossier 05 H.5 y H.7: la solución del estrés inverso, el escenario de mínima distancia de Mahalanobis'],
  ['(Contraste initiative research): back-cast the satellites through 2008-2009 and 2020 with data ending before the episode, check the sign of macro sensitivities, the static balance-sheet rules, bottom-up against top-down, severity against history',
    '(investigación de la iniciativa Contraste): retroproyectar los satélites por 2008-2009 y 2020 con datos que terminan antes del episodio, verificar el signo de las sensibilidades macro, las reglas del balance estático, de abajo hacia arriba contra de arriba hacia abajo, la severidad contra la historia'],
  ['dossier 05 H.7: document severity relative to history (GDP and unemployment paths against the GFC, as the EBA does)',
    'dossier 05 H.7: documentar la severidad relativa a la historia (trayectorias de PIB y desempleo contra la crisis financiera global, como hace la EBA)'],
  ['NGFS Phase V, NiGEM NGFS v1.24.2 runs, read through the IIASA Scenario Explorer', 'NGFS Fase V, corridas NiGEM NGFS v1.24.2, leídas mediante el IIASA Scenario Explorer'],
  [', as percent of RWA (RAN 21-13 section I;', ', como porcentaje de los APR (RAN 21-13 sección I;'],
  ['H.4 and H.7', 'H.4 y H.7'],
];

/** The authors' names as published, in both languages (U16-R4 c22 m11, c23 m9: the engine's reference writes "Ruschendorf"). */
const AUTHORS: ReadonlyArray<readonly [RegExp, string]> = [[/\bRuschendorf\b/g, 'Rüschendorf']];
const authors = (s: string): string => AUTHORS.reduce((acc, [from, to]) => acc.replace(from, to), s);

/** The Spanish of a reference, formula or document line: its English phrases are replaced, the papers' titles and the codes stay. */
export function phraseEs(s: string | null | undefined, lang: 'en' | 'es'): string {
  if (s === null || s === undefined) return '';
  if (lang === 'en') return authors(s);
  return authors(PHRASES.reduce((acc, [en, es]) => acc.replaceAll(en, es), s));
}
