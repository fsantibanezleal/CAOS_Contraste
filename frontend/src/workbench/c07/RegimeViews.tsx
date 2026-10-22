// C07's views: the three regimes side by side (CMF B-1, IFRS 9, BdE Annex 9) with the segments and the bridge from the
// B-1 comparable total to the IFRS 9 total, each regime in its own detail (the B-1 minimum and max rule, the IFRS 9
// probability-weighted components with the overlays apart, the BdE categories mapped to stages), and the scenario's
// delta against the base. Every drawing has its table with the same numbers; every number is the document's.
import { BarChart, PlotCard, Stage, ViewsRow, fitLabel, formatNumber, niceTicks, pick, useShellLang, useWorkbenchState, type BiText } from '@fasl-work/caos-app-shell';
import { useState } from 'react';
import { ChartOverTable, MaybeNumber, STAGE_TEXT, money, pct } from '../c06/format';
import { REPLAY, provenanceOf } from '../model';
import { Pending } from '../Pending';
import { FixtureNotice } from '../c06/C06Common';
import { componentLabel, outputsOf, type C07Outputs, type C07Sel, type RegimeId } from './selection';

const LIVE = 'live' as const;
const REGIME_COLOR: Record<RegimeId, string> = { 'cmf-b1': '--color-accent', ifrs9: '--color-warn', 'bde-annex9': '--color-good' };
const REGIME_TONE: Record<RegimeId, 'accent' | 'warn' | 'good'> = { 'cmf-b1': 'accent', ifrs9: 'warn', 'bde-annex9': 'good' };
const STATUS_TEXT: Record<string, BiText> = {
  'statutory-chile-loans': { en: 'Statutory for loans in Chile', es: 'Estatutaria para créditos en Chile' },
  'comparison-measure': { en: 'Comparison measure, not the Chilean statutory provision', es: 'Medida de comparación, no la provisión estatutaria chilena' },
  'spanish-gaap-alternative-solutions': { en: 'Spanish GAAP alternative solutions, aligned with IFRS 9', es: 'Soluciones alternativas del PGC español, alineadas con IFRS 9' },
};
/** The IFRS 9 column is always named for what it is. */
const IFRS9_NAME: BiText = { en: 'IFRS 9, probability-weighted ECL', es: 'IFRS 9, PCE ponderada por probabilidad' };
const BANK_NOTE: BiText = { en: 'Synthetic bank: no statement about any bank.', es: 'Banco sintético: sin afirmación sobre ningún banco.' };

function regimeName(id: RegimeId, label: BiText): BiText {
  return id === 'ifrs9' ? IFRS9_NAME : label;
}

const colorOf = (token: string) => `var(${token})`;

const segmentName = (o: C07Outputs, id: string): BiText => o.portfolio.segments.find((x) => x.segment_id === id)?.label ?? { en: id, es: id };

const CATEGORY_TEXT: Record<string, BiText> = {
  normal: { en: 'Normal', es: 'Normal' },
  'normal-special-watch': { en: 'Normal, special watch', es: 'Normal en vigilancia especial' },
  doubtful: { en: 'Doubtful', es: 'Dudoso' },
  'written-off': { en: 'Written off', es: 'Fallido' },
};

