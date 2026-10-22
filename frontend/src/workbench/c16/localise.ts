// The Spanish of the English-only strings of the C16 bake (U16-R2, b08 V16-1), by exact text: a convention unit, the assumption of a
// balance-sheet item, a source line, an LCR paragraph, a test note. A string without an entry is printed as it is, and the test
// r2.test.tsx renders every view on every committed document in Spanish and fails on an English word or a slug left. The ids of the
// documents (a variant, a source, a class of deposits) are named by the maps below, never printed as ids.
import { localise, type Rule } from '../c14/localise';

type Map = Record<string, string>;

const exact = (m: Map): ReadonlyArray<Rule> => Object.entries(m).map(([en, es]) => [new RegExp(`^${en.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}$`), () => es] as const);

const TEXT: Map = {
  // the unit of a convention
  'share, added to and taken from each haircut': 'parte, sumada y restada a cada recorte',
  'share of total assets': 'parte de los activos totales',
  'Monte Carlo standard errors': 'errores estándar de Monte Carlo',
  'multiple of the reported HTM unrealised loss': 'múltiplo de la pérdida HTM no realizada informada',
  'share of the reported unrealised loss': 'parte de la pérdida no realizada informada',
  'share, absolute': 'parte, absoluta',
  'USD thousands': 'miles de USD',
  'multiple of the daily rates': 'múltiplo de las tasas diarias',
  'modelled over realised cumulative outflow': 'salida acumulada modelada sobre la realizada',
  'share of domestic deposits': 'parte de los depósitos domésticos',
  'share': 'parte',
  'days': 'días',
  // the assumption of a balance-sheet item
  'Foreign-office deposits mapped to non-operational other financial customers, synthetic behaviour.': 'Depósitos en oficinas extranjeras asignados a otros clientes financieros no operacionales, comportamiento sintético.',
  'Reported at amortised cost; fair value from SCHF.': 'Informado a costo amortizado; valor razonable de SCHF.',
  'Reported at fair value.': 'Informado a valor razonable.',
  'Reported by the FDIC financials, taken as reserves at nominal value (Level 1).': 'Informado en los estados financieros de la FDIC, tomado como reservas a valor nominal (Nivel 1).',
  'Reported estimate; mapped to non-operational non-financial corporates.': 'Estimación informada; asignada a corporativos no financieros no operacionales.',
  'Reported; a liability (addendum L3.1).': 'Informado; un pasivo (adenda L3.1).',
  'Reported; an asset (addendum L3.1); assumed overnight, synthetic behaviour.': 'Informado; un activo (adenda L3.1); supuesto a la vista, comportamiento sintético.',
  'Reported; its maturity bands feed the ladder.': 'Informado; sus bandas de vencimiento alimentan la escalera.',
  'Reported; mapped to other retail sight deposits.': 'Informado; asignado a otros depósitos minoristas a la vista.',
  'Reported; not counted in the CBC.': 'Informado; no se cuenta en el CBC.',
  'Reported.': 'Informado.',
  'Residual liabilities, synthetic aggregation.': 'Pasivos residuales, agregación sintética.',
  'Total assets less the listed asset items, synthetic aggregation.': 'Activos totales menos las partidas de activo listadas, agregación sintética.',
  // the sources and the parameter sets
  'ECB LiST 2019 methodological note, Tables 3.2 and 3.3, Adverse': 'Nota metodológica LiST 2019 del BCE, Tablas 3.2 y 3.3, Adverso',
  'ECB LiST 2019 methodological note, Tables 3.2 and 3.3, Extreme': 'Nota metodológica LiST 2019 del BCE, Tablas 3.2 y 3.3, Extremo',
  'calibrated on the pre-2023 Table A.1 rows by the calibration rule': 'calibrado con las filas de la Tabla A.1 anteriores a 2023 por la regla de calibración',
  'riskvalidation.regulatory.lcr_nsfr (BCBS LCR20, LCR30, LCR40, LCR99, in force 2019-12-15)': 'riskvalidation.regulatory.lcr_nsfr (BCBS LCR20, LCR30, LCR40, LCR99, vigentes desde 2019-12-15)',
  // the LCR paragraphs
  'LCR99 retail less stable deposits': 'LCR99 depósitos minoristas menos estables',
  'LCR99 non-financial corporates, sovereigns, central banks, MDBs, PSEs': 'LCR99 corporativos no financieros, soberanos, bancos centrales, BMD y entidades del sector público',
  'LCR99 other legal entity customers (for example financial institutions)': 'LCR99 otras personas jurídicas (por ejemplo, instituciones financieras)',
  'LCR40 all other secured funding': 'LCR40 todo otro financiamiento garantizado',
  'LCR99 other collateral': 'LCR99 otras garantías',
  'LCR99 retail and non-financial wholesale inflows': 'LCR99 entradas minoristas y mayoristas no financieras',
  // the revaluation of the held-to-maturity book
  'US Treasury par yield curve of 2022-12-30 priced against the par curve of 2021-12-31 (a par bond per maturity band of the securities book, the profile applied to the held-to-maturity amortised cost)':
    'curva de rendimientos par del Tesoro de EE. UU. del 2022-12-30 valorada contra la curva par del 2021-12-31 (un bono a la par por banda de vencimiento del libro de valores, el perfil aplicado al costo amortizado mantenido al vencimiento)',
  // the notes of the tests
  'not evaluated: the horizon of 5 days is shorter than far = 35': 'no evaluada: el horizonte de 5 días es menor que lejos = 35',
  'not evaluated: the solve was refused, so there is no multiplier to round trip': 'no evaluada: la solución fue rechazada, así que no hay multiplicador para el viaje de ida y vuelta',
  // the reference of a test with no note of its own (U16-R2 b06 m3 and b07 m1: the cell shows it)
  // liq.list_compounding_golden
  "dossier 05 E.1 line 237 (constant daily compounding on relevant days, Table 3.3 and para 107 of the LiST note) and the SDD acceptance row of the unit sizing; ECB Banking Supervision, Sensitivity analysis of liquidity risk, stress test 2019, methodological note (2019-02-06) and results annex (2019-10-07), https://www.bankingsupervision.europa.eu/":
    "dossier 05 E.1 línea 237 (capitalización diaria constante sobre los días relevantes, Tabla 3.3 y párrafo 107 de la nota de LiST) y la fila de aceptación del SDD del dimensionamiento de la unidad; Supervisión Bancaria del BCE, Análisis de sensibilidad del riesgo de liquidez, prueba de estrés 2019, nota metodológica (2019-02-06) y anexo de resultados (2019-10-07), https://www.bankingsupervision.europa.eu/",
  // liq.cbc_haircut_rules
  "dossier 05 E.1 line 238 and line 480 (LiST note para 74, Table 2.1: the haircut order, the equity table, 30 and 50 percent); ECB Banking Supervision, Sensitivity analysis of liquidity risk, stress test 2019, methodological note (2019-02-06) and results annex (2019-10-07), https://www.bankingsupervision.europa.eu/":
    "dossier 05 E.1 línea 238 y línea 480 (nota de LiST párrafo 74, Tabla 2.1: el orden de los recortes, la tabla de acciones, 30 y 50 por ciento); Supervisión Bancaria del BCE, Análisis de sensibilidad del riesgo de liquidez, prueba de estrés 2019, nota metodológica (2019-02-06) y anexo de resultados (2019-10-07), https://www.bankingsupervision.europa.eu/",
  // liq.runoff_adequacy_back_test
  "dossier 08 lines 566 to 568 and dossier 06 lines 971 to 973: a Basel outflow assumption back-tested against the observed run rate (BCBS d555 Box A, Table A.1, https://www.bis.org/bcbs/publ/d555.htm); a descriptive score on the real event, one observation, no p-value (decision Q5)":
    "dossier 08 líneas 566 a 568 y dossier 06 líneas 971 a 973: un supuesto de salidas de Basilea contrastado con la tasa de salida observada (BCBS d555 Recuadro A, Tabla A.1, https://www.bis.org/bcbs/publ/d555.htm); una puntuación descriptiva sobre el evento real, una observación, sin valor p (decisión Q5)",
  // liq.nlp_identity
  "dossier 05 E.1 line 234: NLP(t) = CBC(t) - sum over s <= t of (O(s) - I(s)), checked on hand-computed ladders":
    "dossier 05 E.1 línea 234: NLP(t) = CBC(t) - suma sobre s <= t de (O(s) - I(s)), verificada en escaleras calculadas a mano",
  // liq.runoff_vs_generator_truth
  "dossier 08 line 698 and G.4 lines 739 to 742: the run-off estimate against the depositor generator's exact truth, in Monte Carlo standard errors (the generator test of decision Q5)":
    "dossier 08 línea 698 y G.4 líneas 739 a 742: la estimación de salidas contra la verdad exacta del generador de depositantes, en errores estándar de Monte Carlo (la prueba del generador de la decisión Q5)",
  // liq.cliff_effect_diagnostic
  "dossier 05 E.1 line 236 defines the cliff effect (NLP(35) - NLP(30)) / TA as a diagnostic of LCR window optimisation and no limit, so the lights are conventions (decision Q14); ECB Banking Supervision, Sensitivity analysis of liquidity risk, stress test 2019, methodological note (2019-02-06) and results annex (2019-10-07), https://www.bankingsupervision.europa.eu/":
    "dossier 05 E.1 línea 236 define el efecto acantilado (NLP(35) - NLP(30)) / TA como un diagnóstico de la optimización de la ventana del LCR y no como un límite, así que las luces son convenciones (decisión Q14); Supervisión Bancaria del BCE, Análisis de sensibilidad del riesgo de liquidez, prueba de estrés 2019, nota metodológica (2019-02-06) y anexo de resultados (2019-10-07), https://www.bankingsupervision.europa.eu/",
  // liq.htm_loss_effect
  "dossier 05 lines 263, 278 and 480: the CBC and the survival period with and without held-to-maturity unrealised losses (Jiang, Matvos, Piskorski and Seru, doi:10.1016/j.jfineco.2024.103899)":
    "dossier 05 líneas 263, 278 y 480: el CBC y el periodo de supervivencia con y sin pérdidas no realizadas de los valores mantenidos al vencimiento (Jiang, Matvos, Piskorski y Seru, doi:10.1016/j.jfineco.2024.103899)",
  // liq.htm_revaluation_vs_reported
  "dossier 05 line 263 and decision Q11: the HTM book revalued from its maturity profile under the Treasury curve through the engine's irrbb curves against the reported fair value SCHF (FDIC BankFind fields, addendum L3)":
    "dossier 05 línea 263 y decisión Q11: la cartera HTM revalorada desde su perfil de vencimientos bajo la curva del Tesoro mediante las curvas irrbb del motor contra el valor razonable informado SCHF (campos de FDIC BankFind, anexo L3)",
  // liq.uninsured_share_sensitivity
  "dossier 05 line 278: the survival period does not lengthen as the uninsured share of deposits rises":
    "dossier 05 línea 278: el periodo de supervivencia no se alarga cuando sube la parte no asegurada de los depósitos",
  // liq.survival_monotone_in_severity
  "dossier 05 E.1 line 240 (median survival periods 176 and 122 days) and line 480, SDD line 329: the survival period does not lengthen as the severity rises; ECB Banking Supervision, Sensitivity analysis of liquidity risk, stress test 2019, methodological note (2019-02-06) and results annex (2019-10-07), https://www.bankingsupervision.europa.eu/":
    "dossier 05 E.1 línea 240 (periodos de supervivencia medianos de 176 y 122 días) y línea 480, SDD línea 329: el periodo de supervivencia no se alarga cuando sube la severidad; Supervisión Bancaria del BCE, Análisis de sensibilidad del riesgo de liquidez, prueba de estrés 2019, nota metodológica (2019-02-06) y anexo de resultados (2019-10-07), https://www.bankingsupervision.europa.eu/",
  // liq.reverse_stress_round_trip
  "dossier 05 E.5 rung 5, line 279: the reverse liquidity stress round trip (the survival period at the solved multiplier equals the target)":
    "dossier 05 E.5 peldaño 5, línea 279: el viaje de ida y vuelta de la prueba de estrés de liquidez inversa (el periodo de supervivencia en el multiplicador resuelto es igual al objetivo)",
};

