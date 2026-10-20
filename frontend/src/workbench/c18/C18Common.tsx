// C18's tests, Findings, Variants and Context groups, and the live read-outs of its rail (ADR-0017 rule 3: every section shows
// a value that moves with its controls). The Findings card and the fixture notice are the ones C06 and C07 use. What every
// view says, whatever the variant: the headline capital is the simple sum and every diversified or bound figure is
// information for the validator, never capital; the paths and the satellites are US-calibrated adaptations transposed onto
// the synthetic Banco Andino; the P2G proxy is a Contraste approximation; every named parameter is a convention or a case
// assumption. Money is CLP millions as the documents give it; a rail read-out scales it to bn with the unit that says so.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { loadAllVariants, useArtifact } from '../../api/artifacts';
import type { TestRow, VariantArtifact } from '../../lib/contract.types';
import { LIGHT_TEXT } from '../../lib/policy';
import { FindingsCard, FixtureNotice } from '../c06/C06Common';
import { ChartOverTable, MaybeNumber } from '../c06/format';
import { Pending } from '../Pending';
import { LiveReadout, useCard, type Bi } from '../c03/U6Shared';
import { UnavailableCard } from '../c14/C14Common';
import {
  CLASS_TEXT, LABEL_TEXT, LINK_TEXT, LOAN_TEXT, MONEY_UNIT, PLAN_ORDER, PLAN_TEXT, PROVIDER_TEXT, REGRESSOR_TEXT, RISK_TEXT, TEST_TEXT, US_ADAPTATION,
  aggDocOf, aggOf, amount, backcastOf, fitOf, marginalOf, outputsOf, planOf, reverseOf, text, yearOf, methodShort, methodText,
  type C18AggOutputs, type C18Fit, type C18Outputs, type C18Reverse, type C18Sel,
} from './selection';

type Lang = 'en' | 'es';
const NA: BiText = { en: formatNumber(null, 'en'), es: formatNumber(null, 'es') };
export const PCT = (v: number | null | undefined, lang: Lang, decimals = 2) => formatNumber(v, lang, { percent: true, decimals });
export const cell = (v: number | null | undefined, lang: Lang) => formatNumber(v, lang, { decimals: 0 });
export const digits = (v: number | null | undefined, lang: Lang) => formatNumber(v, lang, { digits: 4 });
const RATIO_FORMAT = { percent: true, decimals: 2 } as const;

/** The words an absent block says when the view is given a document of another kind. */
export const NOT_SCENARIO: BiText = { en: 'Not available: this document is not a scenario variant, so it has no capital plan, satellites or back-cast.', es: 'No disponible: este documento no es una variante de escenario, así que no tiene plan de capital, satélites ni back-cast.' };
export const NOT_AGGREGATION: BiText = { en: 'Not available: this document carries no aggregation block.', es: 'No disponible: este documento no trae un bloque de agregación.' };
export const NOT_AGG_VARIANT: BiText = { en: 'Not available: this view reads the t-copula aggregation variant, which holds the stressed matrix, the copula sensitivity and the reference.', es: 'No disponible: esta vista lee la variante de agregación con cópula t, que trae la matriz bajo estrés, la sensibilidad a la cópula y la referencia.' };
export const NOT_REVERSE: BiText = { en: 'Not available: this document is not the reverse-stress variant.', es: 'No disponible: este documento no es la variante de estrés inverso.' };

// --- the tests table -------------------------------------------------------------------------------------------------

