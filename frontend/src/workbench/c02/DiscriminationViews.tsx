// C02's Validation group: how well each rung of the ladder ranks the firms that go bankrupt within the horizon (ROC and
// CAP with AUC, Gini and KS), whether a learned rung beats the champion by a margin the DeLong interval supports, whether
// the predicted PDs match the observed rates by decile (the reliability diagram), and whether the rung overfits (the gap
// between the training and the holdout AUC against its tolerance, a convention). The numbers are the bake's; a view
// draws the polyline of the document and nothing between its points that the document does not hold.
import { BarChart, PlotCard, ViewsRow, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { UPlotChart, type UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { ChartOverTable, alignTo, unionX } from '../c06/format';
import { useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { UnavailableCard } from '../c14/C14Common';
import { ParamTable, U14TestsTable, barMin, f2, f3, f4, int, pc, sig, testsOf, type NamedParam } from '../c20/U14Common';
import { challengerFor, outputsOf, rungFor, rungName, type C02Sel } from './selection';

const COLORS = ['--color-accent', '--color-magenta', '--color-warn', '--color-good', '--color-bad', '--color-fg-subtle'] as const;

/** The ROC (false against true positive rate) or the CAP (population against defaults captured) of every rung of the variant: one curve a rung and the random-ranking line, the rung in focus drawn thicker. */
export function rocChart(sel: C02Sel | null, kind: 'roc' | 'cap'): UPlotChartProps | null {
  const o = outputsOf(sel);
  if (!sel || !o || o.rungs.length === 0) return null;
  const xs = (r: (typeof o.rungs)[number]) => (kind === 'roc' ? r.roc.fpr : r.cap.population);
  const ys = (r: (typeof o.rungs)[number]) => (kind === 'roc' ? r.roc.tpr : r.cap.defaults);
  const x = unionX(...o.rungs.map(xs));
  const focus = rungFor(sel)?.model_id;
  return {
    height: 'fill',
    x: kind === 'roc'
      ? { values: x, label: { en: 'False positive rate', es: 'Tasa de falsos positivos' }, format: { decimals: 2 } }
      : { values: x, label: { en: 'Share of the firms, riskiest first', es: 'Parte de las empresas, las más riesgosas primero' }, format: { decimals: 2 } },
    y: kind === 'roc'
      ? { label: { en: 'True positive rate', es: 'Verdaderos positivos' }, range: [0, 1], format: { decimals: 2 } }
      : { label: { en: 'Share of the bankruptcies captured', es: 'Quiebras capturadas' }, range: [0, 1], format: { decimals: 2 } },
    series: [
      { label: { en: 'Random ranking', es: 'Orden al azar' }, values: x, color: '--color-fg-faint', dash: [4, 4], width: 1 },
      ...o.rungs.map((r, i) => ({ label: rungName(sel, r.model_id), values: alignTo(xs(r), ys(r), x), color: COLORS[i % COLORS.length], dash: i >= COLORS.length ? [6, 3] : undefined, width: r.model_id === focus ? 3 : 1.6 })),
    ],
  };
}

/** ROC and CAP with the AUC, its DeLong interval, Gini and KS of every rung. */
export function RocCapView({ sel }: { sel: C02Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const roc = rocChart(sel, 'roc');
  const cap = rocChart(sel, 'cap');
  if (!sel || !o || !roc || !cap) return <Pending />;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'ROC and the discrimination of each rung', es: 'ROC y discriminación de cada peldaño' }}
        {...card}
        note={{
          en: 'AUC with its 95% DeLong interval, Gini = 2 AUC - 1 and the Kolmogorov-Smirnov distance, on the locked holdout of the file. The files carry no date, so this is a within-file holdout and never an out-of-time test.',
          es: 'AUC con su intervalo DeLong de 95%, Gini = 2 AUC - 1 y la distancia de Kolmogorov-Smirnov, en la muestra reservada del archivo. Los archivos no traen fecha, así que esto es una muestra reservada dentro del archivo y nunca una prueba fuera del tiempo.',
        }}
      >
        <ChartOverTable chartMin="18rem" chart={<UPlotChart {...roc} />}>
          <table className="caos-table ct-wrap-head" data-table="discrimination">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Rung', es: 'Peldaño' }, lang)}</th>
                <th>AUC</th>
                <th>{pick({ en: '95% interval (DeLong)', es: 'Intervalo 95% (DeLong)' }, lang)}</th>
                <th>Gini</th>
                <th>KS</th>
              </tr>
            </thead>
            <tbody>
              {o.rungs.map((r) => (
                <tr key={r.model_id} data-rung={r.model_id} className={r.model_id === rungFor(sel)?.model_id ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(rungName(sel, r.model_id), lang)}</td>
                  <td>{f3(r.discrimination.auc, lang)}</td>
                  <td>{`${f3(r.discrimination.auc_ci.lo, lang)} - ${f3(r.discrimination.auc_ci.hi, lang)}`}</td>
                  <td>{f3(r.discrimination.gini, lang)}</td>
                  <td>{f3(r.discrimination.ks, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <U14TestsTable tests={sel.data.variant.tests} only={testsOf('disc.')} modelLabel={(id) => pick(rungName(sel, id), lang)} />
        </ChartOverTable>
      </PlotCard>
      <PlotCard
        fill
        title={{ en: 'CAP: bankruptcies captured', es: 'CAP: quiebras capturadas' }}
        {...card}
        note={{
          en: `Firms ordered from the riskiest to the safest by the rung's PD; the curve is the cumulative share of the bankruptcies they hold. The bankruptcy rate of the holdout is ${pc(sel && rungFor(sel)?.cap.default_rate, 'en')}.`,
          es: `Empresas ordenadas de la más riesgosa a la más segura por la PD del peldaño; la curva es la parte acumulada de las quiebras que reúnen. La tasa de quiebra de la muestra reservada es ${pc(sel && rungFor(sel)?.cap.default_rate, 'es')}.`,
        }}
      >
        <UPlotChart {...cap} />
      </PlotCard>
    </ViewsRow>
  );
}

/** The challenger rows of the variant against the champion: the DeLong difference of the AUC and the paired bootstrap of the Brier difference, with the grades that move. */
export function RungsView({ sel }: { sel: C02Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const focus = challengerFor(sel);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Do the learned rungs beat the champion?', es: '¿Superan los peldaños aprendidos al campeón?' }}
        {...card}
        note={{
          en: 'The bars are the AUC of every rung. The table gives each challenger minus the champion: the AUC difference with its 95% DeLong interval and p-value (an interval that holds zero is no evidence of a gain), the Brier difference with its paired-bootstrap interval, and the share of firms whose grade moves by two notches or more.',
          es: 'Las barras son el AUC de cada peldaño. La tabla da cada retador menos el campeón: la diferencia de AUC con su intervalo DeLong de 95% y su valor p (un intervalo que contiene el cero no es evidencia de una ganancia), la diferencia de Brier con su intervalo bootstrap pareado, y la parte de empresas cuyo grado se mueve dos escalones o más.',
        }}
      >
        <ChartOverTable
          chartMin={barMin(o.rungs.length)}
          chart={
            <BarChart
              title={{ en: 'AUC of each rung', es: 'AUC de cada peldaño' }}
              height="fill"
              orientation="horizontal"
              data={o.rungs.map((r) => ({ id: r.model_id, label: rungName(sel, r.model_id), value: r.discrimination.auc, highlight: r.model_id === focus?.challenger }))}
              axis={{ label: { en: 'AUC on the holdout', es: 'AUC en la muestra reservada' }, format: { decimals: 3 }, range: [0, 1] }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="challenger">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Challenger', es: 'Retador' }, lang)}</th>
                <th>{pick({ en: 'AUC difference', es: 'Diferencia de AUC' }, lang)}</th>
                <th>{pick({ en: '95% interval (DeLong)', es: 'Intervalo 95% (DeLong)' }, lang)}</th>
                <th>{pick({ en: 'p (DeLong)', es: 'p (DeLong)' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Brier difference', es: 'Diferencia de Brier' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: '95% interval (paired bootstrap)', es: 'Intervalo 95% (bootstrap pareado)' }, lang)}</th>
                <th>{pick({ en: 'Grades moved', es: 'Grados movidos' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.challenger.map((c) => (
                <tr key={`${c.champion}-${c.challenger}`} data-champion={c.champion} data-challenger={c.challenger} className={c.challenger === focus?.challenger ? 'ct-current' : undefined}>
                  <td className="ct-text">{`${pick(rungName(sel, c.challenger), lang)} ${pick({ en: 'against', es: 'contra' }, lang)} ${pick(rungName(sel, c.champion), lang)}`}</td>
                  <td>{f3(c.auc_diff, lang)}</td>
                  <td>{`${f3(c.auc_diff_ci.lo, lang)} - ${f3(c.auc_diff_ci.hi, lang)}`}</td>
                  <td>{sig(c.delong_p_value, lang)}</td>
                  <td className="ct-wide-only">{f4(c.brier_diff, lang)}</td>
                  <td className="ct-wide-only">{`${f4(c.brier_diff_ci.lo, lang)} - ${f4(c.brier_diff_ci.hi, lang)}`}</td>
                  <td>{pc(c.grade_disagreement_share, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The reliability diagram of the rung in focus: the predicted PD of each decile against the observed bankruptcy rate with its interval. */
export function CalibrationView({ sel }: { sel: C02Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  const r = rungFor(sel);
  if (!sel || !o || !r) return <Pending />;
  if (r.reliability.length === 0) {
    return <UnavailableCard sel={sel} title={{ en: 'Calibration by decile', es: 'Calibración por decil' }} reason={{ en: 'Not available: this document carries no reliability bin for the rung, and no diagram is drawn from nothing.', es: 'No disponible: este documento no trae ningún tramo de confiabilidad para el peldaño, y no se dibuja un diagrama de la nada.' }} />;
  }
  const x = r.reliability.map((b) => b.pd);
  const hl = r.calibration.hosmer_lemeshow;
  const name = pick(rungName(sel, r.model_id), lang);
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: `Calibration by decile: ${rungName(sel, r.model_id).en}`, es: `Calibración por decil: ${rungName(sel, r.model_id).es}` }}
        {...card}
        note={{
          en: `${name}: Hosmer-Lemeshow ${f2(hl.statistic, 'en')} on ${hl.df} degrees of freedom, p = ${sig(hl.p_value, 'en')}; Brier ${f3(r.calibration.brier, 'en')}; expected calibration error ${f3(r.calibration.ece, 'en')}. On the dashed line a PD is calibrated; above it the PD under-estimates the bankruptcy rate. Hosmer-Lemeshow and the Brier score are evidence of fit, not proof that a PD is right.`,
          es: `${name}: Hosmer-Lemeshow ${f2(hl.statistic, 'es')} con ${hl.df} grados de libertad, p = ${sig(hl.p_value, 'es')}; Brier ${f3(r.calibration.brier, 'es')}; error de calibración esperado ${f3(r.calibration.ece, 'es')}. Sobre la línea punteada una PD está calibrada; sobre ella, la PD subestima la tasa de quiebra. Hosmer-Lemeshow y el puntaje de Brier son evidencia de ajuste, no prueba de que una PD sea correcta.`,
        }}
      >
        <ChartOverTable
          chart={
            <UPlotChart
              height="fill"
              x={{ values: x, label: { en: 'PD applied (mean of the decile)', es: 'PD aplicada (media del decil)' }, format: { percent: true, decimals: 1 } }}
              y={{ label: { en: 'Observed bankruptcy rate', es: 'Tasa de quiebra observada' }, format: { percent: true, decimals: 1 } }}
              series={[
                { label: { en: 'Perfect calibration', es: 'Calibración perfecta' }, values: x, color: '--color-fg-faint', dash: [4, 4], width: 1 },
                { label: { en: 'Observed rate', es: 'Tasa observada' }, values: r.reliability.map((b) => b.dr), color: '--color-accent', mode: 'points' },
                { label: { en: 'Interval, upper', es: 'Intervalo, superior' }, values: r.reliability.map((b) => b.hi), color: '--color-magenta', dash: [3, 3], width: 1 },
                { label: { en: 'Interval, lower', es: 'Intervalo, inferior' }, values: r.reliability.map((b) => b.lo), color: '--color-magenta', dash: [3, 3], width: 1 },
              ]}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="reliability">
            <thead>
              <tr>
                <th>{pick({ en: 'Decile', es: 'Decil' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Firms', es: 'Empresas' }, lang)}</th>
                <th>{pick({ en: 'PD applied', es: 'PD aplicada' }, lang)}</th>
                <th>{pick({ en: 'Observed rate', es: 'Tasa observada' }, lang)}</th>
                <th>{pick({ en: 'Interval', es: 'Intervalo' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {r.reliability.map((b, i) => (
                <tr key={i} data-bin={i + 1}>
                  <td>{int(i + 1, lang)}</td>
                  <td className="ct-wide-only">{int(b.n, lang)}</td>
                  <td>{pc(b.pd, lang)}</td>
                  <td>{pc(b.dr, lang)}</td>
                  <td>{`${pc(b.lo, lang)} - ${pc(b.hi, lang)}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <U14TestsTable tests={sel.data.variant.tests} only={testsOf('pd.')} modelLabel={(id) => pick(rungName(sel, id), lang)} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The overfit gap of every rung against its tolerance (a convention) and the stability of the holdout against the training slice. */
export function StabilityView({ sel }: { sel: C02Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const tol = o.rungs[0]?.overfit.tolerance ?? null;
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'Overfit gap and stability of the holdout', es: 'Brecha de sobreajuste y estabilidad de la muestra reservada' }}
        {...card}
        note={{
          en: 'The gap is the training AUC minus the holdout AUC; the flag rises above the tolerance, which is a convention of Contraste (the dossier gives no value), never a regulatory threshold. PSI and the largest CSI compare the holdout with the training slice.',
          es: 'La brecha es el AUC de entrenamiento menos el AUC de la muestra reservada; la alerta se levanta sobre la tolerancia, que es una convención de Contraste (el dossier no da un valor), nunca un umbral regulatorio. El PSI y el mayor CSI comparan la muestra reservada con el tramo de entrenamiento.',
        }}
      >
        <ChartOverTable
          chartMin={barMin(o.rungs.length + 1)}
          chart={
            <BarChart
              title={{ en: 'Overfit gap by rung', es: 'Brecha de sobreajuste por peldaño' }}
              height="fill"
              orientation="horizontal"
              data={[
                ...o.rungs.map((r) => ({ id: r.model_id, label: rungName(sel, r.model_id), value: r.overfit.gap, tone: r.overfit.flag ? ('bad' as const) : ('good' as const), highlight: r.model_id === rungFor(sel)?.model_id })),
                ...(tol === null ? [] : [{ id: 'tolerance', label: { en: 'Tolerance (convention)', es: 'Tolerancia (convención)' }, value: tol, tone: 'warn' as const }]),
              ]}
              axis={{ label: { en: 'Train minus holdout AUC', es: 'AUC de entrenamiento menos de la muestra reservada' }, unit: { en: 'AUC points', es: 'puntos de AUC' }, format: { decimals: 3 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="overfit">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Rung', es: 'Peldaño' }, lang)}</th>
                <th>{pick({ en: 'Train AUC', es: 'AUC de entrenamiento' }, lang)}</th>
                <th>{pick({ en: 'Holdout AUC', es: 'AUC reservada' }, lang)}</th>
                <th>{pick({ en: 'Gap', es: 'Brecha' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Overfit', es: 'Sobreajuste' }, lang)}</th>
                <th>PSI</th>
                <th className="ct-wide-only">{pick({ en: 'Largest CSI', es: 'Mayor CSI' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {o.rungs.map((r) => (
                <tr key={r.model_id} data-rung={r.model_id} data-flag={r.overfit.flag} className={r.model_id === rungFor(sel)?.model_id ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(rungName(sel, r.model_id), lang)}</td>
                  <td>{f3(r.overfit.train_auc, lang)}</td>
                  <td>{f3(r.overfit.holdout_auc, lang)}</td>
                  <td>{f3(r.overfit.gap, lang)}</td>
                  <td className="ct-text">{pick(r.overfit.flag ? { en: 'flagged', es: 'alertado' } : { en: 'within tolerance', es: 'dentro de la tolerancia' }, lang)}</td>
                  <td>{f3(r.stability.psi, lang)}</td>
                  <td className="ct-wide-only">{f3(r.stability.csi_max, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <ParamTable params={o.parameters as unknown as NamedParam[]} only={['overfit_tolerance']} />
          <U14TestsTable tests={sel.data.variant.tests} only={testsOf('stability.', 'ml.')} modelLabel={(id) => pick(rungName(sel, id), lang)} />
        </ChartOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

