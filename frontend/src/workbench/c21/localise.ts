// The Spanish of the English-only strings of the C21 bake (U16-R2, b10 B2): the note of a test, the rule of the four-fifths line, the
// label, unit and population of an estimate, the interval and the distance normalisation of the situation test, the licence sentences. A
// quotation of a law stays as the source writes it (it is marked lang="en" where it is printed). A string without a rule is printed as
// it is; r2.test.tsx renders every view on every committed document in Spanish and fails on an English word left.
import { localise, type Rule } from '../c14/localise';
import { CONTROL_TEXT, GROUP_TEXT, text } from './selection';

const controls = (ids: string): string => ids.split(', ').map((c) => text(CONTROL_TEXT, c).es).join(', ');

const R: ReadonlyArray<Rule> = [
  [/^the four-fifths line is an employment benchmark \((29 CFR [\d.]+\(D\)) \(the four-fifths rule of the Uniform Guidelines on Employee Selection Procedures\)\), compared with the highest-rate group and never a credit-law threshold; decided on the exact counts; no legal claim$/,
    (g) => `la línea de las cuatro quintas partes es una referencia del empleo (${g[1]} (la regla de las cuatro quintas partes de las Pautas Uniformes sobre Procedimientos de Selección de Empleados)), comparada con el grupo de mayor tasa y nunca un umbral del derecho del crédito; decidida sobre los conteos exactos; sin afirmación legal`],
  [/^an approximation of comparative evidence controlling for (.+); missing controls: (.+), so the estimate may be confounded by them; never a finding of a violation; no legal claim$/,
    (g) => `una aproximación de evidencia comparativa que controla por ${controls(g[1])}; controles faltantes: ${controls(g[2])}, así que la estimación puede estar confundida por ellos; nunca un hallazgo de infracción; sin afirmación legal`],
  [/^indicator of statistical parity against '(.+)'; the tolerance is a convention, never a regulatory threshold; no legal claim$/,
    (g) => `indicador de paridad estadística contra «${text(GROUP_TEXT, g[1]).es}»; la tolerancia es una convención, nunca un umbral regulatorio; sin afirmación legal`],
  [/^the rate difference is group 1 minus group 2; smaller differences can matter when statistically significant; no legal claim$/,
    () => 'la diferencia de tasas es el grupo 1 menos el grupo 2; diferencias menores pueden importar cuando son estadísticamente significativas; sin afirmación legal'],
  [/^replication by sign and size only, no verdict beyond them; no legal claim$/, () => 'replicación solo por signo y tamaño, sin veredicto más allá de ellos; sin afirmación legal'],
  [/^individual-level indicator over the complainants of the protected group, centers excluded; the cut point is a convention, never a regulatory threshold, and sits in extras\.thresholds, not in the p-value alphas; never red; no legal claim$/,
    () => 'indicador a nivel individual sobre los denunciantes del grupo protegido, centros excluidos; el punto de corte es una convención, nunca un umbral regulatorio, y está en extras.thresholds, no en los alfa del valor p; nunca rojo; sin afirmación legal'],
  [/^approximation of comparative evidence$/, () => 'aproximación de evidencia comparativa'],
  // the unit names the field in words, never its code (the raw-id scan of 2026-10-24)
  [/^percentage points of rate_spread$/, () => 'puntos porcentuales de diferencial de tasa'],
  [/^odds ratio$/, () => 'razón de odds'],
  [/^action_taken 1 or 2$/, () => 'action_taken 1 o 2'],
  [/^flag when 5 \* x_g \* n_h < 4 \* x_h \* n_g$/, () => 'marcar cuando 5 * x_g * n_h < 4 * x_h * n_g'],
  [/^flag when 5 x_g n_h < 4 x_h n_g, exact counts$/, () => 'marcar cuando 5 x_g n_h < 4 x_h n_g, conteos exactos'],
  [/^employment benchmark$/, () => 'referencia del empleo'],
  [/^one-sided Wald, equation \(10\) of arXiv 2502\.01267$/, () => 'Wald de una cola, ecuación (10) de arXiv 2502.01267'],
  [/^range$/, () => 'rango'],
  [/^not applicable \(age is a prohibited basis under ECOA only, not in 42 U\.S\.C\. 3605\(a\)\)$/, () => 'no aplicable (la edad es una base prohibida solo bajo la ECOA, no en 42 U.S.C. 3605(a))'],
  [/^not assessed \(disparate impact under the FHA only; gross HMDA disparities are not appropriate for disproportionate adverse impact analysis, Interagency Procedures appendix, printed page 26\)$/,
    () => 'no evaluado (el impacto dispar solo bajo la FHA; las disparidades brutas de HMDA no son apropiadas para el análisis de impacto adverso desproporcionado, apéndice de los Procedimientos Interagenciales, página impresa 26)'],
  [/^unmodified$/, () => 'sin modificar'],
  [/^top-coded$/, () => 'con tope superior'],
  [/^The publicly available data are modified to protect applicants' and borrowers' privacy$/, () => 'Los datos públicos se modifican para proteger la privacidad de solicitantes y prestatarios'],
  [/^As a work of the United States Government, this package \(excluding any exceptions listed below\) is in the public domain within the United States\. Additionally, we waive copyright and related rights in the work worldwide through the CC0 1\.0 Universal public domain dedication\.$/,
    () => 'Como obra del Gobierno de Estados Unidos, este paquete (salvo las excepciones listadas abajo) es de dominio público dentro de Estados Unidos. Además, renunciamos a los derechos de autor y derechos conexos sobre la obra en todo el mundo mediante la dedicación de dominio público CC0 1.0 Universal.'],
  [/^the software package, not the published datasets$/, () => 'el paquete de software, no los conjuntos de datos publicados'],
  [/^Interagency Fair Lending Examination Procedures, August 2009, appendix, printed page 26$/, () => 'Procedimientos Interagenciales de Examen de Préstamos Justos, agosto de 2009, apéndice, página impresa 26'],
];

/** The Spanish of a document string, or the string itself in English or when no rule knows it. */
export const es = (s: string | null | undefined, lang: 'en' | 'es'): string => localise(s, lang, R);

const TREATMENT_TEXT: Record<string, { en: string; es: string }> = {
  unmodified: { en: 'unmodified', es: 'sin modificar' },
  'top-coded': { en: 'top-coded', es: 'con tope superior' },
  binned: { en: 'binned', es: 'agrupado' },
  rounded: { en: 'rounded', es: 'redondeado' },
  'not-applicable': { en: 'not applicable', es: 'no aplicable' },
};

/** The treatment the public data apply to a field, in words. */
export const treatmentName = (treatment: string, lang: 'en' | 'es'): string => TREATMENT_TEXT[treatment]?.[lang] ?? treatment;
