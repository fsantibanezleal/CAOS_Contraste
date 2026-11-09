// What the recalibration views say next to the C11 verdict (viz review F1, SHOW-F). The window documents carry the pipeline's reading
// of the hypothesis by its pass criterion ("holds in 6 of 6 cells"); the adaptive conformal manuscript measured that the wrapper makes
// the hit count less variable than the binomial law behind the Kupiec test, the conditional coverage test and the Basel zones, so those
// back-tests accept recalibrated runs too easily and every pass count of a recalibrated run is an upper bound. The views therefore
// present the verdict as the bake's reading by the criterion, never as an endorsement, and say so beside it. The wording is number-free
// on purpose: the measured spread is not in the window documents, so no number of the manuscript is typed into a view.
export type Bi = { en: string; es: string };

export const MANUSCRIPT_URL = 'https://github.com/fsantibanezleal/CAOS_Contraste/tree/main/manuscripts/adaptive-conformal-recalibration-of-var';

/** The label of the document's own verdict: it is a reading by the pass criterion fixed before the run. */
export const VERDICT_LABEL: Bi = {
  en: "The bake's reading by the pass criterion fixed before the run:",
  es: 'La lectura del cálculo por el criterio de aprobación fijado antes de la corrida:',
};

/** The caveat that stands beside every pass, p-value and zone of a recalibrated run. */
export const TESTS_TOO_EASY: Bi = {
  en: 'These back-tests accept recalibrated runs too easily: the recalibration makes the breach count less variable than the binomial law behind the Kupiec test, the conditional coverage test and the Basel zones, so the passes, p-values and zones of recalibrated runs are upper bounds. The evidence is the breach count against the expected count.',
  es: 'Estas pruebas retrospectivas aceptan con demasiada facilidad las corridas recalibradas: la recalibración hace que el conteo de excedencias varíe menos que la ley binomial en que se basan la prueba de Kupiec, la prueba de cobertura condicional y las zonas de Basilea, así que las aprobaciones, los valores p y las zonas de las corridas recalibradas son cotas superiores. La evidencia es el conteo de excedencias frente al esperado.',
};

export const MANUSCRIPT_LINK: Bi = {
  en: 'The adaptive conformal recalibration manuscript',
  es: 'El manuscrito de la recalibración conforme adaptativa',
};

/** The "passes" column of the score table: for a recalibrated run it is the engine's own test, which is lenient. */
export const PASSES_HEADER: Bi = {
  en: "Passes the engine's tests (lenient for recalibrated runs)",
  es: 'Aprueba las pruebas del motor (indulgentes con las corridas recalibradas)',
};

/** The mark beside a value read from a test that accepts recalibrated runs too easily. */
export const UPPER_BOUND: Bi = { en: 'upper bound', es: 'cota superior' };
