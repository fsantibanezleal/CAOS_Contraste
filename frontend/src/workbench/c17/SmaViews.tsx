// C17's SMA group: the Basel III standardised approach on the synthetic bank against the true quantile and the LDA of the
// same histories, and the response of the ILM and of both capitals to one large loss. The bank is synthetic and says so;
// the SMA is not calibrated to the 99.9 percent quantile of any bank, and the document's note is printed. Each draws what
// the c17-outputs document carries.
import { BarChart, Callout, PlotCard, ViewsRow, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable, axisScale } from '../c06/format';
import { useCard, type Bi } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { KeyTable } from './KeyTable';
import { C17TestsTable } from './Tests';
import { DISCRETION_TEXT, capitalOf, cellLabel, cellOf, outputsOf, rungName, text, whole, type C17Sel } from './selection';

const ratio = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { digits: 3 });

/** The SMA of the cell chosen against the true quantile and the LDA capital, and the synthetic bank behind it. */
export function SmaView({ sel }: { sel: C17Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const cell = cellOf(o, sel.years, sel.threshold);
  const sma = cell.sma;
  const bank = o.bank;
  const truth = o.truth.annual_loss_quantile.value_eur;
  const lda = capitalOf(cell, sel.rung).summary;
  const scale = axisScale(Math.max(truth, sma.orc_eur.median, sma.bic_eur, lda?.capital_eur.median ?? 0), 'EUR');
  const label = cellLabel(cell.years, cell.collection_threshold_eur);
  const data = [
    { id: 'truth', label: { en: 'True LDA quantile', es: 'Cuantil LDA verdadero' }, value: truth / scale.div, tone: 'neutral' as const },
    { id: 'lda', label: rungName(sel.rung), value: lda ? lda.capital_eur.median / scale.div : null, tone: 'accent' as const },
    { id: 'sma', label: { en: 'SMA capital (BIC x ILM)', es: 'Capital SMA (BIC x ILM)' }, value: sma.orc_eur.median / scale.div, tone: 'accent' as const, highlight: true },
    { id: 'bic', label: { en: 'BIC alone (ILM = 1)', es: 'Solo el BIC (ILM = 1)' }, value: sma.bic_eur / scale.div },
  ];
  const stat = (id: string, name: { en: string; es: string }, q: { p05: number; p25: number; median: number; p75: number; p95: number }, fmt: (v: number) => string) => (
    <tr key={id} data-stat={id}>
      <td className="ct-text">{pick(name, lang)}</td>
      <td className="ct-wide-only">{fmt(q.p05)}</td>
      <td className="ct-wide-only">{fmt(q.p25)}</td>
      <td>{fmt(q.median)}</td>
      <td className="ct-wide-only">{fmt(q.p75)}</td>
      <td>{fmt(q.p95)}</td>
    </tr>
  );
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `The SMA against the LDA: ${label.en}`, es: `El SMA contra el LDA: ${label.es}` }}
        {...card}
        note={{
          en: 'The standardised measurement approach on a synthetic bank, over the same histories as the LDA. Its capital is the business indicator component times the internal loss multiplier; the multiplier moves with the losses of the histories. It is not calibrated to the 99.9 percent quantile of any bank, so it is drawn beside the true quantile, not against it.',
          es: 'El enfoque estandarizado de medición en un banco sintético, sobre las mismas historias que el LDA. Su capital es el componente del indicador de negocio por el multiplicador de pérdidas internas; el multiplicador se mueve con las pérdidas de las historias. No está calibrado al cuantil 99,9 por ciento de ningún banco, así que se dibuja junto al cuantil verdadero, no contra él.',
        }}
      >
        <ChartOverTable
          chartMin={`${data.length * 2.5 + 3}rem`}
          chart={
            <BarChart
              title={{ en: `SMA capital against the LDA and the true quantile, ${label.en}`, es: `Capital SMA contra el LDA y el cuantil verdadero, ${label.es}` }}
              height="fill"
              orientation="horizontal"
              data={data}
              axis={{ label: { en: `Capital (${pick(scale.unit, 'en')})`, es: `Capital (${pick(scale.unit, 'es')})` }, format: { digits: 3 } }}
            />
          }
        >
          <div data-synthetic={String(bank.synthetic)} data-block="bank">
            <Callout variant="honest" title={pick({ en: 'A synthetic bank, not a real one', es: 'Un banco sintético, no uno real' }, lang)}>
              {pick(bank.notice, lang)}
            </Callout>
            <KeyTable
              table="sma-bank"
              rows={[
                { id: 'bank', label: { en: 'Bank', es: 'Banco' }, value: pick(bank.label, lang) },
                { id: 'assets', label: { en: 'Assets', es: 'Activos' }, value: `${whole(bank.assets_eur, lang)} EUR` },
                {
                  id: 'bi',
                  label: { en: 'Business indicator (BI)', es: 'Indicador de negocio (BI)' },
                  value: pick(
                    {
                      en: `${whole(bank.business_indicator.bi_eur, 'en')} EUR: ${whole(bank.business_indicator.ildc_eur, 'en')} from interest and dividends, ${whole(bank.business_indicator.sc_eur, 'en')} from other operating income and fees, ${whole(bank.business_indicator.fc_eur, 'en')} from the trading and banking books`,
                      es: `${whole(bank.business_indicator.bi_eur, 'es')} EUR: ${whole(bank.business_indicator.ildc_eur, 'es')} de intereses y dividendos, ${whole(bank.business_indicator.sc_eur, 'es')} de otros ingresos operativos y comisiones, ${whole(bank.business_indicator.fc_eur, 'es')} de las carteras de negociación y bancaria`,
                    },
                    lang,
                  ),
                },
                { id: 'bic', label: { en: 'Business indicator component (BIC)', es: 'Componente del indicador de negocio (BIC)' }, value: `${whole(sma.bic_eur, lang)} EUR, ${pick({ en: `bucket ${sma.bucket}`, es: `tramo ${sma.bucket}` }, lang)}` },
                { id: 'discretion', label: { en: 'Discretion applied', es: 'Discreción aplicada' }, value: pick(text(DISCRETION_TEXT, sma.discretion_applied), lang), attrs: { 'data-discretion': sma.discretion_applied } },
              ]}
            />
          </div>
          <p className="ct-note">{pick(sma.note, lang)}</p>
          <table className="caos-table ct-wrap-head" data-table="sma-cell" data-cell={cell.id}>
            <thead>
              <tr>
                <th className="ct-text" style={{ minWidth: '11rem' }}>{pick({ en: 'Across the histories of the cell', es: 'Entre las historias de la celda' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: '5th percentile', es: 'Percentil 5' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: '25th percentile', es: 'Percentil 25' }, lang)}</th>
                <th>{pick({ en: 'Median', es: 'Mediana' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: '75th percentile', es: 'Percentil 75' }, lang)}</th>
                <th>{pick({ en: '95th percentile', es: 'Percentil 95' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {stat('lc', { en: 'Loss component (EUR)', es: 'Componente de pérdidas (EUR)' }, sma.lc_eur, (v) => whole(v, lang))}
              {stat('ilm', { en: 'Internal loss multiplier', es: 'Multiplicador de pérdidas internas' }, sma.ilm, (v) => ratio(v, lang))}
              {stat('orc', { en: 'SMA capital (EUR)', es: 'Capital SMA (EUR)' }, sma.orc_eur, (v) => whole(v, lang))}
              {stat('orc-over-truth', { en: 'SMA capital over the true quantile', es: 'Capital SMA sobre el cuantil verdadero' }, sma.orc_over_true_quantile, (v) => ratio(v, lang))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** What one large loss added to the latest year does to the ILM, the SMA capital and the LDA capital of one history. */
export function ResponseView({ sel }: { sel: C17Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const r = o.sma_response;
  const cell = o.cells.find((c) => c.id === r.cell_id);
  const where = cell ? cellLabel(cell.years, cell.collection_threshold_eur) : { en: r.cell_id, es: r.cell_id };
  if (r.rows.length === 0) {
    return (
      <ViewsRow>
        <PlotCard fill title={{ en: 'Response to one large loss', es: 'Respuesta a una pérdida grande' }} {...card}>
          <p className="ct-note" data-state="unavailable">{pick({ en: 'Not available: the document carries no row of the response to a large loss, so no chart is drawn.', es: 'No disponible: el documento no trae filas de la respuesta a una pérdida grande, así que no se dibuja ningún gráfico.' }, lang)}</p>
        </PlotCard>
      </ViewsRow>
    );
  }
  const scale = axisScale(Math.max(...r.rows.flatMap((x) => [x.orc_eur, x.lda_capital_eur])), 'EUR');
  // the rise of each capital from the first row (no added loss) to the last, computed from the committed rows
  const first = r.rows[0];
  const last = r.rows[r.rows.length - 1];
  const rise = (a: number, b: number): Bi => ({ en: formatNumber(((b - a) / a) * 100, 'en', { decimals: 0 }), es: formatNumber(((b - a) / a) * 100, 'es', { decimals: 0 }) });
  const rises = { sma: rise(first.orc_eur, last.orc_eur), lda: rise(first.lda_capital_eur, last.lda_capital_eur) };
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Response to one large loss', es: 'Respuesta a una pérdida grande' }}
        {...card}
        note={{
          en: `One history (${where.en}, seed ${r.seed}) with a single loss of growing size added to its latest year. The SMA reads the loss through the loss component, so its multiplier and its capital move with it. From no added loss to the largest, the SMA capital rises by ${rises.sma.en} percent and the LDA capital rises by ${rises.lda.en} percent in this history. The business indicator component stays fixed.`,
          es: `Una historia (${where.es}, semilla ${r.seed}) a cuyo último año se le suma una pérdida única de tamaño creciente. El SMA lee la pérdida a través del componente de pérdidas, así que su multiplicador y su capital se mueven con ella. Desde ninguna pérdida sumada hasta la mayor, el capital SMA sube ${rises.sma.es} por ciento y el capital LDA sube ${rises.lda.es} por ciento en esta historia. El componente del indicador de negocio queda fijo.`,
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: r.rows.map((x) => x.added_loss_eur / 1e6), label: { en: 'Added loss', es: 'Pérdida sumada' }, unit: { en: 'm EUR', es: 'M EUR' }, format: { decimals: 0 } }}
              y={{ label: { en: `Capital (${pick(scale.unit, 'en')})`, es: `Capital (${pick(scale.unit, 'es')})` }, format: { digits: 3 } }}
              series={[
                { label: { en: 'SMA capital', es: 'Capital SMA' }, values: r.rows.map((x) => x.orc_eur / scale.div), color: '--color-accent', width: 2.6 },
                { label: { en: 'LDA capital, 99.9%', es: 'Capital LDA, 99,9%' }, values: r.rows.map((x) => x.lda_capital_eur / scale.div), color: '--color-magenta', width: 2.2, dash: [6, 3] },
              ]}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="sma-response" data-cell={r.cell_id}>
            <thead>
              <tr>
                <th>{pick({ en: 'Loss added (EUR)', es: 'Pérdida sumada (EUR)' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Loss component (EUR)', es: 'Componente de pérdidas (EUR)' }, lang)}</th>
                <th>{pick({ en: 'Multiplier (ILM)', es: 'Multiplicador (ILM)' }, lang)}</th>
                <th>{pick({ en: 'SMA capital (EUR)', es: 'Capital SMA (EUR)' }, lang)}</th>
                <th>{pick({ en: 'LDA capital (EUR)', es: 'Capital LDA (EUR)' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {r.rows.map((x) => (
                <tr key={x.added_loss_eur} data-added={x.added_loss_eur}>
                  <td>{whole(x.added_loss_eur, lang)}</td>
                  <td className="ct-wide-only">{whole(x.lc_eur, lang)}</td>
                  <td>{ratio(x.ilm, lang)}</td>
                  <td>{whole(x.orc_eur, lang)}</td>
                  <td>{whole(x.lda_capital_eur, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ct-note">{pick({ en: `Business indicator component of the synthetic bank: ${whole(r.bic_eur, 'en')} EUR.`, es: `Componente del indicador de negocio del banco sintético: ${whole(r.bic_eur, 'es')} EUR.` }, lang)}</p>
          <C17TestsTable variant={sel.data.variant} host="response" />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
