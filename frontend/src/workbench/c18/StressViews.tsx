// C18's Stress group: how the scenario reaches the book. The paths as published and as transposed onto the jump-off of Banco
// Andino, the satellite projections of the five Federal Reserve loan types and the three classes of the bank, the back-cast of
// the satellites against the realised (signed) charge-off rates, the severity of each path against the global financial
// crisis, and the expected losses by risk and year. The paths and the satellites are a US-calibrated adaptation and every view
// says so. A realised charge-off rate can be negative (a net recovery): it is drawn and written as it is, never floored.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText, type ShellColorToken } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable } from '../c06/format';
import { useCard, type Bi } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { Defs, NOT_SCENARIO, PCT, UnavailableCard, cell, digits } from './C18Common';
import {
  CLASS_TEXT, LABEL_TEXT, LEVEL_RULE_TEXT, LINK_TEXT, LOAN_ORDER, LOAN_TEXT, MONEY_UNIT, PROVIDER_TEXT, REGRESSOR_TEXT, RISK_ORDER, RISK_TEXT,
  backcastOf, fitOf, outputsOf, satFitOf, text,
  type C18Backcast, type C18Outputs, type C18Sel,
  inSentence, plottedUnit,
} from './selection';
import { unitEs } from './localise';

export { plottedUnit };

type Lang = 'en' | 'es';
/** A quarter end as "2026 Q1" (T1 in Spanish). */
export function quarterText(date: string, lang: Lang): string {
  const [y, m] = date.split('-').map(Number);
  return `${y} ${lang === 'es' ? 'T' : 'Q'}${Math.ceil(m / 3)}`;
}
/** A text that ends as a sentence: one full stop. */
const asSentenceEnd = (s: string): string => (/[.!?]$/.test(s) ? s : `${s}.`);
// a rate under half the last shown decimal is 0, never "-0.000 %" (U16-R3 c19 m11)
const RATE = (v: number | null | undefined, lang: Lang) => formatNumber(v !== null && v !== undefined && Math.abs(v) < 5e-6 ? 0 : v, lang, { percent: true, decimals: 3 });

const COEF_TEXT: Record<string, Bi> = {
  intercept: { en: 'Intercept', es: 'Constante' },
  ar_1: { en: 'Own rate, one quarter back', es: 'Tasa propia, un trimestre atrás' },
};
function coefName(name: string, lang: Lang): string {
  if (COEF_TEXT[name]) return pick(COEF_TEXT[name], lang);
  const m = /^(.*)_lag(\d+)$/.exec(name);
  if (m && REGRESSOR_TEXT[m[1]]) return `${pick(REGRESSOR_TEXT[m[1]], lang)} (${lang === 'es' ? 'rezago' : 'lag'} ${m[2]})`;
  return name;
}
const SIGN_TEXT: Record<string, Bi> = {
  positive: { en: 'positive', es: 'positivo' },
  negative: { en: 'negative', es: 'negativo' },
  none: { en: 'none', es: 'ninguno' },
};

/** The scenario as published and as transposed onto the jump-off of Banco Andino, path by path. */
/** The line of the policy-shock window: its span, then its label; a label that states the span itself is not prefixed by it again
 * (U16-R5 c25 n1: "2031 to 2033: The policy shock acts in 2031 to 2033"). */
export function windowLine(win: { start_year: number; end_year: number; label: BiText }, lang: Lang): string {
  const label = pick(win.label, lang);
  const span = lang === 'en' ? `${win.start_year} to ${win.end_year}` : `${win.start_year} a ${win.end_year}`;
  return label.includes(span) ? label : `${span}: ${label}`;
}