/** Grouped bars: one group per segment, one bar per regime. */
function GroupedBars({ o, sel }: { o: C07Outputs; sel: C07Sel }) {
  const lang = useShellLang();
  const [picked, setPicked] = useState<string | null>(null);
  const cur = o.currency;
  const segs = o.comparison.rows;
  const label = (id: string) => pick(o.portfolio.segments.find((s) => s.segment_id === id)?.label ?? { en: id, es: id }, lang);
  const value = (r: (typeof segs)[number], id: RegimeId) => (id === 'cmf-b1' ? r.cmf_b1_provision : id === 'ifrs9' ? r.ifrs9_provision : r.bde_annex9_provision);
  const ids: RegimeId[] = ['cmf-b1', 'ifrs9', 'bde-annex9'];
  const chosen = picked ? picked.split('|') : null;
  const cs = chosen ? segs.find((r) => r.segment_id === chosen[0]) : null;
  return (
    <div className="ct-map">
      <Stage label={{ en: 'Provision by segment under the three regimes', es: 'Provisión por segmento bajo los tres regímenes' }} className="ct-map-stage">
        {({ width, height }) => {
          const left = 64;
          const bottom = 54;
          const top = 10;
          const plotW = Math.max(width - left - 8, 40);
          const plotH = Math.max(height - top - bottom, 40);
          const hi = Math.max(...segs.flatMap((r) => ids.map((id) => value(r, id))), 1);
          const ticks = niceTicks(0, hi, plotH, 22, 6);
          const top2 = Math.max(hi, ticks[ticks.length - 1]);
          const sy = (v: number) => top + plotH - (v / top2) * plotH;
          const gw = plotW / Math.max(segs.length, 1);
          const bw = Math.min((gw * 0.8) / 3, 40);
          return (
            <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={pick({ en: 'Provision by segment under the three regimes', es: 'Provisión por segmento bajo los tres regímenes' }, lang)}>
              {ticks.map((t) => (
                <g key={t}>
                  <line className="dg-grid" x1={left} x2={width - 4} y1={sy(t)} y2={sy(t)} />
                  <text className="dg-tick" x={left - 6} y={sy(t) + 4} textAnchor="end">{formatNumber(t / 1e6, lang, { digits: 3 })}</text>
                </g>
              ))}
              {segs.map((r, gi) => {
                const x0 = left + gi * gw + (gw - bw * 3) / 2;
                return (
                  <g key={r.segment_id} data-group={r.segment_id}>
                    {ids.map((id, bi) => {
                      const v = value(r, id);
                      const key = `${r.segment_id}|${id}`;
                      return (
                        <rect
                          key={id}
                          x={x0 + bi * bw}
                          y={sy(v)}
                          width={bw - 2}
                          height={Math.max(sy(0) - sy(v), 1)}
                          style={{ fill: colorOf(REGIME_COLOR[id]), stroke: picked === key ? 'var(--color-fg)' : 'none', strokeWidth: 2, opacity: sel.regime === id ? 1 : 0.78 }}
                          role="button"
                          tabIndex={0}
                          aria-label={`${label(r.segment_id)}, ${id}: ${money(v, lang, cur)}`}
                          onClick={() => setPicked(picked === key ? null : key)}
                          onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setPicked(picked === key ? null : key)}
                        />
                      );
                    })}
                    {(() => {
                      const fit = fitLabel(label(r.segment_id), gw - 6, 12, 2);
                      return (
                        <text className="dg-axis-label" x={left + gi * gw + gw / 2} y={height - 38} textAnchor="middle">
                          <title>{label(r.segment_id)}</title>
                          {fit.lines.map((ln, li) => (
                            <tspan key={li} x={left + gi * gw + gw / 2} dy={li === 0 ? 0 : 14}>{ln}</tspan>
                          ))}
                        </text>
                      );
                    })()}
                  </g>
                );
              })}
              <text className="dg-note" x={left} y={height - 4}>{pick({ en: `${cur} millions`, es: `millones de ${cur}` }, lang)}</text>
            </svg>
          );
        }}
      </Stage>
      <p className="ct-note" aria-live="polite">
        {chosen && cs
          ? `${label(cs.segment_id)}, ${pick(regimeName(chosen[1] as RegimeId, o.regimes.find((r) => r.regime === chosen[1])?.label ?? { en: chosen[1], es: chosen[1] }), lang)}: ${money(value(cs, chosen[1] as RegimeId), lang, cur)} ${cur}`
          : pick({ en: 'Pick a bar to read it. Blue is B-1, amber is IFRS 9 (probability-weighted), green is BdE Annex 9.', es: 'Elija una barra para leerla. Azul es B-1, ámbar es IFRS 9 (ponderada por probabilidad), verde es Anexo 9 del BdE.' }, lang)}
      </p>
    </div>
  );
}

