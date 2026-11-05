// The sources of the case manifests by name in the reader's language (U16-F10p, the third capture review R3 c23 B4). A
// manifest names each source in English (`source_details[id].name`, from data/sources/manifest.json); the Spanish page writes
// the description and the locator (section, table) in Spanish and keeps a published title as its authors wrote it. A source
// this table does not hold prints its manifest name, the same in both languages.

const ES: Record<string, string> = {
  'uci-taiwan': 'Default of Credit Card Clients (Taiwán), del repositorio UCI',
  'uci-german': 'Statlog (German Credit Data), del repositorio UCI',
  'uci-polish': 'Polish Companies Bankruptcy, del repositorio UCI',
  'sba-foia': 'datos de préstamos 7(a) y 504 de la SBA, publicados por FOIA',
  'esma-cerep': 'CEREP de la ESMA (el registro central de calificaciones)',
  'israel-rosenthal-wei-2001': 'Finding generators for Markov chains via empirical transition matrices, with applications to credit ratings (versión de los autores), sección 4',
  'engelmann-2024': 'Spurious default probability projections in credit risk stress testing models (arXiv 2401.08892v1), sección 4',
  'schuermann-hanson-2004': 'Estimating probabilities of default (FRBNY Staff Report 190), tabla 5',
  'tasche-2013': 'The art of probability-of-default curve calibration (arXiv 1212.3716v6), tablas 2 a 9',
  'pluto-tasche-2005': 'Estimating probabilities of default for low default portfolios (arXiv cond-mat/0411699v3), tablas 1 a 14',
  'fed-stress-tests': 'escenarios y datos de metodología de las pruebas de estrés supervisoras de la Reserva Federal (2025, 2026)',
  'fed-chargeoff': 'tasas de castigo y de mora de la Reserva Federal',
  'french-data-library': 'la biblioteca de datos de Kenneth R. French',
  'treasury-par-curve': 'la curva diaria de rendimientos a la par del Tesoro de Estados Unidos',
  'fred-public-domain': 'FRED, series de dominio público (H.15, H.8, H.10)',
  'treasury-hqm': 'la curva de rendimientos de bonos corporativos de alta calidad (HQM) del Tesoro de Estados Unidos, tasas al contado de fin de mes',
  'fdic-bankfind': 'BankFind Suite de la FDIC (quiebras, estados financieros)',
  'bcch-bde': 'la Base de Datos Estadísticos (BDE) del Banco Central de Chile y su interfaz de programación',
  'fed-h8': 'H.8 de la Reserva Federal (activos y pasivos de los bancos comerciales)',
  'fed-svb-review': 'la revisión de la Reserva Federal sobre la supervisión y regulación de Silicon Valley Bank',
  'eba-esrb-stress-2025': 'el escenario de la prueba de estrés de la UE de 2025, de la EBA y la JERS',
  'ngfs-phase-v': 'los escenarios climáticos de la NGFS, fase V',
  'santanderai-sgcd': 'Stressed German Credit Dataset (SGCD-v0.1)',
  hmda: 'los datos de la Home Mortgage Disclosure Act (ley de divulgación de hipotecas de Estados Unidos)',
  'bcbs-wp14': 'Studies on the Validation of Internal Rating Systems (revised), Working Paper 14, tablas 5 a 8 (la simulación de las pruebas normal y de semáforo)',
  'yurdakul-naranjo-2020': 'Statistical properties of the population stability index, tabla 4 (las tasas de rechazo de las reglas del PSI y de la referencia chi-cuadrado)',
};

/** The name of source `id` in `lang`: the manifest's English name `en`, or its Spanish name on the Spanish page. */
export function sourceText(id: string, en: string, lang: 'en' | 'es'): string {
  return lang === 'es' ? (ES[id] ?? en) : en;
}
