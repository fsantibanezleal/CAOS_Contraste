// C06's Impact group: where the book moved between two reporting dates (stage flow), what moved the allowance
// (waterfall, overlays as bars of their own), what the scenario weights do to the ECL (the simplex, staging
// recomputed against frozen) and the stage summary. The drawings are SVG at the size their stage measures; every
// drawing has its table beside it with the same numbers, and the numbers are the document's.
import { BarChart, PlotCard, Stage, ViewsRow, fitLabel, formatNumber, niceTicks, pick, useShellLang, useWorkbenchState, type BiText } from '@fasl-work/caos-app-shell';
import { useState } from 'react';
import { provenanceOf, REPLAY } from '../model';
import { viridis } from '../c04/MatrixMap';
import { Pending } from '../Pending';
import { columnScale } from './amounts';
import { ChartOverTable, STAGE_COLOR, STAGE_TEXT, MaybeNumber, axisScale, money, pct } from './format';
import { nearestPoint, outputsOf, rescaled, type C06Sel } from './selection';

const LIVE = 'live' as const;
const colorOf = (token: string) => `var(${token})`;

const SOURCES = ['new', 'stage1', 'stage2', 'stage3', 'poci'];
const TARGETS = ['stage1', 'stage2', 'stage3', 'poci', 'derecognised', 'written-off'];

interface Band {
  key: string;
  source: string;
  target: string;
  accounts: number;
  gca: number;
  y0: number;
  y1: number;
  h: number;
}

/** The bands of the flow, stacked on each side in the fixed order of the nodes; heights are proportional to the carrying amount. */
function layout(flows: Array<{ source: string; target: string; accounts: number; gross_carrying_amount: number }>, height: number) {
  const gap = 10;
  const total = (ids: string[], side: 'source' | 'target') => ids.map((id) => flows.filter((f) => f[side] === id).reduce((a, f) => a + f.gross_carrying_amount, 0));
  const left = total(SOURCES, 'source');
  const right = total(TARGETS, 'target');
  const nodesL = left.filter((v) => v > 0).length;
  const nodesR = right.filter((v) => v > 0).length;
  const sum = Math.max(left.reduce((a, b) => a + b, 0), right.reduce((a, b) => a + b, 0), 1);
  const usable = height - 2 * 12 - gap * (Math.max(nodesL, nodesR) - 1);
  const k = Math.max(usable, 20) / sum;
  const place = (ids: string[], totals: number[]) => {
    const pos: Record<string, { y: number; h: number }> = {};
    let y = 12;
    ids.forEach((id, i) => {
      if (totals[i] <= 0) return;
      pos[id] = { y, h: totals[i] * k };
      y += totals[i] * k + gap;
    });
    return pos;
  };
  const L = place(SOURCES, left);
  const R = place(TARGETS, right);
  const usedL: Record<string, number> = {};
  const usedR: Record<string, number> = {};
  const bands: Band[] = [];
  for (const s of SOURCES)
    for (const t of TARGETS)
      for (const f of flows.filter((x) => x.source === s && x.target === t)) {
        const h = f.gross_carrying_amount * k;
        const yL = L[s].y + (usedL[s] ?? 0);
        const yR = R[t].y + (usedR[t] ?? 0);
        usedL[s] = (usedL[s] ?? 0) + h;
        usedR[t] = (usedR[t] ?? 0) + h;
        bands.push({ key: `${s}>${t}`, source: s, target: t, accounts: f.accounts, gca: f.gross_carrying_amount, y0: yL, y1: yR, h });
      }
  return { L, R, bands };
}

/** A band is drawn at least 4 px thick (centred on its own position) so a sliver of a flow can still be pointed at; the layout stays proportional. */
function bandPath(b: Band, x0: number, x1: number, mid: number): string {
  const h = Math.max(b.h, 4);
  const y0 = b.y0 - (h - b.h) / 2;
  const y1 = b.y1 - (h - b.h) / 2;
  return `M${x0} ${y0} C${mid} ${y0} ${mid} ${y1} ${x1} ${y1} L${x1} ${y1 + h} C${mid} ${y1 + h} ${mid} ${y0 + h} ${x0} ${y0 + h} Z`;
}

