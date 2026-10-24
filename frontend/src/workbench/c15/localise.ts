// The Spanish of the English-only strings of the C15 bake (U16-R2, b07 V15-1, V15-3 and V15-5), written through the rules of
// c14/localise.ts: the calibration source, the assumption sources, the attribution of a curve, the UF source, and the two formulas
// (their words are translated, their symbols stay: ruling of the main session, 2026-10-22).
import { IRRBB_SOURCE_RULES, dec, type Rule } from '../c14/localise';

export const C15_SOURCE_RULES: ReadonlyArray<Rule> = [
  ...IRRBB_SOURCE_RULES,
  [/^CMF, Informe del Desempeno del Sistema Bancario y Cooperativas, agosto 2026 \(published ([\d-]+)\), Cuadro N 1 column Bancos, (\S+), sha256 (\w+); the three loan portfolios are the C07 targets; securities, deposits, equity and loans to banks are the other figures of the same table; scaled to the C07 total exposure; the UF shares, profiles, deposit split and behaviour are synthetic$/,
    (g) => `CMF, Informe del Desempeño del Sistema Bancario y Cooperativas, agosto 2026 (publicado el ${g[1]}), Cuadro N° 1 columna Bancos, ${g[2]}, sha256 ${g[3]}; las tres carteras de crédito son las metas de C07; los valores, los depósitos, el patrimonio y los préstamos a bancos son las otras cifras de la misma tabla; escalado a la exposición total de C07; las proporciones en UF, los perfiles, la separación de depósitos y el comportamiento son sintéticos`],
  [/^Stated by Contraste \(synthetic\): one pass-through of the short rate to the rate paid on non-maturity deposits, used by the dynamic NII\. No deposit-rate history exists for a synthetic bank, so no beta is fitted\.$/,
    () => 'Declarado por Contraste (sintético): un único traspaso de la tasa corta a la tasa pagada sobre los depósitos sin vencimiento, usado por el NII dinámico. No existe historial de tasas de depósitos para un banco sintético, así que no se ajusta ningún beta.'],
  [/^Stated by Contraste \(synthetic\): the CMF aggregates carry no prepayment history\. The residential mortgage items carry the prepayable-loan class; the SRP31\.119 multipliers are tabled in the models document and, as in C14, not applied per shock \(the definition of the outstanding notional of SRP31\.121 is UNVERIFIED in the engine contract\)\.$/,
    () => 'Declarado por Contraste (sintético): los agregados de la CMF no traen historial de prepago. Las partidas hipotecarias residenciales llevan la clase de préstamo prepagable; los multiplicadores de SRP31.119 están tabulados en el documento de modelos y, como en C14, no se aplican por choque (la definición del nocional vigente de SRP31.121 está SIN VERIFICAR en el contrato del motor).'],
  [/^Stated by Contraste \(synthetic\): the baseline early-redemption rate TDRR0 of SRP31\.125, scaled by the Table 6 multiplier of each shock through the engine's term-deposit redemption function\.$/,
    () => 'Declarado por Contraste (sintético): la tasa base de rescate anticipado TDRR0 de SRP31.125, escalada por el multiplicador de la Tabla 6 de cada choque mediante la función de rescate de depósitos a plazo del motor.'],
  [/^request stated by Contraste \(synthetic\); the used value is min\(request, SRP31 Table 4 cap\)$/,
    () => 'solicitud declarada por Contraste (sintética); el valor usado es min(solicitud, tope de la Tabla 4 de SRP31)'],
  [/^Source: Banco Central de Chile \(BDE\), series ([A-Z0-9., ]+)\. The fitted zero curve is an adaptation by Contraste of the Banco Central de Chile's data and is its sole responsibility \(BCCh terms\)\.$/,
    (g) => `Fuente: Banco Central de Chile (BDE), series ${g[1]}. La curva cero ajustada es una adaptación de Contraste de los datos del Banco Central de Chile y es de su exclusiva responsabilidad (términos del BCCh).`],
  [/^Banco Central de Chile, BDE series F073\.UFF\.PRE\.Z\.D \(Unidad de fomento\), value of ([\d-]+)$/,
    (g) => `Banco Central de Chile, serie BDE F073.UFF.PRE.Z.D (Unidad de fomento), valor del ${g[1]}`],
];

/** The formulas of the indexation charge and of the CPI scenario: the words in Spanish, the symbols as written. */
export const FORMULA_RULES: ReadonlyArray<Rule> = [
  [/^charge = ([\d.]+) x \|PN_UR\|, PN_UR = net UF position x UF value$/, (g) => `cargo = ${dec(g[1])} x |PN_UR|, PN_UR = posición neta en UF x valor de la UF`],
  [/^effect = -pn_ur x surprise_pp \/ 100 \(loss-positive\)$/, () => 'efecto = -pn_ur x surprise_pp / 100 (pérdida positiva)'],
];
