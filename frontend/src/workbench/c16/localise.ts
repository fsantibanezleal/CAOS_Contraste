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
