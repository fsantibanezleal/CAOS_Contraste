// The Spanish of the English-only strings the IRRBB bakes carry (U16-R2, b07 V14-3 and V15-5): a source line, an interpolation
// note, the slotting assumption of an item, a test note. The strings are written by the pipeline and the engine in English only; a
// Spanish view prints them through `localise`, which maps a whole string by a rule (an exact text or a pattern with its numbers) and
// leaves a string no rule knows as it is. A test (r2.test.tsx) renders every view on every committed document in Spanish and fails on
// an English word left, so a new string without a rule is found before a reader finds it. Verbatim citations (a URL, the name of a
// dataset, a regulation) are kept as they are.
export type Lang = 'en' | 'es';
/** A rule: the whole English string, and the Spanish written from its groups (numbers keep the Spanish decimal comma). */
export type Rule = readonly [RegExp, (g: string[]) => string];

/** An English decimal as the Spanish form: 0.0236 becomes 0,0236. */
export const dec = (s: string): string => s.replace('.', ',');

/** The Spanish of `s`, or `s` itself in English or when no rule knows it. */
export function localise(s: string | null | undefined, lang: Lang, rules: ReadonlyArray<Rule>): string {
  if (s === null || s === undefined || lang === 'en') return s ?? '';
  for (const [pattern, write] of rules) {
    const m = pattern.exec(s);
    if (m) return write([...m]);
  }
  return s;
}

/** The notes the IRRBB tests carry. */
export const TEST_NOTE_RULES: ReadonlyArray<Rule> = [
  [/^(\d+) change\(s\) coincide with a breach$/, (g) => `${g[1]} ${g[1] === '1' ? 'cambio coincide' : 'cambios coinciden'} con un exceso`],
  [/^not evaluated: fewer than 2 dates$/, () => 'no evaluada: menos de 2 fechas'],
  [/^not evaluated: the realised change in NII is not available$/, () => 'no evaluada: el cambio realizado del NII no está disponible'],
];