/** The rows the engine returned for the tests of this variant; a test that did not run shows its reason, not a number. */
export function C18TestsView({ sel }: { sel: C18Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  if (!sel) return <Pending />;
  const rows: TestRow[] = sel.data.variant.tests;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The tests of the aggregation and the stress', es: 'Las pruebas de la agregación y del estrés' }}
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
                  <th>{pick({ en: 'Statistic', es: 'Estadístico' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Light', es: 'Luz' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Reason or note', es: 'Razón o nota' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((t, i) => {
                  const ran = t.light !== 'not_evaluated' && t.light !== 'error';
                  return (
                    <tr key={`${t.test_id}-${i}`} data-test={t.test_id} data-light={t.light}>
                      <td className="ct-text" title={t.test_id}>{TEST_TEXT[t.test_id] ? pick(TEST_TEXT[t.test_id], lang) : t.test_id}</td>
                      <td data-na={ran && t.statistic !== null ? undefined : 'true'}>{ran && t.statistic !== null ? formatNumber(t.statistic, lang, { digits: 4 }) : formatNumber(null, lang)}</td>
                      <td className={`ct-text ct-light ct-light-${t.light}`}>
                        <span className="ct-light-word">{pick(LIGHT_TEXT[t.light], lang)}</span>
                      </td>
                      <td className="ct-text">{t.notes ?? t.reference}</td>
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

export function C18FindingsView({ sel }: { sel: C18Sel | null }) {
  if (!sel) return <Pending />;
  return (
    <ViewsRow>
      <FindingsCard variant={sel.data.variant} />
    </ViewsRow>
  );
}

// --- the variants ------------------------------------------------------------------------------------------------------

type Entry = { id: string; title: BiText; v: VariantArtifact<C18Outputs> };

/** One row per variant of the case with the measures that answer the validator's question: the headline capital, the CET1 at the end of the stress, the headroom over the target and the P2G proxy. */
export function C18VariantsTable({ variants, aggregation, reverse, onPick, current }: { variants: Entry[]; aggregation: VariantArtifact<C18AggOutputs> | null; reverse: VariantArtifact<C18Reverse> | null; onPick: (id: string) => void; current: string }) {
  const lang = useShellLang();
  const first = variants[0]?.v ?? aggregation ?? reverse;
  const card = useCard(first as unknown as VariantArtifact | undefined);
  const bars = variants.map(({ id, title, v }) => ({ id, label: title, value: v.impact.cet1_ratio_end_stress.value, tone: 'accent' as const, highlight: id === current }));
  const nope: BiText = { en: 'this variant does not compute it', es: 'esta variante no lo calcula' };
  const maybe = (v: number | null, f: (x: number) => string, reason: BiText | null) => <MaybeNumber value={v} reason={reason ? pick(reason, lang) : null} format={f} />;
  return (
    <PlotCard
      fill
      title={{ en: 'The variants of the case', es: 'Las variantes del caso' }}
      {...card}
      note={{
        en: 'The scenario variants run the same bank under the Federal Reserve, EBA and ESRB, and NGFS paths; the bars give the CET1 over RWA at the end of the third year under the stress without mitigation. The aggregation and reverse-stress variants have their own measures. Pick a variant to load it.',
        es: 'Las variantes de escenario corren el mismo banco bajo las trayectorias de la Reserva Federal, de la EBA y la ESRB, y de NGFS; las barras dan el CET1 sobre APR al final del tercer año bajo el estrés sin mitigación. Las variantes de agregación y de estrés inverso tienen sus propias medidas. Elija una variante para cargarla.',
      }}
    >
      <ChartOverTable
        chartMin={`${Math.max(variants.length, 2) * 2 + 3}rem`}
        chart={
          <BarChart
            title={{ en: 'CET1 over RWA at the end of year 3, stress without mitigation', es: 'CET1 sobre APR al final del año 3, estrés sin mitigación' }}
            height="fill"
            orientation="horizontal"
            data={bars}
            axis={{ label: { en: 'CET1 over RWA at the end of the third year', es: 'CET1 sobre APR al final del tercer año' }, format: { percent: true, decimals: 1 } }}
          />
        }
      >
        <table className="caos-table ct-wrap-head" data-table="variants-c18">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Variant', es: 'Variante' }, lang)}</th>
              <th>{pick({ en: 'Headline capital (CLP millions)', es: 'Capital principal (millones de CLP)' }, lang)}</th>
              <th>{pick({ en: 'CET1, end of stress', es: 'CET1, fin del estrés' }, lang)}</th>
              <th className="ct-wide-only">{pick({ en: 'Smallest headroom over the OI', es: 'Holgura mínima sobre el OI' }, lang)}</th>
              <th className="ct-wide-only">{pick({ en: 'P2G proxy (Contraste approximation)', es: 'Proxy de P2G (aproximación de Contraste)' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {variants.map(({ id, title, v }) => (
              <tr key={id} data-variant={id} className={id === current ? 'ct-current' : undefined}>
                <td className="ct-text">
                  <button type="button" className="ct-linkbutton" onClick={() => onPick(id)}>{pick(title, lang)}</button>
                </td>
                <td>{cell(v.outputs.aggregation.headline.capital_clp_m, lang)}</td>
                <td>{PCT(v.impact.cet1_ratio_end_stress.value, lang)}</td>
                <td className="ct-wide-only">{PCT(v.impact.oi_headroom_min.value, lang)}</td>
                <td className="ct-wide-only">{PCT(v.impact.p2g_proxy.value, lang)}</td>
              </tr>
            ))}
            {aggregation ? (
              <tr data-variant={aggregation.variant_id} className={aggregation.variant_id === current ? 'ct-current' : undefined}>
                <td className="ct-text">
                  <button type="button" className="ct-linkbutton" onClick={() => onPick(aggregation.variant_id)}>{pick({ en: 'Student t copula aggregation', es: 'Agregación con cópula t de Student' }, lang)}</button>
                </td>
                <td>{cell(aggregation.outputs.aggregation.headline.capital_clp_m, lang)}</td>
                <td data-na="true">{maybe(null, (x) => PCT(x, lang), nope)}</td>
                <td className="ct-wide-only" data-na="true">{maybe(null, (x) => PCT(x, lang), null)}</td>
                <td className="ct-wide-only" data-na="true">{maybe(null, (x) => PCT(x, lang), null)}</td>
              </tr>
            ) : null}
            {reverse ? (
              <tr data-variant={reverse.variant_id} className={reverse.variant_id === current ? 'ct-current' : undefined}>
                <td className="ct-text">
                  <button type="button" className="ct-linkbutton" onClick={() => onPick(reverse.variant_id)}>{pick({ en: 'Reverse stress', es: 'Estrés inverso' }, lang)}</button>
                </td>
                <td data-na="true">{maybe(null, (x) => cell(x, lang), nope)}</td>
                <td>{PCT(reverse.outputs.failure_point.stack.total, lang, 3)}</td>
                <td className="ct-wide-only" data-na="true">{maybe(null, (x) => PCT(x, lang), null)}</td>
                <td className="ct-wide-only" data-na="true">{maybe(null, (x) => PCT(x, lang), null)}</td>
              </tr>
            ) : null}
          </tbody>
        </table>
        {reverse ? (
          <p className="ct-note">
            {pick({ en: 'For the reverse stress the CET1 column is the failure point: the legal minimum stack that the solved scenario takes the CET1 to.', es: 'En el estrés inverso la columna CET1 es el punto de falla: el mínimo legal apilado al que el escenario resuelto lleva el CET1.' }, lang)}
          </p>
        ) : null}
      </ChartOverTable>
    </PlotCard>
  );
}

export function C18VariantsView({ sel, onPick }: { sel: C18Sel | null; onPick: (id: string) => void }) {
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  if (!sel || all.state !== 'ready') return <Pending />;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const docs = all.data as unknown as Array<VariantArtifact<C18Outputs | C18AggOutputs | C18Reverse>>;
  const scenarios: Entry[] = docs
    .filter((v) => v.outputs.kind === 'scenario')
    .map((v) => ({ id: v.variant_id, title: entries.find((e) => e.variant_id === v.variant_id)?.short_title ?? (v.outputs as C18Outputs).scenario.title, v: v as VariantArtifact<C18Outputs> }));
  const aggregation = (docs.find((v) => v.outputs.kind === 'aggregation') as VariantArtifact<C18AggOutputs> | undefined) ?? null;
  const reverse = (docs.find((v) => v.outputs.kind === 'reverse') as VariantArtifact<C18Reverse> | undefined) ?? null;
  return (
    <ViewsRow>
      <C18VariantsTable variants={scenarios} aggregation={aggregation} reverse={reverse} onPick={onPick} current={sel.data.variant.variant_id} />
    </ViewsRow>
  );
}

// --- the context ------------------------------------------------------------------------------------------------------

const CAPITAL_BASIS_TEXT: Record<string, Bi> = {
  'economic-capital-var-less-el': { en: 'economic capital, VaR less expected loss', es: 'capital económico, VaR menos pérdida esperada' },
};
const PRODUCER_TEXT: Record<string, Bi> = {
  'credit-grouped-copula-c07-segments': { en: 'The grouped copula of the engine on the C07 segments of Banco Andino', es: 'La cópula agrupada del motor sobre los segmentos C07 de Banco Andino' },
  'market-c11-mixed-portfolio-scaled-to-market-rwa': { en: 'The mixed-portfolio VaR and ES of C11, scaled to the market share of the RWA', es: 'El VaR y ES de la cartera mixta de C11, escalados a la parte de mercado de los APR' },
  'irrbb-engine-simulation-c15-curve-and-book': { en: 'The IRRBB simulation of the engine on the curve and book of C15', es: 'La simulación IRRBB del motor sobre la curva y el libro de C15' },
  'operational-oprisk-aggregate-c17-parameters-scaled': { en: 'The operational aggregate of the engine from the C17 parameters, scaled to Banco Andino', es: 'El agregado operacional del motor con los parámetros de C17, escalado a Banco Andino' },
};
export const producerText = (id: string): Bi => PRODUCER_TEXT[id] ?? { en: id, es: id };
const PARAM_TEXT: Record<string, Bi> = {
  nu_set: { en: 'Degrees of freedom of the t copula', es: 'Grados de libertad de la cópula t' },
  correlation_matrix_base: { en: 'Inter-risk correlation, base', es: 'Correlación entre riesgos, base' },
  correlation_matrix_stress: { en: 'Inter-risk correlation, market-credit stress', es: 'Correlación entre riesgos, estrés mercado-crédito' },
  ppnr_fee_ratio: { en: 'PPNR: fee income over NII', es: 'PPNR: comisiones sobre MFN' },
  ppnr_cost_ratio: { en: 'PPNR: cost over income', es: 'PPNR: costos sobre ingresos' },
  c_p2: { en: 'Pillar 2 of the bank (c_P2)', es: 'Pilar 2 del banco (c_P2)' },
  c_d: { en: 'Stress buffer of the OI (c_d)', es: 'Colchón de estrés del OI (c_d)' },
  operational_conversion_rate: { en: 'Conversion rate of the operational marginal', es: 'Tipo de cambio de la marginal operacional' },
  asset_scaling: { en: 'Asset scaling of the operational marginal', es: 'Escala de activos de la marginal operacional' },
  market_rwa_share: { en: 'Market share of the RWA', es: 'Parte de mercado de los APR' },
  market_horizon_scaling: { en: 'Market scaling to 99.9 percent and one year', es: 'Escala de mercado a 99,9 por ciento y un año' },
  reverse_p2_cet1: { en: 'CET1 share of Pillar 2 in the legal stack', es: 'Parte CET1 del Pilar 2 en el mínimo legal' },
};

function Fixture({ sel }: { sel: C18Sel }) {
  return <FixtureNotice variant={sel.data.variant} />;
}

function NamedRows({ fit }: { fit: C18Fit }) {
  const lang = useShellLang();
  const p = fit.named_parameters;
  const rows: Array<{ id: string; value: string; label: string; basis: BiText }> = [
    { id: 'nu_set', value: p.nu_set.values.map((v) => formatNumber(v, lang, { digits: 4 })).join(', '), label: p.nu_set.label, basis: p.nu_set.basis },
    ...(['correlation_matrix_base', 'correlation_matrix_stress'] as const).map((k) => ({ id: k, value: p[k].matrix.map((r) => r.map((v) => formatNumber(v, lang, { digits: 4 })).join(' / ')).join('; '), label: p[k].label, basis: p[k].basis })),
    { id: 'ppnr_fee_ratio', value: PCT(p.ppnr_fee_ratio.value, lang), label: p.ppnr_fee_ratio.label, basis: p.ppnr_fee_ratio.basis },
    { id: 'ppnr_cost_ratio', value: PCT(p.ppnr_cost_ratio.value, lang), label: p.ppnr_cost_ratio.label, basis: p.ppnr_cost_ratio.basis },
    { id: 'c_p2', value: PCT(p.c_p2.value, lang), label: p.c_p2.label, basis: p.c_p2.basis },
    { id: 'c_d', value: PCT(p.c_d.value, lang), label: p.c_d.label, basis: p.c_d.basis },
    { id: 'operational_conversion_rate', value: `${formatNumber(p.operational_conversion_rate.value, lang, { digits: 5 })} ${p.operational_conversion_rate.unit}`, label: p.operational_conversion_rate.label, basis: p.operational_conversion_rate.basis },
    { id: 'asset_scaling', value: formatNumber(p.asset_scaling.value, lang, { digits: 4 }), label: p.asset_scaling.label, basis: p.asset_scaling.basis },
    { id: 'market_rwa_share', value: PCT(p.market_rwa_share.value, lang), label: p.market_rwa_share.label, basis: p.market_rwa_share.basis },
    { id: 'market_horizon_scaling', value: formatNumber(p.market_horizon_scaling.value, lang, { digits: 5 }), label: p.market_horizon_scaling.label, basis: p.market_horizon_scaling.basis },
    { id: 'reverse_p2_cet1', value: PCT(p.reverse_p2_cet1.value, lang, 3), label: p.reverse_p2_cet1.label, basis: p.reverse_p2_cet1.basis },
  ];
  return (
    <tbody>
      {rows.map((r) => (
        <tr key={r.id} data-param={r.id} data-status={r.label}>
          <td className="ct-text" title={r.id}>{pick(PARAM_TEXT[r.id], lang)}</td>
          <td className="ct-text">{r.value}</td>
          <td className="ct-text">{pick(text(LABEL_TEXT, r.label), lang)}</td>
          <td className="ct-text ct-wide-only">{pick(r.basis, lang)}</td>
        </tr>
      ))}
    </tbody>
  );
}

function ModelBlocks({ fit, card }: { fit: C18Fit; card: ReturnType<typeof useCard> }) {
  const lang = useShellLang();
  const a = fit.bank_anchors;
  return (
    <>
      <PlotCard title={{ en: 'The named parameters', es: 'Los parámetros con nombre' }} {...card} note={{ en: 'Every parameter of the case is a convention or a case assumption, labelled as one with the basis of its proposed value; none is a regulatory figure. The value is the document\'s, not a calibration to Banco Andino.', es: 'Cada parámetro del caso es una convención o un supuesto del caso, rotulado como tal con la base de su valor propuesto; ninguno es una cifra regulatoria. El valor es el del documento, no una calibración a Banco Andino.' }}>
        <div className="ct-scroll">
          <table className="caos-table ct-wrap-head" data-table="c18-parameters">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Parameter', es: 'Parámetro' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Value', es: 'Valor' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Status', es: 'Estado' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Basis', es: 'Base' }, lang)}</th>
              </tr>
            </thead>
            <NamedRows fit={fit} />
          </table>
        </div>
      </PlotCard>
      <PlotCard title={{ en: 'The satellites fitted before 2020', es: 'Los satélites ajustados antes de 2020' }} {...card} note={{ en: 'One regression per Federal Reserve loan type on the charge-off rate, fitted on data that ends before the episode it is back-cast through. They are a US-calibrated adaptation, not Chilean satellites.', es: 'Una regresión por tipo de préstamo de la Reserva Federal sobre la tasa de castigo, ajustada con datos que terminan antes del episodio que se retro-proyecta. Son una adaptación calibrada en EE. UU., no satélites chilenos.' }}>
        <div className="ct-scroll">
          <table className="caos-table ct-wrap-head" data-table="c18-satellites-fit">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Loan type', es: 'Tipo de préstamo' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Link', es: 'Enlace' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Window', es: 'Ventana' }, lang)}</th>
                <th>{pick({ en: 'Quarters', es: 'Trimestres' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Non-positive quarters', es: 'Trimestres no positivos' }, lang)}</th>
                <th>{pick({ en: 'R squared', es: 'R cuadrado' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {fit.satellites.map((s) => (
                <tr key={s.model_id} data-loan={s.fed_loan_type} data-fit-start={s.sample_window.start}>
                  <td className="ct-text">{pick(text(LOAN_TEXT, s.fed_loan_type), lang)}</td>
                  <td className="ct-text">{pick(text(LINK_TEXT, s.link), lang)}</td>
                  <td className="ct-text">{`${s.sample_window.start} ${pick({ en: 'to', es: 'a' }, lang)} ${s.sample_window.end}`}</td>
                  <td>{s.n_obs}</td>
                  <td className="ct-wide-only">{s.non_positive_quarters_in_window ?? formatNumber(null, lang)}</td>
                  <td>{digits(s.fit_statistics.r_squared, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
      <PlotCard title={{ en: 'The bank anchors and the scenario sources', es: 'Los anclajes del banco y las fuentes de escenarios' }} {...card} note={{ en: 'Only ratios computed from the Banco Santander-Chile Form 20-F 2025 enter the documents, with the filing cited; the amounts of Banco Andino are scaled from them.', es: 'Solo entran a los documentos razones calculadas del Formulario 20-F 2025 de Banco Santander-Chile, con la presentación citada; los montos de Banco Andino se escalan desde ellas.' }}>
        <div className="ct-scroll">
          <dl className="ct-defs" data-table="c18-anchors">
            <dt>{pick({ en: 'Anchor of the RWA', es: 'Anclaje de los APR' }, lang)}</dt>
            <dd>{`${pick({ en: 'Tier 1 proxy', es: 'Proxy de Tier 1' }, lang)} ${cell(a.rwa_basis.tier1_proxy_clp_m, lang)} ${pick(MONEY_UNIT, lang)}; ${pick({ en: 'CET1 anchor', es: 'ancla CET1' }, lang)} ${PCT(a.rwa_basis.cet1_ratio_anchor, lang)}; ${pick({ en: 'RWA', es: 'APR' }, lang)} ${cell(a.rwa_basis.rwa_total_clp_m, lang)}`}</dd>
            <dt>{pick({ en: 'Mix of the RWA', es: 'Mezcla de los APR' }, lang)}</dt>
            <dd>{`${pick(RISK_TEXT.credit, lang)} ${PCT(a.rwa_mix.credit, lang)}; ${pick(RISK_TEXT.market, lang)} ${PCT(a.rwa_mix.market, lang)}; ${pick(RISK_TEXT.operational, lang)} ${PCT(a.rwa_mix.operational, lang)}`}</dd>
            <dt>{pick({ en: 'Chilean capital stack', es: 'Capital apilado chileno' }, lang)}</dt>
            <dd>{`CET1 ${PCT(a.chilean_stack.cet1_min, lang)}; ${pick({ en: 'conservation', es: 'conservación' }, lang)} ${PCT(a.chilean_stack.c_ccob, lang)}; ${pick({ en: 'countercyclical', es: 'contracíclico' }, lang)} ${PCT(a.chilean_stack.c_ccyb, lang)}; D-SIB ${PCT(a.chilean_stack.c_dsib, lang)}; P2R ${PCT(a.chilean_stack.p2r, lang, 3)} (${pick({ en: 'cap', es: 'tope' }, lang)} ${PCT(a.chilean_stack.p2_cap, lang)})`}</dd>
            <dt>{pick({ en: 'Loan exposures', es: 'Exposiciones de préstamos' }, lang)}</dt>
            <dd>{a.loan_exposures.map((e) => `${pick(text(CLASS_TEXT, e.banco_andino_class), lang)} ${PCT(e.share, lang)}`).join('; ')}</dd>
            <dt>{pick({ en: 'Source of the anchors', es: 'Fuente de los anclajes' }, lang)}</dt>
            <dd data-licence-class={a.licence_class}>{pick(a.source, lang)}</dd>
          </dl>
          <table className="caos-table ct-wrap-head" data-table="c18-scenario-sources">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Scenario', es: 'Escenario' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Provider', es: 'Proveedor' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Vintage', es: 'Versión' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Licence class', es: 'Clase de licencia' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Document', es: 'Documento' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {fit.scenario_sources.map((s) => (
                <tr key={s.scenario_id} data-scenario={s.scenario_id}>
                  <td className="ct-text">{s.scenario_id}</td>
                  <td className="ct-text">{pick(text(PROVIDER_TEXT, s.provider), lang)}</td>
                  <td className="ct-text">{s.vintage_date}</td>
                  <td className="ct-text">{s.licence_class === 'derived-only' ? pick({ en: 'derived only', es: 'solo derivado' }, lang) : pick({ en: 'mirror allowed', es: 'espejo permitido' }, lang)}</td>
                  <td className="ct-text ct-wide-only">{s.document}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head" data-table="c18-marginal-sources">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Marginal', es: 'Marginal' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'How it is produced', es: 'Cómo se produce' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {fit.marginal_sources.map((m) => (
                <tr key={m.risk} data-risk={m.risk}>
                  <td className="ct-text">{pick(text(RISK_TEXT, m.risk), lang)}</td>
                  <td className="ct-text">{pick(m.description, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <dl className="ct-defs" data-table="c18-aggregation-parameters">
            <dt>{pick({ en: 'Draws, seed and chunk', es: 'Sorteos, semilla y bloque' }, lang)}</dt>
            <dd>{`${cell(fit.aggregation.n_draws, lang)}; ${fit.aggregation.seed}; ${cell(fit.aggregation.chunk_size, lang)}`}</dd>
            <dt>{pick({ en: 'Rule that maps a draw through a marginal', es: 'Regla que lleva un sorteo por una marginal' }, lang)}</dt>
            <dd>{fit.aggregation.marginal_interpolation}</dd>
            <dt>{pick({ en: 'Static balance sheet rules (EBA 2025 note)', es: 'Reglas de balance estático (nota EBA 2025)' }, lang)}</dt>
            <dd>{fit.capital_engine.rules.map((r) => `${pick({ en: 'paragraph', es: 'párrafo' }, lang)} ${r.paragraph}`).join('; ')}</dd>
          </dl>
        </div>
      </PlotCard>
    </>
  );
}

/** The case, the bank with its labels, the capital start and the basis of every capital figure, and the models artifact. */
export function C18ContextView({ sel }: { sel: C18Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const a = aggDocOf(sel);
  const r = reverseOf(sel);
  const base = o ?? a ?? r;
  if (!sel || !base) return <Pending />;
  const m = sel.data.manifest;
  const agg = aggOf(sel);
  const fit = fitOf(sel);
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case', es: 'El caso' }} {...card}>
        <Fixture sel={sel} />
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <dl className="ct-defs" data-table="c18-bank">
          <dt>{pick({ en: 'Bank', es: 'Banco' }, lang)}</dt>
          <dd data-synthetic={String(base.bank.synthetic)}>{base.bank.name}</dd>
          <dt>{pick({ en: 'What is real and what is synthetic', es: 'Qué es real y qué es sintético' }, lang)}</dt>
          <dd>{pick({ en: 'The scenario paths are real publications; the bank, its book and its capital are synthetic, calibrated to the aggregates the CMF publishes and to ratios of one filing.', es: 'Las trayectorias de escenario son publicaciones reales; el banco, su libro y su capital son sintéticos, calibrados a los agregados que publica la CMF y a razones de una presentación.' }, lang)}</dd>
          <dt>{pick({ en: 'Notice of the document', es: 'Aviso del documento' }, lang)}</dt>
          <dd>{pick(base.bank.notice, lang)}</dd>
          <dt>{pick({ en: 'The capital of this case', es: 'El capital de este caso' }, lang)}</dt>
          <dd data-headline="simple-sum">{pick({ en: 'The headline capital is the simple sum of the capital of the four risks, as the IAPE adds them. Every diversified or bound figure is information for the validator, never capital.', es: 'El capital principal es la suma simple del capital de los cuatro riesgos, como los suma el IAPE. Toda cifra diversificada o acotada es información para el validador, nunca capital.' }, lang)}</dd>
          <dt>{pick({ en: 'Capital basis of a risk', es: 'Base del capital de un riesgo' }, lang)}</dt>
          <dd data-capital-basis={agg?.capital_basis}>{agg ? pick(text(CAPITAL_BASIS_TEXT, agg.capital_basis), lang) : formatNumber(null, lang)}</dd>
          <dt>{pick({ en: 'Horizon and confidence level', es: 'Horizonte y nivel de confianza' }, lang)}</dt>
          <dd>{agg ? `${agg.horizon_years} ${pick({ en: 'year', es: 'año' }, lang)}; ${PCT(agg.confidence_level, lang, 1)}` : formatNumber(null, lang)}</dd>
          <dt>{pick({ en: 'Money', es: 'Dinero' }, lang)}</dt>
          <dd>{`${pick(MONEY_UNIT, lang)}; ${base.units.ratio}`}</dd>
          <dt>{pick({ en: 'Date of the bank', es: 'Fecha del banco' }, lang)}</dt>
          <dd>{base.bank.as_of}</dd>
          {o ? (
            <>
              <dt>{pick({ en: 'Scenario', es: 'Escenario' }, lang)}</dt>
              <dd data-scenario={o.scenario.scenario_id}>{`${pick(o.scenario.title, lang)}; ${pick(text(PROVIDER_TEXT, o.scenario.provider), lang)}; ${o.scenario.vintage_date}`}</dd>
              <dt>{pick({ en: 'Adaptation', es: 'Adaptación' }, lang)}</dt>
              <dd data-adaptation={o.scenario.adaptation_label}>{`${pick(text(LABEL_TEXT, o.scenario.adaptation_label), lang)}. ${pick(US_ADAPTATION, lang)}`}</dd>
              <dt>{pick({ en: 'Source of the path', es: 'Fuente de la trayectoria' }, lang)}</dt>
              <dd>{`${o.scenario.source_document} (${o.scenario.source_url})`}</dd>
              <dt>{pick({ en: 'Capital at the jump-off', es: 'Capital en el punto de partida' }, lang)}</dt>
              <dd>{`CET1 ${PCT(o.capital_start.cet1_ratio, lang)}; PE ${PCT(o.capital_start.pe_ratio, lang)}; ${pick({ en: 'RWA', es: 'APR' }, lang)} ${cell(o.capital_start.rwa_clp_m, lang)}. ${pick(o.capital_start.basis, lang)}`}</dd>
            </>
          ) : null}
        </dl>
      </PlotCard>
      {fit ? <ModelBlocks fit={fit} card={card} /> : null}
    </div>
  );
}

// --- the read-outs of the rail ---------------------------------------------------------------------------------------

/** The live read-out of the Capital section: the CET1 over RWA of the three plans in the year in focus, and the headroom of the stress. */
export function CapitalReadout({ sel }: { sel: C18Sel | null }) {
  const o = outputsOf(sel);
  const y = (id: (typeof PLAN_ORDER)[number]) => yearOf(planOf(o, id), sel?.year ?? 1);
  const stress = y('stress-without-mitigation');
  const item = (id: (typeof PLAN_ORDER)[number], hint: BiText) => ({ label: text(PLAN_TEXT, id) as BiText, value: y(id)?.cet1.pct_of_rwa ?? null, unitless: true as const, format: RATIO_FORMAT, hint });
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel ? { en: `Year ${sel.year}`, es: `Año ${sel.year}` } : { en: 'The year', es: 'El año' }}
      items={[
        item('base', { en: 'The CET1 over RWA of the ordinary plan at the end of this year.', es: 'El CET1 sobre APR del plan ordinario al final de este año.' }),
        item('stress-without-mitigation', { en: 'The CET1 over RWA after the stressed losses of the years up to this one, with no action of the bank.', es: 'El CET1 sobre APR tras las pérdidas bajo estrés de los años hasta este, sin acción del banco.' }),
        item('stress-with-mitigation', { en: 'The CET1 over RWA with the mitigation actions of the plan.', es: 'El CET1 sobre APR con las acciones de mitigación del plan.' }),
        { label: { en: 'Headroom', es: 'Holgura' }, value: stress?.headroom_pct_of_rwa ?? null, unitless: true, format: RATIO_FORMAT, hint: { en: 'The effective equity over RWA of the stress without mitigation, less the requirement of the year; negative below it.', es: 'El patrimonio efectivo sobre APR del estrés sin mitigación, menos la exigencia del año; negativa bajo ella.' } },
      ]}
    />
  );
}

/** The live read-out of the Path section: the jump-off, the peak against the global financial crisis and the ratio. */
export function PathReadout({ sel }: { sel: C18Sel | null }) {
  const o = outputsOf(sel);
  const p = o?.scenario.paths[sel?.path ?? 0] ?? null;
  const s = p ? o?.severity.rows.find((r) => r.maps_to_regressor === p.maps_to_regressor) ?? null : null;
  const unit: BiText | undefined = p ? { en: p.unit, es: p.unit } : undefined;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={p ? text(REGRESSOR_TEXT, p.maps_to_regressor) : { en: 'The path', es: 'La trayectoria' }}
      items={[
        { label: { en: 'Jump-off', es: 'Punto de partida' }, value: p?.transposition.target.value ?? null, ...(unit ? { unit } : { unitless: true as const }), format: { digits: 4 }, hint: { en: 'The last observed value of Banco Andino, onto which the shape of the published path is transposed.', es: 'El último valor observado de Banco Andino, al que se lleva la forma de la trayectoria publicada.' } },
        { label: { en: 'Peak deviation', es: 'Desviación máxima' }, value: s?.path_peak_deviation ?? null, ...(unit ? { unit } : { unitless: true as const }), format: { digits: 4 }, hint: { en: 'The largest deviation of the path from its starting level.', es: 'La mayor desviación de la trayectoria desde su nivel inicial.' } },
        { label: { en: 'Crisis peak', es: 'Máximo de la crisis' }, value: s?.history_peak_deviation ?? null, ...(unit ? { unit } : { unitless: true as const }), format: { digits: 4 }, hint: { en: 'The largest deviation in the global financial crisis, 2008 to 2009.', es: 'La mayor desviación en la crisis financiera global, 2008 a 2009.' } },
        { label: { en: 'Ratio', es: 'Razón' }, value: s?.ratio ?? null, unitless: true, format: { digits: 4 }, hint: { en: 'The path peak over the crisis peak; the case requires at least the minimum ratio.', es: 'El máximo de la trayectoria sobre el de la crisis; el caso exige al menos la razón mínima.' } },
      ]}
    />
  );
}

/** The live read-out of the Loan type section: the back-cast error and the peaks of the type in focus. */
export function LoanReadout({ sel }: { sel: C18Sel | null }) {
  const o = outputsOf(sel);
  const b = backcastOf(o, sel?.loan ?? '');
  const rate = (v: number | null | undefined, hint: BiText, label: BiText) => ({ label, value: v ?? null, unitless: true as const, format: { percent: true, decimals: 3 } as const, hint });
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel ? text(LOAN_TEXT, sel.loan) : { en: 'The loan type', es: 'El tipo de préstamo' }}
      items={[
        rate(b?.metrics.rmse, { en: 'The root mean squared error of the predicted rate against the realised rate over 2020 to 2025.', es: 'La raíz del error cuadrático medio de la tasa predicha contra la realizada entre 2020 y 2025.' }, { en: 'Error', es: 'Error' }),
        rate(b?.metrics.peak_predicted, { en: 'The highest rate the satellite predicted, fitted on data before 2020.', es: 'La tasa más alta que predijo el satélite, ajustado con datos anteriores a 2020.' }, { en: 'Predicted peak', es: 'Máximo predicho' }),
        rate(b?.metrics.peak_realised, { en: 'The highest rate realised in the window; a realised rate can be negative.', es: 'La tasa más alta realizada en la ventana; una tasa realizada puede ser negativa.' }, { en: 'Realised peak', es: 'Máximo realizado' }),
        { label: { en: 'Timing', es: 'Desfase' }, value: b?.metrics.peak_timing_error_quarters ?? null, unit: { en: 'quarters', es: 'trimestres' }, format: { decimals: 0 }, hint: { en: 'The quarter of the predicted peak less the quarter of the realised peak; positive when the model is late.', es: 'El trimestre del máximo predicho menos el del máximo realizado; positivo cuando el modelo llega tarde.' } },
      ]}
    />
  );
}

/** The live read-out of the Risk section: the capital, the VaR and the share of the Euler allocation of the risk in focus. */
export function RiskReadout({ sel }: { sel: C18Sel | null }) {
  const a = aggOf(sel);
  const m = marginalOf(a, sel?.risk ?? '');
  const e = a?.euler.allocation.find((x) => x.risk === sel?.risk) ?? null;
  const ec = amount(m?.ec_clp_m ?? null);
  const var_ = amount(m?.var_clp_m ?? null);
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel ? text(RISK_TEXT, sel.risk) : { en: 'The risk', es: 'El riesgo' }}
      items={[
        { label: { en: 'Capital', es: 'Capital' }, value: ec.value, unit: ec.unit, format: ec.format, hint: { en: 'The economic capital of this risk at 99.9 percent and one year: the VaR less the expected loss, or the VaR alone when the mean is infinite.', es: 'El capital económico de este riesgo a 99,9 por ciento y un año: el VaR menos la pérdida esperada, o el VaR solo cuando la media es infinita.' } },
        { label: { en: 'VaR', es: 'VaR' }, value: var_.value, unit: var_.unit, format: var_.format, hint: { en: 'The value at risk of the marginal at the same level and horizon.', es: 'El valor en riesgo de la marginal al mismo nivel y horizonte.' } },
        { label: { en: 'Euler share', es: 'Parte de Euler' }, value: e?.share ?? null, unitless: true, format: RATIO_FORMAT, hint: { en: 'The share of the aggregate expected shortfall that the Euler allocation gives to this risk; information, not capital.', es: 'La parte del déficit esperado agregado que la asignación de Euler da a este riesgo; información, no capital.' } },
      ]}
    />
  );
}

/** The live read-out of the Matrix section: the headline capital and the diversified rows under the matrix in focus. */
export function MatrixReadout({ sel }: { sel: C18Sel | null }) {
  const a = aggOf(sel);
  const head = amount(a?.headline.capital_clp_m ?? null);
  const row = (method: string) => amount(a?.band.find((b) => b.method === method)?.capital_clp_m ?? null);
  const gauss = row('gaussian-copula');
  const worst = row('worst-case');
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel?.matrix === 'stress' ? { en: 'Market-credit 0.8', es: 'Mercado-crédito 0,8' } : { en: 'Base matrix', es: 'Matriz base' }}
      items={[
        { label: { en: 'Simple sum', es: 'Suma simple' }, value: head.value, unit: head.unit, format: head.format, hint: { en: 'The headline capital: the sum of the four risks.', es: 'El capital principal: la suma de los cuatro riesgos.' } },
        { label: { en: 'Gaussian', es: 'Gaussiana' }, value: gauss.value, unit: gauss.unit, format: gauss.format, hint: { en: 'Information, not capital: the Gaussian copula aggregate under this matrix.', es: 'Información, no capital: el agregado de la cópula gaussiana bajo esta matriz.' } },
        { label: { en: 'Worst case', es: 'Peor caso' }, value: worst.value, unit: worst.unit, format: worst.format, hint: { en: 'Information, not capital: the upper bound under dependence uncertainty.', es: 'Información, no capital: la cota superior bajo incertidumbre de dependencia.' } },
        { label: { en: 'Market-credit', es: 'Mercado-crédito' }, value: a?.correlation.matrix[1]?.[0] ?? null, unitless: true, format: { digits: 4 }, hint: { en: 'The correlation between the market and credit risks in this matrix.', es: 'La correlación entre los riesgos de mercado y de crédito en esta matriz.' } },
      ]}
    />
  );
}

/** The live read-out of the Row section: the capital of the band row in focus, its diversification factor and its Monte Carlo error. */
export function RowReadout({ sel }: { sel: C18Sel | null }) {
  const a = aggOf(sel);
  const b = a?.band[sel?.row ?? 0] ?? null;
  const cap = amount(b?.capital_clp_m ?? null);
  const se = amount(b?.mc_se_clp_m ?? null);
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={b ? methodShort(b) : { en: 'The row', es: 'La fila' }}
      items={[
        { label: { en: 'Capital', es: 'Capital' }, value: cap.value, unit: cap.unit, format: cap.format, hint: { en: 'The aggregate of the four risks under this method; only the simple sum is capital, every other row is information.', es: 'El agregado de los cuatro riesgos con este método; solo la suma simple es capital, toda otra fila es información.' } },
        { label: { en: 'Factor', es: 'Factor' }, value: b?.diversification_factor ?? null, unitless: true, format: RATIO_FORMAT, hint: { en: 'The aggregate over the simple sum of the capital of the risks.', es: 'El agregado sobre la suma simple del capital de los riesgos.' } },
        { label: { en: 'MC error', es: 'Error MC' }, value: se.value, unit: se.unit, format: se.format, hint: { en: 'The Monte Carlo standard error of the row; not available for a row that is not simulated.', es: 'El error estándar de Monte Carlo de la fila; no disponible para una fila que no se simula.' } },
      ]}
    />
  );
}

/** The live read-out of the Factor section: the factor's spread, its place in the solved scenario and the loss per unit. */
export function FactorReadout({ sel }: { sel: C18Sel | null }) {
  const r = reverseOf(sel);
  const i = sel?.factor ?? 0;
  const f = r?.factor_space.factors[i] ?? null;
  const g = r?.loss_model.gradient_clp_m_per_unit?.[i] ?? null;
  const gm = amount(g);
  const unit: BiText | undefined = f ? { en: f.unit, es: f.unit } : undefined;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={f ? f.label : { en: 'The factor', es: 'El factor' }}
      items={[
        { label: { en: 'Spread', es: 'Dispersión' }, value: f?.sd ?? null, ...(unit ? { unit } : { unitless: true as const }), format: { digits: 4 }, hint: { en: 'The standard deviation of the factor in 1985 to 2019.', es: 'La desviación estándar del factor entre 1985 y 2019.' } },
        { label: { en: 'Solved shock', es: 'Choque resuelto' }, value: r?.solution.x_star[i] ?? null, ...(unit ? { unit } : { unitless: true as const }), format: { digits: 4 }, hint: { en: 'The deviation from the baseline in the minimum-distance scenario that breaks the bank.', es: 'La desviación desde la línea base en el escenario de mínima distancia que quiebra al banco.' } },
        { label: { en: 'Standardised', es: 'Estandarizado' }, value: r?.solution.z_star[i] ?? null, unitless: true, format: { digits: 4 }, hint: { en: 'The same shock in standard deviations of the factor.', es: 'El mismo choque en desviaciones estándar del factor.' } },
        { label: { en: 'Loss per unit', es: 'Pérdida por unidad' }, value: gm.value, unit: gm.unit, format: gm.format, hint: { en: 'The gradient of the loss in this factor; not available when the loss model is nonlinear.', es: 'El gradiente de la pérdida en este factor; no disponible cuando el modelo de pérdida es no lineal.' } },
      ]}
    />
  );
}

/** The live read-out of the Start section: whether the search from this start converged, and where. */
export function StartReadout({ sel }: { sel: C18Sel | null }) {
  const r = reverseOf(sel);
  const s = r?.starts.find((x) => x.start_id === sel?.start) ?? null;
  const loss = amount(s?.loss_clp_m ?? null);
  const index = r ? r.starts.findIndex((x) => x.start_id === sel?.start) : -1;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={index >= 0 ? { en: `Start ${index + 1}`, es: `Inicio ${index + 1}` } : { en: 'The start', es: 'El inicio' }}
      items={[
        { label: { en: 'Converged', es: 'Convergió' }, text: s ? (s.converged ? { en: 'yes', es: 'sí' } : { en: 'no', es: 'no' }) : NA, hint: { en: 'Whether the search from this start reached a scenario that breaks the bank.', es: 'Si la búsqueda desde este inicio llegó a un escenario que quiebra al banco.' } },
        { label: { en: 'Distance', es: 'Distancia' }, value: s?.distance ?? null, unitless: true, format: { digits: 4 }, hint: { en: 'The Mahalanobis distance of the scenario this start found.', es: 'La distancia de Mahalanobis del escenario que encontró este inicio.' } },
        { label: { en: 'Loss', es: 'Pérdida' }, value: loss.value, unit: loss.unit, format: loss.format, hint: { en: 'The loss of that scenario, which should equal the threshold.', es: 'La pérdida de ese escenario, que debe igualar el umbral.' } },
      ]}
    />
  );
}

export { UnavailableCard, methodShort, methodText };
export type { C18Fit };
