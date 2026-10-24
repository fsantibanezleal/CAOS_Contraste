// C10's Findings, Variants and Context views, the tests table with the words of the portfolio tests, the illustrative
// notice every portfolio view carries, and the live read-outs of the rail (ADR-0017 rule 3: every section shows a value
// that moves with its controls). The Findings card and the fixture notice are the ones C06 and C07 use.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText, type FormatOptions } from '@fasl-work/caos-app-shell';
import type { ReactNode } from 'react';
import { loadAllVariants, useArtifact } from '../../api/artifacts';
import type { TestRow, VariantArtifact } from '../../lib/contract.types';
import { LIGHT_TEXT } from '../../lib/policy';
import { FindingsCard, FixtureNotice } from '../c06/C06Common';
import { ChartOverTable, compactMoney } from '../c06/format';
import { Pending } from '../Pending';
import { adjustmentText, noteText, seriesText } from '../c08/notes';
import { LiveReadout, referenceText, useCard, type Bi } from '../c03/U6Shared';
import {
  ESTIMATOR_TEXT, GENERATOR_TEXT, INTERVAL_TEXT, SOURCE_TEXT, estimatorFit, estimatorOf, eulerLevelOf, eulerOf, cellOf, gridOf, groupLabel, levelBi, measureOf, outputsOf, rungOf, text,
  type C10Estimator, type C10GridOutputs, type C10Outputs, type C10Sel,
} from './selection';

const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });
const NA: BiText = { en: formatNumber(null, 'en'), es: formatNumber(null, 'es') };

/** The words of the portfolio tests; an id without an entry is shown as the document gives it. */
export const TEST_TEXT: Record<string, Bi> = {
  'portfolio.tail_backtest': { en: 'Tail back-test of the evaluation years', es: 'Backtest de cola de los años de evaluación' },
  'portfolio.mc_convergence': { en: 'Monte Carlo against the analytic anchor', es: 'Monte Carlo frente al ancla analítica' },
  'portfolio.euler_additivity': { en: 'Euler contributions add up', es: 'Las contribuciones de Euler suman el total' },
  'portfolio.crp_recursion_vs_mc': { en: 'CreditRisk+ recursion against Monte Carlo', es: 'Recursión de CreditRisk+ frente a Monte Carlo' },
  'portfolio.correlation_size_power': { en: 'Size and power of the correlation estimate', es: 'Tamaño y potencia de la estimación de la correlación' },
};

const TRUTH_TEXT: Record<string, Bi> = {
  'real-outcomes': { en: 'Real outcomes', es: 'Resultados reales' },
  'synthetic-known-truth': { en: 'Synthetic, with a known truth', es: 'Sintético, con una verdad conocida' },
};

/** The illustrative portfolio's label and notice: printed on every view that draws from it. */
export function IllustrativeNotice({ notice }: { notice: Bi }) {
  const lang = useShellLang();
  return (
    <p className="ct-note" data-portfolio="illustrative">
      <strong>{pick(notice, lang)}</strong>
    </p>
  );
}

/**
 * The rows the engine returned for the tests of this variant, as a block that sits under the drawing of the view the
 * tests belong to: a test that did not run shows its reason, not a number. `only` keeps the tests of one view.
 */
