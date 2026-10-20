// C20's robustness views: performance against the noise scale (perturbation), the dispersion across retraining seeds,
// the agreement of the attributions with the effect curves, and the leakage screen with its planted leak. The tolerances
// and the limits are conventions of Contraste and are labelled so (06 I.6 l.1268-1270); a null field says "not available"
// with its reason. Every view that can show SGCD carries the dataset card's sentence.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable } from '../c06/format';
import { useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { NotInVariant, SgcdNotice } from './C20Common';
import { LabelledOverTable, ParamTable, barMin, f3, f4, int, pc1, type NamedParam } from './U14Common';
import { SCREEN_TEXT, asKind, type C20Sel } from './selection';

/** The noise scales of the grid with the AUC at each, a line against the scale, and the preset scale where a degradation beyond the tolerance is a finding. */
export function PerturbationView({ sel }: { sel: C20Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const title: BiText = { en: 'Performance against the noise scale', es: 'Desempeño contra la escala de ruido' };
  if (!sel) return <Pending />;
  const o = asKind(sel, 'perturbation');
  if (!o) return <NotInVariant sel={sel} title={title} needs="perturbation" />;
  const tol = o.parameters.find((p) => p.name === 'perturbation_tolerance');
  const preset = o.rows.find((r) => r.eps === o.preset_eps) ?? null;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'Gaussian noise proportional to the standard deviation of each input is added to the evaluation features only. A finding is raised when the AUC loss at the preset scale exceeds the tolerance, which is a convention of Contraste and not a regulatory threshold.',
          es: 'Se añade ruido gaussiano proporcional a la desviación estándar de cada entrada solo a las variables de evaluación. Se levanta un hallazgo cuando la pérdida de AUC en la escala preestablecida supera la tolerancia, que es una convención de Contraste y no un umbral regulatorio.',
        }}
      >
        <ChartOverTable
          chart={
            o.rows.length === 0 ? (
              <p className="caos-pending" data-state="unavailable">{pick({ en: 'Not available: the document carries no noise scale.', es: 'No disponible: el documento no trae ninguna escala de ruido.' }, lang)}</p>
            ) : (
              <UPlotChart
                height="fill"
                x={{ values: o.rows.map((r) => r.eps), label: { en: 'Noise scale', es: 'Escala de ruido' }, unit: { en: 'sd of each input', es: 'desv. de cada entrada' }, format: { digits: 3 } }}
                y={{ label: { en: 'AUC', es: 'AUC' }, format: { decimals: 3 } }}
                series={[{ label: { en: 'AUC under noise', es: 'AUC bajo ruido' }, values: o.rows.map((r) => r.metric.auc), color: '--color-accent', width: 2.4 }]}
                marks={[{ x: o.preset_eps, label: { en: 'Preset scale', es: 'Escala preestablecida' } }]}
              />
            )
          }
        >
          <table className="caos-table ct-wrap-head" data-table="perturbation">
            <thead>
              <tr>
                <th>{pick({ en: 'Noise scale', es: 'Escala de ruido' }, lang)}</th>
                <th>AUC</th>
                <th className="ct-wide-only">Brier</th>
                <th>{pick({ en: 'AUC change', es: 'Cambio del AUC' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Finding', es: 'Hallazgo' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.rows.map((r, i) => (
                <tr key={r.eps} data-eps={r.eps} data-finding={r.finding} data-preset={r.eps === o.preset_eps} className={i === sel.eps ? 'ct-current' : undefined}>
                  <td>{formatNumber(r.eps, lang, { digits: 3 })}</td>
                  <td>{f3(r.metric.auc, lang)}</td>
                  <td className="ct-wide-only">{f3(r.metric.brier, lang)}</td>
                  <td>{f4(r.metric.auc_delta, lang)}</td>
                  <td className="ct-text">
                    {r.eps === o.preset_eps
                      ? pick(r.finding ? { en: 'finding at the preset scale', es: 'hallazgo en la escala preestablecida' } : { en: 'within tolerance at the preset scale', es: 'dentro de la tolerancia en la escala preestablecida' }, lang)
                      : pick({ en: 'not the preset scale', es: 'no es la escala preestablecida' }, lang)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="ct-note" data-preset-delta={preset?.metric.auc_delta ?? ''}>
            {tol ? pick({ en: `Tolerance (convention): ${f3(tol.value as number, 'en')} AUC points at the preset scale ${formatNumber(o.preset_eps, 'en', { digits: 3 })}.`, es: `Tolerancia (convención): ${f3(tol.value as number, 'es')} puntos de AUC en la escala preestablecida ${formatNumber(o.preset_eps, 'es', { digits: 3 })}.` }, lang) : pick({ en: 'The tolerance is not available in this document.', es: 'La tolerancia no está disponible en este documento.' }, lang)}
          </p>
          <SgcdNotice sel={sel} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The dispersion of the AUC, of the grade assigned to each obligor and of the attribution ranks across retraining seeds, and the top-four reason overlap. */
export function SeedsView({ sel }: { sel: C20Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const title: BiText = { en: 'Dispersion across retraining seeds', es: 'Dispersión entre semillas de reentrenamiento' };
  if (!sel) return <Pending />;
  const o = asKind(sel, 'seeds');
  if (!o) return <NotInVariant sel={sel} title={title} needs="seeds" />;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'Each rung is retrained across seeds. The AUC range shows how much a model changes with the randomness of its own training; the grade share and the attribution rank correlation show whether obligors and explanations move with it; the reason codes are the share of the top four reasons kept across bootstrap refits.',
          es: 'Cada peldaño se reentrena con varias semillas. El rango del AUC muestra cuánto cambia un modelo con el azar de su propio entrenamiento; la parte de grados y la correlación de rangos de atribución muestran si los deudores y las explicaciones se mueven con él; los códigos de razón son la parte de las cuatro razones principales que se mantiene entre reajustes bootstrap.',
        }}
      >
        <LabelledOverTable
          chartMin={barMin(Math.max(1, o.rows.length) * 2)}
          chart={
            o.rows.length === 0 ? (
              <p className="caos-pending" data-state="unavailable">{pick({ en: 'Not available: the document carries no seed row.', es: 'No disponible: el documento no trae ninguna fila de semillas.' }, lang)}</p>
            ) : (
              <BarChart
                title={{ en: 'Spread of the AUC and the reason codes kept', es: 'Dispersión del AUC y códigos de razón que se mantienen' }}
                height="fill"
                orientation="horizontal"
                data={o.rows.flatMap((r) => [
                  { id: `${r.rung}-range`, label: { en: `${r.rung}: AUC range`, es: `${r.rung}: rango del AUC` } as BiText, value: r.auc.max - r.auc.min, highlight: r.rung === sel.rung },
                  { id: `${r.rung}-reasons`, label: { en: `${r.rung}: reasons kept`, es: `${r.rung}: razones que se mantienen` } as BiText, value: r.reason_code_overlap.mean, tone: 'good' as const },
                ])}
                axis={{ label: { en: 'AUC points, or share kept', es: 'Puntos de AUC, o parte que se mantiene' }, format: { decimals: 3 } }}
              />
            )
          }
        >
          <table className="caos-table ct-wrap-head" data-table="seeds">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Rung', es: 'Peldaño' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Seeds', es: 'Semillas' }, lang)}</th>
                <th>{pick({ en: 'AUC mean', es: 'AUC media' }, lang)}</th>
                <th>{pick({ en: 'AUC sd', es: 'AUC desv.' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'AUC min - max', es: 'AUC mín - máx' }, lang)}</th>
                <th>{pick({ en: 'Grades changed', es: 'Grados cambiados' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Rank tau, mean', es: 'Tau de rangos, media' }, lang)}</th>
                <th>{pick({ en: 'Reasons kept', es: 'Razones que se mantienen' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.rows.map((r) => (
                <tr key={r.rung} data-rung={r.rung} className={r.rung === sel.rung ? 'ct-current' : undefined}>
                  <td className="ct-text">{r.rung}</td>
                  <td className="ct-wide-only">{int(r.n_seeds, lang)}</td>
                  <td>{f3(r.auc.mean, lang)}</td>
                  <td>{f4(r.auc.sd, lang)}</td>
                  <td className="ct-wide-only">{`${f3(r.auc.min, lang)} - ${f3(r.auc.max, lang)}`}</td>
                  <td>{pc1(r.grade_assignment_changed_share, lang)}</td>
                  <td className="ct-wide-only">{f3(r.attribution_rank_tau.mean, lang)}</td>
                  <td data-top-k={r.reason_code_overlap.top_k}>{`${pc1(r.reason_code_overlap.mean, lang)} (p05 ${pc1(r.reason_code_overlap.p05, lang)})`}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <ParamTable params={o.parameters as unknown as NamedParam[]} only={['n_seeds', 'n_bootstrap_refits']} />
          <SgcdNotice sel={sel} />
        </LabelledOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The agreement of the SHAP attribution ranks with the accumulated local effect curves of the top features. */
export function ExplainerView({ sel }: { sel: C20Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const title: BiText = { en: 'Explainer agreement', es: 'Acuerdo de los explicadores' };
  if (!sel) return <Pending />;
  const o = asKind(sel, 'seeds');
  if (!o) return <NotInVariant sel={sel} title={title} needs="seeds" />;
  const ex = o.explainer_agreement.find((e) => e.rung === sel.rung) ?? o.explainer_agreement[0] ?? null;
  const top = ex?.top_features[0] ?? null;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: 'The rank correlation compares the importance the attribution gives each feature with the range of its effect curve (the accumulated local effect, centred to mean zero). A low agreement says the two explainers tell different stories about the same model.',
          es: 'La correlación de rangos compara la importancia que la atribución da a cada variable con el rango de su curva de efecto (el efecto local acumulado, centrado en media cero). Un acuerdo bajo dice que los dos explicadores cuentan historias distintas del mismo modelo.',
        }}
      >
        {!ex ? (
          <p className="caos-pending" data-state="unavailable">{pick({ en: 'Not available: the document carries no explainer block for a rung.', es: 'No disponible: el documento no trae un bloque de explicadores para ningún peldaño.' }, lang)}</p>
        ) : (
          <ChartOverTable
            chart={
              top && top.ale.effect.length > 0 ? (
                <UPlotChart
                  height="fill"
                  x={{ values: top.ale.edges.slice(0, top.ale.effect.length).map((e, i) => (e + top.ale.edges[i + 1]) / 2), label: { en: `${top.feature} (bin centre)`, es: `${top.feature} (centro del tramo)` }, format: { digits: 3 } }}
                  y={{ label: { en: 'Accumulated local effect', es: 'Efecto local acumulado' }, format: { decimals: 3 } }}
                  series={[{ label: { en: `Effect of ${top.feature}`, es: `Efecto de ${top.feature}` }, values: top.ale.effect, color: '--color-accent', width: 2.2 }]}
                />
              ) : (
                <p className="caos-pending" data-state="unavailable">{pick({ en: 'Not available: no effect curve for the top feature.', es: 'No disponible: sin curva de efecto para la variable principal.' }, lang)}</p>
              )
            }
          >
            <p data-explainer={ex.rung} data-rank-null={ex.rank_correlation === null}>
              <strong>{pick({ en: 'Rank correlation', es: 'Correlación de rangos' }, lang)}</strong>:{' '}
              {ex.rank_correlation === null ? (
                <span data-na="true">{`${formatNumber(null, lang)} (${ex.reason_if_null ?? pick({ en: 'no reason given', es: 'sin razón dada' }, lang)})`}</span>
              ) : (
                f3(ex.rank_correlation, lang)
              )}{' '}
              ({pick({ en: `${ex.n_features} features, reference ${ex.effect_reference.toUpperCase()}`, es: `${ex.n_features} variables, referencia ${ex.effect_reference.toUpperCase()}` }, lang)})
            </p>
            <table className="caos-table ct-wrap-head" data-table="explainer">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Feature', es: 'Variable' }, lang)}</th>
                  <th>{pick({ en: 'Attribution importance', es: 'Importancia por atribución' }, lang)}</th>
                  <th>{pick({ en: 'Effect range', es: 'Rango del efecto' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {ex.top_features.map((f) => (
                  <tr key={f.feature} data-feature={f.feature}>
                    <td className="ct-text">{f.feature}</td>
                    <td>{f3(f.shap_importance, lang)}</td>
                    <td>{f3(f.effect_range, lang)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ChartOverTable>
        )}
      </PlotCard>
    </ViewsRow>
  );
}

/** The four screens of the leakage check on a planted leak, the limits as conventions, and the performance that collapses at decision time. */
export function LeakageView({ sel }: { sel: C20Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const title: BiText = { en: 'Leakage screen', es: 'Filtro de fuga' };
  if (!sel) return <Pending />;
  const o = asKind(sel, 'leakage');
  if (!o) return <NotInVariant sel={sel} title={title} needs="leakage" />;
  const s = o.screen;
  const t = o.thresholds;
  const word = (b: boolean): BiText => (b ? { en: 'raised', es: 'activado' } : { en: 'clear', es: 'sin alerta' });
  const rows: Array<{ id: keyof typeof SCREEN_TEXT; value: string; limit: string; raised: boolean }> = [
    { id: 'temporal', value: int(s.temporal_order.violations, lang), limit: '0', raised: s.temporal_order.violations > 0 },
    { id: 'single', value: `${f3(s.single_feature_auc.max_auc, lang)} (${s.single_feature_auc.feature})`, limit: `${f3(t.single_feature_auc.value, lang)} (${pick({ en: 'convention', es: 'convención' }, lang)})`, raised: s.single_feature_auc.suspect },
    { id: 'overlap', value: pc1(s.entity_overlap.share, lang), limit: pc1(0, lang), raised: s.entity_overlap.share > 0 },
    { id: 'resemblance', value: f3(s.resemblance_auc, lang), limit: `${f3(t.resemblance_auc.value, lang)} (${pick({ en: 'convention', es: 'convención' }, lang)})`, raised: s.resemblance_auc > t.resemblance_auc.value },
  ];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={title}
        {...card}
        note={{
          en: `A feature (${o.planted_feature}) was planted to leak the outcome. The screens are the temporal order, the best AUC of a single feature, the overlap of entities between training and test and the resemblance AUC of development against evaluation rows; the limits are conventions of Contraste.`,
          es: `Se plantó una variable (${o.planted_feature}) que filtra el resultado. Los filtros son el orden temporal, el mejor AUC de una sola variable, el solapamiento de entidades entre entrenamiento y prueba y el AUC de parecido de las filas de desarrollo contra evaluación; los límites son convenciones de Contraste.`,
        }}
      >
        <LabelledOverTable
          chartMin={barMin(2)}
          chart={
            <BarChart
              title={{ en: 'AUC in development and at decision time', es: 'AUC en desarrollo y en el momento de la decisión' }}
              height="fill"
              orientation="horizontal"
              data={[
                { id: 'development', label: { en: 'Development, with the leak', es: 'Desarrollo, con la fuga' }, value: o.performance.development_auc },
                { id: 'decision', label: { en: 'At decision time', es: 'En el momento de la decisión' }, value: o.performance.decision_time_auc, tone: 'bad' },
              ]}
              axis={{ label: { en: 'AUC', es: 'AUC' }, format: { decimals: 2 }, range: [0, 1] }}
            />
          }
        >
          <p data-caught={o.caught}>
            <strong>{pick({ en: 'Planted leak', es: 'Fuga plantada' }, lang)}</strong>:{' '}
            {pick(o.caught ? { en: 'caught by the screen', es: 'detectada por el filtro' } : { en: 'NOT caught by the screen', es: 'NO detectada por el filtro' }, lang)}
          </p>
          <table className="caos-table ct-wrap-head" data-table="leakage-screen">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Screen', es: 'Filtro' }, lang)}</th>
                <th>{pick({ en: 'Value', es: 'Valor' }, lang)}</th>
                <th>{pick({ en: 'Limit', es: 'Límite' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Alert', es: 'Alerta' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} data-screen={r.id} data-raised={r.raised} className={r.id === sel.screen ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(SCREEN_TEXT[r.id], lang)}</td>
                  <td>{r.value}</td>
                  <td>{r.limit}</td>
                  <td className="ct-text">{pick(word(r.raised), lang)}</td>
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
