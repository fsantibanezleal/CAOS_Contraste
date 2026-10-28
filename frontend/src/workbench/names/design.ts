// What a finding's `design:<id>` evidence names, in words. Two kinds share the prefix: a design limit (a stated limit of the
// case's data or method, which a finding rests on; most cases) and an outputs block (the block of the outputs the bake computed
// the finding from; C04 and C18). Each name is transcribed from the findings that cite it (the producer of the case) and the
// case page docs/cases/<case>.md; the names of C04's blocks moved here from c04/C04Common.tsx.
import type { Bi as BiText } from '../c03/U6Shared';

/** The design limits, by id. */
export const DESIGN_LIMITS: Record<string, BiText> = {
  // C01 (data-pipeline/pipeline/cases/c01_retail_pd.py)
  'single-snapshot': { en: 'the data is a single snapshot', es: 'los datos son una sola foto' },
  // C02 (data-pipeline/pipeline/cases/c02/findings.py)
  'firm-overlap-unknown': { en: 'the firm overlap across the five files is unknown', es: 'el solapamiento de empresas entre los cinco archivos es desconocido' },
  'no-date': { en: 'the files carry no date, so no out-of-time validation is possible', es: 'los archivos no traen fecha, así que no es posible una validación fuera de tiempo' },
  'paper-reading-unverified': { en: 'the reading of the source paper is not verified', es: 'la lectura del artículo fuente no está verificada' },
  // C03 (data-pipeline/pipeline/cases/c03/)
  'right-censoring': { en: 'loans followed for less than 60 months carry no outcome', es: 'los créditos seguidos menos de 60 meses no tienen resultado' },
  'sba-7a-is-not-a-bank-book': { en: "SBA 7(a) loans are not a bank's SME book", es: 'los créditos SBA 7(a) no son la cartera pyme de un banco' },
  'training-window-before-the-crisis': { en: 'the training window closes before the 2007 to 2009 recession', es: 'la ventana de entrenamiento cierra antes de la recesión de 2007 a 2009' },
  // C05 (data-pipeline/pipeline/cases/c05/)
  'known-truth-coverage': { en: 'the coverage of the bounds against the known truth', es: 'la cobertura de las cotas frente a la verdad conocida' },
  'known-truth-power': { en: 'the power of the battery against the known truth', es: 'la potencia de la batería frente a la verdad conocida' },
  'known-truth-size': { en: 'the size of the tests against the known truth, with correlated defaults', es: 'el tamaño de las pruebas frente a la verdad conocida, con incumplimientos correlacionados' },
  'pluto-tasche-deviations': { en: "the cells where Pluto and Tasche's tables deviate from their exact values", es: 'las celdas en que las tablas de Pluto y Tasche se apartan de sus valores exactos' },
  'pluto-tasche-section-5': { en: 'Pluto and Tasche, section 5: the expert PDs against the most prudent calibration', es: 'Pluto y Tasche, sección 5: las PD expertas contra la calibración más prudente' },
  'prophetic-pd': { en: "the forecast year's observed default rate used as the PD, as the paper does", es: 'la tasa de incumplimiento observada del año pronosticado usada como PD, como hace el artículo' },
  'tasche-2013-section-4.2.2': { en: 'Tasche (2013), section 4.2.2: the survivor profile approximated by the forecast profile', es: 'Tasche (2013), sección 4.2.2: el perfil de sobrevivientes aproximado por el perfil pronosticado' },
  'tasche-2013-table-8': { en: "Tasche (2013), Table 8: the case 3 approaches without the year's default rate", es: 'Tasche (2013), Tabla 8: los enfoques del caso 3 sin la tasa de incumplimiento del año' },
  // C06 (data-pipeline/pipeline/cases/c06/)
  'backtest-population': { en: 'the lifetime backtest covers only accounts with at least 33 months of contractual life left', es: 'la prueba retrospectiva de vida cubre solo cuentas con al menos 33 meses de vida contractual por delante' },
  'prepayment-as-censoring': { en: 'prepayment is treated as censoring', es: 'el prepago se trata como censura' },
  'sba-chargeoff-lgd-proxy': { en: 'the LGD is a charge-off severity proxy, before the SBA guarantee', es: 'la LGD es una aproximación de la severidad del castigo, antes de la garantía de la SBA' },
  'sba-modelled-balance': { en: 'the balance is modelled: the file has none', es: 'el saldo es modelado: el archivo no lo trae' },
  'sba-no-delinquency-data': { en: 'the SBA file has no delinquency, forbearance or watch-list history', es: 'el archivo de la SBA no trae historial de morosidad, reestructuración ni lista de vigilancia' },
  // C07 (data-pipeline/pipeline/cases/c07/)
  'b1-minimum-normal-individual': { en: 'the 0.50% minimum on the individually assessed normal portfolio', es: 'el mínimo de 0,50 % sobre la cartera normal evaluada individualmente' },
  // C09 (data-pipeline/pipeline/cases/c09/documents.py)
  'undrawn-not-positive-is-undefined': { en: 'a defaulter with no undrawn amount has no CCF', es: 'un deudor incumplido sin monto no girado no tiene CCF' },
  // C10 (data-pipeline/pipeline/cases/c10/documents.py)
  'copula-ladder': { en: 'the copula ladder on one correlation: Gaussian, Student t and CreditRisk+', es: 'la escalera de cópulas sobre una misma correlación: gaussiana, t de Student y CreditRisk+' },
  'granularity-adjustment': { en: 'the granularity adjustment of a finite portfolio', es: 'el ajuste por granularidad de una cartera finita' },
  'irb-reference-block': { en: "the IRB reference: the fitted asset correlation against the IRB's", es: 'la referencia IRB: la correlación de activos ajustada contra la del IRB' },
  // C14 (data-pipeline/pipeline/cases/c14/)
  'retail-share-is-a-synthetic-mapping': { en: 'the retail and wholesale split and the core shares are synthetic', es: 'la división entre minorista y mayorista y las partes estables son sintéticas' },
  // C15 (data-pipeline/pipeline/cases/c15/variant.py)
  // the three tests of riskvalidation.irrbb.eve_nii.prioritised_bank, as the Thresholds view lists them (R4 c18 m11)
  'annex1-prioritised-bank-tests': { en: 'the CMF Annex 1 prioritisation tests: delta EVE against 15 percent of Tier 1 capital, delta NII against 5 percent of Tier 1 capital and against 18 percent of the 12-month net interest and indexation margin', es: 'las pruebas de priorización del Anexo 1 de la CMF: delta EVE contra el 15 por ciento del capital de nivel 1, delta NII contra el 5 por ciento del capital de nivel 1 y contra el 18 por ciento del margen de intereses y reajustabilidad de 12 meses' },
  'clp-curve-fourth-point': { en: "the pesos curve's fourth point is the monetary policy rate", es: 'el cuarto punto de la curva en pesos es la tasa de política monetaria' },
  'indexation-charge-is-a-standard-add-on': { en: 'the standard indexation charge depends on the net UF position, not on the rate shock', es: 'el cargo estándar por reajustabilidad depende de la posición neta en UF, no del choque de tasas' },
  // C17 (data-pipeline/pipeline/cases/c17/documents.py)
  'infinite-mean': { en: 'the severity has an infinite mean', es: 'la severidad tiene media infinita' },
  'sma-not-calibrated-to-the-999-quantile': { en: 'the SMA is not calibrated to the 99.9 percent quantile', es: 'el SMA no está calibrado al cuantil del 99,9 por ciento' },
  // C18 (data-pipeline/pipeline/cases/c18/)
  // the committed losses carry no IRRBB loss (losses.scenario_losses[*].irrbb = 0) while its marginal has an expected loss: IRRBB is out
  // of the capital path, not held at its expected loss (R4 c22 M1, c23 M2)
  'non-credit-losses-at-expected-loss': { en: 'market and operational losses are held at their expected loss; IRRBB stays out of the capital path', es: 'las pérdidas de mercado y operacional se fijan en su pérdida esperada; el IRRBB queda fuera de la trayectoria de capital' },
  // C20 (data-pipeline/pipeline/cases/c20/)
  'fed-no-outcome': { en: 'the Fed portfolios carry no default outcome and no decision', es: 'las carteras de la Fed no traen incumplimientos ni decisiones' },
  'fixed-rounds': { en: 'the boosting rounds are fixed on the first fit', es: 'las rondas de potenciación se fijan en el primer ajuste' },
  'holdout-not-out-of-time': { en: 'Taiwan has no out-of-time sample: the locked holdout stands in for it', es: 'Taiwán no tiene muestra fuera de tiempo: la muestra reservada la reemplaza' },
  'noise-on-codes': { en: 'the noise is added to every feature, the coded ones included', es: 'el ruido se agrega a cada variable, incluidas las codificadas' },
  'planted-not-found': { en: 'the leak is planted, so the screen catches it by construction', es: 'la fuga es plantada, así que el filtro la detecta por construcción' },
  'rungs-swept': { en: 'only the two boosted-tree rungs are swept', es: 'solo se recorren los dos peldaños de árboles potenciados' },
  'sgcd-not-for-scoring': { en: 'SGCD is a research benchmark, not for credit scoring', es: 'SGCD es un referente de investigación, no para calificar crédito' },
  // no count here: the finding's title states the span from the document's rows (R6 c26 B1: "30 to 90" beside a row of 27)
  'small-groups': { en: 'each shock row holds few records, so its AUC carries a wide interval', es: 'cada fila de choque tiene pocos registros, así que su AUC tiene un intervalo amplio' },
  'synthetic-shift': { en: 'the shift is synthetic, of a known size', es: 'el cambio es sintético, de tamaño conocido' },
  'xgboost-float32': { en: 'XGBoost computes in single precision', es: 'XGBoost calcula en precisión simple' },
  // C21 (data-pipeline/pipeline/cases/c21/)
  'complete-case-selection': { en: 'the controlled fits use the complete cases', es: 'los ajustes controlados usan los casos completos' },
  'credit-score-missing': { en: 'the credit score is not in public HMDA', es: 'el puntaje de crédito no está en el HMDA público' },
};

