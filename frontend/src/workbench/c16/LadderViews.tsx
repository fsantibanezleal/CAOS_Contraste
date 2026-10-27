// C16's survival group: the survival-horizon ladder (the NLP by day with the CBC and the cumulative net outflow, the
// survival day marked), the CBC stack by class, the run-off curves against the realised run of March 2023 and the LCR's
// 30-day rates, and the Table A.1 run speeds with the LiST median survival periods as reference points. A survival period
// is a day, or "survives the horizon" with the horizon: a variant that survives has no survival mark and no number. Every
// line and every bar is a field of the document; nothing is computed here but a division by the axis scale.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { LIGHT_TEXT } from '../../lib/policy';
import { ChartOverTable, MaybeNumber } from '../c06/format';
import { useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import {
  CLASS_TEXT, COMPARED_AT_TEXT, DENOMINATOR_LONG, DENOMINATOR_SHORT, ROLE_TEXT, SEGMENT_TEXT, axisOf, fitOf, ladderOf, outputsOf, survivalDay, text,
  type C16Sel,
} from './selection';
import { ChartAbove, NOT_SCENARIO, SHARE, UnavailableCard, cell, survivalSentence } from './C16Common';

const NO_PATH: BiText = { en: 'Not available: this variant has no daily path.', es: 'No disponible: esta variante no tiene trayectoria diaria.' };

/** The NLP by day with the CBC and the cumulative net outflow, the survival day and the LiST medians marked where the ladder reaches them. */
export function LadderView({ sel }: { sel: C16Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The survival-horizon ladder', es: 'La escalera del horizonte de supervivencia' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SCENARIO} />;
  const path = o.path;
  if (!path) return <UnavailableCard sel={sel} title={title} reason={o.path_reason ?? NO_PATH} />;
  const l = path.ladder;
  const axis = axisOf([...l.nlp, ...l.cbc_total, ...l.cumulative_net_outflow]);
  const unit = pick(axis.unit, lang);
  const sday = survivalDay(path.survival);
  const last = l.day_index[l.day_index.length - 1];
  const annex = fitOf(sel)?.list_parameters.results_annex;
  const marks = [
    ...(sday !== null ? [{ x: sday, label: { en: `Survival: day ${sday}`, es: `Supervivencia: día ${sday}` } }] : []),
    ...(sel.day !== sday ? [{ x: sel.day, label: { en: `Day ${sel.day}`, es: `Día ${sel.day}` } }] : []),
    ...(annex && annex.median_survival_days.extreme <= last ? [{ x: annex.median_survival_days.extreme, label: { en: `LiST median, Extreme: day ${annex.median_survival_days.extreme}`, es: `Mediana LiST, Extremo: día ${annex.median_survival_days.extreme}` } }] : []),
    ...(annex && annex.median_survival_days.adverse <= last ? [{ x: annex.median_survival_days.adverse, label: { en: `LiST median, Adverse: day ${annex.median_survival_days.adverse}`, es: `Mediana LiST, Adverso: día ${annex.median_survival_days.adverse}` } }] : []),
  ];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: `${pick(o.variant.label, 'en')}: NLP(t) = CBC(t) minus the cumulative stressed outflows plus the inflows, by day on the ${o.variant.axis === 'relevant-days' ? 'relevant-day' : 'calendar-day'} axis. The survival period is the first day on which the NLP turns negative; a bank whose NLP stays positive survives the horizon and has no survival day.`,
          es: `${pick(o.variant.label, 'es')}: NLP(t) = CBC(t) menos las salidas acumuladas bajo estrés más las entradas, por día en el eje de ${o.variant.axis === 'relevant-days' ? 'días relevantes' : 'días calendario'}. El periodo de supervivencia es el primer día en que la NLP pasa a negativa; un banco cuya NLP sigue positiva sobrevive el horizonte y no tiene día de supervivencia.`,
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: l.day_index, label: { en: 'Day of the ladder', es: 'Día de la escalera' }, format: { decimals: 0 } }}
              y={{ label: { en: `NLP, CBC and net outflow (${pick(axis.unit, 'en')})`, es: `NLP, CBC y salida neta (${pick(axis.unit, 'es')})` }, format: { digits: 4 } }}
              series={[
                { label: { en: 'Net liquidity position (NLP)', es: 'Posición neta de liquidez (NLP)' }, values: l.nlp.map((v) => v / axis.div), color: '--color-accent', width: 2.8 },
                { label: { en: 'CBC', es: 'CBC' }, values: l.cbc_total.map((v) => v / axis.div), color: '--color-good', width: 2, dash: [6, 3] },
                { label: { en: 'Cumulative net outflow', es: 'Salida neta acumulada' }, values: l.cumulative_net_outflow.map((v) => v / axis.div), color: '--color-bad', width: 2, dash: [2, 3] },
              ]}
              marks={marks}
              yMarks={[{ y: 0, label: { en: 'NLP = 0', es: 'NLP = 0' }, tone: 'neutral' }]}
            />
          }
        >
          <p className="ct-note" data-block="survival" data-survival-kind={path.survival.kind} {...(sday !== null ? { 'data-survival-day': String(sday) } : {})}>
            {survivalSentence(path.survival, lang)}
          </p>
          <dl className="ct-defs" data-table="c16-ladder">
            <dt>{pick({ en: `Minimum NLP (${unit})`, es: `NLP mínima (${unit})` }, lang)}</dt>
            <dd>{`${formatNumber(path.minimum_nlp.value / axis.div, lang, { digits: 4 })} ${pick({ en: 'on day', es: 'en el día' }, lang)} ${cell(path.minimum_nlp.day, lang)}`}</dd>
            <dt>{pick({ en: 'Cliff effect, (NLP(35) - NLP(30)) / total assets', es: 'Efecto acantilado, (NLP(35) - NLP(30)) / activos totales' }, lang)}</dt>
            <dd data-na={path.cliff ? undefined : 'true'}>
              <MaybeNumber value={path.cliff?.value ?? null} reason={path.cliff_reason ? pick(path.cliff_reason, lang) : null} format={(v) => SHARE(v, lang)} />
            </dd>
          </dl>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The liquidity value of every class of the CBC on each day of the ladder, and their total. */
