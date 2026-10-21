// The sections of the cross-case pages for the cases of wave 2 batch 3: C02 (corporate PD across horizons), C12 (swap
// exposure, CVA and SA-CCR), C16 (liquidity stress), C18 (ICAAP and IAPE capital aggregation), C20 (ML model validation)
// and C21 (fair-lending disparity). Experiments reads one headline row per variant in the case's own measures; Benchmark
// compares C02, C12, C18 and C20 in their own terms (C16 and C21 are excluded there, with the reason). A case with no
// section of its own gets the generic table of its impact items (`impactTables`), never the C01 scorecard shape. Every
// number is read from the committed variant artifacts when the page opens, none is typed in, and a value the artifact
// leaves null says "not available" with the reason the document gives. The tables are pure functions of the artifacts so
// that the tests read them from the contract fixtures.
import type { ReactElement } from 'react';
import { formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import type { BiText } from '@fasl-work/caos-app-shell';
import type { components } from '../lib/contract.gen';
import type { CaseManifest, VariantArtifact } from '../lib/contract.types';
import { COMMITTED, LIGHT_TEXT } from '../lib/policy';
import { P, useT } from '../content/bi';
import { Marked } from '../workbench/c21/Marked';
import { Loading, Table, money, num, pct, useVariants } from './U6Sections';

type Lang = 'en' | 'es';
type Cell = string | ReactElement;
type Variant = VariantArtifact<unknown>;
type Schemas = components['schemas'];

type C02Outputs = Schemas['c02Outputs'];
type C12Outputs = Schemas['c12Outputs'];
type C16Outputs = Schemas['c16Outputs'];
type C16Reverse = Schemas['c16ReverseOutputs'];
type C18Outputs = Schemas['c18Outputs'];
type C18Aggregation = Schemas['c18AggOutputs'];
type C18Reverse = Schemas['c18RevOutputs'];
type C20Shock = Schemas['c20Outputs'];
type C20Shift = Schemas['c20OutputsShift'];
type C20Seeds = Schemas['c20OutputsSeeds'];
type C20Perturbation = Schemas['c20OutputsPerturbation'];
type C20Leakage = Schemas['c20OutputsLeakage'];
type C21Outputs = Schemas['c21Outputs'];

/** A table of a case, already in the language of the reader: the pure result of the artifacts. */
export interface B3Table {
  key: string;
  title?: string;
  head: string[];
  rows: Cell[][];
  /** The number of left-aligned text columns (the first by default). */
  wide?: number;
  note?: string;
}

/** The cases this file renders on Experiments. */
export const B3_CASES = new Set(['C02', 'C12', 'C16', 'C18', 'C20', 'C21']);
/** The cases with a comparison in their own terms for the Benchmark (C16 and C21 are excluded there, with a reason). */
export const B3_BENCHMARK_CASES = new Set(['C02', 'C12', 'C18', 'C20']);

/** What a value the artifact leaves out reads like: "not available", and the reason when the document gives one. */
const na = (lang: Lang, reason?: string | null): string => `${formatNumber(null, lang)}${reason ? ` (${reason})` : ''}`;
const bi = (t: BiText | undefined | null, lang: Lang, fallback = ''): string => (t ? pick(t, lang) : fallback);
const join = (parts: string[]): string => parts.join('; ');
const signed = (v: number, lang: Lang, decimals = 3): string => `${v > 0 ? '+' : ''}${num(v, lang, decimals)}`;
const T = (lang: Lang) => (en: string, es: string) => (lang === 'es' ? es : en);
const yes = (lang: Lang, v: boolean): string => (v ? T(lang)('Yes', 'Sí') : T(lang)('No', 'No'));
const titles = (manifest: CaseManifest, lang: Lang): Record<string, string> =>
  Object.fromEntries(manifest.artifacts.filter((a) => a.role === 'variant').map((a) => [a.variant_id, pick(a.short_title ?? a.title, lang)]));
/** The money of a document in CLP millions, scaled to units and then to bn or m. */
const clpM = (v: number | null | undefined, lang: Lang): string => money(v === null || v === undefined ? null : v * 1e6, 'CLP', lang);

// ---------------------------------------------------------------------------------------------------- C02

/** The calibration light of a rung: the Hosmer-Lemeshow p under the committed policy (red below 1 percent, amber below 5). */
function c02Light(p: number, lang: Lang): string {
  const light = p < COMMITTED.red ? 'red' : p < COMMITTED.amber ? 'amber' : 'green';
  return `${pick(LIGHT_TEXT[light], lang)} (${T(lang)('Hosmer-Lemeshow p', 'p de Hosmer-Lemeshow')} ${num(p, lang, 3)})`;
}

function c02Row(name: string, v: Variant, lang: Lang): Cell[] {
  const t = T(lang);
  const o = v.outputs as C02Outputs;
  const champ = o.rungs.find((r) => r.rung === 'P1');
  const best = o.rungs.reduce<C02Outputs['rungs'][number] | undefined>((b, r) => (!b || r.discrimination.auc > b.discrimination.auc ? r : b), undefined);
  const noChamp = t('the document holds no P1 rung', 'el documento no contiene el peldaño P1');
  const cell = champ ? o.transfer.cells.find((c) => c.rung === 'P1') : undefined;
  const horizon = o.years === null ? t('Pooled (all five files)', 'Agrupado (los cinco archivos)') : o.years === 1 ? t('1 year', '1 año') : t(`${o.years} years`, `${o.years} años`);
  return [
    name,
    horizon,
    formatNumber(o.counts.rows, lang),
    formatNumber(o.counts.events, lang),
    champ ? num(champ.discrimination.auc, lang, 3) : na(lang, noChamp),
    best ? `${best.rung} (${num(best.discrimination.auc, lang, 3)})` : na(lang, t('the document holds no rung', 'el documento no contiene ningún peldaño')),
    champ ? c02Light(champ.calibration.hosmer_lemeshow.p_value, lang) : na(lang, noChamp),
    champ && cell
      ? `${signed(cell.auc - champ.discrimination.auc, lang)} (${t(`fitted on ${cell.fitted_on_years} years, scored on ${cell.scored_on_years}`, `ajustado con ${cell.fitted_on_years} años, evaluado en ${cell.scored_on_years}`)})`
      : na(lang, champ ? bi(o.transfer.reason, lang) : noChamp),
  ];
}

function c02Ladder(name: string, v: Variant, lang: Lang): B3Table {
  const t = T(lang);
  const o = v.outputs as C02Outputs;
  const champ = o.rungs.find((r) => r.rung === 'P1');
  const modelTitle = (id: string): string => {
    const m = v.model.find((x) => x.id === id);
    return m ? pick(m.title, lang) : id;
  };
  const rows = o.rungs.map((r): Cell[] => {
    const pair = o.challenger.find((c) => c.challenger === r.model_id);
    const d = r === champ ? t('Champion', 'Campeón') : pair ? signed(pair.auc_diff, lang) : na(lang, t('the document holds no paired test for this rung', 'el documento no contiene prueba pareada para este peldaño'));
    const p = r === champ ? '' : pair ? num(pair.delong_p_value, lang, 3) : na(lang);
    return [
      `${r.rung} ${modelTitle(r.model_id)}`,
      `${num(r.discrimination.auc, lang, 3)} (${num(r.discrimination.auc_ci.lo, lang, 3)} ${t('to', 'a')} ${num(r.discrimination.auc_ci.hi, lang, 3)})`,
      num(r.calibration.brier, lang, 4),
      num(r.calibration.ece, lang, 4),
      num(r.calibration.hosmer_lemeshow.p_value, lang, 3),
      d,
      p,
    ];
  });
  return {
    key: `ladder-${v.variant_id}`,
    title: name,
    head: [t('Rung', 'Peldaño'), t('AUC (95% interval)', 'AUC (intervalo 95%)'), 'Brier', 'ECE', t('Hosmer-Lemeshow p', 'p de Hosmer-Lemeshow'), t('AUC difference to the champion', 'Diferencia de AUC con el campeón'), t('DeLong p of the difference', 'p de DeLong de la diferencia')],
    rows,
    wide: 1,
    note: t(
      'Every rung is scored on the same locked holdout; the difference is the challenger minus the champion, and the DeLong test is paired on the same firms.',
      'Cada peldaño se evalúa sobre la misma muestra reservada bloqueada; la diferencia es el retador menos el campeón, y la prueba de DeLong es pareada sobre las mismas empresas.',
    ),
  };
}

// ---------------------------------------------------------------------------------------------------- C12

/** The largest value of a profile, or null when it is empty. */
const peak = (values: number[] | undefined): number | null => (values && values.length ? Math.max(...values) : null);

function c12Effect(o: C12Outputs, lang: Lang): string {
  const t = T(lang);
  const cur = o.exposure.ee.currency;
  const parts: string[] = [];
  if (o.initial_margin) {
    const vm = peak(o.initial_margin.ee_vm_only.values);
    const im = peak(o.exposure.ee.values);
    parts.push(
      t(`initial margin: peak EE ${money(vm, cur, lang)} with variation margin only, ${money(im, cur, lang)} with the margin`, `margen inicial: EE máxima ${money(vm, cur, lang)} solo con margen de variación, ${money(im, cur, lang)} con el margen`),
    );
  }
  if (o.wrong_way_risk && o.wrong_way_risk.sweep.length) {
    const w = o.wrong_way_risk;
    const top = w.sweep.reduce((a, b) => (b.b > a.b ? b : a));
    const ind = w.independent_cva.amount;
    const change = ind ? top.cva.amount / ind - 1 : null;
    parts.push(
      t(
        `wrong-way factor b = ${num(top.b, lang, 1)}: CVA ${money(top.cva.amount, cur, lang)} against ${money(ind, cur, lang)} independent (${change === null ? na(lang) : `${change > 0 ? '+' : ''}${pct(change, lang, 1)}`})`,
        `factor de riesgo de camino equivocado b = ${num(top.b, lang, 1)}: CVA ${money(top.cva.amount, cur, lang)} frente a ${money(ind, cur, lang)} independiente (${change === null ? na(lang) : `${change > 0 ? '+' : ''}${pct(change, lang, 1)}`})`,
      ),
    );
  }
  return parts.length ? join(parts) : na(lang, t('this variant has neither an initial margin nor a wrong-way factor', 'esta variante no tiene margen inicial ni factor de riesgo de camino equivocado'));
}

function c12Gap(o: C12Outputs, lang: Lang): string {
  const t = T(lang);
  const r = o.ore_reconciliation;
  const cur = o.exposure.ee.currency;
  if (!r.eepe_agreement || !r.cva_agreement) return na(lang, bi(r.reason, lang, t('the document holds no ORE reconciliation', 'el documento no contiene conciliación con ORE')));
  const within = r.eepe_agreement.within_two_se && r.cva_agreement.within_two_se;
  return t(
    `EEPE ${signed(r.eepe_agreement.difference, lang, 2)} ${cur}, CVA ${signed(r.cva_agreement.difference, lang, 2)} ${cur} (ORE minus Python; ${within ? 'within' : 'outside'} two combined standard errors)`,
    `EEPE ${signed(r.eepe_agreement.difference, lang, 2)} ${cur}, CVA ${signed(r.cva_agreement.difference, lang, 2)} ${cur} (ORE menos Python; ${within ? 'dentro de' : 'fuera de'} dos errores estándar combinados)`,
  );
}

function c12Row(name: string, v: Variant, lang: Lang): Cell[] {
  const o = v.outputs as C12Outputs;
  const cur = o.exposure.ee.currency;
  return [name, money(o.exposure.eepe.amount, cur, lang), money(o.cva_dva.cva.amount, cur, lang), money(o.sa_ccr.ead.amount, o.sa_ccr.ead.currency, lang), c12Effect(o, lang), c12Gap(o, lang)];
}

function c12Ore(manifest: CaseManifest, vs: Variant[], lang: Lang): B3Table {
  const t = T(lang);
  const name = titles(manifest, lang);
  const rows = vs.map((v): Cell[] => {
    const o = v.outputs as C12Outputs;
    const r = o.ore_reconciliation;
    const cur = o.exposure.ee.currency;
    const reason = na(lang, bi(r.reason, lang, t('the document holds no ORE reconciliation', 'el documento no contiene conciliación con ORE')));
    const e = r.eepe_agreement;
    const c = r.cva_agreement;
    return [
      name[v.variant_id] ?? v.variant_id,
      r.status === 'reconciled' ? t('Reconciled', 'Conciliada') : t('Not applicable', 'No aplica'),
      money(o.exposure.eepe.amount, cur, lang),
      e ? money(e.ore, cur, lang) : reason,
      e ? `${signed(e.difference, lang, 2)} ${cur}` : reason,
      money(o.cva_dva.cva.amount, cur, lang),
      c ? money(c.ore, cur, lang) : reason,
      c ? `${signed(c.difference, lang, 2)} ${cur}` : reason,
      e && c ? yes(lang, e.within_two_se && c.within_two_se) : reason,
    ];
  });
  return {
    key: 'ore',
    head: [t('Variant', 'Variante'), t('ORE reconciliation', 'Conciliación con ORE'), t('EEPE, Python', 'EEPE, Python'), t('EEPE, ORE', 'EEPE, ORE'), t('EEPE gap (ORE minus Python)', 'Brecha de EEPE (ORE menos Python)'), t('CVA, Python', 'CVA, Python'), t('CVA, ORE', 'CVA, ORE'), t('CVA gap (ORE minus Python)', 'Brecha de CVA (ORE menos Python)'), t('Both within two standard errors', 'Ambas dentro de dos errores estándar')],
    rows,
    wide: 2,
    note: t(
      'ORE is the reference engine: the gap is ORE minus the Python value, positive when ORE is higher, and it is judged against the combined Monte Carlo standard error. A variant ORE cannot run says so, with its reason.',
      'ORE es el motor de referencia: la brecha es ORE menos el valor de Python, positiva cuando ORE es mayor, y se juzga contra el error estándar de Monte Carlo combinado. Una variante que ORE no puede correr lo dice, con su razón.',
    ),
  };
}

// ---------------------------------------------------------------------------------------------------- C16

function c16Survival(s: Schemas['c16Survival'], lang: Lang): string {
  const t = T(lang);
  return s.kind === 'day' && s.day !== null && s.day !== undefined ? t(`day ${s.day} of ${s.horizon_days}`, `día ${s.day} de ${s.horizon_days}`) : t(`survives the horizon (${s.horizon_days} days)`, `sobrevive el horizonte (${s.horizon_days} días)`);
}

function c16Row(name: string, v: Variant, lang: Lang): Cell[] {
  const t = T(lang);
  const o = v.outputs as C16Outputs | C16Reverse;
  if (o.kind === 'reverse-stress') {
    return [
      name,
      join(o.bases.map((b) => `${bi(b.label, lang)}: ${c16Survival(b.base_survival, lang)}`)),
      na(lang, t('the reverse stress computes no LCR', 'el estrés inverso no calcula el LCR')),
      join(o.bases.map((b) => `${bi(b.label, lang)}: ${b.solved.status === 'solved' && b.solved.multiplier !== null ? num(b.solved.multiplier, lang, 2) : na(lang, bi(b.solved.refusal_reason, lang))}`)),
    ];
  }
  return [
    name,
    o.path ? c16Survival(o.path.survival, lang) : na(lang, bi(o.path_reason, lang)),
    o.lcr ? pct(o.lcr.ratio, lang, 2) : na(lang, bi(o.lcr_reason, lang)),
    na(lang, t('a scenario document holds no run-off multiplier', 'un documento de escenario no contiene multiplicador de salidas')),
  ];
}

// ---------------------------------------------------------------------------------------------------- C18

const BAND_METHOD: Record<string, BiText> = {
  'lower-bound': { en: 'lower bound', es: 'cota inferior' },
  'simple-sum': { en: 'simple sum', es: 'suma simple' },
  'variance-covariance': { en: 'variance-covariance', es: 'varianza-covarianza' },
  'gaussian-copula': { en: 'Gaussian copula', es: 'cópula gaussiana' },
  't-copula': { en: 't copula', es: 'cópula t' },
  'worst-case': { en: 'worst case', es: 'peor caso' },
};
const bandName = (r: { method: string; nu: number | null }, lang: Lang): string => {
  const m = BAND_METHOD[r.method];
  const name = m ? pick(m, lang) : r.method;
  return r.nu === null ? name : `${name}, nu ${num(r.nu, lang, 0)}`;
};
const bandOf = (o: C18Outputs | C18Aggregation | C18Reverse): Schemas['c18BandRow'][] => ('aggregation' in o ? (o as C18Outputs).aggregation.band : []);

function c18Row(name: string, v: Variant, lang: Lang): Cell[] {
  const t = T(lang);
  const o = v.outputs as C18Outputs | C18Aggregation | C18Reverse;
  const isScenario = o.kind === 'scenario';
  const noPath = na(lang, t('this variant runs the aggregation only', 'esta variante corre solo la agregación'));
  const notReverse = na(lang, t('this variant is not a reverse stress', 'esta variante no es un estrés inverso'));
  const rows = isScenario ? (o as C18Outputs).headline_cet1.rows : [];
  const last = rows[rows.length - 1];
  const ppnr = isScenario ? (o as C18Outputs).headline_cet1.ppnr.rows : [];
  const lastP = ppnr[ppnr.length - 1];
  const band = bandOf(o);
  const lo = band.length ? band.reduce((a, b) => (b.capital_clp_m < a.capital_clp_m ? b : a)) : undefined;
  const hi = band.length ? band.reduce((a, b) => (b.capital_clp_m > a.capital_clp_m ? b : a)) : undefined;
  const rev = o.kind === 'reverse' ? (o as C18Reverse).solution : undefined;
  return [
    name,
    last ? `${pct(last.cet1_ratio, lang, 2)} (${t(`year ${last.year}`, `año ${last.year}`)})` : noPath,
    lastP ? `${pct(lastP.cet1_ratio_with_ppnr, lang, 2)} (${t(`year ${lastP.year}`, `año ${lastP.year}`)})` : noPath,
    'aggregation' in o ? clpM(o.aggregation.headline.capital_clp_m, lang) : na(lang, t('this variant does not aggregate capital', 'esta variante no agrega capital')),
    lo && hi ? `${clpM(lo.capital_clp_m, lang)} (${bandName(lo, lang)}) ${t('to', 'a')} ${clpM(hi.capital_clp_m, lang)} (${bandName(hi, lang)})` : na(lang, t('this variant has no dependence band', 'esta variante no tiene banda de dependencia')),
    rev ? num(rev.mahalanobis_distance, lang, 3) : notReverse,
    rev ? pct(rev.plausibility.tail_probability, lang, 2) : notReverse,
  ];
}

function c18Band(name: string, v: Variant, lang: Lang): B3Table | null {
  const t = T(lang);
  const band = bandOf(v.outputs as C18Outputs | C18Aggregation | C18Reverse);
  if (!band.length) return null;
  return {
    key: `band-${v.variant_id}`,
    title: name,
    head: [t('Dependence rung', 'Peldaño de dependencia'), t('Capital', 'Capital'), t('Over the simple sum', 'Sobre la suma simple'), t('Status', 'Estado')],
    rows: band.map((r): Cell[] => [
      bandName(r, lang),
      clpM(r.capital_clp_m, lang),
      num(r.diversification_factor, lang, 2),
      r.status === 'headline-capital' ? t('Headline capital', 'Capital de referencia') : t('Information, not capital', 'Información, no capital'),
    ]),
    wide: 1,
    note: t(
      'The headline capital is the simple sum of the four marginals, as the IAPE adds the capital of each risk; the other rungs show how far a dependence assumption moves it, at one year and 99.9 percent, and are information for the validator, not capital.',
      'El capital de referencia es la suma simple de los cuatro marginales, como el IAPE suma el capital de cada riesgo; los otros peldaños muestran cuánto lo mueve un supuesto de dependencia, a un año y 99,9 por ciento, y son información para el validador, no capital.',
    ),
  };
}

// ---------------------------------------------------------------------------------------------------- C20

type C20Doc = C20Shock | C20Shift | C20Seeds | C20Perturbation | C20Leakage;

function c20Row(name: string, v: Variant, lang: Lang): Cell[] {
  const t = T(lang);
  const o = v.outputs as C20Doc;
  switch (o.kind) {
    case 'shock': {
      const aucs = o.shipped.rows.map((r) => r.performance.auc);
      const lo = Math.min(...aucs);
      const hi = Math.max(...aucs);
      const range = aucs.length ? (lo === hi ? num(lo, lang, 3) : `${num(lo, lang, 3)} ${t('to', 'a')} ${num(hi, lang, 3)}`) : na(lang, t('the document holds no shipped shock', 'el documento no contiene shocks entregados'));
      return [
        name,
        t('Shock', 'Shock'),
        o.seen_or_held_out === 'seen' ? t('AUC under the seen shocks', 'AUC bajo los shocks vistos') : t('AUC under the held-out shocks', 'AUC bajo los shocks reservados'),
        range,
        t(`${o.shipped.rows.length} shock families as shipped (${o.shipped.rows.map((r) => r.shock_id).join(', ')})`, `${o.shipped.rows.length} familias de shocks tal como se entregaron (${o.shipped.rows.map((r) => r.shock_id).join(', ')})`),
      ];
    }
    case 'shift': {
      const w = o.synthetic_shift?.worst_subsample;
      return [
        name,
        t('Shift', 'Deriva'),
        t('AUC change in the worst subsample', 'Cambio de AUC en la peor submuestra'),
        w ? signed(w.metric.auc_delta, lang) : na(lang, t('the document holds no worst-subsample reading', 'el documento no contiene lectura de la peor submuestra')),
        w ? t(`the worst ${pct(w.share, lang, 0)} of the evaluation set (AUC ${num(w.metric.auc, lang, 3)})`, `el peor ${pct(w.share, lang, 0)} del conjunto de evaluación (AUC ${num(w.metric.auc, lang, 3)})`) : na(lang),
      ];
    }
    case 'seeds':
      return [
        name,
        t('Seeds', 'Semillas'),
        t('Standard deviation of the AUC across seeds', 'Desviación estándar del AUC entre semillas'),
        o.rows.length ? join(o.rows.map((r) => `${r.rung}: ${num(r.auc.sd, lang, 3)}`)) : na(lang, t('the document holds no seed row', 'el documento no contiene fila de semillas')),
        o.rows.length ? join(o.rows.map((r) => t(`${r.rung}: ${r.n_seeds} seeds`, `${r.rung}: ${r.n_seeds} semillas`))) : na(lang),
      ];
    case 'perturbation': {
      const r = o.rows.find((x) => x.eps === o.preset_eps);
      return [
        name,
        t('Perturbation', 'Perturbación'),
        t('AUC change at the preset noise scale', 'Cambio de AUC en la escala de ruido predefinida'),
        r ? signed(r.metric.auc_delta, lang) : na(lang, t(`the grid holds no row at the preset scale ${num(o.preset_eps, lang, 2)}`, `la grilla no contiene fila en la escala predefinida ${num(o.preset_eps, lang, 2)}`)),
        t(`noise of ${num(o.preset_eps, lang, 2)} standard deviations of each feature`, `ruido de ${num(o.preset_eps, lang, 2)} desviaciones estándar de cada variable`),
      ];
    }
    case 'leakage':
      return [
        name,
        t('Leakage', 'Fuga'),
        t('Planted leak caught by the screen', 'Fuga sembrada detectada por el filtro'),
        yes(lang, o.caught),
        t(`planted feature ${o.planted_feature} (single-feature AUC ${num(o.screen.single_feature_auc.max_auc, lang, 2)})`, `variable sembrada ${o.planted_feature} (AUC de una sola variable ${num(o.screen.single_feature_auc.max_auc, lang, 2)})`),
      ];
    default:
      return [name, na(lang), na(lang), na(lang), na(lang)];
  }
}

function c20Seeds(name: string, v: Variant, lang: Lang): B3Table | null {
  const t = T(lang);
  const o = v.outputs as C20Doc;
  if (o.kind !== 'seeds') return null;
  return {
    key: `seeds-${v.variant_id}`,
    title: name,
    head: [t('Rung', 'Peldaño'), t('Seeds', 'Semillas'), t('AUC, mean', 'AUC, media'), t('AUC, standard deviation', 'AUC, desviación estándar'), t('AUC, lowest to highest', 'AUC, de menor a mayor'), t('Grade assignment changed', 'Asignación de grado cambiada'), t('Attribution rank correlation (mean)', 'Correlación de rango de atribución (media)'), t('Reason-code overlap (mean)', 'Solapamiento de códigos de razón (media)')],
    rows: o.rows.map((r): Cell[] => [
      r.rung,
      formatNumber(r.n_seeds, lang),
      num(r.auc.mean, lang, 3),
      num(r.auc.sd, lang, 3),
      `${num(r.auc.min, lang, 3)} ${t('to', 'a')} ${num(r.auc.max, lang, 3)}`,
      pct(r.grade_assignment_changed_share, lang, 1),
      num(r.attribution_rank_tau.mean, lang, 2),
      num(r.reason_code_overlap.mean, lang, 2),
    ]),
    wide: 1,
    note: t(
      'Each rung is refitted under many seeds on the same data: a stable model keeps its AUC, its grades and the reasons it gives for a decision.',
      'Cada peldaño se reajusta con muchas semillas sobre los mismos datos: un modelo estable mantiene su AUC, sus grados y las razones que da de una decisión.',
    ),
  };
}

// ---------------------------------------------------------------------------------------------------- C21

const ATTRIBUTE_TEXT: Record<string, BiText> = {
  derived_race: { en: 'Race', es: 'Raza' },
  derived_ethnicity: { en: 'Ethnicity', es: 'Etnia' },
  derived_sex: { en: 'Sex', es: 'Sexo' },
  applicant_age: { en: 'Age', es: 'Edad' },
  applicant_age_above_62: { en: 'Age, 62 or over', es: 'Edad, 62 o más' },
};
// the groups the C21 bake names in its own words (the 62 contrast); every other group is a source label, the same in both languages
const GROUP_NAME: Record<string, BiText> = {
  '62 or over': { en: '62 or over', es: '62 o más' },
  'under 62': { en: 'under 62', es: 'menores de 62' },
};
const groupName = (group: string, lang: Lang): string => bi(GROUP_NAME[group] ?? { en: group, es: group }, lang);
const BENCHMARK_LABEL_TEXT: Record<string, BiText> = { 'employment benchmark': { en: 'employment benchmark', es: 'referencia de empleo' } };
const attrName = (field: string, lang: Lang): string => bi(ATTRIBUTE_TEXT[field] ?? { en: field, es: field }, lang);

function c21Row(name: string, v: Variant, lang: Lang): Cell[] {
  const t = T(lang);
  const o = v.outputs as C21Outputs;
  const per = (f: (a: C21Outputs['attributes'][number], c: C21Outputs['attributes'][number]['contrasts'][number]) => string): string =>
    join(o.attributes.flatMap((a) => a.contrasts.map((c) => `${attrName(a.field, lang)}, ${groupName(c.group, lang)}: ${f(a, c)}`)));
  return [
    name,
    `${o.fit_year} ${t('to', 'a')} ${o.confirm_year}`,
    per((_, c) => (c.adverse_impact_ratio.value === null ? na(lang, bi(c.adverse_impact_ratio.note, lang)) : num(c.adverse_impact_ratio.value, lang, 2))),
    // the regulation's own citation ("29 CFR 1607.4") is kept as the source writes it, marked by the C21 helper
    <Marked key="four-fifths">{join(
      o.attributes.map((a) => {
        const flagged = a.four_fifths.groups.filter((g) => g.flag).map((g) => groupName(g.group, lang));
        const label = bi(BENCHMARK_LABEL_TEXT[a.four_fifths.label] ?? { en: a.four_fifths.label, es: a.four_fifths.label }, lang);
        return `${attrName(a.field, lang)}: ${flagged.length ? t(`flagged ${flagged.join(', ')}`, `marcado ${flagged.join(', ')}`) : t('no group flagged', 'ningún grupo marcado')} (${label}, ${a.four_fifths.citation})`;
      }),
    )}</Marked>,
    per((_, c) => {
      const e = c.controlled.estimate;
      return e ? t(`odds ratio ${num(e.odds_ratio, lang, 2)} (coefficient ${num(e.coefficient, lang, 2)}, 95% interval ${num(e.ci.lo, lang, 2)} to ${num(e.ci.hi, lang, 2)})`, `razón de momios ${num(e.odds_ratio, lang, 2)} (coeficiente ${num(e.coefficient, lang, 2)}, intervalo 95% ${num(e.ci.lo, lang, 2)} a ${num(e.ci.hi, lang, 2)})`) : na(lang, c.controlled.reason);
    }),
    per((_, c) => {
      const e = c.confirmation.estimate;
      return e ? `${yes(lang, e.same_sign)} (${t('coefficient', 'coeficiente')} ${num(e.fit_coefficient, lang, 2)} ${t('then', 'luego')} ${num(e.confirm_coefficient, lang, 2)})` : na(lang, c.confirmation.reason);
    }),
  ];
}

// -------------------------------------------------------------------------------------- the generic impact table

/** The table of a case without a section of its own: one row per (variant, impact item), with the label and the value and its unit. */
export function impactTables(manifest: CaseManifest, vs: Variant[], lang: Lang): B3Table[] {
  const t = T(lang);
  const name = titles(manifest, lang);
  const rows = vs.flatMap((v): Cell[][] => {
    const items = Object.values(v.impact ?? {});
    const n = name[v.variant_id] ?? v.variant_id;
    if (!items.length) return [[n, t('(no impact item)', '(sin ítem de impacto)'), na(lang, t('the document holds no impact item', 'el documento no contiene ítems de impacto'))]];
    return items.map((i): Cell[] => [n, pick(i.label, lang), i.value === null || i.value === undefined ? na(lang, pick(i.label, lang)) : `${formatNumber(i.value, lang)} ${i.unit}`]);
  });
  return [
    {
      key: manifest.case_id,
      head: [t('Variant', 'Variante'), t('Impact measure', 'Medida de impacto'), t('Value', 'Valor')],
      rows,
      wide: 2,
      note: t(
        'One row per impact item of each variant, as the document states it; an item the document leaves null says so, with its own label.',
        'Una fila por ítem de impacto de cada variante, tal como lo declara el documento; un ítem que el documento deja nulo lo dice, con su propia etiqueta.',
      ),
    },
  ];
}

// ---------------------------------------------------------------------------------------------------- Experiments

/** The Experiments tables of a case: one row per variant, in the order the variants are given (the manifest's). */
export function batch3ExperimentTables(manifest: CaseManifest, vs: Variant[], lang: Lang): B3Table[] {
  const t = T(lang);
  const name = titles(manifest, lang);
  const nameOf = (v: Variant) => name[v.variant_id] ?? v.variant_id;
  const id = manifest.case_id;
  const one = (head: string[], row: (n: string, v: Variant, l: Lang) => Cell[], note: string, wide = 1): B3Table[] => [{ key: id, head, rows: vs.map((v) => row(nameOf(v), v, lang)), note, wide }];
  switch (id) {
    case 'C02':
      return one(
        [t('Variant', 'Variante'), t('Horizon', 'Horizonte'), t('Records', 'Registros'), t('Defaults', 'Incumplimientos'), t('AUC of the champion (P1)', 'AUC del campeón (P1)'), t('Best rung by AUC', 'Mejor peldaño por AUC'), t('Calibration light of the champion', 'Luz de calibración del campeón'), t('AUC change in transfer', 'Cambio de AUC en la transferencia')],
        c02Row,
        t(
          'The AUC is read on the locked holdout; the calibration light applies the committed policy to the Hosmer-Lemeshow p of the champion; the transfer change is the AUC of the champion fitted on one horizon and scored on another, minus its holdout AUC, and is exploratory because the firm overlap across the files is unknown.',
          'El AUC se lee en la muestra reservada bloqueada; la luz de calibración aplica la política comprometida al p de Hosmer-Lemeshow del campeón; el cambio en la transferencia es el AUC del campeón ajustado con un horizonte y evaluado en otro, menos su AUC reservado, y es exploratorio porque se desconoce el solapamiento de empresas entre los archivos.',
        ),
        2,
      );
    case 'C12':
      return one(
        [t('Variant', 'Variante'), t('EEPE', 'EEPE'), t('CVA', 'CVA'), t('SA-CCR EAD', 'EAD de SA-CCR'), t('Effect of the initial margin or of the wrong-way factor', 'Efecto del margen inicial o del factor de riesgo de camino equivocado'), t('ORE reconciliation gap', 'Brecha de conciliación con ORE')],
        c12Row,
        t(
          'EEPE is the effective expected positive exposure of the variant, CVA its credit valuation adjustment and EAD the exposure at default of the standardised approach for counterparty credit risk; the gap is ORE minus Python, with its sign, and a variant ORE cannot reproduce says so.',
          'EEPE es la exposición positiva esperada efectiva de la variante, CVA su ajuste de valoración de crédito y EAD la exposición en caso de incumplimiento del enfoque estandarizado de riesgo de crédito de contraparte; la brecha es ORE menos Python, con su signo, y una variante que ORE no puede reproducir lo dice.',
        ),
        2,
      );
    case 'C16':
      return one(
        [t('Scenario', 'Escenario'), t('Survival period', 'Periodo de supervivencia'), t('LCR', 'LCR'), t('Run-off multiplier at the target (reverse stress)', 'Multiplicador de salidas en la meta (estrés inverso)')],
        c16Row,
        t(
          'A survival period is a day of the horizon, or "survives the horizon" with the horizon, and never a number that stands in for it; the LCR is a Basel formula on call-report aggregates, not the reported ratio; the reverse stress solves the multiple of the daily run-off rates at which the survival falls to the target.',
          'Un periodo de supervivencia es un día del horizonte, o "sobrevive el horizonte" con el horizonte, y nunca un número que lo reemplace; el LCR es una fórmula de Basilea sobre agregados del reporte de llamada, no la razón informada; el estrés inverso resuelve el múltiplo de las tasas diarias de salida con el que la supervivencia cae a la meta.',
        ),
        1,
      );
    case 'C18':
      return one(
        [t('Scenario', 'Escenario'), t('CET1 ratio, loss only', 'Razón CET1, solo pérdidas'), t('CET1 ratio with PPNR', 'Razón CET1 con PPNR'), t('Simple-sum capital', 'Capital por suma simple'), t('Dependence band, lowest to highest', 'Banda de dependencia, de menor a mayor'), t('Reverse stress: Mahalanobis distance', 'Estrés inverso: distancia de Mahalanobis'), t('Reverse stress: tail probability', 'Estrés inverso: probabilidad de cola')],
        c18Row,
        t(
          'The headline CET1 path is the jump-off less the cumulative stressed losses, with no revenue invented; the row with PPNR is labelled and is not the headline. The band runs from the lower bound to the worst case of the dependence assumptions; the reverse stress is the scenario of least Mahalanobis distance that takes CET1 to the legal minimum stack.',
          'La trayectoria CET1 de referencia es el punto de partida menos las pérdidas estresadas acumuladas, sin inventar ingresos; la fila con PPNR está rotulada y no es la referencia. La banda va de la cota inferior al peor caso de los supuestos de dependencia; el estrés inverso es el escenario de menor distancia de Mahalanobis que lleva el CET1 al mínimo legal.',
        ),
        1,
      );
    case 'C20':
      return one(
        [t('Variant', 'Variante'), t('Kind', 'Tipo'), t('Headline measure', 'Medida principal'), t('Value', 'Valor'), t('Basis', 'Base')],
        c20Row,
        t(
          'Each kind of variant asks one question of the same model and states one measure: how the AUC holds under seen and held-out shocks, how far it falls in the worst subsample, how much it varies across seeds, how it degrades under noise, and whether a planted leak is caught.',
          'Cada tipo de variante hace una pregunta al mismo modelo y declara una medida: cómo se mantiene el AUC bajo shocks vistos y reservados, cuánto cae en la peor submuestra, cuánto varía entre semillas, cómo se degrada con ruido y si se detecta una fuga sembrada.',
        ),
        3,
      );
    case 'C21':
      return one(
        [t('Year pair', 'Par de años'), t('Fit and confirmation years', 'Años de ajuste y confirmación'), t('Adverse impact ratio, by group', 'Razón de impacto adverso, por grupo'), t('Four-fifths rule, employment benchmark', 'Regla de cuatro quintos, referencia de empleo'), t('Conditional disparity (controlled model)', 'Disparidad condicional (modelo controlado)'), t('Replicates in the next year', 'Se replica en el año siguiente')],
        c21Row,
        t(
          'The adverse impact ratio is the selection rate of the group over the reference group; the four-fifths rule is an employment benchmark, not a credit-law threshold; the conditional disparity is the odds ratio of a model with the controls the public data hold, an approximation of comparative evidence; no row is a finding of violation.',
          'La razón de impacto adverso es la tasa de selección del grupo sobre la del grupo de referencia; la regla de cuatro quintos es una referencia de empleo, no un umbral de la ley de crédito; la disparidad condicional es la razón de momios de un modelo con los controles que contienen los datos públicos, una aproximación a evidencia comparativa; ninguna fila es una declaración de infracción.',
        ),
        2,
      );
    default:
      return impactTables(manifest, vs, lang);
  }
}

// ------------------------------------------------------------------------------------------------------ Benchmark

/** The Benchmark tables of a case in its own terms: C02 the rungs against the champion, C12 against ORE, C18 across the dependence band, C20 across the rungs of the seed sweep. */
export function batch3BenchmarkTables(manifest: CaseManifest, vs: Variant[], lang: Lang): B3Table[] {
  const name = titles(manifest, lang);
  const nameOf = (v: Variant) => name[v.variant_id] ?? v.variant_id;
  const present = (xs: Array<B3Table | null>): B3Table[] => xs.filter((x): x is B3Table => x !== null);
  switch (manifest.case_id) {
    case 'C02':
      return vs.map((v) => c02Ladder(nameOf(v), v, lang));
    case 'C12':
      return [c12Ore(manifest, vs, lang)];
    case 'C18':
      return present(vs.map((v) => c18Band(nameOf(v), v, lang)));
    case 'C20':
      return present(vs.map((v) => c20Seeds(nameOf(v), v, lang)));
    default:
      return [];
  }
}

// ---------------------------------------------------------------------------------------------------- Components

function Tables({ tables, empty }: { tables: B3Table[]; empty?: { en: string; es: string } }) {
  return (
    <div data-state="ready">
      {tables.length === 0 && empty ? <P en={empty.en} es={empty.es} /> : null}
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
export function B3ExperimentsSection({ manifest }: { manifest: CaseManifest }) {
  const lang = useShellLang();
  const all = useVariants(manifest);
  if (all.state !== 'ready') return <Loading />;
  return <Tables tables={batch3ExperimentTables(manifest, all.data, lang)} />;
}

/** The Experiments section of a case with no section of its own: the table of its impact items. */
export function ImpactSection({ manifest }: { manifest: CaseManifest }) {
  const lang = useShellLang();
  const all = useVariants(manifest);
  if (all.state !== 'ready') return <Loading />;
  return <Tables tables={impactTables(manifest, all.data, lang)} />;
}

/** The Benchmark section of a case: its comparison in its own terms. */
export function B3BenchmarkSection({ manifest }: { manifest: CaseManifest }) {
  const lang = useShellLang();
  const t = useT();
  const all = useVariants(manifest);
  if (all.state !== 'ready') return <p className="caos-pending" data-state="loading">{t('Loading the comparisons', 'Cargando las comparaciones')}</p>;
  return (
    <Tables
      tables={batch3BenchmarkTables(manifest, all.data, lang)}
      empty={{ en: 'None of the variants of this case holds a ladder of rungs to compare.', es: 'Ninguna variante de este caso contiene una escalera de peldaños para comparar.' }}
    />
  );
}
