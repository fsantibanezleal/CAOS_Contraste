// C07's validation views: how well the synthetic bank was calibrated to its public aggregates, the transcribed CMF B-1
// tables the standard method reads (PE = PI x PDI), and the rows of the tests the engine returned.
import { PlotCard, formatNumber, pick, useShellLang, useWorkbenchState, type BiText } from '@fasl-work/caos-app-shell';
import { TestRowsCard } from '../c06/ValidationViews';
import { MaybeNumber, pct } from '../c06/format';
import { REPLAY, provenanceOf } from '../model';
import { Pending } from '../Pending';
import { fitOf, outputsOf, type C07Sel } from './selection';

/** The calibration targets of the synthetic bank against what the calibration achieved. */
export function CalibrationView({ sel }: { sel: C07Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const fit = fitOf(sel);
  return (
    <PlotCard
      title={{ en: 'The synthetic bank against its targets', es: 'El banco sintético contra sus metas' }}
      lane={REPLAY}
      provenance={prov}
      dataKey={stateKey}
      note={{ en: 'Banco Andino is generated, not observed: its portfolio is calibrated to public aggregates, and a target it misses is shown beside the one it hits.', es: 'Banco Andino se genera, no se observa: su cartera se calibra a agregados públicos, y una meta que no logra se muestra junto a las que sí.' }}
    >
      {!fit ? (
        <p className="caos-pending" data-state="unavailable">{pick({ en: 'Not available: the models artifact carries no calibration.', es: 'No disponible: el artefacto de modelos no trae la calibración.' }, lang)}</p>
      ) : (
        <div className="ct-scroll">
          <p className="ct-note" data-bank={fit.bank.name}>{`${fit.bank.name}: ${pick(fit.bank.notice, lang)} (${pick({ en: 'seed', es: 'semilla' }, lang)} ${fit.bank.seed}; ${fit.bank.calibration_source})`}</p>
          <table className="caos-table ct-wrap-head" data-table="calibration-targets">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Metric', es: 'Métrica' }, lang)}</th>
                <th>{pick({ en: 'Target', es: 'Meta' }, lang)}</th>
                <th>{pick({ en: 'Achieved', es: 'Lograda' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Unit', es: 'Unidad' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Source and date', es: 'Fuente y fecha' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {fit.calibration_targets.map((t) => (
                <tr key={t.metric} data-metric={t.metric}>
                  <td className="ct-text">{t.metric}</td>
                  <td>{formatNumber(t.target, lang, { digits: 4 })}</td>
                  <td>{formatNumber(t.achieved, lang, { digits: 4 })}</td>
                  <td className="ct-text ct-wide-only">{t.unit}</td>
                  <td className="ct-text ct-wide-only">{`${t.source} (${t.as_of})`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PlotCard>
  );
}

/** The transcribed B-1 tables with their cells, and the default categories of the individual assessment. */
/** The words for the ids of the B-1 tables (U16-R2 b04 B2): never a bare id in a Spanish caption or cell. */
const TABLE_TEXT: Record<string, BiText> = {
  'mortgage-pe': { en: 'Residential mortgage', es: 'Vivienda' },
  'consumer-pi': { en: 'Consumer', es: 'Consumo' },
  'individual-categories': { en: 'Individually assessed commercial', es: 'Comercial de evaluación individual' },
  'commercial-generic-pe': { en: 'Commercial, group assessment', es: 'Comercial, evaluación grupal' },
};
const AXIS_TEXT: Record<string, BiText> = {
  default: { en: 'default', es: 'incumplimiento' },
  category: { en: 'category', es: 'categoría' },
  'mortgage-no-arrears': { en: 'mortgage, no arrears', es: 'con hipotecario, sin mora' },
  'mortgage-arrears': { en: 'mortgage, arrears', es: 'con hipotecario, con mora' },
  'no-mortgage-no-arrears': { en: 'no mortgage, no arrears', es: 'sin hipotecario, sin mora' },
  'no-mortgage-arrears': { en: 'no mortgage, arrears', es: 'sin hipotecario, con mora' },
  'no-guarantee': { en: 'no guarantee', es: 'sin garantía' },
};
const axisText = (id: string): BiText => AXIS_TEXT[id] ?? { en: id, es: id };

export function TablesView({ sel }: { sel: C07Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const fit = fitOf(sel);
  return (
    <PlotCard
      title={{ en: 'The CMF B-1 tables the standard method reads', es: 'Las tablas CMF B-1 que lee el método estándar' }}
      lane={REPLAY}
      provenance={prov}
      dataKey={stateKey}
      note={{ en: 'PI is the probability of default, PDI the loss given default and PE the expected loss, each a share; where a table gives both, PE = PI x PDI to the table\'s rounding. These are statutory parameters transcribed from the CMF compendium, not estimates.', es: 'PI es la probabilidad de incumplimiento, PDI la pérdida dado el incumplimiento y PE la pérdida esperada, cada una una fracción; donde una tabla da ambas, PE = PI x PDI al redondeo de la tabla. Son parámetros estatutarios transcritos del compendio de la CMF, no estimaciones.' }}
    >
      {!fit ? (
        <p className="caos-pending" data-state="unavailable">{pick({ en: 'Not available: the models artifact carries no B-1 table.', es: 'No disponible: el artefacto de modelos no trae tablas B-1.' }, lang)}</p>
      ) : (
        <div className="ct-scroll">
          {fit.b1_tables.map((t) => (
            <table key={t.table_id} className="caos-table ct-wrap-head" data-table-id={t.table_id}>
              <caption className="ct-note">{`${pick(TABLE_TEXT[t.table_id] ?? { en: t.table_id, es: t.table_id }, lang)}. ${pick(t.source, lang)}`}</caption>
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Row', es: 'Fila' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Column', es: 'Columna' }, lang)}</th>
                  <th>PI</th>
                  <th>PDI</th>
                  <th>PE</th>
                </tr>
              </thead>
              <tbody>
                {t.cells.map((c) => (
                  <tr key={`${c.row}|${c.column}`} data-cell={`${c.row}|${c.column}`}>
                    <td className="ct-text">{pick(axisText(c.row), lang)}</td>
                    <td className="ct-text">{pick(axisText(c.column), lang)}</td>
                    <td>{pct(c.pi, lang, 4)}</td>
                    <td>
                      <MaybeNumber value={c.pdi} reason={pick({ en: 'the table gives no PDI for this cell', es: 'la tabla no da PDI para esta celda' }, lang)} format={(v) => pct(v, lang, 4)} />
                    </td>
                    <td>
                      <MaybeNumber value={c.pe} reason={pick({ en: 'the table gives no PE for this cell', es: 'la tabla no da PE para esta celda' }, lang)} format={(v) => pct(v, lang, 4)} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ))}
          <table className="caos-table" data-table="b1-default-categories">
            <caption className="ct-note">{pick({ en: 'Individual assessment, default categories', es: 'Evaluación individual, categorías de incumplimiento' }, lang)}</caption>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Category', es: 'Categoría' }, lang)}</th>
                <th>{pick({ en: 'Expected loss up to', es: 'Pérdida esperada hasta' }, lang)}</th>
                <th>{pick({ en: 'Provision rate', es: 'Tasa de provisión' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {fit.b1_default_categories.map((c) => (
                <tr key={c.category} data-category={c.category}>
                  <td className="ct-text">{c.category}</td>
                  <td>
                    <MaybeNumber value={c.tpe_upper} reason={pick({ en: 'the last category is open', es: 'la última categoría es abierta' }, lang)} format={(v) => pct(v, lang, 1)} />
                  </td>
                  <td>{pct(c.provision_rate, lang, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PlotCard>
  );
}

export function TestsView({ sel }: { sel: C07Sel | null }) {
  if (!sel) return <Pending />;
  return <TestRowsCard variant={sel.data.variant} prov={provenanceOf(sel.data.variant.provenance.truth_status)} />;
}
