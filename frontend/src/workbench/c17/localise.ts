// The Spanish of the English-only strings of the C17 bake (U16-R2, b08 V17-1): the reason a value is absent, the note of a test,
// the reference of a rung, the title of the LDCE report. A string without a rule is printed as it is; r2.test.tsx renders every view
// on every committed document in Spanish and fails on an English word, so a new string is found before a reader finds it. The names of
// papers and journals stay as published; the connecting words of a citation ("and") are Spanish.
import { localise, type Rule } from '../c14/localise';

const R: ReadonlyArray<Rule> = [
  [/^the tail index is 1 or more: the severity has an infinite mean and the mean correction lambda x E\[X\] does not exist$/,
    () => 'el índice de cola es 1 o más: la severidad tiene media infinita y la corrección por la media lambda x E[X] no existe'],
  [/^the tail index is 1 or more: the severity has an infinite mean, so the annual loss has no mean$/,
    () => 'el índice de cola es 1 o más: la severidad tiene media infinita, así que la pérdida anual no tiene media'],
  [/^descriptive: a Contraste internal gate on the relative deviations, no p-value$/, () => 'descriptivo: un umbral interno de Contraste sobre las desviaciones relativas, sin valor p'],
  [/^descriptive: dispersion \(p75 - p25\) \/ truth and bias median \/ truth - 1, no p-value$/, () => 'descriptivo: dispersión (p75 - p25) / verdad y sesgo mediana / verdad - 1, sin valor p'],
  [/^descriptive: the ILM jump after one added loss, no p-value$/, () => 'descriptivo: el salto del ILM tras sumar una pérdida, sin valor p'],
  [/^descriptive: the largest absolute influence of one scenario point, no p-value$/, () => 'descriptivo: la mayor influencia absoluta de un punto de escenario, sin valor p'],
  [/^descriptive: the range of the fitted tail index, no p-value$/, () => 'descriptivo: el rango del índice de cola ajustado, sin valor p'],
  [/^Results from the 2008 Loss Data Collection Exercise for Operational Risk$/, () => 'Resultados del Ejercicio de Recolección de Datos de Pérdidas de 2008 para Riesgo Operacional'],
  [/^dossier 05 F\.2, rung (\d)(?:; Mignola and Ugoccioni \((\d{4})\))?$/, (g) => `dossier 05 F.2, peldaño ${g[1]}${g[2] ? `; Mignola y Ugoccioni (${g[2]})` : ''}`],
  [/^dossier 05 F\.4, Shevchenko eq\. (\d+)$/, (g) => `dossier 05 F.4, Shevchenko ec. ${g[1]}`],
  [/^dossier 05 F\.4: the form is not checked against Bocker and Sprittulla \((\d{4})\) or Degen \((\d{4})\)$/, (g) => `dossier 05 F.4: la forma no se ha verificado contra Bocker y Sprittulla (${g[1]}) ni Degen (${g[2]})`],
  [/^dossier 05 F\.5, Shevchenko and Wuthrich \((\d{4})\)$/, (g) => `dossier 05 F.5, Shevchenko y Wuthrich (${g[1]})`],
  [/^dossier 05 F\.5; Shevchenko and Wuthrich \((\d{4})\), (.*)$/, (g) => `dossier 05 F.5; Shevchenko y Wuthrich (${g[1]}), ${g[2]}`],
  [/^Shevchenko and Wuthrich \((\d{4})\), (.*)$/, (g) => `Shevchenko y Wuthrich (${g[1]}), ${g[2]}`],
  [/^dossier 01 section F \(OPE25, in force (\S+), published (\S+)\)$/, (g) => `dossier 01 sección F (OPE25, vigente desde ${g[1]}, publicado el ${g[2]})`],
  [/^OPE25\.7 footnote 2$/, () => 'OPE25.7 nota 2'],
];

/** The Spanish of a document string, or the string itself in English or when no rule knows it. */
export const es = (s: string | null | undefined, lang: 'en' | 'es'): string => localise(s, lang, R);
