// The notes and reasons the producers and the validation engine write in English only (a plain string, with no Spanish beside it) that
// the views of C10 to C13 print, read in the page's language (U16-R2: b05 B3, B5, B7, b06 B1, B3). Only a text the documents are known to
// carry is translated, whole; any other text is shown as it comes, English is never changed, and a number inside a text is written by
// the shell's formatter, not copied.
import { formatNumber } from '@fasl-work/caos-app-shell';
import { engineNote } from '../c03/U6Shared';
import { dropPlanTags } from '../c14/localise';

type Lang = 'en' | 'es';
type Rule = [RegExp, (m: RegExpMatchArray, lang: Lang) => string];

/** The decimals a number is written with in a text: as many as its English form has. */
const decimalsOf = (s: string) => (s.includes('.') ? s.split('.')[1].length : 0);
const fixed = (s: string, lang: Lang) => formatNumber(Number(s), lang, { decimals: decimalsOf(s) });
const whole = (s: string, lang: Lang) => formatNumber(Number(s), lang, { decimals: 0 });

const LOAN_TYPE: Record<string, string> = { Commercial: 'Comerciales', Residential: 'Residenciales', 'Credit cards': 'Tarjetas de crédito', Other: 'Otros' };

/** The W^2 note of a C12 PIT test: its level, its subject and its horizon code ("10bd", "1m"). */
const W2_NOTE = /^W\^2 is above the simulated (\d+) percent critical value (?:for )?the (book|risk factor) at the (\d+)(bd|m) horizon$/;
// the producer's form since the R3 re-bake: the horizon already in words ("at the horizon of 10 business days")
const W2_NOTE_WORDS = /^W\^2 is above the simulated (\d+) percent critical value for the (book|risk factor) at the horizon of (\d+) (business days?|months?)$/;
const w2Unit = (words: string): string => (words.startsWith('business') ? 'bd' : 'm');

/** A horizon code of C12 ("10bd", "1m", "12m") in words, the singular for one. */
function horizonWords(n: string, unit: string, lang: Lang): string {
  const one = Number(n) === 1;
  if (lang === 'es') return `${n} ${unit === 'bd' ? (one ? 'día hábil' : 'días hábiles') : one ? 'mes' : 'meses'}`;
  return `${n} ${unit === 'bd' ? (one ? 'business day' : 'business days') : one ? 'month' : 'months'}`;
}

/** The English reader sentence of a note that carries a raw id: a plan unit, a horizon code (R3 c12 B2, c13 BL1). */
const EN_RULES: Rule[] = [
  [/^(challenger only: it must enter the \d+ percent MCS on FZ0 out of sample, and )the U\d+ bake( does not train it)$/, (m) => `${m[1]}the precomputation${m[2]}`],
  [W2_NOTE, (m, lang) => `W² is above the simulated ${m[1]} percent critical value for the ${m[2]} at the ${horizonWords(m[3], m[4], lang)} horizon`],
];