export function PathsView({ sel }: { sel: C18Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The scenario path, published and transposed', es: 'La trayectoria del escenario, publicada y transpuesta' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SCENARIO} />;
  const s = o.scenario;
  const p = s.paths[Math.min(sel.path, s.paths.length - 1)];
  const name = (id: string) => pick(text(REGRESSOR_TEXT, id), lang);
  const jump = p.transposition.target.value;
  const published = p.transposition.source_jump_off.value;
  const marks = [
    { y: jump, label: { en: 'Jump-off of Banco Andino', es: 'Punto de partida de Banco Andino' }, tone: 'neutral' as const },
    ...(published !== jump ? [{ y: published, label: { en: 'Published level at the jump-off', es: 'Nivel publicado en el punto de partida' }, tone: 'warn' as const }] : []),
  ];
  const win = s.policy_shock_window;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: `${pick(s.title, 'en')} (${pick(text(PROVIDER_TEXT, s.provider), 'en')}, vintage ${s.vintage_date}). The line is the path of ${inSentence(name(p.maps_to_regressor))} after the shape of the published path was carried onto the last observed value of the bank; the published values and the levels are in the tables.`,
          es: `${pick(s.title, 'es')} (${pick(text(PROVIDER_TEXT, s.provider), 'es')}, versión ${s.vintage_date}). La línea es la trayectoria de ${inSentence(name(p.maps_to_regressor))} tras llevar la forma de la trayectoria publicada al último valor observado del banco; los valores publicados y los niveles están en las tablas.`,
        }}
      >
        <ChartOverTable
          chartMin="16rem"
          chart={
            <UPlotChart
              height="fill"
              x={{ values: p.transposed.map((_, i) => i + 1), label: { en: `Quarter of the projection (1 is ${quarterText(p.transposed[0].date, 'en')})`, es: `Trimestre de la proyección (1 es ${quarterText(p.transposed[0].date, 'es')})` }, format: { decimals: 0 } }}
              y={{ label: { en: `${name(p.maps_to_regressor)} (${plottedUnit(p).en})`, es: `${name(p.maps_to_regressor)} (${plottedUnit(p).es})` }, format: { digits: 4 } }}
              series={[{ label: { en: 'Transposed onto Banco Andino', es: 'Transpuesta a Banco Andino' }, values: p.transposed.map((q) => q.value), color: '--color-accent', width: 2.8 }]}
              yMarks={marks}
            />
          }
        >
          <p className="ct-note" data-adaptation={s.adaptation_label}>{pick(s.adaptation_statement, lang)}</p>
          {win ? (
            <p className="ct-note" data-window={`${win.start_year}-${win.end_year}`}>{windowLine(win, lang)}</p>
          ) : null}
          <table className="caos-table ct-wrap-head" data-table="c18-paths">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Path', es: 'Trayectoria' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Published unit', es: 'Unidad publicada' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'How the level is built', es: 'Cómo se arma el nivel' }, lang)}</th>
                <th>{pick({ en: 'Published at the jump-off', es: 'Publicado en el punto de partida' }, lang)}</th>
                <th>{pick({ en: 'Jump-off of the bank', es: 'Punto de partida del banco' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'After the published horizon', es: 'Tras el horizonte publicado' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {s.paths.map((q, i) => (
                <tr key={`${q.maps_to_regressor}-${i}`} data-path={i} data-transposition={q.transposition.label} className={i === sel.path ? 'ct-current' : undefined}>
                  <td className="ct-text" title={q.variable}>{name(q.maps_to_regressor)}</td>
                  <td className="ct-text ct-wide-only">{unitEs(q.unit, lang)}</td>
                  <td className="ct-text">{pick(text(LEVEL_RULE_TEXT, q.level_rule.kind), lang)}</td>
                  <td>{formatNumber(q.transposition.source_jump_off.value, lang, { digits: 4 })}</td>
                  <td>{formatNumber(q.transposition.target.value, lang, { digits: 4 })}</td>
                  <td className="ct-text ct-wide-only">{q.transposition.reversion === 'none-within-horizon' ? pick({ en: 'no reversion inside the horizon', es: 'sin reversión dentro del horizonte' }, lang) : pick({ en: 'reverts to the baseline', es: 'revierte a la línea base' }, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head" data-table="c18-path-published">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Published date', es: 'Fecha publicada' }, lang)}</th>
                <th>{pick({ en: 'Published value', es: 'Valor publicado' }, lang)}</th>
                <th>{pick({ en: 'Level', es: 'Nivel' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {p.source.map((v, i) => (
                <tr key={`${v.date}-${i}`}>
                  <td className="ct-text">{quarterText(v.date, lang)}</td>
                  <td>{formatNumber(v.value, lang, { digits: 4 })}</td>
                  <td data-na={p.levels[i] ? undefined : 'true'}>{formatNumber(p.levels[i]?.value ?? null, lang, { digits: 4 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head" data-table="c18-path-transposed">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Quarter', es: 'Trimestre' }, lang)}</th>
                <th>{pick({ en: 'Transposed value', es: 'Valor transpuesto' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {p.transposed.map((v) => (
                <tr key={v.date}>
                  <td className="ct-text">{quarterText(v.date, lang)}</td>
                  <td>{formatNumber(v.value, lang, { digits: 4 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The projected loss rate of each Federal Reserve loan type under the path, and the three classes of the bank built from them. */
/** One colour per loan type, and a dash on the residential line: the default palette drew the commercial and the residential lines in two close blues in the dark theme (U16-R2 b09 m8). */
const LOAN_COLOR: Record<string, ShellColorToken> = {
  'commercial-industrial': '--color-accent',
  'commercial-real-estate': '--color-warn',
  residential: '--color-magenta',
  'credit-cards': '--color-bad',
  'other-consumer': '--color-good',
};

export function SatellitesView({ sel }: { sel: C18Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The satellite projections', es: 'Las proyecciones de los satélites' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SCENARIO} />;
  const sat = o.satellites;
  const first = sat.fed_loan_types[0];
  const q = first?.quarters ?? [];
  const chosen = sat.fed_loan_types.find((f) => f.fed_loan_type === sel.loan) ?? first;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'Each satellite maps the scenario path to the charge-off rate of one Federal Reserve loan type, fitted on 1985 to 2019 or 1991 to 2019. The three classes of Banco Andino are weighted sums of those rates: a US-calibrated adaptation, not Chilean satellites. The loan type in the rail is drawn thicker.',
          es: 'Cada satélite lleva la trayectoria del escenario a la tasa de castigo de un tipo de préstamo de la Reserva Federal, ajustado con 1985 a 2019 o 1991 a 2019. Las tres clases de Banco Andino son sumas ponderadas de esas tasas: una adaptación calibrada en EE. UU., no satélites chilenos. El tipo de préstamo del panel va más grueso.',
        }}
      >
        <ChartOverTable
          chartMin="17rem"
          chart={
            <UPlotChart
              height="fill"
              x={{ values: q.map((_, i) => i + 1), label: { en: `Quarter of the projection (1 is ${q[0] ? quarterText(q[0].quarter_end, 'en') : ''})`, es: `Trimestre de la proyección (1 es ${q[0] ? quarterText(q[0].quarter_end, 'es') : ''})` }, format: { decimals: 0 } }}
              y={{ label: { en: 'Projected charge-off rate', es: 'Tasa de castigo proyectada' }, format: { percent: true, decimals: 2 } }}
              series={sat.fed_loan_types.map((f) => ({ label: text(LOAN_TEXT, f.fed_loan_type), values: f.quarters.map((x) => x.rate), color: LOAN_COLOR[f.fed_loan_type] ?? '--color-fg-subtle', width: f.fed_loan_type === sel.loan ? 3.4 : 1.6, ...(f.fed_loan_type === 'residential' ? { dash: [6, 3] as [number, number] } : {}) }))}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c18-sat-loans">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Federal Reserve loan type', es: 'Tipo de préstamo de la Reserva Federal' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Link', es: 'Enlace' }, lang)}</th>
                <th>{pick({ en: 'First quarter', es: 'Primer trimestre' }, lang)}</th>
                <th>{pick({ en: 'Last quarter', es: 'Último trimestre' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {sat.fed_loan_types.map((f) => (
                <tr key={f.fed_loan_type} data-loan={f.fed_loan_type} className={f.fed_loan_type === sel.loan ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(text(LOAN_TEXT, f.fed_loan_type), lang)}</td>
                  <td className="ct-text">{pick(text(LINK_TEXT, f.link), lang)}</td>
                  <td>{RATE(f.quarters[0]?.rate, lang)}</td>
                  <td>{RATE(f.quarters[f.quarters.length - 1]?.rate, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head" data-table="c18-sat-classes">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Class of Banco Andino', es: 'Clase de Banco Andino' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Built from', es: 'Armada con' }, lang)}</th>
                <th>{pick({ en: 'Weights', es: 'Ponderaciones' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: `Exposure (${pick(MONEY_UNIT, 'en')})`, es: `Exposición (${pick(MONEY_UNIT, 'es')})` }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Status', es: 'Estado' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {sat.banco_andino_classes.map((c) => (
                <tr key={c.banco_andino_class} data-class={c.banco_andino_class}>
                  <td className="ct-text">{pick(text(CLASS_TEXT, c.banco_andino_class), lang)}</td>
                  <td className="ct-text">{c.maps_from.map((f) => pick(text(LOAN_TEXT, f), lang)).join(', ')}</td>
                  <td>{c.weights.map((w) => PCT(w, lang, 0)).join(' / ')}</td>
                  <td className="ct-wide-only">{cell(c.exposure_clp_m, lang)}</td>
                  <td className="ct-text ct-wide-only">{pick(text(LABEL_TEXT, c.label), lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {chosen ? (
            <table className="caos-table ct-wrap-head" data-table="c18-sat-quarters" data-loan={chosen.fed_loan_type}>
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: `Quarters of ${pick(text(LOAN_TEXT, chosen.fed_loan_type), 'en').toLowerCase()}`, es: `Trimestres de ${pick(text(LOAN_TEXT, chosen.fed_loan_type), 'es').toLowerCase()}` }, lang)}</th>
                  <th>{pick({ en: 'Rate', es: 'Tasa' }, lang)}</th>
                  <th>{pick({ en: 'Value on the link', es: 'Valor en el enlace' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {chosen.quarters.map((x) => (
                  <tr key={x.quarter_end}>
                    <td className="ct-text">{quarterText(x.quarter_end, lang)}</td>
                    <td>{RATE(x.rate, lang)}</td>
                    <td>{digits(x.link_value, lang)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/**
 * The peaks the back-cast test judges, drawn on the chart at their quarter and labelled with their rate (U16-R4 c23 M3, rubric
 * law 2: the red test compares the size and the timing of the two peaks, so both are marked); one mark when both peaks fall in
 * the same quarter. The x of a mark is the quarter's position in the window, as the chart's x axis counts it.
 */
export function backcastMarks(b: C18Backcast): Array<{ x: number; label: BiText }> {
  const m = b.metrics;
  const at = (q: string) => b.quarters.findIndex((x) => x.quarter_end === q) + 1;
  const predicted = { en: `Predicted peak ${RATE(m.peak_predicted, 'en')}`, es: `Máximo predicho ${RATE(m.peak_predicted, 'es')}` };
  const realised = { en: `Realised peak ${RATE(m.peak_realised, 'en')}`, es: `Máximo realizado ${RATE(m.peak_realised, 'es')}` };
  const xp = at(m.peak_predicted_quarter);
  const xr = at(m.peak_realised_quarter);
  if (xp > 0 && xp === xr) return [{ x: xp, label: { en: `${predicted.en} · ${realised.en}`, es: `${predicted.es} · ${realised.es}` } }];
  return [...(xp > 0 ? [{ x: xp, label: predicted }] : []), ...(xr > 0 ? [{ x: xr, label: realised }] : [])];
}

/** The satellites, fitted before 2020, predict 2020 to 2025; the realised charge-off rates are drawn as they are, signed. */
export function BackcastView({ sel }: { sel: C18Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The back-cast against the realised rates', es: 'La prueba retrospectiva frente a las tasas realizadas' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SCENARIO} />;
  const b = backcastOf(o, sel.loan);
  if (!b) return <UnavailableCard sel={sel} title={title} reason={{ en: 'Not available: the document has no back-cast for this loan type.', es: 'No disponible: el documento no trae prueba retrospectiva para este tipo de préstamo.' }} />;
  const fit = satFitOf(fitOf(sel), sel.loan);
  const m = b.metrics;
  const loanName = text(LOAN_TEXT, sel.loan);
  const d26 = o.backcast.descriptive_2026;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: `${pick(loanName, 'en')}, link ${pick(text(LINK_TEXT, b.link), 'en')}, fitted on ${quarterText(b.fit_window.start, 'en')} to ${quarterText(b.fit_window.end, 'en')} and scored out of time on 2020 Q1 to 2025 Q4. A realised charge-off rate can be negative, a net recovery: it is drawn below the zero line and never floored. ${pick(o.backcast.statement, 'en')}`,
          es: `${pick(loanName, 'es')}, enlace ${pick(text(LINK_TEXT, b.link), 'es')}, ajustado con ${quarterText(b.fit_window.start, 'es')} a ${quarterText(b.fit_window.end, 'es')} y evaluado fuera de tiempo en 2020 T1 a 2025 T4. Una tasa de castigo realizada puede ser negativa, una recuperación neta: se dibuja bajo la línea de cero y nunca se trunca. ${pick(o.backcast.statement, 'es')}`,
        }}
      >
        <ChartOverTable
          chartMin="17rem"
          chart={
            <UPlotChart
              height="fill"
              x={{ values: b.quarters.map((_, i) => i + 1), label: { en: `Quarter of the window (1 is ${quarterText(b.quarters[0].quarter_end, 'en')})`, es: `Trimestre de la ventana (1 es ${quarterText(b.quarters[0].quarter_end, 'es')})` }, format: { decimals: 0 } }}
              y={{ label: { en: 'Charge-off rate, signed', es: 'Tasa de castigo, con signo' }, format: { percent: true, decimals: 2 } }}
              series={[
                { label: { en: 'Predicted by the satellite', es: 'Predicha por el satélite' }, values: b.quarters.map((x) => x.predicted), color: '--color-accent', width: 2.6 },
                { label: { en: 'Realised', es: 'Realizada' }, values: b.quarters.map((x) => x.realised), color: '--color-bad', width: 2.2, dash: [5, 3] },
              ]}
              yMarks={[{ y: 0, label: { en: 'Zero: below it a net recovery', es: 'Cero: bajo él, una recuperación neta' }, tone: 'neutral' }]}
              marks={backcastMarks(b)}
            />
          }
        >
          <Defs data-table="c18-backcast-metrics">
            <dt>{pick({ en: 'Error of the window', es: 'Error de la ventana' }, lang)}</dt>
            <dd>{RATE(m.rmse, lang)}</dd>
            <dt>{pick({ en: 'Predicted peak', es: 'Máximo predicho' }, lang)}</dt>
            <dd>{`${RATE(m.peak_predicted, lang)} (${quarterText(m.peak_predicted_quarter, lang)})`}</dd>
            <dt>{pick({ en: 'Realised peak', es: 'Máximo realizado' }, lang)}</dt>
            <dd>{`${RATE(m.peak_realised, lang)} (${quarterText(m.peak_realised_quarter, lang)})`}</dd>
            <dt>{pick({ en: 'Timing of the peak', es: 'Desfase del máximo' }, lang)}</dt>
            <dd data-timing={m.peak_timing_error_quarters}>{`${m.peak_timing_error_quarters} ${Math.abs(m.peak_timing_error_quarters) === 1 ? pick({ en: 'quarter', es: 'trimestre' }, lang) : pick({ en: 'quarters', es: 'trimestres' }, lang)} ${pick({ en: '(positive: the model is late)', es: '(positivo: el modelo llega tarde)' }, lang)}`}</dd>
            <dt>{pick({ en: 'Fitted window', es: 'Ventana de ajuste' }, lang)}</dt>
            <dd>{`${quarterText(b.fit_window.start, lang)} ${pick({ en: 'to', es: 'a' }, lang)} ${quarterText(b.fit_window.end, lang)}`}</dd>
            {fit ? (
              <>
                <dt>{pick({ en: 'Quarters fitted', es: 'Trimestres ajustados' }, lang)}</dt>
                <dd>{`${fit.n_obs}; ${pick({ en: 'non-positive quarters in the window', es: 'trimestres no positivos en la ventana' }, lang)}: ${fit.non_positive_quarters_in_window ?? formatNumber(null, lang)}`}</dd>
                <dt>{pick({ en: 'Fit', es: 'Ajuste' }, lang)}</dt>
                <dd>{`R ${pick({ en: 'squared', es: 'cuadrado' }, lang)} ${digits(fit.fit_statistics.r_squared, lang)}; ${pick({ en: 'residual spread', es: 'dispersión residual' }, lang)} ${digits(fit.fit_statistics.residual_sd, lang)}`}</dd>
              </>
            ) : null}
          </Defs>
          {fit ? (
            <table className="caos-table ct-wrap-head" data-table="c18-coefficients" data-loan={sel.loan}>
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Term', es: 'Término' }, lang)}</th>
                  <th>{pick({ en: 'Estimate', es: 'Estimación' }, lang)}</th>
                  <th>{pick({ en: 'Standard error', es: 'Error estándar' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Expected sign', es: 'Signo esperado' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {fit.coefficients.map((c) => (
                  <tr key={c.name} data-coefficient={c.name}>
                    <td className="ct-text" title={c.name}>{coefName(c.name, lang)}</td>
                    <td>{digits(c.estimate, lang)}</td>
                    <td>{digits(c.std_error, lang)}</td>
                    <td className="ct-text">{pick(text(SIGN_TEXT, c.expected_sign), lang)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="ct-note" data-na="true">{`${formatNumber(null, lang)}: ${pick({ en: 'the models artifact carries no fit for this loan type', es: 'el artefacto de modelos no trae el ajuste de este tipo de préstamo' }, lang)}`}</p>
          )}
          <table className="caos-table ct-wrap-head" data-table="c18-backcast" data-fit-start={b.fit_window.start} data-signed-rate="true" data-loan={sel.loan}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Quarter', es: 'Trimestre' }, lang)}</th>
                <th>{pick({ en: 'Predicted', es: 'Predicha' }, lang)}</th>
                <th>{pick({ en: 'Realised', es: 'Realizada' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {b.quarters.map((x) => (
                <tr key={x.quarter_end} data-quarter={x.quarter_end}>
                  <td className="ct-text">{quarterText(x.quarter_end, lang)}</td>
                  <td data-predicted={x.predicted}>{RATE(x.predicted, lang)}</td>
                  <td data-realised={x.realised}>{RATE(x.realised, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3 className="ct-sub">{pick({ en: 'The two quarters of 2026', es: 'Los dos trimestres de 2026' }, lang)}</h3>
          <p className="ct-note">{pick(text(LABEL_TEXT, 'rate-only-descriptive'), lang)}</p>
          <table className="caos-table ct-wrap-head" data-table="c18-descriptive-2026" data-forecast-claim={String(d26[0]?.forecast_claim ?? false)}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Loan type', es: 'Tipo de préstamo' }, lang)}</th>
                {d26.map((d) => (
                  <th key={d.quarter_end}>{quarterText(d.quarter_end, lang)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {LOAN_ORDER.map((l) => (
                <tr key={l} data-loan={l}>
                  <td className="ct-text">{pick(text(LOAN_TEXT, l), lang)}</td>
                  {d26.map((d) => (
                    <td key={d.quarter_end} data-realised={d.realised_rates.find((r) => r.fed_loan_type === l)?.rate}>{RATE(d.realised_rates.find((r) => r.fed_loan_type === l)?.rate ?? null, lang)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/**
 * The bars of the severity chart: each path's peak deviation over the crisis's, and the minimum ratio. A bar carries no note that
 * repeats its own label (U16-R4 c22 m6). is_stress is the scenario's kind (not the baseline); the minimum-ratio rule is judged
 * here, on a stress path only (PR-C18-2).
 */
export function severityBars(o: C18Outputs) {
  const sv = o.severity;
  const severe = (r: (typeof sv.rows)[number]): boolean => r.ratio >= sv.minimum_ratio;
  return [
    ...sv.rows.map((r) => ({ id: r.maps_to_regressor, label: text(REGRESSOR_TEXT, r.maps_to_regressor) as BiText, value: r.ratio, tone: !r.is_stress ? ('neutral' as const) : severe(r) ? ('accent' as const) : ('warn' as const), hint: undefined as BiText | undefined })),
    { id: 'minimum', label: { en: 'Minimum ratio (a convention)', es: 'Razón mínima (una convención)' } as BiText, value: sv.minimum_ratio, tone: 'neutral' as const, hint: undefined as BiText | undefined },
  ];
}

/** How severe each path is against the global financial crisis, and whether it reaches the case's minimum ratio. */
/** The severity chart's title, which its summary and data table print: "deviation", as the table under it (U16-R5 c24 n3). */
export const SEVERITY_TITLE: BiText = { en: 'Path peak deviation over the crisis peak deviation', es: 'Desviación máxima de la trayectoria sobre la de la crisis' };

export function SeverityView({ sel }: { sel: C18Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'Severity of each path against history', es: 'Severidad de cada trayectoria frente a la historia' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SCENARIO} />;
  const sv = o.severity;
  const severe = (r: (typeof sv.rows)[number]): boolean => r.ratio >= sv.minimum_ratio;
  const bars = severityBars(o);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          // the crisis in quarters, as the definition below it, and the caption a sentence (U16-R5 c25 n2)
          en: `The peak deviation of each path over the peak deviation of the global financial crisis (${quarterText(sv.reference_episode.start, 'en')} to ${quarterText(sv.reference_episode.end, 'en')}) for the same variable. A stress path below the minimum ratio, a convention of the case, is not severe enough; a baseline path is not judged. ${asSentenceEnd(pick(sv.reference_episode.source, 'en'))}`,
          es: `La desviación máxima de cada trayectoria sobre la desviación máxima de la crisis financiera global (${quarterText(sv.reference_episode.start, 'es')} a ${quarterText(sv.reference_episode.end, 'es')}) para la misma variable. Una trayectoria de estrés bajo la razón mínima, una convención del caso, no es lo bastante severa; una trayectoria base no se juzga. ${asSentenceEnd(pick(sv.reference_episode.source, 'es'))}`,
        }}
      >
        <ChartOverTable
          chartMin={`${bars.length * 2.3 + 4}rem`}
          chart={
            <BarChart
              title={SEVERITY_TITLE}
              height="fill"
              orientation="horizontal"
              data={bars}
              axis={{ label: { en: 'Ratio of the peak deviations', es: 'Razón de las desviaciones máximas' }, format: { digits: 4 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c18-severity">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Variable', es: 'Variable' }, lang)}</th>
                <th>{pick({ en: 'Peak deviation of the path', es: 'Desviación máxima de la trayectoria' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Quarter', es: 'Trimestre' }, lang)}</th>
                <th>{pick({ en: 'Peak deviation of the crisis', es: 'Desviación máxima de la crisis' }, lang)}</th>
                <th>{pick({ en: 'Ratio', es: 'Razón' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Severe enough?', es: '¿Lo bastante severa?' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {sv.rows.map((r) => (
                <tr key={r.maps_to_regressor} data-severity={r.maps_to_regressor} data-stress={String(r.is_stress)} data-severe={r.is_stress ? String(severe(r)) : 'not-judged'}>
                  <td className="ct-text" title={r.variable}>{`${pick(text(REGRESSOR_TEXT, r.maps_to_regressor), lang)} (${unitEs(r.unit, lang)})`}</td>
                  <td>{formatNumber(r.path_peak_deviation, lang, { digits: 4 })}</td>
                  <td className="ct-wide-only">{quarterText(r.path_peak_quarter, lang)}</td>
                  <td>{formatNumber(r.history_peak_deviation, lang, { digits: 4 })}</td>
                  <td>{formatNumber(r.ratio, lang, { digits: 4 })}</td>
                  <td className="ct-text">{!r.is_stress ? pick({ en: 'not judged (baseline)', es: 'no se juzga (escenario base)' }, lang) : severe(r) ? pick({ en: 'yes', es: 'sí' }, lang) : pick({ en: 'no, below the minimum', es: 'no, bajo el mínimo' }, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ct-note" data-minimum-ratio={sv.minimum_ratio}>
            {pick({ en: 'Minimum ratio, a convention of the case', es: 'Razón mínima, una convención del caso' }, lang)}: {formatNumber(sv.minimum_ratio, lang, { digits: 4 })}
          </p>
          <p className="ct-note">{sv.rows.map((r) => pick(r.history_source, lang)).filter((v, i, a) => a.indexOf(v) === i).join(' ')}</p>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

const RISK_COLOR = { credit: '--color-accent', market: '--color-warn', irrbb: '--color-magenta', operational: '--color-good' } as const;

/** The expected losses of the scenario by risk and year, the engine of the depletion of the capital. */
/**
 * What the key cannot show: the series that lie on each other (U16-R4 c22 m9, c23 m6: Market and IRRBB are zero in every year and draw
 * one line, the credit line lies under the total). From the committed rows; null when every series has a line of its own.
 */
export function lossesOverlap(rows: ReadonlyArray<{ credit: number; market: number; irrbb: number; operational: number; total: number }>): Bi | null {
  const zero = RISK_ORDER.filter((k) => rows.every((r) => r[k] === 0));
  const share = Math.min(...rows.map((r) => (r.total > 0 ? r.credit / r.total : 0)));
  const parts: Bi[] = [];
  if (zero.length > 0) {
    const en = zero.map((k) => pick(text(RISK_TEXT, k), 'en'));
    const es = zero.map((k) => pick(text(RISK_TEXT, k), 'es'));
    const join = (xs: string[], and: string) => (xs.length < 2 ? xs.join('') : `${xs.slice(0, -1).join(', ')} ${and} ${xs[xs.length - 1]}`);
    parts.push(
      zero.length === 1
        ? { en: `${en[0]} is zero in every year: its line lies on the zero line.`, es: `${es[0]} es cero en todos los años: su línea queda sobre la línea de cero.` }
        : { en: `${join(en, 'and')} are zero in every year: their lines lie on one another, on the zero line.`, es: `${join(es, 'y')} son cero en todos los años: sus líneas quedan una sobre otra, en la línea de cero.` },
    );
  }
  if (share >= 0.95) {
    parts.push({
      en: `Credit is ${formatNumber(Math.floor(share * 100), 'en', { decimals: 0 })} percent or more of the total in every year, so its line lies just under the total line.`,
      es: `El crédito es ${formatNumber(Math.floor(share * 100), 'es', { decimals: 0 })} por ciento o más del total en todos los años, así que su línea queda justo bajo la del total.`,
    });
  }
  return parts.length ? { en: parts.map((p) => p.en).join(' '), es: parts.map((p) => p.es).join(' ') } : null;
}

export function LossesView({ sel }: { sel: C18Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The expected losses by risk and year', es: 'Las pérdidas esperadas por riesgo y año' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SCENARIO} />;
  const rows = o.losses.scenario_losses;
  const overlap = lossesOverlap(rows);
  return (
    <ViewsRow>
      <PlotCard fill title={title} {...card} note={{ en: pick(o.losses.basis, 'en'), es: pick(o.losses.basis, 'es') }}>
        <ChartOverTable
          chartMin="16rem"
          chart={
            <UPlotChart
              height="fill"
              x={{ values: rows.map((r) => r.year), label: { en: 'Year of the projection', es: 'Año de la proyección' }, format: { decimals: 0 } }}
              y={{ label: { en: 'Expected loss (CLP millions)', es: 'Pérdida esperada (millones de CLP)' }, format: { digits: 4 } }}
              series={[
                ...RISK_ORDER.map((k) => ({ label: text(RISK_TEXT, k), values: rows.map((r) => r[k]), color: RISK_COLOR[k], width: 2 })),
                { label: text(RISK_TEXT, 'total'), values: rows.map((r) => r.total), color: '--color-fg', width: 3 },
              ]}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c18-losses">
            <thead>
              <tr>
                <th>{pick({ en: 'Year', es: 'Año' }, lang)}</th>
                {RISK_ORDER.map((k) => (
                  <th key={k}>{pick(text(RISK_TEXT, k), lang)}</th>
                ))}
                <th>{pick(text(RISK_TEXT, 'total'), lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.year} data-year={r.year} className={r.year === sel.year ? 'ct-current' : undefined}>
                  <td>{r.year}</td>
                  {RISK_ORDER.map((k) => (
                    <td key={k}>{cell(r[k], lang)}</td>
                  ))}
                  <td>{cell(r.total, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ct-note">{pick({ en: `Amounts in ${pick(MONEY_UNIT, 'en')}; the credit loss is the satellite projections times the book of each class.`, es: `Montos en ${pick(MONEY_UNIT, 'es')}; la pérdida de crédito son las proyecciones de los satélites por el libro de cada clase.` }, lang)}{overlap ? ` ${pick(overlap, lang)}` : ''}</p>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