/** The stage flow between two reporting dates: bands from the stage at the first date to the stage at the second. */
export function StageFlowView({ sel }: { sel: C06Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const [picked, setPicked] = useState<string | null>(null);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const f = o.stage_flows;
  const flows = f.flows;
  const chosen = flows.find((x) => `${x.source}>${x.target}` === picked) ?? null;
  const name = (id: string) => pick(STAGE_TEXT[id] ?? { en: id, es: id }, lang);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `Stage flow, ${f.from_date} to ${f.to_date}`, es: `Flujo de etapas, ${f.from_date} a ${f.to_date}` }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: 'Band height is the gross carrying amount. A flow out of a POCI account ends in derecognised or written off: a POCI account stays POCI for its life. Click a band, or the button of its row, to read it.',
          es: 'La altura de la banda es el valor en libros bruto. Un flujo que sale de una cuenta POCI termina en dada de baja o castigada: una cuenta POCI sigue POCI toda su vida. Pulse una banda, o el botón de su fila, para leerla.',
        }}
      >
        <ChartOverTable chart={
        <div className="ct-map">
          <Stage label={{ en: 'Stage flow between two reporting dates', es: 'Flujo de etapas entre dos fechas de reporte' }} className="ct-map-stage">
            {({ width, height }) => {
              const { L, R, bands } = layout(flows, height);
              const xL = 96;
              const xR = width - 96;
              const nodeW = 12;
              const mid = (xL + nodeW + xR) / 2;
              return (
                <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={pick({ en: 'Stage flow', es: 'Flujo de etapas' }, lang)}>
                  {/* the widest band first, so a thin band is drawn over a wide one. The bands cross, and two of them can cross exactly at their middle, so a band is not a control of its own: the mouse reads it by a click, the keyboard and the screen reader by the button of its row in the table */}
                  {[...bands].sort((a, b) => b.h - a.h).map((b) => (
                    <path
                      key={b.key}
                      data-flow-band={b.key}
                      d={bandPath(b, xL + nodeW, xR, mid)}
                      style={{ fill: colorOf(STAGE_COLOR[b.source]), opacity: picked === null || picked === b.key ? 0.5 : 0.15, stroke: picked === b.key ? 'var(--color-fg)' : 'var(--color-surface)', strokeWidth: picked === b.key ? 2 : 1.5 }}
                      aria-hidden="true"
                      onClick={() => setPicked(picked === b.key ? null : b.key)}
                    />
                  ))}
                  {SOURCES.filter((id) => L[id]).map((id) => (
                    <g key={`l-${id}`}>
                      <rect x={xL} y={L[id].y} width={nodeW} height={Math.max(L[id].h, 1)} style={{ fill: colorOf(STAGE_COLOR[id]) }} />
                      <text x={xL - 6} y={L[id].y + Math.min(L[id].h, 28) / 2 + 4} textAnchor="end" className="dg-axis-label">{fitLabel(name(id), xL - 10, 12, 1).lines[0]}</text>
                    </g>
                  ))}
                  {TARGETS.filter((id) => R[id]).map((id) => (
                    <g key={`r-${id}`}>
                      <rect x={xR} y={R[id].y} width={nodeW} height={Math.max(R[id].h, 1)} style={{ fill: colorOf(STAGE_COLOR[id]) }} />
                      <text x={xR + nodeW + 6} y={R[id].y + Math.min(R[id].h, 28) / 2 + 4} className="dg-axis-label">{fitLabel(name(id), width - xR - nodeW - 8, 12, 1).lines[0]}</text>
                    </g>
                  ))}
                  <text x={xL} y={10} className="dg-note">{f.from_date}</text>
                  <text x={xR + nodeW} y={10} textAnchor="end" className="dg-note">{f.to_date}</text>
                </svg>
              );
            }}
          </Stage>
          <p className="ct-note" aria-live="polite" data-flow-readout={picked ?? ''}>
            {chosen
              ? pick(
                  {
                    en: `${name(chosen.source)} to ${name(chosen.target)}: ${formatNumber(chosen.accounts, 'en', { decimals: 0 })} accounts, ${money(chosen.gross_carrying_amount, 'en', f.currency)} ${f.currency} gross carrying amount.`,
                    es: `${name(chosen.source)} a ${name(chosen.target)}: ${formatNumber(chosen.accounts, 'es', { decimals: 0 })} cuentas, ${money(chosen.gross_carrying_amount, 'es', f.currency)} ${f.currency} de valor en libros bruto.`,
                  },
                  lang,
                )
              : pick({ en: 'Pick a band to read its accounts and gross carrying amount.', es: 'Elija una banda para leer sus cuentas y su valor en libros bruto.' }, lang)}
          </p>
        </div>
        }>
        <div>
          <table className="caos-table" data-table="stage-flows">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'From', es: 'Desde' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'To', es: 'Hasta' }, lang)}</th>
                <th>{pick({ en: 'Accounts', es: 'Cuentas' }, lang)}</th>
                <th>{`${pick({ en: 'Gross carrying amount', es: 'Valor en libros bruto' }, lang)} (${f.currency})`}</th>
              </tr>
            </thead>
            <tbody>
              {flows.map((x) => (
                <tr key={`${x.source}>${x.target}`} data-flow={`${x.source}:${x.target}`} className={picked === `${x.source}>${x.target}` ? 'ct-current' : undefined}>
                  <td className="ct-text" style={{ whiteSpace: 'nowrap' }}>
                    <button type="button" className="ct-linkbutton" aria-pressed={picked === `${x.source}>${x.target}`} onClick={() => setPicked(picked === `${x.source}>${x.target}` ? null : `${x.source}>${x.target}`)}>
                      {name(x.source)}
                    </button>
                  </td>
                  <td className="ct-text" style={{ whiteSpace: 'nowrap' }}>{name(x.target)}</td>
                  <td>{formatNumber(x.accounts, lang, { decimals: 0 })}</td>
                  <td>{money(x.gross_carrying_amount, lang, f.currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ct-note">{pick({ en: `Between ${f.from_date} and ${f.to_date}.`, es: `Entre ${f.from_date} y ${f.to_date}.` }, lang)}</p>
        </div>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

const KIND_TONE = (kind: string, amount: number): string => (kind === 'opening' || kind === 'closing' ? '--color-accent' : kind === 'overlay' ? '--color-magenta' : amount >= 0 ? '--color-warn' : '--color-good');

/** The ECL waterfall from the opening to the closing allowance; every overlay is a bar of its own, apart from the model lines. */
export function WaterfallView({ sel }: { sel: C06Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const [picked, setPicked] = useState<string | null>(null);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const w = o.waterfall;
  const cur = w.currency;
  let run = 0;
  const bars = w.lines.map((l) => {
    const absolute = l.kind === 'opening' || l.kind === 'closing';
    const from = absolute ? 0 : run;
    const to = absolute ? l.amount : run + l.amount;
    run = absolute ? l.amount : to;
    return { line: l, lo: Math.min(from, to), hi: Math.max(from, to) };
  });
  const modelEcl = o.stage_summary.rows.reduce((a, r) => a + r.ecl, 0);
  const overlays = o.overlays.reduce((a, x) => a + x.amount, 0);
  const closing = w.lines.find((l) => l.kind === 'closing')?.amount ?? null;
  const label = (l: (typeof w.lines)[number]) => pick(l.label, lang);
  const chosen = w.lines.find((l) => l.id === picked) ?? null;
  return (
    <ViewsRow shares={[3, 2]}>
        <PlotCard
          fill
          title={{ en: 'Allowance waterfall, opening to closing', es: 'Cascada de la cobertura, de inicial a final' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: 'Each bar is a line of the IFRS 7 35H reconciliation. Overlays (magenta) are bars of their own and never part of the model ECL; a bar that lowers the allowance runs left.',
            es: 'Cada barra es una línea de la conciliación de IFRS 7 35H. Los ajustes (magenta) son barras propias y nunca parte de la PCE del modelo; una barra que baja la cobertura va a la izquierda.',
          }}
        >
          <div className="ct-map">
            <Stage label={{ en: 'ECL waterfall', es: 'Cascada de la PCE' }} className="ct-map-stage">
              {({ width, height }) => {
                const labelW = Math.min(Math.max(width * 0.36, 96), 190);
                const x0 = labelW + 8;
                const plotW = Math.max(width - x0 - 64, 40);
                const top = 8;
                const axis = 22;
                const rowH = (height - top - axis) / bars.length;
                const lo = Math.min(0, ...bars.map((b) => b.lo));
                const hi = Math.max(...bars.map((b) => b.hi), 1e-9);
                // the axis is in billions or millions, its scale said in the unit beside it: an eleven-digit tick is as wide as the unit
                const scale = axisScale(Math.max(Math.abs(lo), Math.abs(hi)), cur);
                const ticks = niceTicks(lo, hi, plotW, 54, 6);
                const dmin = Math.min(lo, ticks[0]);
                const dmax = Math.max(hi, ticks[ticks.length - 1]);
                const sx = (v: number) => x0 + ((v - dmin) / (dmax - dmin)) * plotW;
                return (
                  <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={pick({ en: 'ECL waterfall', es: 'Cascada de la PCE' }, lang)}>
                    {ticks.map((t) => (
                      <g key={t}>
                        <line className="dg-grid" x1={sx(t)} x2={sx(t)} y1={top} y2={height - axis} />
                        <text className="dg-tick" x={sx(t)} y={height - 6} textAnchor="middle">{formatNumber(t / scale.div, lang, { digits: 4 })}</text>
                      </g>
                    ))}
                    <text className="dg-note" x={width - 4} y={height - 6} textAnchor="end">{pick(scale.unit, lang)}</text>
                    {bars.map((b, i) => {
                      const y = top + i * rowH;
                      const h = Math.max(rowH * 0.62, 3);
                      const x = sx(b.lo);
                      const wd = Math.max(sx(b.hi) - sx(b.lo), 1.5);
                      const isPick = picked === b.line.id;
                      return (
                        <g key={b.line.id} data-bar={b.line.id} data-bar-kind={b.line.kind}>
                          <text className="dg-bar-label" x={labelW} y={y + rowH / 2 + 4} textAnchor="end">{fitLabel(label(b.line), labelW, 11, 1).lines[0]}</text>
                          <rect
                            x={x}
                            y={y + (rowH - h) / 2}
                            width={wd}
                            height={h}
                            style={{ fill: colorOf(KIND_TONE(b.line.kind, b.line.amount)), stroke: isPick ? 'var(--color-fg)' : 'none', strokeWidth: 2 }}
                            role="button"
                            tabIndex={0}
                            aria-label={`${label(b.line)}: ${money(b.line.amount, lang, cur)}`}
                            onClick={() => setPicked(isPick ? null : b.line.id)}
                            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setPicked(isPick ? null : b.line.id)}
                          />
                          <text className="dg-tick" x={x + wd + 4} y={y + rowH / 2 + 4}>{formatNumber(b.line.amount / scale.div, lang, { digits: 4 })}</text>
                        </g>
                      );
                    })}
                  </svg>
                );
              }}
            </Stage>
            <p className="ct-note" aria-live="polite">
              {chosen
                ? `${label(chosen)}: ${money(chosen.amount, lang, cur)} ${cur}${chosen.overlay_id ? pick({ en: ' (overlay, apart from the model ECL)', es: ' (ajuste, aparte de la PCE del modelo)' }, lang) : ''}`
                : pick({ en: 'Pick a bar to read its line.', es: 'Elija una barra para leer su línea.' }, lang)}
            </p>
          </div>
        </PlotCard>
        <PlotCard fill title={{ en: 'The lines in numbers', es: 'Las líneas en números' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
          <div className="ct-scroll" data-caos-flow="">
            <table className="caos-table" data-table="waterfall">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Line', es: 'Línea' }, lang)}</th>
                  <th>{`${pick({ en: 'Amount', es: 'Monto' }, lang)} (${cur})`}</th>
                </tr>
              </thead>
              <tbody>
                {w.lines.map((l) => (
                  <tr key={l.id} data-line={l.id} data-kind={l.kind} className={l.kind === 'overlay' ? 'ct-current' : undefined}>
                    <td className="ct-text">{label(l)}</td>
                    <td>{money(l.amount, lang, cur)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr data-total="model-ecl">
                  <td className="ct-text">{pick({ en: 'Model ECL, overlays excluded', es: 'PCE del modelo, sin ajustes' }, lang)}</td>
                  <td>{money(modelEcl, lang, cur)}</td>
                </tr>
                <tr data-total="overlays">
                  <td className="ct-text">{pick({ en: 'Overlays, each its own line', es: 'Ajustes, cada uno su propia línea' }, lang)}</td>
                  <td>{money(overlays, lang, cur)}</td>
                </tr>
                <tr data-total="closing">
                  <td className="ct-text">{pick({ en: 'Closing allowance', es: 'Cobertura final' }, lang)}</td>
                  <td>
                    <MaybeNumber value={closing} reason={null} format={(v) => money(v, lang, cur)} />
                  </td>
                </tr>
              </tfoot>
            </table>
            <h3 className="ct-sub">{pick({ en: 'The overlays, one by one', es: 'Los ajustes, uno por uno' }, lang)}</h3>
            <p className="ct-note">{pick({ en: 'An overlay is judgement on top of the model, kept with its rationale, method, review date and whether it moves accounts between stages; it is not a validated model.', es: 'Un ajuste es juicio sobre el modelo, guardado con su justificación, método, fecha de revisión y si mueve cuentas entre etapas; no es un modelo validado.' }, lang)}</p>
            {o.overlays.length === 0 ? (
          <p className="ct-note" data-state="unavailable">{pick({ en: 'This variant carries no overlay.', es: 'Esta variante no lleva ajustes.' }, lang)}</p>
        ) : (
          <div className="ct-scroll" data-caos-flow="">
            <table className="caos-table ct-wrap-head" data-table="overlays">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Overlay', es: 'Ajuste' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Rationale', es: 'Justificación' }, lang)}</th>
                  <th className="ct-text ct-wide-only">{pick({ en: 'Method and target', es: 'Método y objetivo' }, lang)}</th>
                  <th className="ct-text ct-wide-only">{pick({ en: 'Staging effect', es: 'Efecto en etapas' }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: 'Review', es: 'Revisión' }, lang)}</th>
                  <th>{`${pick({ en: 'Amount', es: 'Monto' }, lang)} (${cur})`}</th>
                </tr>
              </thead>
              <tbody>
                {o.overlays.map((ov) => (
                  <tr key={ov.id} data-overlay={ov.id}>
                    <td className="ct-text">{ov.id}</td>
                    <td className="ct-text">{pick(ov.rationale, lang)}</td>
                    <td className="ct-text ct-wide-only">{`${ov.method}, ${ov.target}${ov.segment_id ? `, ${ov.segment_id}` : ''}`}</td>
                    <td className="ct-text ct-wide-only">{ov.staging_effect === 'none' ? pick({ en: 'none', es: 'ninguno' }, lang) : pick({ en: 'moves accounts to Stage 2', es: 'mueve cuentas a la Etapa 2' }, lang)}</td>
                    <td className="ct-wide-only">{ov.review_date}</td>
                    <td>{money(ov.amount, lang, ov.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
          </div>
        </PlotCard>
      </ViewsRow>
  );
}

const CORNER_ANGLES = [-90, 30, 150];

/** The ternary heat map of the scenario-weight simplex, with the live weights marked; a table of every grid point. */
export function WeightsView({ sel }: { sel: C06Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const g = o.weight_grid;
  const cur = g.currency;
  const weights = rescaled(o, sel.scenario, sel.weight);
  const near = nearestPoint(o, weights);
  const value = (p: (typeof g.points)[number]) =>
    sel.surface === 'ecl' ? (sel.staging === 'recomputed' ? p.ecl_recomputed : p.ecl_frozen) : sel.staging === 'recomputed' ? p.stage2_ratio_recomputed : p.stage2_ratio_frozen;
  const vals = g.points.map(value);
  const vlo = Math.min(...vals);
  const vhi = Math.max(...vals);
  const t = (v: number) => (vhi > vlo ? (v - vlo) / (vhi - vlo) : 0.5);
  // the colour scale reads in the unit of the amounts (billions, millions), never as eleven bare digits (U16-R2 b03 M4)
  const sc = axisScale(Math.max(Math.abs(vlo), Math.abs(vhi)), cur);
  const fmt = (v: number) => (sel.surface === 'ecl' ? `${formatNumber(v / sc.div, lang, { digits: 4 })} ${pick(sc.unit, lang)}` : pct(v, lang, 2));
  const scenarioLabel = (id: string): BiText => o.scenarios.find((s) => s.id === id)?.label ?? { en: id, es: id };
  const ternary = g.scenario_ids.length === 3;
  const eclScale = columnScale(g.points.flatMap((p) => [p.ecl_recomputed, p.ecl_frozen]), cur);
  return (
    <ViewsRow shares={[1, 1]}>
      <PlotCard
        fill
        title={{
          en: `Scenario-weight simplex: ${sel.surface === 'ecl' ? 'ECL' : 'Stage 2 share'}, staging ${sel.staging}`,
          es: `Simplex de pesos de escenarios: ${sel.surface === 'ecl' ? 'PCE' : 'fracción en Etapa 2'}, etapas ${sel.staging === 'recomputed' ? 'recalculadas' : 'congeladas'}`,
        }}
        lane={LIVE}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: 'Each corner is one scenario at 100% weight. Staging recomputed moves accounts between stages as the weights change; frozen keeps the staging at the weighted conditions, and then the ECL is linear in the weights. The ring is the rail\'s weights.',
          es: 'Cada vértice es un escenario con 100 % de peso. Etapas recalculadas mueve cuentas entre etapas al cambiar los pesos; congeladas mantiene las etapas en las condiciones ponderadas, y entonces la PCE es lineal en los pesos. El anillo son los pesos del panel.',
        }}
      >
        {ternary ? (
          <div className="ct-map">
            <Stage label={{ en: 'Scenario-weight simplex', es: 'Simplex de pesos de escenarios' }} className="ct-map-stage">
              {({ width, height }) => {
                // the two lower labels run outwards from their corners: the drawing leaves each the room its fitted label needs
                const labelW = Math.min(Math.max(width * 0.26, 64), 150);
                const r = Math.max(Math.min((width / 2 - labelW - 14) / 0.866, (height - 60) / 1.5), 30);
                const cx = width / 2;
                const cy = height / 2 + r * 0.1;
                const corner = CORNER_ANGLES.map((a) => [cx + r * Math.cos((a * Math.PI) / 180), cy + r * Math.sin((a * Math.PI) / 180)] as const);
                const at = (w: number[]) => [w[0] * corner[0][0] + w[1] * corner[1][0] + w[2] * corner[2][0], w[0] * corner[0][1] + w[1] * corner[1][1] + w[2] * corner[2][1]] as const;
                const live = at(weights);
                return (
                  <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={pick({ en: 'Scenario-weight simplex', es: 'Simplex de pesos de escenarios' }, lang)}>
                    <polygon points={corner.map((c) => c.join(',')).join(' ')} style={{ fill: 'none', stroke: 'var(--color-border)', strokeWidth: 1.3 }} />
                    {g.points.map((p) => {
                      const [x, y] = at(p.weights);
                      return <circle key={p.weights.join('/')} cx={x} cy={y} r={Math.max(Math.min(r / 9, 14), 5)} style={{ fill: viridis(t(value(p))), stroke: 'var(--color-surface)', strokeWidth: 1 }}><title>{`${p.weights.map((x2) => pct(x2, lang, 0)).join(' / ')}: ${fmt(value(p))}`}</title></circle>;
                    })}
                    <circle cx={live[0]} cy={live[1]} r={Math.max(Math.min(r / 9, 14), 5) + 4} data-live-weights={weights.map((x) => String(Math.round(x * 1000) / 1000)).join('/')} style={{ fill: 'none', stroke: 'var(--color-fg)', strokeWidth: 2.4 }} />
                    {g.scenario_ids.map((id, i) => {
                      const [x, y] = corner[i];
                      const anchor = i === 0 ? 'middle' : i === 1 ? 'start' : 'end';
                      const dy = i === 0 ? -20 : 28;
                      const dx = i === 0 ? 0 : i === 1 ? 8 : -8;
                      const full = pick(scenarioLabel(id), lang);
                      return (
                        <text key={id} x={x + dx} y={y + dy} textAnchor={anchor} className="dg-axis-label">
                          {fitLabel(full, i === 0 ? Math.min(width * 0.8, 220) : labelW, 12, 2).lines.map((line, k) => (
                            <tspan key={k} x={x + dx} dy={k === 0 ? 0 : 13}>{line}</tspan>
                          ))}
                          <title>{full}</title>
                        </text>
                      );
                    })}
                  </svg>
                );
              }}
            </Stage>
            <div data-colour-bar="simplex" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <span className="ct-note">{fmt(vlo)}</span>
              <span aria-hidden="true" style={{ flex: '1 1 6rem', minWidth: '6rem', height: '0.6rem', borderRadius: 3, background: `linear-gradient(to right, ${[0, 0.25, 0.5, 0.75, 1].map((x) => viridis(x)).join(', ')})` }} />
              <span className="ct-note">{fmt(vhi)}</span>
            </div>
            <p className="ct-note">{pick({ en: `Colour: ${fmt(vlo)} (dark) to ${fmt(vhi)} (light).`, es: `Color: ${fmt(vlo)} (oscuro) a ${fmt(vhi)} (claro).` }, lang)}</p>
          </div>
        ) : (
          <p className="ct-note" data-state="unavailable">
            {pick({ en: `The simplex drawing needs exactly three scenarios; this variant has ${g.scenario_ids.length}. The grid is in the table.`, es: `El dibujo del simplex necesita exactamente tres escenarios; esta variante tiene ${g.scenario_ids.length}. La grilla está en la tabla.` }, lang)}
          </p>
        )}
      </PlotCard>
      <PlotCard
        fill
        title={{ en: 'The grid in numbers', es: 'La grilla en números' }}
        lane={LIVE}
        provenance={prov}
        dataKey={stateKey}
        note={{
          en: `Weights in the order: ${g.scenario_ids.map((id) => pick(scenarioLabel(id), 'en')).join(' / ')}.`,
          es: `Pesos en el orden: ${g.scenario_ids.map((id) => pick(scenarioLabel(id), 'es')).join(' / ')}.`,
        }}
      >
        <div className="ct-scroll" data-caos-flow="">
          <table className="caos-table ct-wrap-head" data-table="weight-grid">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Weights', es: 'Pesos' }, lang)}</th>
                <th>{`${pick({ en: 'ECL, recomputed', es: 'PCE, recalculada' }, lang)} (${pick(eclScale.unit, lang)})`}</th>
                <th>{`${pick({ en: 'ECL, frozen', es: 'PCE, congelada' }, lang)} (${pick(eclScale.unit, lang)})`}</th>
                <th className="ct-wide-only">{pick({ en: 'Stage 2, recomputed', es: 'Etapa 2, recalculada' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Stage 2, frozen', es: 'Etapa 2, congelada' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {g.points.map((p) => (
                <tr key={p.weights.join('/')} data-weights={p.weights.join('/')} className={p === near ? 'ct-current' : undefined}>
                  <td className="ct-text" style={{ whiteSpace: 'nowrap' }}>{p.weights.map((x) => pct(x, lang, 0)).join(' / ')}</td>
                  <td>{eclScale.fmt(p.ecl_recomputed, lang)}</td>
                  <td>{eclScale.fmt(p.ecl_frozen, lang)}</td>
                  <td className="ct-wide-only">{pct(p.stage2_ratio_recomputed, lang, 1)}</td>
                  <td className="ct-wide-only">{pct(p.stage2_ratio_frozen, lang, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

const STAGE_TONE: Record<string, 'accent' | 'warn' | 'bad' | 'neutral'> = { stage1: 'accent', stage2: 'warn', stage3: 'bad', poci: 'neutral' };

/** The ECL and the coverage by stage, with the allowance closing beside the model ECL (overlays sit in the closing, not in the ECL). */
export function StageSummaryView({ sel }: { sel: C06Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const s = o.stage_summary;
  const closing = (stage: string) => o.reconciliation.allowance.find((r) => r.stage === stage)?.closing ?? null;
  const gcaScale = columnScale(s.rows.map((r) => r.gross_carrying_amount), s.currency);
  const eclScale = columnScale(s.rows.map((r) => r.ecl), s.currency);
  const closingScale = columnScale(s.rows.map((r) => closing(r.stage)), s.currency);
  return (
    <ViewsRow shares={[2, 3]}>
      <PlotCard fill title={{ en: 'Coverage by stage', es: 'Cobertura por etapa' }} lane={REPLAY} provenance={prov} dataKey={stateKey} note={{ en: 'Coverage is the model ECL over the gross carrying amount of the stage.', es: 'La cobertura es la PCE del modelo sobre el valor en libros bruto de la etapa.' }}>
        <BarChart
          title={{ en: 'Coverage by stage', es: 'Cobertura por etapa' }}
          height="fill"
          orientation="vertical"
          data={s.rows.map((r) => ({ id: r.stage, label: STAGE_TEXT[r.stage], value: r.coverage, tone: STAGE_TONE[r.stage] }))}
          axis={{ label: { en: 'Coverage', es: 'Cobertura' }, format: { percent: true, decimals: 1 } }}
        />
      </PlotCard>
      <PlotCard fill title={{ en: 'The stages in numbers', es: 'Las etapas en números' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <div className="ct-scroll" data-caos-flow="">
          <table className="caos-table ct-wrap-head" data-table="stage-summary">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Stage', es: 'Etapa' }, lang)}</th>
                <th>{pick({ en: 'Accounts', es: 'Cuentas' }, lang)}</th>
                <th>{`${pick({ en: 'Gross carrying amount', es: 'Valor en libros bruto' }, lang)} (${pick(gcaScale.unit, lang)})`}</th>
                <th>{`${pick({ en: 'Model ECL', es: 'PCE del modelo' }, lang)} (${pick(eclScale.unit, lang)})`}</th>
                <th>{pick({ en: 'Coverage', es: 'Cobertura' }, lang)}</th>
                <th className="ct-wide-only">{`${pick({ en: 'Allowance closing, with overlays', es: 'Provisión final, con ajustes' }, lang)} (${pick(closingScale.unit, lang)})`}</th>
              </tr>
            </thead>
            <tbody>
              {s.rows.map((r) => (
                <tr key={r.stage} data-stage={r.stage}>
                  <td className="ct-text">{pick(STAGE_TEXT[r.stage], lang)}</td>
                  <td>{formatNumber(r.accounts, lang, { decimals: 0 })}</td>
                  <td>{gcaScale.fmt(r.gross_carrying_amount, lang)}</td>
                  <td>{eclScale.fmt(r.ecl, lang)}</td>
                  <td>{pct(r.coverage, lang, 2)}</td>
                  <td className="ct-wide-only">
                    <MaybeNumber value={closing(r.stage)} reason={null} format={(v) => closingScale.fmt(v, lang)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

