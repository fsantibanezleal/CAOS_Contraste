// C20's SGCD shock views: how much performance, drift and data quality move under each shock the model has seen and
// under the shocks held out of its adaptation, with the shocks as the dataset ships them and Contraste's own application
// of each shock family to the structured view kept apart (the shipped shocks reach the structured view in few records, so
// a structured-only model cannot degrade on most of them by construction; research addendum H4). Every view carries the
// dataset card's prohibited-use sentence. The PSI of 0.10 and 0.25 are the legacy rule of thumb, drawn and labelled as
// such, never as regulation (06 I.4 l.1244-1245, I.6 l.1268-1270).
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { useCard, type Bi } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { LabelledOverTable, U14TestsTable, barMin, f3, f4, int, pc1, sig, testsOf } from './U14Common';
import { NotInVariant, SgcdNotice } from './C20Common';
import { SHOCK_TEXT, asKind, blockRows, text, type Block, type C20Sel, type C20ShockRow } from './selection';
import { es, localTests } from './localise';
import { inputName } from '../names';

const TITLE_DEGRADATION: BiText = { en: 'Degradation by shock', es: 'Degradación por choque' };
const TITLE_DRIFT: BiText = { en: 'Drift by shock', es: 'Deriva por choque' };
const TITLE_QUALITY: BiText = { en: 'Data quality and attribution by shock', es: 'Calidad de datos y atribución por choque' };

const BLOCK_TEXT: Record<Block, { title: Bi; note: (source: string | null) => BiText }> = {
  shipped: {
    title: { en: 'As shipped', es: 'Como se entregan' },
    note: () => ({
      en: 'The shocks as the dataset ships them. Only the records whose structured view the shock changes can move a model that reads the structured view: read the "reach the model" column before the loss.',
      es: 'Los choques como los entrega el conjunto de datos. Solo los registros cuya vista estructurada cambia el choque pueden mover a un modelo que lee la vista estructurada: lea la columna "llegan al modelo" antes que la pérdida.',
    }),
  },
  applied: {
    title: { en: 'Contraste-applied', es: 'Aplicados por Contraste' },
    note: (source) => ({
      en: `Contraste applies each shock family to the structured view itself, with the parameters of ${source ?? 'the dataset metadata'}. These are Contraste's own application, labelled as such, and not the dataset's shipped shocks.`,
      es: `Contraste aplica cada familia de choques a la vista estructurada misma, con los parámetros de ${source ? es(source, 'es') : 'los metadatos del conjunto'}. Es la aplicación propia de Contraste, etiquetada como tal, y no los choques entregados por el conjunto.`,
    }),
  },
};

const heldOut = (o: { seen_or_held_out: string }): Bi =>
  o.seen_or_held_out === 'seen'
    ? { en: 'shocks the model has seen', es: 'choques que el modelo ha visto' }
    : { en: 'shocks held out of the model', es: 'choques reservados fuera del modelo' };

