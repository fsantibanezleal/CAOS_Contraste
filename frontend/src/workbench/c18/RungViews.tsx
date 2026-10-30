// C18's state-of-the-art stress rungs (plan S-2, tier sota), beside the OLS satellites: the VAR conditional forecast of the charge-off
// rates and the growth-at-risk quantile satellite, each back-cast through 2008 to 2009 and 2020 on data that ends before the episode.
// Nothing here computes a statistic: the forecasts, the quantiles, the errors, the sign checks and the counts are the bake's, read from
// the details of the two model records of the models artifact. The views find, name and draw; a result that does not improve on the
// OLS satellite is drawn and written like one that does.
import { Fragment } from 'react';
import { PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable } from '../c06/format';
import { useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { Defs, UnavailableCard } from './C18Common';
import { LOAN_ORDER, LOAN_TEXT, REGRESSOR_TEXT, text, type C18Sel } from './selection';
import { quarterText } from './StressViews';

type Lang = 'en' | 'es';
type Bi = { en: string; es: string };

export const VAR_MODEL_ID = 'c18-var-conditional-forecast';
export const GAR_MODEL_ID = 'c18-growth-at-risk';

interface SignCheck { wrong_signs: number; offending: string[]; light: string }
interface Peak { rmse: number; peak_predicted: number; peak_predicted_quarter: string; peak_realised: number; peak_realised_quarter: string; peak_timing_error_quarters: number; light: string }
export interface VarRow {
  fed_loan_type: string;
  link: string;
  fit_window: { start: string; end: string };
  n_obs: number;
  coefficients: Array<{ name: string; estimate: number; std_error: number; expected_sign: string }>;
  sign_check: SignCheck;
  full_conditioning_gap_to_ols: number;
  quarters: Array<{ quarter_end: string; var: number; ols: number; realised: number; unemployment_var: number; unemployment_realised: number }>;
  metrics: { var: Peak; ols: Peak; rmse_ratio_var_over_ols: number };
  closer: 'var' | 'ols' | 'tie';
}
export interface VarWindow { window_id: string; label: Bi; fit_end: string; start: string; end: string; per_loan_type: VarRow[] }
export interface VarDetails {
  tier: string;
  statement: Bi;
  acceptance: { leak_free: boolean; complete: boolean; met: boolean; var_wrong_signs: number; var_sign_checks: number; gar_wrong_signs: number; gar_sign_checks: number };
  var: { lags: number; windows: VarWindow[]; summary: Array<{ window_id: string; loan_types: number; var_closer: number; ols_closer: number; sign_checks_red: number }> };
}
export interface GarWindow {
  window_id: string;
  fit_end: string;
  train_origins: { first: string; last: string; n: number };
  coefficients: Array<{ tau: number; terms: Array<{ name: string; estimate: number; expected_sign: string }>; sign_check: SignCheck }>;
  unconditional_quantiles: number[];
  origins: Array<{ origin: string; target_end: string; realised: number; quantiles: number[] }>;
  coverage: Array<{ tau: number; hits: number; n: number; rate: number }>;
  pinball: Array<{ tau: number; conditional: number; unconditional: number; ratio: number }>;
  mean_pinball_ratio: number;
  crossing_origins: number;
  skewed_t_at_first_origin: { status: string; mu?: number; sigma?: number; alpha?: number; nu?: number; distance?: number; reason?: string };
  first_origin: { origin: string; realised: number; growth_at_risk_5: number; below_growth_at_risk: boolean };
}
export interface GarDetails {
  tier: string;
  growth_at_risk: { horizon_quarters: number; taus: number[]; windows: GarWindow[]; summary: Array<{ window_id: string; origins: number; mean_pinball_ratio: number; better_than_unconditional: boolean }> };
}

interface ModelRecord { id: string; title: Bi; short_title: Bi; details?: unknown }

/** The details of a model record of the models artifact, or null when the artifact carries none (an older document). */
export function detailsOf<T>(sel: C18Sel | null, id: string): { record: ModelRecord; details: T } | null {
  const models = (sel?.data.models as unknown as { model?: ModelRecord[] } | undefined)?.model;
  const record = models?.find((m) => m.id === id);
  return record?.details ? { record, details: record.details as T } : null;
}

const RATE = (v: number | null | undefined, lang: Lang) => formatNumber(v !== null && v !== undefined && Math.abs(v) < 5e-6 ? 0 : v, lang, { percent: true, decimals: 3 });
const GROWTH = (v: number | null | undefined, lang: Lang) => formatNumber(v, lang, { decimals: 2 });
const RATIO = (v: number | null | undefined, lang: Lang) => formatNumber(v, lang, { decimals: 2 });
const COEF = (v: number | null | undefined, lang: Lang) => formatNumber(v, lang, { digits: 3 });

const SIGN_TEXT: Record<string, Bi> = {
  positive: { en: 'positive', es: 'positivo' },
  negative: { en: 'negative', es: 'negativo' },
  none: { en: 'none', es: 'ninguno' },
};
const LIGHT_TEXT: Record<string, Bi> = {
  green: { en: 'green', es: 'verde' },
  amber: { en: 'amber', es: 'ámbar' },
  red: { en: 'red', es: 'rojo' },
  not_evaluated: { en: 'not evaluated', es: 'no evaluada' },
  error: { en: 'error', es: 'error' },
};
const CLOSER_TEXT: Record<string, Bi> = {
  var: { en: 'VAR', es: 'VAR' },
  ols: { en: 'OLS satellite', es: 'Satélite MCO' },
  tie: { en: 'Tie', es: 'Empate' },
};
const VAR_TERM: Record<string, Bi> = {
  intercept: { en: 'Intercept', es: 'Constante' },
  ar_1: { en: 'Own rate, one quarter back', es: 'Tasa propia, un trimestre atrás' },
  real_gdp_growth_lag1: { en: 'Real GDP growth, one quarter back', es: 'Crecimiento del PIB real, un trimestre atrás' },
  unemployment_rate_lag1: { en: 'Unemployment rate, one quarter back', es: 'Tasa de desempleo, un trimestre atrás' },
};
const GAR_TERM: Record<string, Bi> = {
  intercept: { en: 'Intercept', es: 'Constante' },
  real_gdp_growth: REGRESSOR_TEXT.real_gdp_growth ?? { en: 'Real GDP growth', es: 'Crecimiento del PIB real' },
  term_spread: { en: 'Term spread (10-year Treasury less prime)', es: 'Pendiente (Tesoro a 10 años menos tasa preferencial)' },
};
const NOT_THERE: BiText = {
  en: 'Not available: the models artifact carries no record of this rung.',
  es: 'No disponible: el artefacto de modelos no trae el registro de este peldaño.',
};

/** Two episodes on one axis: the series of each window one after the other, a gap of one empty position between them. */
export function joinWindows(parts: number[][]): Array<number | null> {
  const out: Array<number | null> = [];
  parts.forEach((p, i) => {
    if (i > 0) out.push(null);
    out.push(...p);
  });
  return out;
}

const sentence = (b: Bi, lang: Lang) => pick(b, lang);

/** The VAR conditional forecast beside the OLS satellite for the loan type in focus, in both episodes. */
export function VarRungView({ sel }: { sel: C18Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const title: BiText = { en: 'The VAR conditional forecast beside the OLS satellite', es: 'El pronóstico condicional VAR junto al satélite MCO' };
  if (!sel) return <Pending />;
  const found = detailsOf<VarDetails>(sel, VAR_MODEL_ID);
  if (!found) return <UnavailableCard sel={sel} title={title} reason={NOT_THERE} />;
  const { details } = found;
  const windows = details.var.windows;
  const rows = windows.map((w) => w.per_loan_type.find((r) => r.fed_loan_type === sel.loan));
  if (rows.some((r) => !r)) return <UnavailableCard sel={sel} title={title} reason={{ en: 'Not available: the record has no back-cast for this loan type.', es: 'No disponible: el registro no trae prueba retrospectiva para este tipo de préstamo.' }} />;
  const per = rows as VarRow[];
  const loanName = text(LOAN_TEXT, sel.loan);
  const n = per.map((r) => r.quarters.length);
  const markAt = (i: number) => 1 + n.slice(0, i).reduce((a, b) => a + b + 1, 0);
  const axisLen = n.reduce((a, b) => a + b, 0) + n.length - 1;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: `${pick(loanName, 'en')}. A VAR of real GDP growth, unemployment and the linked charge-off rate, one lag, fitted on data that ends before each episode and given only the realised GDP growth path: unemployment and the rate respond through the system. The OLS satellite is refitted on the same span and fed both realised macro paths. ${sentence(details.statement, 'en')}`,
          es: `${pick(loanName, 'es')}. Un VAR del crecimiento del PIB real, el desempleo y la tasa de castigo transformada, un rezago, ajustado con datos que terminan antes de cada episodio y dado solo el camino realizado del crecimiento del PIB: el desempleo y la tasa responden a través del sistema. El satélite MCO se reajusta con el mismo tramo y recibe los dos caminos macro realizados. ${sentence(details.statement, 'es')}`,
        }}
      >
        <ChartOverTable
          chartMin="17rem"
          chart={
            <UPlotChart
              height="fill"
              x={{ values: Array.from({ length: axisLen }, (_, i) => i + 1), label: { en: 'Quarter of the episodes, 2008 to 2009 first, then 2020 to 2025', es: 'Trimestre de los episodios, primero 2008 a 2009, luego 2020 a 2025' }, format: { decimals: 0 } }}
              y={{ label: { en: 'Charge-off rate, signed', es: 'Tasa de castigo, con signo' }, format: { percent: true, decimals: 2 } }}
              series={[
                { label: { en: 'OLS satellite', es: 'Satélite MCO' }, values: joinWindows(per.map((r) => r.quarters.map((q) => q.ols))), color: '--color-accent', width: 2.2 },
                { label: { en: 'VAR conditional forecast', es: 'Pronóstico condicional VAR' }, values: joinWindows(per.map((r) => r.quarters.map((q) => q.var))), color: '--color-good', width: 2.6 },
                { label: { en: 'Realised', es: 'Realizada' }, values: joinWindows(per.map((r) => r.quarters.map((q) => q.realised))), color: '--color-bad', width: 2.2, dash: [5, 3] },
              ]}
              yMarks={[{ y: 0, label: { en: 'Zero: below it a net recovery', es: 'Cero: bajo él, una recuperación neta' }, tone: 'neutral' }]}
              marks={windows.map((w, i) => ({ x: markAt(i), label: { en: `${w.label.en.split(',')[0]} starts`, es: `${w.label.es.split(',')[0]} comienza` } }))}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c18-var-windows" data-loan={sel.loan}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Episode', es: 'Episodio' }, lang)}</th>
                <th>{pick({ en: 'Error of the OLS satellite', es: 'Error del satélite MCO' }, lang)}</th>
                <th>{pick({ en: 'Error of the VAR', es: 'Error del VAR' }, lang)}</th>
                <th>{pick({ en: 'VAR over OLS', es: 'VAR sobre MCO' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Closer to the realised rates', es: 'Más cerca de lo realizado' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Signs of the VAR', es: 'Signos del VAR' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {windows.map((w, i) => (
                <tr key={w.window_id} data-window={w.window_id} data-closer={per[i].closer}>
                  <td className="ct-text">{pick(w.label, lang)}</td>
                  <td>{RATE(per[i].metrics.ols.rmse, lang)}</td>
                  <td>{RATE(per[i].metrics.var.rmse, lang)}</td>
                  <td>{RATIO(per[i].metrics.rmse_ratio_var_over_ols, lang)}</td>
                  <td className="ct-text">{pick(text(CLOSER_TEXT, per[i].closer), lang)}</td>
                  <td className="ct-text">{`${per[i].sign_check.wrong_signs} ${pick({ en: 'wrong of', es: 'erróneos de' }, lang)} ${per[i].coefficients.length} (${pick(text(LIGHT_TEXT, per[i].sign_check.light), lang)})`}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3 className="ct-sub">{pick({ en: 'Which loan types the VAR is closer for', es: 'Para qué tipos de préstamo el VAR queda más cerca' }, lang)}</h3>
          <table className="caos-table ct-wrap-head" data-table="c18-var-summary">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Episode', es: 'Episodio' }, lang)}</th>
                {LOAN_ORDER.map((l) => (
                  <th key={l}>{pick(text(LOAN_TEXT, l), lang)}</th>
                ))}
                <th>{pick({ en: 'VAR closer', es: 'VAR más cerca' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {windows.map((w, i) => (
                <tr key={w.window_id} data-window={w.window_id}>
                  <td className="ct-text">{pick(w.label, lang)}</td>
                  {LOAN_ORDER.map((l) => {
                    const r = w.per_loan_type.find((x) => x.fed_loan_type === l);
                    return <td key={l} data-loan={l} data-closer={r?.closer}>{r ? `${RATIO(r.metrics.rmse_ratio_var_over_ols, lang)} ${pick(text(CLOSER_TEXT, r.closer), lang)}` : formatNumber(null, lang)}</td>;
                  })}
                  <td>{`${formatNumber(details.var.summary[i].var_closer, lang, { decimals: 0 })} ${pick({ en: 'of', es: 'de' }, lang)} ${formatNumber(details.var.summary[i].loan_types, lang, { decimals: 0 })}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3 className="ct-sub">{pick({ en: 'The rate equation of the VAR and its expected signs', es: 'La ecuación de la tasa del VAR y sus signos esperados' }, lang)}</h3>
          <table className="caos-table ct-wrap-head" data-table="c18-var-coefficients" data-loan={sel.loan}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Term', es: 'Término' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Expected sign', es: 'Signo esperado' }, lang)}</th>
                {windows.map((w) => (
                  <th key={w.window_id}>{`${pick({ en: 'Fitted to', es: 'Ajustado hasta' }, lang)} ${quarterText(w.fit_end, lang)}`}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {per[0].coefficients.map((c, k) => (
                <tr key={c.name} data-coefficient={c.name}>
                  <td className="ct-text">{pick(text(VAR_TERM, c.name), lang)}</td>
                  <td className="ct-text">{pick(text(SIGN_TEXT, c.expected_sign), lang)}</td>
                  {per.map((r, i) => (
                    <td key={windows[i].window_id} data-wrong={String(r.sign_check.offending.includes(c.name))}>{`${COEF(r.coefficients[k].estimate, lang)} (${COEF(r.coefficients[k].std_error, lang)})`}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <Defs data-table="c18-var-checks">
            <dt>{pick({ en: 'Given both macro paths', es: 'Dados los dos caminos macro' }, lang)}</dt>
            <dd>{pick({ en: 'The conditional forecast of a one-lag VAR is the OLS satellite itself: the largest gap in the committed run is below one billionth, so that form adds no model and is not drawn', es: 'El pronóstico condicional de un VAR de un rezago es el propio satélite MCO: la mayor brecha de la corrida confirmada es menor que una milmillonésima, así que esa forma no agrega un modelo y no se dibuja' }, lang)}</dd>
            <dt>{pick({ en: 'Sign checks', es: 'Chequeos de signo' }, lang)}</dt>
            <dd>{`${details.acceptance.var_wrong_signs} ${pick({ en: 'of', es: 'de' }, lang)} ${details.acceptance.var_sign_checks} ${pick({ en: 'VAR fits carry a coefficient of the wrong sign; the expected signs were declared before the fit', es: 'ajustes VAR traen un coeficiente de signo erróneo; los signos esperados se declararon antes del ajuste' }, lang)}`}</dd>
            <dt>{pick({ en: 'Fit', es: 'Ajuste' }, lang)}</dt>
            <dd>{`${quarterText(per[0].fit_window.start, lang)} ${pick({ en: 'to', es: 'a' }, lang)} ${quarterText(per[0].fit_window.end, lang)}, ${per[0].n_obs} ${pick({ en: 'quarters', es: 'trimestres' }, lang)}; ${quarterText(per[1].fit_window.start, lang)} ${pick({ en: 'to', es: 'a' }, lang)} ${quarterText(per[1].fit_window.end, lang)}, ${per[1].n_obs} ${pick({ en: 'quarters', es: 'trimestres' }, lang)}`}</dd>
          </Defs>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The growth-at-risk quantiles against the realised four-quarter growth, on the rolling origins of both episodes. */
export function GarRungView({ sel }: { sel: C18Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const title: BiText = { en: 'Growth-at-risk quantiles against the realised growth', es: 'Cuantiles de crecimiento en riesgo frente al crecimiento realizado' };
  if (!sel) return <Pending />;
  const found = detailsOf<GarDetails>(sel, GAR_MODEL_ID);
  const label = detailsOf<VarDetails>(sel, VAR_MODEL_ID);
  if (!found || !label) return <UnavailableCard sel={sel} title={title} reason={NOT_THERE} />;
  const g = found.details.growth_at_risk;
  const labels = new Map(label.details.var.windows.map((w) => [w.window_id, w.label]));
  const taus = g.taus;
  const k05 = taus.indexOf(0.05);
  const k50 = taus.indexOf(0.5);
  const k95 = taus.indexOf(0.95);
  const n = g.windows.map((w) => w.origins.length);
  const markAt = (i: number) => 1 + n.slice(0, i).reduce((a, b) => a + b + 1, 0);
  const axisLen = n.reduce((a, b) => a + b, 0) + n.length - 1;
  const q = (w: GarWindow, k: number) => w.origins.map((o) => o.quantiles[k]);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'The average real GDP growth over the next four quarters, by quantile regression on the current growth and the term spread (the 10-year Treasury yield less the prime rate; the Chicago Fed financial conditions index of the original is not one of the case\'s agency series). The coefficients are fixed at the end of each fit span and every origin from there on is scored against what happened, beside the unconditional quantiles of the same span. Growth is annualised, in percent.',
          es: 'El crecimiento promedio del PIB real en los cuatro trimestres siguientes, por regresión cuantílica sobre el crecimiento actual y la pendiente de la curva (el rendimiento del Tesoro a 10 años menos la tasa preferencial; el índice de condiciones financieras de la Fed de Chicago del original no es una de las series de agencia del caso). Los coeficientes se fijan al final de cada tramo de ajuste y cada origen desde ahí se evalúa contra lo ocurrido, junto a los cuantiles incondicionales del mismo tramo. El crecimiento está anualizado, en por ciento.',
        }}
      >
        <ChartOverTable
          chartMin="17rem"
          chart={
            <UPlotChart
              height="fill"
              x={{ values: Array.from({ length: axisLen }, (_, i) => i + 1), label: { en: 'Origin of the episodes, 2007 Q4 first, then 2019 Q4', es: 'Origen de los episodios, primero 2007 T4, luego 2019 T4' }, format: { decimals: 0 } }}
              y={{ label: { en: 'Four-quarter average growth (percent, annualised)', es: 'Crecimiento promedio a cuatro trimestres (por ciento, anualizado)' }, format: { decimals: 1 } }}
              series={[
                { label: { en: 'Quantile 5 percent', es: 'Cuantil 5 por ciento' }, values: joinWindows(g.windows.map((w) => q(w, k05))), color: '--color-accent', width: 2.2, dash: [2, 3] },
                { label: { en: 'Median', es: 'Mediana' }, values: joinWindows(g.windows.map((w) => q(w, k50))), color: '--color-accent', width: 2.6 },
                { label: { en: 'Quantile 95 percent', es: 'Cuantil 95 por ciento' }, values: joinWindows(g.windows.map((w) => q(w, k95))), color: '--color-accent', width: 2.2, dash: [2, 3] },
                { label: { en: 'Realised', es: 'Realizado' }, values: joinWindows(g.windows.map((w) => w.origins.map((o) => o.realised))), color: '--color-bad', width: 2.4 },
              ]}
              yMarks={[{ y: 0, label: { en: 'Zero growth', es: 'Crecimiento cero' }, tone: 'neutral' }]}
              marks={g.windows.map((w, i) => ({ x: markAt(i), label: { en: `${pick(labels.get(w.window_id) ?? { en: w.window_id, es: w.window_id }, 'en').split(',')[0]}: first origin`, es: `${pick(labels.get(w.window_id) ?? { en: w.window_id, es: w.window_id }, 'es').split(',')[0]}: primer origen` } }))}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c18-gar-scores">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Episode', es: 'Episodio' }, lang)}</th>
                <th>{pick({ en: 'Origins', es: 'Orígenes' }, lang)}</th>
                {taus.map((t) => (
                  <th key={t}>{`${pick({ en: 'Below quantile', es: 'Bajo el cuantil' }, lang)} ${formatNumber(t, lang, { percent: true, decimals: 0 })}`}</th>
                ))}
                <th>{pick({ en: 'Pinball loss over the unconditional quantile', es: 'Pérdida pinball sobre el cuantil incondicional' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {g.windows.map((w) => (
                <tr key={w.window_id} data-window={w.window_id} data-pinball-ratio={w.mean_pinball_ratio}>
                  <td className="ct-text">{pick(labels.get(w.window_id) ?? { en: w.window_id, es: w.window_id }, lang)}</td>
                  <td>{formatNumber(w.origins.length, lang, { decimals: 0 })}</td>
                  {w.coverage.map((c) => (
                    <td key={c.tau} data-tau={c.tau}>{`${formatNumber(c.hits, lang, { decimals: 0 })} ${pick({ en: 'of', es: 'de' }, lang)} ${formatNumber(c.n, lang, { decimals: 0 })}`}</td>
                  ))}
                  <td>{RATIO(w.mean_pinball_ratio, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3 className="ct-sub">{pick({ en: 'The quantile coefficients and their expected signs', es: 'Los coeficientes cuantílicos y sus signos esperados' }, lang)}</h3>
          <table className="caos-table ct-wrap-head" data-table="c18-gar-coefficients">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Episode', es: 'Episodio' }, lang)}</th>
                <th>{pick({ en: 'Quantile', es: 'Cuantil' }, lang)}</th>
                {['intercept', 'real_gdp_growth', 'term_spread'].map((t) => (
                  <th key={t}>{pick(text(GAR_TERM, t), lang)}</th>
                ))}
                <th className="ct-text">{pick({ en: 'Signs', es: 'Signos' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {g.windows.flatMap((w) =>
                w.coefficients.map((c) => (
                  <tr key={`${w.window_id}-${c.tau}`} data-window={w.window_id} data-tau={c.tau}>
                    <td className="ct-text">{pick(labels.get(w.window_id) ?? { en: w.window_id, es: w.window_id }, lang)}</td>
                    <td>{formatNumber(c.tau, lang, { percent: true, decimals: 0 })}</td>
                    {c.terms.map((t) => (
                      <td key={t.name} data-wrong={String(c.sign_check.offending.includes(t.name))}>{COEF(t.estimate, lang)}</td>
                    ))}
                    <td className="ct-text">{`${c.sign_check.wrong_signs} ${pick({ en: 'wrong of', es: 'erróneos de' }, lang)} ${c.terms.length} (${pick(text(LIGHT_TEXT, c.sign_check.light), lang)})`}</td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
          <Defs data-table="c18-gar-first-origin">
            {g.windows.map((w) => (
              <Fragment key={w.window_id}>
                <dt>{pick(labels.get(w.window_id) ?? { en: w.window_id, es: w.window_id }, lang)}</dt>
                <dd data-below={String(w.first_origin.below_growth_at_risk)}>
                  {pick(
                    {
                      en: `At the first origin (${quarterText(w.first_origin.origin, 'en')}) the 5 percent quantile was ${GROWTH(w.first_origin.growth_at_risk_5, 'en')} and the realised four-quarter growth ${GROWTH(w.first_origin.realised, 'en')}: ${w.first_origin.below_growth_at_risk ? 'below it' : 'not below it'}. The skewed t fitted to the five quantiles ${w.skewed_t_at_first_origin.status === 'fitted' ? `has a degrees-of-freedom parameter of ${GROWTH(w.skewed_t_at_first_origin.nu, 'en')}` : 'was not fitted (the engine search did not converge on these quantiles)'}.`,
                      es: `En el primer origen (${quarterText(w.first_origin.origin, 'es')}) el cuantil de 5 por ciento era ${GROWTH(w.first_origin.growth_at_risk_5, 'es')} y el crecimiento realizado a cuatro trimestres ${GROWTH(w.first_origin.realised, 'es')}: ${w.first_origin.below_growth_at_risk ? 'bajo él' : 'no bajo él'}. La t asimétrica ajustada a los cinco cuantiles ${w.skewed_t_at_first_origin.status === 'fitted' ? `tiene un parámetro de grados de libertad de ${GROWTH(w.skewed_t_at_first_origin.nu, 'es')}` : 'no se ajustó (la búsqueda del motor no convergió con estos cuantiles)'}.`,
                    },
                    lang,
                  )}
                </dd>
              </Fragment>
            ))}
          </Defs>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
