// C14's Deposit behaviour group: how much of the loss hangs on the deposit assumptions (every result with and without the
// behavioural non-maturity deposit model), the replicating portfolio of each deposit category and its stability across
// estimation windows, the supervisory caps shown with and without the cap, and the parameter changes that coincide with
// a limit breach (the Silicon Valley Bank lesson). The behaviour is synthetic and labelled as such; the numbers are the bake's.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { ChartOverTable, MaybeNumber } from '../c06/format';
import { useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { IrrbbTestsTable, UnavailableCard, assumptionValue } from './C14Common';
import {
  CALIBRATION_SHORT, CATEGORY_TEXT, SHOCK_TEXT, SOURCE_KIND_TEXT, axisOf, cell, fitOf, nmdModelOf, outputsOf, scaleUnit, text, type C14Sel,
} from './selection';
import { IRRBB_SOURCE_RULES, localise } from './localise';

const SHARE = (v: number | null | undefined, lang: 'en' | 'es') => formatNumber(v, lang, { percent: true, decimals: 2 });

/** The delta EVE of every shock under the behavioural and the contractual deposit assumption, for both calibrations, and the difference. */
export function WithWithoutView({ sel }: { sel: C14Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const rows = o.behavioural_comparison;
  const mine = rows.filter((r) => r.calibration === sel.calibration);
  const axis = axisOf(o, mine.map((r) => r.difference));
  const unit = pick(scaleUnit(o), lang);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The loss with and without the deposit assumptions', es: 'La pérdida con y sin los supuestos de depósitos' }}
        {...card}
        note={{
          en: `${o.sign_convention.statement.en} The bars are the behavioural delta EVE minus the contractual one: a bar below zero is the loss that the behavioural assumption removes, so it is the part of the result that hangs on the deposit assumptions.`,
          es: `${o.sign_convention.statement.es} Las barras son el delta EVE conductual menos el contractual: una barra bajo cero es la pérdida que el supuesto conductual elimina, es decir, la parte del resultado que depende de los supuestos de depósitos.`,
        }}
      >
        <ChartOverTable
          chartMin="13rem"
          chart={
            <BarChart
              title={{ en: 'Behavioural minus contractual delta EVE', es: 'Delta EVE conductual menos contractual' }}
              height="fill"
              orientation="horizontal"
              data={mine.map((r) => ({ id: r.shock, label: text(SHOCK_TEXT, r.shock), value: r.difference / axis.div, tone: r.difference < 0 ? ('good' as const) : ('bad' as const), highlight: r.shock === sel.shock }))}
              axis={{ label: { en: `Difference, ${sel.calibration} calibration`, es: `Diferencia, calibración ${sel.calibration}` }, unit: axis.unit, format: { digits: 4 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="with-without">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Calibration', es: 'Calibración' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Shock', es: 'Choque' }, lang)}</th>
                <th>{pick({ en: `Behavioural (${unit})`, es: `Conductual (${unit})` }, lang)}</th>
                <th>{pick({ en: `Contractual (${unit})`, es: `Contractual (${unit})` }, lang)}</th>
                <th>{pick({ en: `Difference (${unit})`, es: `Diferencia (${unit})` }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.calibration}-${r.shock}`} data-calibration={r.calibration} data-shock={r.shock} className={r.calibration === sel.calibration && r.shock === sel.shock ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(text(CALIBRATION_SHORT, r.calibration), lang)}</td>
                  <td className="ct-text">{pick(text(SHOCK_TEXT, r.shock), lang)}</td>
                  <td>{cell(r.delta_eve_behavioural, lang)}</td>
                  <td>{cell(r.delta_eve_contractual, lang)}</td>
                  <td>{cell(r.difference, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <IrrbbTestsTable variant={sel.data.variant} only={(t) => t.test_id === 'irrbb.eve_with_without_behavioural'} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

const MATURITY_LABEL = (m: number) => ({ en: `${formatNumber(m, 'en', { digits: 4 })} y`, es: `${formatNumber(m, 'es', { digits: 4 })} a` });

/** The static replicating portfolio of the deposit category in focus: tranche weights, implied maturity, beta, margin volatility and the weights re-estimated on other windows. */
export function ReplicatingView({ sel }: { sel: C14Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const m = nmdModelOf(fitOf(sel), sel.category, o.valuation_date);
  if (!m) {
    return <UnavailableCard sel={sel} title={{ en: 'The replicating portfolio', es: 'La cartera replicante' }} reason={{ en: 'Not available: the models artifact carries no replicating portfolio for this category.', es: 'No disponible: el artefacto de modelos no trae una cartera replicante para esta categoría.' }} />;
  }
  const cat = text(CATEGORY_TEXT, m.category);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `Replicating portfolio: ${cat.en}`, es: `Cartera replicante: ${cat.es.toLowerCase()}` }}
        {...card}
        note={{
          en: 'A static replicating portfolio funds the stable part of the deposits with a ladder of rolling tranches whose weights sum to one. The weighted average maturity of a rolling tranche of maturity m is m over two. The weights are estimated on a window, and re-estimated on other windows to show how stable they are. The fit is synthetic behaviour, labelled as such.',
          es: 'Una cartera replicante estática financia la parte estable de los depósitos con una escalera de tramos rodantes cuyos pesos suman uno. El plazo promedio ponderado de un tramo rodante de plazo m es m sobre dos. Los pesos se estiman en una ventana y se reestiman en otras para mostrar su estabilidad. El ajuste es conducta sintética, declarada como tal.',
        }}
      >
        <ChartOverTable
          chart={
            <BarChart
              title={{ en: 'Weight of each rolling tranche', es: 'Peso de cada tramo rodante' }}
              height="fill"
              orientation="vertical"
              data={m.tranches.map((t) => ({ id: String(t.maturity_years), label: MATURITY_LABEL(t.maturity_years), value: t.weight, tone: 'accent' as const }))}
              axis={{ label: { en: 'Weight in the portfolio', es: 'Peso en la cartera' }, format: { percent: true, decimals: 1 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="replicating">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Estimation window', es: 'Ventana de estimación' }, lang)}</th>
                {m.tranches.map((t) => (
                  <th key={t.maturity_years} data-tranche={t.maturity_years}>{pick(MATURITY_LABEL(t.maturity_years), lang)}</th>
                ))}
                <th className="ct-wide-only">{pick({ en: 'Implied maturity (years)', es: 'Plazo implícito (años)' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              <tr data-window="fit">
                <td className="ct-text">{pick({ en: 'The fit of this variant', es: 'El ajuste de esta variante' }, lang)}</td>
                {m.tranches.map((t) => (
                  <td key={t.maturity_years}>{SHARE(t.weight, lang)}</td>
                ))}
                <td className="ct-wide-only">{formatNumber(m.weighted_average_maturity_years, lang, { digits: 4 })}</td>
              </tr>
              {m.stability.map((w) => (
                <tr key={w.window_start} data-window={w.window_start}>
                  <td className="ct-text">{`${w.window_start} ${pick({ en: 'to', es: 'a' }, lang)} ${w.window_end}`}</td>
                  {w.weights.map((x, i) => (
                    <td key={i}>{SHARE(x, lang)}</td>
                  ))}
                  <td className="ct-wide-only">{formatNumber(w.weighted_average_maturity_years, lang, { digits: 4 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <dl className="ct-defs" data-table="replicating-facts">
            <dt>{pick({ en: 'Weights sum to', es: 'Los pesos suman' }, lang)}</dt>
            <dd>{formatNumber(m.weights_sum, lang, { digits: 4 })}</dd>
            <dt>{pick({ en: 'Margin volatility', es: 'Volatilidad del margen' }, lang)}</dt>
            <dd>
              <MaybeNumber value={m.margin_volatility} reason={m.margin_volatility_reason ? pick(m.margin_volatility_reason, lang) : null} format={(v) => SHARE(v, lang)} />
            </dd>
            <dt>{pick({ en: 'Deposit beta, up', es: 'Beta de depósitos, al alza' }, lang)}</dt>
            <dd>{SHARE(m.deposit_beta.up, lang)}</dd>
            <dt>{pick({ en: 'Deposit beta, down', es: 'Beta de depósitos, a la baja' }, lang)}</dt>
            <dd>{SHARE(m.deposit_beta.down, lang)}</dd>
            <dt>{pick({ en: 'Where the beta comes from', es: 'De dónde viene el beta' }, lang)}</dt>
            <dd>{`${pick(text(SOURCE_KIND_TEXT, m.deposit_beta.source_kind), lang)}: ${localise(m.deposit_beta.source, lang, IRRBB_SOURCE_RULES)}`}</dd>
          </dl>
          <IrrbbTestsTable variant={sel.data.variant} only={(t) => t.test_id === 'irrbb.nmd_parameter_stability'} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The non-maturity deposit segments with the requested core share and maturity, the supervisory cap and the value used: the assumption with and without the cap. */
export function CapsView({ sel }: { sel: C14Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const unit = pick(scaleUnit(o), lang);
  const segs = o.nmd_segments;
  const rows: Array<{ id: string; label: BiText; value: number; tone: 'accent' | 'warn' }> = segs.flatMap((s) => {
    const c = text(CATEGORY_TEXT, s.category);
    return [
      { id: `${s.category}-requested`, label: { en: `${c.en}: requested`, es: `${c.es}: pedida` }, value: s.requested_core_share, tone: s.cap_applied ? ('warn' as const) : ('accent' as const) },
      { id: `${s.category}-used`, label: { en: `${c.en}: used`, es: `${c.es}: usada` }, value: s.core_share_used, tone: 'accent' as const },
    ];
  });
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The deposit caps, with and without the cap', es: 'Los topes de depósitos, con y sin tope' }}
        {...card}
        note={{
          en: 'The standardised EVE uses the capped values (SRP31 Table 4). Each segment shows what was requested, the cap and the value used, so the result can be read without the cap too. A request above its cap is flagged as capped.',
          es: 'El EVE estandarizado usa los valores con tope (SRP31 Tabla 4). Cada segmento muestra lo pedido, el tope y el valor usado, de modo que el resultado puede leerse también sin el tope. Una petición sobre su tope queda marcada con tope.',
        }}
      >
        <ChartOverTable
          chartMin="17rem"
          chart={
            <BarChart
              title={{ en: 'Core share requested and used', es: 'Parte estable pedida y usada' }}
              height="fill"
              orientation="horizontal"
              data={rows}
              axis={{ label: { en: 'Core share of the balance', es: 'Parte estable del saldo' }, format: { percent: true, decimals: 0 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="nmd-caps">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Category', es: 'Categoría' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: `Balance (${unit})`, es: `Saldo (${unit})` }, lang)}</th>
                <th>{pick({ en: 'Core share requested', es: 'Parte estable pedida' }, lang)}</th>
                <th>{pick({ en: 'Share cap', es: 'Tope de la parte' }, lang)}</th>
                <th>{pick({ en: 'Used', es: 'Usada' }, lang)}</th>
                <th>{pick({ en: 'Maturity requested (years)', es: 'Plazo pedido (años)' }, lang)}</th>
                <th>{pick({ en: 'Cap (years)', es: 'Tope (años)' }, lang)}</th>
                <th>{pick({ en: 'Used (years)', es: 'Usado (años)' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Cap applied', es: 'Tope aplicado' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {segs.map((s) => (
                <tr key={s.category} data-category={s.category} data-cap-applied={s.cap_applied}>
                  <td className="ct-text" title={pick(text(SOURCE_KIND_TEXT, s.source_kind), lang)}>{pick(text(CATEGORY_TEXT, s.category), lang)}</td>
                  <td className="ct-wide-only">{cell(s.balance, lang)}</td>
                  <td>{SHARE(s.requested_core_share, lang)}</td>
                  <td>{SHARE(s.core_share_cap, lang)}</td>
                  <td>{SHARE(s.core_share_used, lang)}</td>
                  <td>{formatNumber(s.requested_core_maturity_years, lang, { digits: 4 })}</td>
                  <td>{formatNumber(s.core_maturity_cap_years, lang, { digits: 4 })}</td>
                  <td>{formatNumber(s.core_maturity_used_years, lang, { digits: 4 })}</td>
                  <td className="ct-text">{pick(s.cap_applied ? { en: 'capped', es: 'con tope' } : { en: 'within the cap', es: 'dentro del tope' }, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The name of a behavioural parameter in words: the contract gives it as a phrase, the category is the document's. */
function parameterLabel(parameter: string, category: string): BiText {
  const c = text(CATEGORY_TEXT, category);
  if (parameter.startsWith('core share')) return { en: `Core share, ${c.en.toLowerCase()}`, es: `Parte estable, ${c.es.toLowerCase()}` };
  if (parameter.startsWith('core maturity')) return { en: `Core maturity, ${c.en.toLowerCase()}`, es: `Plazo estable, ${c.es.toLowerCase()}` };
  // the contract's own phrases: "requested core share, wholesale", "replicating-portfolio weighted average maturity, wholesale"
  if (parameter.startsWith('requested core share')) return { en: `Requested core share, ${c.en.toLowerCase()}`, es: `Parte estable solicitada, ${c.es.toLowerCase()}` };
  if (parameter.startsWith('requested core maturity')) return { en: `Requested core maturity, ${c.en.toLowerCase()}`, es: `Plazo estable solicitado, ${c.es.toLowerCase()}` };
  if (parameter.startsWith('replicating-portfolio weighted average maturity')) {
    return { en: `Weighted average maturity of the replicating portfolio, ${c.en.toLowerCase()}`, es: `Plazo medio ponderado de la cartera replicante, ${c.es.toLowerCase()}` };
  }
  return { en: parameter, es: parameter };
}

/** A change of a behavioural parameter between two valuation dates, flagged when it fell in a window that holds a limit breach. */
export function ChangesView({ sel }: { sel: C14Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const fit = sel ? fitOf(sel) : null;
  if (!sel || !o) return <Pending />;
  const changes = fit?.nmd_parameter_changes ?? [];
  if (!fit) {
    return <UnavailableCard sel={sel} title={{ en: 'Parameter changes', es: 'Cambios de parámetros' }} reason={{ en: 'Not available: the models artifact carries no parameter changes.', es: 'No disponible: el artefacto de modelos no trae cambios de parámetros.' }} />;
  }
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Behavioural parameter changes against limit breaches', es: 'Cambios de parámetros conductuales frente a excesos de límite' }}
        {...card}
        note={{
          en: 'A behavioural parameter changed between two valuation dates is flagged when the window also holds a limit breach: a more favourable assumption adopted while a limit was breached is the pattern the 2023 Silicon Valley Bank review found. The flag is the validator\'s question, not a verdict.',
          es: 'Un parámetro conductual que cambió entre dos fechas de valoración queda marcado cuando la ventana contiene además un exceso de límite: un supuesto más favorable adoptado mientras un límite estaba excedido es el patrón que halló la revisión de 2023 de Silicon Valley Bank. La marca es la pregunta del validador, no un veredicto.',
        }}
      >
        <div className="ct-scroll">
          <table className="caos-table ct-wrap-head" data-table="parameter-changes">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Parameter', es: 'Parámetro' }, lang)}</th>
                <th>{pick({ en: 'Before', es: 'Antes' }, lang)}</th>
                <th>{pick({ en: 'After', es: 'Después' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Limit breach in the window', es: 'Exceso de límite en la ventana' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Flag', es: 'Marca' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Note', es: 'Nota' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {changes.map((c, i) => (
                <tr key={i} data-flagged={c.flagged} data-breach={c.limit_breach_in_window}>
                  <td className="ct-text">
                    {pick(parameterLabel(c.parameter, c.category), lang)}
                    <span className="ct-note" style={{ display: 'block' }} data-window={`${c.from_date} ${c.to_date}`}>{`${c.from_date} ${pick({ en: 'to', es: 'a' }, lang)} ${c.to_date}`}</span>
                  </td>
                  <td>{assumptionValue(c.from_value, c.unit, lang)}</td>
                  <td>{assumptionValue(c.to_value, c.unit, lang)}</td>
                  <td className="ct-text">{pick(c.limit_breach_in_window ? { en: 'yes', es: 'sí' } : { en: 'no', es: 'no' }, lang)}</td>
                  <td className="ct-text">{pick(c.flagged ? { en: 'flagged', es: 'marcado' } : { en: 'not flagged', es: 'sin marca' }, lang)}</td>
                  <td className="ct-text ct-wide-only">{pick(c.note, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {changes.length === 0 ? <p className="ct-note" data-state="unavailable">{pick({ en: 'Not available: no behavioural parameter changed between the valuation dates of this document.', es: 'No disponible: ningún parámetro conductual cambió entre las fechas de valoración de este documento.' }, lang)}</p> : null}
          <IrrbbTestsTable variant={sel.data.variant} only={(t) => t.test_id === 'irrbb.behavioural_change_at_breach'} />
        </div>
      </PlotCard>
    </ViewsRow>
  );
}
