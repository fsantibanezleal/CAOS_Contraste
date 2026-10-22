// C16's sensitivity group: the survival period against the uninsured share and against the HTM loss multiple (05 E.5
// rung 4), and the reverse stress (rung 5): the run-off multiplier at which the survival period first falls to the target,
// per base scenario, with its curve and the cap that keeps every daily rate below one. A grid point that survives the
// horizon is drawn as no point and written "survives the horizon", with the horizon, never as a number. A null block shows
// its reason.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable, MaybeNumber } from '../c06/format';
import { useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { BASE_ORDER, BASE_TEXT, baseOf, outputsOf, reverseOf, survivalDay, survivalText, text, type C16Sel, type C16Survival } from './selection';
import { MONEY_UNIT, NOT_REVERSE, NOT_SCENARIO, SHARE, SurvivalCell, UnavailableCard, cell, digits } from './C16Common';

const NO_DRAWN_DAY: BiText = { en: 'Every point survives its horizon: there is no survival day to draw. The table gives each point and the horizon it survived.', es: 'Todo punto sobrevive su horizonte: no hay día de supervivencia que dibujar. La tabla da cada punto y el horizonte que sobrevivió.' };

/** The note under a sensitivity chart: the points that survive the horizon are named, never drawn as a number. */
function SurvivorsNote({ survivals }: { survivals: Array<{ label: string; s: C16Survival }> }) {
  const lang = useShellLang();
  const survivors = survivals.filter(({ s }) => survivalDay(s) === null);
  if (survivors.length === 0) return null;
  return (
    <p className="ct-note" data-state="survives">
      {pick({ en: `Survives the horizon, no survival day: ${survivors.map(({ label }) => label).join(', ')}.`, es: `Sobrevive el horizonte, sin día de supervivencia: ${survivors.map(({ label }) => label).join(', ')}.` }, lang)}
    </p>
  );
}

/** The survival period when the uninsured share of the domestic deposits is each point of the grid. */
export function UninsuredShareView({ sel }: { sel: C16Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'Survival against the uninsured share', es: 'Supervivencia contra la parte no asegurada' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SCENARIO} />;
  const rows = o.sensitivities.uninsured_share;
  if (!rows) return <UnavailableCard sel={sel} title={title} reason={o.sensitivities.uninsured_share_reason ?? { en: 'Not available: this variant has no daily path.', es: 'No disponible: esta variante no tiene trayectoria diaria.' }} />;
  const days = rows.map((r) => survivalDay(r.survival));
  const own = o.balance_sheet.deposits.uninsured_share_of_depdom;
  const drawn = days.some((d) => d !== null);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'The survival period of the variant when the uninsured share of the domestic deposits (DEPUNA over DEPDOM) takes each value of the grid, a convention of the case; a larger uninsured share runs faster. The document\'s own share is marked.',
          es: 'El periodo de supervivencia de la variante cuando la parte no asegurada de los depósitos domésticos (DEPUNA sobre DEPDOM) toma cada valor de la grilla, una convención del caso; una parte no asegurada mayor sale más rápido. Se marca la parte propia del documento.',
        }}
      >
        <ChartOverTable
          chart={
            drawn ? (
              <UPlotChart
                height="fill"
                x={{ values: rows.map((r) => r.share), label: { en: 'Uninsured share of the domestic deposits', es: 'Parte no asegurada de los depósitos domésticos' }, format: { percent: true, decimals: 0 } }}
                y={{ label: { en: 'Survival period (days)', es: 'Supervivencia (días)' }, format: { decimals: 0 } }}
                series={[{ label: { en: 'Survival period', es: 'Periodo de supervivencia' }, values: days, color: '--color-accent', width: 2.6, mode: 'points', size: 10 }]}
                marks={own >= rows[0].share && own <= rows[rows.length - 1].share ? [{ x: own, label: { en: `This document: ${SHARE(own, 'en')}`, es: `Este documento: ${SHARE(own, 'es')}` } }] : []}
              />
            ) : (
              <p className="caos-pending" data-state="survives">{pick(NO_DRAWN_DAY, lang)}</p>
            )
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c16-uninsured-share">
            <thead>
              <tr>
                <th>{pick({ en: 'Uninsured share', es: 'Parte no asegurada' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Survival period', es: 'Periodo de supervivencia' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.share} data-share={r.share}>
                  <td>{SHARE(r.share, lang)}</td>
                  <SurvivalCell s={r.survival} className="ct-text" />
                </tr>
              ))}
            </tbody>
          </table>
          <SurvivorsNote survivals={rows.map((r) => ({ label: SHARE(r.share, lang), s: r.survival }))} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The survival period and the CBC when the HTM unrealised loss is each multiple of the reported loss. */
export function HtmLossView({ sel }: { sel: C16Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'Survival against the HTM loss', es: 'Supervivencia contra la pérdida HTM' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SCENARIO} />;
  const rows = o.sensitivities.htm_loss;
  if (!rows) return <UnavailableCard sel={sel} title={title} reason={o.sensitivities.htm_loss_reason ?? { en: 'Not available: this variant has no daily path.', es: 'No disponible: esta variante no tiene trayectoria diaria.' }} />;
  const days = rows.map((r) => survivalDay(r.survival));
  const drawn = days.some((d) => d !== null);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'The survival period when the unrealised loss on the held-to-maturity book is a multiple of the reported loss: 1 is the reported loss and 0 is no loss. The CBC under each multiple is in the table. The multiples are a grid, a convention of the case.',
          es: 'El periodo de supervivencia cuando la pérdida no realizada de la cartera mantenida al vencimiento es un múltiplo de la pérdida reportada: 1 es la pérdida reportada y 0 es sin pérdida. El CBC bajo cada múltiplo está en la tabla. Los múltiplos son una grilla, una convención del caso.',
        }}
      >
        <ChartOverTable
          chart={
            drawn ? (
              <UPlotChart
                height="fill"
                x={{ values: rows.map((r) => r.multiple), label: { en: 'Multiple of the reported HTM loss', es: 'Múltiplo de la pérdida HTM reportada' }, format: { digits: 3 } }}
                y={{ label: { en: 'Survival period (days)', es: 'Supervivencia (días)' }, format: { decimals: 0 } }}
                series={[{ label: { en: 'Survival period', es: 'Periodo de supervivencia' }, values: days, color: '--color-bad', width: 2.6, mode: 'points', size: 10 }]}
                marks={[{ x: 1, label: { en: 'Reported loss', es: 'Pérdida reportada' } }]}
              />
            ) : (
              <p className="caos-pending" data-state="survives">{pick(NO_DRAWN_DAY, lang)}</p>
            )
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c16-htm-loss">
            <thead>
              <tr>
                <th>{pick({ en: 'Multiple', es: 'Múltiplo' }, lang)}</th>
                <th>{pick({ en: `Unrealised loss (${pick(MONEY_UNIT, 'en')})`, es: `Pérdida no realizada (${pick(MONEY_UNIT, 'es')})` }, lang)}</th>
                <th>{pick({ en: 'CBC', es: 'CBC' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Survival period', es: 'Periodo de supervivencia' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.multiple} data-multiple={r.multiple}>
                  <td>{formatNumber(r.multiple, lang, { digits: 3 })}</td>
                  <td>{cell(r.unrealised_loss, lang)}</td>
                  <td>{cell(r.cbc, lang)}</td>
                  <SurvivalCell s={r.survival} className="ct-text" />
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ct-note">{pick({ en: 'The chart draws the survival period of each multiple; the table keeps the whole amounts of the loss and the CBC.', es: 'El gráfico dibuja el periodo de supervivencia de cada múltiplo; la tabla conserva los montos completos de la pérdida y del CBC.' }, lang)}</p>
          <SurvivorsNote survivals={rows.map((r) => ({ label: formatNumber(r.multiple, lang, { digits: 3 }), s: r.survival }))} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The curve SP(m) of the base scenario in focus against the target, with the solved multiplier marked. */
export function ReverseCurveView({ sel }: { sel: C16Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const r = reverseOf(sel);
  const title: BiText = { en: 'The reverse-stress curve', es: 'La curva de la prueba de estrés inversa' };
  if (!sel) return <Pending />;
  if (!r) return <UnavailableCard sel={sel} title={title} reason={NOT_REVERSE} />;
  const b = baseOf(r, sel.base) ?? r.bases[0];
  const days = b.curve.map((p) => survivalDay(p.survival));
  const horizon = b.base_survival.horizon_days;
  const drawn = days.some((d) => d !== null);
  const solved = b.solved.status === 'solved' ? b.solved.multiplier : null;
  const picked = b.curve[sel.point]?.multiplier ?? null;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `The reverse-stress curve: ${pick(b.label, 'en')}`, es: `La curva de la prueba de estrés inversa: ${pick(b.label, 'es')}` }}
        {...card}
        note={{
          en: `${pick(r.target.statement, 'en')} The multiplier scales every deposit segment's daily rate and is capped so that each rate stays below 1.`,
          es: `${pick(r.target.statement, 'es')} El multiplicador escala la tasa diaria de cada segmento de depósitos y tiene un tope para que cada tasa quede bajo 1.`,
        }}
      >
        <ChartOverTable
          chart={
            drawn ? (
              <UPlotChart
                height="fill"
                x={{ values: b.curve.map((p) => p.multiplier), log: true, label: { en: 'Multiplier of the daily run-off rates (logarithmic)', es: 'Multiplicador de las tasas diarias de salida (logarítmico)' }, format: { digits: 3 } }}
                y={{ label: { en: 'Survival period (days)', es: 'Supervivencia (días)' }, format: { decimals: 0 } }}
                series={[{ label: { en: 'Survival period under the multiplier', es: 'Periodo de supervivencia bajo el multiplicador' }, values: days, color: '--color-accent', width: 2.6, mode: 'points', size: 9 }]}
                marks={[
                  ...(solved !== null ? [{ x: solved, label: { en: `Solved: ${formatNumber(solved, 'en', { digits: 4 })}`, es: `Resuelto: ${formatNumber(solved, 'es', { digits: 4 })}` } }] : []),
                  ...(picked !== null && picked !== solved ? [{ x: picked, label: { en: `Point: ${formatNumber(picked, 'en', { digits: 4 })}`, es: `Punto: ${formatNumber(picked, 'es', { digits: 4 })}` } }] : []),
                ]}
                yMarks={[
                  { y: r.target.days, label: { en: `Target: ${r.target.days} days`, es: `Objetivo: ${r.target.days} días` }, tone: 'bad' },
                  { y: horizon, label: { en: `Horizon: ${horizon} days`, es: `Horizonte: ${horizon} días` }, tone: 'neutral' },
                ]}
              />
            ) : (
              <p className="caos-pending" data-state="survives">{pick(NO_DRAWN_DAY, lang)}</p>
            )
          }
        >
          <dl className="ct-defs" data-table="c16-reverse-base" data-target={r.target.days} data-solved={b.solved.status} data-base={b.base_id}>
            <dt>{pick({ en: 'Survival of the base scenario', es: 'Supervivencia del escenario base' }, lang)}</dt>
            <dd data-survival-kind={b.base_survival.kind}>{survivalText(b.base_survival, lang)}</dd>
            <dt>{pick({ en: 'Solved multiplier', es: 'Multiplicador resuelto' }, lang)}</dt>
            <dd data-na={solved === null ? 'true' : undefined}>
              <MaybeNumber value={solved} reason={b.solved.refusal_reason ? pick(b.solved.refusal_reason, lang) : null} format={(v) => formatNumber(v, lang, { digits: 4 })} />
            </dd>
            <dt>{pick({ en: 'Cap on the multiplier', es: 'Tope del multiplicador' }, lang)}</dt>
            <dd>{formatNumber(b.max_multiplier, lang, { digits: 4 })}</dd>
          </dl>
          <table className="caos-table ct-wrap-head" data-table="c16-reverse-curve">
            <thead>
              <tr>
                <th>{pick({ en: 'Multiplier', es: 'Multiplicador' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Survival period', es: 'Periodo de supervivencia' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {b.curve.map((p, i) => (
                <tr key={p.multiplier} data-multiplier={p.multiplier} data-chosen={i === sel.point ? 'true' : undefined} className={i === sel.point ? 'ct-current' : undefined}>
                  <td>{formatNumber(p.multiplier, lang, { digits: 4 })}</td>
                  <SurvivalCell s={p.survival} className="ct-text" />
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The solved multiplier of every base scenario, the target and the cap, and a refused target with its reason and no number. */
export function ReverseBasesView({ sel }: { sel: C16Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const r = reverseOf(sel);
  const title: BiText = { en: 'The solved multipliers', es: 'Los multiplicadores resueltos' };
  if (!sel) return <Pending />;
  if (!r) return <UnavailableCard sel={sel} title={title} reason={NOT_REVERSE} />;
  const bases = [...r.bases].sort((a, b) => BASE_ORDER.indexOf(a.base_id) - BASE_ORDER.indexOf(b.base_id));
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: `${pick(r.target.statement, 'en')} ${pick(r.cap_rule.statement, 'en')} A target that cannot be bracketed is refused with its reason and no multiplier.`,
          es: `${pick(r.target.statement, 'es')} ${pick(r.cap_rule.statement, 'es')} Un objetivo que no se puede acotar se rechaza con su razón y sin multiplicador.`,
        }}
      >
        <ChartOverTable
          chartMin="12rem"
          chart={
            <BarChart
              title={{ en: 'Solved multiplier by base scenario', es: 'Multiplicador resuelto por escenario base' }}
              height="fill"
              orientation="horizontal"
              data={bases.map((b) => ({ id: b.base_id, label: text(BASE_TEXT, b.base_id), value: b.solved.status === 'solved' ? b.solved.multiplier : null, tone: 'accent' as const, highlight: b.base_id === sel.base, hint: b.solved.refusal_reason ?? undefined }))}
              axis={{ label: { en: `Multiplier of the daily run-off rates at which the survival period first falls to ${r.target.days} days`, es: `Multiplicador de las tasas diarias de salida con que el periodo de supervivencia cae por primera vez a ${r.target.days} días` }, format: { digits: 4 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c16-reverse-bases">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Base scenario', es: 'Escenario base' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Survival of the base', es: 'Supervivencia de la base' }, lang)}</th>
                <th>{pick({ en: 'Largest daily rate below 1', es: 'Mayor tasa diaria bajo 1' }, lang)}</th>
                <th>{pick({ en: 'Cap on the multiplier', es: 'Tope del multiplicador' }, lang)}</th>
                <th>{pick({ en: 'Solved multiplier', es: 'Multiplicador resuelto' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Round-trip error (days)', es: 'Error de ida y vuelta (días)' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {bases.map((b) => (
                <tr key={b.base_id} data-base={b.base_id} data-solved={b.solved.status} className={b.base_id === sel.base ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(b.label, lang)}</td>
                  <SurvivalCell s={b.base_survival} className="ct-text" />
                  <td>{SHARE(b.max_rate_below_one, lang)}</td>
                  <td>{digits(b.max_multiplier, lang)}</td>
                  <td data-na={b.solved.status === 'solved' ? undefined : 'true'}>
                    <MaybeNumber value={b.solved.multiplier} reason={b.solved.refusal_reason ? pick(b.solved.refusal_reason, lang) : null} format={(v) => digits(v, lang)} />
                  </td>
                  <td className="ct-wide-only" data-na={b.solved.round_trip_error === null ? 'true' : undefined}>{b.solved.round_trip_error === null ? formatNumber(null, lang) : formatNumber(b.solved.round_trip_error, lang, { digits: 3 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
