// C20's shift views, on the Federal Reserve 2025 corporate portfolios, read both ways and each labelled (decision Q7):
// the real drift between the three portfolios, with no model, and the portfolios as the reference of a synthetic shift
// injected into the evaluation set of a model fitted on the UCI Polish data. The label-free views, the conformal coverage
// by window and the CBPE estimate, say what a validator can know when the labels are withheld; CBPE is an estimate and is
// never presented as a measurement. A synthetic shift is a stress test, not a forecast.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { useCard } from '../c03/U6Shared';
import { Pending } from '../Pending';
import { Labelled, LabelledOverTable, barMin, f3, f4, int, pc, pc1, sig } from './U14Common';
import { NotInVariant, SgcdNotice } from './C20Common';
import { RULE_OF_THUMB } from './ShockViews';
import { PORTFOLIO_TEXT, asKind, text, type C20Sel } from './selection';

const TITLE_REAL: BiText = { en: 'Real drift between the portfolios', es: 'Deriva real entre las carteras' };
const TITLE_SYNTH: BiText = { en: 'Synthetic shift', es: 'Cambio sintético' };
const TITLE_CONFORMAL: BiText = { en: 'Conformal coverage over time', es: 'Cobertura conforme en el tiempo' };
const TITLE_CBPE: BiText = { en: 'Label-free performance estimate', es: 'Estimación de desempeño sin etiquetas' };

