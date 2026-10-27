// C08's Validation, Variants and Context groups, and the live read-outs of its rail (ADR-0017 rule 3: every section
// shows a value that moves with its controls). The Findings card and the fixture notice are the ones C06 and C07 use.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { loadAllVariants, useArtifact } from '../../api/artifacts';
import type { VariantArtifact } from '../../lib/contract.types';
import { FindingsCard, FixtureNotice } from '../c06/C06Common';
import { ChartOverTable } from '../c06/format';
import { Pending } from '../Pending';
import { Flagged, LiveReadout, flaggedItem, p2, useCard } from '../c03/U6Shared';
import { DATASET_TEXT, INCOMPLETE_TEXT, WORKOUT_CONVENTION, freddieReason, outputsOf, type C08Outputs, type C08Sel } from './selection';
import { truthText, wordsOf } from './words';

const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });

export function C08FindingsView({ sel }: { sel: C08Sel | null }) {
  if (!sel) return <Pending />;
  return (
    <ViewsRow>
      <FindingsCard variant={sel.data.variant} />
    </ViewsRow>
  );
}

/** The default cohorts side by side: the mean LGD proxy of each, with its flag. Pick one to load it. */
export function C08VariantsTable({ variants, onPick, current }: { variants: Array<{ id: string; title: BiText; v: VariantArtifact<C08Outputs> }>; onPick: (id: string) => void; current: string }) {
  const lang = useShellLang();
  const first = variants[0]?.v;
  const card = useCard(first as unknown as VariantArtifact | undefined);
  return (
    <PlotCard
      fill
      title={{ en: 'The default cohorts', es: 'Las cohortes de incumplimiento' }}
      {...card}
      note={{ en: 'The mean LGD proxy of the defaults of each cohort; a mean outside 0 to 1 would carry its flag. Pick a cohort to load it.', es: 'La media de la LGD aproximada de los incumplimientos de cada cohorte; una media fuera de 0 a 1 llevaría su marca. Elija una cohorte para cargarla.' }}
    >
      <ChartOverTable
        chart={
          <BarChart
            title={{ en: 'Mean LGD proxy by default cohort', es: 'LGD aproximada media por cohorte de incumplimiento' }}
            height="fill"
            orientation="vertical"
            data={variants.map(({ id, title, v }) => ({ id, label: title, value: v.outputs.lgd_distribution.mean.value, tone: v.outputs.lgd_distribution.mean.flag === 'in-range' ? ('accent' as const) : ('bad' as const), highlight: id === current }))}
            axis={{ label: { en: 'Mean LGD proxy', es: 'LGD aproximada media' }, format: { percent: true, digits: 2 } }}
          />
        }
      >
        <table className="caos-table ct-wrap-head" data-table="variants-c08">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Default cohort', es: 'Cohorte de incumplimiento' }, lang)}</th>
              <th className="ct-wide-only">{pick({ en: 'Defaults', es: 'Incumplimientos' }, lang)}</th>
              <th>{pick({ en: 'Mean', es: 'Media' }, lang)}</th>
              <th>{pick({ en: 'Median', es: 'Mediana' }, lang)}</th>
              <th>{pick({ en: 'Exactly 1', es: 'Exactamente 1' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {variants.map(({ id, title, v }) => {
              const d = v.outputs.lgd_distribution;
              return (
                <tr key={id} data-variant={id} className={id === current ? 'ct-current' : undefined}>
                  <td className="ct-text">
                    <button type="button" className="ct-linkbutton" onClick={() => onPick(id)}>{pick(title, lang)}</button>
                  </td>
                  <td className="ct-wide-only">{count(d.n, lang)}</td>
                  <td>
                    <Flagged value={d.mean.value} flag={d.mean.flag} />
                  </td>
                  <td>
                    <Flagged value={d.median.value} flag={d.median.flag} />
                  </td>
                  <td>{p2(d.mass_at_one.share, lang)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </ChartOverTable>
    </PlotCard>
  );
}

export function C08VariantsView({ sel, onPick }: { sel: C08Sel | null; onPick: (id: string) => void }) {
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  if (!sel || all.state !== 'ready') return <Pending />;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const variants = (all.data as unknown as Array<VariantArtifact<C08Outputs>>)
    .filter((v) => v.outputs.kind === 'default-cohort')
    .map((v) => ({ id: v.variant_id, title: entries.find((e) => e.variant_id === v.variant_id)?.short_title ?? { en: v.variant_id, es: v.variant_id }, v }));
  return (
    <ViewsRow>
      <C08VariantsTable variants={variants} onPick={onPick} current={sel.data.variant.variant_id} />
    </ViewsRow>
  );
}

/** The case, the data it stands on (and why Freddie Mac is or is not there), the training rule and the workout treatment. */
export function C08ContextView({ sel }: { sel: C08Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const m = sel.data.manifest;
  const v = sel.data.variant;
  const d = o.data_status;
  const w = o.workout;
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case', es: 'El caso' }} {...card}>
        <FixtureNotice variant={v} />
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <dl className="ct-defs" data-table="c08-data-status">
          <dt>{pick({ en: 'Default cohort', es: 'Cohorte de incumplimiento' }, lang)}</dt>
          <dd>{pick(o.cohort.label, lang)}</dd>
          <dt>{pick({ en: 'Primary data', es: 'Datos principales' }, lang)}</dt>
          <dd data-primary-source={d.primary_source}>{pick(wordsOf(DATASET_TEXT, d.primary_source), lang)}</dd>
          <dt>Freddie Mac</dt>
          <dd data-freddie-mac={String(d.freddie_mac_available)}>
            {d.freddie_mac_available ? pick({ en: 'available', es: 'disponible' }, lang) : `${pick({ en: 'not available', es: 'no disponible' }, lang)}: ${freddieReason(d.freddie_mac_reason, lang)}`}
          </dd>
          <dt>{pick({ en: 'Notice of the document', es: 'Aviso del documento' }, lang)}</dt>
          <dd>{pick(d.notice, lang)}</dd>
          <dt>{pick({ en: 'Truth status of this variant', es: 'Estado de verdad de esta variante' }, lang)}</dt>
          <dd data-truth-status={v.provenance.truth_status}>{truthText(v.provenance.truth_status, lang)}</dd>
        </dl>
      </PlotCard>
      <PlotCard title={{ en: 'Training and workout', es: 'Entrenamiento y recuperación' }} {...card} note={{ en: 'Only defaults whose workout closed before the cut-off train the models; later default cohorts are the tests.', es: 'Solo los incumplimientos cuya recuperación cerró antes del corte entrenan los modelos; las cohortes de incumplimiento posteriores son las pruebas.' }}>
        <dl className="ct-defs" data-table="c08-training">
          <dt>{pick({ en: 'Cut-off', es: 'Corte' }, lang)}</dt>
          <dd>{o.training.cutoff_date}</dd>
          <dt>{pick({ en: 'Defaults in training', es: 'Incumplimientos en el entrenamiento' }, lang)}</dt>
          <dd>{count(o.training.n_defaults, lang)}</dd>
          <dt>{pick({ en: 'Open workouts left out', es: 'Recuperaciones abiertas excluidas' }, lang)}</dt>
          <dd>{count(o.training.n_open_workouts_excluded, lang)}</dd>
          <dt>{pick({ en: 'Closure rule', es: 'Regla de cierre' }, lang)}</dt>
          <dd>{pick(o.training.closure_rule, lang)}</dd>
          <dt>{pick({ en: 'Discounting', es: 'Descuento' }, lang)}</dt>
          <dd data-convention={w.discount_rate_convention}>{pick(WORKOUT_CONVENTION[w.discount_rate_convention], lang)}</dd>
          <dt>{pick({ en: 'Open workouts', es: 'Recuperaciones abiertas' }, lang)}</dt>
          <dd>{`${pick(INCOMPLETE_TEXT[w.incomplete_workouts.treatment], lang)}${w.incomplete_workouts.reason ? `: ${pick(w.incomplete_workouts.reason, lang)}` : ''}`}</dd>
          <dt>{pick({ en: 'Note', es: 'Nota' }, lang)}</dt>
          <dd>{pick(w.note, lang)}</dd>
        </dl>
      </PlotCard>
    </div>
  );
}

/** The live read-out of the Model section: the model in focus on this cohort. */
export function RungReadout({ sel }: { sel: C08Sel | null }) {
  const o = outputsOf(sel);
  const r = o?.rung_comparison.find((x) => x.rung_id === sel?.rung) ?? null;
  const why: BiText | undefined = r?.reason ? { en: r.reason, es: r.reason } : undefined;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'This model on the cohort', es: 'Este modelo en la cohorte' }}
      items={[
        { label: { en: 'R squared', es: 'R cuadrado' }, value: r?.r2 ?? null, unitless: true, format: { digits: 3 }, hint: why ?? { en: 'Share of the variance of the LGD that the model explains.', es: 'Proporción de la varianza de la LGD que explica el modelo.' } },
        { label: { en: 'RMSE', es: 'RMSE' }, value: r?.rmse ?? null, unitless: true, format: { digits: 3 }, hint: { en: 'Root mean squared error of the predicted LGD; lower is better.', es: 'Raíz del error cuadrático medio de la LGD predicha; menor es mejor.' } },
        { label: { en: 'Spearman', es: 'Spearman' }, value: r?.spearman ?? null, unitless: true, format: { digits: 3 }, hint: why ?? { en: 'Rank correlation between predicted and realised LGD.', es: 'Correlación de rangos entre la LGD predicha y la realizada.' } },
        { label: { en: 'Calibration gap', es: 'Brecha de calibración' }, value: r?.calibration_gap ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'The signed calibration gap the engine reports for this model.', es: 'La brecha de calibración con signo que el motor informa para este modelo.' } },
      ]}
    />
  );
}

/** The live read-out of the Endpoint section: the beta regression at the shift chosen. */
export function EndpointReadout({ sel }: { sel: C08Sel | null }) {
  const o = outputsOf(sel);
  const e = o?.endpoint_sensitivity.find((x) => x.epsilon === sel?.epsilon) ?? null;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'Beta regression at this shift', es: 'Regresión beta con este desplazamiento' }}
      items={[
        { label: { en: 'Mean predicted LGD', es: 'LGD media predicha' }, value: e?.mean_predicted.value ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'The mean LGD the beta regression predicts when the endpoints are moved in by this shift.', es: 'La LGD media que predice la regresión beta cuando los extremos se mueven hacia adentro en este desplazamiento.' } },
        { label: { en: 'RMSE', es: 'RMSE' }, value: e?.rmse ?? null, unitless: true, format: { digits: 3 }, hint: { en: 'Root mean squared error of the beta regression at this shift.', es: 'Raíz del error cuadrático medio de la regresión beta con este desplazamiento.' } },
      ]}
    />
  );
}