/** One block of the shock rows as a card: the AUC change bar of each shock over the table of its numbers. */
function BlockCard({ sel, block }: { sel: C20Sel; block: Block }) {
  const lang = useShellLang();
  const card = useCard(sel.data.variant);
  const o = asKind(sel, 'shock');
  if (!o) return null;
  const rows = blockRows(o, block);
  const t = BLOCK_TEXT[block];
  const source = block === 'applied' ? o.applied.parameters_source : null;
  return (
    <PlotCard fill title={{ en: `${t.title.en}: ${heldOut(o).en}`, es: `${t.title.es}: ${heldOut(o).es}` }} {...card} note={t.note(source)} >
      <LabelledOverTable
        chartMin={barMin(rows.length)}
        chart={
          rows.length === 0 ? (
            <p className="caos-pending" data-state="unavailable">{pick({ en: 'Not available: the block carries no shock row.', es: 'No disponible: el bloque no trae ninguna fila de choque.' }, lang)}</p>
          ) : (
            <BarChart
              title={{ en: 'AUC loss by shock', es: 'Pérdida de AUC por choque' }}
              height="fill"
              orientation="horizontal"
              data={rows.map((r) => ({ id: r.shock_id, label: text(SHOCK_TEXT, r.shock_id), value: 0 - r.performance.auc_delta, tone: r.performance.auc_delta < 0 ? ('bad' as const) : ('good' as const), highlight: r.shock_id === sel.shock }))}
              axis={{ label: { en: 'AUC loss against the clean set (positive is a loss)', es: 'Pérdida de AUC (positiva) vs. conjunto limpio' }, format: { decimals: 3 } }}
            />
          )
        }
      >
        <table className="caos-table ct-wrap-head" data-table="shock-degradation" data-block={block}>
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Shock', es: 'Choque' }, lang)}</th>
              <th className="ct-wide-only">{pick({ en: 'Records', es: 'Registros' }, lang)}</th>
              <th>{pick({ en: 'Reach the model', es: 'Llegan al modelo' }, lang)}</th>
              <th>AUC</th>
              <th className="ct-wide-only">Brier</th>
              <th>{pick({ en: 'AUC change', es: 'Cambio del AUC' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.shock_id} data-block={block} data-shock={r.shock_id} data-reach={r.n_reaching_structured_view} className={r.shock_id === sel.shock ? 'ct-current' : undefined}>
                <td className="ct-text" title={r.batches.join(', ')}>{pick(text(SHOCK_TEXT, r.shock_id), lang)}</td>
                <td className="ct-wide-only">{int(r.n_records, lang)}</td>
                <td>{int(r.n_reaching_structured_view, lang)}</td>
                <td>{f3(r.performance.auc, lang)}</td>
                <td className="ct-wide-only">{f3(r.performance.brier, lang)}</td>
                <td>{f4(r.performance.auc_delta, lang)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <SgcdNotice sel={sel} />
      </LabelledOverTable>
    </PlotCard>
  );
}

/** Degradation by shock type for the shocks seen and held out, the shipped and the Contraste-applied blocks apart. */
export function DegradationView({ sel }: { sel: C20Sel | null }) {
  if (!sel) return <Pending />;
  if (!asKind(sel, 'shock')) return <NotInVariant sel={sel} title={TITLE_DEGRADATION} needs="shock" />;
  return (
    <ViewsRow>
      <BlockCard sel={sel} block="shipped" />
      <BlockCard sel={sel} block="applied" />
    </ViewsRow>
  );
}

/** The two legacy rule-of-thumb levels of the PSI (little, moderate, significant change): a convention with no error control. */
export const RULE_OF_THUMB = [0.1, 0.25] as const;

const ruleBars = () =>
  RULE_OF_THUMB.map((v) => ({
    id: `rule-${v}`,
    label: { en: `Rule of thumb ${formatNumber(v, 'en', { decimals: 2 })} (convention)`, es: `Regla empírica ${formatNumber(v, 'es', { decimals: 2 })} (convención)` },
    value: v,
    tone: 'neutral' as const,
    hint: { en: 'The legacy PSI bands, used without reference to type I or type II error rates', es: 'Las bandas heredadas del PSI, usadas sin referencia a tasas de error tipo I o tipo II' },
  }));

/** PSI and CSI by shock against the chi-square benchmark and the rule-of-thumb lines, and the inputs of the shock in focus. */
export function DriftView({ sel }: { sel: C20Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  if (!sel) return <Pending />;
  const o = asKind(sel, 'shock');
  if (!o) return <NotInVariant sel={sel} title={TITLE_DRIFT} needs="shock" />;
  const rows = blockRows(o, sel.block);
  const focus = rows.find((r) => r.shock_id === sel.shock) ?? rows[0] ?? null;
  const chart = (which: 'psi' | 'csi'): ReturnType<typeof BarChart> => (
    <BarChart
      title={which === 'psi' ? { en: 'PSI by shock', es: 'PSI por choque' } : { en: 'CSI by shock', es: 'CSI por choque' }}
      height="fill"
      orientation="horizontal"
      data={[
        ...rows.map((r) => ({ id: r.shock_id, label: text(SHOCK_TEXT, r.shock_id), value: which === 'psi' ? r.drift.psi_max : r.drift.csi_max, highlight: r.shock_id === sel.shock })),
        ...ruleBars(),
      ]}
      axis={{ label: which === 'psi' ? { en: 'Largest PSI over the inputs', es: 'Mayor PSI entre las entradas' } : { en: 'Largest CSI over the inputs', es: 'Mayor CSI entre las entradas' }, format: { decimals: 2 } }}
    />
  );
  const min = barMin(rows.length + RULE_OF_THUMB.length);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `PSI by shock: ${BLOCK_TEXT[sel.block].title.en.toLowerCase()}`, es: `PSI por choque: ${BLOCK_TEXT[sel.block].title.es.toLowerCase()}` }}
        {...card}
        note={{
          en: 'The population stability index of the largest-moving input. The two grey bars are the legacy rule of thumb (little change below 0.10, significant above 0.25): a convention, not a regulatory threshold, and the chi-square p-value below is the test that keeps its error rate.',
          es: 'El índice de estabilidad poblacional de la entrada que más se mueve. Las dos barras grises son la regla empírica heredada (poco cambio bajo 0,10, cambio significativo sobre 0,25): una convención, no un umbral regulatorio, y el valor p de chi-cuadrado de abajo es la prueba que conserva su tasa de error.',
        }}
      >
        <LabelledOverTable chartMin={min} chart={chart('psi')}>
          <table className="caos-table ct-wrap-head" data-table="shock-drift" data-block={sel.block}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Shock', es: 'Choque' }, lang)}</th>
                <th>PSI</th>
                <th>CSI</th>
                <th className="ct-text">{pick({ en: 'Chi-square test', es: 'Prueba chi-cuadrado' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.shock_id} data-shock={r.shock_id} className={r.shock_id === sel.shock ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(text(SHOCK_TEXT, r.shock_id), lang)}</td>
                  <td>{f3(r.drift.psi_max, lang)}</td>
                  <td>{f3(r.drift.csi_max, lang)}</td>
                  <td className="ct-text" data-benchmark={r.drift.chi2_p_value === null ? 'none' : r.drift.chi2_p_value < 0.05 ? 'exceeded' : 'within'} data-na={r.drift.chi2_p_value === null ? 'true' : undefined}>
                    {r.drift.chi2_p_value === null
                      ? `${formatNumber(null, lang)} (${pick({ en: 'the test did not run', es: 'la prueba no corrió' }, lang)})`
                      : `p = ${sig(r.drift.chi2_p_value, lang)}, ${pick(r.drift.chi2_p_value < 0.05 ? { en: 'above the benchmark at 5%', es: 'sobre el umbral al 5%' } : { en: 'within the benchmark at 5%', es: 'dentro del umbral al 5%' }, lang)}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <U14TestsTable tests={localTests(sel.data.variant.tests, lang)} only={testsOf('stability.')} caseId="C20" models={sel.data.variant.model} />
          <SgcdNotice sel={sel} />
        </LabelledOverTable>
      </PlotCard>
      <PlotCard
        fill
        title={{ en: `CSI by shock and the inputs of ${focus ? pick(text(SHOCK_TEXT, focus.shock_id), 'en').toLowerCase() : 'the shock'}`, es: `CSI por choque y las entradas de ${focus ? pick(text(SHOCK_TEXT, focus.shock_id), 'es').toLowerCase() : 'el choque'}` }}
        {...card}
        note={{ en: 'The CSI applies the PSI formula to each input. The table lists every input of the shock in focus with its own PSI, CSI and chi-square p-value.', es: 'El CSI aplica la fórmula del PSI a cada entrada. La tabla lista cada entrada del choque en foco con su propio PSI, CSI y valor p de chi-cuadrado.' }}
      >
        <LabelledOverTable chartMin={min} chart={chart('csi')}>
          <table className="caos-table ct-wrap-head" data-table="shock-inputs" data-shock={focus?.shock_id}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Input', es: 'Entrada' }, lang)}</th>
                <th>PSI</th>
                <th>CSI</th>
                <th>{pick({ en: 'Chi-square p', es: 'p chi-cuadrado' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {(focus?.drift.variables ?? []).map((v) => (
                <tr key={v.name} data-input={v.name}>
                  <td className="ct-text">{pick(inputName(v.name) ?? { en: v.name, es: v.name }, lang)}</td>
                  <td>{f3(v.psi, lang)}</td>
                  <td>{f3(v.csi, lang)}</td>
                  <td data-na={v.chi2_p_value === null ? 'true' : undefined}>{v.chi2_p_value === null ? formatNumber(null, lang) : sig(v.chi2_p_value, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <SgcdNotice sel={sel} />
        </LabelledOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** Completeness, consistency and the attribution rank correlation of every shock of the block in focus. */
export function QualityView({ sel }: { sel: C20Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  if (!sel) return <Pending />;
  const o = asKind(sel, 'shock');
  if (!o) return <NotInVariant sel={sel} title={TITLE_QUALITY} needs="shock" />;
  const rows: C20ShockRow[] = blockRows(o, sel.block);
  const na = formatNumber(null, lang);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `Data quality and attribution: ${BLOCK_TEXT[sel.block].title.en.toLowerCase()}`, es: `Calidad de datos y atribución: ${BLOCK_TEXT[sel.block].title.es.toLowerCase()}` }}
        {...card}
        note={{
          en: 'Completeness is the share of fields present; consistency compares the structured and the text view, so it exists only where both are read. The attribution rank correlation is the Spearman correlation of the mean absolute SHAP between the clean and the shocked set: 1 means the model explains itself the same way.',
          es: 'La completitud es la parte de campos presentes; la consistencia compara la vista estructurada y la de texto, así que existe solo donde se leen ambas. La correlación de rangos de atribución es la correlación de Spearman del SHAP absoluto medio entre el conjunto limpio y el con choque: 1 significa que el modelo se explica igual.',
        }}
      >
        <LabelledOverTable
          chartMin={barMin(rows.length)}
          chart={
            <BarChart
              title={{ en: 'Completeness by shock', es: 'Completitud por choque' }}
              height="fill"
              orientation="horizontal"
              data={rows.map((r) => ({ id: r.shock_id, label: text(SHOCK_TEXT, r.shock_id), value: r.data_quality.completeness, highlight: r.shock_id === sel.shock }))}
              axis={{ label: { en: 'Share of fields present', es: 'Parte de los campos presentes' }, format: { percent: true, decimals: 0 }, range: [0, 1] }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="shock-quality" data-block={sel.block}>
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Shock', es: 'Choque' }, lang)}</th>
                <th>{pick({ en: 'Completeness', es: 'Completitud' }, lang)}</th>
                <th>{pick({ en: 'Consistency', es: 'Consistencia' }, lang)}</th>
                <th>{pick({ en: 'Attribution rank correlation', es: 'Correlación de rangos de atribución' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.shock_id} data-shock={r.shock_id} className={r.shock_id === sel.shock ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(text(SHOCK_TEXT, r.shock_id), lang)}</td>
                  <td>{pc1(r.data_quality.completeness, lang)}</td>
                  <td data-na={r.data_quality.consistency === null ? 'true' : undefined}>
                    {r.data_quality.consistency === null ? (
                      <>
                        {na}
                        <span className="ct-note" style={{ display: 'block', whiteSpace: 'normal', textAlign: 'right' }}>({pick({ en: 'needs both views', es: 'necesita ambas vistas' }, lang)})</span>
                      </>
                    ) : (
                      pc1(r.data_quality.consistency, lang)
                    )}
                  </td>
                  <td data-na={r.attribution_rank_correlation === null ? 'true' : undefined}>
                    {r.attribution_rank_correlation === null ? (
                      <>
                        {na}
                        <span className="ct-note" style={{ display: 'block', whiteSpace: 'normal', textAlign: 'right' }}>({pick({ en: 'no attribution on this shock', es: 'sin atribución en este choque' }, lang)})</span>
                      </>
                    ) : (
                      f3(r.attribution_rank_correlation, lang)
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <SgcdNotice sel={sel} />
        </LabelledOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

