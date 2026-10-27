// C18's Capital group: does the bank hold its internal capital target for three years (the CET1 over RWA fan of the base, the
// stress without mitigation and the stress with mitigation, against the layers of the OI), what the target and the legal
// minimum are made of (the capital stack waterfall, the P2G proxy), and the summary table of Annex 3 of the IAPE. The loss-only
// depletion is the headline path; the PPNR path is a labelled row apart from it. Every line, bar and cell is a field of the
// document; the running sums that stack a layer are layout.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable, MaybeNumber } from '../c06/format';
import { useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { Marked } from '../c21/Marked';
import { Defs, NOT_SCENARIO, PCT, UnavailableCard, cell } from './C18Common';
import { stackBars } from './Waterfall';
import {
  ANNEX3_EN, ANNEX3_ES, CELL_TEXT, LABEL_TEXT, MONEY_UNIT, P2G_LABEL, PLAN_LONG, PLAN_ORDER, PLAN_TEXT, REQUIREMENT_TEXT, axisOf, fitOf, outputsOf, planOf, text,
  type C18Cell, type C18Sel,
} from './selection';
import { phraseEs } from './localise';

/** The requirement keeps the two decimals of every other cell of the table, and a third only where the legal figure needs it (9.125 %). */
export const requirementDecimals = (v: number): 2 | 3 => (Math.abs(v * 1e4 - Math.round(v * 1e4)) < 1e-6 ? 2 : 3);
const PLAN_COLOR = { base: '--color-accent', 'stress-without-mitigation': '--color-bad', 'stress-with-mitigation': '--color-good' } as const;

/** The CET1 over RWA of the three plans from the jump-off to year 3, against the layers of the OI, with the plan in numbers beneath. */
export function FanView({ sel }: { sel: C18Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The three-year CET1 fan against the internal target', es: 'El abanico de CET1 a tres años frente al objetivo interno' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SCENARIO} />;
  const t = o.internal_capital_target;
  const plan = PLAN_ORDER.map((id) => planOf(o, id)).filter((c): c is NonNullable<typeof c> => c !== null);
  const start = o.capital_start.cet1_ratio;
  const ppnr = o.headline_cet1.ppnr;
  const layers: Array<{ y: number; label: BiText; tone: 'neutral' | 'warn' }> = [];
  let run = 0;
  for (const [size, label, tone] of [
    [t.min_pe, { en: 'OI: minimum 8%', es: 'OI: mínimo 8 %' }, 'neutral'],
    [t.c_dsib, { en: 'OI: + D-SIB', es: 'OI: + D-SIB' }, 'neutral'],
    [t.c_p2.value, { en: 'OI: + Pillar 2', es: 'OI: + Pilar 2' }, 'neutral'],
    [t.c_ccob, { en: 'OI: + conservation', es: 'OI: + conservación' }, 'neutral'],
    [t.c_ccyb, { en: 'OI: + countercyclical', es: 'OI: + contracíclico' }, 'neutral'],
    [t.c_d.value, { en: 'OI: + d = target', es: 'OI: + d = objetivo' }, 'warn'],
  ] as Array<[number, BiText, 'neutral' | 'warn']>) {
    run += size;
    layers.push({ y: run, label, tone });
  }
  const m = o.capital_plan.mitigation;
  const rowsOfPlan = plan.flatMap((c) => c.years.map((y) => ({ c, y })));
  const baseCase = plan.find((c) => c.case === 'base');
  const ppnrIsBase = !!baseCase && ppnr.rows.every((r) => Math.abs((baseCase.years.find((y) => y.year === r.year)?.cet1.pct_of_rwa ?? Number.NaN) - r.cet1_ratio_with_ppnr) < 1e-9);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: `${pick(o.scenario.title, 'en')}: the CET1 over RWA at the end of each year of the planning period, from the jump-off. The marked levels are the layers of the internal target OI, a target for the effective equity (PE) of which the CET1 is the common-equity part; a CET1 line above a layer does not by itself meet the OI, and the PE ratio and the headroom are in the table. The headline stress path is the loss-only depletion; the PPNR path is a labelled row.`,
          es: `${pick(o.scenario.title, 'es')}: el CET1 sobre APR al final de cada año del periodo de planificación, desde el punto de partida. Los niveles marcados son las capas del objetivo interno OI, un objetivo para el patrimonio efectivo (PE) del que el CET1 es la parte de capital común; una línea de CET1 sobre una capa no cumple por sí sola el OI, y la razón de PE y la holgura están en la tabla. La trayectoria principal del estrés es el agotamiento solo por pérdidas; la trayectoria con PPNR es una fila rotulada.`,
        }}
      >
        <ChartOverTable
          chartMin="19rem"
          chart={
            <UPlotChart
              height="fill"
              x={{ values: [0, 1, 2, 3], label: { en: 'Year of the projection (0 is the jump-off)', es: 'Año de la proyección (0 es el punto de partida)' }, format: { decimals: 0 } }}
              y={{ label: { en: 'CET1 over RWA', es: 'CET1 sobre APR' }, format: { percent: true, decimals: 1 } }}
              series={[
                ...plan.map((c) => ({
                  // with no mitigation to apply, the red and green lines are the same line: the key says so (U16-R2 b09 m2)
                  label: c.case === 'stress-with-mitigation' && !m.applies ? { en: 'Stress, with mitigation (identical: no mitigation applies)', es: 'Estrés con mitigación (idéntico: no se aplica mitigación)' } : text(PLAN_TEXT, c.case),
                  values: [start, ...[1, 2, 3].map((yr) => c.years.find((y) => y.year === yr)?.cet1.pct_of_rwa ?? null)],
                  color: PLAN_COLOR[c.case],
                  width: c.case === 'stress-without-mitigation' ? 3 : 2.2,
                })),
                {
                  // in the baseline variant the PPNR path is the Base line itself, drawn under it: the key says so (U16-R3 c19 m13)
                  label: ppnrIsBase
                    ? { en: 'Stress with the PPNR row (labelled row; identical to Base in this variant)', es: 'Estrés con la fila de PPNR (fila rotulada; idéntica a Base en esta variante)' }
                    : { en: 'Stress with the PPNR row (labelled row)', es: 'Estrés con la fila de PPNR (fila rotulada)' },
                  values: [start, ...[1, 2, 3].map((yr) => ppnr.rows.find((r) => r.year === yr)?.cet1_ratio_with_ppnr ?? null)],
                  color: '--color-warn',
                  width: 1.8,
                  dash: [2, 3],
                },
              ]}
              marks={[{ x: sel.year, label: { en: `Year ${sel.year}`, es: `Año ${sel.year}` } }]}
              yMarks={layers.map((l) => ({ y: l.y, label: l.label, tone: l.tone }))}
            />
          }
        >
          <p className="ct-note" data-layers="oi">
            {pick(
              {
                en: `The layers of the OI as a share of RWA: minimum ${PCT(t.min_pe, 'en')}, D-SIB ${PCT(t.c_dsib, 'en')}, Pillar 2 of the bank ${PCT(t.c_p2.value, 'en')} (case assumption), conservation ${PCT(t.c_ccob, 'en')}, countercyclical ${PCT(t.c_ccyb, 'en')}, stress buffer d ${PCT(t.c_d.value, 'en')} (case assumption); the OI is ${PCT(t.oi, 'en')}.`,
                es: `Las capas del OI como parte de los APR: mínimo ${PCT(t.min_pe, 'es')}, D-SIB ${PCT(t.c_dsib, 'es')}, Pilar 2 del banco ${PCT(t.c_p2.value, 'es')} (supuesto del caso), conservación ${PCT(t.c_ccob, 'es')}, contracíclico ${PCT(t.c_ccyb, 'es')}, colchón de estrés d ${PCT(t.c_d.value, 'es')} (supuesto del caso); el OI es ${PCT(t.oi, 'es')}.`,
              },
              lang,
            )}
          </p>
          <table className="caos-table ct-wrap-head" data-table="c18-plan">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Plan', es: 'Plan' }, lang)}</th>
                <th>{pick({ en: 'Year', es: 'Año' }, lang)}</th>
                <th>{pick({ en: 'CET1 / RWA', es: 'CET1 / APR' }, lang)}</th>
                <th>{pick({ en: 'PE / RWA', es: 'PE / APR' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Requirement', es: 'Exigencia' }, lang)}</th>
                <th>{pick({ en: 'Headroom', es: 'Holgura' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: `Deficit (${pick(MONEY_UNIT, 'en')})`, es: `Déficit (${pick(MONEY_UNIT, 'es')})` }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              <tr data-plan="start">
                <td className="ct-text">{pick({ en: 'Jump-off', es: 'Punto de partida' }, lang)}</td>
                <td>0</td>
                <td>{PCT(start, lang)}</td>
                <td>{PCT(o.capital_start.pe_ratio, lang)}</td>
                <td className="ct-text ct-wide-only">{formatNumber(null, lang)}</td>
                <td>{formatNumber(null, lang)}</td>
                <td className="ct-wide-only">{formatNumber(null, lang)}</td>
              </tr>
              {rowsOfPlan.map(({ c, y }) => (
                <tr key={`${c.case}-${y.year}`} data-plan={c.case} data-year={y.year} className={y.year === sel.year ? 'ct-current' : undefined}>
                  <td className="ct-text" title={pick(text(PLAN_LONG, c.case), lang)}>{pick(text(PLAN_TEXT, c.case), lang)}</td>
                  <td>{y.year}</td>
                  <td>{PCT(y.cet1.pct_of_rwa, lang)}</td>
                  <td>{PCT(y.pe.pct_of_rwa, lang)}</td>
                  <td className="ct-text ct-wide-only">{`${pick(text(REQUIREMENT_TEXT, y.requirement.basis), lang)} ${PCT(y.requirement.pct_of_rwa, lang, requirementDecimals(y.requirement.pct_of_rwa))}`}</td>
                  <td>{PCT(y.headroom_pct_of_rwa, lang)}</td>
                  <td className="ct-wide-only">{cell(y.deficit_clp_m, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3 className="ct-sub">{pick({ en: 'The headline: loss-only depletion', es: 'La cifra principal: agotamiento solo por pérdidas' }, lang)}</h3>
          <p className="ct-note">{pick(o.headline_cet1.statement, lang)}</p>
          <table className="caos-table ct-wrap-head" data-table="c18-headline" data-headline={o.headline_cet1.method}>
            <thead>
              <tr>
                <th>{pick({ en: 'Year', es: 'Año' }, lang)}</th>
                <th>{pick({ en: `CET1 at the start of the year (${pick(MONEY_UNIT, 'en')})`, es: `CET1 al inicio del año (${pick(MONEY_UNIT, 'es')})` }, lang)}</th>
                <th>{pick({ en: 'Loss in the year', es: 'Pérdida del año' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Cumulative loss', es: 'Pérdida acumulada' }, lang)}</th>
                <th>{pick({ en: 'CET1 at the end of the year', es: 'CET1 al final del año' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'RWA', es: 'APR' }, lang)}</th>
                <th>{pick({ en: 'CET1 / RWA', es: 'CET1 / APR' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.headline_cet1.rows.map((r) => (
                <tr key={r.year} data-year={r.year}>
                  <td>{r.year}</td>
                  <td>{cell(r.cet1_start_clp_m, lang)}</td>
                  {/* the year's own loss, so start less loss is the end of the row (U16-R3 c19 B1: the column read "at the jump-off" and printed the start of the year beside the cumulative loss) */}
                  <td>{cell(o.losses.scenario_losses.find((x) => x.year === r.year)?.total ?? null, lang)}</td>
                  <td className="ct-wide-only">{cell(r.cumulative_loss_clp_m, lang)}</td>
                  <td>{cell(r.cet1_clp_m, lang)}</td>
                  <td className="ct-wide-only">{cell(r.rwa_clp_m, lang)}</td>
                  <td>{PCT(r.cet1_ratio, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3 className="ct-sub">{`${pick({ en: 'The PPNR path', es: 'La trayectoria con PPNR' }, lang)} (${pick(text(LABEL_TEXT, ppnr.label), lang)})`}</h3>
          <p className="ct-note">
            {`${pick(ppnr.statement, lang)} ${pick({ en: 'Fee ratio', es: 'Razón de comisiones' }, lang)} ${PCT(ppnr.fee_ratio.value, lang)} (${pick(text(LABEL_TEXT, ppnr.fee_ratio.label), lang)}); ${pick({ en: 'cost ratio', es: 'razón de costos' }, lang)} ${PCT(ppnr.cost_ratio.value, lang)} (${pick(text(LABEL_TEXT, ppnr.cost_ratio.label), lang)}).`}
          </p>
          <table className="caos-table ct-wrap-head" data-table="c18-ppnr" data-ppnr="labelled-row">
            <thead>
              <tr>
                <th>{pick({ en: 'Year', es: 'Año' }, lang)}</th>
                <th>{pick({ en: 'NII', es: 'MFN' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Fee income', es: 'Comisiones' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Operating cost', es: 'Costo operativo' }, lang)}</th>
                <th>{pick({ en: 'PPNR', es: 'PPNR' }, lang)}</th>
                <th>{pick({ en: 'CET1 / RWA with PPNR', es: 'CET1 / APR con PPNR' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {ppnr.rows.map((r) => (
                <tr key={r.year} data-year={r.year}>
                  <td>{r.year}</td>
                  <td>{cell(r.nii_clp_m, lang)}</td>
                  <td className="ct-wide-only">{cell(r.fee_income_clp_m, lang)}</td>
                  <td className="ct-wide-only">{cell(r.operating_cost_clp_m, lang)}</td>
                  <td>{cell(r.ppnr_clp_m, lang)}</td>
                  <td>{PCT(r.cet1_ratio_with_ppnr, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3 className="ct-sub">{pick({ en: 'Mitigation', es: 'Mitigación' }, lang)}</h3>
          {m.applies ? (
            <table className="caos-table ct-wrap-head" data-table="c18-mitigation" data-mitigation="applies">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Action', es: 'Acción' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Status', es: 'Estado' }, lang)}</th>
                  <th>{pick({ en: 'CET1 effect, years 1 to 3', es: 'Efecto en CET1, años 1 a 3' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {m.actions.map((a) => (
                  <tr key={a.id} data-action={a.id}>
                    <td className="ct-text">{pick(a.description, lang)}</td>
                    <td className="ct-text">{pick(text(LABEL_TEXT, a.label), lang)}</td>
                    <td>{a.cet1_effect_clp_m.map((v) => cell(v, lang)).join(' / ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="ct-note" data-mitigation="none" data-na="true">{formatNumber(null, lang)}: <Marked>{m.reason ? pick(m.reason, lang) : ''}</Marked></p>
          )}
          {o.capital_plan.alternative_sources.length > 0 ? (
            <p className="ct-note">
              {o.capital_plan.alternative_sources.map((s) => `${s.source}, ${pick({ en: 'year', es: 'año' }, lang)} ${s.year}: ${cell(s.amount_clp_m, lang)}`).join('; ')}
            </p>
          ) : null}
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

const LAYER_TEXT: Record<string, BiText> = {
  min_pe: { en: 'Minimum PE', es: 'PE mínimo' },
  c_dsib: { en: 'D-SIB buffer', es: 'Colchón D-SIB' },
  c_p2: { en: 'Pillar 2 of the bank', es: 'Pilar 2 del banco' },
  c_ccob: { en: 'Conservation buffer', es: 'Colchón de conservación' },
  c_ccyb: { en: 'Countercyclical buffer', es: 'Colchón contracíclico' },
  c_d: { en: 'Stress buffer d', es: 'Colchón de estrés d' },
};
const LEGAL_TEXT: Record<string, BiText> = {
  cet1_min: { en: 'CET1 minimum', es: 'Mínimo CET1' },
  c_ccob: { en: 'Conservation buffer', es: 'Colchón de conservación' },
  c_ccyb: { en: 'Countercyclical buffer', es: 'Colchón contracíclico' },
  c_dsib: { en: 'D-SIB buffer', es: 'Colchón D-SIB' },
  p2r: { en: 'CET1 share of Pillar 2', es: 'Parte CET1 del Pilar 2' },
};
const REGULATORY: BiText = { en: 'regulatory', es: 'regulatorio' };

/** What the internal target is made of, how the effective equity ends against it, the legal minimum stack, and the P2G proxy. */
export function StackView({ sel }: { sel: C18Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The capital stack', es: 'El capital apilado' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SCENARIO} />;
  const t = o.internal_capital_target;
  const fit = fitOf(sel);
  const layerDefs: Array<{ id: keyof typeof LAYER_TEXT; size: number; label: string | null }> = [
    { id: 'min_pe', size: t.min_pe, label: null },
    { id: 'c_dsib', size: t.c_dsib, label: null },
    { id: 'c_p2', size: t.c_p2.value, label: t.c_p2.label },
    { id: 'c_ccob', size: t.c_ccob, label: null },
    { id: 'c_ccyb', size: t.c_ccyb, label: null },
    { id: 'c_d', size: t.c_d.value, label: t.c_d.label },
  ];
  const oiBars = stackBars(
    layerDefs.map((l) => ({ id: l.id, label: LAYER_TEXT[l.id], size: l.size, tone: l.label ? ('warn' as const) : ('accent' as const), ...(l.label ? { hint: text(LABEL_TEXT, l.label) } : {}) })),
    { id: 'oi', label: { en: 'Internal target OI', es: 'Objetivo interno OI' }, value: t.oi, tone: 'neutral' },
  );
  const stressNo = planOf(o, 'stress-without-mitigation');
  const stressWith = planOf(o, 'stress-with-mitigation');
  const y3 = (c: typeof stressNo) => c?.years.find((y) => y.year === 3) ?? null;
  const refs: Array<{ id: string; label: BiText; v: number | null }> = [
    { id: 'pe-start', label: { en: 'PE at the jump-off', es: 'PE en el punto de partida' }, v: o.capital_start.pe_ratio },
    { id: 'pe-no', label: { en: 'PE, year 3, no mitigation', es: 'PE, año 3, sin mitigación' }, v: y3(stressNo)?.pe.pct_of_rwa ?? null },
    { id: 'pe-with', label: { en: 'PE, year 3, with mitigation', es: 'PE, año 3, con mitigación' }, v: y3(stressWith)?.pe.pct_of_rwa ?? null },
    { id: 'legal', label: { en: 'Legal minimum PE', es: 'PE mínimo legal' }, v: stressNo?.years.find((y) => y.requirement.basis === 'legal-minimum')?.requirement.pct_of_rwa ?? null },
  ];
  const refBars = refs.flatMap((r) => (r.v === null ? [] : [{ id: r.id, label: r.label, value: r.v, span: [0, r.v] as [number, number], tone: 'good' as const }]));
  const legal = fit?.bank_anchors.chilean_stack ?? null;
  // the CET1 legal stack carries the CET1 share of Pillar 2 (reverse_p2_cet1), as the failure-point finding does; the whole P2R is the PE stack's
  const legalShare = (k: 'cet1_min' | 'c_ccob' | 'c_ccyb' | 'c_dsib' | 'p2r'): number => (legal ? (k === 'p2r' ? (fit?.named_parameters.reverse_p2_cet1.value ?? legal.p2r) : legal[k]) : 0);
  const legalBars = legal
    ? stackBars((['cet1_min', 'c_ccob', 'c_ccyb', 'c_dsib', 'p2r'] as const).map((k) => ({ id: k, label: LEGAL_TEXT[k], size: legalShare(k), tone: 'accent' as const })))
    : null;
  const rowsAll = oiBars.length + refBars.length;
  // a share keeps two decimals, and a third only where a figure needs it (9.125 %), as the table does
  // each bar states its share with the decimals the figure needs (2, or 3 such as P2R 9.125 %), as the table does (shell 0.19.0
  // BarDatum.format); the axis ticks keep one decimal
  const ownDecimals = <T extends { value: number | null | undefined }>(bars: T[]): T[] =>
    bars.map((b) => ({ ...b, format: { percent: true, decimals: requirementDecimals(b.value ?? 0) } }));
  const tickFormat = { percent: true, decimals: 1 };
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'The internal target OI is the sum of its layers, as a share of RWA; the bars below it are the effective equity at the jump-off and at the end of the stress, and the legal minimum. The second drawing is the legal minimum stack of the CET1 in Chile. Only the Chilean stack is drawn: the documents carry no figure for the EU or the SSM, so no comparison with them is made.',
          es: 'El objetivo interno OI es la suma de sus capas, como parte de los APR; las barras bajo él son el patrimonio efectivo en el punto de partida y al final del estrés, y el mínimo legal. El segundo dibujo es el mínimo legal apilado de CET1 en Chile. Solo se dibuja el capital apilado chileno: los documentos no traen cifras de la UE ni del SSM, así que no se hace comparación con ellas.',
        }}
      >
        {/* the two drawings take the whole card, each its share of the height by its bars, so neither is cut nor scrolls inside
            itself (R2b c19 M-new-1: under the tables the upper drawing lost its axis and the legal minimum bar) */}
            <div className="ct-c18-stack-charts" data-caos-flow="">
              <div style={{ flex: `${rowsAll + 2} 1 0`, minHeight: 0 }}>
                <BarChart
                  title={{ en: 'The layers of the internal target and the effective equity against it', es: 'Las capas del objetivo interno y el patrimonio efectivo frente a él' }}
                  data={ownDecimals([...oiBars, ...refBars])}
                  axis={{ label: { en: 'Share of RWA', es: 'Parte de los APR' }, format: tickFormat }}
                  height="fill"
                />
              </div>
              {legalBars ? (
                // the lower drawing keeps a floor for its ticks, its axis title and the read-out hint (U16-R3 c19 M1: the hint hid the title)
                <div data-box="legal-stack" style={{ flex: `${legalBars.length + 3} 1 0`, minHeight: '9rem' }}>
                  <BarChart
                    title={{ en: 'The legal minimum stack of the CET1 in Chile', es: 'El mínimo legal apilado de CET1 en Chile' }}
                    data={ownDecimals(legalBars)}
                    axis={{ label: { en: 'Share of RWA, legal stack', es: 'Parte de los APR, capital legal' }, format: tickFormat }}
                    height="fill"
                  />
                </div>
              ) : null}
            </div>
      </PlotCard>
      <PlotCard fill title={{ en: 'The stack in numbers', es: 'El capital apilado en números' }} {...card}>
        <div className="ct-scroll" data-caos-flow="" data-block="numbers">
          <table className="caos-table ct-wrap-head" data-table="c18-stack">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Layer of the OI', es: 'Capa del OI' }, lang)}</th>
                <th>{pick({ en: 'Share of RWA', es: 'Parte de los APR' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Status', es: 'Estado' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {layerDefs.map((l) => (
                <tr key={l.id} data-layer={l.id} data-label={l.label ?? 'regulatory'}>
                  <td className="ct-text">{pick(LAYER_TEXT[l.id], lang)}</td>
                  <td>{PCT(l.size, lang, 3)}</td>
                  <td className="ct-text">{l.label ? pick(text(LABEL_TEXT, l.label), lang) : pick(REGULATORY, lang)}</td>
                </tr>
              ))}
              <tr data-layer="oi">
                <td className="ct-text"><strong>{pick({ en: 'Internal target OI', es: 'Objetivo interno OI' }, lang)}</strong></td>
                <td>{PCT(t.oi, lang, 3)}</td>
                <td className="ct-text">{pick({ en: 'sum of the layers', es: 'suma de las capas' }, lang)}</td>
              </tr>
            </tbody>
          </table>
          <p className="ct-note">{phraseEs(t.formula, lang)}</p>
          <table className="caos-table ct-wrap-head" data-table="c18-stack-refs">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Effective equity and requirement', es: 'Patrimonio efectivo y exigencia' }, lang)}</th>
                <th>{pick({ en: 'Share of RWA', es: 'Parte de los APR' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {refs.map((r) => (
                <tr key={r.id} data-ref={r.id}>
                  <td className="ct-text">{pick(r.label, lang)}</td>
                  <td data-na={r.v === null ? 'true' : undefined}>{r.v === null ? formatNumber(null, lang) : PCT(r.v, lang, 3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {legal ? (
            <table className="caos-table ct-wrap-head" data-table="c18-legal-stack">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Legal minimum stack of the CET1', es: 'Mínimo legal apilado de CET1' }, lang)}</th>
                  <th>{pick({ en: 'Share of RWA', es: 'Parte de los APR' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {(['cet1_min', 'c_ccob', 'c_ccyb', 'c_dsib', 'p2r'] as const).map((k) => (
                  <tr key={k} data-legal-layer={k}>
                    <td className="ct-text">{pick(LEGAL_TEXT[k], lang)}</td>
                    <td>{PCT(legalShare(k), lang, k === 'p2r' ? 3 : 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="ct-note" data-na="true">{`${formatNumber(null, lang)}: ${pick({ en: 'the models artifact carries no legal stack', es: 'el artefacto de modelos no trae el capital apilado legal' }, lang)}`}</p>
          )}
          <h3 className="ct-sub">{pick({ en: 'The P2G proxy', es: 'La aproximación de P2G' }, lang)}</h3>
          <Defs data-table="c18-p2g" data-p2g={o.p2g_proxy.label}>
            <dt>{pick({ en: 'Status', es: 'Estado' }, lang)}</dt>
            <dd>{`${pick(text(LABEL_TEXT, o.p2g_proxy.label), lang)}. ${pick(P2G_LABEL, lang)}`}</dd>
            <dt>{pick({ en: 'Peak depletion of the CET1 ratio', es: 'Máxima caída de la razón de CET1' }, lang)}</dt>
            <dd>{`${PCT(o.p2g_proxy.peak_depletion, lang, 3)} (${pick({ en: 'year', es: 'año' }, lang)} ${o.p2g_proxy.peak_year})`}</dd>
            <dt>{pick({ en: 'Usable buffers and mitigation', es: 'Colchones usables y mitigación' }, lang)}</dt>
            <dd>{PCT(o.p2g_proxy.usable_buffers_and_mitigation, lang, 3)}</dd>
            <dt>{pick({ en: 'Proxy', es: 'Proxy' }, lang)}</dt>
            <dd>{PCT(o.p2g_proxy.value, lang, 3)}</dd>
            <dt>{pick({ en: 'Statement', es: 'Declaración' }, lang)}</dt>
            <dd>{pick(o.p2g_proxy.statement, lang)}</dd>
          </Defs>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

const COLUMN_TEXT: Record<string, BiText> = {
  c: { en: 'legal requirement', es: 'exigencia legal' },
  d: { en: 'internal measure', es: 'medición interna' },
};

function CellText({ c, kind, lang }: { c: C18Cell; kind: 'pct' | 'money'; lang: 'en' | 'es' }) {
  if (c.status === 'value' && c.value !== null) return <>{kind === 'pct' ? PCT(c.value, lang, 3) : cell(c.value, lang)}</>;
  return <span data-na="true" data-cell-status={c.status}>{pick(text(CELL_TEXT, c.status), lang)}</span>;
}

/** The summary table of Annex 3 of the IAPE as the CMF defines it: 34 rows, four columns, each cell a value or the reason it has none. */
export function Annex3View({ sel }: { sel: C18Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The summary table of Annex 3', es: 'El cuadro resumen del Anexo 3' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SCENARIO} />;
  const a = o.annex3;
  const rows = a.rows;
  const label = (r: (typeof rows)[number]) => (lang === 'es' ? ANNEX3_ES[r.row_id] ?? r.label_cmf : ANNEX3_EN[r.row_id] ?? r.label_cmf);
  const get = (id: string) => rows.find((r) => r.row_id === id);
  const bars = ['4.1.1', '4.1.2', '4.2', '4.3', '4.4.1', '4.4.2', '4.4.3', '4.5', '4.6', '4.7', '4.8'].flatMap((id) => {
    const r = get(id);
    if (!r) return [];
    const col = (['c', 'd'] as const).find((k) => r[k].status === 'value');
    if (!col) return [];
    return [{ r, col }];
  });
  const scale = axisOf(bars.flatMap(({ r, col }) => (r[col].status === 'value' ? [r[col].value] : [])));
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: `${a.entity}, ${a.report_date}, consolidation ${a.consolidation === 'local' ? 'local' : 'global consolidated'}. Column A is a share of RWA at the start, B the amount in ${pick(MONEY_UNIT, 'en')}, C the legal requirement of each risk and D the internal measurement; RI marks a risk the bank treats as immaterial and does not quantify. The bars show the capital needed by risk where a cell has a value; the cells without one are in the table with their reason.`,
          es: `${a.entity}, ${a.report_date}, consolidación ${a.consolidation === 'local' ? 'local' : 'global consolidada'}. La columna A es una parte de los APR al inicio, B el monto en ${pick(MONEY_UNIT, 'es')}, C la exigencia legal de cada riesgo y D la medición interna; RI marca un riesgo que el banco trata como inmaterial y no cuantifica. Las barras muestran el capital necesario por riesgo donde una celda tiene valor; las celdas sin él están en la tabla con su razón.`,
        }}
      >
        <ChartOverTable
          chartMin={`${bars.length * 2.2 + 3}rem`}
          chart={
            <BarChart
              title={{ en: 'Capital needed by risk, legal requirement and internal measure', es: 'Capital necesario por riesgo, exigencia legal y medición interna' }}
              height="fill"
              orientation="horizontal"
              data={bars.map(({ r, col }) => ({
                id: `${r.row_id}-${col}`,
                label: { en: `${ANNEX3_EN[r.row_id] ?? r.label_cmf}, ${pick(COLUMN_TEXT[col], 'en')}`, es: `${ANNEX3_ES[r.row_id] ?? r.label_cmf}, ${pick(COLUMN_TEXT[col], 'es')}` },
                value: r[col].status === 'value' && r[col].value !== null ? r[col].value / scale.div : null,
                tone: col === 'c' ? ('accent' as const) : ('warn' as const),
                hint: text(CELL_TEXT, r[col].status),
              }))}
              axis={{ label: { en: 'Capital needed by risk', es: 'Capital necesario por riesgo' }, unit: scale.unit, format: { digits: 4 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c18-annex3">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Row', es: 'Fila' }, lang)}</th>
                <th>{pick({ en: 'A: share of RWA', es: 'A: parte de los APR' }, lang)}</th>
                <th>{pick({ en: `B: amount (${pick(MONEY_UNIT, 'en')})`, es: `B: monto (${pick(MONEY_UNIT, 'es')})` }, lang)}</th>
                <th>{pick({ en: 'C: legal requirement', es: 'C: exigencia legal' }, lang)}</th>
                <th>{pick({ en: 'D: internal measure', es: 'D: medición interna' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.row_id} data-annex-row={r.row_id}>
                  <td className="ct-text" title={r.label_cmf}><span translate="no">{r.row_id}</span> <Marked>{label(r)}</Marked></td>
                  <td><CellText c={r.a} kind="pct" lang={lang} /></td>
                  <td><CellText c={r.b} kind="money" lang={lang} /></td>
                  <td><CellText c={r.c} kind="money" lang={lang} /></td>
                  <td><CellText c={r.d} kind="money" lang={lang} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ct-note">
            <MaybeNumber value={get('12')?.a.value ?? null} reason={null} format={(v) => `${pick({ en: 'Headroom of the effective equity ratio over the OI', es: 'Holgura de la razón de patrimonio efectivo sobre el OI' }, lang)}: ${PCT(v, lang, 3)}`} />
          </p>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