/** The outputs blocks a finding is computed from, by id, and the group that draws each (C04; C18's capital plan and CET1 path). */
export const OUTPUT_BLOCKS: Record<string, BiText> = {
  definition_gap: { en: 'the definition gaps, pooled D4/D2 and D3/D2 by grade (Validation group)', es: 'las brechas de definición, D4/D2 y D3/D2 agrupadas por grado (grupo Validación)' },
  'cohorts.defaulted_cohort': { en: "the default-rate page's own cohort against the transition page's, year by year (Validation group)", es: 'la cohorte propia de la página de tasas de incumplimiento contra la de la página de transiciones, año a año (grupo Validación)' },
  'cohorts.counts': { en: "the transition page's counts by year, its default column (Validation group)", es: 'los conteos de la página de transiciones por año, su columna de incumplimiento (grupo Validación)' },
  embedding: { en: "the embedding diagnostics: Israel et al.'s Theorem 3 and stochastic monotonicity (Model group)", es: 'los diagnósticos de inclusión: el Teorema 3 de Israel et al. y la monotonía estocástica (grupo Modelo)' },
  generators: { en: "the generators' L1 distances to the pooled matrix (Model group)", es: 'las distancias L1 de los generadores a la matriz agrupada (grupo Modelo)' },
  lra: { en: 'the long-run averages and their Jeffreys intervals (Validation group)', es: 'los promedios de largo plazo y sus intervalos de Jeffreys (grupo Validación)' },
  pd: { en: 'the one-year PDs by cohort and grade (Validation group)', es: 'las PD anuales por cohorte y grado (grupo Validación)' },
  lifetime: { en: 'the five-year windows: observed against the chained one-year matrices (Validation group)', es: 'las ventanas de cinco años: lo observado contra las matrices anuales encadenadas (grupo Validación)' },
  ttc: { en: "the pooled matrix's TTC portfolio and the drift towards it (Impact group)", es: 'la cartera TTC de la matriz agrupada y la deriva hacia ella (grupo Impacto)' },
  'rungs.estimators': { en: "the estimators' bias and RMSE by grade (Validation group)", es: 'el sesgo y el RMSE de los estimadores por grado (grupo Validación)' },
  'rungs.estimators.zero': { en: 'the share of exactly zero PDs by estimator and grade (Validation group)', es: 'la proporción de PD exactamente cero por estimador y grado (grupo Validación)' },
  'rungs.coverage': { en: "the intervals' coverage by grade (Validation group)", es: 'la cobertura de los intervalos por grado (grupo Validación)' },
  'rungs.error_cohort_power': { en: "the Markov projections' errors against the five-year default frequency (Validation group)", es: 'los errores de las proyecciones de Markov contra la frecuencia de incumplimiento a cinco años (grupo Validación)' },
  'rungs.pd_stressed_year': { en: "the stressed year's PD against the truth (Validation group)", es: 'la PD del año estresado contra la verdad (grupo Validación)' },
  'rungs.pd_removed': { en: 'the PD with withdrawals removed against the truth (Validation group)', es: 'la PD con los retiros eliminados contra la verdad (grupo Validación)' },
  'rungs.pd_followed': { en: 'the PD with withdrawals followed (EBA paragraph 76) against the truth (Validation group)', es: 'la PD con los retiros seguidos (párrafo 76 de la EBA) contra la verdad (grupo Validación)' },
  'rungs.overlap_jeffreys': { en: "adjacent grades' Jeffreys overlap by cohort size (Validation group)", es: 'el traslape de Jeffreys de grados adyacentes por tamaño de cohorte (grupo Validación)' },
  irw: { en: "Israel et al.'s nine distances, printed against recomputed (Validation group)", es: 'las nueve distancias de Israel et al., impresas contra recalculadas (grupo Validación)' },
  sr190: { en: "Schuermann and Hanson's Table 5, printed against recomputed (Validation group)", es: 'la Tabla 5 de Schuermann y Hanson, impresa contra recalculada (grupo Validación)' },
  engelmann: { en: "Engelmann's TTC portfolio and projections, printed against recomputed (Validation group)", es: 'la cartera TTC y las proyecciones de Engelmann, impresas contra recalculadas (grupo Validación)' },
  // C18 (data-pipeline/pipeline/cases/c18/): the capital plan and the CET1 path of the scenario
  'outputs.capital_plan': { en: "the scenario's capital plan: the PE ratio against the internal target (Capital group)", es: 'el plan de capital del escenario: la razón de PE contra la meta interna (grupo Capital)' },
  // C15 (U16-F12d, R4 c18 n2): the floors block a finding cites since the re-bake
  'floors.distances': { en: 'the distance of each leg and shock to its post-shock floor (Floors view)', es: 'la distancia de cada tramo y choque a su piso posterior al choque (vista de pisos)' },
  'outputs.headline_cet1': { en: "the scenario's CET1 path on losses only (Capital group)", es: 'la trayectoria del CET1 del escenario solo con pérdidas (grupo Capital)' },
};
