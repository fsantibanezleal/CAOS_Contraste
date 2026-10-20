// C12's tests, Findings, Variants and Context groups, and the live read-outs of its rail (ADR-0017 rule 3: every section
// shows a value that moves with its controls). The Findings card and the fixture notice are the ones C06 and C07 use.
// What every view says, whatever the variant: the exposure is a Hull-White one-factor simulation on a synthetic swap book
// over a real Treasury curve; the counterparty curve is a proxy (an AAA to A market spread derived from the Treasury HQM
// curve, or a stated synthetic flat spread); initial margin is a regression proxy, never SIMM; every named parameter of the
// book and the CSA is a convention; the wrong-way variant has no ORE reconciliation.
import type { ReactNode } from 'react';
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import type { TestRow } from '../../lib/contract.types';
import { LIGHT_TEXT } from '../../lib/policy';
import { FindingsCard, FixtureNotice } from '../c06/C06Common';
import { ChartOverTable } from '../c06/format';
import { Pending } from '../Pending';
import { LiveReadout, useCard, type Bi } from '../c03/U6Shared';
import { T } from '../../content/bi';
import { UnavailableCard } from '../c14/C14Common';
import { riskWeight } from './bacva';
import { RATING_SHORT, RATING_TEXT, SECTOR_TEXT, VARIANT_ORDER, VARIANT_TEXT, BASIS_TEXT, CASE_TEXT, HORIZON_LONG, SUBJECT_TEXT, amount, axisOf, fitOf, horizonOf, liveBaCva, liveSaCcr, outputsOf, sensitivityOf, text, gridOf, type C12Outputs, type C12Sel, type Peers } from './selection';

type Lang = 'en' | 'es';
const NA: BiText = { en: formatNumber(null, 'en'), es: formatNumber(null, 'es') };
export const cell = (v: number | null | undefined, lang: Lang) => formatNumber(v, lang, { decimals: 0 });
export const digits = (v: number | null | undefined, lang: Lang) => formatNumber(v, lang, { digits: 4 });
export const SHARE = (v: number | null | undefined, lang: Lang) => formatNumber(v, lang, { percent: true, decimals: 2 });
/** Years on a time axis or in a cell: 0.25, 1, 10. */
export const years = (v: number | null | undefined, lang: Lang) => formatNumber(v, lang, { digits: 4 });

/** The grid of a definition list in a narrow place: the term may wrap and the value keeps 60 percent, so a number never breaks over lines (G19). */
export const DEFS_STYLE = { gridTemplateColumns: 'minmax(0, 40%) minmax(0, 1fr)' } as const;
/** A value that must stay on one line: a number, an amount, a pair of them. */
export function Nw({ children }: { children: ReactNode }) {
  return <span style={{ whiteSpace: 'nowrap' }}>{children}</span>;
}

/** The unit of a column of the documents' money. */
export const MONEY_UNIT: Bi = { en: 'USD', es: 'USD' };

/** The words an absent block says when the view is given a document of another kind. */
export const NOT_SWAP: BiText = { en: 'Not available: this document is not a swap-exposure document of the counterparty credit risk case.', es: 'No disponible: este documento no es un documento de exposición de swaps del caso de riesgo de crédito de contraparte.' };

// --- the tests table ---------------------------------------------------------------------------------------------------

/** The words of the tests the counterparty engine returns for C12; an id without an entry is shown as it is. */
const TEST_TEXT: Record<string, BiText> = {
  'ccr.ee_analytic_vs_simulated': { en: 'Analytic and simulated EE of a single swap', es: 'EE analítica y simulada de un solo swap' },
  'ccr.martingale_discounted_bonds': { en: 'Discounted bond prices are martingales', es: 'Los precios de bonos descontados son martingalas' },
  'ccr.eepe_recomputed': { en: 'EEPE recomputed from the EE profile', es: 'EEPE recalculada desde el perfil de EE' },
  'ccr.cva_recomputed': { en: 'CVA recomputed from the discounted EE', es: 'CVA recalculado desde la EE descontada' },
  'ccr.path_convergence': { en: 'Convergence in the number of paths', es: 'Convergencia en el número de trayectorias' },
  'ccr.reconcile_ee_profile': { en: 'EE profile reconciled with ORE', es: 'Perfil de EE conciliado con ORE' },
  'ccr.pfe_exceedance_backtest': { en: 'PFE exceedance back-test (secondary)', es: 'Backtest de excedencias del PFE (secundario)' },
  'ccr.pit_exposure_backtest': { en: 'PIT back-test of the exposure distribution', es: 'Backtest PIT de la distribución de exposición' },
};

const LIGHT_ORDER = ['green', 'amber', 'red', 'not_evaluated', 'error'] as const;
const LIGHT_TONE_BAR = { green: 'good', amber: 'warn', red: 'bad', not_evaluated: 'neutral', error: 'bad' } as const;

