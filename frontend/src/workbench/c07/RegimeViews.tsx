// C07's views: the three regimes side by side (CMF B-1, IFRS 9, BdE Annex 9) with the segments and the bridge from the
// B-1 comparable total to the IFRS 9 total, each regime in its own detail (the B-1 minimum and max rule, the IFRS 9
// probability-weighted components with the overlays apart, the BdE categories mapped to stages), and the scenario's
// delta against the base. Every drawing has its table with the same numbers; every number is the document's.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, useWorkbenchState, type BarDatum, type BiText } from '@fasl-work/caos-app-shell';
import { ChartOverTable, MaybeNumber, STAGE_TEXT, money, pct } from '../c06/format';
import { REPLAY, provenanceOf } from '../model';
import { Pending } from '../Pending';
import { FixtureNotice } from '../c06/C06Common';
import { componentLabel, outputsOf, type C07Outputs, type C07Sel, type RegimeId } from './selection';

/** The short name of each regime, as the rail's chips name it: a grouped bar's member label (the full names are in the legend; R2b
 * c08 M1: the full names were cut mid-word under every group). */
const REGIME_SHORT: Record<RegimeId, BiText> = { 'cmf-b1': { en: 'B-1', es: 'B-1' }, ifrs9: { en: 'IFRS 9', es: 'IFRS 9' }, 'bde-annex9': { en: 'BdE 9', es: 'BdE 9' } };

/** The macro drivers and units of a scenario's shocks in words (R2b c08 B2: "gdp-growth", "percentage points" in the Spanish page). */
const DRIVER_TEXT: Record<string, BiText> = {
  'gdp-growth': { en: 'GDP growth', es: 'Crecimiento del PIB' },
  unemployment: { en: 'Unemployment', es: 'Desempleo' },
  'house-prices': { en: 'House prices', es: 'Precios de la vivienda' },
  'consumer-arrears': { en: 'Consumer arrears', es: 'Morosidad de consumo' },
  'uf-inflation': { en: 'UF inflation', es: 'Inflación de la UF' },
};
const UNIT_TEXT: Record<string, BiText> = {
  'percentage points': { en: 'percentage points', es: 'puntos porcentuales' },
  percent: { en: 'percent', es: 'por ciento' },
};

/** A scenario by the name its variant has in the case manifest, never its id (R2b c08 B2). */
function scenarioName(sel: C07Sel, id: string): BiText {
  const a = sel.data.manifest.artifacts.find((x) => x.role === 'variant' && x.variant_id === id);
  return (a?.short_title ?? a?.title ?? { en: id, es: id }) as BiText;
}

const LIVE = 'live' as const;
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

const segmentName = (o: C07Outputs, id: string): BiText => o.portfolio.segments.find((x) => x.segment_id === id)?.label ?? { en: id, es: id };

const CATEGORY_TEXT: Record<string, BiText> = {
  normal: { en: 'Normal', es: 'Normal' },
  'normal-special-watch': { en: 'Normal, special watch', es: 'Normal en vigilancia especial' },
  doubtful: { en: 'Doubtful', es: 'Dudoso' },
  'written-off': { en: 'Written off', es: 'Fallido' },
};

/** Grouped bars: one group per segment, one bar per regime, drawn by the shell (D16-21); the bar under the pointer or the keyboard is
 * read in the shell's live readout. */
