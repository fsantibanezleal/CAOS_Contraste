// C16's buffer group: the counterbalancing capacity by class with its haircuts and the pledged securities, the CBC with and
// without the held-to-maturity loss (the Bank Term Funding Program's par row is a counterfactual after the run, and is
// labelled one), the LCR composition with the inflow cap (a Basel formula on call-report aggregates, never the bank's
// reported ratio), and the time block of 2021-12-31 and 2022-06-30 as the HTM losses grew. A null block shows "not
// available" with its reason; nothing here is a number the document does not hold.
import { BarChart, Callout, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { MaybeNumber } from '../c06/format';
import { useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { es } from './localise';
import { CLASS_TEXT, HAIRCUT_RULE_TEXT, LCR_CATEGORY_TEXT, axisOf, outputsOf, text, type C16Sel } from './selection';
import { ChartAbove, MONEY_UNIT, NOT_SCENARIO, SHARE, SurvivalCell, UnavailableCard, cell } from './C16Common';

const BASIS_TEXT: Record<string, BiText> = {
  'amortised-cost': { en: 'amortised cost', es: 'costo amortizado' },
  'fair-value': { en: 'fair value', es: 'valor razonable' },
};

/** The CBC by class at the valuation date with the haircut and its rule, the pledged securities and the basis of the held-to-maturity book. */
export function CbcView({ sel }: { sel: C16Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The counterbalancing capacity', es: 'La capacidad de contrapeso' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SCENARIO} />;
  const c = o.cbc;
  const axis = axisOf(c.classes.map((k) => k.liquidity_value));
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `The counterbalancing capacity at ${c.as_of}`, es: `La capacidad de contrapeso al ${c.as_of}` }}
        {...card}
        note={{
          en: 'The unencumbered liquid assets after the haircuts: liquidity value = (value used minus the encumbered part) x (1 minus the haircut). The haircuts are the central bank framework rows in force on 2023-03-10 (the duration bucket of each is a convention); the held-to-maturity book is at the valuation basis the document states.',
          es: 'Los activos líquidos sin gravamen tras los recortes: valor de liquidez = (valor usado menos la parte con gravamen) x (1 menos el recorte). Los recortes son las filas del marco del banco central vigentes el 2023-03-10 (el tramo de duración de cada una es una convención); la cartera mantenida al vencimiento está en la base de valoración que declara el documento.',
        }}
      >
        <ChartAbove
          chartHeight="17rem"
          chart={
            <BarChart
              title={{ en: 'Liquidity value of the CBC by class', es: 'Valor de liquidez del CBC por clase' }}
              height="fill"
              orientation="horizontal"
              data={c.classes.map((k) => ({ id: k.class_id, label: text(CLASS_TEXT, k.class_id), value: k.liquidity_value / axis.div, tone: 'accent' as const, hint: k.label }))}
              axis={{ label: { en: 'Liquidity value after the haircut', es: 'Valor de liquidez tras el recorte' }, unit: axis.unit, format: { digits: 4 } }}
            />
          }
        >
          <dl className="ct-defs" data-table="c16-cbc" data-basis={c.htm_valuation_basis}>
            <dt>{pick({ en: 'Valuation of the held-to-maturity book', es: 'Valoración de la cartera mantenida al vencimiento' }, lang)}</dt>
            <dd>{pick(BASIS_TEXT[c.htm_valuation_basis], lang)}</dd>
            <dt>{pick({ en: 'Haircut framework', es: 'Marco de recortes' }, lang)}</dt>
            <dd>{`${pick(c.haircut_framework.label, lang)}, ${c.haircut_framework.effective_from} ${pick({ en: 'to', es: 'al' }, lang)} ${c.haircut_framework.effective_to}`}</dd>
            <dt>{pick({ en: `Pledged securities, ${c.pledged.field} (${pick(MONEY_UNIT, 'en')})`, es: `Valores prendados, ${c.pledged.field} (${pick(MONEY_UNIT, 'es')})` }, lang)}</dt>
            <dd data-pledged={c.pledged.share_of_securities}>{`${cell(c.pledged.amount, lang)}, ${SHARE(c.pledged.share_of_securities, lang)} ${pick({ en: 'of the securities, encumbered and out of the CBC', es: 'de los valores, con gravamen y fuera del CBC' }, lang)}`}</dd>
            <dt>{pick({ en: `CBC, total (${pick(MONEY_UNIT, 'en')})`, es: `CBC, total (${pick(MONEY_UNIT, 'es')})` }, lang)}</dt>
            <dd>{cell(c.total_liquidity_value, lang)}</dd>
          </dl>
          <table className="caos-table ct-wrap-head" data-table="c16-cbc-classes">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Class', es: 'Clase' }, lang)}</th>
                <th>{pick({ en: 'Carrying value', es: 'Valor en libros' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Fair value', es: 'Valor razonable' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Encumbered', es: 'Con gravamen' }, lang)}</th>
                <th>{pick({ en: 'Haircut', es: 'Recorte' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Haircut rule', es: 'Regla del recorte' }, lang)}</th>
                <th>{pick({ en: 'Liquidity value', es: 'Valor de liquidez' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {c.classes.map((k) => (
                <tr key={k.class_id} data-class={k.class_id}>
                  <td className="ct-text">{pick(k.label, lang)}</td>
                  <td>{cell(k.carrying_value, lang)}</td>
                  <td className="ct-wide-only" data-na={k.fair_value === null ? 'true' : undefined}>{cell(k.fair_value, lang)}</td>
                  <td className="ct-wide-only">{cell(k.encumbered, lang)}</td>
                  <td>{SHARE(k.haircut.value, lang)}</td>
                  <td className="ct-text ct-wide-only">{pick(text(HAIRCUT_RULE_TEXT, k.haircut.rule), lang)}</td>
                  <td>{cell(k.liquidity_value, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartAbove>
      </PlotCard>
    </ViewsRow>
  );
}

/** The CBC with and without the HTM loss, and the par row of the Bank Term Funding Program as a labelled counterfactual after the run. */
export function HtmView({ sel }: { sel: C16Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The CBC with and without the HTM loss', es: 'El CBC con y sin la pérdida HTM' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SCENARIO} />;
  const h = o.htm;
  if (!h) {
    return <UnavailableCard sel={sel} title={title} reason={o.htm_reason ?? { en: 'Not available: this variant takes the held-to-maturity book at amortised cost.', es: 'No disponible: esta variante toma la cartera mantenida al vencimiento a costo amortizado.' }} />;
  }
  const axis = axisOf([h.cbc_without_loss, h.cbc_with_loss, h.btfp_par.cbc_at_par]);
  const rv = h.revaluation;
  const reported = h.reported;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'Unrealised losses on held-to-maturity securities reduce the CBC that can be monetised. The loss is the reported fair value less the amortised cost, applied to the securities book as a whole: a stated assumption, never a reported loss by type. The par row is a counterfactual: the Bank Term Funding Program was announced on 2023-03-12, after the run.',
          es: 'Las pérdidas no realizadas de los valores mantenidos al vencimiento reducen el CBC que se puede monetizar. La pérdida es el valor razonable reportado menos el costo amortizado, aplicada al libro de valores completo: un supuesto declarado, nunca una pérdida reportada por tipo. La fila a la par es un contrafactual: el Programa de Financiamiento a Plazo Bancario se anunció el 2023-03-12, después de la corrida.',
        }}
      >
        <ChartAbove
          chartHeight="12rem"
          chart={
            <BarChart
              title={{ en: 'The CBC with and without the HTM loss, and at par after the run', es: 'El CBC con y sin la pérdida HTM, y a la par tras la corrida' }}
              height="fill"
              orientation="horizontal"
              data={[
                { id: 'without-loss', label: { en: 'Without the loss, amortised cost', es: 'Sin la pérdida, costo amortizado' }, value: h.cbc_without_loss / axis.div, tone: 'good' },
                { id: 'with-loss', label: { en: 'With the loss, reported fair values', es: 'Con la pérdida, valores razonables reportados' }, value: h.cbc_with_loss / axis.div, tone: 'bad' },
                { id: 'btfp-par', label: { en: 'Counterfactual: BTFP par, after the run', es: 'Contrafactual: BTFP a la par, tras la corrida' }, value: h.btfp_par.cbc_at_par / axis.div, tone: 'neutral', hint: h.btfp_par.label },
              ]}
              axis={{ label: { en: 'Counterbalancing capacity', es: 'Capacidad de contrapeso' }, unit: axis.unit, format: { digits: 4 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c16-htm">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'CBC', es: 'CBC' }, lang)}</th>
                <th>{pick({ en: `Amount (${pick(MONEY_UNIT, 'en')})`, es: `Monto (${pick(MONEY_UNIT, 'es')})` }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Note', es: 'Nota' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              <tr data-row="without-loss">
                <td className="ct-text">{pick({ en: 'Without the HTM loss (amortised cost)', es: 'Sin la pérdida HTM (costo amortizado)' }, lang)}</td>
                <td>{cell(h.cbc_without_loss, lang)}</td>
                <td className="ct-text ct-wide-only">{pick({ en: 'The held-to-maturity book at its carrying value.', es: 'La cartera mantenida al vencimiento a su valor en libros.' }, lang)}</td>
              </tr>
              <tr data-row="with-loss">
                <td className="ct-text">{pick({ en: 'With the HTM loss (reported fair values)', es: 'Con la pérdida HTM (valores razonables reportados)' }, lang)}</td>
                <td>{cell(h.cbc_with_loss, lang)}</td>
                <td className="ct-text ct-wide-only">{pick(h.application.statement, lang)}</td>
              </tr>
              <tr data-row="removed">
                <td className="ct-text">{pick({ en: 'Removed by the loss', es: 'Retirado por la pérdida' }, lang)}</td>
                <td>{cell(h.cbc_removed, lang)}</td>
                <td className="ct-text ct-wide-only">{pick({ en: 'The difference of the two rows above.', es: 'La diferencia de las dos filas de arriba.' }, lang)}</td>
              </tr>
              <tr data-row="btfp-par" data-counterfactual="true">
                <td className="ct-text">{pick({ en: 'Counterfactual: BTFP par valuation (announced 2023-03-12, after the run)', es: 'Contrafactual: valoración a la par del BTFP (anunciada el 2023-03-12, tras la corrida)' }, lang)}</td>
                <td>{cell(h.btfp_par.cbc_at_par, lang)}</td>
                <td className="ct-text ct-wide-only">{pick(h.btfp_par.label, lang)}</td>
              </tr>
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head" data-table="c16-htm-reported">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Reported securities', es: 'Valores reportados' }, lang)}</th>
                <th>{pick({ en: 'Amortised cost', es: 'Costo amortizado' }, lang)}</th>
                <th>{pick({ en: 'Fair value', es: 'Valor razonable' }, lang)}</th>
                <th>{pick({ en: 'Unrealised', es: 'No realizada' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              <tr data-book="htm">
                <td className="ct-text">{pick({ en: 'Held to maturity', es: 'Mantenidos al vencimiento' }, lang)}</td>
                <td>{cell(reported.htm_amortised_cost, lang)}</td>
                <td>{cell(reported.htm_fair_value, lang)}</td>
                <td>{cell(reported.htm_unrealised, lang)}</td>
              </tr>
              <tr data-book="afs">
                <td className="ct-text">{pick({ en: 'Available for sale', es: 'Disponibles para la venta' }, lang)}</td>
                <td>{cell(reported.afs_amortised_cost, lang)}</td>
                <td>{cell(reported.afs_fair_value, lang)}</td>
                <td>{cell(reported.afs_unrealised, lang)}</td>
              </tr>
            </tbody>
          </table>
          <dl className="ct-defs" data-table="c16-htm-revaluation" data-revaluation={rv.status}>
            <dt>{pick({ en: 'Revaluation of the HTM book from its maturity profile', es: 'Revaluación de la cartera HTM desde su perfil de vencimientos' }, lang)}</dt>
            <dd>{pick(rv.status === 'evaluated' ? { en: 'evaluated against the Treasury curve', es: 'evaluada contra la curva del Tesoro' } : { en: 'not evaluated', es: 'no evaluada' }, lang)}</dd>
            <dt>{pick({ en: 'Model fair value', es: 'Valor razonable del modelo' }, lang)}</dt>
            <dd data-na={rv.model_fair_value === null ? 'true' : undefined}>
              <MaybeNumber value={rv.model_fair_value} reason={rv.reason ? pick(rv.reason, lang) : null} format={(v) => cell(v, lang)} />
            </dd>
            <dt>{pick({ en: 'Reported fair value', es: 'Valor razonable reportado' }, lang)}</dt>
            <dd>{cell(rv.reported_fair_value, lang)}</dd>
            <dt>{pick({ en: 'Difference, model less reported', es: 'Diferencia, modelo menos reportado' }, lang)}</dt>
            <dd data-na={rv.difference === null ? 'true' : undefined}>
              {rv.difference === null ? formatNumber(null, lang) : `${cell(rv.difference, lang)} (${SHARE(rv.relative_difference, lang)})`}
            </dd>
            <dt>{pick({ en: 'Curve', es: 'Curva' }, lang)}</dt>
            <dd>{es(rv.curve_source, lang)}</dd>
          </dl>
        </ChartAbove>
      </PlotCard>
    </ViewsRow>
  );
}

/** The LCR of the variant: HQLA, outflows, inflows with the 75 percent cap and the ratio, under every mapping of the uninsured balance. */
export function LcrView({ sel }: { sel: C16Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The LCR composition', es: 'La composición del LCR' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SCENARIO} />;
  const l = o.lcr;
  if (!l) {
    return <UnavailableCard sel={sel} title={title} reason={o.lcr_reason ?? { en: 'Not available: this variant does not run the LCR.', es: 'No disponible: esta variante no corre el LCR.' }} />;
  }
  const axis = axisOf([l.hqla.hqla, l.total_outflows, l.total_inflows, l.inflows_counted, l.net_outflows]);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'HQLA after the 40 and 15 percent caps against the 30-day stressed outflows, less the inflows counted, which are capped at 75 percent of the outflows. The categories are an assumption: the call report carries no customer type, so the uninsured balance is mapped to a category by a named convention, with the ratio under each plausible class.',
          es: 'HQLA tras los topes de 40 y 15 por ciento contra las salidas bajo estrés a 30 días, menos las entradas contadas, que tienen un tope de 75 por ciento de las salidas. Las categorías son un supuesto: el reporte no trae el tipo de cliente, así que el saldo no asegurado se asigna a una categoría por una convención con nombre, con la razón bajo cada clase plausible.',
        }}
      >
        <ChartAbove
          chartHeight="13.5rem"
          chart={
            <BarChart
              title={{ en: 'HQLA, outflows, inflows and net outflows of the LCR', es: 'HQLA, salidas, entradas y salidas netas del LCR' }}
              height="fill"
              orientation="horizontal"
              data={[
                { id: 'hqla', label: { en: 'HQLA after the caps', es: 'HQLA tras los topes' }, value: l.hqla.hqla / axis.div, tone: 'good' },
                { id: 'outflows', label: { en: 'Outflows, 30 days', es: 'Salidas, 30 días' }, value: l.total_outflows / axis.div, tone: 'bad' },
                { id: 'inflows', label: { en: 'Inflows, before the cap', es: 'Entradas, antes del tope' }, value: l.total_inflows / axis.div, tone: 'neutral' },
                { id: 'counted', label: { en: `Inflows counted (cap ${SHARE(l.inflow_cap, 'en')} of outflows)`, es: `Entradas contadas (tope ${SHARE(l.inflow_cap, 'es')} de las salidas)` }, value: l.inflows_counted / axis.div, tone: 'accent' },
                { id: 'net', label: { en: 'Net outflows', es: 'Salidas netas' }, value: l.net_outflows / axis.div, tone: 'warn' },
              ]}
              axis={{ label: { en: 'LCR components', es: 'Componentes del LCR' }, unit: axis.unit, format: { digits: 4 } }}
            />
          }
        >
          <Callout variant="honest" title={pick({ en: 'A formula on aggregates, not the bank\'s LCR', es: 'Una fórmula sobre agregados, no el LCR del banco' }, lang)}>
            <span data-reported-or-regulatory={String(l.reported_or_regulatory)}>
              <strong>{pick({ en: 'A Basel formula on call-report aggregates, not the bank\'s reported LCR.', es: 'Una fórmula de Basilea sobre agregados del reporte de llamada, no el LCR reportado del banco.' }, lang)}</strong>{' '}
              {pick(l.statement, lang)}
            </span>
          </Callout>
          <dl className="ct-defs" data-table="c16-lcr">
            <dt>{pick({ en: 'LCR ratio, this mapping', es: 'Razón LCR, este mapeo' }, lang)}</dt>
            <dd data-ratio={l.ratio}>{SHARE(l.ratio, lang)}</dd>
            <dt>{pick({ en: 'Cap on the inflows', es: 'Tope de las entradas' }, lang)}</dt>
            <dd>{`${SHARE(l.inflow_cap, lang)} ${pick({ en: 'of the outflows', es: 'de las salidas' }, lang)}`}</dd>
            <dt>{pick({ en: `Inflows counted (${pick(MONEY_UNIT, 'en')})`, es: `Entradas contadas (${pick(MONEY_UNIT, 'es')})` }, lang)}</dt>
            <dd>{cell(l.inflows_counted, lang)}</dd>
            <dt>{pick({ en: `Net outflows (${pick(MONEY_UNIT, 'en')})`, es: `Salidas netas (${pick(MONEY_UNIT, 'es')})` }, lang)}</dt>
            <dd>{cell(l.net_outflows, lang)}</dd>
            <dt>{pick({ en: 'Level 2 and Level 2B shares of HQLA', es: 'Partes de Nivel 2 y Nivel 2B del HQLA' }, lang)}</dt>
            <dd>{l.hqla.l2_share === null || l.hqla.l2b_share === null
              ? pick(l.hqla.shares_reason ?? { en: 'Not available: the HQLA stock is empty.', es: 'No disponible: el stock de HQLA está vacío.' }, lang)
              : `${SHARE(l.hqla.l2_share, lang)} (${pick({ en: 'cap', es: 'tope' }, lang)} ${SHARE(l.hqla.caps.l2_cap, lang)}), ${SHARE(l.hqla.l2b_share, lang)} (${pick({ en: 'cap', es: 'tope' }, lang)} ${SHARE(l.hqla.caps.l2b_cap, lang)})`}</dd>
          </dl>
          <table className="caos-table ct-wrap-head" data-table="c16-lcr-flows">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Category', es: 'Categoría' }, lang)}</th>
                <th>{pick({ en: 'Balance', es: 'Saldo' }, lang)}</th>
                <th>{pick({ en: 'Rate', es: 'Tasa' }, lang)}</th>
                <th>{pick({ en: 'Amount', es: 'Monto' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Basel paragraph', es: 'Párrafo de Basilea' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {l.outflows.map((r) => (
                <tr key={`o-${r.category}`} data-category={r.category} data-flow="outflow">
                  <td className="ct-text">{`${pick({ en: 'Outflow', es: 'Salida' }, lang)}: ${pick(text(LCR_CATEGORY_TEXT, r.category), lang)}`}</td>
                  <td>{cell(r.balance, lang)}</td>
                  <td>{SHARE(r.rate, lang)}</td>
                  <td>{cell(r.amount, lang)}</td>
                  <td className="ct-text ct-wide-only">{es(r.reference, lang)}</td>
                </tr>
              ))}
              {l.inflows.map((r) => (
                <tr key={`i-${r.category}`} data-category={r.category} data-flow="inflow">
                  <td className="ct-text">{`${pick({ en: 'Inflow', es: 'Entrada' }, lang)}: ${pick(text(LCR_CATEGORY_TEXT, r.category), lang)}`}</td>
                  <td>{cell(r.balance, lang)}</td>
                  <td>{SHARE(r.rate, lang)}</td>
                  <td>{cell(r.amount, lang)}</td>
                  <td className="ct-text ct-wide-only">{es(r.reference, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="caos-table ct-wrap-head" data-table="c16-lcr-mapping">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Mapping of the uninsured balance', es: 'Mapeo del saldo no asegurado' }, lang)}</th>
                <th>{pick({ en: 'Uninsured outflow', es: 'Salida no asegurada' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Net outflows', es: 'Salidas netas' }, lang)}</th>
                <th>{pick({ en: 'LCR, Basel formula', es: 'LCR, fórmula de Basilea' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {l.mapping_sensitivity.map((m) => (
                <tr key={m.mapping_id} data-mapping={m.mapping_id} data-chosen={m.mapping_id === sel.mapping ? 'true' : undefined} className={m.mapping_id === sel.mapping ? 'ct-current' : undefined}>
                  <td className="ct-text">{`${pick(text(LCR_CATEGORY_TEXT, m.lcr_category), lang)}${m.mapping_id === 'central' ? ` (${pick({ en: 'central', es: 'central' }, lang)})` : ''}`}</td>
                  <td>{cell(m.uninsured_outflow, lang)}</td>
                  <td className="ct-wide-only">{cell(m.net_outflows, lang)}</td>
                  <td>{SHARE(m.ratio, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ct-note">{pick(l.below_100_note, lang)}</p>
        </ChartAbove>
      </PlotCard>
    </ViewsRow>
  );
}

/** The unrealised HTM loss of a variant with no HTM block: the fair value less the amortised cost of the held-to-maturity line of its own balance sheet (U16-R2 b08 m2). */
export function htmLossOfBalanceSheet(items: ReadonlyArray<{ item_id: string; amount?: number | null; fair_value?: number | null }>): number | null {
  const htm = items.find((i) => i.item_id === 'securities-htm');
  return htm && typeof htm.amount === 'number' && typeof htm.fair_value === 'number' ? htm.fair_value - htm.amount : null;
}

/** The call-report dates before the run: deposits, the HTM loss, the CBC on both bases, the survival period and the LCR as the losses grew. */
export function TimeBlockView({ sel }: { sel: C16Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const title: BiText = { en: 'The time block: as the HTM losses grew', es: 'El bloque temporal: a medida que crecieron las pérdidas HTM' };
  if (!sel) return <Pending />;
  if (!o) return <UnavailableCard sel={sel} title={title} reason={NOT_SCENARIO} />;
  const block = o.time_block;
  const t0 = Date.parse(`${block[0].as_of}T00:00:00Z`);
  const day = (d: string) => Math.round((Date.parse(`${d}T00:00:00Z`) - t0) / 86400000);
  const own = { as_of: o.valuation_date, basis: o.cbc.htm_valuation_basis, cbc: o.cbc.total_liquidity_value, loss: o.htm?.reported.htm_unrealised ?? htmLossOfBalanceSheet(o.balance_sheet.items) };
  const dates = [...block.map((t) => t.as_of), own.as_of];
  const axis = axisOf([...block.flatMap((t) => [t.cbc_amortised_basis, t.cbc_fair_value_basis, t.htm_unrealised_loss]), own.cbc]);
  const dep = o.balance_sheet.deposits;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'Two earlier call-report dates, 2021-12-31 and 2022-06-30, beside the valuation date of the document: the CBC on the amortised-cost and the fair-value basis, the unrealised loss on the held-to-maturity book, the survival period and the LCR. The last date shows the basis the document itself uses; the other basis is not available for it.',
          es: 'Dos fechas anteriores de los reportes de llamada, 2021-12-31 y 2022-06-30, junto a la fecha de valoración del documento: el CBC en la base de costo amortizado y en la de valor razonable, la pérdida no realizada de la cartera mantenida al vencimiento, el periodo de supervivencia y el LCR. La última fecha muestra la base que usa el propio documento; la otra base no está disponible para ella.',
        }}
      >
        <ChartAbove
          chartHeight="14rem"
          chart={
            <UPlotChart
              height="fill"
              x={{ values: dates.map(day), label: { en: `Days after ${block[0].as_of}`, es: `Días después del ${block[0].as_of}` }, format: { decimals: 0 } }}
              marks={dates.map((d) => ({ x: day(d), label: { en: d, es: d } }))}
              y={{ label: { en: `CBC, HTM loss (${pick(axis.unit, 'en')})`, es: `CBC, pérdida HTM (${pick(axis.unit, 'es')})` }, format: { digits: 4 } }}
              series={[
                { label: { en: 'CBC, amortised-cost basis', es: 'CBC, base de costo amortizado' }, values: [...block.map((t) => t.cbc_amortised_basis / axis.div), own.basis === 'amortised-cost' ? own.cbc / axis.div : null], color: '--color-good', width: 2.6 },
                { label: { en: 'CBC, fair-value basis', es: 'CBC, base de valor razonable' }, values: [...block.map((t) => t.cbc_fair_value_basis / axis.div), own.basis === 'fair-value' ? own.cbc / axis.div : null], color: '--color-accent', width: 2.6 },
                { label: { en: 'Unrealised HTM loss', es: 'Pérdida HTM no realizada' }, values: [...block.map((t) => t.htm_unrealised_loss / axis.div), own.loss === null ? null : own.loss / axis.div], color: '--color-bad', width: 2.4 },
              ]}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="c16-time-block">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Date', es: 'Fecha' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'DEP', es: 'DEP' }, lang)}</th>
                <th>{pick({ en: 'Uninsured of DEP', es: 'No asegurado de DEP' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Uninsured of DEPDOM', es: 'No asegurado de DEPDOM' }, lang)}</th>
                <th>{pick({ en: 'HTM loss', es: 'Pérdida HTM' }, lang)}</th>
                <th>{pick({ en: 'CBC, amortised cost', es: 'CBC, costo amortizado' }, lang)}</th>
                <th>{pick({ en: 'CBC, fair value', es: 'CBC, valor razonable' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Survival period', es: 'Periodo de supervivencia' }, lang)}</th>
                <th>{pick({ en: 'LCR, Basel formula', es: 'LCR, fórmula de Basilea' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {block.map((t) => (
                <tr key={t.as_of} data-date={t.as_of}>
                  <td className="ct-text">{t.as_of}</td>
                  <td className="ct-wide-only">{cell(t.deposits.dep, lang)}</td>
                  <td>{SHARE(t.deposits.uninsured_share_of_dep, lang)}</td>
                  <td className="ct-wide-only">{SHARE(t.deposits.uninsured_share_of_depdom, lang)}</td>
                  <td>{cell(t.htm_unrealised_loss, lang)}</td>
                  <td>{cell(t.cbc_amortised_basis, lang)}</td>
                  <td>{cell(t.cbc_fair_value_basis, lang)}</td>
                  <SurvivalCell s={t.survival} className="ct-text" />
                  <td data-na={t.lcr_ratio === null ? 'true' : undefined}>{t.lcr_ratio === null ? formatNumber(null, lang) : SHARE(t.lcr_ratio, lang)}</td>
                </tr>
              ))}
              <tr data-date={own.as_of} data-own="true">
                <td className="ct-text">{`${own.as_of} (${pick({ en: 'this document', es: 'este documento' }, lang)})`}</td>
                <td className="ct-wide-only">{cell(dep.dep, lang)}</td>
                <td>{SHARE(dep.uninsured_share_of_dep, lang)}</td>
                <td className="ct-wide-only">{SHARE(dep.uninsured_share_of_depdom, lang)}</td>
                <td data-na={own.loss === null ? 'true' : undefined}>{cell(own.loss, lang)}</td>
                <td data-na={own.basis === 'amortised-cost' ? undefined : 'true'}>{own.basis === 'amortised-cost' ? cell(own.cbc, lang) : formatNumber(null, lang)}</td>
                <td data-na={own.basis === 'fair-value' ? undefined : 'true'}>{own.basis === 'fair-value' ? cell(own.cbc, lang) : formatNumber(null, lang)}</td>
                {o.path ? <SurvivalCell s={o.path.survival} className="ct-text" /> : <td className="ct-text" data-na="true">{formatNumber(null, lang)}</td>}
                <td data-na={o.lcr ? undefined : 'true'}>{o.lcr ? SHARE(o.lcr.ratio, lang) : formatNumber(null, lang)}</td>
              </tr>
            </tbody>
          </table>
          <p className="ct-note">{pick({ en: `Money in ${pick(MONEY_UNIT, 'en')}. The survival period is a day or survives the horizon of its variant; the LCR has no daily path and the other variants have no LCR.`, es: `Dinero en ${pick(MONEY_UNIT, 'es')}. El periodo de supervivencia es un día o sobrevive el horizonte de su variante; el LCR no tiene trayectoria diaria y las otras variantes no tienen LCR.` }, lang)}</p>
        </ChartAbove>
      </PlotCard>
    </ViewsRow>
  );
}