/** The live read-out of the Cohort section: realised against predicted LGD of the cohort for the model in focus. */
export function CohortReadout({ sel }: { sel: C08Sel | null }) {
  const o = outputsOf(sel);
  const r = o?.realised_vs_predicted.find((x) => x.rung_id === sel?.rung && x.cohort_id === sel?.cohort) ?? null;
  const none: BiText = { en: 'This document has no row for this model and cohort.', es: 'Este documento no trae fila para este modelo y cohorte.' };
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'Realised against predicted', es: 'Realizada contra predicha' }}
      items={[
        flaggedItem({ en: 'Realised LGD', es: 'LGD realizada' }, r ? { en: 'The mean LGD the defaults of this cohort realised; outside 0 to 1 it keeps its flag.', es: 'La LGD media que realizaron los incumplimientos de esta cohorte; fuera de 0 a 1 conserva su marca.' } : none, r?.realised.value ?? null, r?.realised.flag ?? null),
        flaggedItem({ en: 'Predicted LGD', es: 'LGD predicha' }, { en: 'The mean LGD the model predicted for the same defaults.', es: 'La LGD media que predijo el modelo para los mismos incumplimientos.' }, r?.predicted.value ?? null, r?.predicted.flag ?? null),
        { label: { en: 'Gap', es: 'Brecha' }, value: r?.gap ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'The gap between realised and predicted, as the document states it.', es: 'La brecha entre realizada y predicha, como la declara el documento.' } },
        { label: { en: 'Interval', es: 'Intervalo' }, text: r ? { en: `${p2(r.ci_low, 'en')} to ${p2(r.ci_high, 'en')}`, es: `${p2(r.ci_low, 'es')} a ${p2(r.ci_high, 'es')}` } : { en: formatNumber(null, 'en'), es: formatNumber(null, 'es') }, hint: { en: 'The interval of the realised mean.', es: 'El intervalo de la media realizada.' } },
      ]}
    />
  );
}

