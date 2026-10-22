// The Spanish of the English-only strings of the C20 bake (U16-R2, b09 B3): the basis of a named parameter, its unit, the role of a
// dataset, the description of an engine, an age group, the note of a test. A string without an entry is printed as it is, and r2.test.tsx
// renders every view on every committed document in Spanish and fails on an English word left. The tests, units and bases are the
// bake's (pipeline/cases/c20/conv.py, models.py); they stay English in the document, which is the contract's text.
import { localise, type Rule } from '../c14/localise';

type Map = Record<string, string>;
const exact = (m: Map): ReadonlyArray<Rule> => Object.entries(m).map(([en, es]) => [new RegExp(`^${en.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}$`), () => es] as const);

const TEXT: Map = {
  // the basis of a named parameter
  'Degradation of AUC tolerated at the preset scale 0.1; about 2.5 standard errors of an AUC on the Taiwan holdout (about 6,000 holdout rows).':
    'Degradación del AUC tolerada a la escala preestablecida 0,1; cerca de 2,5 errores estándar de un AUC sobre la reserva de Taiwán (cerca de 6.000 filas de reserva).',
  'Noise scales for the perturbation robustness grid (06 C.7 l.1009-1012 gives the construction, no values).':
    'Escalas de ruido de la grilla de robustez a perturbaciones (06 C.7 l.1009-1012 da la construcción, no los valores).',
  'Refits of the reason-code stability (04 J.2 l.881-883 gives none).': 'Reajustes de la estabilidad de los códigos de razón (04 J.2 l.881-883 no da ninguno).',
  'Seeds of the seed sweep (06 I.1 l.1191 gives none); 20 gives a standard deviation of the AUC with a relative error near 16 percent.':
    'Semillas del barrido de semillas (06 I.1 l.1191 no da ninguna); 20 da una desviación estándar del AUC con un error relativo cercano a 16 por ciento.',
  'The cut-off is the baseline score quantile that declines this share; held fixed under every shift (decision Q10).':
    'El punto de corte es el cuantil del puntaje base que rechaza esta parte; se mantiene fijo bajo todo cambio (decisión Q10).',
  "The dossier's example is the worst 10 percent (06 C.7 l.1013-1014).": 'El ejemplo del dossier es el peor 10 por ciento (06 C.7 l.1013-1014).',
  'The shift score ranking subsamples; a classifier of development against evaluation rows (06 C.7 l.1048-1051 resemblance AUC).':
    'El puntaje de cambio que ordena las submuestras; un clasificador de filas de desarrollo contra filas de evaluación (06 C.7 l.1048-1051, AUC de semejanza).',
  'Train minus test AUC gap beyond which the overfit flag is raised (06 C.7 l.1016-1018 gives no value).':
    'Brecha de AUC entre entrenamiento y prueba sobre la cual se levanta la marca de sobreajuste (06 C.7 l.1016-1018 no da valor).',
  'k: a slice is a weak spot when its test error exceeds k times the average (06 C.7 l.1016-1018).':
    'k: un corte es un punto débil cuando su error de prueba excede k veces el promedio (06 C.7 l.1016-1018).',
  // the unit of a named parameter
  'AUC points': 'puntos de AUC',
  'bootstrap refits': 'reajustes bootstrap',
  "multiple of each feature's standard deviation": 'múltiplo de la desviación estándar de cada variable',
  'multiple of the average test error': 'múltiplo del error promedio de prueba',
  'name of the score': 'nombre del puntaje',
  'retraining seeds': 'semillas de reentrenamiento',
  'share of baseline decisions declined': 'parte de las decisiones base rechazadas',
  'share of the evaluation rows': 'parte de las filas de evaluación',
  'inverse penalty': 'penalización inversa',
  'information value': 'valor de información',
  'fraction of records': 'fracción de registros',
  'candidate rules': 'reglas candidatas',
  // the role of a dataset
  'German model fit (setup and adaptation batches) and shock evaluation (test batches)': 'Ajuste del modelo alemán (lotes de preparación y adaptación) y evaluación de los choques (lotes de prueba)',
  'model fit and locked holdout of the Fed shift probes (3-year file)': 'ajuste del modelo y reserva bloqueada de las sondas de cambio de la Fed (archivo de 3 años)',
  'model fit and locked holdout of the seed, perturbation and leakage variants': 'ajuste del modelo y reserva bloqueada de las variantes de semillas, perturbación y fuga',
  'real drift between the portfolios and the size of the synthetic shift': 'deriva real entre las carteras y tamaño del cambio sintético',
  // the engine of a model
  'own on optbinning': 'propio sobre optbinning',
  'scikit-learn trees and LogisticRegression, own rule extraction': 'árboles de scikit-learn y regresión logística de scikit-learn, extracción de reglas propia',
  'calibration slice': 'corte de calibración',
  // the bands of the drift index and the notes of the tests
  'conventional band: little change (0.10/0.25 rule of thumb, no error control)': 'banda convencional: cambio pequeño (regla empírica 0,10/0,25, sin control del error)',
  'conventional band: moderate change (0.10/0.25 rule of thumb, no error control)': 'banda convencional: cambio moderado (regla empírica 0,10/0,25, sin control del error)',
  'conventional band: significant change (0.10/0.25 rule of thumb, no error control)': 'banda convencional: cambio significativo (regla empírica 0,10/0,25, sin control del error)',
  'not evaluated: an estimate, not a test: CBPE estimates performance without labels (06 C.7 l.1052-1058); it assumes calibrated-probabilities, no-concept-drift, no-extrapolation, adequate-sample; it complements, never replaces, back-testing':
    'no evaluada: una estimación, no una prueba: CBPE estima el desempeño sin etiquetas (06 C.7 l.1052-1058); supone probabilidades calibradas, ausencia de deriva de concepto, ausencia de extrapolación y muestra adecuada; complementa y nunca reemplaza la prueba retrospectiva',
  // the groups of the fairness battery
  'under 30': 'menores de 30',
  '50 and over': '50 y más',
  'uci-polish-3year-holdout (3,151 rows, locked)': 'uci-polish-3year-holdout (3.151 filas, bloqueada)',
};

export const C20_RULES: ReadonlyArray<Rule> = [
  ...exact(TEXT),
  [/^(\d+) to (\d+)$/, (g) => `${g[1]} a ${g[2]}`],
  [/^(.+), seed (\d+)$/, (g) => `${g[1]}, semilla ${g[2]}`],
];

/** The Spanish of a document string, or the string itself in English or when no entry knows it. */
export const es = (s: string | null | undefined, lang: 'en' | 'es'): string => localise(s, lang, C20_RULES);

type Row = { notes?: string | null };
/** The tests of a document with their notes in the language: the shared tests table prints `notes` as it finds it. */
export function localTests<T extends Row>(tests: T[], lang: 'en' | 'es'): T[] {
  return lang === 'en' ? tests : tests.map((t) => (t.notes ? { ...t, notes: es(t.notes, lang) } : t));
}

/** The named parameters with their basis and unit in the language: the shared parameter table prints them as it finds them. */
export function localParams<T extends { basis: string; unit: string }>(params: T[], lang: 'en' | 'es'): T[] {
  return lang === 'en' ? params : params.map((p) => ({ ...p, basis: es(p.basis, lang), unit: es(p.unit, lang) }));
}