/** The rows the engine returned for the tests of this variant; a test that did not run shows its reason, not a number. */
export function C12TestsView({ sel }: { sel: C12Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  if (!sel) return <Pending />;
  const rows: TestRow[] = sel.data.variant.tests;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The tests of the exposure model', es: 'Las pruebas del modelo de exposición' }}
        {...card}
        note={{
          en: 'The statistic when the test ran, the light under the stated convention and its reference. The lights are conventions of the case, never regulatory thresholds; a test that did not run says why and shows no number.',
          es: 'El estadístico cuando la prueba corrió, la luz bajo la convención declarada y su referencia. Las luces son convenciones del caso, nunca umbrales regulatorios; una prueba que no corrió dice por qué y no muestra número.',
        }}
      >
        {rows.length === 0 ? (
          <p className="ct-note" data-state="unavailable">{pick({ en: 'This variant carries no test row.', es: 'Esta variante no trae filas de pruebas.' }, lang)}</p>
        ) : (
          <ChartOverTable
            chartMin="12rem"
            chart={
              <BarChart
                title={{ en: 'Tests by light', es: 'Pruebas por luz' }}
                height="fill"
                orientation="horizontal"
                data={LIGHT_ORDER.map((l) => ({ id: l, label: LIGHT_TEXT[l], value: rows.filter((t) => t.light === l).length, tone: LIGHT_TONE_BAR[l] }))}
                axis={{ label: { en: 'Number of tests', es: 'Número de pruebas' }, format: { decimals: 0 } }}
              />
            }
          >
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
                    <tr key={`${t.test_id}-${t.segment}-${i}`} data-test={t.test_id} data-light={t.light}>
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
          </ChartOverTable>
        )}
      </PlotCard>
    </ViewsRow>
  );
}

export function C12FindingsView({ sel }: { sel: C12Sel | null }) {
  if (!sel) return <Pending />;
  return (
    <ViewsRow>
      <FindingsCard variant={sel.data.variant} />
    </ViewsRow>
  );
}

// --- the variants -----------------------------------------------------------------------------------------------------

