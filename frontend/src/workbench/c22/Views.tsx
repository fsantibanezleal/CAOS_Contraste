// C22's views (CT-309): the generators (Model), the measured size and power with the published reproductions
// (Validation), the live exact size and power of the count tests (Impact), the findings evidenced by measured rates,
// the families side by side (Variants) and the case (Context). Every replayed rate carries its Monte Carlo error.
import { PlotCard, Readout, formatNumber, pick, useShellLang, useWorkbenchState, type BiText } from '@fasl-work/caos-app-shell';
import { WithQuotes } from '../../content/bi';
import { UPlotChart, type ChartSeries } from '@fasl-work/caos-app-shell/chart';
import { useMemo } from 'react';
import { loadAllVariants, useArtifact } from '../../api/artifacts';
import { C22WriteUp } from '../../content/cases/C22';
import type { C22Simulation, Finding, VariantArtifact } from '../../lib/contract.types';
import { LightCell } from '../ValidationViews';
import { REPLAY, provenanceOf } from '../model';
import { Pending } from '../Pending';
import { COUNT_TESTS, curves, isC22, rateOf, rule, seriesStyle, useLiveCurves, useLivePortfolio, type C22Sel, type C22Variant } from './selection';

const LIVE = 'live' as const;
const pct = (lang: 'en' | 'es', v: number | null | undefined, decimals = 2) => formatNumber(v, lang, { percent: true, decimals });

const SEVERITY_TEXT: Record<string, BiText> = {
  S1: { en: 'S1 critical', es: 'S1 crítico' },
  S2: { en: 'S2 significant', es: 'S2 significativo' },
  S3: { en: 'S3 moderate', es: 'S3 moderado' },
  S4: { en: 'S4 minor', es: 'S4 menor' },
};
const STATUS_TEXT: Record<string, BiText> = {
  open: { en: 'open', es: 'abierto' },
  accepted: { en: 'accepted (a stated limit)', es: 'aceptado (un límite declarado)' },
  closed: { en: 'closed (fixed)', es: 'cerrado (corregido)' },
};

export function c22Of(sel: C22Sel | null): C22Variant | null {
  const v = sel?.data.variant as VariantArtifact<unknown> | undefined;
  return v && isC22(v) ? v : null;
}

/** "rate (SE)" of one simulation at a rule. */
function rateText(s: C22Simulation, ruleKey: string, lang: 'en' | 'es'): string {
  const r = rateOf(s, ruleKey);
  return r.rate === null ? '-' : `${pct(lang, r.rate)} (${pct(lang, r.se)})`;
}

// ---------------------------------------------------------------------------------------------------------------------
// Model: the generators

/** All the numbers of a (nested) numeric array, or null when it holds anything else. */
function numbers(x: unknown): number[] | null {
  if (typeof x === 'number') return [x];
  if (!Array.isArray(x)) return null;
  const out: number[] = [];
  for (const y of x) {
    const f = numbers(y);
    if (!f) return null;
    out.push(...f);
  }
  return out;
}

/** "key value" for each entry of a generator's configuration or truth: a value repeated across an array once with its
 * count, a short list in full, a square matrix by its size, a long list by its range; text and flags as they are. */
function describeRecord(rec: unknown, lang: 'en' | 'es'): string[] {
  const fmt = (v: number) => formatNumber(v, lang, { digits: 4 });
  const out: string[] = [];
  for (const [k, x] of Object.entries((rec ?? {}) as Record<string, unknown>)) {
    if (x === null) out.push(`${k} -`);
    else if (typeof x === 'string') out.push(`${k} ${x}`);
    else if (typeof x === 'boolean') out.push(`${k} ${pick(x ? { en: 'yes', es: 'sí' } : { en: 'no', es: 'no' }, lang)}`);
    else {
      const f = numbers(x);
      if (!f || f.length === 0) continue;
      const square = Array.isArray(x) && x.length > 2 && x.every((r) => Array.isArray(r) && r.length === x.length);
      if (f.every((v) => v === f[0])) out.push(f.length > 1 ? `${k} ${fmt(f[0])} (×${f.length})` : `${k} ${fmt(f[0])}`);
      else if (square) out.push(`${k} ${pick({ en: `${x.length} by ${x.length} matrix`, es: `matriz de ${x.length} por ${x.length}` }, lang)}`);
      else if (f.length <= 7) out.push(`${k} ${f.map(fmt).join('; ')}`);
      else out.push(`${k} ${fmt(Math.min(...f))} ${pick({ en: 'to', es: 'a' }, lang)} ${fmt(Math.max(...f))} (${f.length})`);
    }
  }
  return out;
}

