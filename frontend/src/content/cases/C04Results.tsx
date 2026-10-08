// The measured results of case C04 (CT-412), read from the committed variant artifacts at load time; no number here is
// typed in. The agencies' long-run averages and checks, the known-truth families' headline measurements, the papers
// recomputed and every variant's findings. The Context view shows it under the write-up (C04.tsx). The readers below
// (the variants of the case, an agency's facts, the papers' agreements, the findings' order) are shared with the
// Findings and Variants views (workbench/c04/C04Common.tsx) and the cross-case sections (pages/C04Sections.tsx).
import { formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { createContext, useContext, type ReactNode } from 'react';
import { loadAllVariants, useArtifact, type Loaded } from '../../api/artifacts';
import type { C04Homogeneity, CaseManifest, Finding, ImpactItem, VariantArtifact } from '../../lib/contract.types';
import { Pending } from '../../workbench/Pending';
import {
  DEFINITION_LABEL,
  ESMA_DEFINITIONS,
  GENERATOR_KEYS,
  GRADES,
  N_GRADES,
  isAgency,
  isFamily,
  isPublished,
  type AgencyVariant,
  type FamilyVariant,
  type GeneratorKey,
  type PublishedVariant,
} from '../../workbench/c04/selection';

export type Lang = 'en' | 'es';

const sum = (a: readonly number[]) => a.reduce((s, x) => s + x, 0);

/** A PD, a rate or a share as a percentage, three significant digits by default. */
export const pctText = (lang: Lang, v: number | null | undefined, digits = 3): string => formatNumber(v, lang, { percent: true, digits });

/** A p-value as the findings print it: one that underflowed to 0 in double precision is said to lie below 1e-300. */
export function pText(lang: Lang, p: number | null | undefined): string {
  return p === 0 ? 'p < 1e-300' : `p ${formatNumber(p, lang, { digits: 2 })}`;
}

/** Consecutive years as ranges: "2006 to 2014", "2003, 2006 to 2008" (years are written without a thousands mark). */
export function yearRanges(labels: readonly string[], lang: Lang): string {
  const ys = [...new Set(labels.map(Number).filter(Number.isFinite))].sort((a, b) => a - b);
  const out: string[] = [];
  for (let i = 0; i < ys.length; ) {
    let j = i;
    while (j + 1 < ys.length && ys[j + 1] === ys[j] + 1) j++;
    out.push(j === i ? String(ys[i]) : `${ys[i]} ${lang === 'es' ? 'a' : 'to'} ${ys[j]}`);
    i = j + 1;
  }
  return out.join(', ');
}

// ---------------------------------------------------------------------------------------------------------------------
// the variants of the case

const Preloaded = createContext<VariantArtifact[] | null>(null);

/** Variants already in hand (a test, a page that loaded them): the C04 sections read them instead of fetching. */
export function C04VariantsProvider({ variants, children }: { variants: VariantArtifact[]; children: ReactNode }) {
  return <Preloaded.Provider value={variants}>{children}</Preloaded.Provider>;
}

/** Every variant of the case, loaded once (api/artifacts caches each file) or taken from a C04VariantsProvider. */
export function useC04Variants(manifest: CaseManifest | null | undefined): Loaded<VariantArtifact<unknown>[]> {
  const pre = useContext(Preloaded);
  const loaded = useArtifact<VariantArtifact[]>(
    (s) => (pre ? Promise.resolve(pre) : manifest ? loadAllVariants(manifest, s) : new Promise<VariantArtifact[]>(() => undefined)),
    [manifest?.case_id, pre],
  );
  if (pre) return { state: 'ready', data: pre as VariantArtifact<unknown>[] };
  return loaded as Loaded<VariantArtifact<unknown>[]>;
}

/** What a section shows when the variants could not be loaded: the error, never a loading state that never ends. */
export function LoadError({ error }: { error: string }) {
  const lang = useShellLang();
  return (
    <p className="ct-note" data-state="error" role="alert">
      {pick({ en: 'The variants of the case could not be loaded: ', es: 'No se pudieron cargar las variantes del caso: ' }, lang)}
      {error}
    </p>
  );
}

export interface C04Kinds {
  agencies: AgencyVariant[];
  families: FamilyVariant[];
  published: PublishedVariant | null;
}

export function kindsOf(vs: readonly VariantArtifact<unknown>[]): C04Kinds {
  return { agencies: vs.filter(isAgency), families: vs.filter(isFamily), published: vs.find(isPublished) ?? null };
}

const entryOf = (m: CaseManifest, id: string) => m.artifacts.find((a) => a.role === 'variant' && a.variant_id === id);
/** The label a chip or a row shows for a variant ("S&P", "Markov"). */
export const shortOf = (m: CaseManifest, id: string): BiText => entryOf(m, id)?.short_title ?? { en: id, es: id };
/** A variant's full title. */
export const titleOf = (m: CaseManifest, id: string): BiText => entryOf(m, id)?.title ?? { en: id, es: id };

// ---------------------------------------------------------------------------------------------------------------------
// readings of an agency, a family and the papers

/** ESMA's attribution as the source registry states it: the source's own wording, kept verbatim in both languages. */
export const ATTRIBUTION_FALLBACK = 'Source: ESMA CEREP; tables transformed by Contraste';

/** What the known-truth families draw their paths from (contract.md section 2: the case computes the generator by EM
 * on S&P's pooled annual counts); the artifact's own source string is English only. */
export const GENERATOR_TEXT = {
  en: "the EM generator of S&P's pooled annual CEREP counts (riskvalidation.transitions.em)",
  es: 'el generador EM de los conteos anuales agrupados de S&P en CEREP (riskvalidation.transitions.em)',
} as const;

export interface AgencyFacts {
  code: string;
  entity: string;
  attribution: string;
  cohorts: number;
  first: string;
  last: string;
  semesters: number;
  /** the annual cohorts' sizes summed over years and grades: a rating counts once a year */
  ratings: number;
  /** the years whose default-rate page counts a different cohort from the transition page's (tab2_gap above 0) */
  tab2Gaps: number;
  homogeneity: C04Homogeneity;
  /** every annual cohort against the pooled matrix: how many reject at the policy's red threshold */
  reference: { red: number; total: number; alpha: number };
  d4Empty: { years: string[]; defaulted: number } | null;
  ttc: number | null;
  latest: number | null;
  l1: Record<GeneratorKey, number | null>;
}

/** The years whose transition page holds no rating in a default category, and the default page's rated defaulters in
 * them; null where the page has no default category at all (Moody's). */
export function d4EmptyYears(v: AgencyVariant): { years: string[]; defaulted: number } | null {
  const o = v.outputs;
  if (o.pd.d4 === null) return null;
  const empty = o.cohorts.filter((c) => c.counts.length > 0 && c.counts.every((row) => (row[N_GRADES] ?? 0) === 0));
  return { years: empty.map((c) => c.label), defaulted: empty.reduce((s, c) => s + sum(c.defaulted ?? []), 0) };
}

export function agencyFacts(v: AgencyVariant): AgencyFacts {
  const o = v.outputs;
  const ref = v.tests.filter((t) => t.test_id === 'rating.matrix_reference' && t.model_id === o.agency.code);
  const alpha = ref.find((t) => t.alpha_red !== null)?.alpha_red ?? 0.01;
  return {
    code: o.agency.code,
    entity: o.agency.name,
    attribution: o.attribution || ATTRIBUTION_FALLBACK,
    cohorts: o.cohorts.length,
    first: o.cohorts[0]?.label ?? '',
    last: o.cohorts[o.cohorts.length - 1]?.label ?? '',
    semesters: o.semesters.length,
    ratings: sum(o.cohorts.map((c) => sum(c.size))),
    tab2Gaps: o.cohorts.filter((c) => c.tab2_gap !== null && c.tab2_gap > 0).length,
    homogeneity: o.homogeneity.annual,
    reference: { red: ref.filter((t) => t.p_value !== null && t.p_value < alpha).length, total: ref.length, alpha },
    d4Empty: d4EmptyYears(v),
    ttc: v.impact.ttc_default_rate?.value ?? null,
    latest: v.impact.latest_default_rate?.value ?? null,
    l1: Object.fromEntries(GENERATOR_KEYS.map((k) => [k, o.generators[k]?.l1 ?? null])) as Record<GeneratorKey, number | null>,
  };
}

/** An impact item's value in its unit: probabilities and shares of EAD as percentages, a difference of probabilities
 * (a bias, a projection error) in signed percentage points, counts as whole numbers. */
export function impactValue(it: ImpactItem, lang: Lang): string {
  if (it.unit === 'probability' || it.unit === 'share of EAD') return pctText(lang, it.value);
  if (it.unit === 'probability difference') {
    return it.value === null ? formatNumber(null, lang) : `${it.value > 0 ? '+' : ''}${formatNumber(it.value * 100, lang, { digits: 3 })}\u00a0pp`;
  }
  if (it.unit === 'count') return formatNumber(it.value, lang, { decimals: 0 });
  return formatNumber(it.value, lang, { digits: 4 });
}

/** A family's design in words: repetitions, years and cohort sizes, or the exact enumeration of the thin family. */
export function familyDesign(f: FamilyVariant, lang: Lang): string {
  const o = f.outputs;
  const ladder = o.ladder ? `${pick(o.ladder.name, lang)}: ${o.ladder.values.map((x) => formatNumber(x, lang, { digits: 4 })).join('; ')}` : null;
  if (o.design.reps === 0) {
    return lang === 'es'
      ? `exacta por enumeración, un año, sin repeticiones${ladder ? `; ${ladder}` : ''}`
      : `exact by enumeration, one year, no repetitions${ladder ? `; ${ladder}` : ''}`;
  }
  const obligors = formatNumber(sum(o.generator.obligors), lang);
  return lang === 'es'
    ? `${formatNumber(o.design.reps, lang)} repeticiones de ${o.design.years} años de cohortes de ${obligors} deudores en siete grados${ladder ? `; ${ladder}` : '; sin escala: la cadena es de Markov'}`
    : `${formatNumber(o.design.reps, lang)} repetitions of ${o.design.years} years of cohorts of ${obligors} obligors in seven grades${ladder ? `; ${ladder}` : '; no ladder: the chain is Markov'}`;
}

/** Whether a recomputed value rounds to its print at the printed decimals. */
export const atPrintedDigits = (printed: number, recomputed: number, decimals: number): boolean => Math.abs(recomputed - printed) <= 0.5 * 10 ** -decimals + 1e-12;

/** Israel et al.'s three generators by the key the published variant stores. */
export const IRW_METHOD: Record<string, BiText> = {
  jlt: { en: 'JLT approximation', es: 'aproximación JLT' },
  diagonal: { en: 'diagonal adjustment', es: 'ajuste diagonal' },
  weighted: { en: 'weighted adjustment', es: 'ajuste ponderado' },
};
export const irwMethod = (key: string): BiText => IRW_METHOD[key] ?? key;

export interface PaperAgreement {
  id: 'irw' | 'sr190' | 'engelmann';
  name: BiText;
  agree: number;
  total: number;
  detail: BiText;
}

/** Each paper's printed values against their recomputation, counted from the published variant's outputs. */
export function paperAgreements(p: PublishedVariant): PaperAgreement[] {
  const o = p.outputs;
  const f = (x: number, lang: Lang, digits = 6) => formatNumber(x, lang, { digits });
  const irwOff = o.irw.rows.filter((r) => !r.agrees);
  const irwDetail = (lang: Lang) =>
    irwOff.length
      ? irwOff
          .map((r) =>
            lang === 'es'
              ? `${r.matrix}, ${pick(irwMethod(r.method), lang)}: impresa ${f(r.printed, lang)}, recalculada ${f(r.recomputed, lang)}${r.method === 'jlt' && r.matrix === o.irw.rows[0]?.matrix ? `; desde el generador impreso a cuatro dígitos, ${f(o.irw.jlt_from_printed_generator, lang)}` : ''}`
              : `${r.matrix}, ${pick(irwMethod(r.method), lang)}: printed ${f(r.printed, lang)}, recomputed ${f(r.recomputed, lang)}${r.method === 'jlt' && r.matrix === o.irw.rows[0]?.matrix ? `; from the printed four-digit generator, ${f(o.irw.jlt_from_printed_generator, lang)}` : ''}`,
          )
          .join('; ')
      : lang === 'es'
        ? 'todas a los dígitos impresos'
        : 'all at the printed digits';
  const nd = o.sr190.n_dagger;
  const ndAgree = nd.printed.filter((x, i) => atPrintedDigits(x, nd.recomputed[i], nd.decimals[i])).length;
  const e = o.engelmann;
  const checks: boolean[] = [
    ...e.w_ttc.printed.map((x, i) => atPrintedDigits(x, e.w_ttc.recomputed[i], e.w_ttc.decimals[i])),
    atPrintedDigits(e.ttc_pd.printed, e.ttc_pd.recomputed, e.ttc_pd.decimals),
    ...e.portfolios.filter((q) => q.pd0.check === 'printed digits').map((q) => atPrintedDigits(q.pd0.printed, q.pd0.recomputed, q.pd0.decimals)),
    ...e.portfolios.flatMap((q) => (q.extreme ? [atPrintedDigits(q.extreme.printed, q.extreme.recomputed, q.extreme.decimals)] : [])),
  ];
  const rounding = e.portfolios.filter((q) => q.pd0.check === 'entry rounding');
  return [
    {
      id: 'irw',
      name: { en: 'Israel, Rosenthal and Wei (2001): the L1 distances of the generators', es: 'Israel, Rosenthal y Wei (2001): las distancias L1 de los generadores' },
      agree: o.irw.rows.filter((r) => r.agrees).length,
      total: o.irw.rows.length,
      detail: { en: irwDetail('en'), es: irwDetail('es') },
    },
    {
      id: 'sr190',
      name: { en: 'Schuermann and Hanson (2004), Table 5: the analytical intervals', es: 'Schuermann y Hanson (2004), Tabla 5: los intervalos analíticos' },
      agree: o.sr190.rows.filter((r) => r.agrees).length,
      total: o.sr190.rows.length,
      detail: {
        en: `${o.sr190.defaults} defaults of ${formatNumber(o.sr190.n, 'en')}; N† printed ${nd.printed.map((x) => f(x, 'en', 4)).join(', ')}, recomputed ${nd.recomputed.map((x) => f(x, 'en', 4)).join(', ')} (${ndAgree} of ${nd.printed.length} at the printed digits)`,
        es: `${o.sr190.defaults} incumplimientos de ${formatNumber(o.sr190.n, 'es')}; N† impreso ${nd.printed.map((x) => f(x, 'es', 4)).join('; ')}, recalculado ${nd.recomputed.map((x) => f(x, 'es', 4)).join('; ')} (${ndAgree} de ${nd.printed.length} a los dígitos impresos)`,
      },
    },
    {
      id: 'engelmann',
      name: { en: 'Engelmann (2024), section 4: the TTC portfolio and the projections', es: 'Engelmann (2024), sección 4: la cartera TTC y las proyecciones' },
      agree: checks.filter(Boolean).length,
      total: checks.length,
      detail: {
        en: `TTC PD printed ${pctText('en', e.ttc_pd.printed, 4)}, recomputed ${pctText('en', e.ttc_pd.recomputed, 5)}${rounding.length ? `; ${rounding.map((q) => `${q.name} is judged within the rounding of its printed entries${q.pd0.note ? ` (${q.pd0.note.en})` : ''}`).join('; ')}` : ''}`,
        es: `PD TTC impresa ${pctText('es', e.ttc_pd.printed, 4)}, recalculada ${pctText('es', e.ttc_pd.recomputed, 5)}${rounding.length ? `; ${rounding.map((q) => `${q.name} se juzga dentro del redondeo de sus entradas impresas${q.pd0.note ? ` (${q.pd0.note.es})` : ''}`).join('; ')}` : ''}`,
      },
    },
  ];
}

// ---------------------------------------------------------------------------------------------------------------------
// the findings' words and order

export const SEVERITY_TEXT: Record<string, BiText> = {
  S1: { en: 'S1 critical', es: 'S1 crítico' },
  S2: { en: 'S2 significant', es: 'S2 significativo' },
  S3: { en: 'S3 moderate', es: 'S3 moderado' },
  S4: { en: 'S4 minor', es: 'S4 menor' },
};
export const STATUS_TEXT: Record<string, BiText> = {
  open: { en: 'open', es: 'abierto' },
  accepted: { en: 'accepted (a stated limit)', es: 'aceptado (un límite declarado)' },
  closed: { en: 'closed', es: 'cerrado' },
};
const SEVERITY_ORDER = ['S1', 'S2', 'S3', 'S4'];

/** The findings by severity, the most severe first (the artifact's order within a severity). */
export function sortFindings(findings: readonly Finding[]): Finding[] {
  return [...findings].sort((a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity));
}

/** The transition tests by their riskvalidation id. */
export const TEST_NAME: Record<string, BiText> = {
  'rating.time_homogeneity': { en: 'Time homogeneity', es: 'Homogeneidad temporal' },
  'rating.matrix_reference': { en: 'Cohort against the pooled matrix', es: 'Cohorte contra la matriz agrupada' },
  'rating.markov_order': { en: 'Markov order', es: 'Orden de Markov' },
  'rating.momentum': { en: 'Momentum hazard', es: 'Riesgo de momentum' },
  'rating.migration_ztests': { en: 'ECB migration z-tests', es: 'Pruebas z de migración del BCE' },
  'rating.mwb': { en: 'ECB migration bandwidth', es: 'Ancho de banda de migración del BCE' },
};
export const testName = (id: string): BiText => TEST_NAME[id] ?? { en: id, es: id };

export const TRUTH_TEXT: Record<string, BiText> = {
  'real-outcomes': { en: 'real outcomes', es: 'resultados reales' },
  'synthetic-known-truth': { en: 'synthetic, known truth', es: 'sintético, verdad conocida' },
  'synthetic-calibrated': { en: 'synthetic, calibrated', es: 'sintético, calibrado' },
  'published-answer': { en: 'published answer', es: 'respuesta publicada' },
};

// ---------------------------------------------------------------------------------------------------------------------
// the results

function AgencyItem({ v, manifest }: { v: AgencyVariant; manifest: CaseManifest }) {
  const lang = useShellLang();
  const o = v.outputs;
  const a = agencyFacts(v);
  const ccc = N_GRADES - 1;
  const b = N_GRADES - 2;
  const d4 = o.lra.d4;
  const gap = o.definition_gap.d4_over_d2;
  const sameDefaults = o.lra.d3.defaults.every((d, i) => d === o.lra.d2.defaults[i]);
  const f = (x: number | null | undefined, digits = 4) => formatNumber(x, lang, { digits });
  const l1 = GENERATOR_KEYS.filter((k) => a.l1[k] !== null);
  const L1_NAME: Record<GeneratorKey, BiText> = { em: 'EM', diagonal: { en: 'diagonal', es: 'diagonal' }, weighted: { en: 'weighted', es: 'ponderado' }, jlt: 'JLT' };
  const en = [
    `${a.cohorts} annual cohorts from ${a.first} to ${a.last} and ${a.semesters} semesters; ${formatNumber(a.ratings, 'en')} ratings over the annual cohorts (a rating counts once a year).`,
    `The default-rate page counts a different cohort from the transition page's in ${a.tab2Gaps} of ${a.cohorts} years.`,
    d4
      ? `Long-run average PD of ${GRADES[ccc]}: ${pctText('en', o.lra.d2.rate[ccc])} under D2 and ${pctText('en', d4.rate[ccc])} under D4 (pooled D4/D2 ${f(gap?.[ccc] ?? null, 3)}); of ${GRADES[b]}: ${pctText('en', o.lra.d2.rate[b])} and ${pctText('en', d4.rate[b])} (${f(gap?.[b] ?? null, 3)}).`
      : `Long-run average PD of ${GRADES[ccc]}: ${pctText('en', o.lra.d2.rate[ccc])} under D2; of ${GRADES[b]}: ${pctText('en', o.lra.d2.rate[b])}. The transition page has no default category, so D4 and Keep do not exist.`,
    sameDefaults
      ? `D3 counts the same defaults as D2 in every grade; its rate differs by its cohort only (${GRADES[ccc]}: ${pctText('en', o.lra.d3.rate[ccc])}).`
      : `D3 counts ${o.lra.d3.defaults[ccc]} defaults in ${GRADES[ccc]} against D2's ${o.lra.d2.defaults[ccc]}.`,
    `Time homogeneity across the annual cohorts: chi-square ${formatNumber(a.homogeneity.statistic, 'en', { decimals: 0 })} on ${formatNumber(a.homogeneity.dof, 'en')} degrees of freedom, ${pText('en', a.homogeneity.p_value)}; ${a.reference.red} of ${a.reference.total} cohorts depart from the pooled matrix at ${formatNumber(a.reference.alpha, 'en', { percent: true, decimals: 0 })}.`,
    `L1 distance of each generator's one-year matrix to the pooled matrix: ${l1.map((k) => `${pick(L1_NAME[k], 'en')} ${f(a.l1[k], 3)}`).join(', ')}.`,
    a.d4Empty && a.d4Empty.years.length
      ? `The transition page's default column is empty in the years ${yearRanges(a.d4Empty.years, 'en')} while the default page counts ${formatNumber(a.d4Empty.defaulted, 'en')} rated defaulters in those years.`
      : '',
    a.ttc !== null ? `The pooled matrix's TTC portfolio defaults at ${pctText('en', a.ttc)} a year (Engelmann 2024); the latest cohort's mix under the same matrix at ${pctText('en', a.latest)}.` : '',
  ];
  const es = [
    `${a.cohorts} cohortes anuales de ${a.first} a ${a.last} y ${a.semesters} semestres; ${formatNumber(a.ratings, 'es')} calificaciones en las cohortes anuales (una calificación cuenta una vez por año).`,
    `La página de tasas de incumplimiento cuenta una cohorte distinta de la de la página de transiciones en ${a.tab2Gaps} de ${a.cohorts} años.`,
    d4
      ? `PD promedio de largo plazo de ${GRADES[ccc]}: ${pctText('es', o.lra.d2.rate[ccc])} con D2 y ${pctText('es', d4.rate[ccc])} con D4 (D4/D2 agrupada ${f(gap?.[ccc] ?? null, 3)}); de ${GRADES[b]}: ${pctText('es', o.lra.d2.rate[b])} y ${pctText('es', d4.rate[b])} (${f(gap?.[b] ?? null, 3)}).`
      : `PD promedio de largo plazo de ${GRADES[ccc]}: ${pctText('es', o.lra.d2.rate[ccc])} con D2; de ${GRADES[b]}: ${pctText('es', o.lra.d2.rate[b])}. La página de transiciones no tiene categoría de incumplimiento, así que no existen ni D4 ni Con retiros.`,
    sameDefaults
      ? `D3 cuenta los mismos incumplimientos que D2 en cada grado; su tasa difiere solo por su cohorte (${GRADES[ccc]}: ${pctText('es', o.lra.d3.rate[ccc])}).`
      : `D3 cuenta ${o.lra.d3.defaults[ccc]} incumplimientos en ${GRADES[ccc]} contra ${o.lra.d2.defaults[ccc]} de D2.`,
    `Homogeneidad temporal entre las cohortes anuales: chi-cuadrado ${formatNumber(a.homogeneity.statistic, 'es', { decimals: 0 })} con ${formatNumber(a.homogeneity.dof, 'es')} grados de libertad, ${pText('es', a.homogeneity.p_value)}; ${a.reference.red} de ${a.reference.total} cohortes se apartan de la matriz agrupada al ${formatNumber(a.reference.alpha, 'es', { percent: true, decimals: 0 })}.`,
    `Distancia L1 de la matriz anual de cada generador a la matriz agrupada: ${l1.map((k) => `${pick(L1_NAME[k], 'es')} ${f(a.l1[k], 3)}`).join(', ')}.`,
    a.d4Empty && a.d4Empty.years.length
      ? `La columna de incumplimiento de la página de transiciones está vacía en los años ${yearRanges(a.d4Empty.years, 'es')} mientras la página de incumplimientos cuenta ${formatNumber(a.d4Empty.defaulted, 'es')} calificaciones incumplidas en esos años.`
      : '',
    a.ttc !== null ? `La cartera TTC de la matriz agrupada incumple ${pctText('es', a.ttc)} al año (Engelmann 2024); la mezcla de la última cohorte con la misma matriz, ${pctText('es', a.latest)}.` : '',
  ];
  return (
    <li data-variant={v.variant_id}>
      <strong>{pick(shortOf(manifest, v.variant_id), lang)}</strong> ({a.entity}, {a.code}): {(lang === 'es' ? es : en).filter(Boolean).join(' ')}
    </li>
  );
}

/** The agencies' long-run averages by grade under every definition each one's pages give (D2, D3, D4). */
function LraTable({ agencies, manifest }: { agencies: AgencyVariant[]; manifest: CaseManifest }) {
  const lang = useShellLang();
  const cols = agencies.flatMap((v) =>
    (['d2', 'd3', 'd4'] as const).flatMap((d) => {
      const lra = v.outputs.lra[d];
      return lra ? [{ key: `${v.variant_id}-${d}`, v, d, lra }] : [];
    }),
  );
  return (
    <div className="ct-scroll">
      <table className="caos-table ct-wrap-head" data-table="results-lra">
        <thead>
          <tr>
            <th className="ct-text">{pick({ en: 'Grade', es: 'Grado' }, lang)}</th>
            {cols.map((c) => (
              <th key={c.key} title={pick(DEFINITION_LABEL[c.d], lang)}>
                {`${pick(shortOf(manifest, c.v.variant_id), lang)} ${c.d.toUpperCase()}`}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {GRADES.map((g, i) => (
            <tr key={g} data-grade={g}>
              <td className="ct-text">{g}</td>
              {cols.map((c) => (
                <td key={c.key}>{pctText(lang, c.lra.rate[i])}</td>
              ))}
            </tr>
          ))}
          <tr data-row="cohorts">
            <td className="ct-text">{pick({ en: 'Cohorts (CCC-C)', es: 'Cohortes (CCC-C)' }, lang)}</td>
            {cols.map((c) => (
              <td key={c.key}>{formatNumber(c.lra.cohorts[N_GRADES - 1], lang)}</td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
}

export function C04Results({ manifest }: { manifest: CaseManifest }) {
  const lang = useShellLang();
  const all = useC04Variants(manifest);
  if (all.state === 'loading') return <Pending label={{ en: 'Loading the measured results', es: 'Cargando los resultados medidos' }} />;
  if (all.state === 'error') return <LoadError error={all.error} />;
  const { agencies, families, published } = kindsOf(all.data);
  const t = (en: string, es: string) => (lang === 'es' ? es : en);
  const attribution = agencies[0]?.outputs.attribution || ATTRIBUTION_FALLBACK;
  return (
    <div data-state="ready" data-results={manifest.case_id}>
      <h3>{t('Measured: the agencies', 'Medido: las agencias')}</h3>
      <p>
        {t(
          `Read from this release's artifacts (pipeline ${manifest.engine.pipeline}, riskvalidation ${manifest.engine.riskvalidation ?? ''}): CEREP's corporate long-term ratings by category, one-year cohorts, each agency's EU entity as ESMA computes its statistics. Every PD names its definition: D2 the default-rate page, D3 the defaults page, D4 the transition page's default column. ${attribution}.`,
          `Leído desde los artefactos de esta versión (pipeline ${manifest.engine.pipeline}, riskvalidation ${manifest.engine.riskvalidation ?? ''}): las calificaciones corporativas de largo plazo por categoría de CEREP, cohortes de un año, la entidad UE de cada agencia como ESMA calcula sus estadísticas. Cada PD nombra su definición: D2 la página de tasas de incumplimiento, D3 la página de incumplimientos, D4 la columna de incumplimiento de la página de transiciones. ${attribution}.`,
        )}{' '}
        {pick(ESMA_DEFINITIONS, lang)}
      </p>
      <ul data-results="agencies">
        {agencies.map((v) => (
          <AgencyItem key={v.variant_id} v={v} manifest={manifest} />
        ))}
      </ul>
      <p>
        {t(
          'The long-run average one-year PD by grade (EBA/GL/2017/16 paragraph 84: the mean of the yearly rates over the cohorts where the grade has ratings), under every definition each agency\'s pages give:',
          'La PD anual promedio de largo plazo por grado (párrafo 84 de EBA/GL/2017/16: la media de las tasas anuales sobre las cohortes donde el grado tiene calificaciones), con cada definición que dan las páginas de cada agencia:',
        )}
      </p>
      <LraTable agencies={agencies} manifest={manifest} />
      <h3>{t('Measured: the known-truth families', 'Medido: las familias de verdad conocida')}</h3>
      <p>
        {t(
          `Rating paths drawn by riskvalidation's RatingPaths from ${GENERATOR_TEXT.en}, so every error is measured against a truth that is known (${attribution}).`,
          `Trayectorias de calificación generadas por RatingPaths de riskvalidation desde ${GENERATOR_TEXT.es}, así que cada error se mide contra una verdad conocida (${attribution}).`,
        )}
      </p>
      <ul data-results="families">
        {families.map((f) => (
          <li key={f.variant_id} data-variant={f.variant_id}>
            <strong>{pick(shortOf(manifest, f.variant_id), lang)}</strong> ({pick(titleOf(manifest, f.variant_id), lang)}; {familyDesign(f, lang)}):{' '}
            {Object.values(f.impact)
              .map((it) => `${pick(it.label, lang)}: ${impactValue(it, lang)}`)
              .join('; ')}
            .
          </li>
        ))}
      </ul>
      {published && (
        <>
          <h3>{t('Measured: the papers recomputed', 'Medido: los artículos recalculados')}</h3>
          <ul data-results="papers">
            {paperAgreements(published).map((p) => (
              <li key={p.id} data-paper={p.id}>
                <strong>{pick(p.name, lang)}</strong>: {t(`${p.agree} of ${p.total} printed values recomputed at the printed digits`, `${p.agree} de ${p.total} valores impresos recalculados a los dígitos impresos`)}; {pick(p.detail, lang)}.
              </li>
            ))}
          </ul>
        </>
      )}
      <h3>{t('The findings of every variant', 'Los hallazgos de cada variante')}</h3>
      <ul data-results="findings">
        {all.data.map((v) => (
          <li key={v.variant_id} data-variant={v.variant_id}>
            <strong>{pick(shortOf(manifest, v.variant_id), lang)}</strong> ({pick(TRUTH_TEXT[v.provenance.truth_status] ?? { en: v.provenance.truth_status, es: v.provenance.truth_status }, lang)})
            <ul>
              {sortFindings(v.findings).map((f) => (
                <li key={f.id} data-finding={f.id}>
                  {pick(SEVERITY_TEXT[f.severity] ?? { en: f.severity, es: f.severity }, lang)}, {pick(STATUS_TEXT[f.status] ?? { en: f.status, es: f.status }, lang)}: {pick(f.title, lang)}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </div>
  );
}