/** The real drift between two portfolios of the Federal Reserve, variable by variable, with no model: PSI, CSI, KS and the chi-square test. */
export function RealDriftView({ sel }: { sel: C20Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  if (!sel) return <Pending />;
  const o = asKind(sel, 'shift');
  if (!o) return <NotInVariant sel={sel} title={TITLE_REAL} needs="shift" />;
  const d = o.real_drift;
  const name = (id: string) => pick(text(PORTFOLIO_TEXT, id), lang);
  const bars = d.pairs.flatMap((p) => p.variables.map((v) => ({ id: `${p.a}-${p.b}-${v.name}`, label: { en: `${v.name} (${text(PORTFOLIO_TEXT, p.a).en} to ${text(PORTFOLIO_TEXT, p.b).en})`, es: `${v.name} (${text(PORTFOLIO_TEXT, p.a).es} a ${text(PORTFOLIO_TEXT, p.b).es})` }, value: v.psi })));
  const rules = RULE_OF_THUMB.map((v) => ({
    id: `rule-${v}`,
    label: { en: `Rule of thumb ${formatNumber(v, 'en', { decimals: 2 })} (convention)`, es: `Regla empírica ${formatNumber(v, 'es', { decimals: 2 })} (convención)` },
    value: v,
    tone: 'neutral' as const,
  }));
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={TITLE_REAL}
        {...card}
        note={{
          en: 'The portfolios of typical, higher and lower risk are different real populations of loans, so the drift between them is a real shift. No model is scored here: the view compares the variables only. The grey bars are the legacy PSI rule of thumb, a convention and not a regulatory threshold.',
          es: 'Las carteras de riesgo típico, mayor y menor son poblaciones reales distintas de créditos, así que la deriva entre ellas es un cambio real. Aquí no se puntúa ningún modelo: la vista compara solo las variables. Las barras grises son la regla empírica heredada del PSI, una convención y no un umbral regulatorio.',
        }}
      >
        <LabelledOverTable
          head={
            <Labelled
              label={d.label}
              reason={{ en: 'Real drift between the portfolios, with no model.', es: 'Deriva real entre las carteras, sin modelo.' }}
            />
          }
          chartMin={barMin(bars.length + rules.length)}
          chart={
            bars.length === 0 ? (
              <p className="caos-pending" data-state="unavailable">{pick({ en: 'Not available: the document carries no variable of any portfolio pair.', es: 'No disponible: el documento no trae ninguna variable de ningún par de carteras.' }, lang)}</p>
            ) : (
              <BarChart
                title={{ en: 'PSI by variable and portfolio pair', es: 'PSI por variable y par de carteras' }}
                height="fill"
                orientation="horizontal"
                data={[...bars, ...rules]}
                axis={{ label: { en: 'Population stability index', es: 'Índice de estabilidad poblacional' }, format: { decimals: 2 } }}
              />
            )
          }
        >
          <table className="caos-table ct-wrap-head" data-table="real-drift">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Pair', es: 'Par' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'Variable', es: 'Variable' }, lang)}</th>
                <th>PSI</th>
                <th>CSI</th>
                <th className="ct-wide-only">KS</th>
                <th>{pick({ en: 'Chi-square p', es: 'p chi-cuadrado' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {d.pairs.flatMap((p) =>
                p.variables.map((v) => (
                  <tr key={`${p.a}-${p.b}-${v.name}`} data-pair={`${p.a}-${p.b}`} data-input={v.name}>
                    <td className="ct-text">{`${name(p.a)} / ${name(p.b)}`}</td>
                    <td className="ct-text">{v.name}</td>
                    <td>{f3(v.psi, lang)}</td>
                    <td>{f3(v.csi, lang)}</td>
                    <td className="ct-wide-only">{f3(v.ks, lang)}</td>
                    <td data-na={v.chi2_p_value === null ? 'true' : undefined}>{v.chi2_p_value === null ? formatNumber(null, lang) : sig(v.chi2_p_value, lang)}</td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </LabelledOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The synthetic shift of the evaluation set built from a portfolio as the reference: performance, PSI and flips under each shift, and the worst subsample. */
export function SyntheticShiftView({ sel }: { sel: C20Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  if (!sel) return <Pending />;
  const o = asKind(sel, 'shift');
  if (!o) return <NotInVariant sel={sel} title={TITLE_SYNTH} needs="shift" />;
  const s = o.synthetic_shift;
  const rows = [
    ...s.shifts.map((x) => ({ id: x.shift_id, label: { en: x.shift_id, es: x.shift_id } as BiText, value: x.metric.auc_delta, highlight: x.shift_id === sel.shift })),
    { id: 'worst', label: { en: `Worst ${pc1(s.worst_subsample.share, 'en')} of the rows`, es: `Peor ${pc1(s.worst_subsample.share, 'es')} de las filas` } as BiText, value: s.worst_subsample.metric.auc_delta, highlight: false },
  ];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={TITLE_SYNTH}
        {...card}
        note={{
          en: `The ${text(PORTFOLIO_TEXT, s.reference_portfolio).en.toLowerCase()} portfolio is the reference of the shift, injected into the evaluation set ${s.evaluation_set} only. The score is the strength of the shift; the cut-off of the decision flips is held fixed. A stress test, not a forecast.`,
          es: `La cartera de ${text(PORTFOLIO_TEXT, s.reference_portfolio).es.toLowerCase()} es la referencia del cambio, inyectado solo en el conjunto de evaluación ${s.evaluation_set}. El puntaje es la fuerza del cambio; el corte de las decisiones que cambian se mantiene fijo. Una prueba de estrés, no un pronóstico.`,
        }}
      >
        <LabelledOverTable
          head={<Labelled label={s.label} reason={{ en: 'Synthetic shift with a Federal Reserve portfolio as its reference, on the UCI evaluation set.', es: 'Cambio sintético con una cartera de la Reserva Federal como referencia, en el conjunto de evaluación de UCI.' }} />}
          chartMin={barMin(rows.length)}
          chart={
            <BarChart
              title={{ en: 'AUC change under each shift', es: 'Cambio del AUC bajo cada cambio' }}
              height="fill"
              orientation="horizontal"
              data={rows.map((r) => ({ ...r, tone: r.value < 0 ? ('bad' as const) : ('good' as const) }))}
              axis={{ label: { en: 'AUC change against the unshifted set', es: 'Cambio del AUC contra el conjunto sin cambio' }, format: { decimals: 3 } }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="synthetic-shift">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Shift', es: 'Cambio' }, lang)}</th>
                <th>{pick({ en: 'Strength', es: 'Fuerza' }, lang)}</th>
                <th>AUC</th>
                <th>{pick({ en: 'AUC change', es: 'Cambio del AUC' }, lang)}</th>
                <th className="ct-wide-only">PSI</th>
                <th>{pick({ en: 'Flips', es: 'Cambian' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {s.shifts.map((x) => (
                <tr key={x.shift_id} data-shift={x.shift_id} className={x.shift_id === sel.shift ? 'ct-current' : undefined}>
                  <td className="ct-text">{x.shift_id}</td>
                  <td>{f3(x.score, lang)}</td>
                  <td>{f3(x.metric.auc, lang)}</td>
                  <td>{f4(x.metric.auc_delta, lang)}</td>
                  <td className="ct-wide-only">{f3(x.psi, lang)}</td>
                  <td>{pc1(x.flip_share, lang)}</td>
                </tr>
              ))}
              <tr data-shift="worst-subsample">
                <td className="ct-text">{pick({ en: `Worst ${pc1(s.worst_subsample.share, 'en')}`, es: `Peor ${pc1(s.worst_subsample.share, 'es')}` }, lang)}</td>
                <td data-na="true">{formatNumber(null, lang)}</td>
                <td>{f3(s.worst_subsample.metric.auc, lang)}</td>
                <td>{f4(s.worst_subsample.metric.auc_delta, lang)}</td>
                <td className="ct-wide-only" data-na="true">{formatNumber(null, lang)}</td>
                <td data-na="true">{formatNumber(null, lang)}</td>
              </tr>
            </tbody>
          </table>
        </LabelledOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The split conformal coverage by window against its target: a coverage that falls below it reads as an exchangeability violation. */
export function ConformalView({ sel }: { sel: C20Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  if (!sel) return <Pending />;
  const o = asKind(sel, 'shift');
  if (!o) return <NotInVariant sel={sel} title={TITLE_CONFORMAL} needs="shift" />;
  const c = o.synthetic_shift.label_free.conformal;
  const rows = [
    ...c.coverage_by_window.map((w) => ({ id: w.window, label: { en: w.window, es: w.window } as BiText, value: w.coverage, highlight: w.window === sel.window, tone: w.coverage < c.target_coverage ? ('bad' as const) : ('good' as const) })),
    { id: 'overall', label: { en: 'All windows', es: 'Todas las ventanas' } as BiText, value: c.coverage, highlight: false, tone: undefined },
    { id: 'target', label: { en: 'Target (1 minus alpha)', es: 'Meta (1 menos alfa)' } as BiText, value: c.target_coverage, highlight: false, tone: 'neutral' as const },
  ];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={TITLE_CONFORMAL}
        {...card}
        note={{
          en: `Split conformal prediction with alpha ${f3(c.alpha, 'en')} (a convention): the sets cover the true label at least 1 minus alpha of the time when calibration and evaluation are exchangeable. A window that falls below the target, with a small binomial p-value, says the evaluation data have left the calibration data.`,
          es: `Predicción conforme dividida con alfa ${f3(c.alpha, 'es')} (una convención): los conjuntos cubren la etiqueta verdadera al menos 1 menos alfa de las veces cuando calibración y evaluación son intercambiables. Una ventana bajo la meta, con un valor p binomial pequeño, dice que los datos de evaluación se alejaron de los de calibración.`,
        }}
      >
        <LabelledOverTable
          head={<Labelled label={c.label} reason={{ en: 'Coverage is measured without labels being needed for the sets; the alpha is a convention.', es: 'La cobertura se mide sin necesitar etiquetas para los conjuntos; alfa es una convención.' }} />}
          chartMin={barMin(rows.length)}
          chart={
            <BarChart
              title={{ en: 'Coverage by window', es: 'Cobertura por ventana' }}
              height="fill"
              orientation="horizontal"
              data={rows}
              axis={{ label: { en: 'Coverage of the conformal sets', es: 'Cobertura de los conjuntos conformes' }, format: { percent: true, decimals: 0 }, range: [0, 1] }}
            />
          }
        >
          <table className="caos-table ct-wrap-head" data-table="conformal">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Window', es: 'Ventana' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Rows', es: 'Filas' }, lang)}</th>
                <th>{pick({ en: 'Coverage', es: 'Cobertura' }, lang)}</th>
                <th>{pick({ en: 'p (binomial)', es: 'p (binomial)' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {c.coverage_by_window.map((w) => (
                <tr key={w.window} data-window={w.window} data-below-target={w.coverage < c.target_coverage} className={w.window === sel.window ? 'ct-current' : undefined}>
                  <td className="ct-text">{w.window}</td>
                  <td className="ct-wide-only">{int(w.n, lang)}</td>
                  <td>{pc1(w.coverage, lang)}</td>
                  <td>{sig(w.binomial_p_value, lang)}</td>
                </tr>
              ))}
              <tr data-window="all">
                <td className="ct-text">{pick({ en: 'All windows', es: 'Todas las ventanas' }, lang)}</td>
                <td className="ct-wide-only" data-na="true">{formatNumber(null, lang)}</td>
                <td>{pc1(c.coverage, lang)}</td>
                <td>{sig(c.binomial_p_value, lang)}</td>
              </tr>
            </tbody>
          </table>
        </LabelledOverTable>
      </PlotCard>
    </ViewsRow>
  );
}

/** The CBPE estimate of the AUC where labels are withheld, beside the AUC measured under each shift, always labelled an estimate with its four assumptions. */
export function CbpeView({ sel }: { sel: C20Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  if (!sel) return <Pending />;
  const o = asKind(sel, 'shift');
  if (!o) return <NotInVariant sel={sel} title={TITLE_CBPE} needs="shift" />;
  const s = o.synthetic_shift;
  const e = s.label_free.cbpe;
  const rows = [
    ...s.shifts.map((x) => ({ id: x.shift_id, label: { en: `Measured, ${x.shift_id}`, es: `Medido, ${x.shift_id}` } as BiText, value: x.metric.auc })),
    { id: 'cbpe', label: { en: 'CBPE estimate (no labels)', es: 'Estimación CBPE (sin etiquetas)' } as BiText, value: e.estimated_auc, tone: 'warn' as const },
  ];
  return (
    <ViewsRow>
      <PlotCard
        fill
        title={TITLE_CBPE}
        {...card}
        note={{
          en: 'The confidence-based performance estimate reads the AUC from the model\'s own probabilities when the labels are not yet known. It is an estimate under four assumptions, never a measurement.',
          es: 'La estimación de desempeño basada en confianza lee el AUC de las probabilidades del propio modelo cuando las etiquetas aún no se conocen. Es una estimación bajo cuatro supuestos, nunca una medición.',
        }}
      >
        <LabelledOverTable
          head={<Labelled label={e.label} reason={{ en: 'An estimate with its assumptions, not a measured result.', es: 'Una estimación con sus supuestos, no un resultado medido.' }} />}
          chartMin={barMin(rows.length)}
          chart={
            <BarChart
              title={{ en: 'AUC measured and estimated', es: 'AUC medido y estimado' }}
              height="fill"
              orientation="horizontal"
              data={rows}
              axis={{ label: { en: 'AUC', es: 'AUC' }, format: { decimals: 2 }, range: [0, 1] }}
            />
          }
        >
          <p data-cbpe="estimate">
            <strong>{pick({ en: 'Estimated AUC', es: 'AUC estimado' }, lang)}</strong>: {f3(e.estimated_auc, lang)}
          </p>
          <ul className="ct-note" data-list="cbpe-assumptions">
            {e.assumptions.map((a) => (
              <li key={a.id} data-assumption={a.id}>{pick(a.text, lang)}</li>
            ))}
          </ul>
          <SgcdNotice sel={sel} />
          <p className="ct-note">{pick({ en: `Share of rows in the worst subsample: ${pc(s.worst_subsample.share, 'en')}.`, es: `Parte de las filas en la peor submuestra: ${pc(s.worst_subsample.share, 'es')}.` }, lang)}</p>
        </LabelledOverTable>
      </PlotCard>
    </ViewsRow>
  );
}