/** The names of the documents' ids, in words. */
export const NAME_TEXT: Record<string, { en: string; es: string }> = {
  'lcr-standard': { en: 'LCR standard run-off', es: 'LCR con salidas estándar' },
  'list-adverse': { en: 'LiST adverse', es: 'LiST adverso' },
  'list-extreme': { en: 'LiST extreme', es: 'LiST extremo' },
  'fast-run': { en: '2023 fast run', es: 'Corrida rápida 2023' },
  'htm-losses': { en: 'HTM losses', es: 'Pérdidas HTM' },
  'maximum-implied-daily-rate': { en: 'maximum implied daily rate', es: 'mayor tasa diaria implícita' },
  'relevant-days': { en: 'relevant days', es: 'días relevantes' },
  'lcr-30-day': { en: '30-day LCR', es: 'LCR a 30 días' },
  'basel-lcr': { en: 'Basel LCR', es: 'LCR de Basilea' },
  'fdic-bankfind': { en: 'FDIC BankFind', es: 'FDIC BankFind' },
  'fed-h8': { en: 'Federal Reserve H.8', es: 'H.8 de la Reserva Federal' },
  'fed-svb-review': { en: 'Federal Reserve review of SVB', es: 'Revisión de SVB de la Reserva Federal' },
  'bcbs-d555-table-a1': { en: 'BCBS d555 Table A.1', es: 'BCBS d555 Tabla A.1' },
  'ecb-list-2019': { en: 'ECB LiST 2019', es: 'LiST 2019 del BCE' },
  'open-repos': { en: 'Open repos', es: 'Repos abiertos' },
  'stable-retail': { en: 'Stable retail', es: 'Minorista estable' },
  'other-retail': { en: 'Other retail', es: 'Otro minorista' },
  operational: { en: 'Operational', es: 'Operacional' },
  'non-operational-credit-institutions': { en: 'Non-operational, credit institutions', es: 'No operacional, instituciones de crédito' },
  'non-operational-other-financial': { en: 'Non-operational, other financial', es: 'No operacional, otros financieros' },
  'non-operational-non-financial-corporates': { en: 'Non-operational, non-financial corporates', es: 'No operacional, corporativos no financieros' },
  'non-operational-others': { en: 'Non-operational, others', es: 'No operacional, otros' },
  'other-transactions': { en: 'Other transactions', es: 'Otras transacciones' },
  'held-to-maturity': { en: 'held to maturity', es: 'mantenidos al vencimiento' },
  'non-financial': { en: 'non-financial', es: 'no financiero' },
  'derived-only': { en: 'derived only', es: 'solo derivado' },
  'limited-extract': { en: 'limited extract', es: 'extracto limitado' },
  'public-domain': { en: 'public domain', es: 'dominio público' },
  'roll-off': { en: 'roll-off', es: 'salida' },
};

export const C16_RULES: ReadonlyArray<Rule> = exact(TEXT);

/** The Spanish of a document string, or the string itself in English or when no entry knows it. */
export const es = (s: string | null | undefined, lang: 'en' | 'es'): string => localise(s, lang, C16_RULES);

/** The name of an id in the language; an id without a name keeps its text. */
export const nameOf = (id: string, lang: 'en' | 'es'): string => NAME_TEXT[id]?.[lang] ?? id;

/** The name of the bank: the document gives the English only. */
export const bankName = (name: string, lang: 'en' | 'es'): string => {
  if (lang === 'en') return name;
  const m = /^(.*), failed ([\d-]+)$/.exec(name);
  return m ? `${m[1]}, quebró el ${m[2]}` : name;
};