export function CbcStackView({ sel }: { sel: C16Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The CBC stack by class', es: 'El CBC apilado por clase' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SCENARIO} />;
  const l = ladderOf(o);
  if (!l) return <UnavailableCard sel={sel} title={title} reason={o.path_reason ?? NO_PATH} />;
  const axis = axisOf([...l.cbc_total, ...l.cbc_stack.flatMap((c) => c.liquidity_value)]);
  const colors = ['--color-accent', '--color-good', '--color-warn', '--color-magenta', '--color-fg-subtle', '--color-bad'] as const;
  const at = (a: number[], d: number) => l.day_index.indexOf(d) >= 0 ? a[l.day_index.indexOf(d)] : null;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'The unencumbered liquid assets by class after the haircuts of the central bank framework, usable by each day under the monetisation schedule (a convention of the case); the total is the CBC of the ladder. Pledged securities are not in it.',
          es: 'Los activos líquidos sin gravamen por clase tras los recortes del marco del banco central, utilizables en cada día según el calendario de monetización (una convención del caso); el total es el CBC de la escalera. Los valores prendados no están en él.',
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: l.day_index, label: { en: 'Day of the ladder', es: 'Día de la escalera' }, format: { decimals: 0 } }}
              y={{ label: { en: `Liquidity value of the CBC (${pick(axis.unit, 'en')})`, es: `Valor de liquidez del CBC (${pick(axis.unit, 'es')})` }, format: { digits: 4 } }}
              series={[
                ...l.cbc_stack.map((c, i) => ({ label: text(CLASS_TEXT, c.class_id), values: c.liquidity_value.map((v) => v / axis.div), color: colors[i % colors.length], width: 2 })),
                { label: { en: 'CBC, total', es: 'CBC, total' }, values: l.cbc_total.map((v) => v / axis.div), color: '--color-fg', width: 2.8 },
              ]}
              marks={sel.day >= l.day_index[0] && sel.day <= l.day_index[l.day_index.length - 1] ? [{ x: sel.day, label: { en: `Day ${sel.day}`, es: `Día ${sel.day}` } }] : []}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c16-cbc-stack">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Class', es: 'Clase' }, lang)}</th>
                <th>{pick({ en: `Day ${sel.day} (${pick({ en: 'USD thousands', es: 'miles de USD' }, lang)})`, es: `Día ${sel.day} (miles de USD)` }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: `Last day (${l.day_index[l.day_index.length - 1]})`, es: `Último día (${l.day_index[l.day_index.length - 1]})` }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {l.cbc_stack.map((c) => (
                <tr key={c.class_id} data-class={c.class_id}>
                  <td className="ct-text">{pick(text(CLASS_TEXT, c.class_id), lang)}</td>
                  <td>{cell(at(c.liquidity_value, sel.day), lang)}</td>
                  <td className="ct-wide-only">{cell(c.liquidity_value[c.liquidity_value.length - 1], lang)}</td>
                </tr>
              ))}
              <tr data-class="total">
                <td className="ct-text"><strong>{pick({ en: 'Total CBC', es: 'CBC total' }, lang)}</strong></td>
                <td>{cell(at(l.cbc_total, sel.day), lang)}</td>
                <td className="ct-wide-only">{cell(l.cbc_total[l.cbc_total.length - 1], lang)}</td>
              </tr>
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The run-off curves of the variant against the realised run in both denominators and the LCR's 30-day rates, with the scoring table. */
export function RunoffView({ sel }: { sel: C16Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The run-off against the realised run', es: 'La salida de depósitos contra la corrida realizada' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SCENARIO} />;
  const s = o.scoring;
  const l = ladderOf(o);
  const range = fitOf(sel)?.table_a1.lcr_range ?? null;
  const chosen = s.denominators.find((d) => d.id === sel.denominator) ?? s.denominators[0];
  const at = (share: number) => (l ? l.day_index.map((d) => (d === s.event.horizon_days ? share : null)) : []);
  const lcrMarks = range
    ? [
        { y: range.low, label: { en: `LCR, lowest 30-day rate: ${SHARE(range.low, 'en')}`, es: `LCR, tasa más baja a 30 días: ${SHARE(range.low, 'es')}` }, tone: 'neutral' as const },
        { y: range.high, label: { en: `LCR, highest 30-day rate: ${SHARE(range.high, 'en')}`, es: `LCR, tasa más alta a 30 días: ${SHARE(range.high, 'es')}` }, tone: 'warn' as const },
      ]
    : [];
  const chart = l ? (
    <UPlotChart
      height="fill"
      x={{ values: l.day_index, label: { en: 'Day of the ladder', es: 'Día de la escalera' }, format: { decimals: 0 } }}
      y={{ label: { en: 'Cumulative outflow (share)', es: 'Salida acumulada (parte)' }, format: { percent: true, decimals: 0 } }}
      series={[
        ...l.segments.map((g, i) => ({ label: text(SEGMENT_TEXT, g.segment), values: g.cumulative_outflow_share, color: (['--color-accent', '--color-warn', '--color-magenta', '--color-fg-subtle', '--color-good'] as const)[i % 5], width: 2.4 })),
        ...s.denominators.map((d) => ({ label: { en: `Realised run, ${text(DENOMINATOR_SHORT, d.id).en}`, es: `Corrida realizada, ${text(DENOMINATOR_SHORT, d.id).es}` }, values: at(d.realised_share), color: '--color-bad' as const, mode: 'points' as const, size: d.id === sel.denominator ? 13 : 8 })),
      ]}
      marks={l.day_index[l.day_index.length - 1] >= 30 && range ? [{ x: range.days, label: { en: 'LCR window: 30 days', es: 'Ventana del LCR: 30 días' } }] : []}
      yMarks={[{ y: chosen.realised_share, label: { en: `Realised run, ${text(DENOMINATOR_SHORT, chosen.id).en}: ${SHARE(chosen.realised_share, 'en')}`, es: `Corrida realizada, ${text(DENOMINATOR_SHORT, chosen.id).es}: ${SHARE(chosen.realised_share, 'es')}` }, tone: 'bad' }, ...lcrMarks]}
    />
  ) : (
    <BarChart
      title={{ en: 'Modelled outflow against the realised run and the LCR rates', es: 'Salida modelada contra la corrida realizada y las tasas del LCR' }}
      height="fill"
      orientation="horizontal"
      data={[
        { id: 'modelled', label: { en: `Modelled outflow, ${s.modelled_outflow.at_model_horizon.horizon_days} days`, es: `Salida modelada, ${s.modelled_outflow.at_model_horizon.horizon_days} días` }, value: s.modelled_outflow.at_model_horizon.share_of_model_base, tone: 'accent' },
        ...s.denominators.map((d) => ({ id: d.id, label: { en: `Realised run, ${text(DENOMINATOR_SHORT, d.id).en}`, es: `Corrida realizada, ${text(DENOMINATOR_SHORT, d.id).es}` }, value: d.realised_share, tone: 'bad' as const, highlight: d.id === sel.denominator })),
        ...(range ? [{ id: 'lcr-low', label: { en: 'LCR, lowest 30-day rate', es: 'LCR, tasa más baja a 30 días' }, value: range.low, tone: 'neutral' as const }, { id: 'lcr-high', label: { en: 'LCR, highest 30-day rate', es: 'LCR, tasa más alta a 30 días' }, value: range.high, tone: 'warn' as const }] : []),
      ]}
      axis={{ label: { en: 'Share of the deposit base', es: 'Parte de la base de depósitos' }, format: { percent: true, decimals: 0 }, range: [0, 1] }}
    />
  );
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: `${pick(s.event.label, 'en')}. The realised run is stated against both denominators: the Board's roughly 85 percent of the deposit base, and 40 plus 100 billion USD over the call report's DEP. The model's outflow is compared where the variant has a daily path at the event horizon of ${s.event.horizon_days} days and otherwise at its own horizon.`,
          es: `${pick(s.event.label, 'es')}. La corrida realizada se declara contra ambos denominadores: cerca de 85 por ciento de la base de depósitos según la Junta, y 40 más 100 mil millones de USD sobre el DEP del reporte. La salida del modelo se compara, donde la variante tiene trayectoria diaria, en el horizonte del evento de ${s.event.horizon_days} días y en otro caso en su propio horizonte.`,
        }}
      >
        <ChartAbove chartHeight="16rem" chart={chart}>
          <table className="caos-table ct-wrap-head" data-table="c16-denominators" data-chosen={sel.denominator}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Denominator', es: 'Denominador' }, lang)}</th>
                <th>{pick({ en: 'Realised', es: 'Realizada' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Amount (USD thousands)', es: 'Monto (miles de USD)' }, lang)}</th>
                <th>{pick({ en: 'Modelled', es: 'Modelada' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Compared', es: 'Comparada' }, lang)}</th>
                <th>{pick({ en: 'Modelled over realised', es: 'Modelada sobre realizada' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Light', es: 'Luz' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {s.denominators.map((d) => (
                <tr key={d.id} data-denominator={d.id} data-light={d.light} data-compared-at={d.compared_at} className={d.id === sel.denominator ? 'ct-current' : undefined}>
                  <td className="ct-text" title={pick(text(DENOMINATOR_LONG, d.id), lang)}>{pick(d.label, lang)}</td>
                  <td>{SHARE(d.realised_share, lang)}</td>
                  <td className="ct-wide-only" data-na={d.realised_amount === null ? 'true' : undefined}>{cell(d.realised_amount, lang)}</td>
                  <td>{SHARE(d.modelled_share, lang)}</td>
                  <td className="ct-text">{pick(text(COMPARED_AT_TEXT, d.compared_at), lang)}</td>
                  <td>{SHARE(d.ratio, lang)}</td>
                  <td className={`ct-text ct-light ct-light-${d.light}`}>
                    <span className="ct-light-word">{pick(LIGHT_TEXT[d.light], lang)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <dl className="ct-defs" data-table="c16-reference">
            <dt>{pick({ en: 'LCR deposit outflow rates over 30 days', es: 'Tasas de salida de depósitos del LCR a 30 días' }, lang)}</dt>
            <dd data-na={range ? undefined : 'true'}>{range ? `${SHARE(range.low, lang)} ${pick({ en: 'to', es: 'a' }, lang)} ${SHARE(range.high, lang)}` : formatNumber(null, lang)}</dd>
            <dt>{pick({ en: 'SVB anchor', es: 'Ancla de SVB' }, lang)}</dt>
            <dd data-forecast-claim={String(s.svb_anchor.forecast_claim)}>
              {`${pick(s.svb_anchor.label, lang)}: ${SHARE(s.svb_anchor.outflow_share, lang)} ${pick({ en: 'in', es: 'en' }, lang)} ${s.svb_anchor.days} ${pick({ en: 'days, a daily rate of', es: 'días, una tasa diaria de' }, lang)} ${SHARE(s.svb_anchor.implied_daily_rate, lang)}`}
              <span className="ct-note" style={{ display: 'block', whiteSpace: 'normal' }}>{pick({ en: 'A labelled anchor row, never a forecast.', es: 'Una fila ancla rotulada, nunca un pronóstico.' }, lang)}</span>
            </dd>
            <dt>{pick({ en: 'Modelled deposit base (USD thousands)', es: 'Base de depósitos del modelo (miles de USD)' }, lang)}</dt>
            <dd>{cell(s.model_deposit_base, lang)}</dd>
          </dl>
        </ChartAbove>
      </PlotCard>
    </ViewsRow>
  );
}

/** The nine Table A.1 run speeds with the model's share at each row's horizon, and the LiST median survival periods as reference points. */
export function RunSpeedsView({ sel }: { sel: C16Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The Table A.1 run speeds', es: 'Las velocidades de corrida de la Tabla A.1' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SCENARIO} />;
  const rows = o.scoring.table_a1_scoring;
  const fit = fitOf(sel);
  const annex = fit?.list_parameters.results_annex ?? null;
  const implied = new Map((fit?.calibration.implied_daily_rates ?? []).map((r) => [r.row_id as string, r.implied_daily_rate] as const));
  implied.set('svb-2023', o.scoring.svb_anchor.implied_daily_rate);
  const tone = { calibration: 'accent', scored: 'warn', reference: 'neutral' } as const;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'Deposit outflow shares of the nine rows of BCBS Table A.1, with the days each took. The fast run is calibrated on the rows dated before 2023 and scored on the 2023 rows; the other variants show the rows only as reference points. A row whose horizon is beyond the ladder has no modelled share, and says so. Amber bars are the rows scored on, blue bars the rows calibrated on, grey bars rows shown only as reference.',
          es: 'Partes de salida de depósitos de las nueve filas de la Tabla A.1 del BCBS, con los días que tomó cada una. La corrida rápida se calibra con las filas anteriores a 2023 y se evalúa en las filas de 2023; las otras variantes muestran las filas solo como puntos de referencia. Una fila cuyo horizonte excede la escalera no tiene parte modelada, y lo dice. Las barras ámbar son las filas en que se evalúa, las azules las filas con que se calibra, las grises filas que solo se muestran como referencia.',
        }}
      >
        <ChartOverTable
          chartMin="22rem"
          chart={
            <BarChart
              title={{ en: 'Deposit outflow share of each Table A.1 row', es: 'Parte de salida de depósitos de cada fila de la Tabla A.1' }}
              height="fill"
              orientation="horizontal"
              data={rows.map((r) => ({
                id: r.row_id,
                label: { en: `${r.bank} ${r.year}, ${r.horizon_days} ${r.horizon_days === 1 ? 'day' : 'days'}`, es: `${r.bank} ${r.year}, ${r.horizon_days} ${r.horizon_days === 1 ? 'día' : 'días'}` },
                value: r.observed_share,
                tone: tone[r.role],
                highlight: r.row_id === sel.row,
                hint: text(ROLE_TEXT, r.role),
              }))}
              axis={{ label: { en: 'Share of deposits that left over the days of the row', es: 'Parte de los depósitos que salió en los días de la fila' }, format: { percent: true, decimals: 0 }, range: [0, 1] }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c16-table-a1" data-chosen={sel.row}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Row', es: 'Fila' }, lang)}</th>
                <th>{pick({ en: 'Days', es: 'Días' }, lang)}</th>
                <th>{pick({ en: 'Observed', es: 'Observada' }, lang)}</th>
                <th>{pick({ en: 'Modelled at its horizon', es: 'Modelada en su horizonte' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Daily rate it implies', es: 'Tasa diaria que implica' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Role', es: 'Papel' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.row_id} data-row={r.row_id} data-role={r.role} className={r.row_id === sel.row ? 'ct-current' : undefined}>
                  <td className="ct-text">{`${r.bank} ${r.year}`}</td>
                  <td>{r.horizon_days}</td>
                  <td>{SHARE(r.observed_share, lang)}</td>
                  <td data-na={r.modelled_share === null ? 'true' : undefined}>
                    <MaybeNumber value={r.modelled_share} reason={r.reason ? pick(r.reason, lang) : null} format={(v) => SHARE(v, lang)} />
                  </td>
                  <td className="ct-wide-only" data-na={implied.has(r.row_id) ? undefined : 'true'}>{implied.has(r.row_id) ? SHARE(implied.get(r.row_id) ?? null, lang) : formatNumber(null, lang)}</td>
                  <td className="ct-text">{pick(text(ROLE_TEXT, r.role), lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head" data-table="c16-list-medians">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Reference point', es: 'Punto de referencia' }, lang)}</th>
                <th>{pick({ en: 'Survival period (days)', es: 'Periodo de supervivencia (días)' }, lang)}</th>
                <th>{pick({ en: 'Banks', es: 'Bancos' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {(['adverse', 'extreme'] as const).map((k) => (
                <tr key={k} data-median={k} data-na={annex ? undefined : 'true'}>
                  <td className="ct-text">{pick(k === 'adverse' ? { en: 'ECB LiST 2019, median under the Adverse shock', es: 'BCE LiST 2019, mediana bajo el choque adverso' } : { en: 'ECB LiST 2019, median under the Extreme shock', es: 'BCE LiST 2019, mediana bajo el choque extremo' }, lang)}</td>
                  <td>{annex ? cell(annex.median_survival_days[k], lang) : formatNumber(null, lang)}</td>
                  <td>{annex ? cell(annex.n_banks, lang) : formatNumber(null, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {annex ? <p className="ct-note">{pick(annex.statement, lang)}</p> : null}
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
