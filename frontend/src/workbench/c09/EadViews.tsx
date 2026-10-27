// C09's EAD group: the back-test of each EAD model in currency by utilisation band, the models themselves (kind,
// design, treatment, what was clipped for the fit) and the EAD floor with the small-undrawn rule. Each draws what the
// c09-outputs and c09-models documents carry; an amount is in the currency of the document, never a bare number.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { LIGHT_TEXT } from '../../lib/policy';
import { MaybeNumber, axisScale, money } from '../c06/format';
import { ChartAbove } from '../c16/C16Common';
import { U6TestsTable, p2, useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { COVARIATE_TEXT, DESIGN_TEXT, TREATMENT_TEXT, bandLabel, bandsOf, facilityLabel, fitOf, kindText, modelLabel, outputsOf, text, type C09Sel } from './selection';
import { rangeText } from '../c08/words';

const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });

/** Predicted against realised EAD by utilisation band for the model in focus, in the currency of the document. */
export function BacktestView({ sel }: { sel: C09Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const b = o.ead_backtest;
  const rows = b.rows.filter((r) => r.model_id === sel.model).sort((x, y) => x.utilisation_lower - y.utilisation_lower);
  const label = modelLabel(o, sel.model);
  if (rows.length === 0) {
    return (
      <ViewsRow>
        <PlotCard fill title={{ en: 'EAD back-test by utilisation band', es: 'Prueba retrospectiva de la EAD por tramo de utilización' }} {...card}>
          <p className="caos-pending" data-state="unavailable">
            {pick({ en: 'Not available: this document has no back-test row for the EAD model in focus.', es: 'No disponible: este documento no trae filas de prueba retrospectiva para el modelo de EAD en foco.' }, lang)}
          </p>
        </PlotCard>
      </ViewsRow>
    );
  }
  const scale = axisScale(Math.max(...rows.flatMap((r) => [r.predicted_ead, r.realised_ead])), b.currency);
  const ccy = b.currency;
  return (
    // split, not scrolled (ADR-0071 rule 6; R3 c10 M2): the bands under a drawing of fixed height, the tests a sub-view of their own
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `EAD back-test by utilisation band: ${label.en}`, es: `Prueba retrospectiva de la EAD por tramo de utilización: ${label.es}` }}
        {...card}
        note={{
          en: 'Each band groups the facilities by their utilisation at the reference date. The model predicts an exposure at default; the realised exposure is what the defaults drew. The gap is predicted minus realised, in currency, and the light is the engine\'s.',
          es: 'Cada tramo agrupa las líneas por su utilización en la fecha de referencia. El modelo predice una exposición al incumplimiento; la exposición realizada es lo que usaron los incumplimientos. La brecha es predicha menos realizada, en moneda, y la luz es la del motor.',
        }}
      >
        <ChartAbove
          chartHeight="13rem"
          chart={
            <UPlotChart
              height="fill"
              x={{ values: rows.map((r) => r.utilisation_lower), label: { en: 'Utilisation at the reference date (lower edge of the band)', es: 'Utilización en la fecha de referencia (borde inferior del tramo)' }, format: { percent: true, decimals: 0 } }}
              y={{ label: { en: `Total EAD of the band (${pick(scale.unit, 'en')})`, es: `EAD total del tramo (${pick(scale.unit, 'es')})` }, format: { digits: 4 } }}
              series={[
                { label: { en: 'Realised EAD', es: 'EAD realizada' }, values: rows.map((r) => r.realised_ead / scale.div), color: '--color-accent', width: 2.6 },
                { label: { en: 'Predicted EAD', es: 'EAD predicha' }, values: rows.map((r) => (r.prediction_flag === 'in-range' ? r.predicted_ead / scale.div : null)), color: '--color-magenta', width: 2, dash: [6, 3] },
              ]}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="ead-backtest">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Utilisation band', es: 'Tramo de utilización' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Facilities', es: 'Líneas' }, lang)}</th>
                <th>{pick({ en: `Predicted (${ccy})`, es: `Predicha (${ccy})` }, lang)}</th>
                <th>{pick({ en: `Realised (${ccy})`, es: `Realizada (${ccy})` }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: `Gap (${ccy})`, es: `Brecha (${ccy})` }, lang)}</th>
                <th>{pick({ en: 'Relative gap', es: 'Brecha relativa' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Light', es: 'Luz' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.band_id} data-band={r.band_id} data-light={r.light} className={r.band_id === sel.band ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(bandLabel({ lower: r.utilisation_lower, upper: r.utilisation_upper }), lang)}</td>
                  <td className="ct-wide-only">{count(r.n, lang)}</td>
                  <td data-flag={r.prediction_flag}>
                    {money(r.predicted_ead, lang, ccy)}
                    {r.prediction_flag === 'outside-range' ? <span className="ct-note">{pick({ en: ' (outside the range of the fit)', es: ' (fuera del rango del ajuste)' }, lang)}</span> : null}
                  </td>
                  <td>{money(r.realised_ead, lang, ccy)}</td>
                  <td className="ct-wide-only">{money(r.gap, lang, ccy)}</td>
                  <td>{p2(r.relative_gap, lang)}</td>
                  <td className={`ct-text ct-light ct-light-${r.light}`}>
                    <span className="ct-light-word">{pick(LIGHT_TEXT[r.light], lang)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartAbove>
      </PlotCard>
    </ViewsRow>
  );
}

/** The EAD back-test of every band, a sub-view of its own (R3 c10 M2). */
export function BacktestTestsView({ sel }: { sel: C09Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  return (
    <ViewsRow>
      <PlotCard fill title={{ en: 'The back-test of every band', es: 'La prueba retrospectiva de cada tramo' }} {...card}>
        <div className="ct-scroll" data-caos-flow="">
          <U6TestsTable variant={sel.data.variant} modelLabel={(id) => pick(modelLabel(o, id), lang)} only={(t) => t.test_id === 'lgd_ead.ead_backtest_by_band'} />
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

/** The EAD models: what each estimates, with which design and treatment, and what was clipped for its fit. */
export function ModelsView({ sel }: { sel: C09Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const bandCount = bandsOf(o).length;
  const none = pick({ en: 'none', es: 'ninguna' }, lang);
  const notApplicable = pick({ en: 'not applicable', es: 'no aplica' }, lang);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The EAD models', es: 'Los modelos de EAD' }}
        {...card}
        note={{
          en: 'A CCF model estimates the share of the undrawn amount that is drawn by default; a direct model estimates the exposure itself. Only a direct EAD model clips observations for its fit, and it says how many.',
          es: 'Un modelo de CCF estima la parte del monto no utilizado que se usa al incumplir; un modelo directo estima la exposición misma. Solo un modelo directo de EAD recorta observaciones para su ajuste, y dice cuántas.',
        }}
      >
        <div className="ct-scroll" data-caos-flow="">
          <table className="caos-table ct-wrap-head" data-table="ead-models" data-bands={bandCount}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Model', es: 'Modelo' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Design', es: 'Diseño' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Treatment', es: 'Tratamiento' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Covariates', es: 'Covariables' }, lang)}</th>
                <th>{pick({ en: 'Clipped below', es: 'Recortados abajo' }, lang)}</th>
                <th>{pick({ en: 'Clipped above', es: 'Recortados arriba' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.ead_models.map((m) => (
                <tr key={m.model_id} data-model={m.model_id} data-kind={m.kind} className={m.model_id === sel.model ? 'ct-current' : undefined}>
                  <td className="ct-text" title={pick(kindText(m.kind), lang)}>{pick(modelLabel(o, m.model_id), lang)}</td>
                  <td className="ct-text ct-wide-only">{m.design ? pick(text(DESIGN_TEXT, m.design), lang) : notApplicable}</td>
                  <td className="ct-text ct-wide-only">{m.treatment ? pick(text(TREATMENT_TEXT, m.treatment), lang) : notApplicable}</td>
                  <td className="ct-text ct-wide-only">{m.covariates.length ? m.covariates.map((c) => pick(text(COVARIATE_TEXT, c), lang)).join(', ') : none}</td>
                  {/* only a direct EAD model clips for its fit: a CCF model has nothing to clip, which is "not applicable", not a value
                      that is missing (R3 c10 m3) */}
                  <td data-na={m.kind === 'direct-ead' ? undefined : 'true'}>
                    {m.kind === 'direct-ead' ? <MaybeNumber value={m.n_clipped_below} reason={null} format={(v) => count(v, lang)} /> : notApplicable}
                  </td>
                  <td data-na={m.kind === 'direct-ead' ? undefined : 'true'}>
                    {m.kind === 'direct-ead' ? <MaybeNumber value={m.n_clipped_above} reason={null} format={(v) => count(v, lang)} /> : notApplicable}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

/** The EAD floor, the supervisory CCFs it uses and the small-undrawn rule. */
export function FloorsView({ sel }: { sel: C09Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const f = o.ead_floor;
  const s = o.small_undrawn;
  const fit = fitOf(sel);
  const yes = pick({ en: 'yes', es: 'sí' }, lang);
  const no = pick({ en: 'no', es: 'no' }, lang);
  return (
    <ViewsRow shares={[3, 2]}>
      <PlotCard
        fill
        title={{ en: 'The EAD floor and where it binds', es: 'El piso de EAD y dónde se activa' }}
        {...card}
        note={{
          en: 'An internal EAD estimate may not fall below the on-balance amount plus a share of the off-balance exposure at the standardised CCF. The bar is the share of facilities of each class where the floor binds.',
          es: 'Una estimación interna de EAD no puede quedar bajo el monto en balance más una parte de la exposición fuera de balance al CCF estandarizado. La barra es la proporción de líneas de cada clase donde el piso se activa.',
        }}
      >
        <ChartAbove
          chartHeight="9rem"
          chart={
            <BarChart
              title={{ en: 'Share of facilities where the floor binds', es: 'Proporción de líneas donde el piso se activa' }}
              height="fill"
              orientation="horizontal"
              data={f.rows.map((r) => ({ id: r.facility_class, label: facilityLabel(r.facility_class), value: r.share_binding, tone: 'accent' as const }))}
              axis={{ label: { en: 'Share where the floor binds', es: 'Proporción donde el piso se activa' }, format: { percent: true, digits: 2 } }}
            />
          }
        >
          <p className="ct-note" data-floor-rule="true">{pick(f.rule, lang)}</p>
          {f.rows.every((r) => r.share_binding === 0) ? (
            <p className="ct-note" data-floor-binds="none">{pick({ en: 'At this level the floor binds for no facility: every bar is 0 %.', es: 'En este nivel el piso no se activa en ninguna línea: cada barra es 0 %.' }, lang)}</p>
          ) : null}
          <table className="caos-table ct-wrap-head" data-table="ead-floor">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Facility class', es: 'Clase de línea' }, lang)}</th>
                <th>{pick({ en: 'Standardised CCF', es: 'CCF estandarizado' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Facilities', es: 'Líneas' }, lang)}</th>
                <th>{pick({ en: 'Binds', es: 'Se activa' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: `Mean EAD before (${f.currency})`, es: `EAD media antes (${f.currency})` }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: `Mean EAD after (${f.currency})`, es: `EAD media después (${f.currency})` }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Paragraph', es: 'Párrafo' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {f.rows.map((r) => (
                <tr key={r.facility_class} data-class={r.facility_class}>
                  <td className="ct-text">{pick(facilityLabel(r.facility_class), lang)}</td>
                  <td>{p2(r.sa_ccf, lang)}</td>
                  <td className="ct-wide-only">{count(r.n, lang)}</td>
                  <td>{p2(r.share_binding, lang)}</td>
                  <td className="ct-wide-only">{money(r.mean_ead_before, lang, f.currency)}</td>
                  <td className="ct-wide-only">{money(r.mean_ead_after, lang, f.currency)}</td>
                  <td className="ct-text ct-wide-only" translate="no">{rangeText(r.reference, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartAbove>
      </PlotCard>
      <PlotCard fill title={{ en: 'Supervisory CCFs and the small-undrawn rule', es: 'CCF supervisores y la regla de saldo no utilizado pequeño' }} {...card}>
        <div className="ct-scroll" data-caos-flow="">
          <dl className="ct-defs" data-table="small-undrawn" data-applied={String(s.applied)}>
            <dt>{pick({ en: 'Threshold', es: 'Umbral' }, lang)}</dt>
            <dd>{`${money(s.threshold, lang, s.currency)} ${s.currency}`}</dd>
            <dt>{pick({ en: 'Applied', es: 'Aplicada' }, lang)}</dt>
            <dd>{s.applied ? yes : no}</dd>
            <dt>{pick(s.applied ? { en: 'Facilities switched', es: 'Líneas cambiadas' } : { en: 'Lines the rule would switch (not applied)', es: 'Líneas que la regla cambiaría (no aplicada)' }, lang)}</dt>
            <dd>{count(s.n_switched, lang)}</dd>
            <dt>{pick({ en: 'Source', es: 'Fuente' }, lang)}</dt>
            <dd translate="no">{s.reference}</dd>
          </dl>
          {fit ? (
            <table className="caos-table ct-wrap-head" data-table="supervisory-ccfs">
              <caption className="ct-note">{pick({ en: `Standardised CCFs of the framework, as the run recorded them (off-balance share ${p2(fit.floors.off_balance_share, 'en')})`, es: `CCF estandarizados del marco, como los registró la corrida (parte fuera de balance ${p2(fit.floors.off_balance_share, 'es')})` }, lang)}</caption>
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Item', es: 'Partida' }, lang)}</th>
                  <th>CCF</th>
                  <th className="ct-text ct-wide-only">{pick({ en: 'Paragraph', es: 'Párrafo' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {fit.floors.supervisory_ccfs.map((c) => (
                  <tr key={c.item} data-item={c.item}>
                    <td className="ct-text">{pick(facilityLabel(c.item), lang)}</td>
                    <td>{p2(c.ccf, lang)}</td>
                    <td className="ct-text ct-wide-only" translate="no">{rangeText(c.reference, lang)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="ct-note" data-state="unavailable">{pick({ en: 'Not available: the models artifact carries no supervisory CCFs.', es: 'No disponible: el artefacto de modelos no trae los CCF supervisores.' }, lang)}</p>
          )}
        </div>
      </PlotCard>
    </ViewsRow>
  );
}
