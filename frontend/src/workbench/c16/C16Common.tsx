// C16's tests, Findings, Variants and Context groups, and the live read-outs of its rail (ADR-0017 rule 3: every section
// shows a value that moves with its controls). The Findings card and the fixture notice are the ones C06 and C07 use.
// What every view says, whatever the variant: the LCR is a Basel formula applied to call-report aggregates and never the
// bank's reported or regulatory ratio; the aggregates are real, the behaviour and the deposits are synthetic; the realised
// run has two denominators; every named parameter is a convention; a survival period is a day or "survives the horizon".
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import type { CSSProperties, ReactNode } from 'react';
import { loadAllVariants, useArtifact, type CaseData } from '../../api/artifacts';
import type { TestRow, VariantArtifact } from '../../lib/contract.types';
import { LIGHT_TEXT } from '../../lib/policy';
import { FindingsCard, FixtureNotice } from '../c06/C06Common';
import { ChartOverTable } from '../c06/format';
import { Pending } from '../Pending';
import { LiveReadout, useCard, type Bi } from '../c03/U6Shared';
import { UnavailableCard } from '../c14/C14Common';
import { bankName, es, nameOf } from './localise';
import {
  BASE_TEXT, CLASS_TEXT, COMPARED_AT_TEXT, DENOMINATOR_LONG, DENOMINATOR_SHORT, HAIRCUT_RULE_TEXT, ROLE_TEXT, SEGMENT_TEXT, SOURCE_KIND_TEXT,
  amount, axisOf, baseOf, denominatorOf, dayIndex, fitOf, ladderOf, outputsOf, reverseOf, rowOf, survivalDay, survivalText, text, scenarioPhrase,
  type C16Fit, type C16Outputs, type C16Reverse, type C16Sel, type C16Survival,
} from './selection';
import { testText } from '../names';

type Lang = 'en' | 'es';
const NA: BiText = { en: formatNumber(null, 'en'), es: formatNumber(null, 'es') };
export const SHARE = (v: number | null | undefined, lang: Lang) => formatNumber(v, lang, { percent: true, decimals: 2 });
/** A whole amount; a value that rounds to zero is 0, never "-0" (U16-R2 b08 m3). */
export const cell = (v: number | null | undefined, lang: Lang) => formatNumber(v === null || v === undefined ? v : Math.round(v) + 0, lang, { decimals: 0 });
export const digits = (v: number | null | undefined, lang: Lang) => formatNumber(v, lang, { digits: 4 });

/**
 * A drawing of a fixed height above a long block of tables and notes that scrolls under it: for the views whose tables are
 * the larger part of what they say (the LCR, the HTM loss, the run-off scoring, the time block, the CBC), where the
 * drawing taking the height the tables leave would leave the tables a sliver. The gate measures the drawing's box.
 */
export function ChartAbove({ chart, children, chartHeight = '15rem' }: { chart: ReactNode; children?: ReactNode; chartHeight?: string }) {
  return (
    <div className="ct-stack">
      <div className="ct-stack-fixed" style={{ minHeight: chartHeight, '--ct-chart-min': chartHeight } as CSSProperties}>{chart}</div>
      {children ? <div className="ct-stack-rest">{children}</div> : null}
    </div>
  );
}

/** The unit of a column of the documents' money: USD thousands as the FDIC call report gives it. */
export const MONEY_UNIT: Bi = { en: 'USD thousands', es: 'miles de USD' };

/** The words an absent block says when the view is given a document of the other kind. */
export const NOT_SCENARIO: BiText = { en: 'Not available: this document is the reverse-stress document, which has no scenario ladder.', es: 'No disponible: este documento es el de la prueba de estrés inversa, que no tiene la escalera de escenarios.' };
export const NOT_REVERSE: BiText = { en: 'Not available: this document is a scenario variant; the reverse stress is its own document.', es: 'No disponible: este documento es una variante de escenario; la prueba de estrés inversa es un documento aparte.' };

/** The survival period as a sentence: the day, or the horizon it survived, never a number for the second. */
export function survivalSentence(s: Pick<C16Survival, 'kind' | 'day' | 'horizon_days'> | null | undefined, lang: Lang): string {
  if (!s) return formatNumber(null, lang);
  if (s.kind === 'day' && s.day !== null) {
    return lang === 'es' ? `Periodo de supervivencia: día ${s.day}, el primer día en que la posición neta de liquidez (NLP) pasa a negativa.` : `Survival period: day ${s.day}, the first day on which the net liquidity position (NLP) turns negative.`;
  }
  return lang === 'es'
    ? `Sobrevive el horizonte de ${s.horizon_days} días: la NLP no pasa a negativa dentro de él, así que no hay un día de supervivencia que mostrar.`
    : `Survives the ${s.horizon_days}-day horizon: the NLP does not turn negative inside it, so there is no survival day to state.`;
}

/** The survival cell of a table: the words, with the kind and the day in data attributes (the day only when there is one). */
export function SurvivalCell({ s, className }: { s: C16Survival | null | undefined; className?: string }) {
  const lang = useShellLang();
  const day = survivalDay(s);
  return (
    <td className={className} data-survival-kind={s?.kind} {...(day !== null ? { 'data-survival-day': String(day) } : {})} data-na={s ? undefined : 'true'}>
      {survivalText(s, lang)}
    </td>
  );
}

// --- the tests table -------------------------------------------------------------------------------------------------

/** The words of the tests the liquidity engine returns for C16; an id without an entry is shown as it is. */
const TEST_TEXT: Record<string, BiText> = {
  'liq.list_compounding_golden': { en: 'The LiST compounding example reproduced', es: 'Ejemplo de composición de LiST reproducido' },
  'liq.cbc_haircut_rules': { en: 'CBC haircut rules applied as specified', es: 'Reglas de recorte del CBC aplicadas como se especifican' },
  'liq.runoff_adequacy_back_test': { en: 'The back-test of the run-off against the realised run', es: 'El backtest de la salida de depósitos contra la corrida realizada' },
  'liq.nlp_identity': { en: 'NLP identity on the ladder', es: 'Identidad de la NLP en la escalera' },
  'liq.cliff_effect_diagnostic': { en: 'Cliff-effect diagnostic', es: 'Diagnóstico del efecto acantilado' },
  'liq.runoff_vs_generator_truth': { en: 'Run-off against the generator truth', es: 'Salida de depósitos contra la verdad del generador' },
  'liq.survival_monotone_in_severity': { en: 'Survival period shortens with severity', es: 'El periodo de supervivencia se acorta con la severidad' },
  'liq.uninsured_share_sensitivity': { en: 'Sensitivity to the uninsured share', es: 'Sensibilidad a la parte no asegurada' },
  'liq.htm_loss_effect': { en: 'Effect of the HTM unrealised loss on the CBC', es: 'Efecto de la pérdida no realizada HTM en el CBC' },
  'liq.htm_revaluation_vs_reported': { en: 'HTM revaluation against the reported fair value', es: 'Revaluación HTM contra el valor razonable reportado' },
  'liq.reverse_stress_round_trip': { en: 'Reverse stress: the solved multiplier returns the target', es: 'Estrés inverso: el multiplicador resuelto devuelve el objetivo' },
};
const SEGMENT_NAMES: Record<string, Bi> = { ...DENOMINATOR_SHORT, ...BASE_TEXT };

