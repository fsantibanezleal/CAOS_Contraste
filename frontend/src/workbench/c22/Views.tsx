// C22's views (CT-309): the generators (Model), the measured size and power with the published reproductions
// (Validation), the live exact size and power of the count tests (Impact), the findings evidenced by measured rates,
// the families side by side (Variants) and the case (Context). Every replayed rate carries its Monte Carlo error.
import { PlotCard, Readout, ViewsRow, formatNumber, pick, useShellLang, useWorkbenchState, type BiText } from '@fasl-work/caos-app-shell';
import { WithQuotes } from '../../content/bi';
import { UPlotChart, type ChartSeries } from '@fasl-work/caos-app-shell/chart';
import { useMemo } from 'react';
import { loadAllVariants, useArtifact } from '../../api/artifacts';
import { C22WriteUp } from '../../content/cases/C22';
import { TRUTH_TEXT } from '../../content/cases/C04Results';
import type { C22Simulation, Finding, VariantArtifact } from '../../lib/contract.types';
import { useFindingsShares } from '../../lib/useMedia';
import './c22-flow.css';
import { LightCell } from '../ValidationViews';
import { testName } from '../c20/U14Common';
import { REPLAY, provenanceOf } from '../model';
import { evidenceText } from '../names';
import { Pending } from '../Pending';
import { COUNT_TESTS, curves, excessOf, isC22, rateOf, rowKeyOf, rule, seriesStyle, useLiveCurves, useLivePortfolio, type C22Sel, type C22Variant } from './selection';
import { CODE_BREAKS_STYLE, codeBreaks } from './codeBreaks';

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

/** The nominal level of the tests, a reference line of every rate plot (a yMark, not a series). */
const NOMINAL = (level: number) => ({ y: level, label: { en: 'Nominal level', es: 'Nivel nominal' }, tone: 'neutral' as const });

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
function describeRecord(rec: unknown, lang: 'en' | 'es'): Array<{ k: string; v: string }> {
  // a value under 1e-12 in size is 0: no "-0" and no floating-point noise shown as a truth (U16-R3 c22 m2, m3)
  const fmt = (v: number) => formatNumber(Math.abs(v) < 1e-12 ? 0 : v, lang, { digits: 4 });
  const out: Array<{ k: string; v: string }> = [];
  for (const [k, x] of Object.entries((rec ?? {}) as Record<string, unknown>)) {
    if (x === null) out.push({ k, v: '-' });
    else if (typeof x === 'string') out.push({ k, v: x });
    else if (typeof x === 'boolean') out.push({ k, v: pick(x ? { en: 'yes', es: 'sí' } : { en: 'no', es: 'no' }, lang) });
    else {
      const f = numbers(x);
      if (!f || f.length === 0) continue;
      const square = Array.isArray(x) && x.length > 2 && x.every((r) => Array.isArray(r) && r.length === x.length);
      if (f.every((v) => v === f[0])) out.push({ k, v: f.length > 1 ? `${fmt(f[0])} (×${f.length})` : fmt(f[0]) });
      else if (square) out.push({ k, v: pick({ en: `${x.length} by ${x.length} matrix`, es: `matriz de ${x.length} por ${x.length}` }, lang) });
      else if (f.length <= 7) out.push({ k, v: f.map(fmt).join('; ') });
      else out.push({ k, v: `${fmt(Math.min(...f))} ${pick({ en: 'to', es: 'a' }, lang)} ${fmt(Math.max(...f))} (${f.length})` });
    }
  }
  return out;
}

/** The Spanish of the two published sources of C22 (the manifest writes them in English): the paper's title as published, the part of it the
 * case reads, and its licence statement (U16-R3 c22 B4). */
const SOURCE_ES: Record<string, { title: string; part: string; licence_en: string; licence: string }> = {
  'bcbs-wp14': {
    title: 'Studies on the Validation of Internal Rating Systems (revised)',
    part: ', Working Paper 14, tablas 5 a 8 (la simulación de las pruebas normal y de semáforos)',
    licence_en: '© Bank for International Settlements 2005. All rights reserved. Brief excerpts may be reproduced or translated provided the source is stated.',
    licence: '© Bank for International Settlements 2005. Todos los derechos reservados. Se pueden reproducir o traducir extractos breves siempre que se cite la fuente.',
  },
  'yurdakul-naranjo-2020': {
    title: 'Statistical properties of the population stability index',
    part: ', tabla 4 (las tasas de rechazo de las reglas del PSI y de la prueba chi-cuadrado de referencia)',
    licence_en: 'Copyright Infopro Digital Limited 2021. All rights reserved. You may share using our article tools. This article may be printed for the sole use of the Authorised User (named subscriber), as outlined in our terms and conditions.',
    licence: 'Copyright Infopro Digital Limited 2021. Todos los derechos reservados. Puede compartirse con las herramientas de artículo del editor. Este artículo puede imprimirse para uso exclusivo del Usuario Autorizado (el suscriptor nombrado), según sus términos y condiciones.',
  },
};

