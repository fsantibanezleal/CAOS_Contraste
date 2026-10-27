// C07's validation views: how well the synthetic bank was calibrated to its public aggregates, the transcribed CMF B-1
// tables the standard method reads (PE = PI x PDI), and the rows of the tests the engine returned.
import { PlotCard, formatNumber, pick, useShellLang, useWorkbenchState, type BiText } from '@fasl-work/caos-app-shell';
import { TestRowsCard } from '../c06/ValidationViews';
import { MaybeNumber, pct } from '../c06/format';
import { REPLAY, provenanceOf } from '../model';
import { Pending } from '../Pending';
import { fitOf, outputsOf, type C07Sel } from './selection';

/** The calibration targets' metric and unit in Spanish (the models document writes them in English; R2b c08 B3). */
const PART_ES: Record<string, string> = {
  'loan mix': 'composición de la cartera', 'provision index': 'índice de provisiones', '90-day delinquency': 'morosidad de 90 días',
  'consumer product split': 'división de productos de consumo', commercial: 'comercial', consumer: 'consumo', mortgage: 'vivienda',
  total: 'total', 'instalment loans': 'créditos en cuotas',
};
const UNIT_ES: Record<string, string> = {
  'share of the three portfolios': 'proporción de las tres carteras', 'share of loans': 'proporción de las colocaciones',
  'share of consumer loans': 'proporción de las colocaciones de consumo',
};
/** "loan mix: commercial" in the language: each part by the map, the string as written when a part is not in it. */
function metricText(metric: string, lang: 'en' | 'es'): string {
  if (lang === 'en') return metric;
  const parts = metric.split(': ');
  return parts.every((p) => PART_ES[p]) ? parts.map((p) => PART_ES[p]).join(': ') : metric;
}

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
        <div className="ct-scroll" data-caos-flow="">
          <p className="ct-note" data-bank={fit.bank.name} style={{ overflowWrap: 'anywhere' }}>{`${pick(fit.bank.notice, lang)} (${pick({ en: 'seed', es: 'semilla' }, lang)} ${fit.bank.seed}; ${calibrationSource(fit.bank.calibration_source as string | BiText, lang)})`}</p>
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
                  <td className="ct-text">{metricText(t.metric, lang)}</td>
                  <td>{formatNumber(t.target, lang, { digits: 4 })}</td>
                  <td>{formatNumber(t.achieved, lang, { digits: 4 })}</td>
                  <td className="ct-text ct-wide-only">{lang === 'es' ? UNIT_ES[t.unit] ?? t.unit : t.unit}</td>
                  <td className="ct-text ct-wide-only">{`${targetSource(t.source as string | BiText, lang)} (${t.as_of})`}</td>
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
/**
 * The words for a row or a column id of a B-1 table (U16-R2 b04 m4): a band of days past due ('1-29', '0-7'), a band of the loan
 * over the value of the guarantee ('pvg<=40', '40<pvg<=80', 'ptvg>90'), else the id's own entry or the id as written.
 */
const axisText = (id: string): BiText => {
  if (AXIS_TEXT[id]) return AXIS_TEXT[id];
  const days = /^(\d+)(?:-(\d+))?$/.exec(id);
  if (days) return days[2] ? { en: `${days[1]} to ${days[2]} days past due`, es: `${days[1]} a ${days[2]} días de mora` } : { en: `${days[1]} days past due`, es: `${days[1]} días de mora` };
  const ratio = /^(?:(\d+)<)?(p?t?vg)(?:<=(\d+)|>(\d+))$/.exec(id);
  if (ratio) {
    const total = ratio[2] === 'ptvg';
    const en = total ? 'total loan over the value of the guarantee' : 'loan over the value of the guarantee';
    const es = total ? 'préstamo total sobre el valor de la garantía' : 'préstamo sobre el valor de la garantía';
    if (ratio[1] && ratio[3]) return { en: `${en}: over ${ratio[1]}% up to ${ratio[3]}%`, es: `${es}: sobre ${ratio[1]} % hasta ${ratio[3]} %` };
    if (ratio[3]) return { en: `${en}: up to ${ratio[3]}%`, es: `${es}: hasta ${ratio[3]} %` };
    return { en: `${en}: over ${ratio[4]}%`, es: `${es}: sobre ${ratio[4]} %` };
  }
  return { en: id, es: id };
};

/** The CMF report's own words as published, with their accents: a document baked before c07-models 3.0.0 wrote them without (the
 * same words with the accents stripped), and the view restores them. */
const QUOTED = ['Informe del Desempeño', 'días o más', 'índice de provisiones', 'créditos en cuotas', 'participación'];
const bare = (w: string): string => w.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
const withAccents = (s: string): string => QUOTED.reduce((acc, w) => acc.split(bare(w)).join(w), s);

/** The calibration source of the bank in the page's language: a bilingual text (c07-models 3.0.0), or the English string of a document
 * baked before, rendered in Spanish here (the citation and the hash as published). */