function GroupedBars({ o, sel }: { o: C07Outputs; sel: C07Sel }) {
  const lang = useShellLang();
  const cur = o.currency;
  const segs = o.comparison.rows;
  const value = (r: (typeof segs)[number], id: RegimeId) => (id === 'cmf-b1' ? r.cmf_b1_provision : id === 'ifrs9' ? r.ifrs9_provision : r.bde_annex9_provision);
  const ids: RegimeId[] = ['cmf-b1', 'ifrs9', 'bde-annex9'];
  const nameOf = (id: RegimeId) => regimeName(id, o.regimes.find((r) => r.regime === id)?.label ?? { en: id, es: id });
  // 18 bars in six groups need about 28 rem: on a phone the card is as tall as what it holds, and the stage kept 160 px, so the
  // drawing showed 4 of 6 segments and no axis (R3 c08 M2)
  return (
    <div className="ct-map" data-caos-flow="" style={{ minHeight: 'max(28rem, calc(50rem - 25vw))' }}>
      <BarChart
        title={{ en: 'Provision by segment under the three regimes', es: 'Provisión por segmento bajo los tres regímenes' }}
        height="fill"
        data={segs.flatMap((r) =>
          ids.map((id) => ({
            id: `${r.segment_id}|${id}`,
            label: REGIME_SHORT[id],
            group: { id: r.segment_id, label: segmentName(o, r.segment_id) },
            value: value(r, id) / 1e6,
            tone: REGIME_TONE[id],
            highlight: sel.regime === id,
          })),
        )}
        legend={ids.map((id) => ({ tone: REGIME_TONE[id], label: nameOf(id) }))}
        axis={{ label: { en: 'Provision', es: 'Provisión' }, unit: { en: `${cur} millions`, es: `millones de ${cur}` }, format: { digits: 3 } }}
      />
      <p className="ct-note">
        {pick({ en: 'Blue is B-1, amber is IFRS 9 (probability-weighted), green is BdE Annex 9.', es: 'Azul es B-1, ámbar es IFRS 9 (ponderada por probabilidad), verde es Anejo 9 del BdE.' }, lang)}
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
        title={{ en: `The three regimes, scenario ${pick(scenarioName(sel, o.scenario_id), 'en')} (${cur} millions)`, es: `Los tres regímenes, escenario ${pick(scenarioName(sel, o.scenario_id), 'es')} (millones de ${cur})` }}
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
  // the drawing and the gap table a card each (R3 c08 M1: under a 28 rem drawing in one card, the table kept half a row at 1280 and
  // the drawing lost its last bar and its value axis); the gap table takes three fifths of the row and shows the two gaps it is named
  // for next to the segment (U16-R4 c09 M1: in half the row both gap columns were cut at the card edge)
  return (
    <ViewsRow shares={[2, 3]}>
      <PlotCard
        fill
        title={{ en: 'Provision by segment under the three regimes', es: 'Provisión por segmento bajo los tres regímenes' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
      >
        <GroupedBars o={o} sel={sel} />
      </PlotCard>
      <PlotCard
        fill
        title={{ en: 'The gaps against B-1 by segment', es: 'Las brechas contra B-1 por segmento' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={{ en: 'A positive gap means the regime provisions more than B-1 for that segment. The IFRS 9 column is the model ECL without overlays; overlays and the B-1 minimum top-up are in the unallocated row.', es: 'Una brecha positiva significa que el régimen provisiona más que B-1 en ese segmento. La columna IFRS 9 es la PCE del modelo sin ajustes; los ajustes y el complemento del mínimo de B-1 están en la fila no asignada.' }}
      >
        <div className="ct-scroll" data-caos-flow="">
      <table className="caos-table ct-wrap-head" data-table="segments">
        <thead>
          <tr>
            <th className="ct-text">{pick({ en: 'Segment', es: 'Segmento' }, lang)}</th>
            <th>{pick({ en: 'IFRS 9 minus B-1', es: 'IFRS 9 menos B-1' }, lang)}</th>
            <th>{pick({ en: 'BdE minus B-1', es: 'BdE menos B-1' }, lang)}</th>
            <th>{`CMF B-1 (${cur})`}</th>
            <th>{pick({ en: 'IFRS 9 (weighted)', es: 'IFRS 9 (ponderada)' }, lang)}</th>
            <th>{pick({ en: 'BdE Annex 9', es: 'Anejo 9 del BdE' }, lang)}</th>
          </tr>
        </thead>
        <tbody>
          {c.rows.map((r) => (
            <tr key={r.segment_id} data-segment={r.segment_id} className={sel.segment === r.segment_id ? 'ct-current' : undefined}>
              <td className="ct-text">{label(r.segment_id)}</td>
              <td>{money(r.gap_ifrs9_minus_b1, lang, cur)}</td>
              <td>{money(r.gap_bde_minus_b1, lang, cur)}</td>
              <td>{money(r.cmf_b1_provision, lang, cur)}</td>
              <td>{money(r.ifrs9_provision, lang, cur)}</td>
              <td>{money(r.bde_annex9_provision, lang, cur)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr data-row="unallocated">
            <td className="ct-text">{pick({ en: 'Unallocated lines', es: 'Líneas no asignadas' }, lang)}</td>
            <td>{money(c.unallocated.gap_ifrs9_minus_b1, lang, cur)}</td>
            <td>{money(c.unallocated.gap_bde_minus_b1, lang, cur)}</td>
            <td>{money(c.unallocated.cmf_b1_provision, lang, cur)}</td>
            <td>{money(c.unallocated.ifrs9_provision, lang, cur)}</td>
            <td>{money(c.unallocated.bde_annex9_provision, lang, cur)}</td>
          </tr>
        </tfoot>
      </table>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

/** A bridge step's name on the drawing: the words before its colon ("Measurement basis"), else the whole label. */
export function stepShort(label: { en: string; es: string }): { en: string; es: string } {
  const cut = (t: string) => (t.includes(': ') ? t.slice(0, t.indexOf(': ')) : t);
  return { en: cut(label.en), es: cut(label.es) };
}

/** The bridge from the B-1 comparable total to the IFRS 9 total: exhaustive steps that sum to the gap. */
export function BridgeView({ sel }: { sel: C07Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
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
  // the totals are dots and the steps float from the running total, in millions; the axis spans the running total only (it does not start at zero)
  let run = from.total_provision / 1e6;
  const bars: BarDatum[] = [
    { id: 'from', label: from.label, value: from.total_provision / 1e6, span: [from.total_provision / 1e6, from.total_provision / 1e6], tone: 'accent' },
    ...b.steps.map((s): BarDatum => {
      const start = run;
      run += s.amount / 1e6;
      // the drawing names a step by the words before its colon, the full label is the bar's hint (U16-R4 c09 n1: cut with an ellipsis)
      return { id: s.id, label: stepShort(s.label), hint: s.label, value: s.amount / 1e6, span: [start, run], tone: s.amount >= 0 ? 'bad' : 'good' };
    }),
    { id: 'to', label: IFRS9_NAME, value: to.total_provision / 1e6, span: [to.total_provision / 1e6, to.total_provision / 1e6], tone: 'warn' },
  ];
  const zeros = b.steps.filter((s) => s.amount === 0).map((s) => s.label);
  const ends = bars.flatMap((x) => x.span as [number, number]);
  const lo0 = Math.min(...ends);
  const hi0 = Math.max(...ends);
  const pad = Math.max((hi0 - lo0) * 0.12, 1);
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
          <BarChart
            title={{ en: 'Bridge from B-1 to IFRS 9', es: 'Puente de B-1 a IFRS 9' }}
            height="fill"
            data={bars}
            axis={{ label: { en: 'Provision', es: 'Provisión' }, unit: { en: `${cur} millions`, es: `millones de ${cur}` }, format: { digits: 4 }, range: [lo0 - pad, hi0 + pad] }}
          />
          <p className="ct-note">
            {pick({ en: `Millions of ${cur}; the axis covers the running total of the bridge, and the two totals are the dots`, es: `Millones de ${cur}; el eje cubre el total acumulado del puente, y los dos totales son los puntos` }, lang)}
            {/* a step of zero has no length, so the shell draws it as a dot too (U16-R4 c09 m2) */}
            {zeros.length
              ? lang === 'en'
                ? `; a step of zero (${zeros.map((z) => z.en).join(', ')}) is a dot on the running total.`
                : `; un paso de cero (${zeros.map((z) => z.es).join(', ')}) es un punto sobre el total acumulado.`
              : '.'}
          </p>
        </div>
      </PlotCard>
      <PlotCard fill title={{ en: 'The steps in numbers', es: 'Los pasos en números' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <div className="ct-scroll" data-caos-flow="">
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
        note={{ en: 'The group provision is the larger of the standard method and the internal one, unless the CMF has not objected to the internal one. The 0.50% minimum applies to the individually assessed normal portfolio.', es: 'La provisión grupal es la mayor entre el método estándar y el interno, salvo que la CMF no haya objetado el interno. El mínimo de 0,50 % se aplica a la cartera normal evaluada individualmente.' }}
      >
        <div className="ct-scroll" data-caos-flow="">
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
        <div className="ct-scroll" data-caos-flow="">
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
        note={{ en: 'The IFRS 9 measure is the weighted sum of the scenarios (5.5.17(a), B5.5.42). A single scenario at 100% weight is a sensitivity and never the measure. IFRS 9 5.5 is carved out for bank loans in Chile: this is a comparison, not the provision Chilean banks book.', es: 'La medida IFRS 9 es la suma ponderada de los escenarios (5.5.17(a), B5.5.42). Un solo escenario con 100 % de peso es una sensibilidad y nunca la medida. IFRS 9 5.5 está excluida para los créditos bancarios en Chile: esto es una comparación, no la provisión que constituyen los bancos chilenos.' }}
      >
        <div className="ct-scroll" data-caos-flow="" data-measure={d.measure}>
          <table className="caos-table ct-wrap-head" data-table="ifrs9-components">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Scenario', es: 'Escenario' }, lang)}</th>
                <th>{pick({ en: 'Weight', es: 'Peso' }, lang)}</th>
                <th>z</th>
                <th>{`${pick({ en: 'ECL at 100% weight (sensitivity)', es: 'PCE con 100 % de peso (sensibilidad)' }, lang)} (${cur})`}</th>
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
          <div className="ct-scroll" data-caos-flow="">
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
      <PlotCard fill title={{ en: 'BdE Annex 9: coverage by category', es: 'Anejo 9 del BdE: cobertura por categoría' }} lane={REPLAY} provenance={prov} dataKey={stateKey} note={{ en: 'The coverage of each category over its exposure, with the percentages of the alternative solutions of the Annex.', es: 'La cobertura de cada categoría sobre su exposición, con los porcentajes de las soluciones alternativas del Anejo.' }}>
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
              ? pick({ en: 'Method: the alternative solutions of the Annex (Spanish GAAP), aligned with IFRS 9.', es: 'Método: las soluciones alternativas del Anejo (PGC español), alineadas con IFRS 9.' }, lang)
              : pick({ en: 'Method: internal methodology, validated under the Annex.', es: 'Método: metodología interna, validada bajo el Anejo.' }, lang)}
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
        <PlotCard title={{ en: `Scenario ${pick(scenarioName(sel, o.scenario_id), 'en')}`, es: `Escenario ${pick(scenarioName(sel, o.scenario_id), 'es')}` }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
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
      <PlotCard fill title={{ en: `Scenario ${pick(scenarioName(sel, o.scenario_id), 'en')}`, es: `Escenario ${pick(scenarioName(sel, o.scenario_id), 'es')}` }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <p>{pick(o.scenario.description, lang)}</p>
        {o.scenario.shocks.length === 0 ? (
          <p className="ct-note">{pick({ en: 'The scenario applies no shock to any driver.', es: 'El escenario no aplica choque a ningún motor.' }, lang)}</p>
        ) : (
          <table className="caos-table" data-table="shocks">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Driver', es: 'Motor' }, lang)}</th>
                <th>{pick({ en: 'Shock', es: 'Choque' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Unit', es: 'Unidad' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.scenario.shocks.map((s) => (
                <tr key={s.driver} data-driver={s.driver}>
                  <td className="ct-text">{pick(DRIVER_TEXT[s.driver] ?? { en: s.driver, es: s.driver }, lang)}</td>
                  <td>{formatNumber(s.value, lang, { digits: 3 })}</td>
                  <td className="ct-text">{pick(UNIT_TEXT[s.unit] ?? { en: s.unit, es: s.unit }, lang)}</td>
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
                <td className="ct-text">{pick({ en: 'BdE Annex 9', es: 'Anejo 9 del BdE' }, lang)}</td>
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