export function C10TestsTable({ variant, only }: { variant: VariantArtifact; only?: (t: TestRow) => boolean }) {
  const lang = useShellLang();
  const rows: TestRow[] = only ? variant.tests.filter(only) : variant.tests;
  const modelName = (id: string | null) => {
    if (id === null) return '-';
    const m = variant.model.find((x) => x.id === id);
    return m ? pick(m.short_title, lang) : id;
  };
  return (
    <div data-block="tests">
      <p className="ct-note">
        {pick({ en: 'The tests the engine returned: the statistic and p-value when it ran, the light under the committed policy and its reference. A test that did not run says why and shows no number.', es: 'Las pruebas que devolvió el motor: el estadístico y el valor p cuando corrió, la luz bajo la política versionada y su referencia. Una prueba que no corrió dice por qué y no muestra número.' }, lang)}
      </p>
      {rows.length === 0 ? (
        <p className="ct-note" data-state="unavailable">{pick({ en: 'This variant carries no test row for this view.', es: 'Esta variante no trae filas de pruebas para esta vista.' }, lang)}</p>
      ) : (
        <table className="caos-table ct-wrap-head" data-table="tests">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Test', es: 'Prueba' }, lang)}</th>
              <th className="ct-text ct-wide-only">{pick({ en: 'Model', es: 'Modelo' }, lang)}</th>
              <th>{pick({ en: 'Statistic', es: 'Estadístico' }, lang)}</th>
              <th>p</th>
              <th className="ct-text">{pick({ en: 'Light', es: 'Luz' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Reason or note', es: 'Razón o nota' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t, i) => {
              const ran = t.light !== 'not_evaluated' && t.light !== 'error';
              return (
                <tr key={`${t.test_id}-${t.model_id}-${t.segment}-${i}`} data-test={t.test_id} data-light={t.light}>
                  <td className="ct-text">{pick(text(TEST_TEXT, t.test_id), lang)}</td>
                  <td className="ct-text ct-wide-only">{modelName(t.model_id)}</td>
                  <td data-na={ran && t.statistic !== null ? undefined : 'true'}>{ran && t.statistic !== null ? formatNumber(t.statistic, lang, { digits: 4 }) : formatNumber(null, lang)}</td>
                  <td data-na={ran && t.p_value !== null ? undefined : 'true'}>{ran && t.p_value !== null ? formatNumber(t.p_value, lang, { digits: 2 }) : formatNumber(null, lang)}</td>
                  <td className={`ct-text ct-light ct-light-${t.light}`}>
                    <span className="ct-light-word">{pick(LIGHT_TEXT[t.light], lang)}</span>
                  </td>
                  <td className="ct-text">{t.notes ? noteText(t.notes, lang) : referenceText(t, lang)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

export function C10FindingsView({ sel }: { sel: C10Sel | null }) {
  if (!sel) return <Pending />;
  return (
    <ViewsRow>
      <FindingsCard variant={sel.data.variant} />
    </ViewsRow>
  );
}

type AnyVariant = VariantArtifact<C10Outputs | C10GridOutputs>;

/** The variants side by side: the fitted correlation of each loan type and the size of each simulator length. Pick one to load it. */
export function C10VariantsTable({ variants, onPick, current }: { variants: Array<{ id: string; title: BiText; v: AnyVariant }>; onPick: (id: string) => void; current: string }) {
  const lang = useShellLang();
  const card = useCard(variants[0]?.v as unknown as VariantArtifact | undefined);
  const loans = variants.filter((x) => x.v.outputs.kind === 'loan-type') as Array<{ id: string; title: BiText; v: VariantArtifact<C10Outputs> }>;
  const grids = variants.filter((x) => x.v.outputs.kind === 'correlation-grid') as Array<{ id: string; title: BiText; v: VariantArtifact<C10GridOutputs> }>;
  const backtest99 = (v: VariantArtifact<C10Outputs>) => v.outputs.backtest.rows.find((r) => r.level === 0.99) ?? null;
  const sizeCell = (v: VariantArtifact<C10GridOutputs>) => v.outputs.cells.find((c) => c.role === 'size') ?? null;
  const link = (id: string, title: BiText) => (
    <button type="button" className="ct-linkbutton" onClick={() => onPick(id)}>{pick(title, lang)}</button>
  );
  return (
    <PlotCard
      fill
      title={{ en: 'The loan types and the simulator', es: 'Los tipos de crédito y el simulador' }}
      {...card}
      note={{
        en: 'The fitted asset correlation of each Federal Reserve loan type against the IRB correlation of its regulatory class, and the exact size of the correlation test on the simulator at each series length. Pick a row to load it.',
        es: 'La correlación de activos ajustada de cada tipo de crédito de la Reserva Federal contra la correlación IRB de su clase regulatoria, y el tamaño exacto de la prueba de correlación en el simulador con cada largo de serie. Elija una fila para cargarla.',
      }}
    >
      <ChartOverTable
        chartMin={`${Math.max(loans.length, 1) * 3 + 3}rem`}
        chart={
          <BarChart
            title={{ en: 'Fitted asset correlation by loan type', es: 'Correlación de activos ajustada por tipo de crédito' }}
            height="fill"
            orientation="vertical"
            data={loans.map(({ id, title, v }) => ({ id, label: title, value: v.outputs.fit.maximum_likelihood.rho.estimate, tone: 'accent' as const, highlight: id === current }))}
            axis={{ label: { en: 'Maximum-likelihood asset correlation', es: 'Correlación de activos de máxima verosimilitud' }, format: { percent: true, decimals: 1 } }}
          />
        }
      >
        {loans.length > 0 ? (
          <table className="caos-table ct-wrap-head" data-table="variants-c10-loans">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Loan type', es: 'Tipo de crédito' }, lang)}</th>
                <th>{pick({ en: 'Fitted correlation', es: 'Correlación ajustada' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'IRB correlation', es: 'Correlación IRB' }, lang)}</th>
                <th>{pick({ en: 'Years above the 99% quantile', es: 'Años sobre el cuantil 99 %' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {loans.map(({ id, title, v }) => {
                const b = backtest99(v);
                return (
                  <tr key={id} data-variant={id} className={id === current ? 'ct-current' : undefined}>
                    <td className="ct-text">{link(id, title)}</td>
                    <td>{formatNumber(v.outputs.fit.maximum_likelihood.rho.estimate, lang, { percent: true, decimals: 1 })}</td>
                    <td className="ct-wide-only">{formatNumber(v.outputs.irb_reference.irb_correlation, lang, { percent: true, decimals: 1 })}</td>
                    <td>{b ? `${count(b.observed_exceedances, lang)} / ${formatNumber(b.expected_exceedances, lang, { digits: 3 })}` : formatNumber(null, lang)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : null}
        {grids.length > 0 ? (
          <table className="caos-table ct-wrap-head" data-table="variants-c10-grids">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Simulator', es: 'Simulador' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Years in the series', es: 'Años de la serie' }, lang)}</th>
                <th>{pick({ en: 'Size, maximum likelihood', es: 'Tamaño, máxima verosimilitud' }, lang)}</th>
                <th>{pick({ en: 'Nominal size', es: 'Tamaño nominal' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {grids.map(({ id, title, v }) => {
                const cell = sizeCell(v);
                const ml = estimatorOf(cell ?? undefined, 'maximum-likelihood');
                return (
                  <tr key={id} data-variant={id} className={id === current ? 'ct-current' : undefined}>
                    <td className="ct-text">{link(id, title)}</td>
                    <td className="ct-wide-only">{count(v.outputs.generator.series_length_years, lang)}</td>
                    <td>{ml ? formatNumber(ml.rejection_rate, lang, { percent: true, decimals: 1 }) : formatNumber(null, lang)}</td>
                    <td>{formatNumber(v.outputs.generator.alpha, lang, { percent: true, decimals: 0 })}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : null}
      </ChartOverTable>
    </PlotCard>
  );
}

export function C10VariantsView({ sel, onPick }: { sel: C10Sel | null; onPick: (id: string) => void }) {
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  if (!sel || all.state !== 'ready') return <Pending />;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const variants = (all.data as unknown as AnyVariant[])
    .filter((v) => v.outputs.kind === 'loan-type' || v.outputs.kind === 'correlation-grid')
    .map((v) => ({ id: v.variant_id, title: entries.find((e) => e.variant_id === v.variant_id)?.short_title ?? { en: v.variant_id, es: v.variant_id }, v }));
  return (
    <ViewsRow>
      <C10VariantsTable variants={variants} onPick={onPick} current={sel.data.variant.variant_id} />
    </ViewsRow>
  );
}

/** The case, the Federal Reserve table and the quarters it lacks, the windows; or the simulator and its generator. */
export function C10ContextView({ sel, children }: { sel: C10Sel | null; children?: ReactNode }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const g = gridOf(sel);
  if (!sel || (!o && !g)) return <Pending />;
  const m = sel.data.manifest;
  const v = sel.data.variant;
  const to = pick({ en: 'to', es: 'a' }, lang);
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case', es: 'El caso' }} {...card}>
        <FixtureNotice variant={v} />
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        {o ? (
          <dl className="ct-defs" data-table="c10-definition">
            <dt>{pick({ en: 'Loan type', es: 'Tipo de crédito' }, lang)}</dt>
            <dd>{pick(o.label, lang)}</dd>
            <dt>{pick({ en: 'Loss rate', es: 'Tasa de pérdida' }, lang)}</dt>
            <dd>{pick(o.loss_rate_definition, lang)}</dd>
            <dt>{pick({ en: 'Fit window', es: 'Ventana de ajuste' }, lang)}</dt>
            <dd data-window="fit">{`${o.windows.fit.first_year} ${to} ${o.windows.fit.last_year} (${count(o.windows.fit.n_years, lang)} ${pick({ en: 'years', es: 'años' }, lang)})`}</dd>
            <dt>{pick({ en: 'Evaluation window', es: 'Ventana de evaluación' }, lang)}</dt>
            <dd data-window="evaluation">{`${o.windows.evaluation.first_year} ${to} ${o.windows.evaluation.last_year} (${count(o.windows.evaluation.n_years, lang)} ${pick({ en: 'years', es: 'años' }, lang)})`}</dd>
            <dt>{pick({ en: 'Truth status of this variant', es: 'Estado de verdad de esta variante' }, lang)}</dt>
            <dd data-truth-status={v.provenance.truth_status}>{pick(text(TRUTH_TEXT, v.provenance.truth_status), lang)}</dd>
          </dl>
        ) : null}
        {g ? (
          <dl className="ct-defs" data-table="c10-definition">
            <dt>{pick({ en: 'Variant', es: 'Variante' }, lang)}</dt>
            <dd>{pick(g.label, lang)}</dd>
            <dt>{pick({ en: 'Size and power', es: 'Tamaño y potencia' }, lang)}</dt>
            <dd>{pick(g.size_power_definition, lang)}</dd>
            <dt>{pick({ en: 'Truth status of this variant', es: 'Estado de verdad de esta variante' }, lang)}</dt>
            <dd data-truth-status={v.provenance.truth_status}>{pick(text(TRUTH_TEXT, v.provenance.truth_status), lang)}</dd>
          </dl>
        ) : null}
      </PlotCard>
      {o ? (
        <PlotCard title={{ en: 'The Federal Reserve series', es: 'La serie de la Reserva Federal' }} {...card} note={{ en: 'A quarter the table lacks is a missing quarter with its reason: it is never interpolated, and the year it belongs to has no rate.', es: 'Un trimestre que la tabla no tiene es un trimestre faltante con su razón: nunca se interpola, y el año al que pertenece no tiene tasa.' }}>
          <dl className="ct-defs" data-table="c10-series">
            <dt>{pick({ en: 'Source', es: 'Fuente' }, lang)}</dt>
            <dd>{pick(text(SOURCE_TEXT, o.data_status.source), lang)}</dd>
            <dt>{pick({ en: 'Table', es: 'Tabla' }, lang)}</dt>
            <dd translate="no">{o.data_status.table}</dd>
            <dt>{pick({ en: 'Series', es: 'Serie' }, lang)}</dt>
            <dd>{seriesText(o.data_status.series, lang)}</dd>
            <dt>{pick({ en: 'Adjustment and scope', es: 'Ajuste y alcance' }, lang)}</dt>
            <dd>{`${adjustmentText(o.data_status.seasonal_adjustment, lang)}, ${adjustmentText(o.data_status.bank_scope, lang)}`}</dd>
            <dt>{pick({ en: 'Files as of', es: 'Archivos al' }, lang)}</dt>
            <dd>{o.data_status.files_as_of}</dd>
            <dt>{pick({ en: 'Quarters expected', es: 'Trimestres esperados' }, lang)}</dt>
            <dd>{count(o.data_status.quarters_expected, lang)}</dd>
            <dt>{pick({ en: 'Notice of the document', es: 'Aviso del documento' }, lang)}</dt>
            <dd>{pick(o.data_status.notice, lang)}</dd>
          </dl>
          {o.data_status.missing_quarters.length === 0 ? (
            <p className="ct-note" data-state="complete">{pick({ en: 'No quarter is missing from the table.', es: 'Ningún trimestre falta en la tabla.' }, lang)}</p>
          ) : (
            <table className="caos-table ct-wrap-head" data-table="c10-missing-quarters">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Missing quarter', es: 'Trimestre faltante' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Reason', es: 'Razón' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {o.data_status.missing_quarters.map((q) => (
                  <tr key={q.quarter} data-quarter={q.quarter}>
                    <td className="ct-text">{q.quarter}</td>
                    <td className="ct-text">{noteText(q.reason, lang)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </PlotCard>
      ) : null}
      {g ? (
        <PlotCard title={{ en: 'The simulator', es: 'El simulador' }} {...card} note={{ en: 'The truth is the correlation the generator draws the yearly factor with. Every replication uses an independent seeded stream.', es: 'La verdad es la correlación con que el generador simula el factor anual. Cada replicación usa una corriente con semilla independiente.' }}>
          <dl className="ct-defs" data-table="c10-generator">
            <dt>{pick({ en: 'Generator', es: 'Generador' }, lang)}</dt>
            <dd>{pick(text(GENERATOR_TEXT, g.generator.name), lang)}</dd>
            <dt>{pick({ en: 'Shaped on', es: 'Con la forma de' }, lang)}</dt>
            <dd data-shaped-on={g.generator.shaped_on}>{noteText(g.generator.shaped_on, lang)}</dd>
            <dt>{pick({ en: 'Known PD', es: 'PD conocida' }, lang)}</dt>
            <dd>{formatNumber(g.generator.known_pd, lang, { percent: true, decimals: 2 })}</dd>
            <dt>{pick({ en: 'Years in the series', es: 'Años de la serie' }, lang)}</dt>
            <dd>{count(g.generator.series_length_years, lang)}</dd>
            <dt>{pick({ en: 'Replications', es: 'Replicaciones' }, lang)}</dt>
            <dd>{count(g.generator.n_replications, lang)}</dd>
            <dt>{pick({ en: 'Correlation under the null', es: 'Correlación bajo la nula' }, lang)}</dt>
            <dd>{formatNumber(g.generator.null_rho, lang, { percent: true, decimals: 0 })}</dd>
            <dt>{pick({ en: 'Seed', es: 'Semilla' }, lang)}</dt>
            <dd data-seed={g.generator.seed}>{g.generator.seed}</dd>
            <dt>{pick({ en: 'Notice of the document', es: 'Aviso del documento' }, lang)}</dt>
            <dd>{pick(g.generator.notice, lang)}</dd>
          </dl>
        </PlotCard>
      ) : null}
      {children}
    </div>
  );
}

/** The live read-out of the estimator section on the simulator: the estimator across the whole grid. */
export function GridEstimatorReadout({ sel }: { sel: C10Sel | null }) {
  const g = gridOf(sel);
  const rows = g ? g.cells.map((c) => ({ c, e: estimatorOf(c, sel?.estimator ?? '') })).filter((x) => x.e !== null) : [];
  const size = rows.find((x) => x.c.role === 'size')?.e ?? null;
  const power = rows.filter((x) => x.c.role === 'power').map((x) => (x.e as C10Estimator).rejection_rate);
  const coverage = rows.map((x) => (x.e as C10Estimator).coverage);
  const low = (xs: number[]) => (xs.length ? Math.min(...xs) : null);
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel ? { en: `${text(ESTIMATOR_TEXT, sel.estimator).en} across the grid`, es: `${text(ESTIMATOR_TEXT, sel.estimator).es} en toda la grilla` } : { en: 'The estimator across the grid', es: 'El estimador en toda la grilla' }}
      items={[
        { label: { en: 'Size at the null', es: 'Tamaño en la nula' }, value: size?.rejection_rate ?? null, unitless: true, format: { percent: true, decimals: 1 }, hint: { en: 'The rejection rate where the known correlation is the null; it should sit at the nominal level.', es: 'La tasa de rechazo donde la correlación conocida es la nula; debería quedar en el nivel nominal.' } },
        { label: { en: 'Lowest power', es: 'Menor potencia' }, value: low(power), unitless: true, format: { percent: true, decimals: 1 }, hint: { en: 'The smallest rejection rate among the cells where the null is false.', es: 'La menor tasa de rechazo entre las celdas donde la nula es falsa.' } },
        { label: { en: 'Lowest coverage', es: 'Menor cobertura' }, value: low(coverage), unitless: true, format: { percent: true, decimals: 1 }, hint: { en: 'The smallest share of intervals that hold the known correlation.', es: 'La menor proporción de intervalos que contienen la correlación conocida.' } },
      ]}
    />
  );
}

const money = (v: number | null, ccy: string) => compactMoney(v, ccy);

/** The amounts of one read-out in one shared unit (the largest decides it), so a row of 0.8 m and a row of 1.0 m never mix with 873,766. */
function moneySet(values: Array<number | null>, ccy: string): Array<{ value: number | null; unit: BiText; format: FormatOptions }> {
  const max = Math.max(0, ...values.filter((v): v is number => v !== null).map((v) => Math.abs(v)));
  const ref = compactMoney(max, ccy);
  const div = ref.value ? max / ref.value : 1;
  return values.map((v) => ({ value: v === null ? null : v / div, unit: ref.unit, format: ref.format }));
}

/** The live read-out of the Rung section: EL, VaR and ES of the rung in focus at the level, with the VaR's sampling error. */
export function RungReadout({ sel }: { sel: C10Sel | null }) {
  const o = outputsOf(sel);
  const r = o && sel ? rungOf(o, sel.rung) : undefined;
  const m = r && sel ? measureOf(r, sel.level) : null;
  const ccy = o?.currency ?? '';
  const level = sel ? levelBi(sel.level) : { en: '', es: '' };
  const why: BiText = r && !r.evaluated ? { en: 'This rung did not run, so it has no number.', es: 'Este escalón no corrió, así que no tiene número.' } : { en: 'Not in this document.', es: 'No está en este documento.' };
  const [elM, varM, esM, seM] = moneySet([m?.el ?? null, m?.var ?? null, m?.es ?? null, m?.var_se ?? null], ccy);
  const esWhy: BiText = m && m.es === null ? { en: noteText(m.es_reason, 'en'), es: noteText(m.es_reason, 'es') } : { en: 'The expected shortfall: the mean loss beyond the VaR.', es: 'El déficit esperado: la pérdida media más allá del VaR.' };
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: `This rung at ${level.en}`, es: `Este escalón al ${level.es}` }}
      items={[
        { label: { en: 'Expected loss', es: 'Pérdida esperada' }, ...elM, hint: m ? { en: 'The mean of the portfolio loss over one year.', es: 'La media de la pérdida de la cartera en un año.' } : why },
        { label: { en: 'VaR', es: 'VaR' }, ...varM, hint: { en: 'The loss the portfolio does not exceed with the confidence of the level.', es: 'La pérdida que la cartera no supera con la confianza del nivel.' } },
        { label: { en: 'Expected shortfall', es: 'Déficit esperado' }, ...esM, hint: esWhy },
        m && m.var_se === null && r?.evaluated
          ? { label: { en: 'Error of the VaR', es: 'Error del VaR' }, text: { en: 'none, analytic', es: 'ninguno, analítico' }, hint: { en: 'An analytic rung has no sampling error.', es: 'Un escalón analítico no tiene error de muestreo.' } }
          : { label: { en: 'Error of the VaR', es: 'Error del VaR' }, ...seM, hint: { en: 'The Monte Carlo standard error of the VaR.', es: 'El error estándar de Monte Carlo del VaR.' } },
      ]}
    />
  );
}

/** The live read-out of the Level section: the fitted quantile and the evaluation years above it. */
export function LevelReadout({ sel }: { sel: C10Sel | null }) {
  const o = outputsOf(sel);
  const b = o && sel ? o.backtest.rows.find((r) => r.level === sel.level) ?? null : null;
  const light = b ? LIGHT_TEXT[b.light] : null;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'The evaluation years at this level', es: 'Los años de evaluación en este nivel' }}
      items={[
        { label: { en: 'Fitted quantile', es: 'Cuantil ajustado' }, value: b?.fitted_quantile ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'The yearly loss rate the fitted distribution puts at the level.', es: 'La tasa de pérdida anual que la distribución ajustada pone en el nivel.' } },
        { label: { en: 'Years expected above', es: 'Años esperados sobre él' }, value: b?.expected_exceedances ?? null, unitless: true, format: { digits: 3 }, hint: { en: 'Evaluation years times one minus the level.', es: 'Años de evaluación por uno menos el nivel.' } },
        { label: { en: 'Years observed above', es: 'Años observados sobre él' }, value: b?.observed_exceedances ?? null, unitless: true, format: { decimals: 0 }, hint: { en: 'Evaluation years whose loss rate is above the fitted quantile.', es: 'Años de evaluación cuya tasa de pérdida supera el cuantil ajustado.' } },
        { label: { en: 'Light', es: 'Luz' }, text: light ?? NA, hint: { en: 'The light of the binomial tail probability under the committed policy.', es: 'La luz de la probabilidad de cola binomial bajo la política versionada.' } },
      ]}
    />
  );
}

/** The live read-out of the Estimator section: the correlation and the PD of the estimator in focus, with the interval. */
export function EstimatorReadout({ sel }: { sel: C10Sel | null }) {
  const o = outputsOf(sel);
  const f = o && sel ? estimatorFit(o, sel.estimator) : null;
  const method = f ? text(INTERVAL_TEXT, f.interval_method) : null;
  const fmt = { percent: true, decimals: 1 } as const;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel ? { en: `${text(ESTIMATOR_TEXT, sel.estimator).en}: the fit`, es: `${text(ESTIMATOR_TEXT, sel.estimator).es}: el ajuste` } : { en: 'The fit', es: 'El ajuste' }}
      items={[
        { label: { en: 'Asset correlation', es: 'Correlación de activos' }, value: f?.rho.estimate ?? null, unitless: true, format: fmt, hint: { en: 'The correlation of the obligors with the one systematic factor, squared loading.', es: 'La correlación de los deudores con el único factor sistemático, carga al cuadrado.' } },
        { label: { en: 'Interval, low', es: 'Intervalo, inferior' }, value: f?.rho.ci_low ?? null, unitless: true, format: fmt, hint: method ? { en: `95% interval by ${method.en}.`, es: `Intervalo del 95 % por ${method.es}.` } : { en: 'The 95% interval.', es: 'El intervalo del 95 %.' } },
        { label: { en: 'Interval, high', es: 'Intervalo, superior' }, value: f?.rho.ci_high ?? null, unitless: true, format: fmt, hint: method ? { en: `95% interval by ${method.en}.`, es: `Intervalo del 95 % por ${method.es}.` } : { en: 'The 95% interval.', es: 'El intervalo del 95 %.' } },
        { label: { en: 'Probability of default', es: 'Probabilidad de incumplimiento' }, value: f?.pd.estimate ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'The long-run yearly default or loss rate of the fitted distribution.', es: 'La tasa anual de incumplimiento o pérdida de largo plazo de la distribución ajustada.' } },
      ]}
    />
  );
}

/** The live read-out of the Group section: the group's share of the VaR and the ES at the level, in the Euler block of the rung. */
export function GroupReadout({ sel }: { sel: C10Sel | null }) {
  const o = outputsOf(sel);
  const rung = o && sel ? rungOf(o, sel.rung) : undefined;
  const block = o ? (eulerOf(o, rung) ?? o.euler[0] ?? null) : null;
  const row = eulerLevelOf(block, sel?.level ?? 0.999)?.rows.find((r) => r.group_id === sel?.group) ?? null;
  const ccy = block?.currency ?? o?.currency ?? '';
  const label = o && sel ? groupLabel(o.portfolio.groups, sel.group) : { en: 'The group', es: 'El grupo' };
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: `${label.en} in the tail`, es: `${label.es} en la cola` }}
      items={[
        { label: { en: 'Share of the VaR', es: 'Parte del VaR' }, value: row?.share_var ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'The Euler contribution of the group to the VaR, over the VaR.', es: 'La contribución de Euler del grupo al VaR, sobre el VaR.' } },
        { label: { en: 'Share of the ES', es: 'Parte del ES' }, value: row?.share_es ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'The Euler contribution of the group to the expected shortfall, over the ES.', es: 'La contribución de Euler del grupo al déficit esperado, sobre el ES.' } },
        { label: { en: 'Contribution to the VaR', es: 'Contribución al VaR' }, ...money(row?.rc_var ?? null, ccy), hint: { en: 'In money, from the sampled rung that carries Euler contributions.', es: 'En dinero, del escalón muestreado que trae contribuciones de Euler.' } },
      ]}
    />
  );
}

/** The live read-out of the known-correlation section of the simulator: the cell's role and the estimator's rates. */
export function CellReadout({ sel }: { sel: C10Sel | null }) {
  const g = gridOf(sel);
  const cell = g && sel ? cellOf(g, sel.cell) : undefined;
  const e = estimatorOf(cell, sel?.estimator ?? '');
  const role: BiText | null = cell ? (cell.role === 'size' ? { en: 'size', es: 'tamaño' } : { en: 'power', es: 'potencia' }) : null;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={cell ? { en: `Known correlation ${levelLabelOf(cell.known_rho, 'en')}`, es: `Correlación conocida ${levelLabelOf(cell.known_rho, 'es')}` } : { en: 'This known correlation', es: 'Esta correlación conocida' }}
      items={[
        { label: { en: 'Role of the cell', es: 'Papel de la celda' }, text: role ?? NA, hint: { en: 'Size where the known correlation equals the null; power elsewhere.', es: 'Tamaño donde la correlación conocida es la de la nula; potencia en las demás.' } },
        { label: { en: 'Rejection rate', es: 'Tasa de rechazo' }, value: e?.rejection_rate ?? null, unitless: true, format: { percent: true, decimals: 1 }, hint: { en: 'How often the test rejects that the correlation equals the null.', es: 'Con qué frecuencia la prueba rechaza que la correlación sea la de la nula.' } },
        { label: { en: 'Coverage of the interval', es: 'Cobertura del intervalo' }, value: e?.coverage ?? null, unitless: true, format: { percent: true, decimals: 1 }, hint: { en: 'How often the 95% interval holds the known correlation.', es: 'Con qué frecuencia el intervalo del 95 % contiene la correlación conocida.' } },
        { label: { en: 'Mean estimate', es: 'Estimación media' }, value: e?.mean_estimate ?? null, unitless: true, format: { percent: true, decimals: 1 }, hint: { en: 'The mean of the estimates over the valid replications.', es: 'La media de las estimaciones en las replicaciones válidas.' } },
      ]}
    />
  );
}

const levelLabelOf = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { percent: true, decimals: 1 });