export function calibrationSource(source: string | BiText, lang: 'en' | 'es'): string {
  if (typeof source !== 'string') return pick(source, lang);
  if (lang === 'en') return withAccents(source);
  return withAccents(source)
    .replace('public web publication (the CMF Bancos API key is absent)', 'publicación web pública (falta la clave de la API de CMF Bancos)')
    .replace(/; generator /, '; generador ')
    .replace(/; parameters sha256 /, '; parámetros sha256 ');
}

/** The source of a calibration target in the page's language: a bilingual text (c07-models 3.0.0), or the English string of a
 * document baked before, its remarks rendered in Spanish and the report's own words with their accents (R3 c08 B1). */
export function targetSource(source: string | BiText, lang: 'en' | 'es'): string {
  if (typeof source !== 'string') return pick(source, lang);
  const quoted = withAccents(source).replace('Cuadro N 1', 'Cuadro N° 1');
  if (lang === 'en') return quoted;
  return quoted
    .replace(/\(published (\d{4}-\d{2}-\d{2})\)/, '(publicado el $1)')
    .replace('column Bancos', 'columna Bancos')
    .replace(' of Comercial + ', ' de Comercial + ')
    .replace(/; section (\d)/, '; sección $1')
    .replace('(includes loans to banks)', '(incluye créditos a bancos)');
}

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
      note={{ en: 'PI is the probability of default, PDI the loss given default and PE the expected loss, each a share; where a table gives both, PE = PI × PDI to the table\'s rounding. These are statutory parameters transcribed from the CMF compendium, not estimates.', es: 'PI es la probabilidad de incumplimiento, PDI la pérdida dado el incumplimiento y PE la pérdida esperada, cada una una fracción; donde una tabla da ambas, PE = PI × PDI al redondeo de la tabla. Son parámetros estatutarios transcritos del compendio de la CMF, no estimaciones.' }}
    >
      {!fit ? (
        <p className="caos-pending" data-state="unavailable">{pick({ en: 'Not available: the models artifact carries no B-1 table.', es: 'No disponible: el artefacto de modelos no trae tablas B-1.' }, lang)}</p>
      ) : (
        <div className="ct-scroll" data-caos-flow="">
          {fit.b1_tables.map((t) => {
            // a reason every cell shares is said once, in the caption, and a column that holds one value in every row is dropped
            // (R3 c08 m4: "no disponible (la tabla no da PDI ...)" in all 16 rows; m5: "categoría" in all ten)
            const noPdi = t.cells.every((c) => c.pdi === null);
            const noPe = t.cells.every((c) => c.pe === null);
            const oneColumn = new Set(t.cells.map((c) => c.column)).size === 1;
            const absent: BiText[] = [
              ...(noPdi ? [{ en: 'the table gives no PDI for its cells', es: 'la tabla no da PDI para sus celdas' }] : []),
              ...(noPe ? [{ en: 'the table gives no PE for its cells', es: 'la tabla no da PE para sus celdas' }] : []),
            ];
            return (
              <table key={t.table_id} className="caos-table ct-wrap-head" data-table-id={t.table_id}>
                <caption className="ct-note">{`${pick(TABLE_TEXT[t.table_id] ?? { en: t.table_id, es: t.table_id }, lang)}. ${pick(t.source, lang)}${absent.length ? `. ${absent.map((a) => pick(a, lang)).join('; ')}.` : ''}`}</caption>
                <thead>
                  <tr>
                    <th className="ct-text">{pick({ en: 'Row', es: 'Fila' }, lang)}</th>
                    {oneColumn ? null : <th className="ct-text">{pick({ en: 'Column', es: 'Columna' }, lang)}</th>}
                    <th>PI</th>
                    {noPdi ? null : <th>PDI</th>}
                    {noPe ? null : <th>PE</th>}
                  </tr>
                </thead>
                <tbody>
                  {t.cells.map((c) => (
                    <tr key={`${c.row}|${c.column}`} data-cell={`${c.row}|${c.column}`}>
                      <td className="ct-text">{pick(axisText(c.row), lang)}</td>
                      {oneColumn ? null : <td className="ct-text">{pick(axisText(c.column), lang)}</td>}
                      <td>{pct(c.pi, lang, 4)}</td>
                      {noPdi ? null : (
                        <td>
                          <MaybeNumber value={c.pdi} reason={pick({ en: 'the table gives no PDI for this cell', es: 'la tabla no da PDI para esta celda' }, lang)} format={(v) => pct(v, lang, 4)} />
                        </td>
                      )}
                      {noPe ? null : (
                        <td>
                          <MaybeNumber value={c.pe} reason={pick({ en: 'the table gives no PE for this cell', es: 'la tabla no da PE para esta celda' }, lang)} format={(v) => pct(v, lang, 4)} />
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            );
          })}
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