/** The six variants of the case: the EEPE of each as a bar, and the headline numbers of each in a table. */
export function C12VariantsTable({ peers, onPick, current }: { peers: Peers; onPick: (id: string) => void; current: string }) {
  const lang = useShellLang();
  const rows = VARIANT_ORDER.flatMap((v) => (peers[v] ? [{ id: v, peer: peers[v] }] : []));
  const first = rows[0]?.peer.o;
  const card = useCard(undefined);
  const axis = axisOf(rows.map((r) => r.peer.o.exposure.eepe.amount));
  const unit = pick(axis.unit, lang);
  return (
    <PlotCard
      fill
      title={{ en: 'The variants of the case', es: 'Las variantes del caso' }}
      {...card}
      note={{
        en: 'The six variants of the SDD on the same book and curve. The bars give the effective expected positive exposure (EEPE) of each: collateral and initial margin lower it, the wrong-way variant changes the CVA and not the exposure. The table holds the headline numbers of each document.',
        es: 'Las seis variantes del SDD sobre la misma cartera y curva. Las barras dan la exposición positiva esperada efectiva (EEPE) de cada una: el colateral y el margen inicial la bajan, la variante de correlación adversa cambia el CVA y no la exposición. La tabla trae las cifras principales de cada documento.',
      }}
    >
      <ChartOverTable
        chartMin="17rem"
        chart={
          <BarChart
            title={{ en: 'EEPE by variant', es: 'EEPE por variante' }}
            height="fill"
            orientation="horizontal"
            data={rows.map((r) => ({ id: r.id, label: text(VARIANT_TEXT, r.id), value: r.peer.o.exposure.eepe.amount / axis.div, tone: 'accent' as const, highlight: r.peer.variantId === current }))}
            axis={{ label: { en: `Effective EPE over the first year (${pick(axis.unit, 'en')})`, es: `EPE efectiva del primer año (${pick(axis.unit, 'es')})` }, format: { digits: 4 } }}
          />
        }
      >
        <table className="caos-table ct-wrap-head" data-table="variants-c12">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Variant', es: 'Variante' }, lang)}</th>
              <th className="ct-text ct-wide-only">{pick({ en: 'Exposure basis', es: 'Base de la exposición' }, lang)}</th>
              <th>{pick({ en: `EEPE (${unit})`, es: `EEPE (${unit})` }, lang)}</th>
              <th>{pick({ en: 'CVA (USD)', es: 'CVA (USD)' }, lang)}</th>
              <th>{pick({ en: 'SA-CCR EAD (USD)', es: 'EAD SA-CCR (USD)' }, lang)}</th>
              <th className="ct-wide-only">{pick({ en: 'ORE', es: 'ORE' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ id, peer }) => {
              const o = peer.o;
              return (
                <tr key={id} data-variant={id} className={peer.variantId === current ? 'ct-current' : undefined}>
                  <td className="ct-text">
                    <button type="button" className="ct-linkbutton" onClick={() => onPick(peer.variantId)}>{pick(text(VARIANT_TEXT, id), lang)}</button>
                  </td>
                  <td className="ct-text ct-wide-only">{pick(text(BASIS_TEXT, o.exposure.basis), lang)}</td>
                  <td>{formatNumber(o.exposure.eepe.amount / axis.div, lang, { digits: 4 })}</td>
                  <td>{cell(o.cva_dva.cva.amount, lang)}</td>
                  <td>{cell(o.sa_ccr.ead.amount, lang)}</td>
                  <td className="ct-wide-only" data-ore={o.ore_reconciliation.status}>
                    {o.ore_reconciliation.status === 'reconciled' ? pick({ en: 'reconciled', es: 'conciliada' }, lang) : pick({ en: 'no reconciliation', es: 'sin conciliación' }, lang)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {first ? null : <p className="ct-note">{pick({ en: 'No variant document is loaded.', es: 'No hay documentos de variantes cargados.' }, lang)}</p>}
      </ChartOverTable>
    </PlotCard>
  );
}

export function C12VariantsView({ sel, onPick }: { sel: C12Sel | null; onPick: (id: string) => void }) {
  if (!sel || !sel.peers) return <Pending />;
  return (
    <ViewsRow>
      <C12VariantsTable peers={sel.peers} onPick={onPick} current={sel.data.variant.variant_id} />
    </ViewsRow>
  );
}

// --- the context ------------------------------------------------------------------------------------------------------

const NAMED_TEXT: Record<string, Bi> = {
  notionals: { en: 'Notionals of the four swaps', es: 'Nocionales de los cuatro swaps' },
  maturities_years: { en: 'Maturities of the four swaps', es: 'Vencimientos de los cuatro swaps' },
  sides: { en: 'Side of each swap', es: 'Lado de cada swap' },
  netting_set_members: { en: 'Members of the netting set', es: 'Miembros del conjunto de neteo' },
  single_swap_member: { en: 'The swap of the single-swap variant', es: 'El swap de la variante de un solo swap' },
  fixed_rate_rule: { en: 'Rule of the fixed rate', es: 'Regla de la tasa fija' },
  csa_threshold: { en: 'CSA threshold', es: 'Umbral del CSA' },
  csa_minimum_transfer_amount: { en: 'CSA minimum transfer amount', es: 'Monto mínimo de transferencia del CSA' },
  csa_independent_amount: { en: 'CSA independent amount', es: 'Monto independiente del CSA' },
  mpor_business_days_short: { en: 'Margin period of risk, short', es: 'Periodo de riesgo de margen, corto' },
  mpor_business_days_long: { en: 'Margin period of risk, long', es: 'Periodo de riesgo de margen, largo' },
  counterparty_spread: { en: 'Counterparty spread, synthetic', es: 'Spread de la contraparte, sintético' },
  counterparty_lgd: { en: 'Counterparty loss given default', es: 'Pérdida dado el incumplimiento de la contraparte' },
  bank_spread: { en: 'Own spread of the bank', es: 'Spread propio del banco' },
  bank_lgd: { en: 'Own loss given default', es: 'Pérdida dado el incumplimiento propia' },
  pfe_quantile: { en: 'Quantile of the PFE', es: 'Cuantil del PFE' },
  path_count: { en: 'Monte Carlo paths', es: 'Trayectorias de Monte Carlo' },
  seed: { en: 'Seed', es: 'Semilla' },
  time_grid_years: { en: 'Time grid of the exposure', es: 'Grilla de tiempo de la exposición' },
  wwr_b_grid: { en: 'Grid of the wrong-way parameter b', es: 'Grilla del parámetro b de correlación adversa' },
  im_quantile: { en: 'Quantile of the initial margin', es: 'Cuantil del margen inicial' },
  im_horizon_calendar_days: { en: 'Horizon of the initial margin', es: 'Horizonte del margen inicial' },
  im_mpor_calendar_days: { en: 'Margin period of the initial margin', es: 'Periodo de margen del margen inicial' },
  im_regression_order: { en: 'Order of the initial margin regression', es: 'Orden de la regresión del margen inicial' },
  ba_cva_sector: { en: 'Sector of the counterparty (BA-CVA)', es: 'Sector de la contraparte (BA-CVA)' },
  ba_cva_rating: { en: 'Rating class of the counterparty (BA-CVA)', es: 'Clase de calificación de la contraparte (BA-CVA)' },
  stress_window_start: { en: 'Start of the stress window', es: 'Inicio de la ventana de estrés' },
  stress_window_end: { en: 'End of the stress window', es: 'Fin de la ventana de estrés' },
  backtest_window_start: { en: 'Start of the back-test window', es: 'Inicio de la ventana del backtest' },
  backtest_paths_per_date: { en: 'Paths per back-test date', es: 'Trayectorias por fecha del backtest' },
  backtest_simulated_critical_count: { en: 'Simulated back-tests for the critical values', es: 'Backtests simulados para los valores críticos' },
  reconciliation_se_threshold: { en: 'ORE agreement threshold', es: 'Umbral de acuerdo con ORE' },
  ee_check_k_se: { en: 'Threshold of the analytic EE check', es: 'Umbral de la verificación de la EE analítica' },
};
const UNIT_TEXT: Record<string, Bi> = {
  USD: { en: 'USD', es: 'USD' },
  years: { en: 'years', es: 'años' },
  'payer or receiver': { en: 'payer or receiver', es: 'pagador o receptor' },
  'trade ids': { en: 'trade ids', es: 'identificadores de operación' },
  'trade id': { en: 'trade id', es: 'identificador de operación' },
  rule: { en: 'rule', es: 'regla' },
  'business days': { en: 'business days', es: 'días hábiles' },
  'decimal per year': { en: 'per year', es: 'por año' },
  decimal: { en: '', es: '' },
  paths: { en: 'paths', es: 'trayectorias' },
  integer: { en: '', es: '' },
  'per USD million': { en: 'per USD million', es: 'por millón de USD' },
  'calendar days (10 business days)': { en: 'calendar days (10 business days)', es: 'días corridos (10 días hábiles)' },
  'polynomial order': { en: 'polynomial order', es: 'orden del polinomio' },
  'MAR50.16 Table 1 sector': { en: 'sector of MAR50.16 Table 1', es: 'sector de la Tabla 1 de MAR50.16' },
  class: { en: 'class', es: 'clase' },
  date: { en: 'date', es: 'fecha' },
  month: { en: 'month', es: 'mes' },
  'simulated backtests': { en: 'simulated back-tests', es: 'backtests simulados' },
  'combined standard errors': { en: 'combined standard errors', es: 'errores estándar combinados' },
  'standard errors': { en: 'standard errors', es: 'errores estándar' },
};
const VALUE_TEXT: Record<string, Bi> = {
  payer: { en: 'payer', es: 'pagador' },
  receiver: { en: 'receiver', es: 'receptor' },
  "the par yield at the swap's maturity on the curve date, rounded to 10 bp": { en: "the par yield at the swap's maturity on the curve date, rounded to 10 bp", es: 'el rendimiento par al vencimiento del swap en la fecha de la curva, redondeado a 10 pb' },
  financials: SECTOR_TEXT.financials,
  'investment-grade': RATING_TEXT['investment-grade'],
  'high-yield-or-not-rated': RATING_TEXT['high-yield-or-not-rated'],
};
const CONVENTION_WORD: Bi = { en: 'convention', es: 'convención' };

function conventionValue(v: unknown, unit: string, lang: Lang): string {
  const one = (x: unknown): string => {
    if (typeof x === 'number') return unit === 'USD' && Math.abs(x) >= 1e6 ? `${formatNumber(x / 1e6, lang, { digits: 4 })} ${lang === 'es' ? 'M' : 'm'}` : formatNumber(x, lang, { digits: 4, grouping: unit !== 'integer' });
    if (typeof x === 'string') return VALUE_TEXT[x] ? pick(VALUE_TEXT[x], lang) : x;
    return String(x);
  };
  return Array.isArray(v) ? v.map(one).join(', ') : one(v);
}

/** The case, the book, the curve, the calibration, every named parameter as a convention, and the models artifact. */
export function C12ContextView({ sel }: { sel: C12Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const m = sel.data.manifest;
  const v = sel.data.variant;
  const fit = fitOf(sel);
  const cal = o.calibration_used;
  const word = pick(CONVENTION_WORD, lang);
  const params = Object.entries(o.named_parameters);
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case', es: 'El caso' }} {...card}>
        <FixtureNotice variant={v} />
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <dl className="ct-defs" style={DEFS_STYLE} data-table="c12-case" data-variant-id={o.variant}>
          <dt>{pick({ en: 'Variant', es: 'Variante' }, lang)}</dt>
          <dd>{pick(text(VARIANT_TEXT, o.variant), lang)}</dd>
          <dt>{pick({ en: 'What is real and what is synthetic', es: 'Qué es real y qué es sintético' }, lang)}</dt>
          <dd>{pick({ en: 'The Treasury par yield curve is real; the swap book and the CSA are synthetic, with named parameters that are conventions; the counterparty spread is a proxy or a stated synthetic spread.', es: 'La curva de rendimientos par del Tesoro es real; la cartera de swaps y el CSA son sintéticos, con parámetros con nombre que son convenciones; el spread de la contraparte es un proxy o un spread sintético declarado.' }, lang)}</dd>
          <dt>{pick({ en: 'Sign convention', es: 'Convención de signos' }, lang)}</dt>
          <dd>{pick(o.sign_convention.statement, lang)}</dd>
          <dt>{pick({ en: 'Initial margin', es: 'Margen inicial' }, lang)}</dt>
          <dd>{pick({ en: 'A regression proxy of the dynamic initial margin that ORE documents, never ISDA SIMM, whose public methodology restricts its use to a market participant\'s own transactions.', es: 'Un proxy por regresión del margen inicial dinámico que documenta ORE, nunca ISDA SIMM, cuya metodología pública restringe su uso a las operaciones propias de un participante del mercado.' }, lang)}</dd>
          <dt>{pick({ en: 'Wrong-way variant', es: 'Variante de correlación adversa' }, lang)}</dt>
          <dd>{pick({ en: 'It has no ORE reconciliation: ORE\'s wrong-way example is a different model.', es: 'No tiene conciliación con ORE: el ejemplo de correlación adversa de ORE es otro modelo.' }, lang)}</dd>
          <dt>{pick({ en: 'Units', es: 'Unidades' }, lang)}</dt>
          <dd>{pick({ en: 'Money in USD, rates as decimals with continuous compounding, time in years from the curve date, the margin period in business days.', es: 'Dinero en USD, tasas como decimales con capitalización continua, tiempo en años desde la fecha de la curva, el periodo de margen en días hábiles.' }, lang)}</dd>
        </dl>
      </PlotCard>
      <PlotCard title={{ en: 'The swap book', es: 'La cartera de swaps' }} {...card} note={{ en: 'The netting set holds the swaps below; the single-swap variant holds the first. Notional, fixed rate, maturity and side are conventions of the case.', es: 'El conjunto de neteo tiene los swaps de abajo; la variante de un solo swap tiene el primero. Nocional, tasa fija, vencimiento y lado son convenciones del caso.' }}>
        <div className="ct-scroll">
          <table className="caos-table ct-wrap-head" data-table="c12-book">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Swap', es: 'Swap' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Side', es: 'Lado' }, lang)}</th>
                <th>{pick({ en: 'Notional (USD)', es: 'Nocional (USD)' }, lang)}</th>
                <th>{pick({ en: 'Fixed rate', es: 'Tasa fija' }, lang)}</th>
                <th>{pick({ en: 'Maturity (years)', es: 'Vencimiento (años)' }, lang)}</th>
                <th className="ct-wide-only ct-text">{pick({ en: 'Status', es: 'Estado' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.book.trades.map((t) => (
                <tr key={t.trade_id} data-trade={t.trade_id} data-side={t.side}>
                  <td className="ct-text">{t.trade_id}</td>
                  <td className="ct-text">{pick(text(VALUE_TEXT, t.side), lang)}</td>
                  <td>{cell(t.notional.amount, lang)}</td>
                  <td>{formatNumber(t.fixed_rate, lang, { percent: true, decimals: 2 })}</td>
                  <td>{years(t.maturity_years, lang)}</td>
                  <td className="ct-wide-only ct-text">{t.label === 'convention' ? word : t.label}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
      <PlotCard title={{ en: 'The Treasury curve and the calibration', es: 'La curva del Tesoro y la calibración' }} {...card} note={{ en: 'The par yields are the Treasury daily curve of the curve date; a tenor the source does not carry is listed as absent and never interpolated silently. The short-rate parameters are estimated only on data before the curve date.', es: 'Los rendimientos par son la curva diaria del Tesoro de la fecha de la curva; un plazo que la fuente no trae se lista como ausente y nunca se interpola en silencio. Los parámetros de la tasa corta se estiman solo con datos anteriores a la fecha de la curva.' }}>
        <div className="ct-scroll">
          <dl className="ct-defs" style={DEFS_STYLE} data-table="c12-curve">
            <dt>{pick({ en: 'Curve date', es: 'Fecha de la curva' }, lang)}</dt>
            <dd>{o.curve.curve_date}</dd>
            <dt>{pick({ en: 'Tenors present', es: 'Plazos presentes' }, lang)}</dt>
            <dd>{o.curve.tenors_present.map((x) => years(x, lang)).join(', ')}</dd>
            <dt>{pick({ en: 'Tenors absent', es: 'Plazos ausentes' }, lang)}</dt>
            <dd data-na={o.curve.tenors_absent.length === 0 ? 'true' : undefined}>{o.curve.tenors_absent.length ? o.curve.tenors_absent.map((x) => years(x, lang)).join(', ') : pick({ en: 'none', es: 'ninguno' }, lang)}</dd>
            <dt>{pick({ en: 'Interpolated silently', es: 'Interpolada en silencio' }, lang)}</dt>
            <dd>{o.curve.interpolated_silently ? pick({ en: 'yes', es: 'sí' }, lang) : pick({ en: 'no', es: 'no' }, lang)}</dd>
            <dt>{pick({ en: 'Sample of the calibration', es: 'Muestra de la calibración' }, lang)}</dt>
            <dd>{`${cal.sample_start} ${pick({ en: 'to', es: 'a' }, lang)} ${cal.sample_end}; ${cal.n_obs} ${pick({ en: 'observations', es: 'observaciones' }, lang)}; ${years(cal.history_years, lang)} ${pick({ en: 'years', es: 'años' }, lang)}`}</dd>
            <dt>{pick({ en: 'Reversion a and volatility sigma', es: 'Reversión a y volatilidad sigma' }, lang)}</dt>
            <dd data-calibration={cal.backtest_date}>{`a = ${formatNumber(cal.a, lang, { digits: 4 })} (SE ${formatNumber(cal.a_se, lang, { digits: 4 })}); sigma = ${formatNumber(cal.sigma, lang, { digits: 4 })} (SE ${formatNumber(cal.sigma_se, lang, { digits: 4 })})`}</dd>
          </dl>
          <table className="caos-table ct-wrap-head" data-table="c12-curve-points">
            <thead>
              <tr>
                <th>{pick({ en: 'Tenor (years)', es: 'Plazo (años)' }, lang)}</th>
                <th>{pick({ en: 'Par yield', es: 'Rendimiento par' }, lang)}</th>
                <th>{pick({ en: 'Zero rate', es: 'Tasa cero' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.curve.points.map((p) => (
                <tr key={p.tenor_years}>
                  <td>{years(p.tenor_years, lang)}</td>
                  <td>{formatNumber(p.par_yield, lang, { percent: true, decimals: 3 })}</td>
                  <td>{formatNumber(p.zero_rate, lang, { percent: true, decimals: 3 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
      <PlotCard title={{ en: 'The named parameters', es: 'Los parámetros con nombre' }} {...card} note={{ en: 'Every notional, rate, term, CSA term, spread, grid, threshold and seed of the case is a convention, labelled as one.', es: 'Cada nocional, tasa, plazo, término del CSA, spread, grilla, umbral y semilla del caso es una convención, rotulada como tal.' }}>
        <div className="ct-scroll">
          <table className="caos-table ct-wrap-head" data-table="c12-conventions">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Parameter', es: 'Parámetro' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Value', es: 'Valor' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Status', es: 'Estado' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {params.map(([k, p]) => (
                <tr key={k} data-convention={k} data-status={p.label}>
                  <td className="ct-text">{pick(text(NAMED_TEXT, k), lang)}</td>
                  <td className="ct-text">{`${conventionValue(p.value, p.unit, lang)} ${pick(text(UNIT_TEXT, p.unit), lang)}`.trim()}</td>
                  <td className="ct-text">{p.label === 'convention' ? word : p.label}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
      {fit ? (
        <PlotCard title={{ en: 'The models artifact', es: 'El artefacto de modelos' }} {...card} note={{ en: 'The short-rate model is fitted to the Treasury curve of each back-test date and its two parameters are estimated on data up to that date; the closed forms are transcribed from the engine source and their journal derivations are not verified as papers.', es: 'El modelo de tasa corta se ajusta a la curva del Tesoro de cada fecha del backtest y sus dos parámetros se estiman con datos hasta esa fecha; las formas cerradas se transcriben de la fuente del motor y sus derivaciones de la literatura no están verificadas como artículos.' }}>
          <div className="ct-scroll">
            <dl className="ct-defs" style={DEFS_STYLE} data-table="c12-fit">
              <dt>{pick({ en: 'Estimator', es: 'Estimador' }, lang)}</dt>
              <dd><span translate="no">{fit.estimator}</span></dd>
              <dt>{pick({ en: 'Minimum history', es: 'Historia mínima' }, lang)}</dt>
              <dd>{`${fit.min_history_years} ${pick({ en: 'years (CRE53.51)', es: 'años (CRE53.51)' }, lang)}`}</dd>
              <dt>{pick({ en: 'Closed forms', es: 'Formas cerradas' }, lang)}</dt>
              <dd data-unverified="true">
                <T en="transcribed from " es="transcritas de " />
                <span translate="no">{fit.closed_forms_source}</span>
                <T en="; the journal derivations are UNVERIFIED as papers" es="; las derivaciones de la literatura NO están verificadas como artículos" />
              </dd>
              <dt>{pick({ en: 'Counterparty curve', es: 'Curva de la contraparte' }, lang)}</dt>
              <dd data-label={fit.credit_curve.label}>{`${pick({ en: 'proxy', es: 'proxy' }, lang)}: ${pick(fit.credit_curve.derivation, lang)}`}</dd>
              <dt>{pick({ en: 'Licence of the spread source', es: 'Licencia de la fuente del spread' }, lang)}</dt>
              <dd>{pick(fit.credit_curve.licence_basis, lang)}</dd>
              <dt>{pick({ en: 'Synthetic spread', es: 'Spread sintético' }, lang)}</dt>
              <dd data-status={fit.credit_curve.synthetic_spread.label}>{`${formatNumber(Number(fit.credit_curve.synthetic_spread.value), lang, { percent: true, decimals: 2 })} (${word})`}</dd>
              <dt>{pick({ en: 'Negative spread', es: 'Spread negativo' }, lang)}</dt>
              <dd>{pick({ en: 'A negative HQM-minus-Treasury spread is set to zero and counted, never carried as a negative spread.', es: 'Un spread HQM menos Tesoro negativo se fija en cero y se cuenta, nunca se arrastra como spread negativo.' }, lang)}</dd>
            </dl>
            <table className="caos-table ct-wrap-head" data-table="c12-calibrations">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Back-test date', es: 'Fecha del backtest' }, lang)}</th>
                  <th>{pick({ en: 'a', es: 'a' }, lang)}</th>
                  <th>{pick({ en: 'sigma', es: 'sigma' }, lang)}</th>
                  <th className="ct-wide-only">{pick({ en: 'Observations', es: 'Observaciones' }, lang)}</th>
                  <th className="ct-text ct-wide-only">{pick({ en: 'Sample', es: 'Muestra' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {fit.calibrations.map((c) => (
                  <tr key={c.backtest_date} data-calibration={c.backtest_date}>
                    <td className="ct-text">{c.backtest_date}</td>
                    <td>{formatNumber(c.a, lang, { digits: 4 })}</td>
                    <td>{formatNumber(c.sigma, lang, { digits: 4 })}</td>
                    <td className="ct-wide-only">{c.n_obs}</td>
                    <td className="ct-text ct-wide-only">{`${c.sample_start} ${pick({ en: 'to', es: 'a' }, lang)} ${c.sample_end}`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <ul className="ct-note" data-table="c12-limits">
              {fit.limits.map((l, i) => (
                <li key={i}>{pick(l, lang)}</li>
              ))}
            </ul>
          </div>
        </PlotCard>
      ) : null}
    </div>
  );
}

// --- the read-outs of the rail ---------------------------------------------------------------------------------------

const SHARE_FORMAT = { percent: true, decimals: 2 } as const;
export const MAX_SENSITIVITY = 5;

/** The live read-out of the Time section: the EE, the ENE and the PFE at the grid point in focus. */
export function TimeReadout({ sel }: { sel: C12Sel | null }) {
  const o = outputsOf(sel);
  const i = sel && o ? Math.min(sel.t, gridOf(o).length - 1) : -1;
  const at = (a: number[] | undefined) => amount(o && a && i >= 0 ? a[i] : null);
  const ee = at(o?.exposure.ee.values);
  const ene = at(o?.exposure.ene.values);
  const pfe = at(o?.exposure.pfe.values);
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={o && i >= 0 ? { en: `Year ${formatNumber(gridOf(o)[i], 'en', { digits: 4 })}`, es: `Año ${formatNumber(gridOf(o)[i], 'es', { digits: 4 })}` } : { en: 'The time point', es: 'El punto de tiempo' }}
      items={[
        { label: { en: 'EE', es: 'EE' }, value: ee.value, unit: ee.unit, format: ee.format, hint: { en: 'The expected exposure to the counterparty at this time, undiscounted (Basel style).', es: 'La exposición esperada a la contraparte en este tiempo, sin descontar (estilo Basilea).' } },
        { label: { en: 'ENE', es: 'ENE' }, value: ene.value, unit: ene.unit, format: ene.format, hint: { en: 'The expected negative exposure: the bank\'s own exposure, reported as a positive number.', es: 'La exposición negativa esperada: la exposición propia del banco, informada como número positivo.' } },
        { label: { en: 'PFE', es: 'PFE' }, value: pfe.value, unit: pfe.unit, format: pfe.format, hint: { en: 'The potential future exposure at the quantile of the case.', es: 'La exposición futura potencial en el cuantil del caso.' } },
      ]}
    />
  );
}

/** The live read-out of the Back-test section: the statistic and the decision of the horizon in focus. */
export function HorizonReadout({ sel }: { sel: C12Sel | null }) {
  const o = outputsOf(sel);
  const h = horizonOf(o, sel?.subject ?? 'book', sel?.horizon ?? '12m');
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel ? { en: `${pick(text(HORIZON_LONG, sel.horizon), 'en')}, ${pick(text(SUBJECT_TEXT, sel.subject), 'en').toLowerCase()}`, es: `${pick(text(HORIZON_LONG, sel.horizon), 'es')}, ${pick(text(SUBJECT_TEXT, sel.subject), 'es').toLowerCase()}` } : { en: 'The horizon', es: 'El horizonte' }}
      items={[
        { label: { en: 'W²', es: 'W²' }, value: h?.w2 ?? null, unitless: true, format: { digits: 4 }, hint: { en: 'The Anderson-Darling statistic of the PITs: large when they are not uniform.', es: 'El estadístico de Anderson-Darling de los PIT: grande cuando no son uniformes.' } },
        { label: { en: '5% value', es: 'Valor al 5%' }, value: h?.critical_simulated.p05 ?? null, unitless: true, format: { digits: 4 }, hint: { en: 'The 95th percentile of W² when the whole back-test is simulated under the model itself.', es: 'El percentil 95 de W² cuando todo el backtest se simula bajo el propio modelo.' } },
        { label: { en: 'Decision', es: 'Decisión' }, text: h ? (h.reject_at_5pct ? { en: 'rejected at 5%', es: 'rechazado al 5%' } : { en: 'not rejected', es: 'no rechazado' }) : NA, hint: { en: 'Against the simulated critical value, not the independent-sample table.', es: 'Contra el valor crítico simulado, no la tabla de muestras independientes.' } },
      ]}
    />
  );
}

/** The live read-out of the Case section: the wrong-way point in focus, or the calibration case in focus. */
export function CaseReadout({ sel }: { sel: C12Sel | null }) {
  const o = outputsOf(sel);
  const w = o?.wrong_way_risk ?? null;
  if (w) {
    const p = w.sweep[Math.min(sel?.b ?? 0, w.sweep.length - 1)] ?? null;
    const cva = amount(p?.cva.amount ?? null);
    const base = amount(w.independent_cva.amount);
    return (
      <LiveReadout
        variant={sel?.data.variant}
        title={p ? { en: `b = ${formatNumber(p.b, 'en', { digits: 4 })}`, es: `b = ${formatNumber(p.b, 'es', { digits: 4 })}` } : { en: 'The wrong-way point', es: 'El punto de correlación adversa' }}
        items={[
          { label: { en: 'CVA', es: 'CVA' }, value: cva.value, unit: cva.unit, format: cva.format, hint: { en: 'The CVA when the counterparty hazard rate moves with the portfolio value at this b.', es: 'El CVA cuando la tasa de riesgo de la contraparte se mueve con el valor de la cartera con este b.' } },
          { label: { en: 'Independent', es: 'Independiente' }, value: base.value, unit: base.unit, format: base.format, hint: { en: 'The CVA with b = 0 on the same paths: exposure and default independent.', es: 'El CVA con b = 0 sobre las mismas trayectorias: exposición e incumplimiento independientes.' } },
        ]}
      />
    );
  }
  const c = sensitivityOf(o, sel?.caseId ?? 'base');
  const eepe = amount(c?.eepe.amount ?? null);
  const peak = amount(c?.pfe_peak.amount ?? null);
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel ? text(CASE_TEXT, sel.caseId) : { en: 'The calibration case', es: 'El caso de calibración' }}
      items={[
        { label: { en: 'a', es: 'a' }, value: c?.a ?? null, unitless: true, format: { digits: 4 }, hint: { en: 'The mean reversion speed of the short rate in this case.', es: 'La velocidad de reversión a la media de la tasa corta en este caso.' } },
        { label: { en: 'Sigma', es: 'Sigma' }, value: c?.sigma ?? null, unitless: true, format: { digits: 4 }, hint: { en: 'The volatility of the short rate in this case.', es: 'La volatilidad de la tasa corta en este caso.' } },
        { label: { en: 'EEPE', es: 'EEPE' }, value: eepe.value, unit: eepe.unit, format: eepe.format, hint: { en: 'The effective expected positive exposure of the first year in this case.', es: 'La exposición positiva esperada efectiva del primer año en este caso.' } },
        { label: { en: 'PFE peak', es: 'Pico del PFE' }, value: peak.value, unit: peak.unit, format: peak.format, hint: { en: 'The largest PFE of the profile in this case.', es: 'El mayor PFE del perfil en este caso.' } },
      ]}
    />
  );
}

/** The live read-out of the Collateral section: the live SA-CCR on the collateral in focus (the port of CRE52). */
export function SaCcrReadout({ sel }: { sel: C12Sel | null }) {
  const o = outputsOf(sel);
  const live = liveSaCcr(o, sel?.collateral ?? null);
  const rc = amount(live?.rc ?? null);
  const pfe = amount(live?.pfe ?? null);
  const ead = amount(live?.ead ?? null);
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'SA-CCR, live', es: 'SA-CCR, en vivo' }}
      items={[
        { label: { en: 'RC', es: 'RC' }, value: rc.value, unit: rc.unit, format: rc.format, hint: { en: 'The replacement cost: the larger of the value less the collateral and zero (CRE52.10).', es: 'El costo de reemplazo: el mayor entre el valor menos el colateral y cero (CRE52.10).' } },
        { label: { en: 'Multiplier', es: 'Multiplicador' }, value: live?.multiplier ?? null, unitless: true, format: { digits: 4 }, hint: { en: 'At most 1, with a floor of 5 percent: it falls as the netting set is over-collateralised (CRE52.23).', es: 'A lo más 1, con un piso de 5 por ciento: baja cuando el conjunto está sobrecolateralizado (CRE52.23).' } },
        { label: { en: 'PFE add-on', es: 'Add-on PFE' }, value: pfe.value, unit: pfe.unit, format: pfe.format, hint: { en: 'The multiplier times the aggregate add-on (CRE52.20).', es: 'El multiplicador por el add-on agregado (CRE52.20).' } },
        { label: { en: 'EAD', es: 'EAD' }, value: ead.value, unit: ead.unit, format: ead.format, hint: { en: 'Alpha 1.4 times RC plus PFE (CRE52.1).', es: 'Alfa 1,4 por RC más PFE (CRE52.1).' } },
      ]}
    />
  );
}

/** The live read-out of the Counterparty section: the live BA-CVA on the sector and rating in focus (the port of MAR50). */
export function BaCvaReadout({ sel }: { sel: C12Sel | null }) {
  const o = outputsOf(sel);
  const sa = liveSaCcr(o, sel?.collateral ?? null);
  const ba = liveBaCva(o, sa?.ead ?? null, sel?.sector ?? 'financials', sel?.rating ?? 'investment-grade');
  const scva = amount(ba?.scva[0] ?? null);
  const cap = amount(ba?.capital ?? null);
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel ? { en: `${pick(text(SECTOR_TEXT, sel.sector), 'en')}, ${pick(text(RATING_SHORT, sel.rating), 'en')}`, es: `${pick(text(SECTOR_TEXT, sel.sector), 'es')}, ${pick(text(RATING_SHORT, sel.rating), 'es')}` } : { en: 'The counterparty', es: 'La contraparte' }}
      items={[
        { label: { en: 'Risk weight', es: 'Ponderador' }, value: sel ? riskWeight(sel.sector, sel.rating) : null, unitless: true, format: SHARE_FORMAT, hint: { en: 'MAR50.16 Table 1: by sector and by investment grade or high yield and not rated.', es: 'Tabla 1 de MAR50.16: por sector y por grado de inversión o alto rendimiento y sin calificación.' } },
        { label: { en: 'SCVA', es: 'SCVA' }, value: scva.value, unit: scva.unit, format: scva.format, hint: { en: 'The standalone CVA charge of the counterparty: risk weight times maturity, EAD and discount factor over alpha.', es: 'El cargo de CVA individual de la contraparte: ponderador por vencimiento, EAD y factor de descuento sobre alfa.' } },
        { label: { en: 'Capital', es: 'Capital' }, value: cap.value, unit: cap.unit, format: cap.format, hint: { en: 'DS 0.65 times K reduced (MAR50.14); the reduced version, no hedges.', es: 'DS 0,65 por K reducido (MAR50.14); la versión reducida, sin coberturas.' } },
      ]}
    />
  );
}

export { UnavailableCard, axisOf, amount };
export type { C12Outputs };
