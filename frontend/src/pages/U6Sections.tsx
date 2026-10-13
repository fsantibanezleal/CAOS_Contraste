// The sections of the cross-case pages for the cases that are not the C01 scorecard shape: C03 (vintages), C06 and C07
// (provisions), C08 (LGD) and C09 (EAD and CCF). Experiments reads one headline row per variant; Benchmark compares the
// rungs of each variant with the case's own metrics. Every number is read from the committed variant artifacts when the
// page opens; none is typed in, and a value the artifact leaves null says "not available" (T13).
import { formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import type { ReactNode } from 'react';
import { loadAllVariants, useArtifact } from '../api/artifacts';
import type { CaseManifest, VariantArtifact } from '../lib/contract.types';
import { P, useT } from '../content/bi';
import type { C03Outputs } from '../workbench/c03/selection';
import type { C06Outputs } from '../workbench/c06/selection';
import type { C07Outputs } from '../workbench/c07/selection';
import type { C08Outputs } from '../workbench/c08/selection';
import type { C09Outputs } from '../workbench/c09/selection';
import { compactMoney } from '../workbench/c06/format';

type Lang = 'en' | 'es';
type Cell = ReactNode;

/** The cases this file renders; every other built case has its own section or the C01 scorecard shape. */
export const U6_CASES = new Set(['C03', 'C06', 'C07', 'C08', 'C09']);
/** The cases with a rung comparison for the Benchmark (the provisions cases compare regimes, in the App). */
export const U6_BENCHMARK_CASES = new Set(['C03', 'C08', 'C09']);

const num = (v: number | null | undefined, lang: Lang, decimals = 3) => formatNumber(v, lang, { decimals });
const pct = (v: number | null | undefined, lang: Lang, decimals = 2) => formatNumber(v, lang, { percent: true, decimals });

/** An amount for a table cell: scaled to billions or millions with its unit, never an eleven-digit number. */
function money(v: number | null | undefined, currency: string, lang: Lang): string {
  const c = compactMoney(v, currency);
  return c.value === null ? formatNumber(null, lang) : `${formatNumber(c.value, lang, c.format)} ${pick(c.unit, lang)}`;
}

/** The weighted mean of the values that are present, or null when there is none. */
function wmean(items: Array<{ v: number | null | undefined; w: number }>): number | null {
  let s = 0;
  let w = 0;
  for (const i of items) {
    if (i.v === null || i.v === undefined || !Number.isFinite(i.v)) continue;
    s += i.v * i.w;
    w += i.w;
  }
  return w > 0 ? s / w : null;
}

function Table({ head, rows, wide = 1 }: { head: string[]; rows: Cell[][]; wide?: number }) {
  return (
    <table className="caos-table" data-state="ready">
      <thead>
        <tr>
          {head.map((h, i) => (
            <th key={h} className={i < wide ? 'caos-col-text' : undefined}>
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            {r.map((c, j) => (
              <td key={j} className={j < wide ? 'caos-col-text' : undefined}>
                {c}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function useVariants(manifest: CaseManifest) {
  return useArtifact<VariantArtifact<unknown>[]>((s) => loadAllVariants(manifest, s) as never, [manifest.case_id]);
}

function Loading() {
  const t = useT();
  return <p className="caos-pending" data-state="loading">{t('Loading the variants', 'Cargando las variantes')}</p>;
}

/** The rows of a case's Experiments table: one per variant, in the order of the manifest. */
export function experimentRows(manifest: CaseManifest, vs: VariantArtifact<unknown>[], lang: Lang): Cell[][] {
  const title = Object.fromEntries(manifest.artifacts.filter((a) => a.role === 'variant').map((a) => [a.variant_id, pick(a.short_title ?? a.title, lang)]));
  const id = manifest.case_id;
  return vs.map((v) => {
    const name = title[v.variant_id] ?? v.variant_id;
    if (id === 'C03') {
      const o = v.outputs as C03Outputs;
      const rows = o.vintage_summary.rows;
      const seen = rows.filter((r) => r.mark_observed);
      const w = (f: (r: (typeof rows)[number]) => number | null | undefined) => wmean(seen.map((r) => ({ v: f(r), w: r.n })));
      const psi = o.stability.rows.map((r) => r.psi).filter((x): x is number => typeof x === 'number');
      return [name, formatNumber(o.training.n_loans, lang), `${seen.length} / ${rows.length}`, pct(w((r) => r.predicted_5y_pd), lang), pct(w((r) => r.observed_5y_pd), lang), psi.length ? num(Math.max(...psi), lang) : formatNumber(null, lang)];
    }
    if (id === 'C06') {
      const o = v.outputs as C06Outputs;
      const rows = o.stage_summary.rows;
      const gross = rows.reduce((a, r) => a + r.gross_carrying_amount, 0);
      const ecl = rows.reduce((a, r) => a + r.ecl, 0);
      const late = rows.filter((r) => r.stage !== 'stage1').reduce((a, r) => a + r.gross_carrying_amount, 0);
      return [name, formatNumber(rows.reduce((a, r) => a + r.accounts, 0), lang), money(gross, o.currency, lang), money(ecl, o.currency, lang), pct(gross > 0 ? ecl / gross : null, lang), pct(gross > 0 ? late / gross : null, lang, 1)];
    }
    if (id === 'C07') {
      const o = v.outputs as C07Outputs;
      const by = Object.fromEntries(o.regimes.map((r) => [r.regime, r.total_provision]));
      return [name, money(by['cmf-b1'], o.currency, lang), money(by['ifrs9'], o.currency, lang), money(by['bde-annex9'], o.currency, lang)];
    }
    if (id === 'C08') {
      const o = v.outputs as C08Outputs;
      const d = o.lgd_distribution;
      return [name, formatNumber(d.n, lang), pct(d.mean.value, lang), pct(d.mass_at_one.share, lang), pct(d.share_above_one, lang), pct(o.downturn.coverage.share_covered, lang, 0)];
    }
    const o = v.outputs as C09Outputs;
    const base = o.ccf_by_design.rows.filter((r) => r.estimator === 'mean');
    const inside = o.ccf_by_design.rows.filter((r) => r.within_tolerance).length;
    const row = base[0];
    return [name, pct(o.generator.true_ccf.value, lang), pct(row?.estimate.value, lang), pct(row?.bias, lang), `${inside} / ${o.ccf_by_design.rows.length}`];
  });
}

/** The Experiments section of a case: what each variant found, in the case's own measures. */
export function U6ExperimentsSection({ manifest }: { manifest: CaseManifest }) {
  const lang = useShellLang();
  const t = useT();
  const all = useVariants(manifest);
  if (all.state !== 'ready') return <Loading />;
  const rows = experimentRows(manifest, all.data, lang);
  const head: Record<string, string[]> = {
    C03: [t('Variant', 'Variante'), t('Training loans', 'Créditos de entrenamiento'), t('Vintages with a 5-year mark', 'Cosechas con marca de 5 años'), t('Predicted 5-year PD', 'PD a 5 años predicha'), t('Observed 5-year PD', 'PD a 5 años observada'), t('Largest PSI', 'PSI máximo')],
    C06: [t('Variant', 'Variante'), t('Accounts', 'Cuentas'), t('Gross carrying amount', 'Importe en libros bruto'), t('Expected credit loss', 'Pérdida crediticia esperada'), t('Coverage', 'Cobertura'), t('Share not in stage 1', 'Parte fuera de la etapa 1')],
    C07: [t('Variant', 'Variante'), t('CMF B-1', 'CMF B-1'), t('IFRS 9', 'IFRS 9'), t('BdE Annex 9', 'Anejo 9 del BdE')],
    C08: [t('Variant', 'Variante'), t('Defaults', 'Incumplimientos'), t('Mean LGD proxy', 'LGD proxy media'), t('Share at 1', 'Parte en 1'), t('Share above 1', 'Parte sobre 1'), t('Downturn cohorts covered', 'Cohortes de recesión cubiertas')],
    C09: [t('Variant', 'Variante'), t('Known CCF', 'CCF conocido'), t('Mean estimator, fixed horizon', 'Estimador de media, horizonte fijo'), t('Its bias', 'Su sesgo'), t('Estimates inside the tolerance', 'Estimaciones dentro de la tolerancia')],
  };
  return (
    <>
      <Table head={head[manifest.case_id]} rows={rows} />
      <P
        en="The columns are the case's own measures, read from each variant's artifact; the App holds the full instrument, with the tests and their lights."
        es="Las columnas son las medidas propias del caso, leídas del artefacto de cada variante; la App contiene el instrumento completo, con las pruebas y sus luces."
      />
    </>
  );
}

function rungName(v: VariantArtifact<unknown>, id: string, lang: Lang): string {
  const m = v.model.find((x) => x.id === id);
  return m ? `${m.rung ? `${m.rung} ` : ''}${pick(m.title, lang)}` : id;
}

/** The Benchmark section of a case: its rungs compared with its own metrics, one table per variant. */
export function U6BenchmarkSection({ manifest }: { manifest: CaseManifest }) {
  const lang = useShellLang();
  const t = useT();
  const all = useVariants(manifest);
  if (all.state !== 'ready') return <Loading />;
  const title = Object.fromEntries(manifest.artifacts.filter((a) => a.role === 'variant').map((a) => [a.variant_id, pick(a.short_title ?? a.title, lang)]));
  return (
    <div data-state="ready">
      {all.data.map((v) => {
        const name = title[v.variant_id] ?? v.variant_id;
        if (manifest.case_id === 'C03') {
          const o = v.outputs as C03Outputs;
          return (
            <section key={v.variant_id}>
              <h4>{name}</h4>
              <Table
                head={[t('Rung', 'Peldaño'), 'AUC', t('95% interval', 'Intervalo 95%'), 'Brier', t('5-year calibration gap', 'Brecha de calibración a 5 años')]}
                rows={o.rung_comparison.map((r) => [
                  rungName(v, r.rung_id, lang),
                  r.auc === null ? `${formatNumber(null, lang)}${r.reason ? ` (${r.reason})` : ''}` : num(r.auc, lang, 4),
                  r.auc_ci_low === null || r.auc_ci_high === null ? '' : `${num(r.auc_ci_low, lang, 4)} - ${num(r.auc_ci_high, lang, 4)}`,
                  num(r.brier, lang, 4),
                  pct(r.calibration_gap_5y, lang),
                ])}
              />
            </section>
          );
        }
        if (manifest.case_id === 'C08') {
          const o = v.outputs as C08Outputs;
          return (
            <section key={v.variant_id}>
              <h4>{name}</h4>
              <Table
                head={[t('Rung', 'Peldaño'), 'R²', 'RMSE', 'MAE', 'Spearman', t('Calibration gap', 'Brecha de calibración')]}
                rows={o.rung_comparison.map((r) => [rungName(v, r.rung_id, lang), num(r.r2, lang, 4), num(r.rmse, lang, 4), num(r.mae, lang, 4), num(r.spearman, lang, 4), pct(r.calibration_gap, lang)])}
              />
            </section>
          );
        }
        const o = v.outputs as C09Outputs;
        const cur = o.ead_backtest.currency;
        const models = o.ead_models.map((m) => {
          const rs = o.ead_backtest.rows.filter((r) => r.model_id === m.model_id);
          const pred = rs.reduce((a, r) => a + (r.predicted_ead ?? 0), 0);
          const real = rs.reduce((a, r) => a + (r.realised_ead ?? 0), 0);
          const worst = rs.some((r) => r.light === 'red') ? 'red' : rs.some((r) => r.light === 'amber') ? 'amber' : 'green';
          return { m, pred, real, rel: real !== 0 ? (pred - real) / real : null, worst };
        });
        const light = { red: t('red', 'rojo'), amber: t('amber', 'ámbar'), green: t('green', 'verde') } as Record<string, string>;
        return (
          <section key={v.variant_id}>
            <h4>{name}</h4>
            <Table
              head={[t('EAD model', 'Modelo de EAD'), t('Predicted EAD', 'EAD predicha'), t('Realised EAD', 'EAD realizada'), t('Relative gap', 'Brecha relativa'), t('Worst band light', 'Peor luz por tramo')]}
              rows={models.map((r) => [r.m.model_id, money(r.pred, cur, lang), money(r.real, cur, lang), pct(r.rel, lang), light[r.worst] ?? r.worst])}
            />
          </section>
        );
      })}
    </div>
  );
}