/** The three regimes side by side: the totals with their legal status, and the provision by segment. */
export function ThreeRegimeView({ sel }: { sel: C07Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const cur = o.currency;
  return (
    <ViewsRow shares={[1, 1]}>
      <PlotCard
        fill
        title={{ en: `The three regimes, scenario ${o.scenario_id} (${cur} millions)`, es: `Los tres regímenes, escenario ${o.scenario_id} (millones de ${cur})` }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: 'The comparable total is the sum of the segment provisions plus the unallocated lines of each regime. The B-1 additional provisions are outside it. The IFRS 9 column is the probability-weighted measure, a comparison, not the provision Chilean banks book on loans.',
          es: 'El total comparable es la suma de las provisiones por segmento más las líneas no asignadas de cada régimen. Las provisiones adicionales de B-1 quedan fuera. La columna IFRS 9 es la medida ponderada por probabilidad, una comparación, no la provisión que los bancos chilenos constituyen sobre los créditos.',
        }}
      >
        <ChartOverTable
          chart={
            <BarChart
              title={{ en: 'Total provision by regime', es: 'Provisión total por régimen' }}
              height="fill"
              orientation="vertical"
              data={o.regimes.map((r) => ({ id: r.regime, label: regimeName(r.regime, r.label), value: r.total_provision / 1e6, tone: REGIME_TONE[r.regime], highlight: sel.regime === r.regime, hint: STATUS_TEXT[r.status] }))}
              axis={{ label: { en: 'Millions', es: 'Millones' }, format: { digits: 4 } }}
            />
          }
        >
          <div>
            <FixtureNotice variant={sel.data.variant} />
            <table className="caos-table ct-wrap-head" data-table="regimes">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Regime', es: 'Régimen' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Status', es: 'Estatus' }, lang)}</th>
                  <th>{`${pick({ en: 'Total', es: 'Total' }, lang)} (${cur})`}</th>
                  <th>{pick({ en: 'Coverage', es: 'Cobertura' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {o.regimes.map((r) => (
                  <tr key={r.regime} data-regime={r.regime} data-status={r.status} className={sel.regime === r.regime ? 'ct-current' : undefined}>
                    <td className="ct-text">{pick(regimeName(r.regime, r.label), lang)}</td>
                    <td className="ct-text">{pick(STATUS_TEXT[r.status], lang)}</td>
                    <td>{money(r.total_provision, lang, cur)}</td>
                    <td>{pct(r.coverage_rate, lang, 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <ul className="ct-evidence" data-table="unallocated-lines">
              {o.regimes.flatMap((r) =>
                r.unallocated_lines.map((u) => (
                  <li key={`${r.regime}-${u.id}`} data-unallocated={u.id}>
                    {`${pick(regimeName(r.regime, r.label), lang)}: ${pick(u.label, lang)}, ${u.amount === 0 ? (lang === 'es' ? 'no se requiere' : 'none needed') : `${money(u.amount, lang, cur)} ${cur}`}`}
                  </li>
                )),
              )}
            </ul>
            <p className="ct-note">{pick(o.notice, lang)}</p>
            <p className="ct-note">{pick(BANK_NOTE, lang)}</p>
          </div>
        </ChartOverTable>
      </PlotCard>
      <PlotCard fill title={{ en: 'Provision by segment', es: 'Provisión por segmento' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <GroupedBars o={o} sel={sel} />
      </PlotCard>
    </ViewsRow>
  );
}

/** The segment table: the three provisions, both gaps against B-1, and the unallocated lines apart. */
export function SegmentsView({ sel }: { sel: C07Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const c = o.comparison;
  const cur = c.currency;
  const label = (id: string) => pick(o.portfolio.segments.find((s) => s.segment_id === id)?.label ?? { en: id, es: id }, lang);
  return (
    <ViewsRow>
    <PlotCard
      fill
      title={{ en: 'Provision by segment and the gaps against B-1', es: 'Provisión por segmento y las brechas contra B-1' }}
      lane={REPLAY}
      provenance={prov}
      dataKey={stateKey}
      note={{ en: 'A positive gap means the regime provisions more than B-1 for that segment. The IFRS 9 column is the model ECL without overlays; overlays and the B-1 minimum top-up are in the unallocated row.', es: 'Una brecha positiva significa que el régimen provisiona más que B-1 en ese segmento. La columna IFRS 9 es la PCE del modelo sin ajustes; los ajustes y el complemento del mínimo de B-1 están en la fila no asignada.' }}
    >
      <ChartOverTable chart={<GroupedBars o={o} sel={sel} />}>
        <table className="caos-table ct-wrap-head" data-table="segments">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Segment', es: 'Segmento' }, lang)}</th>
              <th>{`CMF B-1 (${cur})`}</th>
              <th>{pick({ en: 'IFRS 9 (weighted)', es: 'IFRS 9 (ponderada)' }, lang)}</th>
              <th>BdE Annex 9</th>
              <th>{pick({ en: 'IFRS 9 minus B-1', es: 'IFRS 9 menos B-1' }, lang)}</th>
              <th>{pick({ en: 'BdE minus B-1', es: 'BdE menos B-1' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {c.rows.map((r) => (
              <tr key={r.segment_id} data-segment={r.segment_id} className={sel.segment === r.segment_id ? 'ct-current' : undefined}>
                <td className="ct-text">{label(r.segment_id)}</td>
                <td>{money(r.cmf_b1_provision, lang, cur)}</td>
                <td>{money(r.ifrs9_provision, lang, cur)}</td>
                <td>{money(r.bde_annex9_provision, lang, cur)}</td>
                <td>{money(r.gap_ifrs9_minus_b1, lang, cur)}</td>
                <td>{money(r.gap_bde_minus_b1, lang, cur)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr data-row="unallocated">
              <td className="ct-text">{pick({ en: 'Unallocated lines', es: 'Líneas no asignadas' }, lang)}</td>
              <td>{money(c.unallocated.cmf_b1_provision, lang, cur)}</td>
              <td>{money(c.unallocated.ifrs9_provision, lang, cur)}</td>
              <td>{money(c.unallocated.bde_annex9_provision, lang, cur)}</td>
              <td>{money(c.unallocated.gap_ifrs9_minus_b1, lang, cur)}</td>
              <td>{money(c.unallocated.gap_bde_minus_b1, lang, cur)}</td>
            </tr>
          </tfoot>
        </table>
      </ChartOverTable>
    </PlotCard>
    </ViewsRow>
  );
}

/** The bridge from the B-1 comparable total to the IFRS 9 total: exhaustive steps that sum to the gap. */
export function BridgeView({ sel }: { sel: C07Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const [picked, setPicked] = useState<string | null>(null);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const b = o.gap_bridge;
  const cur = b.currency;
  const from = o.regimes.find((r) => r.regime === b.from_regime);
  const to = o.regimes.find((r) => r.regime === b.to_regime);
  if (!from || !to) return <Pending />;
  const sum = b.steps.reduce((a, s) => a + s.amount, 0);
  const closes = Math.abs(from.total_provision + sum - to.total_provision) <= 1e-6 * Math.max(1, Math.abs(to.total_provision));
  let run = from.total_provision;
  const bars = [
    { id: 'from', label: from.label, amount: from.total_provision, lo: from.total_provision, hi: from.total_provision, kind: 'total' },
    ...b.steps.map((s) => {
      const start = run;
      run += s.amount;
      return { id: s.id, label: s.label, amount: s.amount, lo: Math.min(start, run), hi: Math.max(start, run), kind: 'step' };
    }),
    { id: 'to', label: IFRS9_NAME, amount: to.total_provision, lo: to.total_provision, hi: to.total_provision, kind: 'total' },
  ];
  const chosen = bars.find((x) => x.id === picked) ?? null;
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={{ en: 'Bridge from CMF B-1 to IFRS 9', es: 'Puente de CMF B-1 a IFRS 9' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{ en: 'The steps are exhaustive: they sum to the gap, and an unexplained step would be its own line. The B-1 additional provisions are outside both totals and are not a step; the B-1 minimum top-up and the IFRS 9 overlays are.', es: 'Los pasos son exhaustivos: suman la brecha, y un paso sin explicar sería su propia línea. Las provisiones adicionales de B-1 están fuera de ambos totales y no son un paso; el complemento del mínimo de B-1 y los ajustes de IFRS 9 sí lo son.' }}
      >
        <div className="ct-map">
          <Stage label={{ en: 'Bridge from B-1 to IFRS 9', es: 'Puente de B-1 a IFRS 9' }} className="ct-map-stage">
            {({ width, height }) => {
              const labelW = Math.min(Math.max(width * 0.34, 90), 190);
              const x0 = labelW + 8;
              const plotW = Math.max(width - x0 - 70, 40);
              const top = 6;
              const axis = 22;
              const rowH = (height - top - axis) / bars.length;
              // the totals are markers, so the axis spans the running total only (it does not start at zero)
              const lo0 = Math.min(...bars.map((x) => x.lo));
              const hi0 = Math.max(...bars.map((x) => x.hi));
              const pad = Math.max((hi0 - lo0) * 0.12, 1);
              const ticks = niceTicks(lo0 - pad, hi0 + pad, plotW, 60, 6);
              const dmin = Math.min(lo0 - pad, ticks[0]);
              const dmax = Math.max(hi0 + pad, ticks[ticks.length - 1]);
              const sx = (v: number) => x0 + ((v - dmin) / (dmax - dmin)) * plotW;
              return (
                <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={pick({ en: 'Bridge from B-1 to IFRS 9', es: 'Puente de B-1 a IFRS 9' }, lang)}>
                  {ticks.map((t) => (
                    <g key={t}>
                      <line className="dg-grid" x1={sx(t)} x2={sx(t)} y1={top} y2={height - axis} />
                      <text className="dg-tick" x={sx(t)} y={height - 6} textAnchor="middle">{formatNumber(t / 1e6, lang, { digits: 4 })}</text>
                    </g>
                  ))}
                  {bars.map((x, i) => {
                    const y = top + i * rowH;
                    const h = Math.max(rowH * 0.62, 3);
                    const fill = x.kind === 'total' ? (x.id === 'from' ? REGIME_COLOR['cmf-b1'] : REGIME_COLOR.ifrs9) : x.amount >= 0 ? '--color-bad' : '--color-good';
                    return (
                      <g key={x.id} data-bar={x.id}>
                        <text className="dg-bar-label" x={labelW} y={y + rowH / 2 + 4} textAnchor="end">{fitLabel(pick(x.label, lang), labelW, 11, 1).lines[0]}</text>
                        <rect
                          x={x.kind === 'total' ? sx(x.lo) - h / 2 : sx(x.lo)}
                          y={y + (rowH - h) / 2}
                          width={x.kind === 'total' ? h : Math.max(sx(x.hi) - sx(x.lo), 1.5)}
                          height={h}
                          rx={x.kind === 'total' ? h / 2 : 0}
                          style={{ fill: colorOf(fill), stroke: picked === x.id ? 'var(--color-fg)' : 'none', strokeWidth: 2 }}
                          role="button"
                          tabIndex={0}
                          aria-label={`${pick(x.label, lang)}: ${money(x.amount, lang, cur)}`}
                          onClick={() => setPicked(picked === x.id ? null : x.id)}
                          onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setPicked(picked === x.id ? null : x.id)}
                        />
                        <text className="dg-tick" x={sx(x.hi) + (x.kind === 'total' ? h / 2 + 4 : 4)} y={y + rowH / 2 + 4}>{formatNumber(x.amount / 1e6, lang, { digits: 4 })}</text>
                      </g>
                    );
                  })}
                </svg>
              );
            }}
          </Stage>
          <p className="ct-note" aria-live="polite">
            {chosen ? `${pick(chosen.label, lang)}: ${money(chosen.amount, lang, cur)} ${cur}` : pick({ en: `Millions of ${cur}; the axis does not start at zero, the two totals are the dots. Pick a bar to read it.`, es: `Millones de ${cur}; el eje no parte de cero, los dos totales son los puntos. Elija una barra para leerla.` }, lang)}
          </p>
        </div>
      </PlotCard>
      <PlotCard fill title={{ en: 'The steps in numbers', es: 'Los pasos en números' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <div className="ct-scroll">
          <table className="caos-table" data-table="gap-bridge" data-closes={String(closes)}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Step', es: 'Paso' }, lang)}</th>
                <th>{`${pick({ en: 'Amount', es: 'Monto' }, lang)} (${cur})`}</th>
              </tr>
            </thead>
            <tbody>
              <tr data-total="from">
                <td className="ct-text">{pick(from.label, lang)}</td>
                <td>{money(from.total_provision, lang, cur)}</td>
              </tr>
              {b.steps.map((s) => (
                <tr key={s.id} data-step={s.id}>
                  <td className="ct-text">{pick(s.label, lang)}</td>
                  <td>{money(s.amount, lang, cur)}</td>
                </tr>
              ))}
              <tr data-total="to">
                <td className="ct-text">{pick(IFRS9_NAME, lang)}</td>
                <td>{money(to.total_provision, lang, cur)}</td>
              </tr>
            </tbody>
          </table>
          <p className="ct-note">
            {closes
              ? pick({ en: 'The steps close the bridge exactly.', es: 'Los pasos cierran el puente exactamente.' }, lang)
              : pick({ en: 'The steps do not close the bridge: the document is inconsistent.', es: 'Los pasos no cierran el puente: el documento es inconsistente.' }, lang)}
          </p>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

/** CMF B-1: the minimum check, the group max rule, the individual provisions and the additional provisions outside the comparable total. */
export function B1View({ sel }: { sel: C07Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const d = o.b1_detail;
  const cur = d.currency;
  const comparable = o.regimes.find((r) => r.regime === 'cmf-b1')?.total_provision ?? null;
  const additional = sel.additional ?? d.additional_provisions.amount;
  const METHOD: Record<string, BiText> = { standard: { en: 'standard', es: 'estándar' }, internal: { en: 'internal', es: 'interno' }, max: { en: 'maximum of both', es: 'máximo de ambos' } };
  return (
    <ViewsRow shares={[1, 1]}>
      <PlotCard
        fill
        title={{ en: 'CMF B-1: group assessment and the minimum', es: 'CMF B-1: evaluación grupal y el mínimo' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{ en: 'The group provision is the larger of the standard method and the internal one, unless the CMF has not objected to the internal one. The 0.50% minimum applies to the individually assessed normal portfolio.', es: 'La provisión grupal es la mayor entre el método estándar y el interno, salvo que la CMF no haya objetado el interno. El mínimo de 0,50% se aplica a la cartera normal evaluada individualmente.' }}
      >
        <div className="ct-scroll">
          <table className="caos-table ct-wrap-head" data-table="group-max-rule">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Segment', es: 'Segmento' }, lang)}</th>
                <th>{pick({ en: 'Standard', es: 'Estándar' }, lang)}</th>
                <th>{pick({ en: 'Internal', es: 'Interno' }, lang)}</th>
                <th>{pick({ en: 'Applied', es: 'Aplicada' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Method', es: 'Método' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {d.group_max_rule.map((g) => (
                <tr key={g.segment_id} data-segment={g.segment_id} data-method={g.method}>
                  <td className="ct-text">{pick(segmentName(o, g.segment_id), lang)}</td>
                  <td>{money(g.standard, lang, cur)}</td>
                  <td>
                    <MaybeNumber value={g.internal} reason={null} format={(v) => money(v, lang, cur)} />
                  </td>
                  <td>{money(g.applied, lang, cur)}</td>
                  <td className="ct-text ct-wide-only">{pick(METHOD[g.method], lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {/* the reason is the same for every row: said once under the table, not in every cell (U16-R2 b04 M8) */}
          {d.group_max_rule.find((g) => g.internal_reason) ? (
            <p className="ct-note" data-note="internal-reason">{pick(d.group_max_rule.find((g) => g.internal_reason)!.internal_reason!, lang)}</p>
          ) : null}
          <table className="caos-table" data-table="b1-minimum" data-binding={String(d.minimum_check.binding)}>
            <tbody>
              <tr>
                <td className="ct-text">{pick({ en: 'Normal portfolio exposure (A1 to A6)', es: 'Exposición de la cartera normal (A1 a A6)' }, lang)}</td>
                <td>{money(d.minimum_check.normal_portfolio_exposure, lang, cur)}</td>
              </tr>
              <tr>
                <td className="ct-text">{pick({ en: 'Provision before the minimum', es: 'Provisión antes del mínimo' }, lang)}</td>
                <td>{money(d.minimum_check.normal_portfolio_provision_before_minimum, lang, cur)}</td>
              </tr>
              <tr>
                <td className="ct-text">{pick({ en: `Minimum at ${pct(d.minimum_check.minimum_rate, lang, 2)}`, es: `Mínimo a ${pct(d.minimum_check.minimum_rate, lang, 2)}` }, lang)}</td>
                <td>{money(d.minimum_check.minimum_amount, lang, cur)}</td>
              </tr>
              <tr>
                <td className="ct-text">{d.minimum_check.binding ? pick({ en: 'The minimum binds: top-up', es: 'El mínimo obliga: complemento' }, lang) : pick({ en: 'The minimum does not bind: top-up', es: 'El mínimo no obliga: complemento' }, lang)}</td>
                <td>{money(d.minimum_check.top_up, lang, cur)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </PlotCard>
      <PlotCard
        fill
        title={{ en: 'What B-1 books, and what is comparable', es: 'Lo que B-1 constituye, y lo comparable' }}
        lane={LIVE}
        provenance={prov}
        dataKey={stateKey}
        note={{ en: 'The additional provisions are counter-cyclical, a board policy with a minimum and a maximum: they are in what the bank books but outside the total the three regimes are compared on. They may never cover model deficiencies.', es: 'Las provisiones adicionales son contracíclicas, una política del directorio con mínimo y máximo: están en lo que el banco constituye pero fuera del total sobre el que se comparan los tres regímenes. Nunca pueden cubrir deficiencias de los modelos.' }}
      >
        <div className="ct-scroll">
          <table className="caos-table" data-table="b1-booked">
            <tbody>
              <tr>
                <td className="ct-text">{pick({ en: 'Individual: normal and substandard', es: 'Individual: normal y subestándar' }, lang)}</td>
                <td>{money(d.individual.normal_substandard_provision, lang, cur)}</td>
              </tr>
              <tr>
                <td className="ct-text">{pick({ en: 'Individual: default', es: 'Individual: incumplimiento' }, lang)}</td>
                <td>{money(d.individual.default_provision, lang, cur)}</td>
              </tr>
              <tr>
                <td className="ct-text">{pick({ en: 'Comparable total (group, individual and the minimum top-up)', es: 'Total comparable (grupal, individual y el complemento del mínimo)' }, lang)}</td>
                <td data-total="comparable">{money(comparable, lang, cur)}</td>
              </tr>
              <tr>
                <td className="ct-text">{pick({ en: `Additional provisions, policy ${money(d.additional_provisions.policy_min, lang, cur)} to ${money(d.additional_provisions.policy_max, lang, cur)}`, es: `Provisiones adicionales, política ${money(d.additional_provisions.policy_min, lang, cur)} a ${money(d.additional_provisions.policy_max, lang, cur)}` }, lang)}</td>
                <td data-total="additional">{money(additional, lang, cur)}</td>
              </tr>
              <tr>
                <td className="ct-text">{pick({ en: 'Booked total', es: 'Total constituido' }, lang)}</td>
                <td data-total="booked">{money(sel.additional === null ? d.booked_total : (comparable ?? 0) + additional, lang, cur)}</td>
              </tr>
            </tbody>
          </table>
          <p className="ct-note">{pick(d.additional_provisions.rationale, lang)}</p>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

/** IFRS 9: the probability-weighted measure with its components as sensitivities, the stage summary and the overlays apart. */
export function Ifrs9View({ sel }: { sel: C07Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const d = o.ifrs9_detail;
  const cur = d.currency;
  const label = (id: string): BiText => componentLabel(sel, id);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'IFRS 9: the probability-weighted ECL', es: 'IFRS 9: la PCE ponderada por probabilidad' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{ en: 'The IFRS 9 measure is the weighted sum of the scenarios (5.5.17(a), B5.5.42). A single scenario at 100% weight is a sensitivity and never the measure. IFRS 9 5.5 is carved out for bank loans in Chile: this is a comparison, not the provision Chilean banks book.', es: 'La medida IFRS 9 es la suma ponderada de los escenarios (5.5.17(a), B5.5.42). Un solo escenario con 100% de peso es una sensibilidad y nunca la medida. IFRS 9 5.5 está excluida para los créditos bancarios en Chile: esto es una comparación, no la provisión que constituyen los bancos chilenos.' }}
      >
        <div className="ct-scroll" data-measure={d.measure}>
          <table className="caos-table ct-wrap-head" data-table="ifrs9-components">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Scenario', es: 'Escenario' }, lang)}</th>
                <th>{pick({ en: 'Weight', es: 'Peso' }, lang)}</th>
                <th>z</th>
                <th>{`${pick({ en: 'ECL at 100% weight (sensitivity)', es: 'PCE con 100% de peso (sensibilidad)' }, lang)} (${cur})`}</th>
              </tr>
            </thead>
            <tbody>
              {d.weighted_components.map((c) => (
                <tr key={c.scenario_id} data-component={c.scenario_id}>
                  <td className="ct-text">{pick(label(c.scenario_id), lang)}</td>
                  <td>{pct(c.weight, lang, 0)}</td>
                  <td>{formatNumber(c.z, lang, { digits: 3 })}</td>
                  <td>{money(c.single_scenario_ecl, lang, cur)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr data-total="model-ecl">
                <td className="ct-text" colSpan={3}>{pick({ en: 'Model ECL, probability-weighted, overlays excluded', es: 'PCE del modelo, ponderada por probabilidad, sin ajustes' }, lang)}</td>
                <td>{money(d.stage_summary.reduce((a, r) => a + r.ecl, 0), lang, cur)}</td>
              </tr>
            </tfoot>
          </table>
          <table className="caos-table ct-wrap-head" data-table="ifrs9-stages">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Stage', es: 'Etapa' }, lang)}</th>
                <th>{pick({ en: 'Accounts', es: 'Cuentas' }, lang)}</th>
                <th>{`${pick({ en: 'Gross carrying amount', es: 'Valor en libros bruto' }, lang)} (${cur})`}</th>
                <th>{pick({ en: 'ECL', es: 'PCE' }, lang)}</th>
                <th>{pick({ en: 'Coverage', es: 'Cobertura' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {d.stage_summary.map((r) => (
                <tr key={r.stage} data-stage={r.stage}>
                  <td className="ct-text" style={{ whiteSpace: 'nowrap' }}>{pick(STAGE_TEXT[r.stage], lang)}</td>
                  <td>{formatNumber(r.accounts, lang, { decimals: 0 })}</td>
                  <td>{money(r.gross_carrying_amount, lang, cur)}</td>
                  <td>{money(r.ecl, lang, cur)}</td>
                  <td>{pct(r.coverage, lang, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3 className="ct-sub">{pick({ en: 'Overlays, each its own line', es: 'Ajustes, cada uno su propia línea' }, lang)}</h3>
          <p className="ct-note">{pick({ en: 'Overlays are judgement on top of the model: never merged into a segment or a stage, and counted in the IFRS 9 total as lines of their own.', es: 'Los ajustes son juicio sobre el modelo: nunca se mezclan en un segmento ni en una etapa, y cuentan en el total IFRS 9 como líneas propias.' }, lang)}</p>
          {d.overlays.length === 0 ? (
          <p className="ct-note" data-state="unavailable">{pick({ en: 'This variant carries no overlay.', es: 'Esta variante no lleva ajustes.' }, lang)}</p>
        ) : (
          <div className="ct-scroll">
            <table className="caos-table ct-wrap-head" data-table="ifrs9-overlays">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Overlay', es: 'Ajuste' }, lang)}</th>
                  <th className="ct-text ct-wide-only">{pick({ en: 'Segment and stage', es: 'Segmento y etapa' }, lang)}</th>
                  <th>{`${pick({ en: 'Amount', es: 'Monto' }, lang)} (${cur})`}</th>
                </tr>
              </thead>
              <tbody>
                {d.overlays.map((ov) => (
                  <tr key={ov.id} data-overlay={ov.id}>
                    <td className="ct-text">{pick(ov.label, lang)}</td>
                    <td className="ct-text ct-wide-only">{`${ov.segment_id ? pick(segmentName(o, ov.segment_id), lang) : pick({ en: 'portfolio', es: 'cartera' }, lang)}, ${ov.stage ? pick(STAGE_TEXT[ov.stage], lang) : pick({ en: 'no stage', es: 'sin etapa' }, lang)}`}</td>
                    <td>{money(ov.amount, lang, cur)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr data-total="overlays">
                  <td className="ct-text" colSpan={2}>{pick({ en: 'Overlays in total', es: 'Ajustes en total' }, lang)}</td>
                  <td>{money(d.overlays_total, lang, cur)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

/** BdE Annex 9: the categories of Circular 4/2017 mapped to the IFRS 9 stages, with the coverage of each. */
export function BdeView({ sel }: { sel: C07Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const d = o.bde_detail;
  const cur = d.currency;
  return (
    <ViewsRow>
      <PlotCard fill title={{ en: 'BdE Annex 9: coverage by category', es: 'Anexo 9 del BdE: cobertura por categoría' }} lane={REPLAY} provenance={prov} dataKey={stateKey} note={{ en: 'The coverage of each category over its exposure, with the percentages of the alternative solutions of the Annex.', es: 'La cobertura de cada categoría sobre su exposición, con los porcentajes de las soluciones alternativas del Anexo.' }}>
        <ChartOverTable
          chart={
        <BarChart
          title={{ en: 'Coverage by category', es: 'Cobertura por categoría' }}
          height="fill"
          orientation="vertical"
          data={d.categories.map((c) => ({ id: c.category, label: CATEGORY_TEXT[c.category], value: c.coverage_rate, tone: c.mapped_stage === 'stage1' ? ('accent' as const) : c.mapped_stage === 'stage2' ? ('warn' as const) : ('bad' as const) }))}
          axis={{ label: { en: 'Coverage', es: 'Cobertura' }, format: { percent: true, decimals: 1 } }}
        />
          }
        >
        <div>
          <table className="caos-table ct-wrap-head" data-table="bde-categories">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Category', es: 'Categoría' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'IFRS 9 stage', es: 'Etapa IFRS 9' }, lang)}</th>
                <th>{`${pick({ en: 'Exposure', es: 'Exposición' }, lang)} (${cur})`}</th>
                <th>{pick({ en: 'Provision', es: 'Provisión' }, lang)}</th>
                <th>{pick({ en: 'Coverage', es: 'Cobertura' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {d.categories.map((c) => (
                <tr key={c.category} data-category={c.category} data-stage={c.mapped_stage}>
                  <td className="ct-text">{pick(CATEGORY_TEXT[c.category], lang)}</td>
                  <td className="ct-text">{c.mapped_stage === 'written-off' ? pick(STAGE_TEXT['written-off'], lang) : pick(STAGE_TEXT[c.mapped_stage], lang)}</td>
                  <td>{money(c.exposure, lang, cur)}</td>
                  <td>{money(c.provision, lang, cur)}</td>
                  <td>{pct(c.coverage_rate, lang, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ct-note">
            {d.method === 'alternative-solutions'
              ? pick({ en: 'Method: the alternative solutions of the Annex (Spanish GAAP), aligned with IFRS 9.', es: 'Método: las soluciones alternativas del Anexo (PGC español), alineadas con IFRS 9.' }, lang)
              : pick({ en: 'Method: internal methodology, validated under the Annex.', es: 'Método: metodología interna, validada bajo el Anexo.' }, lang)}
          </p>
        </div>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The scenario of the variant, its shocks, and its delta against the base; the base itself says it has none, with its reason. */
export function DeltaView({ sel }: { sel: C07Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const cur = o.currency;
  const dv = o.delta_vs_base;
  if (dv === null) {
    return (
      <ViewsRow>
        <PlotCard title={{ en: `Scenario ${o.scenario_id}`, es: `Escenario ${o.scenario_id}` }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
          <p>{pick(o.scenario.description, lang)}</p>
          <p className="caos-pending" data-state="unavailable">
            {pick({ en: 'Not available: this is the base scenario, the reference the other scenarios are measured against, so it has no change to report.', es: 'No disponible: este es el escenario base, la referencia contra la que se miden los otros, así que no tiene cambio que informar.' }, lang)}
          </p>
        </PlotCard>
      </ViewsRow>
    );
  }
  return (
    <ViewsRow shares={[1, 1]}>
      <PlotCard fill title={{ en: `Scenario ${o.scenario_id}`, es: `Escenario ${o.scenario_id}` }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <p>{pick(o.scenario.description, lang)}</p>
        {o.scenario.shocks.length === 0 ? (
          <p className="ct-note">{pick({ en: 'The scenario applies no shock to any driver.', es: 'El escenario no aplica shock a ningún motor.' }, lang)}</p>
        ) : (
          <table className="caos-table" data-table="shocks">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Driver', es: 'Motor' }, lang)}</th>
                <th>{pick({ en: 'Shock', es: 'Shock' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Unit', es: 'Unidad' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.scenario.shocks.map((s) => (
                <tr key={s.driver} data-driver={s.driver}>
                  <td className="ct-text">{s.driver}</td>
                  <td>{formatNumber(s.value, lang, { digits: 3 })}</td>
                  <td className="ct-text">{s.unit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </PlotCard>
      <PlotCard fill title={{ en: 'Change against the base scenario', es: 'Cambio contra el escenario base' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        {dv === null ? (
          <p className="caos-pending" data-state="unavailable">
            {pick({ en: 'Not available: this is the base scenario, the reference the other scenarios are measured against.', es: 'No disponible: este es el escenario base, la referencia contra la que se miden los otros.' }, lang)}
          </p>
        ) : (
          <table className="caos-table" data-table="delta-vs-base">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Regime', es: 'Régimen' }, lang)}</th>
                <th>{`${pick({ en: 'Change', es: 'Cambio' }, lang)} (${dv.currency})`}</th>
              </tr>
            </thead>
            <tbody>
              <tr data-delta="cmf-b1">
                <td className="ct-text">CMF B-1</td>
                <td>{money(dv.cmf_b1_delta, lang, dv.currency)}</td>
              </tr>
              <tr data-delta="ifrs9">
                <td className="ct-text">{pick(IFRS9_NAME, lang)}</td>
                <td>{money(dv.ifrs9_delta, lang, dv.currency)}</td>
              </tr>
              <tr data-delta="bde-annex9">
                <td className="ct-text">BdE Annex 9</td>
                <td>{money(dv.bde_annex9_delta, lang, dv.currency)}</td>
              </tr>
            </tbody>
          </table>
        )}
        <p className="ct-note">{pick({ en: `Amounts in ${cur}. The changes are the document's own, measured against the base scenario.`, es: `Montos en ${cur}. Los cambios son los del documento, medidos contra el escenario base.` }, lang)}</p>
      </PlotCard>
    </ViewsRow>
  );
}
