// C02's exploratory horizon group and its Impact group. The five files are bankruptcy status after one to five years;
// they carry no firm identifier and no date and the overlap of firms across them is unknown (UNVERIFIED, 08 l.855-856),
// so the cross-file transfer, the term structure read from the five event rates and the ECL effect of the horizon PDs are
// each labelled exploratory, with the reason, wherever they are drawn. A null field says "not available" with its reason.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { UnavailableCard } from '../c14/C14Common';
import { Labelled, LabelledOverTable, barMin, f3, int, pc } from '../c20/U14Common';
import { outputsOf, rungFor, rungName, type C02Sel } from './selection';

/** The display band of a transfer AUC (a shade, not a threshold): below 0.6, 0.6 to 0.7, 0.7 to 0.8, 0.8 and above. */
const band = (auc: number): 1 | 2 | 3 | 4 => (auc < 0.6 ? 1 : auc < 0.7 ? 2 : auc < 0.8 ? 3 : 4);

/** The exploratory transfer heat map: a rung fitted on one horizon file and scored on the holdout of another. */
export function TransferView({ sel }: { sel: C02Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const focus = rungFor(sel);
  if (!sel || !o || !focus) return <Pending />;
  const cells = o.transfer.cells.filter((c) => c.rung === focus.rung);
  if (cells.length === 0) {
    return (
      <UnavailableCard
        sel={sel}
        title={{ en: 'Transfer between horizons (exploratory)', es: 'Transferencia entre horizontes (exploratorio)' }}
        reason={{
          en: `Not available: this variant has no transfer cell for the rung in focus. ${o.transfer.reason.en}`,
          es: `No disponible: esta variante no trae una celda de transferencia para el peldaño en foco. ${o.transfer.reason.es}`,
        }}
      />
    );
  }
  const years = [...new Set(cells.flatMap((c) => [c.fitted_on_years, c.scored_on_years]))].sort((a, b) => a - b);
  const at = (fit: number, scored: number) => cells.find((c) => c.fitted_on_years === fit && c.scored_on_years === scored) ?? null;
  const na = formatNumber(null, lang);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `Transfer between horizons: ${rungName(sel, focus.model_id).en}`, es: `Transferencia entre horizontes: ${rungName(sel, focus.model_id).es}` }}
        {...card}
        note={{
          en: 'AUC of the rung fitted on the file of the row and scored on the holdout of the file of the column. The shade is a display band (below 0.6, 0.6 to 0.7, 0.7 to 0.8, 0.8 and above), not a threshold. A cell the document does not carry stays empty.',
          es: 'AUC del peldaño ajustado en el archivo de la fila y puntuado en la muestra reservada del archivo de la columna. El tono es una banda de visualización (bajo 0,6, de 0,6 a 0,7, de 0,7 a 0,8, de 0,8 y más), no un umbral. Una celda que el documento no trae queda vacía.',
        }}
      >
        <LabelledOverTable
          head={<Labelled label="exploratory" reason={o.transfer.reason} />}
          chartMin={barMin(cells.length)}
          chart={
            <BarChart
              title={{ en: 'AUC of the rung by fitted and scored horizon', es: 'AUC del peldaño por horizonte ajustado y puntuado' }}
              height="fill"
              orientation="horizontal"
              data={cells.map((c) => ({ id: `${c.fitted_on_years}-${c.scored_on_years}`, label: { en: `Fitted on ${c.fitted_on_years}y, scored on ${c.scored_on_years}y`, es: `Ajustado en ${c.fitted_on_years}a, puntuado en ${c.scored_on_years}a` } as BiText, value: c.auc }))}
              axis={{ label: { en: 'AUC on the scored holdout', es: 'AUC en la muestra reservada puntuada' }, format: { decimals: 2 }, range: [0, 1] }}
            />
          }
        >
          <table className="caos-table ct-wrap-head ct-heat-table" data-table="transfer">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Fitted on, scored on', es: 'Ajustado en, puntuado en' }, lang)}</th>
                {years.map((y) => (
                  <th key={y}>{pick({ en: `${y}-year file`, es: y === 1 ? 'archivo de 1 año' : `archivo de ${y} años` }, lang)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {years.map((fit) => (
                <tr key={fit}>
                  <td className="ct-text">{pick({ en: `${fit}-year file`, es: fit === 1 ? 'archivo de 1 año' : `archivo de ${fit} años` }, lang)}</td>
                  {years.map((scored) => {
                    const c = at(fit, scored);
                    return c ? (
                      <td key={scored} className="ct-heat" data-heat={band(c.auc)} data-fitted={c.fitted_on_years} data-scored={c.scored_on_years} data-n={c.n} data-events={c.events} title={pick({ en: `AUC on ${int(c.n, 'en')} firms, ${int(c.events, 'en')} bankruptcies`, es: `AUC sobre ${int(c.n, 'es')} empresas, ${int(c.events, 'es')} quiebras` }, lang)}>
                        {f3(c.auc, lang)}
                      </td>
                    ) : (
                      <td key={scored} data-na="true">{na}</td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </LabelledOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The exploratory term structure: the five file event rates read as a cumulative PD, with the hazard each year implies. */
export function TermStructureView({ sel }: { sel: C02Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const t = o.term_structure;
  if (t.points.length === 0) {
    return <UnavailableCard sel={sel} title={{ en: 'Term structure (exploratory)', es: 'Estructura de plazos (exploratorio)' }} reason={{ en: `Not available: the document carries no point. ${t.reason.en}`, es: `No disponible: el documento no trae ningún punto. ${t.reason.es}` }} />;
  }
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Term structure read from the five files (exploratory)', es: 'Estructura de plazos leída de los cinco archivos (exploratorio)' }}
        {...card}
        note={{
          en: 'The event rate of each file read as a cumulative PD, with cumulative = 1 - product of (1 - hazard); the hazard is what each extra year adds. It treats five files as one population, which is not known.',
          es: 'La tasa de eventos de cada archivo leída como una PD acumulada, con acumulada = 1 - producto de (1 - riesgo); el riesgo es lo que añade cada año. Trata cinco archivos como una población, lo que no se sabe.',
        }}
      >
        <LabelledOverTable
          head={
            <>
              <Labelled label="exploratory" reason={t.reason} />
              <p className="ct-note" data-nondecreasing={t.cumulative_nondecreasing}>
                {pick(
                  t.cumulative_nondecreasing
                    ? { en: 'The cumulative PD does not fall with the horizon, as a cumulative PD cannot.', es: 'La PD acumulada no baja con el horizonte, como no puede bajar una PD acumulada.' }
                    : { en: 'The cumulative PD falls somewhere with the horizon, which a cumulative PD cannot do: the files do not draw one population.', es: 'La PD acumulada baja en algún punto con el horizonte, lo que una PD acumulada no puede hacer: los archivos no provienen de una sola población.' },
                  lang,
                )}
              </p>
            </>
          }
          chart={
            <UPlotChart
              height="fill"
              x={{ values: t.points.map((p) => p.years), label: { en: 'Horizon', es: 'Horizonte' }, unit: { en: 'years', es: 'años' }, format: { decimals: 0 } }}
              y={{ label: { en: 'PD', es: 'PD' }, format: { percent: true, decimals: 1 } }}
              series={[
                { label: { en: 'Cumulative PD', es: 'PD acumulada' }, values: t.points.map((p) => p.cumulative_pd), color: '--color-accent', width: 2.4 },
                { label: { en: 'Hazard of the year', es: 'Riesgo del año' }, values: t.points.map((p) => p.hazard), color: '--color-magenta', width: 1.8, dash: [5, 3] },
              ]}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="term-structure">
            <thead>
              <tr>
                <th>{pick({ en: 'Horizon (years)', es: 'Horizonte (años)' }, lang)}</th>
                <th>{pick({ en: 'Cumulative PD', es: 'PD acumulada' }, lang)}</th>
                <th>{pick({ en: 'Hazard of the year', es: 'Riesgo del año' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {t.points.map((p) => (
                <tr key={p.years} data-years={p.years}>
                  <td>{int(p.years, lang)}</td>
                  <td>{pc(p.cumulative_pd, lang)}</td>
                  <td>{formatNumber(p.hazard, lang, { percent: true, decimals: 3 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ct-note">{pick({ en: 'Source: the engine provisions API, from_cumulative and the lifetime PD back-test (dossier 04, E.2).', es: 'Fuente: la API de provisiones del motor, from_cumulative y el backtest de la PD de toda la vida (dossier 04, E.2).' }, lang)}</p>
        </LabelledOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The Impact view: the 12-month and the lifetime ECL effect of the horizon PDs, exploratory, in the unit the document gives. */
export function EclImpactView({ sel }: { sel: C02Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const d = o.impact_detail;
  const missing = d.ecl_12m_effect === null || d.ecl_lifetime_effect === null;
  const na = formatNumber(null, lang);
  const value = (v: number | null) => (v === null ? na : formatNumber(v, lang, { digits: 4 }));
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'ECL effect of the horizon PDs (exploratory)', es: 'Efecto en la PCE de las PD por horizonte (exploratorio)' }}
        {...card}
        note={{
          en: `The effect on the 12-month and the lifetime expected credit loss when the horizon PDs of the rung replace the ones in use, through the engine provisions API, in ${d.unit}. The LGD is an assumption of Contraste, not an estimate.`,
          es: `El efecto en la pérdida crediticia esperada a 12 meses y de toda la vida cuando las PD por horizonte del peldaño reemplazan a las en uso, a través de la API de provisiones del motor, en ${d.unit}. La LGD es un supuesto de Contraste, no una estimación.`,
        }}
      >
        <LabelledOverTable
          head={
            <>
              <Labelled label="exploratory" reason={d.reason} />
              {missing ? (
                <p className="caos-pending" data-state="unavailable">
                  {pick({ en: 'Not available: ', es: 'No disponible: ' }, lang)}
                  {d.reason_if_null ?? pick({ en: 'the document gives no reason', es: 'el documento no da una razón' }, lang)}
                </p>
              ) : null}
            </>
          }
          chartMin={barMin(2)}
          chart={
            missing ? null : (
              <BarChart
                title={{ en: 'ECL effect of the horizon PDs', es: 'Efecto en la PCE de las PD por horizonte' }}
                height="fill"
                orientation="horizontal"
                data={[
                  { id: 'ecl-12m', label: { en: '12-month ECL', es: 'PCE a 12 meses' }, value: d.ecl_12m_effect },
                  { id: 'ecl-lifetime', label: { en: 'Lifetime ECL', es: 'PCE de toda la vida' }, value: d.ecl_lifetime_effect, tone: 'warn' },
                ]}
                axis={{ label: { en: 'Effect of the horizon PDs', es: 'Efecto de las PD por horizonte' }, unit: { en: d.unit, es: d.unit }, format: { digits: 4 } }}
              />
            )
          }
        >
          <table className="caos-table ct-wrap-head" data-table="ecl-impact">
            <tbody>
              <tr data-measure="ecl-12m">
                <td className="ct-text">{pick({ en: '12-month ECL effect', es: 'Efecto en la PCE a 12 meses' }, lang)}</td>
                <td data-na={d.ecl_12m_effect === null ? 'true' : undefined}>{value(d.ecl_12m_effect)}</td>
              </tr>
              <tr data-measure="ecl-lifetime">
                <td className="ct-text">{pick({ en: 'Lifetime ECL effect', es: 'Efecto en la PCE de toda la vida' }, lang)}</td>
                <td data-na={d.ecl_lifetime_effect === null ? 'true' : undefined}>{value(d.ecl_lifetime_effect)}</td>
              </tr>
              <tr>
                <td className="ct-text">{pick({ en: 'Unit', es: 'Unidad' }, lang)}</td>
                <td>{d.unit}</td>
              </tr>
              <tr data-lgd={d.lgd.label}>
                <td className="ct-text">{pick({ en: 'LGD (an assumption)', es: 'LGD (un supuesto)' }, lang)}</td>
                <td>{pc(d.lgd.value, lang)}</td>
              </tr>
              <tr>
                <td className="ct-text">{pick({ en: 'PD basis', es: 'Base de las PD' }, lang)}</td>
                <td className="ct-text">{d.pd_basis}</td>
              </tr>
            </tbody>
          </table>
        </LabelledOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