const RULES: Rule[] = [
  // C10: the Federal Reserve series, the rungs of the ladder and the granularity recursion
  [/^the asymptotic one-factor contribution is a Gaussian one-factor result; no closed form is specified for this rung$/, () => 'la contribución asintótica de un factor es un resultado gaussiano de un factor; no se especifica una forma cerrada para este escalón'],
  [/^the granularity adjustment is a quantile add-on and defines no expected shortfall$/, () => 'el ajuste por granularidad es un complemento del cuantil y no define un déficit esperado'],
  [/^(\d{4}Q\d(?:, \d{4}Q\d)*): the Board's table marks them n\.a\. for this loan type; never interpolated$/, (m) => `${m[1]}: la tabla de la Junta los marca n.d. para este tipo de crédito; nunca se interpola`],
  [/^the Board's table marks (\d{4}Q\d(?:, \d{4}Q\d)*) as n\.a\. for (.+); the annual rate is null, never interpolated$/, (m) => `la tabla de la Junta marca ${m[1]} como n.d. para ${LOAN_TYPE[m[2]] ?? m[2]}; la tasa anual es nula, nunca se interpola`],
  [/^the exponential twist of dossier (\d+) H\.(\d+) is derived for the normal copula; no Student-t twist is specified, so the rung did not run and no number stands in for it$/, (m) => `la inclinación exponencial del dossier ${m[1]} H.${m[2]} se deriva para la cópula normal; no se especifica una inclinación para la t de Student, de modo que el escalón no corrió y ningún número lo reemplaza`],
  [/^the weight on the systematic factor implied by K \(([\d.]+)\) is outside \(0, 1\]; the recursion was not run$/, (m, lang) => `el peso del factor sistemático implícito en K (${fixed(m[1], lang)}) queda fuera de (0, 1]; no se corrió la recursión`],
  [/^yearly default fractions of a large homogeneous portfolio with one systematic factor \(dossier (\d+) C\.(\d+)\)$/, (m) => `fracciones anuales de incumplimiento de una cartera homogénea grande con un factor sistemático (dossier ${m[1]} C.${m[2]})`],
  // C11: the market back-tests
  [/^expected count ([\d.]+) is small: the power is low \(dossier (\d+) B\.(\d+)\) and the asymptotic size is not the nominal one; read the exact binomial p-value in the metric$/, (m, lang) => `el conteo esperado ${fixed(m[1], lang)} es pequeño: la potencia es baja (dossier ${m[2]} B.${m[3]}) y el tamaño asintótico no es el nominal; lea el valor p binomial exacto en la métrica`],
  [/^not evaluated: an ES forecast is undefined \(NaN\) on at least one day$/, () => 'no evaluada: un pronóstico de ES queda indefinido (NaN) en al menos un día'],
  [/^not evaluated: fewer than (\d+) exceedances: no completed no-hit duration$/, (m, lang) => `no evaluada: menos de ${whole(m[1], lang)} excedencias: no hay una duración completa sin excedencia`],
  [/^not evaluated: no exceedance$/, () => 'no evaluada: sin excedencias'],
  [/^the Weibull shape reached the bound of its search \[([^\]]+)\]: the statistic is capped$/, (m, lang) => `la forma de Weibull llegó al límite de su búsqueda [${m[1].split(', ').map((x) => fixed(x, lang)).join('; ')}]: el estadístico queda acotado`],
  [/^the critical values are simulated per model; (-?[\d.]+) and (-?[\d.]+) are a published reference point, not a threshold$/, (m, lang) => `los valores críticos se simulan por modelo; ${fixed(m[1], lang)} y ${fixed(m[2], lang)} son un punto de referencia publicado, no un umbral`],
  // FZ0 is a score ("el puntaje FZ0"): one gender, as the Model hint writes it (R3 c12 m16)
  [/^the model forecasts no ES: FZ0 is not defined$/, () => 'el modelo no pronostica ES: FZ0 no está definido'],
  [/^the loss differential has no spread: the statistic is undefined$/, () => 'el diferencial de pérdidas no tiene dispersión: el estadístico queda indefinido'],
  // the plan unit of the bake is no reader text (R3 c12 B2)
  [/^challenger only: it must enter the (\d+) percent MCS on FZ0 out of sample, and the U\d+ bake does not train it$/, (m, lang) => `solo retador: debe entrar al MCS de ${whole(m[1], lang)} por ciento sobre FZ0 fuera de muestra, y la precomputación no lo entrena`],
  [/^A component of this portfolio is the Kenneth French equity return, a derived-only source \(dossier (\d+) C\.(\d+)\): only model outputs are committed, so the realised loss series is withheld; the exceedance days and the scores stand\.$/, (m) => `Un componente de esta cartera es el retorno accionario de Kenneth French, una fuente de solo derivados (dossier ${m[1]} C.${m[2]}): solo se versionan las salidas de los modelos, de modo que la serie de pérdida realizada se retiene; los días de excedencia y los puntajes se mantienen.`],
  [/^fewer than (\d+) forecast days \((\d+)\): the Basel traffic light of MAR(\d+\.\d+) is defined on (\d+) observations and the window has no lead-in(?: \(decision D\d+\))?$/, (m, lang) => `menos de ${whole(m[1], lang)} días de pronóstico (${whole(m[2], lang)}): la luz de tráfico de Basilea de MAR${m[3]} se define sobre ${whole(m[4], lang)} observaciones y la ventana no tiene período previo`],
  [/^no eligible model has an ES on every day, so none has an FZ0 score to rank$/, () => 'ningún modelo elegible tiene un ES cada día, de modo que ninguno tiene un puntaje FZ0 que ordenar'],
  // the reasons the C11 producer writes since U16-F10c (c11/documents.py; their Spanish as c11/selection.ts reads them), so a page that reads
  // the documents through these notes (the Experiments page) prints them in Spanish too (R4 c28 B1)
  [/^no model is eligible: every model fails at least one gate$/, () => 'ningún modelo es elegible: cada modelo falla al menos una compuerta'],
  [/^challenger only: it must enter the (\d+) percent MCS on FZ0 out of sample, and the published run does not train it$/, (m, lang) => `solo retador: debe entrar al MCS de ${whole(m[1], lang)} por ciento sobre FZ0 fuera de muestra, y la corrida publicada no lo entrena`],
  [/^fewer than (\d+) forecast days \((\d+)\): the Basel traffic light of MAR(\d+\.\d+) is defined on (\d+) observations and the window has no lead-in$/, (m, lang) => `menos de ${whole(m[1], lang)} días de pronóstico (${whole(m[2], lang)}): la luz de tráfico de Basilea de MAR${m[3]} se define sobre ${whole(m[4], lang)} observaciones y la ventana no tiene período previo`],
  // C12: the counterparty credit risk tests and reconciliations
  [/^BCBS (\d+) paragraph (\d+): exception counts assume independence and the overlapping horizons are not independent$/, (m) => `BCBS ${m[1]} párrafo ${m[2]}: los conteos de excepciones suponen independencia y los horizontes que se traslapan no son independientes`],
  // the horizon in words, never its code ("1m", "10bd"; R3 c13 BL1), and one month in the singular (m4)
  [W2_NOTE, (m, lang) => `W² supera el valor crítico simulado de ${whole(m[1], lang)} por ciento ${m[2] === 'book' ? 'de la cartera' : 'del factor de riesgo'} en el horizonte de ${horizonWords(m[3], m[4], 'es')}`],
  [W2_NOTE_WORDS, (m, lang) => `W² supera el valor crítico simulado de ${whole(m[1], lang)} por ciento ${m[2] === 'book' ? 'de la cartera' : 'del factor de riesgo'} en el horizonte de ${horizonWords(m[3], w2Unit(m[4]), 'es')}`],
  [/^secondary row\. (\d+) exceedances in (\d+) dates against ([\d.]+) expected$/, (m, lang) => `fila secundaria. ${whole(m[1], lang)} excedencias en ${whole(m[2], lang)} fechas frente a ${fixed(m[3], lang)} esperadas`],
  [/^([\d.]+) combined standard errors$/, (m, lang) => `${fixed(m[1], lang)} errores estándar combinados`],
  [/^ORE (\d+) samples against Python (\d+) paths; the profile is the t-forward EE$/, (m, lang) => `ORE con ${whole(m[1], lang)} muestras frente a Python con ${whole(m[2], lang)} trayectorias; el perfil es la EE a plazo t`],
  [/^the largest difference is ([\d.]+) combined standard errors (.+)$/, (m, lang) => `la mayor diferencia es de ${fixed(m[1], lang)} errores estándar combinados; ${noteText(m[2], lang)}`],
  [/^diagnostic: the minimum transfer amount is zero in both engines \((\d+) ORE samples\)$/, (m, lang) => `diagnóstico: el monto mínimo de transferencia es cero en ambos motores (${whole(m[1], lang)} muestras de ORE)`],
  [/^the largest gap is ([\d.]+) combined standard errors; ORE's mean DIM is ([\d.]+) of the Python one on average \(cause UNVERIFIED: the expected exposure after margin agrees, see the EE profile reconciled with ORE\)$/, (m, lang) => `la mayor brecha es de ${fixed(m[1], lang)} errores estándar combinados; el DIM medio de ORE es ${fixed(m[2], lang)} del de Python en promedio (causa NO VERIFICADA: la exposición esperada tras el margen coincide, véase el perfil de EE conciliado con ORE)`],
  // C13: the planted-deficiency replications
  [/^Aggregate over (\d+) replications: the engine row of replication (\d+), the one with the median exception count \((\d+)\); seed (\d+)\.$/, (m, lang) => `Agregado sobre ${whole(m[1], lang)} replicaciones: la fila del motor de la replicación ${m[2]}, la que tiene el conteo mediano de excepciones (${whole(m[3], lang)}); semilla ${m[4]}.`],
  [/^The example replication (\d+) of (\d+), the one with the median Spearman statistic; seed (\d+)\. Statistic is Spearman, metric is KS\.$/, (m, lang) => `La replicación de ejemplo ${m[1]} de ${whole(m[2], lang)}, la que tiene el estadístico de Spearman mediano; semilla ${m[3]}. El estadístico es Spearman, la métrica es KS.`],
];

/** A note or a reason of a document in the language; a text without an entry is returned as it is. */
export function noteText(note: string | null | undefined, lang: Lang): string {
  if (note === null || note === undefined) return '';
  for (const [re, make] of lang === 'en' ? EN_RULES : RULES) {
    const m = note.match(re);
    if (m) return make(m, lang);
  }
  // a plan or decision tag is no reader text in either language (the 2026-10-27 ruling)
  return dropPlanTags(lang === 'en' ? note : engineNote(note, lang));
}

/** The Federal Reserve series of C10 ("C&I loans (column CI of the table)") in the language. */
const SERIES: Record<string, string> = {
  'C&I loans': 'Préstamos comerciales e industriales',
  Commercial: 'Préstamos inmobiliarios comerciales',
  'Credit cards': 'Tarjetas de crédito',
  Other: 'Otros préstamos de consumo',
  Residential: 'Préstamos inmobiliarios residenciales',
};

export function seriesText(series: string, lang: Lang): string {
  const m = series.match(/^(.+) \(column (\w+) of the table\)$/);
  if (!m || lang === 'en' || !SERIES[m[1]]) return series;
  return `${SERIES[m[1]]} (columna ${m[2]} de la tabla)`;
}

/** The seasonal adjustment and the bank scope of the series ("SA", "all-banks"). */
const ADJUSTMENT: Record<string, { en: string; es: string }> = {
  SA: { en: 'seasonally adjusted', es: 'ajustada por estacionalidad' },
  NSA: { en: 'not seasonally adjusted', es: 'sin ajuste estacional' },
  'all-banks': { en: 'all banks', es: 'todos los bancos' },
  'large-banks': { en: 'large banks', es: 'bancos grandes' },
};
export const adjustmentText = (id: string, lang: Lang): string => ADJUSTMENT[id]?.[lang] ?? id;

/** The platform string of an ORE run ("open-source-risk-engine 1.8.17.0 wheel, CPython 3.13, Windows 11 AMD64, native (no WSL); 10000 samples, antithetic"). */
export function platformText(platform: string | null | undefined, lang: Lang): string {
  if (!platform) return '';
  if (lang === 'en') return platform;
  return platform
    // the distribution format in Spanish words, no English "wheel" (R4 c15 C12 B1, U16-F12d)
    .replace(/\bwheel\b/, 'paquete')
    .replace('native (no WSL)', 'nativo (sin WSL)')
    .replace(/(\d+) samples, antithetic/, (_m, n: string) => `${whole(n, lang)} muestras, antitéticas`);
}
