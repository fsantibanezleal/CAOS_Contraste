// The sections of the cross-case pages for the cases of wave 2 batch 2: C10 (portfolio credit capital), C11 (market VaR and
// ES back-tests), C13 (FRTB desk eligibility), C14 and C15 (IRRBB) and C17 (operational risk). Experiments reads one
// headline row per variant in the case's own measures; Benchmark compares the case in its own terms (C14 and C15 have no
// champion-against-challenger comparison and are excluded on the Benchmark page, with the reason). Every number is read
// from the committed variant artifacts when the page opens, none is typed in, and a value the artifact leaves null says
// "not available" with the reason the document gives (T13). The tables are built by pure functions of the artifacts so
// that the tests read them from the contract fixtures.
import { formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import type { BiText } from '@fasl-work/caos-app-shell';
import type { CaseManifest, VariantArtifact } from '../lib/contract.types';
import { P, useT } from '../content/bi';
import { Loading, Table, money, num, pct, useVariants } from './U6Sections';
import { DEFICIENCY_TEXT, INTENDED_TEXT, type C13Outputs } from '../workbench/c13/selection';
import { SHOCK_TEXT as C14_SHOCK_TEXT, scenarioOf, type C14Outputs } from '../workbench/c14/selection';
import { SHOCK_TEXT as C15_SHOCK_TEXT, type C15Outputs, type C15Pair } from '../workbench/c15/selection';
import { AGGREGATION_TEXT, RUNG_ORDER, STATUS_TEXT, capitalOf, cellLabel, cellOf, rungName, type C17Outputs } from '../workbench/c17/selection';
import { DIRECTION_TEXT, ZONE_TEXT, alphaShort, text as c11Text, type C11Outputs } from '../workbench/c11/selection';
import { ESTIMATOR_KIND_TEXT, ESTIMATOR_SHORT, METHOD_TEXT, estimatorOf, levelLabel, measureOf, text as c10Text, type C10GridOutputs, type C10Outputs } from '../workbench/c10/selection';

type Lang = 'en' | 'es';
type Cell = string;
type Variant = VariantArtifact<unknown>;

/** A table of a case, already in the language of the reader: the pure result of the artifacts. */
export interface W2Table {
  key: string;
  title?: string;
  head: string[];
  rows: Cell[][];
  /** The number of left-aligned text columns (the first by default). */
  wide?: number;
  note?: string;
}

/** The cases this file renders on Experiments. */
export const W2_CASES = new Set(['C10', 'C11', 'C13', 'C14', 'C15', 'C17']);
/** The cases with a comparison in their own terms for the Benchmark (C14 and C15 are excluded there, with a reason). */
export const W2_BENCHMARK_CASES = new Set(['C10', 'C11', 'C13', 'C17']);

/** The level of the C10 headline: the 99.9 percent capital of the Basel IRB formula and of the rungs. */
const C10_LEVEL_FOCUS = 0.999;

/** What a value the artifact leaves out reads like: "not available", and the reason when the document gives one. */
const na = (lang: Lang, reason?: string | null): string => `${formatNumber(null, lang)}${reason ? ` (${reason})` : ''}`;
const bi = (t: BiText | undefined, lang: Lang, fallback = ''): string => (t ? pick(t, lang) : fallback);
const join = (parts: string[]): string => parts.join('; ');
/** A value between two bounds: "0.0030 (0.0025 to 0.0036)". */
const within = (v: string, lo: string, hi: string, lang: Lang): string => `${v} (${lo} ${lang === 'es' ? 'a' : 'to'} ${hi})`;
const factor = (u: { money_scale: string }): number => (u.money_scale === 'millions' ? 1e6 : u.money_scale === 'thousands' ? 1e3 : 1);
/** An amount of a document with a money scale (C14 thousands, C15 millions): scaled to units, then to bn or m. */
const scaled = (v: number | null | undefined, u: { money_scale: string }, currency: string, lang: Lang) => money(v === null || v === undefined ? null : v * factor(u), currency, lang);
const titles = (manifest: CaseManifest, lang: Lang): Record<string, string> =>
  Object.fromEntries(manifest.artifacts.filter((a) => a.role === 'variant').map((a) => [a.variant_id, pick(a.short_title ?? a.title, lang)]));
const kindOf = (v: Variant): string | undefined => (v.outputs as { kind?: string } | undefined)?.kind;
const modelTitle = (v: Variant, id: string, lang: Lang): string => {
  const m = v.model.find((x) => x.id === id);
  return m ? pick(m.title, lang) : id;
};

// ---------------------------------------------------------------------------------------------------- Experiments

function c10LoanRow(name: string, v: Variant, lang: Lang): Cell[] {
  const o = v.outputs as C10Outputs;
  const ml = o.fit.maximum_likelihood;
  const e = o.windows.evaluation;
  const exceed = join(o.backtest.rows.map((r) => `${levelLabel(r.level, lang)}: ${formatNumber(r.observed_exceedances, lang)}`));
  const years = lang === 'es' ? `de ${o.backtest.n_years_evaluated} años (${e.first_year} a ${e.last_year})` : `of ${o.backtest.n_years_evaluated} years (${e.first_year} to ${e.last_year})`;
  const capital = (method: string): string => {
    const r = o.rungs.find((x) => x.method === method);
    const m = measureOf(r, C10_LEVEL_FOCUS);
    return r && r.evaluated && m ? money(m.ec, r.currency, lang) : na(lang, r?.reason ?? (lang === 'es' ? 'el peldaño no corrió' : 'the rung did not run'));
  };
  return [
    name,
    within(pct(ml.pd.estimate, lang), pct(ml.pd.ci_low, lang), pct(ml.pd.ci_high, lang), lang),
    within(num(ml.rho.estimate, lang), num(ml.rho.ci_low, lang), num(ml.rho.ci_high, lang), lang),
    `${exceed} ${years}`,
    capital('gaussian-copula-one-factor'),
    capital('lhp-vasicek'),
  ];
}

function c10GridRow(name: string, v: Variant, lang: Lang): Cell[] {
  const o = v.outputs as C10GridOutputs;
  const sizeCell = o.cells.find((c) => c.known_rho === o.generator.null_rho) ?? o.cells.find((c) => c.role === 'size');
  const power = o.cells.filter((c) => c.role === 'power');
  const size = (est: string) => {
    const e = estimatorOf(sizeCell, est);
    return e ? pct(e.rejection_rate, lang, 1) : na(lang, lang === 'es' ? 'la grilla no tiene celda de tamaño' : 'the grid has no size cell');
  };
  const pow = (est: string) => {
    const rates = power.map((c) => estimatorOf(c, est)?.rejection_rate).filter((x): x is number => typeof x === 'number');
    return rates.length ? `${pct(Math.min(...rates), lang, 1)} ${lang === 'es' ? 'a' : 'to'} ${pct(Math.max(...rates), lang, 1)}` : na(lang, lang === 'es' ? 'la grilla no tiene celdas de potencia' : 'the grid has no power cells');
  };
  return [name, `${o.cells.map((c) => num(c.known_rho, lang, 2)).join(', ')} (${lang === 'es' ? 'nula' : 'null'}: ${num(o.generator.null_rho, lang, 2)})`, size('maximum-likelihood'), size('moments'), pow('maximum-likelihood'), pow('moments')];
}

function c11Row(name: string, v: Variant, lang: Lang): Cell[] {
  const o = v.outputs as C11Outputs;
  const per = (f: (alpha: number) => string): string => join(o.levels.map((l) => `${bi(alphaShort(l.alpha), lang)}: ${f(l.alpha)}`));
  const champ = (alpha: number) => o.comparison.champions.find((c) => c.alpha === alpha);
  const level = (alpha: number) => {
    const id = champ(alpha)?.model_id;
    return id ? o.models.find((m) => m.model_id === id)?.by_level.find((l) => l.alpha === alpha) : undefined;
  };
  return [
    name,
    per((a) => {
      const c = champ(a);
      return c?.model_id ? modelTitle(v, c.model_id, lang) : na(lang, c?.reason);
    }),
    per((a) => {
      const l = level(a);
      if (!l) return na(lang, champ(a)?.reason);
      return l.traffic_light ? bi(c11Text(ZONE_TEXT, l.traffic_light.final_zone), lang) : na(lang, lang === 'es' ? 'el semáforo de Basilea se define solo para el VaR al 99%' : 'the Basel traffic light is defined for the 99% VaR only');
    }),
    per((a) => {
      const l = level(a);
      return l ? (l.fz0_mean === null || l.fz0_mean === undefined ? na(lang, l.fz0_reason) : num(l.fz0_mean, lang, 3)) : na(lang, champ(a)?.reason);
    }),
    per((a) => {
      const m = o.comparison.mcs.find((x) => x.alpha === a && x.loss === 'fz0');
      return m ? `${formatNumber(m.n_in_set, lang)} ${lang === 'es' ? 'de' : 'of'} ${formatNumber(m.members.length, lang)}` : na(lang, lang === 'es' ? 'sin conjunto de confianza' : 'no confidence set');
    }),
  ];
}

function c13Row(name: string, v: Variant, lang: Lang): Cell[] {
  const o = v.outputs as C13Outputs;
  const d = o.detection;
  const z = o.pla.zones.overall;
  const caught = within(pct(d.share_amber_or_red, lang, 1), pct(d.ci_low, lang, 1), pct(d.ci_high, lang, 1), lang);
  return [
    name,
    bi(DEFICIENCY_TEXT[o.known_deficiency.deficiency_id] ?? { en: o.known_deficiency.deficiency_id, es: o.known_deficiency.deficiency_id }, lang),
    d.role === 'size' ? `${caught} ${lang === 'es' ? '(falsas alarmas)' : '(false alarms)'}` : caught,
    lang === 'es'
      ? `verde ${formatNumber(z.green, lang)}, ámbar ${formatNumber(z.amber, lang)}, rojo ${formatNumber(z.red, lang)} de ${formatNumber(o.pla.zones.n, lang)}`
      : `green ${formatNumber(z.green, lang)}, amber ${formatNumber(z.amber, lang)}, red ${formatNumber(z.red, lang)} of ${formatNumber(o.pla.zones.n, lang)}`,
  ];
}

/** The outlier test of IRRBB as a cell: the delta over Tier 1 capital against its limit. */
function outlier(ratio: number | null | undefined, threshold: number | null | undefined, breached: boolean | undefined, lang: Lang): string {
  if (ratio === null || ratio === undefined) return na(lang);
  const verdict = breached ? (lang === 'es' ? 'supera' : 'above') : lang === 'es' ? 'dentro de' : 'within';
  return lang === 'es' ? `${pct(ratio, lang, 1)} del capital de nivel 1 (${verdict} el límite de ${pct(threshold, lang, 0)})` : `${pct(ratio, lang, 1)} of Tier 1 (${verdict} the ${pct(threshold, lang, 0)} limit)`;
}

function c14Row(name: string, v: Variant, lang: Lang): Cell[] {
  const o = v.outputs as C14Outputs;
  const reason = lang === 'es' ? 'el documento no contiene este escenario' : 'the document holds no such scenario';
  const largest = (nmd: string) => {
    const s = scenarioOf(o, '2024', nmd);
    if (!s) return na(lang, reason);
    const w = s.worst_shock;
    return `${scaled(s.eve_risk_measure, o.units, o.currency, lang)}${w ? ` (${bi(C14_SHOCK_TEXT[w] ?? { en: w, es: w }, lang)})` : ''}`;
  };
  const test = (nmd: string) => {
    const s = scenarioOf(o, '2024', nmd);
    return s ? outlier(s.outlier.ratio, s.outlier.threshold_share_tier1, s.outlier.breached, lang) : na(lang, reason);
  };
  return [name, largest('behavioural'), largest('contractual'), test('behavioural'), test('contractual')];
}

/** The largest of the six pair totals of a leg-pair table, and the shock where it falls (null when no shock loses). */
function largestPair<T extends { shock: string; pair: C15Pair }>(rows: T[], field: 'with_offset' | 'without_offset'): { value: number; shock: string | null } {
  let best: { value: number; shock: string | null } = { value: 0, shock: null };
  for (const r of rows) if (r.pair[field] > best.value) best = { value: r.pair[field], shock: r.shock };
  return best;
}

function c15Row(name: string, v: Variant, lang: Lang): Cell[] {
  const o = v.outputs as C15Outputs;
  const shock = (s: string | null) => (s ? ` (${bi(C15_SHOCK_TEXT[s] ?? { en: s, es: s }, lang)})` : '');
  const eve = (field: 'with_offset' | 'without_offset') => {
    const b = largestPair(o.eve.rows, field);
    return `${scaled(b.value, o.units, o.reporting_currency, lang)}${shock(b.shock)}`;
  };
  const t = (id: string) => o.thresholds.tests.find((x) => x.id === id);
  const eveTest = t('eve-tier1');
  const niiTest = t('nii-tier1');
  return [
    name,
    eve('with_offset'),
    eve('without_offset'),
    eveTest ? outlier(eveTest.ratio, eveTest.threshold, eveTest.breached, lang) : na(lang),
    `${scaled(o.nii.delta_nii, o.units, o.reporting_currency, lang)} (${lang === 'es' ? 'con el cargo por reajustabilidad de' : 'with the indexation charge of'} ${scaled(o.nii.indexation_charge, o.units, o.reporting_currency, lang)})`,
    niiTest ? outlier(niiTest.ratio, niiTest.threshold, niiTest.breached, lang) : na(lang),
  ];
}

/** The grid cell the headline of C17 reads: 10 years of losses at the collection threshold of OPE25.18, as the App opens. */
const C17_YEARS = 10;
const C17_THRESHOLD = 20000;

function c17Row(name: string, v: Variant, lang: Lang): Cell[] {
  const o = v.outputs as C17Outputs;
  const cell = cellOf(o, C17_YEARS, C17_THRESHOLD);
  const q = o.truth.annual_loss_quantile;
  const { summary, reason } = capitalOf(cell, 'lda-splice');
  const sma = o.sma_response.rows.find((r) => r.added_loss_eur === 0) ?? o.sma_response.rows[0];
  return [
    name,
    num(o.tail_index, lang, 2),
    q ? money(q.value_eur, o.currency, lang) : na(lang),
    summary ? num(summary.ratio_to_truth.median, lang, 2) : na(lang, reason),
    summary ? num(summary.iqr_over_truth, lang, 2) : na(lang, reason),
    sma ? money(sma.orc_eur, o.currency, lang) : na(lang),
  ];
}

const T = (lang: Lang) => (en: string, es: string) => (lang === 'es' ? es : en);

/** The Experiments tables of a case: one row per variant, in the order the variants are given (the manifest's). */
export function wave2ExperimentTables(manifest: CaseManifest, vs: Variant[], lang: Lang): W2Table[] {
  const t = T(lang);
  const name = titles(manifest, lang);
  const nameOf = (v: Variant) => name[v.variant_id] ?? v.variant_id;
  const id = manifest.case_id;
  if (id === 'C10') {
    const loan = vs.filter((v) => kindOf(v) === 'loan-type');
    const grid = vs.filter((v) => kindOf(v) === 'correlation-grid');
    const out: W2Table[] = [];
    if (loan.length)
      out.push({
        key: 'loan-type',
        head: [t('Loan type', 'Tipo de crédito'), t('Fitted PD (95% interval)', 'PD ajustada (intervalo 95%)'), t('Fitted correlation (95% interval)', 'Correlación ajustada (intervalo 95%)'), t('Exceedances in the evaluation years', 'Excedencias en los años de evaluación'), t('99.9% capital, C2 Monte Carlo', 'Capital al 99,9%, C2 Monte Carlo'), t('99.9% capital, LHP (C1)', 'Capital al 99,9%, LHP (C1)')],
        rows: loan.map((v) => c10LoanRow(nameOf(v), v, lang)),
        note: t(
          'The fit reads the yearly loss rates up to 2006 by maximum likelihood; the exceedances count the years from 2007 to 2012 in which the loss rate went over the fitted quantile of each level; the capital is the economic capital of the illustrative portfolio, in the currency shown.',
          'El ajuste lee las tasas de pérdida anuales hasta 2006 por máxima verosimilitud; las excedencias cuentan los años de 2007 a 2012 en que la tasa de pérdida superó el cuantil ajustado de cada nivel; el capital es el capital económico de la cartera ilustrativa, en la moneda indicada.',
        ),
      });
    if (grid.length)
      out.push({
        key: 'correlation-grid',
        head: [t('Correlation grid', 'Grilla de correlaciones'), t('Known correlations', 'Correlaciones conocidas'), t('Size, maximum likelihood', 'Tamaño, máxima verosimilitud'), t('Size, moments', 'Tamaño, momentos'), t('Power, maximum likelihood', 'Potencia, máxima verosimilitud'), t('Power, moments', 'Potencia, momentos')],
        rows: grid.map((v) => c10GridRow(nameOf(v), v, lang)),
        note: t(
          'Size is the rate at which the test rejects the null correlation when it is true; power is the range of the rejection rate over the other known correlations. The simulator knows the true correlation of every cell.',
          'El tamaño es la tasa a la que la prueba rechaza la correlación nula cuando es cierta; la potencia es el rango de la tasa de rechazo sobre las otras correlaciones conocidas. El simulador conoce la correlación verdadera de cada celda.',
        ),
      });
    return out;
  }
  const one = (head: string[], row: (n: string, v: Variant, l: Lang) => Cell[], note: string, wide = 1): W2Table[] => [{ key: id, head, rows: vs.map((v) => row(nameOf(v), v, lang)), note, wide }];
  if (id === 'C11')
    return one(
      [t('Window', 'Ventana'), t('Champion of each level', 'Campeón de cada nivel'), t('Traffic-light zone of the champion', 'Zona del semáforo del campeón'), t('Average FZ0 score of the champion', 'Puntaje FZ0 promedio del campeón'), t('Models in the confidence set (FZ0)', 'Modelos en el conjunto de confianza (FZ0)')],
      c11Row,
      t(
        'The champion of a level is the model with the lowest average FZ0 score among the eligible ones; the confidence set (MCS) counts the models the test cannot separate from the best. The Basel traffic light is defined for the 99% VaR only.',
        'El campeón de un nivel es el modelo con el menor puntaje FZ0 promedio entre los elegibles; el conjunto de confianza (MCS) cuenta los modelos que la prueba no logra separar del mejor. El semáforo de Basilea se define solo para el VaR al 99%.',
      ),
      5,
    );
  if (id === 'C13')
    return one(
      [t('Desk', 'Mesa'), t('Planted deficiency', 'Deficiencia sembrada'), t('Share caught (95% interval)', 'Parte detectada (intervalo 95%)'), t('PLA zones, joint (replications)', 'Zonas PLA, conjuntas (réplicas)')],
      c13Row,
      t(
        'A replication is caught when its joint zone of the P&L attribution test is amber or red; on the control, with no deficiency, that share is the false alarm rate.',
        'Una réplica se detecta cuando su zona conjunta de la prueba de atribución de P&L es ámbar o roja; en el control, sin deficiencia, esa parte es la tasa de falsas alarmas.',
      ),
      2,
    );
  if (id === 'C14')
    return one(
      [t('Valuation date', 'Fecha de valoración'), t('Largest delta EVE, behavioural NMD', 'Mayor delta EVE, NMD conductual'), t('Largest delta EVE, contractual NMD', 'Mayor delta EVE, NMD contractual'), t('Outlier test, behavioural NMD', 'Prueba de valor atípico, NMD conductual'), t('Outlier test, contractual NMD', 'Prueba de valor atípico, NMD contractual')],
      c14Row,
      t(
        'The largest of the six prescribed shocks of the 2024 calibration, with the shock that gives it; the outlier test compares it with 15% of Tier 1 capital. A positive delta is a loss; contractual puts every non-maturity deposit in the overnight bucket.',
        'El mayor de los seis shocks prescritos de la calibración 2024, con el shock que lo da; la prueba de valor atípico lo compara con 15% del capital de nivel 1. Un delta positivo es una pérdida; contractual pone todo depósito sin vencimiento en el tramo a la vista.',
      ),
      5,
    );
  if (id === 'C15')
    return one(
      [t('Variant', 'Variante'), t('Largest delta EVE, offset applied', 'Mayor delta EVE, con compensación'), t('Largest delta EVE, no offset', 'Mayor delta EVE, sin compensación'), t('Outlier test, delta EVE', 'Prueba de valor atípico, delta EVE'), t('Delta NII with the indexation charge', 'Delta NII con el cargo por reajustabilidad'), t('Outlier test, delta NII', 'Prueba de valor atípico, delta NII')],
      c15Row,
      t(
        'The largest of the six shocks of Annex 1 over the CLP and UF legs, with the 50% offset applied or not; the bank is synthetic, calibrated to public aggregates, and its rows stay on the fixtures until the owner supplies the data.',
        'El mayor de los seis shocks del Anexo 1 sobre los tramos CLP y UF, con la compensación de 50% aplicada o no; el banco es sintético, calibrado a agregados públicos, y sus filas siguen en los ejemplos hasta que el dueño entregue los datos.',
      ),
      6,
    );
  return one(
    [t('Variant', 'Variante'), t('Tail index', 'Índice de cola'), t('True 99.9% quantile', 'Cuantil verdadero al 99,9%'), t('LDA capital over the true quantile (median)', 'Capital LDA sobre el cuantil verdadero (mediana)'), t('Its dispersion (IQR over the true quantile)', 'Su dispersión (rango intercuartil sobre el cuantil verdadero)'), t('SMA capital', 'Capital SMA')],
    c17Row,
    t(
      `The LDA capital is the spliced lognormal and GPD rung over ${C17_YEARS} years of losses collected above EUR 20,000, across the independent histories of the cell; a ratio of 1 is the true quantile. The SMA capital is the standardised measure of the synthetic bank with no added loss.`,
      `El capital LDA es el peldaño de empalme lognormal y GPD sobre ${C17_YEARS} años de pérdidas recolectadas sobre EUR 20.000, entre las historias independientes de la celda; una razón de 1 es el cuantil verdadero. El capital SMA es la medida estandarizada del banco sintético sin pérdida agregada.`,
    ),
    1,
  );
}

// ------------------------------------------------------------------------------------------------------ Benchmark

function c10Rungs(name: string, v: Variant, lang: Lang): W2Table {
  const t = T(lang);
  const o = v.outputs as C10Outputs;
  const ref = o.rungs.find((r) => r.method === 'gaussian-copula-one-factor' && r.evaluated);
  const refEc = measureOf(ref, C10_LEVEL_FOCUS)?.ec ?? null;
  const rows = o.rungs.map((r): Cell[] => {
    const label = `${r.rung} ${bi(r.label, lang)}`;
    const method = bi(c10Text(METHOD_TEXT, r.method), lang);
    const kind = bi(c10Text(ESTIMATOR_KIND_TEXT, r.estimator), lang);
    const m = measureOf(r, C10_LEVEL_FOCUS);
    if (!r.evaluated || !m) return [label, method, kind, na(lang, r.reason), '', '', '', ''];
    const gap = r === ref ? t('Reference (Monte Carlo)', 'Referencia (Monte Carlo)') : refEc ? pct((m.ec - refEc) / refEc, lang, 1) : na(lang, t('the reference did not run', 'la referencia no corrió'));
    return [
      label,
      method,
      kind,
      money(m.var, r.currency, lang),
      m.es === null || m.es === undefined ? na(lang, m.es_reason) : money(m.es, r.currency, lang),
      money(m.ec, r.currency, lang),
      m.var_se === null || m.var_se === undefined ? t('analytic', 'analítico') : money(m.var_se, r.currency, lang),
      gap,
    ];
  });
  return {
    key: `rungs-${v.variant_id}`,
    title: name,
    head: [t('Rung', 'Peldaño'), t('Method', 'Método'), t('Estimator', 'Estimador'), t('99.9% VaR', 'VaR al 99,9%'), t('99.9% ES', 'ES al 99,9%'), t('99.9% capital', 'Capital al 99,9%'), t('Monte Carlo error of the VaR', 'Error de Monte Carlo del VaR'), t('Capital against the reference', 'Capital frente a la referencia')],
    rows,
    wide: 3,
    note: t(
      'Every rung is measured on the same illustrative portfolio; the reference is the one-factor Gaussian copula by Monte Carlo, and a rung that did not run says so, with its reason, and no number stands in for it.',
      'Cada peldaño se mide sobre la misma cartera ilustrativa; la referencia es la cópula gaussiana de un factor por Monte Carlo, y un peldaño que no corrió lo dice, con su razón, y ningún número lo reemplaza.',
    ),
  };
}

function c10Estimators(name: string, v: Variant, lang: Lang): W2Table {
  const t = T(lang);
  const o = v.outputs as C10GridOutputs;
  const rows = o.cells.flatMap((c) =>
    c.estimators.map((e): Cell[] => [
      num(c.known_rho, lang, 2),
      bi(c10Text(ESTIMATOR_SHORT, e.estimator), lang),
      num(e.mean_estimate, lang, 3),
      num(e.bias, lang, 3),
      num(e.rmse, lang, 3),
      pct(e.coverage, lang, 1),
      `${pct(e.rejection_rate, lang, 1)} (${c.role === 'size' ? t('size', 'tamaño') : t('power', 'potencia')})`,
    ]),
  );
  return {
    key: `estimators-${v.variant_id}`,
    title: name,
    head: [t('Known correlation', 'Correlación conocida'), t('Estimator', 'Estimador'), t('Mean estimate', 'Estimación media'), t('Bias', 'Sesgo'), 'RMSE', t('Coverage of the 95% interval', 'Cobertura del intervalo 95%'), t('Rejection of the null', 'Rechazo de la nula')],
    rows,
    wide: 2,
    note: t('The simulator knows the true correlation of each cell, so the bias and the coverage are measured against it.', 'El simulador conoce la correlación verdadera de cada celda, así que el sesgo y la cobertura se miden contra ella.'),
  };
}

function c11Ladder(name: string, v: Variant, lang: Lang): W2Table {
  const t = T(lang);
  const o = v.outputs as C11Outputs;
  const yes = t('Yes', 'Sí');
  const no = t('No', 'No');
  const rows = o.levels.flatMap((l) =>
    o.models.map((m): Cell[] => {
      const r = m.by_level.find((x) => x.alpha === l.alpha);
      const isChamp = o.comparison.champions.find((c) => c.alpha === l.alpha)?.model_id === m.model_id;
      const dm = o.comparison.dm.find((d) => d.model_id === m.model_id && d.alpha === l.alpha && d.loss === 'fz0');
      const mcs = o.comparison.mcs.find((x) => x.alpha === l.alpha && x.loss === 'fz0')?.members.find((x) => x.model_id === m.model_id);
      let versus: string;
      if (isChamp) versus = t('Champion', 'Campeón');
      else if (!dm) versus = na(lang);
      else if (dm.p_value === null || dm.p_value === undefined) versus = na(lang, dm.not_evaluated_reason);
      else versus = `${bi(c11Text(DIRECTION_TEXT, dm.direction), lang)} (p ${num(dm.p_value, lang, 3)})`;
      return [
        bi(alphaShort(l.alpha), lang),
        `${m.rung} ${modelTitle(v, m.model_id, lang)}`,
        r ? `${formatNumber(r.n_exceedances, lang)} / ${num(r.expected_exceedances, lang, 2)}` : na(lang),
        !r ? na(lang) : r.fz0_mean === null || r.fz0_mean === undefined ? na(lang, r.fz0_reason) : num(r.fz0_mean, lang, 3),
        versus,
        mcs ? (mcs.in_set ? yes : no) : na(lang, t('the model has no FZ0, so it is not in the set', 'el modelo no tiene FZ0, así que no está en el conjunto')),
      ];
    }),
  );
  return {
    key: `ladder-${v.variant_id}`,
    title: name,
    head: [t('Level', 'Nivel'), t('Model', 'Modelo'), t('Exceedances / expected', 'Excedencias / esperadas'), t('Average FZ0 score', 'Puntaje FZ0 promedio'), t('Against the champion (Diebold-Mariano, FZ0)', 'Frente al campeón (Diebold-Mariano, FZ0)'), t('In the confidence set', 'En el conjunto de confianza')],
    rows,
    wide: 2,
    note: t(
      'A lower FZ0 score is better. A model that forecasts no expected shortfall has no FZ0 and says so; it is judged by its VaR back-tests in the App.',
      'Un puntaje FZ0 más bajo es mejor. Un modelo que no pronostica pérdida esperada no tiene FZ0 y lo dice; se juzga por sus pruebas de VaR en la App.',
    ),
  };
}

function c13Detection(manifest: CaseManifest, vs: Variant[], lang: Lang): W2Table {
  const t = T(lang);
  const name = titles(manifest, lang);
  const rows = vs.map((v): Cell[] => {
    const o = v.outputs as C13Outputs;
    const d = o.detection;
    const share = (n: number) => pct(d.n_replications > 0 ? n / d.n_replications : null, lang, 1);
    return [
      name[v.variant_id] ?? v.variant_id,
      bi(DEFICIENCY_TEXT[o.known_deficiency.deficiency_id] ?? { en: o.known_deficiency.deficiency_id, es: o.known_deficiency.deficiency_id }, lang),
      bi(INTENDED_TEXT[o.known_deficiency.intended_to_fail ?? 'none'] ?? { en: 'none', es: 'ninguna' }, lang),
      share(d.by_test.spearman_flagged),
      share(d.by_test.ks_flagged),
      share(d.by_test.desk_backtest_flagged),
      within(pct(d.share_amber_or_red, lang, 1), pct(d.ci_low, lang, 1), pct(d.ci_high, lang, 1), lang),
    ];
  });
  return {
    key: 'detection',
    head: [t('Desk', 'Mesa'), t('Planted deficiency', 'Deficiencia sembrada'), t('Intended to fail', 'Debía fallar'), t('Flagged by Spearman', 'Marcada por Spearman'), t('Flagged by Kolmogorov-Smirnov', 'Marcada por Kolmogorov-Smirnov'), t('Flagged by the desk back-test', 'Marcada por el backtest de mesa'), t('Joint zone amber or red (95% interval)', 'Zona conjunta ámbar o roja (intervalo 95%)')],
    rows,
    wide: 3,
    note: t(
      'The detection rate is the share of replications of the planted deficiency that each test flags; on the control (no deficiency) the same rate is the false alarm rate, which a sound test keeps low.',
      'La tasa de detección es la parte de las réplicas de la deficiencia sembrada que cada prueba marca; en el control (sin deficiencia) la misma tasa es la de falsas alarmas, que una prueba sana mantiene baja.',
    ),
  };
}

function c17Ladder(name: string, v: Variant, lang: Lang): W2Table {
  const t = T(lang);
  const o = v.outputs as C17Outputs;
  const cell = cellOf(o, C17_YEARS, C17_THRESHOLD);
  const q = o.truth.annual_loss_quantile;
  const rows: Cell[][] = RUNG_ORDER.map((rung): Cell[] => {
    const { summary, reason } = capitalOf(cell, rung);
    const label = pick(rungName(rung), lang);
    if (!summary) return [label, '', '', na(lang, reason), '', '', ''];
    return [
      label,
      bi(AGGREGATION_TEXT[summary.aggregation], lang, summary.aggregation),
      bi(STATUS_TEXT[summary.status], lang, summary.status),
      money(summary.capital_eur.median, o.currency, lang),
      num(summary.ratio_to_truth.median, lang, 2),
      pct(summary.share_underestimating, lang, 1),
      num(summary.iqr_over_truth, lang, 2),
    ];
  });
  const sma = o.sma_response.rows.find((r) => r.added_loss_eur === 0) ?? o.sma_response.rows[0];
  if (sma)
    rows.push([t('Standardised measurement approach (SMA)', 'Enfoque de medición estandarizado (SMA)'), t('closed form', 'forma cerrada'), STATUS_TEXT.verified ? pick(STATUS_TEXT.verified, lang) : '', money(sma.orc_eur, o.currency, lang), q ? num(sma.orc_eur / q.value_eur, lang, 2) : na(lang), '', '']);
  const truth = q ? `${t('True 99.9% quantile', 'Cuantil verdadero al 99,9%')}: ${money(q.value_eur, o.currency, lang)}` : '';
  return {
    key: `ladder-${v.variant_id}`,
    title: `${name} (${pick(cellLabel(cell.years, cell.collection_threshold_eur), lang)}${truth ? `; ${truth}` : ''})`,
    head: [t('Rung', 'Peldaño'), t('Aggregation', 'Agregación'), t('Status', 'Estado'), t('Capital (median)', 'Capital (mediana)'), t('Over the true quantile', 'Sobre el cuantil verdadero'), t('Histories underestimating', 'Historias que subestiman'), t('Dispersion (IQR over the truth)', 'Dispersión (rango intercuartil sobre la verdad)')],
    rows,
    wide: 3,
    note: t(
      'The ratio is the median capital over the true 99.9% quantile of the generator, so 1 is exact and below 1 underestimates; the SMA is a regulatory measure with no sampling, so it has a single value.',
      'La razón es el capital mediano sobre el cuantil verdadero al 99,9% del generador, así que 1 es exacto y bajo 1 subestima; el SMA es una medida regulatoria sin muestreo, así que tiene un solo valor.',
    ),
  };
}

/** The Benchmark tables of a case in its own terms: C10 the rungs against the Monte Carlo reference, C11 the ladder by FZ0 and the confidence set, C13 the detection rates, C17 the LDA rungs against the true quantile and the SMA. */
export function wave2BenchmarkTables(manifest: CaseManifest, vs: Variant[], lang: Lang): W2Table[] {
  const name = titles(manifest, lang);
  const nameOf = (v: Variant) => name[v.variant_id] ?? v.variant_id;
  switch (manifest.case_id) {
    case 'C10':
      return vs.map((v) => (kindOf(v) === 'correlation-grid' ? c10Estimators(nameOf(v), v, lang) : c10Rungs(nameOf(v), v, lang)));
    case 'C11':
      return vs.map((v) => c11Ladder(nameOf(v), v, lang));
    case 'C13':
      return [c13Detection(manifest, vs, lang)];
    case 'C17':
      return vs.map((v) => c17Ladder(nameOf(v), v, lang));
    default:
      return [];
  }
}

// ---------------------------------------------------------------------------------------------------- Components

function Tables({ tables }: { tables: W2Table[] }) {
  return (
    <div data-state="ready">
      {tables.map((tb) => (
        <section key={tb.key}>
          {tb.title ? <h4>{tb.title}</h4> : null}
          <Table head={tb.head} rows={tb.rows} wide={tb.wide} />
          {tb.note ? <P en={tb.note} es={tb.note} /> : null}
        </section>
      ))}
    </div>
  );
}

/** The Experiments section of a case: what each variant found, in the case's own measures. */
export function W2ExperimentsSection({ manifest }: { manifest: CaseManifest }) {
  const lang = useShellLang();
  const all = useVariants(manifest);
  if (all.state !== 'ready') return <Loading />;
  return <Tables tables={wave2ExperimentTables(manifest, all.data, lang)} />;
}

/** The Benchmark section of a case: its comparison in its own terms. */
export function W2BenchmarkSection({ manifest }: { manifest: CaseManifest }) {
  const lang = useShellLang();
  const t = useT();
  const all = useVariants(manifest);
  if (all.state !== 'ready') return <p className="caos-pending" data-state="loading">{t('Loading the comparisons', 'Cargando las comparaciones')}</p>;
  return <Tables tables={wave2BenchmarkTables(manifest, all.data, lang)} />;
}