/** The rows the engine returned for the tests of this variant; a test that did not run shows its reason, not a number. */
export function C16TestsView({ sel }: { sel: C16Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  if (!sel) return <Pending />;
  const rows: TestRow[] = sel.data.variant.tests;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The tests of the liquidity model', es: 'Las pruebas del modelo de liquidez' }}
        {...card}
        note={{
          en: 'The statistic when the test ran, the light under the stated convention and its reference. The lights are conventions of the case, never regulatory thresholds; a test that did not run says why and shows no number.',
          es: 'El estadístico cuando la prueba corrió, la luz bajo la convención declarada y su referencia. Las luces son convenciones del caso, nunca umbrales regulatorios; una prueba que no corrió dice por qué y no muestra número.',
        }}
      >
        {rows.length === 0 ? (
          <p className="ct-note" data-state="unavailable">{pick({ en: 'This variant carries no test row.', es: 'Esta variante no trae filas de pruebas.' }, lang)}</p>
        ) : (
          <div className="ct-scroll">
            <table className="caos-table ct-wrap-head" data-table="tests">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Test', es: 'Prueba' }, lang)}</th>
                  <th className="ct-text ct-wide-only ct-repeated">{pick({ en: 'Against', es: 'Contra' }, lang)}</th>
                  <th>{pick({ en: 'Statistic', es: 'Estadístico' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Light', es: 'Luz' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Reason or note', es: 'Razón o nota' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((t, i) => {
                  const ran = t.light !== 'not_evaluated' && t.light !== 'error';
                  return (
                    <tr key={`${t.test_id}-${t.segment}-${i}`} data-test={t.test_id} data-light={t.light}>
                      <td className="ct-text" title={t.test_id}>
                        {pick(TEST_TEXT[t.test_id] ?? testText(t.test_id), lang)}
                        {t.segment === null ? null : <span className="ct-narrow-only" data-segment={t.segment}>{pick(text(SEGMENT_NAMES, t.segment), lang)}</span>}
                      </td>
                      <td className="ct-text ct-wide-only ct-repeated">{t.segment === null ? formatNumber(null, lang) : pick(text(SEGMENT_NAMES, t.segment), lang)}</td>
                      <td data-na={ran && t.statistic !== null ? undefined : 'true'}>{ran && t.statistic !== null ? formatNumber(t.statistic, lang, { digits: 4 }) : formatNumber(null, lang)}</td>
                      <td className={`ct-text ct-light ct-light-${t.light}`}>
                        <span className="ct-light-word">{pick(LIGHT_TEXT[t.light], lang)}</span>
                      </td>
                      <td className="ct-text">{es(t.notes ? t.notes : t.reference, lang)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </PlotCard>
    </ViewsRow>
  );
}

export function C16FindingsView({ sel }: { sel: C16Sel | null }) {
  if (!sel) return <Pending />;
  return (
    <ViewsRow>
      <FindingsCard variant={sel.data.variant} />
    </ViewsRow>
  );
}

// --- the variants -----------------------------------------------------------------------------------------------------

export interface MedianRef {
  adverse: number;
  extreme: number;
  nBanks: number;
}

/** The survival period of each variant that has a daily path, with the LiST medians as reference bars, and the variants in a table. */
export function C16VariantsTable({ variants, onPick, current, medians, reverse }: { variants: Array<{ id: string; title: BiText; v: VariantArtifact<C16Outputs> }>; onPick: (id: string) => void; current: string; medians?: MedianRef | null; reverse?: VariantArtifact<C16Reverse> | null }) {
  const lang = useShellLang();
  const first = variants[0]?.v;
  const card = useCard(first as unknown as VariantArtifact | undefined);
  const bars = variants.flatMap(({ id, title, v }) => {
    const d = survivalDay(v.outputs.path?.survival);
    return d === null ? [] : [{ id, label: title, value: d, tone: 'accent' as const, highlight: id === current }];
  });
  const refs = medians
    ? [
        { id: 'median-adverse', label: { en: `LiST median, Adverse (${medians.nBanks} banks)`, es: `Mediana LiST, Adverso (${medians.nBanks} bancos)` }, value: medians.adverse, tone: 'neutral' as const, hint: { en: 'A published reference point, not a model result', es: 'Un punto de referencia publicado, no un resultado del modelo' } },
        { id: 'median-extreme', label: { en: `LiST median, Extreme (${medians.nBanks} banks)`, es: `Mediana LiST, Extremo (${medians.nBanks} bancos)` }, value: medians.extreme, tone: 'neutral' as const, hint: { en: 'A published reference point, not a model result', es: 'Un punto de referencia publicado, no un resultado del modelo' } },
      ]
    : [];
  const survivors = variants.filter(({ v }) => v.outputs.path && survivalDay(v.outputs.path.survival) === null);
  return (
    <PlotCard
      fill
      title={{ en: 'The variants of the case', es: 'Las variantes del caso' }}
      {...card}
      note={{
        en: 'The five variants of the SDD at the last call report before the run. The bars give the survival period of each variant that has a daily path and one that is reached; a variant that survives its horizon is in the table with its horizon and has no bar, and the LCR gives a ratio and no daily path. Pick a variant to load it.',
        es: 'Las cinco variantes del SDD en el último reporte de llamada antes de la corrida. Las barras dan el periodo de supervivencia de cada variante con trayectoria diaria que lo alcanza; una variante que sobrevive su horizonte está en la tabla con su horizonte y no tiene barra, y el LCR da una razón y no una trayectoria diaria. Elija una variante para cargarla.',
      }}
    >
      <ChartOverTable
        chartMin="17rem"
        chart={
          <BarChart
            title={{ en: 'Survival period by variant, in days', es: 'Periodo de supervivencia por variante, en días' }}
            height="fill"
            orientation="horizontal"
            data={[...bars, ...refs]}
            axis={{ label: { en: 'Survival period: the first day on which the NLP turns negative', es: 'Periodo de supervivencia: el primer día en que la NLP pasa a negativa' }, unit: { en: 'days', es: 'días' }, format: { decimals: 0 } }}
          />
        }
      >
        <table className="caos-table ct-wrap-head" data-table="variants-c16">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Variant', es: 'Variante' }, lang)}</th>
              <th className="ct-text ct-wide-only">{pick({ en: 'Scenario', es: 'Escenario' }, lang)}</th>
              <th>{pick({ en: 'Horizon (days)', es: 'Horizonte (días)' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Survival period', es: 'Periodo de supervivencia' }, lang)}</th>
              <th>{pick({ en: 'LCR, Basel formula', es: 'LCR, fórmula de Basilea' }, lang)}</th>
              <th className="ct-wide-only">{pick({ en: 'Modelled outflow of the model base', es: 'Salida modelada de la base del modelo' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {variants.map(({ id, title, v }) => {
              const o = v.outputs;
              const run = o.scoring.modelled_outflow.at_event_horizon ?? o.scoring.modelled_outflow.at_model_horizon;
              return (
                <tr key={id} data-variant={id} className={id === current ? 'ct-current' : undefined}>
                  <td className="ct-text">
                    <button type="button" className="ct-linkbutton" onClick={() => onPick(id)}>{pick(title, lang)}</button>
                  </td>
                  <td className="ct-text ct-wide-only">{scenarioPhrase(o.variant.scenario_family, o.variant.phase, lang)}</td>
                  <td>{o.variant.horizon_days}</td>
                  {o.path ? <SurvivalCell s={o.path.survival} className="ct-text" /> : <td className="ct-text" data-na="true">{formatNumber(null, lang)}</td>}
                  <td data-na={o.lcr ? undefined : 'true'}>{o.lcr ? SHARE(o.lcr.ratio, lang) : formatNumber(null, lang)}</td>
                  <td className="ct-wide-only">{`${SHARE(run.share_of_model_base, lang)} ${pick({ en: `in ${run.horizon_days} days`, es: `en ${run.horizon_days} días` }, lang)}`}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {reverse ? <C16ReverseTable reverse={reverse} current={current} onPick={onPick} /> : null}
        {survivors.length > 0 ? (
          <p className="ct-note" data-state="survives">
            {pick(
              {
                en: `Survives its horizon, no survival day: ${survivors.map(({ title, v }) => `${pick(title, 'en')} (${v.outputs.variant.horizon_days} days)`).join(', ')}.`,
                es: `Sobrevive su horizonte, sin día de supervivencia: ${survivors.map(({ title, v }) => `${pick(title, 'es')} (${v.outputs.variant.horizon_days} días)`).join(', ')}.`,
              },
              lang,
            )}
          </p>
        ) : null}
      </ChartOverTable>
    </PlotCard>
  );
}

/** The reverse-stress document as a table under the variants: the multiplier at which each base scenario first falls to the target. */
function C16ReverseTable({ reverse, current, onPick }: { reverse: VariantArtifact<C16Reverse>; current: string; onPick: (id: string) => void }) {
  const lang = useShellLang();
  const r = reverse.outputs;
  return (
    <table className="caos-table ct-wrap-head" data-table="variants-c16-reverse" data-variant={reverse.variant_id}>
      <thead>
        <tr>
          <th className="ct-text">
            <button type="button" className="ct-linkbutton" onClick={() => onPick(reverse.variant_id)}>{pick({ en: 'Reverse stress: base scenario', es: 'Estrés inverso: escenario base' }, lang)}</button>
          </th>
          <th className="ct-text">{pick({ en: 'Survival period of the base', es: 'Periodo de supervivencia de la base' }, lang)}</th>
          <th>{pick({ en: `Multiplier for ${r.target.days} days`, es: `Multiplicador para ${r.target.days} días` }, lang)}</th>
        </tr>
      </thead>
      <tbody>
        {r.bases.map((b) => (
          <tr key={b.base_id} data-base={b.base_id} className={reverse.variant_id === current ? 'ct-current' : undefined}>
            <td className="ct-text">{pick(b.label, lang)}</td>
            <SurvivalCell s={b.base_survival} className="ct-text" />
            <td data-na={b.solved.status === 'solved' ? undefined : 'true'}>{b.solved.status === 'solved' ? digits(b.solved.multiplier, lang) : formatNumber(null, lang)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function C16VariantsView({ sel, onPick }: { sel: C16Sel | null; onPick: (id: string) => void }) {
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  if (!sel || all.state !== 'ready') return <Pending />;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const docs = all.data as unknown as Array<VariantArtifact<C16Outputs | C16Reverse>>;
  const scenarios = docs
    .filter((v) => v.outputs.kind === 'scenario')
    .map((v) => ({ id: v.variant_id, title: entries.find((e) => e.variant_id === v.variant_id)?.short_title ?? (v.outputs as C16Outputs).variant.label, v: v as VariantArtifact<C16Outputs> }));
  const reverse = docs.find((v) => v.outputs.kind === 'reverse-stress') as VariantArtifact<C16Reverse> | undefined;
  const annex = fitOf(sel)?.list_parameters.results_annex;
  const medians = annex ? { adverse: annex.median_survival_days.adverse, extreme: annex.median_survival_days.extreme, nBanks: annex.n_banks } : null;
  return (
    <ViewsRow>
      <C16VariantsTable variants={scenarios} onPick={onPick} current={sel.data.variant.variant_id} medians={medians} reverse={reverse ?? null} />
    </ViewsRow>
  );
}

// --- the context ------------------------------------------------------------------------------------------------------

type Conventions = C16Outputs['conventions'];
type Scalar = Conventions['event_horizon_days'];
type Grid = Conventions['uninsured_share_grid'];

const CONVENTION_TEXT: Record<string, Bi> = {
  event_horizon_days: { en: 'Event horizon of the run', es: 'Horizonte del evento de la corrida' },
  reverse_target_days: { en: 'Target of the reverse stress', es: 'Objetivo de la prueba de estrés inversa' },
  list_compounding_tolerance: { en: 'Tolerance of the LiST compounding example', es: 'Tolerancia del ejemplo de composición de LiST' },
  monotonicity_tolerance_days: { en: 'Tolerance of the monotonicity test', es: 'Tolerancia de la prueba de monotonía' },
  nlp_identity_tolerance: { en: 'Tolerance of the NLP identity', es: 'Tolerancia de la identidad de la NLP' },
  cliff_amber_threshold: { en: 'Cliff effect, amber threshold', es: 'Efecto acantilado, umbral ámbar' },
  cliff_red_threshold: { en: 'Cliff effect, red threshold', es: 'Efecto acantilado, umbral rojo' },
  scoring_ratio_green: { en: 'Scoring ratio, green', es: 'Razón de evaluación, verde' },
  scoring_ratio_amber: { en: 'Scoring ratio, amber', es: 'Razón de evaluación, ámbar' },
  generator_truth_se_green: { en: 'Generator truth, green (standard errors)', es: 'Verdad del generador, verde (errores estándar)' },
  generator_truth_se_red: { en: 'Generator truth, red (standard errors)', es: 'Verdad del generador, rojo (errores estándar)' },
  htm_revaluation_green: { en: 'HTM revaluation, green', es: 'Revaluación HTM, verde' },
  htm_revaluation_amber: { en: 'HTM revaluation, amber', es: 'Revaluación HTM, ámbar' },
  round_trip_tolerance_days: { en: 'Tolerance of the reverse-stress round trip', es: 'Tolerancia del viaje de ida y vuelta del estrés inverso' },
  cbc_haircut_band: { en: 'Width of the CBC haircut band', es: 'Ancho de la banda de recorte del CBC' },
  contractual_bucket_edges_days: { en: 'Edges of the contractual buckets', es: 'Bordes de los tramos contractuales' },
  uninsured_share_grid: { en: 'Grid of the uninsured share', es: 'Grilla de la parte no asegurada' },
  htm_loss_multiple_grid: { en: 'Grid of the HTM loss multiple', es: 'Grilla del múltiplo de la pérdida HTM' },
  runoff_multiplier_grid: { en: 'Grid of the run-off multiplier', es: 'Grilla del multiplicador de salidas' },
};
const SCALAR_KEYS = ['event_horizon_days', 'reverse_target_days', 'list_compounding_tolerance', 'monotonicity_tolerance_days', 'nlp_identity_tolerance', 'cliff_amber_threshold', 'cliff_red_threshold', 'scoring_ratio_green', 'scoring_ratio_amber', 'generator_truth_se_green', 'generator_truth_se_red', 'htm_revaluation_green', 'htm_revaluation_amber', 'round_trip_tolerance_days', 'cbc_haircut_band'] as const;
const GRID_KEYS = ['contractual_bucket_edges_days', 'uninsured_share_grid', 'htm_loss_multiple_grid', 'runoff_multiplier_grid'] as const;
const CONVENTION_WORD: Bi = { en: 'convention', es: 'convención' };

/** The conventions of the documents of this bake (the same in every document), from the selected one. */
export const conventionsOf = (sel: C16Sel | null): Conventions | null => outputsOf(sel)?.conventions ?? reverseOf(sel)?.conventions ?? null;

const unitWord = (unit: string, lang: Lang): string => {
  const words: Record<string, Bi> = { days: { en: 'days', es: 'días' }, ratio: { en: 'ratio', es: 'razón' } };
  return words[unit] ? pick(words[unit], lang) : es(unit, lang);
};

function ConventionRows({ c }: { c: Conventions }) {
  const lang = useShellLang();
  const word = pick(CONVENTION_WORD, lang);
  const values = (g: Grid) => g.values.map((v) => formatNumber(v, lang, { digits: 4 })).join(', ');
  const named: Array<{ id: string; label: Bi; value: string; basis: BiText; status: string }> = [
    ...SCALAR_KEYS.map((k) => {
      const s: Scalar = c[k];
      return { id: k, label: CONVENTION_TEXT[k], value: `${formatNumber(s.value, lang, { digits: 4 })} ${unitWord(s.unit, lang)}`, basis: s.basis, status: s.status };
    }),
    ...GRID_KEYS.map((k) => ({ id: k, label: CONVENTION_TEXT[k], value: `${values(c[k])} ${unitWord(c[k].unit, lang)}`, basis: c[k].basis, status: c[k].status })),
    { id: 'deposit_category_mapping', label: { en: 'Deposit mapping to the LCR categories', es: 'Mapeo de depósitos a las categorías del LCR' }, value: c.deposit_category_mapping.rows.map((r) => pick(r.label, lang)).join('; '), basis: c.deposit_category_mapping.basis, status: c.deposit_category_mapping.status },
    { id: 'variant_scenarios', label: { en: 'Scenario family and phase of each variant', es: 'Familia de escenario y fase de cada variante' }, value: c.variant_scenarios.rows.map((r) => `${nameOf(r.variant, lang)}: ${scenarioPhrase(r.scenario_family, r.phase, lang)}, ${r.horizon_days}`).join('; '), basis: c.variant_scenarios.basis, status: c.variant_scenarios.status },
    { id: 'day_calendar', label: { en: 'Day calendar of the ladder', es: 'Calendario de días de la escalera' }, value: `${pick({ en: 'US business days from', es: 'días hábiles de EE. UU. desde' }, lang)} ${c.day_calendar.first_day}`, basis: c.day_calendar.basis, status: c.day_calendar.status },
    { id: 'cbc_securities_mapping', label: { en: 'Securities classes and haircuts of the CBC', es: 'Clases de valores y recortes del CBC' }, value: c.cbc_securities_mapping.rows.map((r) => `${pick(text(CLASS_TEXT, r.class_id), lang)} ${SHARE(r.haircut, lang)}`).join('; '), basis: c.cbc_securities_mapping.basis, status: c.cbc_securities_mapping.status },
    { id: 'monetisation_schedule', label: { en: 'Monetisation schedule of the CBC', es: 'Calendario de monetización del CBC' }, value: c.monetisation_schedule.points.map((p) => `${pick({ en: 'day', es: 'día' }, lang)} ${p.day}: ${SHARE(p.cumulative_share, lang)}`).join('; '), basis: c.monetisation_schedule.basis, status: c.monetisation_schedule.status },
    { id: 'fast_run_calibration_rule', label: { en: 'Rule of the fast-run calibration', es: 'Regla de la calibración de la corrida rápida' }, value: nameOf(c.fast_run_calibration_rule.rule, lang), basis: c.fast_run_calibration_rule.basis, status: c.fast_run_calibration_rule.status },
    { id: 'cliff_days', label: { en: 'Days of the cliff diagnostic', es: 'Días del diagnóstico del acantilado' }, value: `${c.cliff_days.near} / ${c.cliff_days.far}, ${nameOf(c.cliff_days.day_basis, lang)}`, basis: c.cliff_days.basis, status: c.cliff_days.status },
  ];
  return (
    <tbody>
      {named.map((n) => (
        <tr key={n.id} data-convention={n.id} data-status={n.status}>
          <td className="ct-text">{pick(n.label, lang)}</td>
          <td className="ct-text">{n.value}</td>
          <td className="ct-text">{n.status === 'convention' ? word : n.status}</td>
          <td className="ct-text ct-wide-only">{pick(n.basis, lang)}</td>
        </tr>
      ))}
    </tbody>
  );
}

function DepositsBlock({ d }: { d: C16Outputs['balance_sheet']['deposits'] }) {
  const lang = useShellLang();
  return (
    <dl className="ct-defs" data-table="c16-deposits">
      <dt>{pick({ en: `Total deposits, DEP (${pick(MONEY_UNIT, 'en')})`, es: `Depósitos totales, DEP (${pick(MONEY_UNIT, 'es')})` }, lang)}</dt>
      <dd>{`${cell(d.dep, lang)} ${pick({ en: '(includes foreign offices)', es: '(incluye oficinas en el exterior)' }, lang)}`}</dd>
      <dt>{pick({ en: 'Domestic deposits, DEPDOM', es: 'Depósitos domésticos, DEPDOM' }, lang)}</dt>
      <dd>{cell(d.depdom, lang)}</dd>
      <dt>{pick({ en: 'Uninsured, DEPUNA, and insured, DEPINS', es: 'No asegurados, DEPUNA, y asegurados, DEPINS' }, lang)}</dt>
      <dd>{`${cell(d.depuna, lang)} / ${cell(d.depins, lang)}`}</dd>
      <dt>{pick({ en: 'Uninsured share of DEP', es: 'Parte no asegurada de DEP' }, lang)}</dt>
      <dd data-denominator="DEP">{SHARE(d.uninsured_share_of_dep, lang)}</dd>
      <dt>{pick({ en: 'Uninsured share of DEPDOM', es: 'Parte no asegurada de DEPDOM' }, lang)}</dt>
      <dd data-denominator="DEPDOM">{SHARE(d.uninsured_share_of_depdom, lang)}</dd>
      <dt>{pick({ en: 'Size fields, DEPSMAMT and DEPLGAMT', es: 'Campos por tamaño, DEPSMAMT y DEPLGAMT' }, lang)}</dt>
      <dd>{`${cell(d.depsmamt, lang)} / ${cell(d.deplgamt, lang)}; ${pick({ en: 'threshold', es: 'umbral' }, lang)} ${formatNumber(d.size_threshold.value, lang, { decimals: 0 })} ${es(d.size_threshold.unit, lang)}`}</dd>
    </dl>
  );
}

const LICENCE_TEXT: Record<string, Bi> = {
  'mirror-allowed': { en: 'mirror allowed', es: 'espejo permitido' },
  'derived-only': { en: 'derived only', es: 'solo derivado' },
  'link-only': { en: 'link only', es: 'solo enlace' },
  unusable: { en: 'unusable', es: 'inutilizable' },
};

function ModelBlocks({ fit, card }: { fit: C16Fit; card: ReturnType<typeof useCard> }) {
  const lang = useShellLang();
  const lp = fit.list_parameters;
  return (
    <>
      <PlotCard title={{ en: 'The run-off parameter sets', es: 'Los conjuntos de parámetros de salida' }} {...card} note={{ en: 'Each set names where it comes from: a transcribed table, a calibration on rows dated before 2023, or a stated value. The LiST rates are the note\'s own, on its 2019 TARGET2 relevant-day calendar.', es: 'Cada conjunto dice de dónde viene: una tabla transcrita, una calibración con filas anteriores a 2023, o un valor declarado. Las tasas LiST son las de la nota, en su calendario de días relevantes TARGET2 de 2019.' }}>
        <div className="ct-scroll">
          <table className="caos-table ct-wrap-head" data-table="c16-parameter-sets">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Set', es: 'Conjunto' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Kind', es: 'Tipo' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Source', es: 'Fuente' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {fit.parameter_sets.map((p) => (
                <tr key={p.set_id} data-parameter-set={p.set_id} data-source-kind={p.source_kind}>
                  <td className="ct-text">{nameOf(p.set_id, lang)}</td>
                  <td className="ct-text">{pick(text(SOURCE_KIND_TEXT, p.source_kind), lang)}</td>
                  <td className="ct-text ct-wide-only">{es(p.source, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head" data-table="c16-list-open">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Open-maturity class (daily rate)', es: 'Clase sin vencimiento (tasa diaria)' }, lang)}</th>
                <th>{pick({ en: 'Baseline', es: 'Base' }, lang)}</th>
                <th>{pick({ en: 'Adverse', es: 'Adverso' }, lang)}</th>
                <th>{pick({ en: 'Extreme', es: 'Extremo' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {lp.open_maturity_daily.map((r) => (
                <tr key={r.item}>
                  <td className="ct-text">{nameOf(r.item, lang)}</td>
                  <td>{formatNumber(r.baseline, lang, { percent: true, digits: 4 })}</td>
                  <td>{formatNumber(r.adverse, lang, { percent: true, digits: 4 })}</td>
                  <td>{formatNumber(r.extreme, lang, { percent: true, digits: 4 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ct-note">{pick(lp.calendar_note, lang)}</p>
          <p className="ct-note" data-block="results-annex">{pick(lp.results_annex.statement, lang)}</p>
        </div>
      </PlotCard>
      <PlotCard title={{ en: 'The calibration and the generator', es: 'La calibración y el generador' }} {...card} note={{ en: 'The fast run is calibrated on rows dated before 2023 and scored on the 2023 rows; the SVB observation is an anchor, not a forecast. The depositor generator has a known truth, so the model\'s run-off can be checked against it.', es: 'La corrida rápida se calibra con filas anteriores a 2023 y se evalúa en las filas de 2023; la observación de SVB es un ancla, no un pronóstico. El generador de depositantes tiene una verdad conocida, así que la salida del modelo se puede contrastar con ella.' }}>
        <div className="ct-scroll">
          <dl className="ct-defs" data-table="c16-calibration">
            <dt>{pick({ en: 'Calibration', es: 'Calibración' }, lang)}</dt>
            <dd>{pick(fit.calibration.statement, lang)}</dd>
            <dt>{pick({ en: 'Fitted daily rate', es: 'Tasa diaria ajustada' }, lang)}</dt>
            <dd data-source-kind={fit.calibration.fitted_daily_rate.source_kind}>{SHARE(fit.calibration.fitted_daily_rate.value, lang)}</dd>
          </dl>
          <table className="caos-table ct-wrap-head" data-table="c16-generator">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Generator segment', es: 'Segmento del generador' }, lang)}</th>
                <th>{pick({ en: 'Share of deposits', es: 'Parte de los depósitos' }, lang)}</th>
                <th>{pick({ en: 'Calm hazard per day', es: 'Riesgo diario en calma' }, lang)}</th>
                <th>{pick({ en: 'Stress hazard per day', es: 'Riesgo diario en estrés' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {fit.generator.config.segments.map((s) => (
                <tr key={s.segment} data-segment={s.segment}>
                  <td className="ct-text">{pick(text(SEGMENT_TEXT, s.segment), lang)}</td>
                  <td>{SHARE(s.share_of_deposits, lang)}</td>
                  <td>{SHARE(s.calm_daily_hazard, lang)}</td>
                  <td>{SHARE(s.stress_daily_hazard, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ct-note" data-within-error={fit.generator.verification.within_error}>
            {pick(
              {
                en: `Verification: ${formatNumber(fit.generator.verification.n_draws, 'en', { decimals: 0 })} draws, largest error ${formatNumber(fit.generator.verification.max_abs_error, 'en', { digits: 4 })} against a Monte Carlo standard error of ${formatNumber(fit.generator.verification.mc_standard_error, 'en', { digits: 4 })}: ${fit.generator.verification.within_error ? 'within the error' : 'outside the error'}.`,
                es: `Verificación: ${formatNumber(fit.generator.verification.n_draws, 'es', { decimals: 0 })} sorteos, error máximo ${formatNumber(fit.generator.verification.max_abs_error, 'es', { digits: 4 })} contra un error estándar de Monte Carlo de ${formatNumber(fit.generator.verification.mc_standard_error, 'es', { digits: 4 })}: ${fit.generator.verification.within_error ? 'dentro del error' : 'fuera del error'}.`,
              },
              lang,
            )}
          </p>
        </div>
      </PlotCard>
      <PlotCard title={{ en: 'The sources and their licence class', es: 'Las fuentes y su clase de licencia' }} {...card} note={{ en: 'The class is a reading of each publisher\'s notice, not legal advice; a source whose notice was not read says so.', es: 'La clase es una lectura del aviso de cada editor, no asesoría legal; una fuente cuyo aviso no se leyó lo dice.' }}>
        <div className="ct-scroll">
          <table className="caos-table ct-wrap-head" data-table="c16-sources">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Source', es: 'Fuente' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Licence class', es: 'Clase de licencia' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Basis', es: 'Base' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Statement', es: 'Declaración' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {fit.sources.map((s) => (
                <tr key={s.source_id} data-source={s.source_id} data-unverified={s.licence_basis === 'unverified' ? 'true' : undefined}>
                  <td className="ct-text" title={s.publisher}>{nameOf(s.source_id, lang)}</td>
                  <td className="ct-text">{pick(text(LICENCE_TEXT, s.licence_class), lang)}</td>
                  <td className="ct-text">{s.licence_basis === 'unverified' ? pick({ en: 'unverified', es: 'no verificada' }, lang) : pick({ en: 'notice read', es: 'aviso leído' }, lang)}</td>
                  <td className="ct-text ct-wide-only">{pick(s.statement, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </>
  );
}

/** The case, the bank with its three labels, the balance sheet and the deposits with both denominators, every convention as a convention, and the models artifact. */
export function C16ContextView({ sel }: { sel: C16Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const r = reverseOf(sel);
  const base = o ?? r;
  if (!sel || !base) return <Pending />;
  const m = sel.data.manifest;
  const v = sel.data.variant;
  const fit = fitOf(sel);
  const conv = base.conventions;
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case', es: 'El caso' }} {...card}>
        <FixtureNotice variant={v} />
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <dl className="ct-defs" data-table="c16-bank" data-bank-aggregates={base.bank.aggregates} data-bank-behaviour={base.bank.behaviour} data-bank-deposits={base.bank.deposits}>
          <dt>{pick({ en: 'Bank', es: 'Banco' }, lang)}</dt>
          <dd>{bankName(base.bank.name, lang)}</dd>
          <dt>{pick({ en: 'What is real and what is synthetic', es: 'Qué es real y qué es sintético' }, lang)}</dt>
          <dd>{pick({ en: 'The balance-sheet aggregates are real, from the FDIC call reports; the behaviour of the depositors and the deposits are synthetic, from a generator with a known truth.', es: 'Los agregados del balance son reales, de los reportes de llamada de la FDIC; el comportamiento de los depositantes y los depósitos son sintéticos, de un generador con verdad conocida.' }, lang)}</dd>
          <dt>{pick({ en: 'Notice of the document', es: 'Aviso del documento' }, lang)}</dt>
          <dd>{pick(base.bank.notice, lang)}</dd>
          <dt>{pick({ en: 'The LCR', es: 'El LCR' }, lang)}</dt>
          <dd>{pick({ en: 'A Basel formula applied to call-report aggregates with stated assumptions, never the bank\'s reported or regulatory LCR.', es: 'Una fórmula de Basilea aplicada a agregados del reporte de llamada con supuestos declarados, nunca el LCR reportado ni regulatorio del banco.' }, lang)}</dd>
          <dt>{pick({ en: 'Valuation date and money', es: 'Fecha de valoración y dinero' }, lang)}</dt>
          <dd>{`${base.valuation_date}; ${pick(MONEY_UNIT, lang)}`}</dd>
          {o ? (
            <>
              <dt>{pick({ en: 'Variant', es: 'Variante' }, lang)}</dt>
              <dd data-variant-id={o.variant.id}>{`${pick(o.variant.label, lang)}. ${pick(o.variant.description, lang)}`}</dd>
              <dt>{pick({ en: 'Scenario', es: 'Escenario' }, lang)}</dt>
              <dd>{`${scenarioPhrase(o.variant.scenario_family, o.variant.phase, lang)}, ${o.variant.horizon_days} ${pick({ en: 'days', es: 'días' }, lang)}`}</dd>
              <dt>{pick({ en: 'Call reports read', es: 'Reportes de llamada leídos' }, lang)}</dt>
              <dd>{`${o.data.call_reports.map((c) => c.report_date).join(', ')}; ${pick({ en: 'data cut-off', es: 'corte de datos' }, lang)} ${o.data.data_cutoff}`}</dd>
              <dt>{pick({ en: 'Dating rule', es: 'Regla de fechas' }, lang)}</dt>
              <dd>{pick(o.data.rule, lang)}</dd>
            </>
          ) : null}
        </dl>
      </PlotCard>
      {o ? (
        <PlotCard title={{ en: 'The balance sheet and the deposits', es: 'El balance y los depósitos' }} {...card} note={{ en: 'DEPUNA and DEPINS cover the domestic offices and their denominator is DEPDOM; DEP includes the foreign offices. Both denominators are stated wherever the uninsured share appears.', es: 'DEPUNA y DEPINS cubren las oficinas domésticas y su denominador es DEPDOM; DEP incluye las oficinas en el exterior. Ambos denominadores se declaran donde aparece la parte no asegurada.' }}>
          <div className="ct-scroll">
            <DepositsBlock d={o.balance_sheet.deposits} />
            <table className="caos-table ct-wrap-head" data-table="c16-items">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Item', es: 'Partida' }, lang)}</th>
                  <th className="ct-text ct-wide-only">{pick({ en: 'FDIC field', es: 'Campo FDIC' }, lang)}</th>
                  <th>{pick({ en: `Amount (${pick(MONEY_UNIT, 'en')})`, es: `Monto (${pick(MONEY_UNIT, 'es')})` }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Assumption or reason', es: 'Supuesto o razón' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {o.balance_sheet.items.map((i) => (
                  <tr key={i.item_id} data-item={i.item_id} data-reported={i.reported_amount === null ? 'false' : 'true'}>
                    <td className="ct-text">{pick(i.label, lang)}</td>
                    <td className="ct-text ct-wide-only">{i.source_field}</td>
                    <td>{cell(i.amount, lang)}</td>
                    <td className="ct-text">{i.reason_missing ? pick(i.reason_missing, lang) : es(i.assumption, lang)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <ul className="ct-note" data-table="c16-assumptions">
              {o.balance_sheet.assumptions.map((a) => (
                <li key={a.assumption_id}>{pick(a.statement, lang)}</li>
              ))}
            </ul>
          </div>
        </PlotCard>
      ) : null}
      <PlotCard title={{ en: 'The named parameters', es: 'Los parámetros con nombre' }} {...card} note={{ en: 'Every grid, tolerance, threshold, mapping and calendar of the case is a convention, labelled as one with the basis of its proposed value; none is a regulatory threshold.', es: 'Cada grilla, tolerancia, umbral, mapeo y calendario del caso es una convención, rotulada como tal con la base de su valor propuesto; ninguno es un umbral regulatorio.' }}>
        <div className="ct-scroll">
          <table className="caos-table ct-wrap-head" data-table="c16-conventions">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Parameter', es: 'Parámetro' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Value', es: 'Valor' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Status', es: 'Estado' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Basis', es: 'Base' }, lang)}</th>
              </tr>
            </thead>
            <ConventionRows c={conv} />
          </table>
        </div>
      </PlotCard>
      {fit ? <ModelBlocks fit={fit} card={card} /> : null}
    </div>
  );
}

// --- the read-outs of the rail ---------------------------------------------------------------------------------------

const SHARE_FORMAT = { percent: true, decimals: 2 } as const;

/** The live read-out of the Day section: the NLP, the CBC and the cumulative net outflow on the day in focus. */
export function DayReadout({ sel }: { sel: C16Sel | null }) {
  const o = outputsOf(sel);
  const l = ladderOf(o);
  const i = sel && o ? dayIndex(o, sel.day) : -1;
  const at = (a: number[] | undefined) => amount(l && a && i >= 0 ? a[i] : null);
  const nlp = at(l?.nlp);
  const cbc = at(l?.cbc_total);
  const net = at(l?.cumulative_net_outflow);
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel ? { en: `Day ${sel.day}`, es: `Día ${sel.day}` } : { en: 'The day', es: 'El día' }}
      items={[
        { label: { en: 'NLP', es: 'NLP' }, value: nlp.value, unit: nlp.unit, format: nlp.format, hint: { en: 'The net liquidity position: the CBC less the cumulative stressed outflows plus the inflows, on this day; the survival period is the first day it is negative.', es: 'El CBC menos las salidas acumuladas bajo estrés más las entradas, en este día; el periodo de supervivencia es el primer día en que es negativa.' } },
        { label: { en: 'CBC', es: 'CBC' }, value: cbc.value, unit: cbc.unit, format: cbc.format, hint: { en: 'The counterbalancing capacity: unencumbered liquid assets after haircuts, usable by this day.', es: 'La capacidad de contrapeso: activos líquidos sin gravamen tras los recortes, utilizables a este día.' } },
        { label: { en: 'Net outflow', es: 'Salida neta' }, value: net.value, unit: net.unit, format: net.format, hint: { en: 'The cumulative stressed outflows less the inflows since the valuation date.', es: 'Las salidas acumuladas bajo estrés menos las entradas desde la fecha de valoración.' } },
        { label: { en: 'Date', es: 'Fecha' }, text: l && i >= 0 ? { en: l.dates[i], es: l.dates[i] } : NA, hint: { en: 'The business day of this ladder day, on the calendar the case states.', es: 'El día hábil de este día de la escalera, en el calendario que declara el caso.' } },
      ]}
    />
  );
}

/** The live read-out of the Realised run section: the denominator in focus, the realised share, the modelled share and their ratio. */
export function DenominatorReadout({ sel }: { sel: C16Sel | null }) {
  const o = outputsOf(sel);
  const d = denominatorOf(o, sel?.denominator ?? '');
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel ? text(DENOMINATOR_SHORT, sel.denominator) : { en: 'The realised run', es: 'La corrida realizada' }}
      items={[
        { label: { en: 'Realised outflow', es: 'Salida realizada' }, value: d?.realised_share ?? null, unitless: true, format: SHARE_FORMAT, hint: { en: 'The share of the denominator that left in the run of 9 and 10 March 2023.', es: 'La parte del denominador que salió en la corrida del 9 y 10 de marzo de 2023.' } },
        { label: { en: 'Modelled outflow', es: 'Salida modelada' }, value: d?.modelled_share ?? null, unitless: true, format: SHARE_FORMAT, hint: { en: 'The share of the model deposit base this variant lets out at the horizon of the comparison.', es: 'La parte de la base de depósitos del modelo que esta variante deja salir en el horizonte de la comparación.' } },
        { label: { en: 'Modelled / realised', es: 'Modelada / realizada' }, value: d?.ratio ?? null, unitless: true, format: SHARE_FORMAT, hint: { en: 'Below 100 percent the model understates the run.', es: 'Bajo 100 por ciento el modelo subestima la corrida.' } },
        { label: { en: 'Light', es: 'Luz' }, text: d ? LIGHT_TEXT[d.light] : NA, hint: { en: 'The light under the stated convention of the case, not a regulatory threshold.', es: 'La luz bajo la convención declarada del caso, no un umbral regulatorio.' } },
      ]}
    />
  );
}

/** The live read-out of the Table A.1 row section: what the row observed and what the model gives at its horizon. */
export function RowReadout({ sel }: { sel: C16Sel | null }) {
  const o = outputsOf(sel);
  const r = rowOf(o, sel?.row ?? '');
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={r ? { en: `${r.bank} ${r.year}`, es: `${r.bank} ${r.year}` } : { en: 'The row', es: 'La fila' }}
      items={[
        { label: { en: 'Observed outflow', es: 'Salida observada' }, value: r?.observed_share ?? null, unitless: true, format: SHARE_FORMAT, hint: { en: 'The deposit outflow of the row over its days (BCBS Table A.1).', es: 'La salida de depósitos de la fila en sus días (Tabla A.1 del BCBS).' } },
        { label: { en: 'Days', es: 'Días' }, value: r?.horizon_days ?? null, unit: { en: 'days', es: 'días' }, format: { decimals: 0 }, hint: { en: 'The horizon over which the row observed its outflow.', es: 'El horizonte en que la fila observó su salida.' } },
        { label: { en: 'Modelled outflow', es: 'Salida modelada' }, value: r?.modelled_share ?? null, unitless: true, format: SHARE_FORMAT, hint: { en: 'The model\'s share at the horizon of the row; not available when the row\'s horizon is beyond the ladder.', es: 'La parte del modelo en el horizonte de la fila; no disponible cuando el horizonte de la fila excede la escalera.' } },
        { label: { en: 'Role', es: 'Papel' }, text: r ? text(ROLE_TEXT, r.role) : NA, hint: { en: 'Whether the fast run was calibrated on the row, scored on it, or only shows it.', es: 'Si la corrida rápida se calibró con la fila, se evaluó en ella, o solo la muestra.' } },
      ]}
    />
  );
}

/** The live read-out of the Deposit mapping section (the LCR variant): the ratio under the mapping in focus. */
export function MappingReadout({ sel }: { sel: C16Sel | null }) {
  const o = outputsOf(sel);
  const m = o?.lcr?.mapping_sensitivity.find((x) => x.mapping_id === sel?.mapping) ?? null;
  const out = amount(m?.uninsured_outflow ?? null);
  const net = amount(m?.net_outflows ?? null);
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'The mapping', es: 'El mapeo' }}
      items={[
        { label: { en: 'LCR', es: 'LCR' }, value: m?.ratio ?? null, unitless: true, format: SHARE_FORMAT, hint: { en: 'A Basel formula on call-report aggregates under this mapping of the uninsured balance; not the bank\'s reported LCR.', es: 'Una fórmula de Basilea sobre agregados del reporte de llamada bajo este mapeo del saldo no asegurado; no el LCR reportado del banco.' } },
        { label: { en: 'Uninsured', es: 'Sin seguro' }, value: out.value, unit: out.unit, format: out.format, hint: { en: 'The 30-day outflow of the uninsured balance at the rate of the mapped category.', es: 'La salida a 30 días del saldo no asegurado a la tasa de la categoría asignada.' } },
        { label: { en: 'Net outflows', es: 'Salidas netas' }, value: net.value, unit: net.unit, format: net.format, hint: { en: 'Outflows less the inflows counted, which are capped at 75 percent of the outflows.', es: 'Las salidas menos las entradas contadas, que tienen un tope de 75 por ciento de las salidas.' } },
      ]}
    />
  );
}

/** The live read-out of the Base scenario section (the reverse stress): the base survival, the solved multiplier and the cap. */
export function BaseReadout({ sel }: { sel: C16Sel | null }) {
  const r = reverseOf(sel);
  const b = baseOf(r, sel?.base ?? '');
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={b ? b.label : { en: 'The base scenario', es: 'El escenario base' }}
      items={[
        { label: { en: 'Base', es: 'Base' }, text: b ? { en: survivalText(b.base_survival, 'en'), es: survivalText(b.base_survival, 'es') } : NA, hint: { en: 'The survival period of the base scenario before any multiplier (survival of the base).', es: 'El periodo de supervivencia del escenario base antes de todo multiplicador.' } },
        { label: { en: 'Solved', es: 'Resuelto' }, value: b?.solved.multiplier ?? null, unitless: true, format: { digits: 4 }, hint: { en: 'The multiple of the daily run-off rates at which the survival period first falls to the target; not available when the target is refused.', es: 'El múltiplo de las tasas diarias de salida con que el periodo de supervivencia cae por primera vez al objetivo; no disponible cuando el objetivo se rechaza.' } },
        { label: { en: 'Cap', es: 'Tope' }, value: b?.max_multiplier ?? null, unitless: true, format: { digits: 4 }, hint: { en: 'The largest multiple that keeps every daily rate below 1.', es: 'El mayor múltiplo que mantiene toda tasa diaria bajo 1.' } },
      ]}
    />
  );
}

/** The live read-out of the Multiplier section: the multiplier of the point in focus and the survival period under it. */
export function PointReadout({ sel }: { sel: C16Sel | null }) {
  const r = reverseOf(sel);
  const b = baseOf(r, sel?.base ?? '');
  const p = b?.curve[sel?.point ?? 0] ?? null;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'The point of the curve', es: 'El punto de la curva' }}
      items={[
        { label: { en: 'Multiplier', es: 'Multiplicador' }, value: p?.multiplier ?? null, unitless: true, format: { digits: 4 }, hint: { en: 'The factor applied to every daily run-off rate of the base scenario.', es: 'El factor aplicado a toda tasa diaria de salida del escenario base.' } },
        { label: { en: 'Survival period', es: 'Periodo de supervivencia' }, text: p ? { en: survivalText(p.survival, 'en'), es: survivalText(p.survival, 'es') } : NA, hint: { en: 'A day, or survives the horizon with the horizon, under this multiplier.', es: 'Un día, o sobrevive el horizonte con el horizonte, bajo este multiplicador.' } },
      ]}
    />
  );
}

export { UnavailableCard, axisOf, amount, COMPARED_AT_TEXT, DENOMINATOR_LONG, HAIRCUT_RULE_TEXT, CLASS_TEXT };
export type { CaseData };