export function GeneratorsView({ sel }: { sel: C22Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = c22Of(sel);
  if (!sel || !v) return <Pending />;
  const o = v.outputs;
  const config = (cfg: unknown) => describeRecord(cfg, lang).join(', ');
  // the truth beyond what the configuration already states, without the bibliographic reference
  const truth = (g: { config: unknown; truth: unknown }) => {
    const cfg = (g.config ?? {}) as Record<string, unknown>;
    const rest = Object.fromEntries(Object.entries((g.truth ?? {}) as Record<string, unknown>).filter(([k, x]) => k !== 'reference' && JSON.stringify(cfg[k]) !== JSON.stringify(x)));
    return describeRecord(rest, lang).join(', ');
  };
  const users = (ref: string) => [...new Set(o.simulations.filter((s) => s.generator === ref).map((s) => pick(s.label, lang)))].join(', ');
  return (
    <div className="caos-views-row" data-views="1">
      <div className="ct-col">
        <PlotCard
          fill
          title={{ en: 'The data-generating mechanisms of this family', es: 'Los mecanismos generadores de esta familia' }}
          lane={REPLAY}
          provenance={provenanceOf(v.provenance.truth_status)}
          dataKey={stateKey}
          note={{
            en: `${Object.keys(o.generators).length} generators from riskvalidation ${v.provenance.riskvalidation_version ?? ''}, each with its configuration and its exact truth committed; ${o.ladder ? `severity ladder: ${o.ladder.values.join(', ')} (${o.ladder.label.en})` : 'every test at the boundary of its null'}.`,
            es: `${Object.keys(o.generators).length} generadores de riskvalidation ${v.provenance.riskvalidation_version ?? ''}, cada uno con su configuración y su verdad exacta comprometidas; ${o.ladder ? `escala de severidad: ${o.ladder.values.map((x) => String(x).replace('.', ',')).join('; ')} (${o.ladder.label.es})` : 'cada prueba en la frontera de su nula'}.`,
          }}
        >
          <div className="ct-scroll">
            <table className="caos-table ct-wrap-head" data-table="generators">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Generator', es: 'Generador' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Class', es: 'Clase' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Configuration', es: 'Configuración' }, lang)}</th>
                  <th className="ct-text ct-wide-only">{pick({ en: 'Exact truth', es: 'Verdad exacta' }, lang)}</th>
                  <th className="ct-text ct-wide-only">{pick({ en: 'Tests measured on it', es: 'Pruebas medidas en él' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(o.generators).map(([ref, g]) => (
                  <tr key={ref} data-generator={ref}>
                    <td className="ct-text">{ref}</td>
                    <td className="ct-text">{g.name}</td>
                    <td className="ct-text">{config(g.config)}</td>
                    <td className="ct-text ct-wide-only">{truth(g)}</td>
                    <td className="ct-text ct-wide-only">{users(ref)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// Validation: power curves, the size table, p-values, the papers, one sample's report

/** The repetitions behind the view's points: the most common count, and the rows that differ from it. */
function repetitions(rows: C22Simulation[], lang: 'en' | 'es'): string {
  const counts = new Map<number, number>();
  for (const s of rows) counts.set(s.n_rep, (counts.get(s.n_rep) ?? 0) + 1);
  const mode = [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? 0;
  const odd = [...new Map(rows.filter((s) => s.n_rep !== mode).map((s) => [`${s.label.en}|${s.n_rep}`, s])).values()];
  const base = pick({ en: `${formatNumber(mode, 'en')} repetitions per point`, es: `${formatNumber(mode, 'es')} repeticiones por punto` }, lang);
  return odd.length ? `${base} (${odd.map((s) => `${pick(s.label, lang)}: ${formatNumber(s.n_rep, lang)}`).join('; ')})` : base;
}

/** A panel of designs rather than a ladder (one setting each, as the nested and non-nested DeLong designs): the rate
 * of each design at the level, read as a table, since a curve of one point says nothing. */
function DesignsTable({ rows, ruleKey }: { rows: C22Simulation[]; ruleKey: string }) {
  const lang = useShellLang();
  return (
    <div className="ct-scroll">
      <table className="caos-table ct-wrap-head" data-table="designs">
        <thead>
          <tr>
            <th className="ct-text">{pick({ en: 'Design', es: 'Diseño' }, lang)}</th>
            <th className="ct-text ct-wide-only">{pick({ en: 'Scenario', es: 'Escenario' }, lang)}</th>
            <th>{pick({ en: 'Repetitions', es: 'Repeticiones' }, lang)}</th>
            <th>{pick({ en: 'Rate (SE)', es: 'Tasa (EE)' }, lang)}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((s) => (
            <tr key={s.key} data-sim={s.key}>
              <td className="ct-text">{pick(s.label, lang)}</td>
              <td className="ct-text ct-wide-only">{pick(s.scenario, lang)}</td>
              <td>{formatNumber(s.n_rep, lang)}</td>
              <td>{rateText(s, ruleKey, lang)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Every panel of the family at once, one small multiple each: the rejection rate against the severity per test (its
 * exact curve dashed), the nominal level dotted; a panel of designs is a small table. */
export function PowerView({ sel }: { sel: C22Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = c22Of(sel);
  const panels = useMemo(() => {
    if (!sel || !v || !v.outputs.ladder) return null;
    const r = rule(sel.level);
    return v.outputs.panels.map((p) => {
      const groups = curves(v, p.id);
      // the union of the panel's settings, in order: a curve without a setting has a gap there, never a shifted point
      const x = [...new Set(groups.flatMap((g) => g.rows.map((s) => s.x)))].sort((a, b) => a - b);
      const at = (rows: C22Simulation[], pickValue: (s: C22Simulation) => number | null) =>
        x.map((xi) => {
          const s = rows.find((row) => row.x === xi);
          return s ? pickValue(s) : null;
        });
      const series: ChartSeries[] = groups.flatMap((g, i) => {
        const first = g.rows[0];
        const { color, dash } = seriesStyle(i);
        const out: ChartSeries[] = [{ label: first.label, values: at(g.rows, (s) => rateOf(s, r).rate), color, width: 2, dash }];
        if (g.rows.some((s) => s.exact)) out.push({ label: { en: `${first.label.en}, exact`, es: `${first.label.es}, exacta` }, values: at(g.rows, (s) => rateOf(s, r).exact), color, width: 1.2, dash: [6, 4] });
        return out;
      });
      series.push({ label: { en: 'Nominal level', es: 'Nivel nominal' }, values: x.map(() => sel.level), color: '--color-fg-subtle', width: 1, dash: [2, 4] });
      return { panel: p, x, series, rows: groups.flatMap((g) => g.rows), ruleKey: r };
    });
  }, [sel, v]);
  if (!sel || !v || !panels || !v.outputs.ladder) return <Pending />;
  const ladder = v.outputs.ladder;
  const allSize = v.outputs.panels.every((p) => p.measures === 'size');
  const mixed = !allSize && v.outputs.panels.some((p) => p.measures === 'size');
  return (
    <PlotCard
      fill
      title={
        allSize
          ? { en: `False alarms at ${pct('en', sel.level, 0)}: the model is right in every panel`, es: `Falsas alarmas al ${pct('es', sel.level, 0)}: el modelo es correcto en cada panel` }
          : { en: `Rejection rate at ${pct('en', sel.level, 0)}, every panel of the family`, es: `Tasa de rechazo al ${pct('es', sel.level, 0)}, cada panel de la familia` }
      }
      lane={REPLAY}
      provenance={provenanceOf(v.provenance.truth_status)}
      dataKey={stateKey}
      note={{
        en: `Against the family's ladder (${ladder.label.en}) unless a panel names its own axis; ${repetitions(v.outputs.simulations, 'en')}, so a rate's Monte Carlo SE is at most ${pct('en', 0.5 / Math.sqrt(Math.min(...v.outputs.simulations.map((s) => s.n_rep))), 1)}; dashed: the exact probability where one exists; dotted: the nominal level.`,
        es: `Contra la escala de la familia (${ladder.label.es}) salvo que un panel nombre su propio eje; ${repetitions(v.outputs.simulations, 'es')}, así que el EE de Monte Carlo de una tasa es a lo más ${pct('es', 0.5 / Math.sqrt(Math.min(...v.outputs.simulations.map((s) => s.n_rep))), 1)}; segmentada: la probabilidad exacta donde existe; punteada: el nivel nominal.`,
      }}
    >
      <div className="ct-panels-fill" data-views={String(panels.length)}>
        {panels.map((pp) => (
          <div key={pp.panel.id} className="ct-small-multiple" data-panel={pp.panel.id}>
            <p className="ct-sm-title">
              {pick(pp.panel.label, lang)}
              {mixed && pp.panel.measures === 'size' ? pick({ en: ' (sizes: the model is right)', es: ' (tamaños: el modelo es correcto)' }, lang) : ''}
            </p>
            {pp.x.length >= 2 ? (
              <UPlotChart
                height="fill"
                x={{ values: pp.x, label: pp.panel.axis ?? ladder.label, format: { digits: 3 } }}
                y={{ label: { en: 'Rejection rate', es: 'Tasa de rechazo' }, format: { percent: true, decimals: 0 }, range: [0, 1] }}
                series={pp.series}
              />
            ) : (
              <DesignsTable rows={pp.rows} ruleKey={pp.ruleKey} />
            )}
          </div>
        ))}
      </div>
    </PlotCard>
  );
}

/** Every rate of the family, panel by panel, with its SE, its Wilson interval, its scenario and the exact value. */
export function RatesTableView({ sel }: { sel: C22Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = c22Of(sel);
  if (!sel || !v) return <Pending />;
  const r = rule(sel.level);
  const label = Object.fromEntries(v.outputs.panels.map((p) => [p.id, p.label]));
  return (
    <div className="caos-views-row" data-views="1">
      <div className="ct-col">
        <PlotCard
          fill
          title={{ en: `Every rate of the family at ${pct('en', sel.level, 0)}`, es: `Cada tasa de la familia al ${pct('es', sel.level, 0)}` }}
          lane={REPLAY}
          provenance={provenanceOf(v.provenance.truth_status)}
          dataKey={stateKey}
          note={{ en: 'Rate (Monte Carlo SE), 95% Wilson interval, and the exact probability where one exists, with whether the rate agrees with it within 3.29 SE. The setting is on the panel\'s axis; the scenario states it in words.', es: 'Tasa (EE de Monte Carlo), intervalo de Wilson al 95%, y la probabilidad exacta donde existe, con si la tasa concuerda con ella dentro de 3,29 EE. El ajuste está en el eje del panel; el escenario lo dice en palabras.' }}
        >
          <div className="ct-scroll">
            <table className="caos-table ct-wrap-head" data-table="rates">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Panel', es: 'Panel' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Test', es: 'Prueba' }, lang)}</th>
                  <th>{pick({ en: 'Setting', es: 'Ajuste' }, lang)}</th>
                  <th className="ct-text ct-wide-only">{pick({ en: 'Scenario', es: 'Escenario' }, lang)}</th>
                  <th>{pick({ en: 'Rate (SE)', es: 'Tasa (EE)' }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: 'Wilson 95%', es: 'Wilson 95%' }, lang)}</th>
                  <th>{pick({ en: 'Exact', es: 'Exacta' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {v.outputs.simulations.map((s) => {
                  const x = rateOf(s, r);
                  return (
                    <tr key={s.key} data-sim={s.key}>
                      <td className="ct-text">{pick(label[s.panel] ?? { en: s.panel, es: s.panel }, lang)}</td>
                      <td className="ct-text">{pick(s.label, lang)}</td>
                      <td>{formatNumber(s.x, lang, { digits: 3 })}</td>
                      <td className="ct-text ct-wide-only">{pick(s.scenario, lang)}</td>
                      <td>{rateText(s, r, lang)}</td>
                      <td className="ct-wide-only">{`${pct(lang, x.lo, 1)} - ${pct(lang, x.hi, 1)}`}</td>
                      <td data-agrees={s.agrees?.[r] ? 'yes' : 'no'}>
                        {x.exact === null ? '-' : `${pct(lang, x.exact)}, ${pick(s.agrees?.[r] ? { en: 'agrees', es: 'concuerda' } : { en: 'differs', es: 'difiere' }, lang)}`}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
    </div>
  );
}

/** The null family: every test's size with its interval, its exact value and its verdict. */
export function SizeView({ sel }: { sel: C22Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = c22Of(sel);
  if (!sel || !v) return <Pending />;
  const r = rule(sel.level);
  const bound = v.outputs.size_bounds[r];
  const holds = (s: C22Simulation) => {
    const x = rateOf(s, r);
    return x.exact !== null ? x.exact <= sel.level + 1e-12 : (x.rate ?? 1) <= bound;
  };
  return (
    <div className="caos-views-row" data-views="1">
      <div className="ct-col">
        <PlotCard
          fill
          title={{ en: `Size of every test at ${pct('en', sel.level, 0)}`, es: `Tamaño de cada prueba al ${pct('es', sel.level, 0)}` }}
          lane={REPLAY}
          provenance={provenanceOf(v.provenance.truth_status)}
          dataKey={stateKey}
          note={{
            en: `The rejection rate when the test's null holds at its boundary (${v.outputs.simulations[0]?.n_rep.toLocaleString('en')} repetitions). A test holds its size when its exact probability is at most the level, or, without one, when the rate is at most ${pct('en', bound)} (the level plus 3.09 Monte Carlo SEs).`,
            es: `La tasa de rechazo cuando la nula de la prueba se cumple en su frontera (${v.outputs.simulations[0]?.n_rep.toLocaleString('es')} repeticiones). Una prueba mantiene su tamaño cuando su probabilidad exacta es a lo más el nivel, o, sin ella, cuando la tasa es a lo más ${pct('es', bound)} (el nivel más 3,09 EE de Monte Carlo).`,
          }}
        >
          <div className="ct-scroll">
            <table className="caos-table ct-wrap-head" data-table="size">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Test', es: 'Prueba' }, lang)}</th>
                  <th className="ct-text ct-wide-only">{pick({ en: 'Where its null holds', es: 'Dónde se cumple su nula' }, lang)}</th>
                  <th>{pick({ en: 'Rate (SE)', es: 'Tasa (EE)' }, lang)}</th>
                  <th>{pick({ en: 'Exact', es: 'Exacta' }, lang)}</th>
                  <th>{pick({ en: 'Size', es: 'Tamaño' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {v.outputs.simulations.map((s) => {
                  const x = rateOf(s, r);
                  const ok = holds(s);
                  return (
                    <tr key={s.key} data-sim={s.key} className={ok ? undefined : 'ct-current'}>
                      <td className="ct-text">{pick(s.label, lang)}</td>
                      <td className="ct-text ct-wide-only">{pick(s.scenario, lang)}</td>
                      <td>{rateText(s, r, lang)}</td>
                      <td>{x.exact === null ? '-' : pct(lang, x.exact)}</td>
                      <td data-holds={ok ? 'yes' : 'no'}>{pick(ok ? { en: 'holds', es: 'se mantiene' } : { en: 'exceeds', es: 'excede' }, lang)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
    </div>
  );
}

/** Under the null a p-value is uniform: its histogram is flat. One small multiple per panel, one curve per test. */
export function PValuesView({ sel }: { sel: C22Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = c22Of(sel);
  const panels = useMemo(() => {
    if (!v) return null;
    return v.outputs.panels
      .map((p) => {
        const rows = v.outputs.simulations.filter((s) => s.panel === p.id && s.p_histogram);
        const bins = rows[0]?.p_histogram?.length ?? 20;
        const x = Array.from({ length: bins }, (_, i) => (i + 0.5) / bins);
        const series: ChartSeries[] = rows.map((s, i) => {
          const total = (s.p_histogram ?? []).reduce((a, b) => a + b, 0) || 1;
          const label = s.key.endsWith('@null') ? s.label : { en: `${s.label.en} (${s.key.split('@')[1]})`, es: `${s.label.es} (${s.key.split('@')[1]})` };
          return { label, values: (s.p_histogram ?? []).map((c) => (c / total) * bins), width: 1.6, ...seriesStyle(i) };
        });
        series.push({ label: { en: 'Uniform', es: 'Uniforme' }, values: x.map(() => 1), color: '--color-fg-subtle', width: 1, dash: [2, 4] });
        return { panel: p, x, series, n: rows.length };
      })
      .filter((p) => p.n > 0);
  }, [v]);
  if (!sel || !v || !panels) return <Pending />;
  return (
    <PlotCard
      fill
      title={{ en: 'The p-values under the null, panel by panel', es: 'Los valores p bajo la nula, panel por panel' }}
      lane={REPLAY}
      provenance={provenanceOf(v.provenance.truth_status)}
      dataKey={stateKey}
      note={{ en: 'Density of the p-values in 20 bins (1 = uniform). A test with an exact continuous null is flat; a discrete or conservative one piles up near 1; an oversized one rises near 0.', es: 'Densidad de los valores p en 20 intervalos (1 = uniforme). Una prueba con nula continua exacta es plana; una discreta o conservadora se acumula cerca de 1; una sobredimensionada sube cerca de 0.' }}
    >
      <div className="ct-panels-fill" data-views={String(panels.length)}>
        {panels.map((pp) => (
          <div key={pp.panel.id} className="ct-small-multiple" data-panel={pp.panel.id}>
            <p className="ct-sm-title">{pick(pp.panel.label, lang)}</p>
            <UPlotChart
              height="fill"
              x={{ values: pp.x, label: { en: 'p-value', es: 'Valor p' }, format: { decimals: 2 } }}
              y={{ label: { en: 'Density', es: 'Densidad' }, format: { decimals: 1 } }}
              series={pp.series}
            />
          </div>
        ))}
      </div>
    </PlotCard>
  );
}

/** The published simulations, cell by cell: the published rate against the harness's. */
export function PaperView({ sel }: { sel: C22Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = c22Of(sel);
  const chart = useMemo(() => {
    if (!v || v.outputs.golden.length === 0) return null;
    const cells = v.outputs.golden.flatMap((g) => g.cells.map((c) => ({ ...c, study: g.study }))).sort((a, b) => a.published - b.published);
    const x = cells.map((c) => c.published);
    return {
      x,
      series: [
        { label: { en: 'Agrees', es: 'Concuerda' }, values: cells.map((c) => (c.agrees ? c.measured : null)), color: '--color-accent' as const, width: 1, mode: 'points' as const },
        { label: { en: 'Does not agree', es: 'No concuerda' }, values: cells.map((c) => (c.agrees ? null : c.measured)), color: '--color-bad' as const, width: 1, mode: 'points' as const },
        { label: { en: 'Published = measured', es: 'Publicada = medida' }, values: x, color: '--color-fg-subtle' as const, width: 1, dash: [4, 4] },
      ],
    };
  }, [v]);
  if (!sel || !v) return <Pending />;
  if (!chart) return <p className="ct-note">{pick({ en: 'No published simulation is reproduced in this family.', es: 'Ninguna simulación publicada se reproduce en esta familia.' }, lang)}</p>;
  const g = v.outputs.golden;
  return (
    <>
      <PlotCard
        title={{ en: 'The published studies', es: 'Los estudios publicados' }}
        lane={REPLAY}
        provenance={provenanceOf(v.provenance.truth_status)}
        dataKey={stateKey}
      >
        <ul className="ct-stack-natural">
          {g.map((s) => (
            <li key={s.study} data-study={s.study}>
              <strong>{pick(s.title, lang)}</strong>: {pick({ en: `${s.agree} of ${s.total} cells agree within 3.29 combined SEs (${s.runs.toLocaleString('en')} runs, as published). `, es: `${s.agree} de ${s.total} celdas concuerdan dentro de 3,29 EE combinados (${s.runs.toLocaleString('es')} corridas, como se publicó). ` }, lang)}
              <WithQuotes text={pick(s.note, lang)} />
            </li>
          ))}
        </ul>
      </PlotCard>
      <PlotCard
        fill
        title={{ en: 'Published rate against the harness', es: 'Tasa publicada contra el arnés' }}
        lane={REPLAY}
        provenance={provenanceOf(v.provenance.truth_status)}
        dataKey={stateKey}
      >
        <UPlotChart
          height="fill"
          x={{ values: chart.x, label: { en: 'Published', es: 'Publicada' }, format: { percent: true, decimals: 0 } }}
          y={{ label: { en: 'Measured', es: 'Medida' }, format: { percent: true, decimals: 0 }, range: [0, 1] }}
          series={chart.series}
        />
      </PlotCard>
    </>
  );
}

/** What the tests say about one dataset of the family (the committed policy's lights, the rail's thresholds). */
export function SpecimenView({ sel }: { sel: C22Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = c22Of(sel);
  if (!sel || !v) return <Pending />;
  return (
    <div className="caos-views-row" data-views="1">
      <div className="ct-col">
        <PlotCard
          fill
          title={{ en: 'One sample, one report', es: 'Una muestra, un reporte' }}
          lane={REPLAY}
          provenance={provenanceOf(v.provenance.truth_status)}
          dataKey={stateKey}
          note={{
            en: `The tests on one dataset drawn at severity ${v.outputs.specimen.severity}: what a validator would read in a single report. The rates of the other views say how often such a report is right.`,
            es: `Las pruebas sobre un conjunto generado con severidad ${v.outputs.specimen.severity}: lo que un validador leería en un solo reporte. Las tasas de las otras vistas dicen con qué frecuencia ese reporte acierta.`,
          }}
        >
          <div className="ct-scroll">
            <table className="caos-table" data-table="specimen">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Test', es: 'Prueba' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Generator', es: 'Generador' }, lang)}</th>
                  <th>{pick({ en: 'Statistic', es: 'Estadístico' }, lang)}</th>
                  <th>{pick({ en: 'p-value', es: 'Valor p' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {v.tests.map((t, i) => (
                  <tr key={`${t.test_id}-${i}`}>
                    <td className="ct-text">{t.test_id}</td>
                    <td className="ct-text">{t.model_id}</td>
                    <td>{formatNumber(t.statistic ?? t.metric, lang, { digits: 4 })}</td>
                    <LightCell row={t} alphas={sel.alphas} />
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
    </div>
  );
}

/** The estimators the null family measures: the AUC and its ECB standard error, the ECE when the PDs are right. */
export function EstimatorsView({ sel }: { sel: C22Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = c22Of(sel);
  if (!sel || !v || !v.outputs.estimators) return <Pending />;
  const a = v.outputs.estimators.auc;
  const e = v.outputs.estimators.ece_when_right;
  const num = (x: number | undefined, d = 5) => formatNumber(x ?? null, lang, { decimals: d });
  return (
    <div className="caos-views-row" data-views="1">
      <div className="ct-col">
        <PlotCard
          fill
          title={{ en: 'Estimators against their truth', es: 'Estimadores contra su verdad' }}
          lane={REPLAY}
          provenance={provenanceOf(v.provenance.truth_status)}
          dataKey={stateKey}
          note={{ en: 'The performance measures of Morris, White and Crowther (2019), each with its Monte Carlo SE: the AUC of binormal scores (150 defaulters, 4,850 survivors, true AUC 0.80) and the expected calibration error of right PDs (5,000 obligors).', es: 'Las medidas de desempeño de Morris, White y Crowther (2019), cada una con su EE de Monte Carlo: el AUC de puntajes binormales (150 incumplidos, 4.850 sobrevivientes, AUC verdadera 0,80) y el error de calibración esperado de PD correctas (5.000 deudores).' }}
        >
          <table className="caos-table" data-table="estimators">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Measure', es: 'Medida' }, lang)}</th>
                <th>{pick({ en: 'Value', es: 'Valor' }, lang)}</th>
                <th>{pick({ en: 'Monte Carlo SE', es: 'EE de Monte Carlo' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="ct-text">{pick({ en: 'AUC: bias', es: 'AUC: sesgo' }, lang)}</td><td>{num(a.bias)}</td><td>{num(a.bias_mcse)}</td></tr>
              <tr><td className="ct-text">{pick({ en: 'AUC: empirical SE', es: 'AUC: EE empírico' }, lang)}</td><td>{num(a.empirical_se)}</td><td>{num(a.empirical_se_mcse)}</td></tr>
              <tr><td className="ct-text">{pick({ en: 'AUC: exact SE (Hanley and McNeil)', es: 'AUC: EE exacto (Hanley y McNeil)' }, lang)}</td><td>{num(a.exact_se)}</td><td>-</td></tr>
              <tr><td className="ct-text">{pick({ en: 'AUC: ECB SE (average)', es: 'AUC: EE del BCE (promedio)' }, lang)}</td><td>{num(a.model_se)}</td><td>-</td></tr>
              <tr><td className="ct-text">{pick({ en: 'AUC: coverage of the 95% interval', es: 'AUC: cobertura del intervalo al 95%' }, lang)}</td><td>{pct(lang, a.coverage)}</td><td>{pct(lang, a.coverage_mcse)}</td></tr>
              <tr><td className="ct-text">{pick({ en: 'ECE when the PDs are right (its bias)', es: 'ECE cuando las PD son correctas (su sesgo)' }, lang)}</td><td>{num(e.mean)}</td><td>{num(e.bias_mcse)}</td></tr>
            </tbody>
          </table>
        </PlotCard>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// Impact: the live exact size and power for the rail's portfolio

export function LiveCalculatorView({ sel }: { sel: C22Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const live = useLiveCurves(sel);
  const v = c22Of(sel);
  if (!sel || !v || !live) return <Pending />;
  const p = sel.portfolio;
  const prov = provenanceOf(v.provenance.truth_status);
  const level = pct(lang, sel.level, 0);
  const nominal = (xs: number[]) => ({ label: { en: 'Nominal level', es: 'Nivel nominal' }, values: xs.map(() => sel.level), color: '--color-fg-subtle' as const, width: 1, dash: [2, 4] });
  const impact = Object.entries(v.impact);
  return (
    <>
      <PlotCard
        title={{ en: "The family's decision numbers", es: 'Los números de decisión de la familia' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
      >
        <table className="caos-table ct-wrap-head" data-table="impact">
          <tbody>
            {impact.map(([k, it]) => (
              <tr key={k} data-impact={k}>
                <td className="ct-text">{pick(it.label, lang)}</td>
                <td>{it.unit === 'probability' ? pct(lang, it.value, 1) : formatNumber(it.value, lang, { digits: 4 })}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </PlotCard>
      <div className="caos-views-row" data-views="2">
        <div className="ct-col">
        <PlotCard
          fill
          title={{ en: `Power against the true-to-applied PD, at ${level}`, es: `Potencia según PD verdadera sobre aplicada, al ${level}` }}
          lane={LIVE}
          provenance={prov}
          dataKey={stateKey}
          note={{ en: `${p.n.toLocaleString('en')} obligors, PD applied ${pct('en', p.pd)}, true correlation ${pct('en', p.rhoTrue, 1)}; exact, recomputed in your browser.`, es: `${p.n.toLocaleString('es')} deudores, PD aplicada ${pct('es', p.pd)}, correlación verdadera ${pct('es', p.rhoTrue, 1)}; exacta, recalculada en su navegador.` }}
        >
          <UPlotChart
            height="fill"
            x={{ values: live.ratios, label: { en: 'True PD / PD applied', es: 'PD verdadera / PD aplicada' }, format: { decimals: 1 } }}
            y={{ label: { en: 'Rejection probability', es: 'Probabilidad de rechazo' }, format: { percent: true, decimals: 0 }, range: [0, 1] }}
            series={[...live.byRatio.map((s) => ({ label: s.label, values: s.values, color: s.color, width: 2 })), nominal(live.ratios)]}
            marks={[{ x: p.ratio, label: { en: 'rail', es: 'panel' } }]}
          />
        </PlotCard>
        </div>
        <div className="ct-col">
        <PlotCard
          fill
          title={{ en: `Rejection against the true correlation, at ${level}`, es: `Rechazo según la correlación verdadera, al ${level}` }}
          lane={LIVE}
          provenance={prov}
          dataKey={stateKey}
          note={{ en: `At the rail's ratio ${formatNumber(p.ratio, 'en', { decimals: 2 })} (1 is the size); the Vasicek test assumes ${pct('en', p.rhoAssumed, 0)}.`, es: `Con la razón del panel ${formatNumber(p.ratio, 'es', { decimals: 2 })} (1 es el tamaño); la prueba de Vasicek supone ${pct('es', p.rhoAssumed, 0)}.` }}
        >
          <UPlotChart
            height="fill"
            x={{ values: live.rhos, label: { en: 'True asset correlation', es: 'Correlación de activos verdadera' }, format: { percent: true, decimals: 0 } }}
            y={{ label: { en: 'Rejection probability', es: 'Probabilidad de rechazo' }, format: { percent: true, decimals: 0 }, range: [0, 1] }}
            series={[...live.byRho.map((s) => ({ label: s.label, values: s.values, color: s.color, width: 2 })), nominal(live.rhos)]}
            marks={[{ x: p.rhoTrue, label: { en: 'rail', es: 'panel' } }]}
          />
        </PlotCard>
        </div>
      </div>
    </>
  );
}

/** The rail's read-out: the three count tests' exact rejection probability for the portfolio. */
export function PortfolioReadout({ sel }: { sel: C22Sel | null }) {
  const stateKey = useWorkbenchState()?.stateKey;
  const live = useLivePortfolio(sel);
  const v = c22Of(sel);
  return (
    <Readout
      title={{ en: sel && sel.portfolio.ratio === 1 ? 'Size (exact)' : 'Power (exact)', es: sel && sel.portfolio.ratio === 1 ? 'Tamaño (exacto)' : 'Potencia (exacta)' }}
      lane={LIVE}
      provenance={provenanceOf(v?.provenance.truth_status)}
      dataKey={stateKey}
      items={(live ?? COUNT_TESTS.map((t) => ({ ...t, at5: null, at1: null }))).map((t) => ({
        label: t.label,
        value: t.at5 && sel ? (sel.level === 0.01 ? t.at1?.probability ?? null : t.at5.probability) : null,
        unitless: true,
        format: { percent: true, decimals: 2 },
        hint: t.at5 ? { en: `Rejects from ${(sel?.level === 0.01 ? t.at1 : t.at5)?.criticalCount ?? '-'} defaults.`, es: `Rechaza desde ${(sel?.level === 0.01 ? t.at1 : t.at5)?.criticalCount ?? '-'} incumplimientos.` } : undefined,
      }))}
    />
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// Findings, Variants, Context

export function C22FindingsView({ sel }: { sel: C22Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = c22Of(sel);
  if (!sel || !v) return <Pending />;
  const order = ['S1', 'S2', 'S3', 'S4'];
  const findings: Finding[] = [...v.findings].sort((a, b) => order.indexOf(a.severity) - order.indexOf(b.severity));
  const sim = (e: string) => v.outputs.simulations.find((s) => `rate:${s.key}` === e);
  const r = rule(sel.level);
  // every cited rate, numbered in reading order: the table's [k] and the chart's x
  const points = findings.flatMap((f) => f.evidence.map((e) => ({ key: `${f.id}|${e}`, s: sim(e) }))).filter((x) => x.s);
  const number = new Map(points.map((x, i) => [x.key, i + 1]));
  // half a step of room on each side, so the first and last points are not cut by the plot's edges
  const xs = [0.5, ...points.map((_, i) => i + 1), points.length + 0.5];
  const pad = (vals: Array<number | null>): Array<number | null> => [null, ...vals, null];
  const prov = provenanceOf(v.provenance.truth_status);
  return (
    <div className="caos-views-row" data-views="2">
      <div className="ct-col ct-findings-table">
        <PlotCard
          fill
          title={{ en: 'What the measurements found', es: 'Lo que encontraron las mediciones' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{ en: "Each finding cites the measured rates behind it, at the rail's level, with their Monte Carlo SE; the numbers are the chart's.", es: 'Cada hallazgo cita las tasas medidas que lo respaldan, al nivel del panel, con su EE de Monte Carlo; los números son los del gráfico.' }}
        >
          <div className="ct-scroll">
            <table className="caos-table" data-table="findings">
              <thead>
                <tr>
                  <th>{pick({ en: 'Severity', es: 'Severidad' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Finding', es: 'Hallazgo' }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: 'Status', es: 'Estado' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {findings.map((f) => (
                  <tr key={f.id} data-finding={f.id}>
                    <td>{pick(SEVERITY_TEXT[f.severity], lang)}</td>
                    <td className="ct-text">
                      {pick(f.title, lang)}
                      <ul className="ct-evidence">
                        {f.evidence.map((e) => {
                          const s = sim(e);
                          const k = number.get(`${f.id}|${e}`);
                          return <li key={e}>{s ? `[${k}] ${pick(s.label, lang)}, ${pick(s.scenario, lang)}: ${rateText(s, r, lang)}` : e}</li>;
                        })}
                      </ul>
                    </td>
                    <td className="ct-wide-only">{pick(STATUS_TEXT[f.status], lang)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
      <div className="ct-col ct-findings-chart">
        <PlotCard
          fill
          title={{ en: 'The cited rates', es: 'Las tasas citadas' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{ en: `Each cited rate at ${pct('en', sel.level, 0)}, numbered as in the table, with its 95% Wilson interval, against the nominal level.`, es: `Cada tasa citada al ${pct('es', sel.level, 0)}, numerada como en la tabla, con su intervalo de Wilson al 95%, contra el nivel nominal.` }}
        >
          <UPlotChart
            height="fill"
            x={{ values: xs, label: { en: 'Cited rate (the number in the table)', es: 'Tasa citada (el número de la tabla)' }, format: { decimals: 0 } }}
            y={{ label: { en: 'Rejection rate', es: 'Tasa de rechazo' }, format: { percent: true, decimals: 0 }, range: [0, 1] }}
            series={[
              { label: { en: 'Rate', es: 'Tasa' }, values: pad(points.map((x) => (x.s ? rateOf(x.s, r).rate : null))), color: '--color-accent', mode: 'points' },
              { label: { en: 'Wilson 95%, low', es: 'Wilson 95%, inferior' }, values: pad(points.map((x) => (x.s ? rateOf(x.s, r).lo : null))), color: '--color-fg-subtle', mode: 'points' },
              { label: { en: 'Wilson 95%, high', es: 'Wilson 95%, superior' }, values: pad(points.map((x) => (x.s ? rateOf(x.s, r).hi : null))), color: '--color-fg-subtle', mode: 'points' },
              { label: { en: 'Nominal level', es: 'Nivel nominal' }, values: xs.map(() => sel.level), color: '--color-warn', width: 1.2, dash: [6, 4] },
            ]}
          />
        </PlotCard>
      </div>
    </div>
  );
}

/** The shade of a rate: 0 below 5%, then 5% to 20%, 20% to 50%, 50% to 80%, 80% and above. */
const heat = (r: number | null) => (r === null ? 'none' : r < 0.05 ? '0' : r < 0.2 ? '1' : r < 0.5 ? '2' : r < 0.8 ? '3' : '4');

/** A test's cell in one family: its power at the highest severity where the family plants a defect the test should
 * see, else its false-alarm rate there where the model is right (a size panel). */
export function familyCell(f: C22Variant, testId: string, r: string): { rate: number | null; kind: 'power' | 'size' } | null {
  const kinds: Array<'power' | 'size'> = ['power', 'size'];
  for (const kind of kinds) {
    const panels = new Set(f.outputs.panels.filter((p) => p.measures === kind).map((p) => p.id));
    const rows = f.outputs.simulations.filter((x) => x.test_id === testId && panels.has(x.panel) && x.key.split('@').length === 2);
    if (rows.length === 0) continue;
    const top = Math.max(...rows.map((x) => x.severity));
    if (top === 0) continue;
    return { rate: Math.max(...rows.filter((x) => x.severity === top).map((x) => rateOf(x, r).rate ?? 0)), kind };
  }
  return null;
}

/** The families side by side: which test sees which defect. A row per test with a p-value; the null column is its
 * size, each defect column its rate at the family's highest severity on the family's ladder; a column header loads the
 * family. */
export function C22VariantsView({ sel, onPick }: { sel: C22Sel | null; onPick: (id: string) => void }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  const fams = useMemo(() => (all.state === 'ready' ? (all.data as VariantArtifact<unknown>[]).filter(isC22) : []), [all]);
  const matrix = useMemo(() => {
    if (!sel || fams.length === 0) return null;
    const r = rule(sel.level);
    const nul = fams.find((f) => f.outputs.ladder === null);
    const tests = nul ? nul.outputs.simulations.filter((s) => s.key.endsWith('@null')) : [];
    const cells = (f: C22Variant, testId: string) => {
      if (f.outputs.ladder === null) {
        const s = f.outputs.simulations.find((x) => x.key === `${testId}@null`);
        return s ? { rate: rateOf(s, r).exact ?? rateOf(s, r).rate, kind: 'size' as const } : null;
      }
      return familyCell(f, testId, r);
    };
    return { tests, rows: tests.map((s) => ({ s, cells: fams.map((f) => cells(f, s.test_id)) })) };
  }, [sel, fams]);
  if (!sel || all.state !== 'ready' || !matrix) return <Pending />;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const short = (id: string) => entries.find((e) => e.variant_id === id)?.short_title ?? { en: id, es: id };
  const prov = provenanceOf((sel.data.variant as VariantArtifact<unknown>).provenance.truth_status);
  const current = (sel.data.variant as VariantArtifact<unknown>).variant_id;
  return (
    <div className="caos-views-row" data-views="1">
      <div className="ct-col">
        <PlotCard
          fill
          title={{ en: `Which test sees which defect, at ${pct('en', sel.level, 0)}`, es: `Qué prueba ve qué defecto, al ${pct('es', sel.level, 0)}` }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: "Each cell is the test's rejection rate at the family's highest severity. Blue: its power, where the family plants a defect the test should see. Amber: a false alarm, where the model is right and an assumption fails (correlated defaults, a covariate shift, an estimated development AUC), and in the null column the test's size (exact where it exists). Darker: a higher rate; blank: a test the family does not measure. A column header loads the family.",
            es: 'Cada celda es la tasa de rechazo de la prueba en la mayor severidad de la familia. Azul: su potencia, donde la familia planta un defecto que la prueba debería ver. Ámbar: una falsa alarma, donde el modelo es correcto y falla un supuesto (incumplimientos correlacionados, un desplazamiento de covariables, un AUC de desarrollo estimado), y en la columna nula el tamaño de la prueba (exacto donde existe). Más oscuro: una tasa mayor; vacía: una prueba que la familia no mide. El encabezado de una columna carga la familia.',
          }}
        >
          <div className="ct-scroll">
            <table className="caos-table ct-wrap-head ct-heat-table" data-table="detections">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Test', es: 'Prueba' }, lang)}</th>
                  {fams.map((f) => (
                    <th key={f.variant_id} data-variant={f.variant_id} className={f.variant_id === current ? 'ct-heat-current' : undefined}>
                      <button type="button" className="ct-linkbutton" onClick={() => onPick(f.variant_id)}>
                        {pick(short(f.variant_id), lang)}
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.rows.map(({ s, cells }) => (
                  <tr key={s.test_id} data-test={s.test_id}>
                    <td className="ct-text">{pick(s.label, lang)}</td>
                    {cells.map((c, k) => (
                      <td key={fams[k].variant_id} className="ct-heat" data-heat={heat(c?.rate ?? null)} data-kind={c?.kind}>
                        {c ? pct(lang, c.rate, 1) : ''}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlotCard>
      </div>
    </div>
  );
}

export function C22ContextView({ sel }: { sel: C22Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  if (!sel) return <Pending />;
  const m = sel.data.manifest;
  const v = sel.data.variant as VariantArtifact<unknown>;
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case', es: 'El caso' }} lane={REPLAY} provenance={provenanceOf(v.provenance.truth_status)} dataKey={stateKey}>
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <table className="caos-table" data-sources={m.sources.join(' ')}>
          <thead>
            <tr>
              <th className="caos-col-text">{pick({ en: 'Source', es: 'Fuente' }, lang)}</th>
              <th className="caos-col-text">{pick({ en: 'Licence and class', es: 'Licencia y clase' }, lang)}</th>
              <th className="caos-col-text">{pick({ en: 'Attribution', es: 'Atribución' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {m.sources.map((id) => {
              const s = m.source_details[id];
              return (
                <tr key={id} data-licence-class={s.class}>
                  <td className="caos-col-text">
                    <a href={s.landing} target="_blank" rel="noreferrer">{s.name}</a>
                  </td>
                  <td className="caos-col-text">{s.licence} ({s.class})</td>
                  <td className="caos-col-text">{s.attribution}</td>
                </tr>
              );
            })}
            <tr data-licence-class="generator">
              <td className="caos-col-text">{pick({ en: "riskvalidation's generators (Contraste's own)", es: 'Generadores de riskvalidation (de Contraste)' }, lang)}</td>
              <td className="caos-col-text">{pick({ en: 'MIT, no third-party data', es: 'MIT, sin datos de terceros' }, lang)}</td>
              <td className="caos-col-text">{pick({ en: 'Every rate is measured on seeded data with a known truth; the papers give only the published rates the harness is held to.', es: 'Cada tasa se mide en datos con semilla y verdad conocida; los artículos aportan solo las tasas publicadas contra las que se contrasta el arnés.' }, lang)}</td>
            </tr>
          </tbody>
        </table>
        <p className="ct-note">
          {pick(
            {
              en: `Truth status of this variant: ${v.provenance.truth_status}. The readers check each paper against its own print (WP14's Tables 5 to 8 name its eight scenarios, each with its 16 parameters and every rate in [0, 1], and Table 6 repeats Table 5's forecasts; Yurdakul and Naranjo's Table 4 has its six pairs of sample sizes and a benchmark near 5% without a shift) and refuse the bake otherwise. riskvalidation ${m.engine.riskvalidation ?? ''}.`,
              es: `Estado de verdad de esta variante: ${v.provenance.truth_status}. Los lectores verifican cada artículo contra su propia impresión (las tablas 5 a 8 de WP14 nombran sus ocho escenarios, cada uno con sus 16 parámetros y cada tasa en [0, 1], y la tabla 6 repite los pronósticos de la tabla 5; la tabla 4 de Yurdakul y Naranjo tiene sus seis pares de tamaños de muestra y una referencia cercana al 5% sin desplazamiento) y si no, rechazan el horneado. riskvalidation ${m.engine.riskvalidation ?? ''}.`,
            },
            lang,
          )}
        </p>
        <C22WriteUp />
      </PlotCard>
    </div>
  );
}
