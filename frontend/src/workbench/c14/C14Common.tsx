// C14's Findings, Variants and Context groups, the live read-outs of its rail (ADR-0017 rule 3: every section shows a
// value that moves with its controls) and the tests table every IRRBB view shares. The Findings card and the fixture
// notice are the ones C06 and C07 use. Money is the document's: `units.money_scale` says whether a table cell is in
// units, thousands or millions, and a narrow place (a read-out, an axis) scales it to bn or m with the unit that says so.
import { Fragment } from 'react';
import { PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { loadAllVariants, useArtifact, type CaseData } from '../../api/artifacts';
import type { TestRow, VariantArtifact } from '../../lib/contract.types';
import { LIGHT_TEXT } from '../../lib/policy';
import { FindingsCard, FixtureNotice } from '../c06/C06Common';
import { ChartOverTable } from '../c06/format';
import { Pending } from '../Pending';
import { LiveReadout, useCard, type Bi } from '../c03/U6Shared';
import {
  CALIBRATION_TEXT, CATEGORY_TEXT, NMD_LONG, NMD_TEXT, ORIGIN_TEXT, SOURCE_KIND_TEXT, SHOCK_TEXT, amount, axisOf, cell, categoriesOf, fitOf, nmdModelOf,
  outputsOf, scaleUnit, scenarioFor, scenarioOf, shockOf, text, type C14Outputs, type C14Sel,
} from './selection';
import { IRRBB_SOURCE_RULES, TEST_NOTE_RULES, TEST_REFERENCE_RULES, localise } from './localise';
import { testText } from '../names';

/** The words of the tests the IRRBB engine returns for C14 and C15; an id without an entry is shown as it is. */
const TEST_TEXT: Record<string, BiText> = {
  'irrbb.srp31_92_goldens': { en: 'SRP31.92 golden values reproduced', es: 'Valores de referencia de SRP31.92 reproducidos' },
  'irrbb.cmf_annex1_goldens': { en: 'CMF Annex 1 golden values reproduced', es: 'Valores de referencia del Anexo 1 de la CMF reproducidos' },
  'irrbb.eve_sum_of_parts': { en: 'EVE sum-of-parts reconciliation', es: 'Conciliación de la suma de partes del EVE' },
  'irrbb.nmd_parameter_stability': { en: 'NMD parameter stability across windows', es: 'Estabilidad de los parámetros NMD entre ventanas' },
  'irrbb.eve_with_without_behavioural': { en: 'EVE with and without behavioural assumptions', es: 'EVE con y sin supuestos conductuales' },
  'irrbb.behavioural_change_at_breach': { en: 'Behavioural parameter change at a limit breach', es: 'Cambio de un parámetro conductual en un exceso de límite' },
  'irrbb.nii_out_of_sample': { en: 'NII projection against the realised NII', es: 'Proyección del NII contra el NII realizado' },
};

/**
 * The rows the engine returned for the tests of this variant, as a block that sits under the drawing of the view the
 * tests belong to: a test that did not run shows its reason, not a number. `only` keeps the tests of one view.
 */
export function IrrbbTestsTable({ variant, only }: { variant: VariantArtifact; only?: (t: TestRow) => boolean }) {
  const lang = useShellLang();
  const rows: TestRow[] = only ? variant.tests.filter(only) : variant.tests;
  return (
    <div data-block="tests">
      <p className="ct-note">
        {pick({ en: 'The tests the engine returned: the statistic when it ran, the light under the committed policy and its reference. A test that did not run says why and shows no number.', es: 'Las pruebas que devolvió el motor: el estadístico cuando corrió, la luz bajo la política versionada y su referencia. Una prueba que no corrió dice por qué y no muestra número.' }, lang)}
      </p>
      {rows.length === 0 ? (
        <p className="ct-note" data-state="unavailable">{pick({ en: 'This variant carries no test row for this view.', es: 'Esta variante no trae filas de pruebas para esta vista.' }, lang)}</p>
      ) : (
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
                  <td className="ct-text">{pick(TEST_TEXT[t.test_id] ?? testText(t.test_id), lang)}</td>
                  <td data-na={ran && t.statistic !== null ? undefined : 'true'}>{ran && t.statistic !== null ? formatNumber(t.statistic, lang, { digits: 4 }) : formatNumber(null, lang)}</td>
                  <td className={`ct-text ct-light ct-light-${t.light}`}>
                    <span className="ct-light-word">{pick(LIGHT_TEXT[t.light], lang)}</span>
                  </td>
                  <td className="ct-text">{t.notes ? localise(t.notes, lang, TEST_NOTE_RULES) : localise(t.reference, lang, TEST_REFERENCE_RULES)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

/** "Unavailable" card for a view whose block the document lacks: a declared state, never an empty chart. */
export function UnavailableCard({ sel, title, reason }: { sel: { data: CaseData } | null; title: BiText; reason: BiText }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  return (
    <ViewsRow>
      <PlotCard fill title={title} {...card}>
        <p className="caos-pending" data-state="unavailable">{pick(reason, lang)}</p>
      </PlotCard>
    </ViewsRow>
  );
}

export function C14FindingsView({ sel }: { sel: C14Sel | null }) {
  if (!sel) return <Pending />;
  return (
    <ViewsRow>
      <FindingsCard variant={sel.data.variant} />
    </ViewsRow>
  );
}

/** The ratio of the EVE risk measure to Tier 1 of each valuation date against the 15 percent line, with the date's out-of-sample error. */
export function C14VariantsTable({ variants, onPick, current, calibration }: { variants: Array<{ id: string; title: BiText; v: VariantArtifact<C14Outputs> }>; onPick: (id: string) => void; current: string; calibration: string }) {
  const lang = useShellLang();
  const first = variants[0]?.v;
  const card = useCard(first as unknown as VariantArtifact | undefined);
  const sorted = [...variants].sort((a, b) => a.v.outputs.valuation_date.localeCompare(b.v.outputs.valuation_date));
  const ratio = (v: VariantArtifact<C14Outputs>, nmd: string) => scenarioOf(v.outputs, calibration, nmd)?.outlier.ratio ?? null;
  const x = sorted.map((e) => Date.parse(`${e.v.outputs.valuation_date}T00:00:00Z`) / 1000);
  return (
    <PlotCard
      fill
      title={{ en: 'The valuation dates', es: 'Las fechas de valoración' }}
      {...card}
      note={{
        en: 'The EVE risk measure over Tier 1 at each valuation date, with and without the behavioural deposit assumptions, against the 15 percent outlier threshold. Pick a date to load it.',
        es: 'La medida de riesgo EVE sobre el capital de nivel 1 en cada fecha de valoración, con y sin los supuestos conductuales de depósitos, contra el umbral de valor atípico de 15 por ciento. Elija una fecha para cargarla.',
      }}
    >
      <ChartOverTable
        chart={
          <UPlotChart
            height="fill"
            x={{ values: x, time: true, label: { en: 'Valuation date', es: 'Fecha de valoración' } }}
            y={{ label: { en: 'EVE risk measure over Tier 1', es: 'Medida de riesgo EVE sobre capital de nivel 1' }, format: { percent: true, decimals: 0 } }}
            series={[
              { label: NMD_TEXT.behavioural, values: sorted.map((e) => ratio(e.v, 'behavioural')), color: '--color-accent', width: 2.6, mode: 'points', size: 11 },
              { label: NMD_TEXT.contractual, values: sorted.map((e) => ratio(e.v, 'contractual')), color: '--color-magenta', width: 2.2, mode: 'points', size: 11 },
            ]}
            marks={sorted.map((e, i) => ({ x: x[i], label: { en: e.v.outputs.quarter, es: e.v.outputs.quarter } }))}
            yMarks={[{ y: 0.15, label: { en: 'Outlier threshold: 15% of Tier 1', es: 'Umbral de valor atípico: 15 % del capital de nivel 1' }, tone: 'bad' }]}
          />
        }
      >
        <table className="caos-table ct-wrap-head" data-table="variants-c14" data-threshold="0.15">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Valuation date', es: 'Fecha de valoración' }, lang)}</th>
              <th>{pick({ en: 'Behavioural', es: 'Conductual' }, lang)}</th>
              <th>{pick({ en: 'Contractual', es: 'Contractual' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Outlier', es: 'Valor atípico' }, lang)}</th>
              <th className="ct-wide-only">{pick({ en: 'NII projection error', es: 'Error de la proyección del NII' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map(({ id, title, v }) => {
              const b = scenarioOf(v.outputs, calibration, 'behavioural');
              const c = scenarioOf(v.outputs, calibration, 'contractual');
              const oos = v.outputs.out_of_sample;
              const breached = [b, c].some((s) => s?.outlier.breached);
              return (
                <tr key={id} data-variant={id} data-date={v.outputs.valuation_date} className={id === current ? 'ct-current' : undefined}>
                  <td className="ct-text">
                    <button type="button" className="ct-linkbutton" onClick={() => onPick(id)}>{pick(title, lang)}</button>
                    <span className="ct-note">{` ${v.outputs.valuation_date}`}</span>
                  </td>
                  <td>{b ? formatNumber(b.outlier.ratio, lang, { percent: true, decimals: 2 }) : formatNumber(null, lang)}</td>
                  <td>{c ? formatNumber(c.outlier.ratio, lang, { percent: true, decimals: 2 }) : formatNumber(null, lang)}</td>
                  <td className="ct-text" data-breached={breached}>
                    {pick(b?.outlier.breached ? { en: 'fires with the behavioural assumption', es: 'se activa con el supuesto conductual' } : c?.outlier.breached ? { en: 'fires without it only', es: 'se activa solo sin él' } : { en: 'does not fire', es: 'no se activa' }, lang)}
                  </td>
                  <td className="ct-wide-only" data-na={oos.applicable ? undefined : 'true'}>{oos.applicable && oos.relative_error !== null ? formatNumber(oos.relative_error, lang, { percent: true, decimals: 2 }) : formatNumber(null, lang)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </ChartOverTable>
    </PlotCard>
  );
}

export function C14VariantsView({ sel, onPick }: { sel: C14Sel | null; onPick: (id: string) => void }) {
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  if (!sel || all.state !== 'ready') return <Pending />;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const variants = (all.data as unknown as Array<VariantArtifact<C14Outputs>>)
    .filter((v) => v.outputs.kind === 'valuation-date')
    .map((v) => ({ id: v.variant_id, title: entries.find((e) => e.variant_id === v.variant_id)?.short_title ?? { en: v.variant_id, es: v.variant_id }, v }));
  return (
    <ViewsRow>
      <C14VariantsTable variants={variants} onPick={onPick} current={sel.data.variant.variant_id} calibration={sel.calibration} />
    </ViewsRow>
  );
}

const ASSUMPTION_TEXT: Record<string, Bi> = {
  nmd_core_share: { en: 'Core share of non-maturity deposits', es: 'Parte estable de los depósitos sin vencimiento' },
  nmd_core_maturity_years: { en: 'Core maturity of non-maturity deposits', es: 'Plazo de la parte estable de los depósitos sin vencimiento' },
  prepayment_cpr: { en: 'Prepayment rate (CPR)', es: 'Tasa de prepago (CPR)' },
  term_deposit_redemption_rate: { en: 'Early redemption of term deposits', es: 'Rescate anticipado de depósitos a plazo' },
  deposit_beta: { en: 'Deposit beta', es: 'Beta de depósitos' },
};
const ITEM_CATEGORY_TEXT: Record<string, Bi> = {
  cash: { en: 'Cash', es: 'Efectivo' },
  'securities-htm': { en: 'Securities held to maturity', es: 'Valores mantenidos al vencimiento' },
  'securities-afs': { en: 'Securities available for sale', es: 'Valores disponibles para la venta' },
  'loans-fixed': { en: 'Fixed-rate loans', es: 'Créditos a tasa fija' },
  'loans-floating': { en: 'Floating-rate loans', es: 'Créditos a tasa variable' },
  'other-assets': { en: 'Other assets', es: 'Otros activos' },
  'deposits-transactional': { en: 'Transactional deposits', es: 'Depósitos transaccionales' },
  'deposits-non-transactional': { en: 'Non-transactional deposits', es: 'Depósitos no transaccionales' },
  'deposits-time': { en: 'Time deposits', es: 'Depósitos a plazo' },
  borrowings: { en: 'Borrowings', es: 'Obligaciones' },
  'other-liabilities': { en: 'Other liabilities', es: 'Otros pasivos' },
};

/** An assumption's value in its unit: shares and rates as percent, years as a number. */
export function assumptionValue(value: number, unit: string, lang: 'en' | 'es'): string {
  return unit === 'years' ? `${formatNumber(value, lang, { digits: 4 })} ${lang === 'es' ? 'años' : 'years'}` : formatNumber(value, lang, { percent: true, decimals: 2 });
}

/** The case, the real aggregates and the synthetic behaviour (labelled), the data cut-off, the curve, the assumptions and the slotted balance sheet. */
export function C14ContextView({ sel }: { sel: C14Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const m = sel.data.manifest;
  const v = sel.data.variant;
  const unit = pick(scaleUnit(o), lang);
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case', es: 'El caso' }} {...card}>
        <FixtureNotice variant={v} />
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <dl className="ct-defs" data-table="c14-bank">
          <dt>{pick({ en: 'Bank', es: 'Banco' }, lang)}</dt>
          <dd>{o.bank.name}</dd>
          <dt>{pick({ en: 'Balance-sheet aggregates', es: 'Agregados del balance' }, lang)}</dt>
          <dd data-aggregates={o.bank.aggregates}>{pick({ en: 'real: the FDIC call reports', es: 'reales: los reportes de condición de la FDIC' }, lang)}</dd>
          <dt>{pick({ en: 'Behaviour of deposits and loans', es: 'Conducta de depósitos y créditos' }, lang)}</dt>
          <dd data-behaviour={o.bank.behaviour}>{pick({ en: 'synthetic: stated assumptions, not the bank\'s models', es: 'sintética: supuestos declarados, no los modelos del banco' }, lang)}</dd>
          <dt>{pick({ en: 'Notice of the document', es: 'Aviso del documento' }, lang)}</dt>
          <dd>{pick(o.bank.notice, lang)}</dd>
          <dt>{pick({ en: 'Valuation date', es: 'Fecha de valoración' }, lang)}</dt>
          <dd>{`${o.valuation_date} (${o.quarter})`}</dd>
          <dt>{pick({ en: 'Sign convention', es: 'Convención de signo' }, lang)}</dt>
          <dd>{pick(o.sign_convention.statement, lang)}</dd>
          <dt>{pick({ en: 'Money', es: 'Dinero' }, lang)}</dt>
          <dd>{unit}</dd>
        </dl>
      </PlotCard>
      <PlotCard title={{ en: 'The data and the curve', es: 'Los datos y la curva' }} {...card} note={{ en: 'The call reports are read only up to the valuation date; a later report is never read.', es: 'Los reportes se leen solo hasta la fecha de valoración; nunca se lee uno posterior.' }}>
        <dl className="ct-defs" data-table="c14-data">
          <dt>{pick({ en: 'Data cut-off', es: 'Corte de los datos' }, lang)}</dt>
          <dd>{o.data.data_cutoff}</dd>
          <dt>{pick({ en: 'Reading rule', es: 'Regla de lectura' }, lang)}</dt>
          <dd>{pick(o.data.rule, lang)}</dd>
          {o.data.call_reports.map((r) => (
            <Fragment key={r.report_date}>
              <dt>{`${pick({ en: 'Call report', es: 'Reporte' }, lang)} ${r.report_date}`}</dt>
              <dd data-report={r.report_date}>{r.source}</dd>
            </Fragment>
          ))}
          <dt>{pick({ en: 'Treasury curve', es: 'Curva del Tesoro' }, lang)}</dt>
          <dd>{`${localise(o.curve.source, lang, IRRBB_SOURCE_RULES)} (${o.curve.date})`}</dd>
          <dt>{pick({ en: 'Interpolation', es: 'Interpolación' }, lang)}</dt>
          <dd>{localise(o.curve.interpolation, lang, IRRBB_SOURCE_RULES)}</dd>
          <dt>{pick({ en: 'Tenors the date lacks', es: 'Plazos que la fecha no trae' }, lang)}</dt>
          <dd data-missing-tenors={o.curve.missing_tenors.length}>{o.curve.missing_tenors.length === 0 ? pick({ en: 'none', es: 'ninguno' }, lang) : o.curve.missing_tenors.map((t) => `${formatNumber(t, lang, { digits: 4 })} ${lang === 'es' ? 'años' : 'y'}`).join(', ')}</dd>
        </dl>
      </PlotCard>
      <PlotCard title={{ en: 'The behavioural assumptions', es: 'Los supuestos conductuales' }} {...card} note={{ en: 'Each assumption names where it comes from: a regulatory cap, a fit, or a synthetic value stated here. The standardised EVE uses the capped values.', es: 'Cada supuesto dice de dónde viene: un tope regulatorio, un ajuste, o un valor sintético declarado aquí. El EVE estandarizado usa los valores con tope.' }}>
        <div className="ct-scroll" data-caos-flow="">
          <table className="caos-table ct-wrap-head" data-table="c14-assumptions">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Assumption', es: 'Supuesto' }, lang)}</th>
                <th>{pick({ en: 'Value', es: 'Valor' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Where it comes from', es: 'De dónde viene' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Source', es: 'Fuente' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {(Object.keys(o.assumptions) as Array<keyof C14Outputs['assumptions']>).map((k) => {
                const a = o.assumptions[k];
                return (
                  <tr key={k} data-assumption={k} data-source-kind={a.source_kind}>
                    <td className="ct-text">{pick(text(ASSUMPTION_TEXT, k), lang)}</td>
                    <td>{assumptionValue(a.value, a.unit, lang)}</td>
                    <td className="ct-text">{pick(text(SOURCE_KIND_TEXT, a.source_kind), lang)}</td>
                    <td className="ct-text ct-wide-only">{localise(a.source, lang, IRRBB_SOURCE_RULES)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </PlotCard>
      <PlotCard title={{ en: 'The slotted balance sheet', es: 'El balance ubicado en tramos' }} {...card} note={{ en: `Amounts in ${unit}. An item the financials lack shows not available with its reason and the slotting assumption that replaces it, never an invented number.`, es: `Montos en ${unit}. Una partida que los estados no traen muestra no disponible con su razón y el supuesto de ubicación que la reemplaza, nunca un número inventado.` }}>
        <div className="ct-scroll" data-caos-flow="">
          <table className="caos-table ct-wrap-head" data-table="c14-items">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Item', es: 'Partida' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Category', es: 'Categoría' }, lang)}</th>
                <th>{pick({ en: 'Reported', es: 'Informado' }, lang)}</th>
                <th>{pick({ en: 'Slotted', es: 'Ubicado' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Slotting assumption', es: 'Supuesto de ubicación' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.balance_sheet.items.map((i) => (
                <tr key={i.item_id} data-item={i.item_id} data-reported={i.reported_amount === null ? 'missing' : 'reported'}>
                  <td className="ct-text">{pick(i.label, lang)}</td>
                  <td className="ct-text ct-wide-only">{pick(text(ITEM_CATEGORY_TEXT, i.category), lang)}</td>
                  <td data-na={i.reported_amount === null ? 'true' : undefined}>
                    {i.reported_amount === null ? (
                      <>
                        {formatNumber(null, lang)}
                        {i.reason_missing ? <span className="ct-note" style={{ display: 'block', whiteSpace: 'normal', textAlign: 'right' }}>({pick(i.reason_missing, lang)})</span> : null}
                      </>
                    ) : (
                      cell(i.reported_amount, lang)
                    )}
                  </td>
                  <td>{cell(i.amount, lang)}</td>
                  <td className="ct-text ct-wide-only">{localise(i.slotting_assumption, lang, IRRBB_SOURCE_RULES)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </div>
  );
}

// --- the read-outs of the rail ---------------------------------------------------------------------------------------

const BP: BiText = { en: 'bp', es: 'pb' };
const YEARS: BiText = { en: 'years', es: 'años' };
const NA: BiText = { en: formatNumber(null, 'en'), es: formatNumber(null, 'es') };

/** The live read-out of the Calibration section: the three shock sizes of the scenario in focus and where they come from. */
export function CalibrationReadout({ sel }: { sel: C14Sel | null }) {
  const s = scenarioFor(sel);
  const z = s?.shock_size ?? null;
  const hint = (en: string, es: string): BiText => ({ en, es });
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'The shock sizes', es: 'Los tamaños de choque' }}
      items={[
        { label: { en: 'Parallel', es: 'Paralelo' }, value: z?.parallel_bp ?? null, unit: BP, format: { decimals: 0 }, hint: hint('The size of the two parallel shocks.', 'El tamaño de los dos choques paralelos.') },
        { label: { en: 'Short rates', es: 'Tasas cortas' }, value: z?.short_bp ?? null, unit: BP, format: { decimals: 0 }, hint: hint('The size of the short-rate shocks, and of the short leg of the steepener and the flattener.', 'El tamaño de los choques de tasas cortas y del tramo corto del empinamiento y el aplanamiento.') },
        { label: { en: 'Long rates', es: 'Tasas largas' }, value: z?.long_bp ?? null, unit: BP, format: { decimals: 0 }, hint: hint('The size of the long leg of the steepener and the flattener.', 'El tamaño del tramo largo del empinamiento y el aplanamiento.') },
        { label: { en: 'Source', es: 'Fuente' }, text: z ? text(ORIGIN_TEXT, z.origin) : NA, hint: hint('The table the sizes are taken from.', 'La tabla de la que se toman los tamaños.') },
      ]}
    />
  );
}

/** The live read-out of the NMD section: the deposit assumption in force and what it does to the risk measure. */
export function NmdReadout({ sel }: { sel: C14Sel | null }) {
  const o = outputsOf(sel);
  const s = scenarioFor(sel);
  const behavioural = sel?.nmd === 'behavioural';
  const notUsed: BiText = { en: 'not used', es: 'no se usa' };
  const risk = o ? amount(o, s?.eve_risk_measure ?? null) : { value: null, unit: NA, format: { digits: 4 } };
  const capped = o ? o.nmd_segments.filter((g) => g.cap_applied).length : null;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'The deposit assumption', es: 'El supuesto de depósitos' }}
      items={[
        behavioural
          ? { label: { en: 'Core share', es: 'Parte estable' }, value: o?.assumptions.nmd_core_share.value ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'The balance-weighted share of non-maturity deposits that is treated as stable, after the caps.', es: 'La parte de los depósitos sin vencimiento tratada como estable, ponderada por saldo, después de los topes.' } }
          : { label: { en: 'Core share', es: 'Parte estable' }, text: notUsed, hint: { en: 'Every non-maturity deposit sits in the overnight bucket, so no core share is used.', es: 'Todo depósito sin vencimiento está en el tramo a la vista, así que no se usa parte estable.' } },
        behavioural
          ? { label: { en: 'Core maturity', es: 'Plazo estable' }, value: o?.assumptions.nmd_core_maturity_years.value ?? null, unit: YEARS, format: { digits: 4 }, hint: { en: 'The balance-weighted average maturity assigned to the stable part, after the caps.', es: 'El plazo promedio ponderado por saldo asignado a la parte estable, después de los topes.' } }
          : { label: { en: 'Core maturity', es: 'Plazo estable' }, text: notUsed, hint: { en: 'Every non-maturity deposit sits in the overnight bucket.', es: 'Todo depósito sin vencimiento está en el tramo a la vista.' } },
        behavioural
          ? { label: { en: 'Caps that bit', es: 'Topes aplicados' }, value: capped, unitless: true, format: { decimals: 0 }, hint: { en: 'How many deposit categories asked for more than the supervisory cap allows.', es: 'Cuántas categorías de depósitos pidieron más de lo que permite el tope supervisor.' } }
          : { label: { en: 'Caps that bit', es: 'Topes aplicados' }, text: notUsed, hint: { en: 'The caps limit the behavioural assumption only.', es: 'Los topes limitan solo el supuesto conductual.' } },
        { label: { en: 'EVE risk measure', es: 'Medida de riesgo EVE' }, value: risk.value, unit: risk.unit, format: risk.format, hint: { en: 'The largest loss over the six shocks, under this assumption (SRP31.129).', es: 'La mayor pérdida entre los seis choques, bajo este supuesto (SRP31.129).' } },
      ]}
    />
  );
}

/** The live read-out of the Shock section: the loss, its share of Tier 1, the floored buckets and, for a parallel shock, the NII. */
export function ShockReadout({ sel }: { sel: C14Sel | null }) {
  const o = outputsOf(sel);
  const r = shockOf(scenarioFor(sel), sel?.shock ?? '');
  const eve = o ? amount(o, r?.delta_eve ?? null) : { value: null, unit: NA, format: { digits: 4 } };
  const nii = o ? amount(o, r?.delta_nii ?? null) : { value: null, unit: NA, format: { digits: 4 } };
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel ? { en: SHOCK_TEXT[sel.shock]?.en ?? sel.shock, es: SHOCK_TEXT[sel.shock]?.es ?? sel.shock } : { en: 'The shock', es: 'El choque' }}
      items={[
        { label: { en: 'Delta EVE', es: 'Delta EVE' }, value: eve.value, unit: eve.unit, format: eve.format, hint: { en: 'Base EVE minus shocked EVE: positive is a loss.', es: 'EVE base menos EVE con choque: positivo es una pérdida.' } },
        { label: { en: 'Share of Tier 1', es: 'Parte del capital N1' }, value: r?.delta_eve_share_tier1 ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'Delta EVE over Tier 1 capital; the outlier test compares the largest with 15 percent.', es: 'Delta EVE sobre el capital de nivel 1; la prueba de valor atípico compara el mayor con 15 por ciento.' } },
        { label: { en: 'Floored buckets', es: 'Tramos con piso' }, value: r ? r.floor_bound_buckets.length : null, unitless: true, format: { decimals: 0 }, hint: { en: 'How many of the 19 buckets have the post-shock floor binding.', es: 'En cuántos de los 19 tramos el piso posterior al choque es el que rige.' } },
        { label: { en: 'Delta NII', es: 'Delta NII' }, value: nii.value, unit: nii.unit, format: nii.format, hint: { en: 'The NII loss over twelve months; the standard gives it for the two parallel shocks only.', es: 'La pérdida de NII a doce meses; la norma la da solo para los dos choques paralelos.' } },
      ]}
    />
  );
}

/** The live read-out of the Segment section: the replicating portfolio of the deposit category in focus. */
export function SegmentReadout({ sel }: { sel: C14Sel | null }) {
  const o = outputsOf(sel);
  const fit = sel ? fitOf(sel) : null;
  const m = sel ? nmdModelOf(fit, sel.category, o?.valuation_date) : null;
  const pctItem = (label: BiText, value: number | null, hint: BiText) => ({ label, value, unitless: true as const, format: { percent: true, decimals: 2 }, hint });
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel ? text(CATEGORY_TEXT, sel.category) : { en: 'The deposit category', es: 'La categoría de depósitos' }}
      items={[
        { label: { en: 'Implied maturity', es: 'Plazo implícito' }, value: m?.weighted_average_maturity_years ?? null, unit: YEARS, format: { digits: 4 }, hint: { en: 'The weighted average maturity of the replicating portfolio: half the maturity of each rolling tranche.', es: 'El plazo promedio ponderado de la cartera replicante: la mitad del plazo de cada tramo rodante.' } },
        pctItem({ en: 'Beta up', es: 'Beta al alza' }, m?.deposit_beta.up ?? null, { en: 'The share of a rise in the market rate that reaches the client rate.', es: 'La parte de un alza de la tasa de mercado que llega a la tasa del cliente.' }),
        pctItem({ en: 'Beta down', es: 'Beta a la baja' }, m?.deposit_beta.down ?? null, { en: 'The share of a fall in the market rate that reaches the client rate.', es: 'La parte de una baja de la tasa de mercado que llega a la tasa del cliente.' }),
        pctItem({ en: 'Margin volatility', es: 'Volatilidad del margen' }, m?.margin_volatility ?? null, { en: 'The volatility of the margin the replication minimises; not available when the window is too short.', es: 'La volatilidad del margen que minimiza la réplica; no disponible cuando la ventana es muy corta.' }),
      ]}
    />
  );
}

export { axisOf, categoriesOf, CALIBRATION_TEXT, CATEGORY_TEXT, NMD_LONG, NMD_TEXT, SHOCK_TEXT };