/** The assumptions, curve and slotting lines of the C14 and C15 documents. */
export const IRRBB_SOURCE_RULES: ReadonlyArray<Rule> = [
  [/^US Treasury daily par yield curve \(Daily Treasury Par Yield Curve Rates\), observation date (\S+?)(?:; carried to (\S+), the last curve published on or before it)?$/,
    (g) => `Curva de rendimientos par diaria del Tesoro de EE. UU. (Daily Treasury Par Yield Curve Rates), fecha de observación ${g[1]}${g[2] ? `; trasladada al ${g[2]}, la última curva publicada en esa fecha o antes` : ''}`],
  [/^par yields bootstrapped to continuously compounded zero rates \(the engine's zero-curve bootstrap, semiannual bond-equivalent, simple interest up to six months\); linear in tenor and flat outside the grid at the 19 midpoints$/,
    () => 'rendimientos par convertidos por bootstrap en tasas cero de capitalización continua (bootstrap de la curva cero del motor, equivalente de bono semestral, interés simple hasta seis meses); lineal en el plazo y plana fuera de la grilla en los 19 puntos medios'],
  [/^balance-weighted average of the used values of the deposit categories below \(the SRP31 Table 4 caps applied to the synthetic requests\)$/,
    () => 'promedio ponderado por saldo de los valores usados de las categorías de depósitos de abajo (los topes de la Tabla 4 de SRP31 aplicados a las solicitudes sintéticas)'],
  [/^balance-weighted average of the used values of the deposit categories below$/, () => 'promedio ponderado por saldo de los valores usados de las categorías de depósitos de abajo'],
  [/^Stated by Contraste \(synthetic\): the call report has no loan-level prepayment history\. Applied to the amortising mortgage items \(residential loans repricing beyond three months, mortgage-backed securities\) in the behavioural flows; the SRP31\.119 multipliers are tabled in the models document, not applied per shock\.$/,
    () => 'Declarado por Contraste (sintético): el reporte no trae historial de prepago a nivel de préstamo. Se aplica a las partidas hipotecarias amortizables (préstamos residenciales que reprecian después de tres meses, títulos respaldados por hipotecas) en los flujos conductuales; los multiplicadores de SRP31.119 están tabulados en el documento de modelos y no se aplican por choque.'],
  [/^Stated by Contraste \(synthetic\): the baseline early-redemption rate TDRR0 of SRP31\.125, scaled by the Table 6 multiplier of each shock\.$/,
    () => 'Declarado por Contraste (sintético): la tasa base de rescate anticipado TDRR0 de SRP31.125, escalada por el multiplicador de la Tabla 6 de cada choque.'],
  [/^Fitted per valuation date on the quarterly cost of deposits \(deposit interest expense over average deposits\) against the 3-month Treasury par yield, last 16 quarters up to the date, slope through the origin on the quarters with a rising market rate \(up\) and a falling one \(down\)\. (?:Up ([\d.]+) on (\d+) quarters, down ([\d.]+) on (\d+); the dynamic NII uses the up value|(\d+) quarters up, (\d+) down\. One series \(the bank's cost of deposits\) stands for all non-maturity deposits and is filed under the dominant category)\.$/,
    (g) => 'Ajustado por fecha de valoración sobre el costo trimestral de los depósitos (gasto en intereses de depósitos sobre depósitos promedio) contra el rendimiento par a 3 meses del Tesoro, últimos 16 trimestres hasta la fecha, pendiente por el origen sobre los trimestres con tasa de mercado al alza (alza) y a la baja (baja). '
      + (g[1] !== undefined
        ? `Alza ${dec(g[1])} en ${g[2]} trimestres, baja ${dec(g[3])} en ${g[4]}; el NII dinámico usa el valor al alza.`
        : `${g[5]} trimestres al alza, ${g[6]} a la baja. Una sola serie (el costo de depósitos del banco) representa a todos los depósitos sin vencimiento y se ordena bajo la categoría dominante.`)],
  [/^Request stated by Contraste \(synthetic\); the call report carries no behavioural assumption\. Used value: the SRP31 Table 4 cap when the request exceeds it\.$/,
    () => 'Solicitud declarada por Contraste (sintética); el reporte no trae ningún supuesto conductual. Valor usado: el tope de la Tabla 4 de SRP31 cuando la solicitud lo excede.'],
  // the slotting assumption of an item
  [/^overnight bucket$/, () => 'tramo a la vista'],
  [/^not interest-sensitive: overnight bucket at par$/, () => 'no sensible a tasas: tramo a la vista a la par'],
  [/^uniform spread of the report bands over the buckets they overlap$/, () => 'reparto uniforme de las bandas del reporte entre los tramos que cubren'],
  [/^amortising linearly over the remaining maturity band; behavioural flows prepay at the base CPR of ([\d.]+) a year$/,
    (g) => `amortización lineal sobre la banda de plazo restante; los flujos conductuales se prepagan al CPR base de ${dec(g[1])} al año`],
  [/^behavioural: non-core overnight, core around the used maturity \(nmd_split, SRP31 Table 4 caps\); contractual: overnight$/,
    () => 'conductual: la parte no estable a la vista y la estable en torno al plazo usado (nmd_split, topes de la Tabla 4 de SRP31); contractual: a la vista'],
  [/^non-mortgage debt at its maturity band, mortgage-backed securities amortising linearly over their remaining maturity band; behavioural flows prepay the mortgage-backed part at the base CPR of ([\d.]+) a year; split pro rata to the (held-to-maturity|available-for-sale) share$/,
    (g) => `deuda no hipotecaria en su banda de plazo, títulos respaldados por hipotecas con amortización lineal sobre su banda de plazo restante; los flujos conductuales prepagan la parte hipotecaria al CPR base de ${dec(g[1])} al año; reparto proporcional a la parte ${g[2] === 'held-to-maturity' ? 'mantenida hasta el vencimiento' : 'disponible para la venta'}`],
  // the reference of the outlier test
  [/^SRP31\.82 to SRP31\.83 \(15 percent of Tier 1\)$/, () => 'SRP31.82 a SRP31.83 (15 por ciento del capital de nivel 1)'],
];

/** The references the IRRBB tests carry when a test has no note of its own (the cell then shows its source, in Spanish). */
export const TEST_REFERENCE_RULES: ReadonlyArray<Rule> = [
  [/^BCBS SRP31\.90 to SRP31\.92, Interest rate risk in the banking book, the six standardised shock scenarios and the worked example at t = 3\.5 years \(dossier 01 H\.2\), (https:\/\/\S+)$/,
    (g) => `BCBS SRP31.90 a SRP31.92, riesgo de tasa de interés en el libro de banca, los seis escenarios de choque estandarizados y el ejemplo resuelto a t = 3,5 años (dossier 01 H.2), ${g[1]}`],
  [/^BCBS SRP31\.82 to SRP31\.83 and SRP31\.129: the EVE supervisory outlier test \(15 percent of Tier 1\) and the standardised EVE; dossier 05 D\.7: always report EVE with and without behavioural assumptions$/,
    () => 'BCBS SRP31.82 a SRP31.83 y SRP31.129: la prueba supervisora de valores atípicos del EVE (15 por ciento del capital de nivel 1) y el EVE estandarizado; dossier 05 D.7: informar siempre el EVE con y sin supuestos conductuales'],
  [/^BCBS d368 \(2016\), Standards: Interest rate risk in the banking book, (https:\/\/\S+); dossier 05 D\.3 \(weight stability across estimation windows\)$/,
    (g) => `BCBS d368 (2016), Normas: riesgo de tasa de interés en el libro de banca, ${g[1]}; dossier 05 D.3 (estabilidad de los pesos entre ventanas de estimación)`],
  [/^dossier 05, IRRBB acceptance: the 2022 hiking cycle as the out-of-sample test of an NII projection$/,
    () => 'dossier 05, aceptación del IRRBB: el ciclo de alzas de 2022 como prueba fuera de muestra de una proyección del NII'],
  [/^CMF Recopilaci(?:o)n Actualizada de Normas, cap(?:i)tulo 21-13, Anexo 1 \(Hoja 9 to Hoja 12\): CLP and UR shock sizes, the 50 percent offset, the 2\.5 percent indexation charge \(dossier 03 F\.2\), (https:\/\/\S+)$/,
    (g) => `CMF Recopilación Actualizada de Normas, capítulo 21-13, Anexo 1 (Hoja 9 a Hoja 12): tamaños de los choques en CLP y UR, la compensación de 50 por ciento, el cargo de 2,5 por ciento por reajustabilidad (dossier 03 F.2), ${g[1]}`],
];