/** The live read-out of the Floor section: the floor of the segment chosen and how it bites. */
export function FloorReadout({ sel }: { sel: C08Sel | null }) {
  const o = outputsOf(sel);
  const r = o?.floors_bite.rows.find((x) => x.segment_id === sel?.segment) ?? null;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'The floor of this segment', es: 'El piso de este segmento' }}
      items={[
        { label: { en: 'Floor', es: 'Piso' }, value: r?.floor ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: `The regulatory LGD floor that applies${r ? ` (${r.reference})` : ''}.`, es: `El piso regulatorio de LGD que aplica${r ? ` (${r.reference})` : ''}.` } },
        { label: { en: 'Binds on', es: 'Se activa en' }, value: r?.share_binding ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'Share of the defaults of the segment whose estimate the floor lifts.', es: 'Proporción de los incumplimientos del segmento cuya estimación sube el piso.' } },
        { label: { en: 'Mean before', es: 'Media antes' }, value: r?.mean_before.value ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'The mean predicted LGD before the floor.', es: 'La LGD media predicha antes del piso.' } },
        { label: { en: 'Mean after', es: 'Media después' }, value: r?.mean_after.value ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'The mean predicted LGD after the floor.', es: 'La LGD media predicha después del piso.' } },
      ]}
    />
  );
}