/** The licence classes of a source in words. */
const LICENCE_CLASS_TEXT: Record<string, { en: string; es: string }> = {
  'derived-only': { en: 'derived only', es: 'solo derivado' },
  'mirror-allowed': { en: 'mirror allowed', es: 'espejo permitido' },
};

/** A record of keys and values for a cell: the generator's own keys are code (they are identifiers, not words), the values are read in the language. */
function RecordText({ items }: { items: Array<{ k: string; v: string }> }) {
  return (
    <>
      {items.map((it, i) => (
        <span key={it.k}>
          {i > 0 ? ', ' : ''}
          <code translate="no">{it.k}</code> {it.v}
        </span>
      ))}
    </>
  );
}

export function GeneratorsView({ sel }: { sel: C22Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = c22Of(sel);
  if (!sel || !v) return <Pending />;
  const o = v.outputs;
  const config = (cfg: unknown) => describeRecord(cfg, lang);
  // the truth beyond what the configuration already states, without the bibliographic reference
  const truth = (g: { config: unknown; truth: unknown }) => {
    const cfg = (g.config ?? {}) as Record<string, unknown>;
    const rest = Object.fromEntries(Object.entries((g.truth ?? {}) as Record<string, unknown>).filter(([k, x]) => k !== 'reference' && JSON.stringify(cfg[k]) !== JSON.stringify(x)));
    return describeRecord(rest, lang);
  };
  const users = (ref: string) => [...new Set(o.simulations.filter((s) => s.generator === ref).map((s) => pick(s.label, lang)))].join(', ');
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The data-generating mechanisms of this family', es: 'Los mecanismos generadores de esta familia' }}
        lane={REPLAY}
        provenance={provenanceOf(v.provenance.truth_status)}
        dataKey={stateKey}
        note={{
          en: `${Object.keys(o.generators).length} generators from riskvalidation ${v.provenance.riskvalidation_version ?? ''}, each with its configuration and its exact truth committed; ${o.ladder ? `severity ladder: ${o.ladder.values.join(', ')}; ${o.ladder.label.en}` : 'every test at the boundary of its null'}.`,
          es: `${Object.keys(o.generators).length} generadores de riskvalidation ${v.provenance.riskvalidation_version ?? ''}, cada uno con su configuración y su verdad exacta versionadas; ${o.ladder ? `escala de severidad: ${o.ladder.values.map((x) => String(x).replace('.', ',')).join('; ')}; ${o.ladder.label.es}` : 'cada prueba en la frontera de su nula'}.`,
        }}
      >
        <div className="ct-scroll" data-caos-flow="">
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
                  {/* the engine's own reference and class of a generator: code, as its configuration keys (an engine-configuration
                      appendix; ruling of 2026-10-24) */}
                  <td className="ct-text"><code translate="no" style={CODE_BREAKS_STYLE}>{codeBreaks(ref)}</code></td>
                  <td className="ct-text"><code translate="no" style={CODE_BREAKS_STYLE}>{codeBreaks(g.name)}</code></td>
                  <td className="ct-text"><RecordText items={config(g.config)} /></td>
                  <td className="ct-text ct-wide-only"><RecordText items={truth(g)} /></td>
                  <td className="ct-text ct-wide-only">{users(ref)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </ViewsRow>
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
    <div className="ct-scroll" data-caos-flow="">
      <table className="caos-table ct-wrap-head" data-table="designs">
        <thead>
          <tr>
            <th className="ct-text">{pick({ en: 'Design', es: 'Diseño' }, lang)}</th>
            <th>{pick({ en: 'Repetitions', es: 'Repeticiones' }, lang)}</th>
            <th>{pick({ en: 'Rate (SE)', es: 'Tasa (EE)' }, lang)}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((s) => (
            <tr key={s.key} data-sim={s.key}>
              <td className="ct-text">
                {pick(s.label, lang)}
                {/* the scenario under the design (U16-R3 c22 M2: as a column it cut the Rate (SE) column at 1280) */}
                <span className="ct-row-detail">{pick(s.scenario, lang)}</span>
              </td>
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
      return { panel: p, x, series, rows: groups.flatMap((g) => g.rows), ruleKey: r };
    });
  }, [sel, v]);
  if (!sel || !v || !panels || !v.outputs.ladder) return <Pending />;
  const ladder = v.outputs.ladder;
  const allSize = v.outputs.panels.every((p) => p.measures === 'size');
  const mixed = !allSize && v.outputs.panels.some((p) => p.measures === 'size');
  // the other-families variant measures two points per study: the test's null (0) and the engine's stated alternative (1)
  const twoPoint = ladder.values.length === 2;
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
        en: `Against the family's ladder, ${ladder.label.en}, unless a panel names its own axis; ${repetitions(v.outputs.simulations, 'en')}, so a rate's Monte Carlo SE is at most ${pct('en', 0.5 / Math.sqrt(Math.min(...v.outputs.simulations.map((s) => s.n_rep))), 1)}; dashed: the exact probability where one exists; dotted: the nominal level.${twoPoint ? ' Two points per study: its null (0, the rate is its size) and the one alternative the engine states (1, the rate is its power); a test with several studies has a curve each.' : ''}`,
        es: `Contra la escala de la familia, ${ladder.label.es}, salvo que un panel nombre su propio eje; ${repetitions(v.outputs.simulations, 'es')}, así que el EE de Monte Carlo de una tasa es a lo más ${pct('es', 0.5 / Math.sqrt(Math.min(...v.outputs.simulations.map((s) => s.n_rep))), 1)}; segmentada: la probabilidad exacta donde existe; punteada: el nivel nominal.${twoPoint ? ' Dos puntos por estudio: su nula (0, la tasa es su tamaño) y la única alternativa que declara el motor (1, la tasa es su potencia); una prueba con varios estudios tiene una curva cada uno.' : ''}`,
      }}
    >
      <div className="ct-panels-fill" data-caos-flow="" data-views={String(panels.length)}>
        {panels.map((pp) => (
          <div key={pp.panel.id} className="ct-small-multiple" data-panel={pp.panel.id}>
            <p className="ct-sm-title">
              {pick(pp.panel.label, lang)}
              {mixed && pp.panel.measures === 'size' ? pick({ en: ' (sizes: the model is right)', es: ' (tamaños: el modelo es correcto)' }, lang) : ''}
            </p>
            {pp.x.length >= 2 ? (
              // a panel of more than three series (Calibration draws nine) gets the solo key, so one curve can be read alone (b10 m16);
              // the plot keeps a floor under its key (U16-R3 c22 M1: squashed to 15 to 30 px)
              <div data-plot-floor="14rem" style={{ flex: '1 1 auto', minHeight: '14rem', display: 'flex', flexDirection: 'column' }}>
              <UPlotChart
                height="fill"
                x={{ values: pp.x, label: pp.panel.axis ?? ladder.label, format: { digits: 3 } }}
                y={{ label: { en: 'Rejection rate', es: 'Tasa de rechazo' }, format: { percent: true, decimals: 0 }, range: [0, 1] }}
                series={pp.series}
                solo={pp.series.length > 3}
                yMarks={[NOMINAL(sel.level)]}
              />
              </div>
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
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `Every rate of the family at ${pct('en', sel.level, 0)}`, es: `Cada tasa de la familia al ${pct('es', sel.level, 0)}` }}
        lane={REPLAY}
        provenance={provenanceOf(v.provenance.truth_status)}
        dataKey={stateKey}
        note={{ en: 'Rate (Monte Carlo SE), 95% Wilson interval, and the exact probability where one exists, with whether the rate agrees with it within 3.29 SE. The setting is on the panel\'s axis; the scenario states it in words.', es: 'Tasa (EE de Monte Carlo), intervalo de Wilson al 95 %, y la probabilidad exacta donde existe, con si la tasa concuerda con ella dentro de 3,29 EE. El ajuste está en el eje del panel; el escenario lo dice en palabras.' }}
      >
        <div className="ct-scroll" data-caos-flow="">
          <table className="caos-table ct-wrap-head" data-table="rates">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Panel', es: 'Panel' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Test', es: 'Prueba' }, lang)}</th>
                <th>{pick({ en: 'Setting', es: 'Ajuste' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Scenario', es: 'Escenario' }, lang)}</th>
                <th>{pick({ en: 'Rate (SE)', es: 'Tasa (EE)' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Wilson 95%', es: 'Wilson 95 %' }, lang)}</th>
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
                    <td className="ct-wide-only">{`${pct(lang, x.lo, 1)} ${pick({ en: 'to', es: 'a' }, lang)} ${pct(lang, x.hi, 1)}`}</td>
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
    </ViewsRow>
  );
}

/** The size above its bound that the engine documents on its own page (portfolio.mc_convergence): the measured size at
 * its level, the bound, the excess and the page, shown whether or not this run exceeds, never hidden. */
export function DocumentedExcess({ rows }: { rows: C22Simulation[] }) {
  const lang = useShellLang();
  const documented = rows.filter((s) => excessOf(s));
  if (documented.length === 0) return null;
  return (
    <ul className="ct-evidence" data-list="documented-excess">
      {documented.map((s) => {
        const ex = excessOf(s)!;
        const points = formatNumber(100 * Math.abs(ex.excess), lang, { decimals: 2 });
        return (
          <li key={s.key} data-sim={s.key} data-exceeds={ex.exceeds ? 'yes' : 'no'}>
            {pick(
              {
                en: `${s.label.en}: measured size ${pct('en', ex.measured)} at ${pct('en', ex.level, 0)}, against a bound of ${pct('en', ex.bound)}: ${ex.exceeds ? `${points} points above it` : `${points} points below it in this run`}. Engine page ${ex.page} (${ex.repository}). ${ex.engine.en}`,
                es: `${s.label.es}: tamaño medido ${pct('es', ex.measured)} al ${pct('es', ex.level, 0)}, contra una cota de ${pct('es', ex.bound)}: ${ex.exceeds ? `${points} puntos sobre ella` : `${points} puntos bajo ella en esta corrida`}. Página del motor ${ex.page} (${ex.repository}). ${ex.engine.es}`,
              },
              lang,
            )}
          </li>
        );
      })}
    </ul>
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
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `Size of every test at ${pct('en', sel.level, 0)}`, es: `Tamaño de cada prueba al ${pct('es', sel.level, 0)}` }}
        lane={REPLAY}
        provenance={provenanceOf(v.provenance.truth_status)}
        dataKey={stateKey}
        note={{
          en: `The rejection rate when the test's null holds at its boundary (${formatNumber(v.outputs.simulations[0]?.n_rep, 'en', { decimals: 0 })} repetitions). A test holds its size when its exact probability is at most the level, or, without one, when the rate is at most ${pct('en', bound)} (the level plus 3.09 Monte Carlo SEs).`,
          es: `La tasa de rechazo cuando la nula de la prueba se cumple en su frontera (${formatNumber(v.outputs.simulations[0]?.n_rep, 'es', { decimals: 0 })} repeticiones). Una prueba mantiene su tamaño cuando su probabilidad exacta es a lo más el nivel, o, sin ella, cuando la tasa es a lo más ${pct('es', bound)} (el nivel más 3,09 EE de Monte Carlo).`,
        }}
      >
        <div className="ct-scroll" data-caos-flow="">
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
                    <td data-holds={ok ? 'yes' : 'no'} data-documented={excessOf(s) ? 'yes' : undefined}>
                      {pick(ok ? { en: 'holds', es: 'se mantiene' } : { en: 'exceeds', es: 'excede' }, lang)}
                      {excessOf(s) && !ok ? pick({ en: ' (documented by the engine)', es: ' (documentado por el motor)' }, lang) : ''}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <DocumentedExcess rows={v.outputs.simulations} />
        </div>
      </PlotCard>
    </ViewsRow>
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
        // a second curve of one test is numbered, never named by the key's suffix ("(dev1)", "(null-20000)"; R2b c22), and the
        // number is read under the panels with where that curve's null holds (a legend of whole sentences left a phone panel no plot)
        const notes: Array<{ label: BiText; scenario: BiText }> = [];
        const seen = new Map<string, number>();
        const series: ChartSeries[] = rows.map((s, i) => {
          const total = (s.p_histogram ?? []).reduce((a, b) => a + b, 0) || 1;
          const k = (seen.get(pick(s.label, 'en')) ?? 0) + 1;
          seen.set(pick(s.label, 'en'), k);
          const numbered = !s.key.endsWith('@null') || k > 1;
          const label: BiText = numbered ? { en: `${pick(s.label, 'en')} (${k})`, es: `${pick(s.label, 'es')} (${k})` } : s.label;
          if (numbered) notes.push({ label, scenario: s.scenario });
          return { label, values: (s.p_histogram ?? []).map((c) => (c / total) * bins), width: 1.6, ...seriesStyle(i) };
        });
        return { panel: p, x, series, n: rows.length, notes };
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
      {/* the grid takes the height left above the numbered-curves note, never the card's whole body (U16-R4 c26, c27: at height 100%
          the note below it was cut by the body); it scrolls with its cue when the panels do not fit (c22-flow.css) */}
      <div className="ct-c22-flow" data-caos-flow="">
      <div className="ct-panels-fill" data-caos-flow="" data-views={String(panels.length)}>
        {panels.map((pp) => (
          <div key={pp.panel.id} className="ct-small-multiple" data-panel={pp.panel.id}>
            <p className="ct-sm-title">{pick(pp.panel.label, lang)}</p>
            <div data-plot-floor="14rem" style={{ flex: '1 1 auto', minHeight: '14rem', display: 'flex', flexDirection: 'column' }}>
            <UPlotChart
              height="fill"
              x={{ values: pp.x, label: { en: 'p-value', es: 'Valor p' }, format: { decimals: 2 } }}
              y={{ label: { en: 'Density', es: 'Densidad' }, format: { decimals: 1 } }}
              series={pp.series}
              solo
              yMarks={[{ y: 1, label: { en: 'Uniform', es: 'Uniforme' }, tone: 'neutral' }]}
            />
            </div>
          </div>
        ))}
      </div>
      {panels.some((pp) => pp.notes.length > 0) ? (
        <ul className="ct-note" data-list="numbered-curves">
          {panels.flatMap((pp) => pp.notes.map((n) => (
            <li key={`${pp.panel.id}-${pick(n.label, 'en')}`}>{`${pick(pp.panel.label, lang)}, ${pick(n.label, lang)}: ${pick(n.scenario, lang)}`}</li>
          )))}
        </ul>
      ) : null}
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
              <strong>{pick(s.title, lang)}</strong>: {pick({ en: `${s.agree} of ${s.total} cells agree within 3.29 combined SEs (${formatNumber(s.runs, 'en', { decimals: 0 })} runs, as published). `, es: `${s.agree} de ${s.total} celdas concuerdan dentro de 3,29 EE combinados (${formatNumber(s.runs, 'es', { decimals: 0 })} corridas, como se publicó). ` }, lang)}
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
/** Where the One report's sample is drawn on its ladder; a ladder label that ends in its own parenthesis takes the rung after a comma,
 * never a second parenthesis (U16-R5 c28 m4: "drawn at 0.2 (mean shift (standard deviations))"). */
export function drawnAt(en: string, es: string, label: BiText | { en: string; es: string }): { en: string; es: string } {
  const l = label as { en: string; es: string };
  return /\(/.test(l.en)
    ? { en: `drawn at ${en}, on the ladder of ${l.en}`, es: `generado en ${es}, en la escala de ${l.es}` }
    : { en: `drawn at ${en} (${l.en})`, es: `generado en ${es} (${l.es})` };
}

export function SpecimenView({ sel }: { sel: C22Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const v = c22Of(sel);
  if (!sel || !v) return <Pending />;
  // the severity is an index into the ladder: the note gives the rung itself with the ladder's label (U16-R3 c22 B2), and the null
  // family has no ladder (m14)
  const ladder = v.outputs.ladder;
  const rung = ladder ? ladder.values[v.outputs.specimen.severity] : undefined;
  const drawn = ladder && rung !== undefined
    ? drawnAt(formatNumber(rung, 'en', { digits: 4 }), formatNumber(rung, 'es', { digits: 4 }), ladder.label)
    : { en: 'drawn under its null', es: 'generado bajo su nula' };
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'One sample, one report', es: 'Una muestra, un reporte' }}
        lane={REPLAY}
        provenance={provenanceOf(v.provenance.truth_status)}
        dataKey={stateKey}
        note={{
          en: `The tests on one dataset ${drawn.en}: what a validator would read in a single report. The rates of the other views say how often such a report is right.`,
          es: `Las pruebas sobre un conjunto ${drawn.es}: lo que un validador leería en un solo reporte. Las tasas de las otras vistas dicen con qué frecuencia ese reporte acierta.`,
        }}
      >
        <div className="ct-scroll" data-caos-flow="">
          <table className="caos-table" data-table="specimen">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Test', es: 'Prueba' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Generator configuration', es: 'Configuración del generador' }, lang)}</th>
                <th>{pick({ en: 'Statistic', es: 'Estadístico' }, lang)}</th>
                <th>{pick({ en: 'p-value', es: 'Valor p' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {v.tests.map((t, i) => (
                <tr key={`${t.test_id}-${i}`}>
                  <td className="ct-text" title={t.test_id}>{pick(testName(t.test_id), lang)}</td>
                  {/* the engine's configuration key, marked as code as the Generators appendix lists it (the ruling of 2026-10-24); the
                      dataset of the row, so the One report's segment (R5 ruling 2) */}
                  <td className="ct-text" data-segment={t.model_id ?? undefined}><code translate="no">{t.model_id}</code></td>
                  <td>{formatNumber(t.statistic ?? t.metric, lang, { digits: 4 })}</td>
                  {/* a test with no p-value (a descriptive metric) shows none there, not its metric a second time (U16-R3 c22 B3) */}
                  {t.p_value === null ? <td data-na="true" data-p="none">-</td> : <LightCell row={t} alphas={sel.alphas} />}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </ViewsRow>
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
    <ViewsRow>
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
            <tr><td className="ct-text">{pick({ en: 'AUC: coverage of the 95% interval', es: 'AUC: cobertura del intervalo al 95 %' }, lang)}</td><td>{pct(lang, a.coverage)}</td><td>{pct(lang, a.coverage_mcse)}</td></tr>
            <tr><td className="ct-text">{pick({ en: 'ECE when the PDs are right (its bias)', es: 'ECE cuando las PD son correctas (su sesgo)' }, lang)}</td><td>{num(e.mean)}</td><td>{num(e.bias_mcse)}</td></tr>
          </tbody>
        </table>
      </PlotCard>
    </ViewsRow>
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
      <ViewsRow>
        <PlotCard
          fill
          title={{ en: `Power against the true-to-applied PD, at ${level}`, es: `Potencia según PD verdadera sobre aplicada, al ${level}` }}
          lane={LIVE}
          provenance={prov}
          dataKey={stateKey}
          note={{ en: `${formatNumber(p.n, 'en', { decimals: 0 })} obligors, PD applied ${pct('en', p.pd)}, true correlation ${pct('en', p.rhoTrue, 1)}; exact, recomputed in your browser. Where the Binomial and Jeffreys curves reject alike, the Jeffreys line lies over the Binomial one.`, es: `${formatNumber(p.n, 'es', { decimals: 0 })} deudores, PD aplicada ${pct('es', p.pd)}, correlación verdadera ${pct('es', p.rhoTrue, 1)}; exacta, recalculada en su navegador. Donde las curvas Binomial y Jeffreys rechazan igual, la línea de Jeffreys cubre a la Binomial.` }}
        >
          <UPlotChart
            height="fill"
            x={{ values: live.ratios, label: { en: 'True PD / PD applied', es: 'PD verdadera / PD aplicada' }, format: { decimals: 1 } }}
            y={{ label: { en: 'Rejection probability', es: 'Probabilidad de rechazo' }, format: { percent: true, decimals: 0 }, range: [0, 1] }}
            series={live.byRatio.map((s) => ({ label: s.label, values: s.values, color: s.color, width: 2 }))}
            yMarks={[NOMINAL(sel.level)]}
            marks={[{ x: p.ratio, label: { en: 'rail', es: 'panel' } }]}
          />
        </PlotCard>
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
            x={{ values: live.rhos, label: { en: 'True asset correlation', es: 'Correlación de activos verdadera' }, format: { percent: true, decimals: 1 } }}
            y={{ label: { en: 'Rejection probability', es: 'Probabilidad de rechazo' }, format: { percent: true, decimals: 0 }, range: [0, 1] }}
            series={live.byRho.map((s) => ({ label: s.label, values: s.values, color: s.color, width: 2 }))}
            yMarks={[NOMINAL(sel.level)]}
            marks={[{ x: p.rhoTrue, label: { en: 'rail', es: 'panel' } }]}
          />
        </PlotCard>
      </ViewsRow>
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
  const shares = useFindingsShares();
  const v = c22Of(sel);
  if (!sel || !v) return <Pending />;
  const order = ['S1', 'S2', 'S3', 'S4'];
  const findings: Finding[] = [...v.findings].sort((a, b) => order.indexOf(a.severity) - order.indexOf(b.severity));
  const sim = (e: string) => v.outputs.simulations.find((s) => `rate:${s.key}` === e);
  const r = rule(sel.level);
  // every cited rate, numbered in reading order: the table's [k] and the chart's x
  const points = findings.flatMap((f) => f.evidence.map((e) => ({ key: `${f.id}|${e}`, s: sim(e) }))).filter((x) => x.s);
  const number = new Map(points.map((x, i) => [x.key, i + 1]));
  // half a step of room on each side as the axis range, so the first and last points are not cut by the plot's edges
  const axis = citedAxis(points.length);
  const prov = provenanceOf(v.provenance.truth_status);
  return (
    <ViewsRow shares={shares}>
      <PlotCard
        fill
        title={{ en: 'What the measurements found', es: 'Lo que encontraron las mediciones' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{ en: "Each finding cites the measured rates behind it, at the rail's level, with their Monte Carlo SE; the numbers are the chart's.", es: 'Cada hallazgo cita las tasas medidas que lo respaldan, al nivel del panel, con su EE de Monte Carlo; los números son los del gráfico.' }}
      >
        <div className="ct-scroll" data-caos-flow="">
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
                        return <li key={e}>{s ? `[${k}] ${pick(s.label, lang)}, ${pick(s.scenario, lang)}: ${rateText(s, r, lang)}` : evidenceText(e, { caseId: 'C22', models: v.model }, lang)}</li>;
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
      <PlotCard
        fill
        title={{ en: 'The cited rates', es: 'Las tasas citadas' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{ en: `Each cited rate at ${pct('en', sel.level, 0)}, numbered as in the table, with its 95% Wilson interval, against the nominal level.`, es: `Cada tasa citada al ${pct('es', sel.level, 0)}, numerada como en la tabla, con su intervalo de Wilson al 95 %, contra el nivel nominal.` }}
      >
        <UPlotChart
          height="fill"
          x={{ values: axis.values, range: axis.range, label: { en: 'Cited rate (the number in the table)', es: 'Tasa citada (el número de la tabla)' }, format: { decimals: 0 } }}
          y={{ label: { en: 'Rejection rate', es: 'Tasa de rechazo' }, format: { percent: true, decimals: 0 }, range: [0, Math.min(1, Math.max(sel.level, ...points.map((x) => (x.s ? rateOf(x.s, r).hi : 0))) * 1.1)] }}
          series={[
            // the interval ends are small dots drawn first; the rate is the larger accent dot drawn last, so the interval never covers it
            { label: { en: 'Wilson 95%, low', es: 'Wilson 95 %, inferior' }, values: points.map((x) => (x.s ? rateOf(x.s, r).lo : null)), color: '--color-fg-subtle', mode: 'points', size: 5 },
            { label: { en: 'Wilson 95%, high', es: 'Wilson 95 %, superior' }, values: points.map((x) => (x.s ? rateOf(x.s, r).hi : null)), color: '--color-fg-subtle', mode: 'points', size: 5 },
            { label: { en: 'Rate', es: 'Tasa' }, values: points.map((x) => (x.s ? rateOf(x.s, r).rate : null)), color: '--color-accent', mode: 'points', size: 9 },
          ]}
          yMarks={[{ ...NOMINAL(sel.level), tone: 'warn' }]}
        />
      </PlotCard>
    </ViewsRow>
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
/**
 * The note of the detection matrix. A stronger colour is a higher rate in both themes (U16-R4 c26 n1: "darker" is false on the dark
 * page), and a false alarm or a size carries a dagger, so the kind of a cell is read in text, not by hue alone (c27 n3, rubric
 * section 8).
 */
export const HEAT_NOTE: { en: string; es: string } = {
  en: "Each cell is the test's rejection rate at the family's highest severity. Blue: its power, where the family plants a defect the test should see. Amber: a false alarm, where the model is right and an assumption fails (correlated defaults, a covariate shift, an estimated development AUC), and in the null column the test's size (exact where it exists). A stronger colour: a higher rate; † beside a rate: a false alarm or a size, the model being right; blank: a test the family does not measure. A column header loads the family. The Other families column is a test's power against the one alternative the engine states for it (blue); the tests of the five credit families are blank there, and the other tests are blank in the credit families' columns.",
  es: 'Cada celda es la tasa de rechazo de la prueba en la mayor severidad de la familia. Azul: su potencia, donde la familia planta un defecto que la prueba debería ver. Ámbar: una falsa alarma, donde el modelo es correcto y falla un supuesto (incumplimientos correlacionados, un desplazamiento de covariables, un AUC de desarrollo estimado), y en la columna nula el tamaño de la prueba (exacto donde existe). Color más intenso: una tasa mayor; † junto a una tasa: una falsa alarma o un tamaño, con el modelo correcto; vacía: una prueba que la familia no mide. El encabezado de una columna carga la familia. La columna Otras familias es la potencia de una prueba contra la única alternativa que el motor declara para ella (azul); las pruebas de las cinco familias de crédito quedan vacías ahí, y las demás pruebas quedan vacías en las columnas de las familias de crédito.',
};

/** The text of a matrix cell: its rate, with a dagger when the cell is a false alarm or a size (the model is right). */
export function heatText(c: { rate: number | null; kind: 'power' | 'size' }, lang: 'en' | 'es'): string {
  return `${pct(lang, c.rate, 1)}${c.kind === 'size' ? '†' : ''}`;
}

/** A code identifier that breaks only after its separators (".", "_", "-"), never inside a word (U16-R4 c27 n5: "stage_tran / sitions"). */
export { codeBreaks };

/** A source's attribution in the page's language: the bibliographic reference keeps its published title, and the Spanish joins its
 * authors with "y" and writes "n.º" for a number (U16-R5 c28 m8, ruling 5: an English author pair in a Spanish reference is English
 * body text). */
export function attributionText(attribution: string, lang: 'en' | 'es'): string {
  if (lang === 'en') return attribution;
  return attribution
    .replace(/(\p{Lu}[\p{L}'-]+, (?:\p{Lu}\.\s?)+) and (?=\p{Lu}[\p{L}'-]+, \p{Lu}\.)/gu, '$1 y ')
    .replace(/\bNo\. (?=\d)/g, 'n.º ');
}

/** The x axis of the cited-rates chart: the cited rates 1 to n only, with half a step of room on each side as the axis range, so no
 * padding row enters the chart's summary and data table (U16-R4 c27 n1: "30 points ... from 1 to 29" for 28 cited rates). */
export function citedAxis(n: number): { values: number[]; range: [number, number] } {
  return { values: Array.from({ length: n }, (_, i) => i + 1), range: [0.5, n + 0.5] };
}

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
    // a row per study of the null family (a test with several studies keeps one each); the null column is the study's own
    // size, the other-families column its power at the engine's stated alternative, the defect columns the credit tests'
    const cells = (f: C22Variant, s: C22Simulation) => {
      if (f.outputs.ladder === null) return { rate: rateOf(s, r).exact ?? rateOf(s, r).rate, kind: 'size' as const };
      if (f.variant_id === 'other-families') {
        const x = f.outputs.simulations.find((y) => y.key === `${rowKeyOf(s)}@d1`);
        return x ? { rate: rateOf(x, r).rate, kind: 'power' as const } : null;
      }
      return familyCell(f, s.test_id, r);
    };
    return { tests, rows: tests.map((s) => ({ s, cells: fams.map((f) => cells(f, s)) })) };
  }, [sel, fams]);
  if (!sel || all.state !== 'ready' || !matrix) return <Pending />;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const short = (id: string) => entries.find((e) => e.variant_id === id)?.short_title ?? { en: id, es: id };
  const prov = provenanceOf((sel.data.variant as VariantArtifact<unknown>).provenance.truth_status);
  const current = (sel.data.variant as VariantArtifact<unknown>).variant_id;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `Which test sees which defect, at ${pct('en', sel.level, 0)}`, es: `Qué prueba ve qué defecto, al ${pct('es', sel.level, 0)}` }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={HEAT_NOTE}
      >
        <div className="ct-scroll" data-caos-flow="">
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
                <tr key={s.key} data-test={s.test_id} data-row={rowKeyOf(s)}>
                  <td className="ct-text">{pick(s.label, lang)}</td>
                  {cells.map((c, k) => (
                    <td key={fams[k].variant_id} className="ct-heat" data-heat={heat(c?.rate ?? null)} data-kind={c?.kind}>
                      {c ? heatText(c, lang) : ''}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </ViewsRow>
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
                    <a href={s.landing} target="_blank" rel="noreferrer">{lang === 'es' && SOURCE_ES[id] ? <><span lang="en" translate="no">{SOURCE_ES[id].title}</span>{SOURCE_ES[id].part}</> : s.name}</a>
                  </td>
                  {/* the licence class in words (the raw-id scan: derived-only); in Spanish the licence in Spanish, the original marked (U16-R3 c22 B4) */}
                  <td className="caos-col-text">
                    {lang === 'es' && SOURCE_ES[id] && s.licence === SOURCE_ES[id].licence_en ? (
                      <>
                        {`«${SOURCE_ES[id].licence}» `}
                        <span data-original="en">(original en inglés: <span translate="no" lang="en">{`"${s.licence}"`}</span>)</span>
                      </>
                    ) : (
                      s.licence
                    )}{' '}
                    ({pick(LICENCE_CLASS_TEXT[s.class] ?? { en: s.class, es: s.class }, lang)})
                  </td>
                  <td className="caos-col-text">{attributionText(s.attribution, lang)}</td>
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
              en: `Truth status of this variant: ${pick(TRUTH_TEXT[v.provenance.truth_status] ?? { en: v.provenance.truth_status, es: v.provenance.truth_status }, 'en')}. The readers check each paper against its own print (WP14's Tables 5 to 8 name its eight scenarios, each with its 16 parameters and every rate in [0, 1], and Table 6 repeats Table 5's forecasts; Yurdakul and Naranjo's Table 4 has its six pairs of sample sizes and a benchmark near 5% without a shift) and refuse to compute the case otherwise. riskvalidation ${m.engine.riskvalidation ?? ''}.`,
              es: `Estado de verdad de esta variante: ${pick(TRUTH_TEXT[v.provenance.truth_status] ?? { en: v.provenance.truth_status, es: v.provenance.truth_status }, 'es')}. Los lectores verifican cada artículo contra su propia impresión (las tablas 5 a 8 de WP14 nombran sus ocho escenarios, cada uno con sus 16 parámetros y cada tasa en [0, 1], y la tabla 6 repite los pronósticos de la tabla 5; la tabla 4 de Yurdakul y Naranjo tiene sus seis pares de tamaños de muestra y una referencia cercana al 5 % sin desplazamiento) y si no, se niegan a calcular el caso. riskvalidation ${m.engine.riskvalidation ?? ''}.`,
            },
            lang,
          )}
        </p>
        <C22WriteUp />
      </PlotCard>
    </div>
  );
}
