// C20's notices, Findings, Variants and Context groups and the live read-outs of its rail (ADR-0017 rule 3: every section
// shows a value that moves with its controls). Every view that shows SGCD carries the dataset card's prohibited-use
// sentence (conventions/third-party-datasets.md; 07 A.3 l.212-213): `SgcdNotice` is the one place that writes it.
import { Fragment, type ReactElement } from 'react';
import { PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { loadAllVariants, useArtifact } from '../../api/artifacts';
import type { VariantArtifact } from '../../lib/contract.types';
import { FindingsCard, FixtureNotice } from '../c06/C06Common';
import { UnavailableCard } from '../c14/C14Common';
import { Pending } from '../Pending';
import { LiveReadout, useCard } from '../c03/U6Shared';
import { ParamTable, U14TestsTable, f3, int, type NamedParam } from './U14Common';
import {
  DATASET_TEXT, KIND_TEXT, SCREEN_TEXT, asKind, blockRows, fitOf, kindOf, outputsOf, text,
  type C20Kind, type C20Outputs, type C20Sel,
} from './selection';

type Notice = NonNullable<C20Outputs['sgcd_notice']>;

/** The sentence of the dataset card, in the page's language, with the card's own words quoted. */
export function SgcdNoticeText({ notice }: { notice: Notice | null }) {
  const lang = useShellLang();
  return (
    <p className="ct-note" data-notice="sgcd">
      <strong>{pick({ en: 'SGCD dataset card.', es: 'Ficha del conjunto SGCD.' }, lang)}</strong>{' '}
      {notice ? (
        <>
          {pick(notice.text, lang)}
          {': '}
          <span translate="no" lang="en">{`"${notice.quote}"`}</span>
        </>
      ) : (
        pick({ en: 'The notice is not available in this document.', es: 'El aviso no está disponible en este documento.' }, lang)
      )}
    </p>
  );
}

/** The dataset card's prohibited-use sentence, on every view that shows SGCD; null for a variant that does not. */
export function SgcdNotice({ sel }: { sel: Pick<C20Sel, 'data'> | null }) {
  const o = outputsOf(sel);
  if (!o || o.dataset_id !== 'sgcd') return null;
  return <SgcdNoticeText notice={o.sgcd_notice ?? fitOf(sel)?.sgcd.notice ?? null} />;
}

/** A view of one kind of variant, given the document of another: says so and names the kinds that carry it, and draws nothing. */
export function NotInVariant({ sel, title, needs }: { sel: C20Sel | null; title: BiText; needs: C20Kind }) {
  const open = kindOf(sel);
  const want = KIND_TEXT[needs];
  const have = open ? KIND_TEXT[open] : null;
  return (
    <UnavailableCard
      sel={sel}
      title={title}
      reason={{
        en: `Not available: this view reads the "${want.en}" variant and the open one is "${have?.en ?? 'unknown'}". Pick the "${want.en}" variant in the rail.`,
        es: `No disponible: esta vista lee la variante "${want.es}" y la abierta es "${have?.es ?? 'desconocida'}". Elija la variante "${want.es}" en el riel.`,
      }}
    />
  );
}

export function C20FindingsView({ sel }: { sel: C20Sel | null }) {
  const card = useCard(sel?.data.variant);
  if (!sel) return <Pending />;
  const v = sel.data.variant;
  return (
    <ViewsRow shares={[3, 2]}>
      <FindingsCard variant={v} />
      <PlotCard fill title={{ en: 'The tests of the engine', es: 'Las pruebas del motor' }} {...card}>
        <div className="ct-scroll">
          <FixtureNotice variant={v} />
          <SgcdNotice sel={sel} />
          <U14TestsTable tests={v.tests} />
        </div>
      </PlotCard>
    </ViewsRow>
  );
}

type Entry = { id: string; title: BiText; v: VariantArtifact<C20Outputs> };

/** What each kind of variant answers, in one number: the headline of its row. */
function headline(o: C20Outputs, lang: 'en' | 'es'): { measure: BiText; value: string } {
  switch (o.kind) {
    case 'shock': {
      const rows = o.shipped.rows;
      const worst = rows.length ? Math.min(...rows.map((r) => r.performance.auc_delta)) : null;
      return { measure: { en: 'Largest AUC loss, as shipped', es: 'Mayor pérdida de AUC, como se entrega' }, value: worst === null ? formatNumber(null, lang) : f3(worst, lang) };
    }
    case 'shift': {
      const s = o.synthetic_shift.shifts;
      const worst = s.length ? Math.min(...s.map((x) => x.metric.auc_delta)) : null;
      return { measure: { en: 'Largest AUC loss under a synthetic shift', es: 'Mayor pérdida de AUC bajo un cambio sintético' }, value: worst === null ? formatNumber(null, lang) : f3(worst, lang) };
    }
    case 'seeds': {
      const sd = o.rows.length ? Math.max(...o.rows.map((r) => r.auc.sd)) : null;
      return { measure: { en: 'Largest AUC standard deviation across seeds', es: 'Mayor desviación estándar del AUC entre semillas' }, value: sd === null ? formatNumber(null, lang) : f3(sd, lang) };
    }
    case 'perturbation': {
      const at = o.rows.find((r) => r.eps === o.preset_eps);
      return { measure: { en: 'AUC change at the preset noise scale', es: 'Cambio del AUC en la escala de ruido preestablecida' }, value: at ? f3(at.metric.auc_delta, lang) : formatNumber(null, lang) };
    }
    case 'leakage':
      return { measure: { en: 'Planted leak caught', es: 'Fuga plantada detectada' }, value: pick(o.caught ? { en: 'yes', es: 'sí' } : { en: 'no', es: 'no' }, lang) };
  }
}

/** The six variants of C20 in rows: what each is, on which data, and its headline number. */
export function C20VariantsTable({ variants, onPick, current }: { variants: Entry[]; onPick: (id: string) => void; current: string }) {
  const lang = useShellLang();
  const card = useCard(variants[0]?.v as unknown as VariantArtifact | undefined);
  const sgcd = variants.find((e) => e.v.outputs.dataset_id === 'sgcd');
  return (
    <PlotCard
      fill
      title={{ en: 'The variants of the case', es: 'Las variantes del caso' }}
      {...card}
      note={{ en: 'Each variant answers one question on a locked holdout with synthetic shifts applied to the evaluation set only. Pick one to load it.', es: 'Cada variante responde una pregunta en una muestra reservada, con cambios sintéticos aplicados solo al conjunto de evaluación. Elija una para cargarla.' }}
    >
      <div className="ct-scroll">
        {sgcd ? <SgcdNoticeText notice={sgcd.v.outputs.sgcd_notice} /> : null}
        <table className="caos-table ct-wrap-head" data-table="variants-c20">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Variant', es: 'Variante' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Question', es: 'Pregunta' }, lang)}</th>
              <th className="ct-text ct-wide-only">{pick({ en: 'Data', es: 'Datos' }, lang)}</th>
              <th className="ct-text ct-wide-only">{pick({ en: 'Measure', es: 'Medida' }, lang)}</th>
              <th>{pick({ en: 'Value', es: 'Valor' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {variants.map(({ id, title, v }) => {
              const h = headline(v.outputs, lang);
              return (
                <tr key={id} data-variant={id} data-kind={v.outputs.kind} className={id === current ? 'ct-current' : undefined}>
                  <td className="ct-text">
                    <button type="button" className="ct-linkbutton" onClick={() => onPick(id)}>{pick(title, lang)}</button>
                  </td>
                  <td className="ct-text">{pick(KIND_TEXT[v.outputs.kind], lang)}</td>
                  <td className="ct-text ct-wide-only">{pick(text(DATASET_TEXT, v.outputs.dataset_id), lang)}</td>
                  <td className="ct-text ct-wide-only">{pick(h.measure, lang)}</td>
                  <td>{h.value}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </PlotCard>
  );
}

export function C20VariantsView({ sel, onPick }: { sel: C20Sel | null; onPick: (id: string) => void }) {
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  if (!sel || all.state !== 'ready') return <Pending />;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const variants = (all.data as unknown as Array<VariantArtifact<C20Outputs>>)
    .filter((v) => ['shock', 'shift', 'seeds', 'perturbation', 'leakage'].includes(v.outputs.kind))
    .map((v) => ({ id: v.variant_id, title: entries.find((e) => e.variant_id === v.variant_id)?.short_title ?? { en: v.variant_id, es: v.variant_id }, v }));
  return (
    <ViewsRow>
      <C20VariantsTable variants={variants} onPick={onPick} current={sel.data.variant.variant_id} />
    </ViewsRow>
  );
}

/** The case, the data and the model of the variant, the SGCD notice and the named parameters, each a convention. */
export function C20ContextView({ sel }: { sel: C20Sel | null }): ReactElement {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const m = sel.data.manifest;
  const v = sel.data.variant;
  const fit = fitOf(sel);
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case', es: 'El caso' }} {...card}>
        <FixtureNotice variant={v} />
        <SgcdNotice sel={sel} />
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <dl className="ct-defs" data-table="c20-case">
          <dt>{pick({ en: 'Variant', es: 'Variante' }, lang)}</dt>
          <dd>{pick(KIND_TEXT[o.kind], lang)}</dd>
          <dt>{pick({ en: 'Data', es: 'Datos' }, lang)}</dt>
          <dd data-dataset={o.dataset_id}>{pick(text(DATASET_TEXT, o.dataset_id), lang)}</dd>
          <dt>{pick({ en: 'Model fitted on', es: 'Modelo ajustado con' }, lang)}</dt>
          <dd>{pick(text(DATASET_TEXT, o.model_dataset), lang)}</dd>
          {o.kind === 'shock' ? (
            <Fragment>
              <dt>{pick({ en: 'Shocks', es: 'Choques' }, lang)}</dt>
              <dd data-seen={o.seen_or_held_out}>{pick(o.seen_or_held_out === 'seen' ? { en: 'seen by the model in adaptation', es: 'vistos por el modelo en la adaptación' } : { en: 'held out: the model has not seen them', es: 'reservados: el modelo no los ha visto' }, lang)}</dd>
            </Fragment>
          ) : null}
        </dl>
      </PlotCard>
      {fit ? (
        <PlotCard title={{ en: 'The data and the model', es: 'Los datos y el modelo' }} {...card} note={{ en: 'The model reads one view of each record; a shock that does not reach that view cannot move it.', es: 'El modelo lee una vista de cada registro; un choque que no llega a esa vista no puede moverlo.' }}>
          <div className="ct-scroll">
            <table className="caos-table ct-wrap-head" data-table="c20-datasets">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Data', es: 'Datos' }, lang)}</th>
                  <th>{pick({ en: 'Rows', es: 'Filas' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Role', es: 'Función' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {fit.datasets.map((d) => (
                  <tr key={d.id} data-dataset={d.id}>
                    <td className="ct-text">{pick(text(DATASET_TEXT, d.id), lang)}</td>
                    <td>{int(d.rows, lang)}</td>
                    <td className="ct-text">{d.role}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="ct-note" data-sgcd-commit={fit.sgcd.commit}>{pick({ en: `SGCD at commit ${fit.sgcd.commit.slice(0, 7)}, shock seed ${fit.sgcd.seed}.`, es: `SGCD en el commit ${fit.sgcd.commit.slice(0, 7)}, semilla de los choques ${fit.sgcd.seed}.` }, lang)}</p>
          </div>
        </PlotCard>
      ) : null}
      <PlotCard title={{ en: 'The named parameters', es: 'Los parámetros con nombre' }} {...card} note={{ en: 'Each is a convention of Contraste, never a regulatory threshold.', es: 'Cada uno es una convención de Contraste, nunca un umbral regulatorio.' }}>
        <div className="ct-scroll">
          <ParamTable params={o.parameters as unknown as NamedParam[]} />
        </div>
      </PlotCard>
    </div>
  );
}

// --- the read-outs of the rail ---------------------------------------------------------------------------------------

const hint = (en: string, es: string): BiText => ({ en, es });

/** The live read-out of the Block section: how many records of the block reach the structured view, and the loss they cause. */
export function BlockReadout({ sel }: { sel: C20Sel | null }) {
  const o = asKind(sel, 'shock');
  const rows = o && sel ? blockRows(o, sel.block) : [];
  const total = rows.reduce((a, r) => a + r.n_records, 0);
  const reach = rows.reduce((a, r) => a + r.n_reaching_structured_view, 0);
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel?.block === 'applied' ? { en: 'Contraste-applied shocks', es: 'Choques aplicados por Contraste' } : { en: 'Shocks as shipped', es: 'Choques como se entregan' }}
      items={[
        { label: { en: 'Records', es: 'Registros' }, value: o ? total : null, unitless: true, format: { decimals: 0 }, hint: hint('The records the shock rows of the block cover.', 'Los registros que cubren las filas de choque del bloque.') },
        { label: { en: 'Reach the model', es: 'Llegan al modelo' }, value: o ? reach : null, unitless: true, format: { decimals: 0 }, hint: hint('The records whose structured view the shock changes: the only ones a model that reads the structured view can feel.', 'Los registros cuya vista estructurada cambia el choque: los únicos que puede sentir un modelo que lee la vista estructurada.') },
      ]}
    />
  );
}

export function ShockReadout({ sel }: { sel: C20Sel | null }) {
  const o = asKind(sel, 'shock');
  const r = o && sel ? blockRows(o, sel.block).find((x) => x.shock_id === sel.shock) ?? null : null;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel ? text({ F0: { en: 'F0 faithful', es: 'F0 fieles' }, F1: { en: 'F1 missing', es: 'F1 faltante' }, F2: { en: 'F2 ambiguous', es: 'F2 ambigua' }, F3: { en: 'F3 cosmetic', es: 'F3 cosmético' }, F4: { en: 'F4 contradiction', es: 'F4 contradicción' }, 'numeric-noise': { en: 'Numeric noise', es: 'Ruido numérico' } }, sel.shock) : { en: 'The shock', es: 'El choque' }}
      items={[
        { label: { en: 'AUC', es: 'AUC' }, value: r?.performance.auc ?? null, unitless: true, format: { decimals: 3 }, hint: hint('The AUC on the shocked evaluation records.', 'El AUC en los registros de evaluación con choque.') },
        { label: { en: 'AUC change', es: 'Cambio del AUC' }, value: r?.performance.auc_delta ?? null, unitless: true, format: { decimals: 3 }, hint: hint('Against the clean evaluation set: negative is a loss.', 'Contra el conjunto de evaluación limpio: negativo es una pérdida.') },
        { label: { en: 'PSI, largest', es: 'PSI, mayor' }, value: r?.drift.psi_max ?? null, unitless: true, format: { decimals: 3 }, hint: hint('The largest population stability index over the inputs.', 'El mayor índice de estabilidad poblacional entre las entradas.') },
        { label: { en: 'CSI, largest', es: 'CSI, mayor' }, value: r?.drift.csi_max ?? null, unitless: true, format: { decimals: 3 }, hint: hint('The largest characteristic stability index over the inputs.', 'El mayor índice de estabilidad de características entre las entradas.') },
      ]}
    />
  );
}

export function ShiftReadout({ sel }: { sel: C20Sel | null }) {
  const o = asKind(sel, 'shift');
  const s = o?.synthetic_shift.shifts.find((x) => x.shift_id === sel?.shift) ?? null;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'The synthetic shift', es: 'El cambio sintético' }}
      items={[
        { label: { en: 'AUC', es: 'AUC' }, value: s?.metric.auc ?? null, unitless: true, format: { decimals: 3 }, hint: hint('The AUC on the evaluation set under the shift.', 'El AUC en el conjunto de evaluación bajo el cambio.') },
        { label: { en: 'AUC change', es: 'Cambio del AUC' }, value: s?.metric.auc_delta ?? null, unitless: true, format: { decimals: 3 }, hint: hint('Negative is a loss against the unshifted set.', 'Negativo es una pérdida contra el conjunto sin cambio.') },
        { label: { en: 'PSI', es: 'PSI' }, value: s?.psi ?? null, unitless: true, format: { decimals: 3 }, hint: hint('The stability index of the shifted score.', 'El índice de estabilidad del puntaje con cambio.') },
        { label: { en: 'Decisions that flip', es: 'Decisiones que cambian' }, value: s?.flip_share ?? null, unitless: true, format: { percent: true, decimals: 1 }, hint: hint('At the stated cut-off, held fixed under every shift.', 'En el corte declarado, fijo bajo todo cambio.') },
      ]}
    />
  );
}

export function WindowReadout({ sel }: { sel: C20Sel | null }) {
  const o = asKind(sel, 'shift');
  const w = o?.synthetic_shift.label_free.conformal.coverage_by_window.find((x) => x.window === sel?.window) ?? null;
  const target = o?.synthetic_shift.label_free.conformal.target_coverage ?? null;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'The conformal window', es: 'La ventana conforme' }}
      items={[
        { label: { en: 'Coverage', es: 'Cobertura' }, value: w?.coverage ?? null, unitless: true, format: { percent: true, decimals: 1 }, hint: hint('The share of the window the conformal set covers.', 'La parte de la ventana que cubre el conjunto conforme.') },
        { label: { en: 'Target', es: 'Meta' }, value: target, unitless: true, format: { percent: true, decimals: 1 }, hint: hint('1 minus alpha; a loss of coverage reads as an exchangeability violation.', '1 menos alfa; una pérdida de cobertura se lee como una violación de intercambiabilidad.') },
        { label: { en: 'p (binomial)', es: 'p (binomial)' }, value: w?.binomial_p_value ?? null, unitless: true, format: { digits: 2 }, hint: hint('The binomial test of the coverage against the target.', 'La prueba binomial de la cobertura contra la meta.') },
      ]}
    />
  );
}

export function SeedReadout({ sel }: { sel: C20Sel | null }) {
  const o = asKind(sel, 'seeds');
  const r = o?.rows.find((x) => x.rung === sel?.rung) ?? null;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'Across the seeds', es: 'Entre las semillas' }}
      items={[
        { label: { en: 'AUC, mean', es: 'AUC, media' }, value: r?.auc.mean ?? null, unitless: true, format: { decimals: 3 }, hint: hint('The mean AUC over the retraining seeds.', 'El AUC medio entre las semillas de reentrenamiento.') },
        { label: { en: 'AUC, sd', es: 'AUC, desv.' }, value: r?.auc.sd ?? null, unitless: true, format: { decimals: 4 }, hint: hint('The standard deviation of the AUC across seeds.', 'La desviación estándar del AUC entre semillas.') },
        { label: { en: 'Grades changed', es: 'Grados cambiados' }, value: r?.grade_assignment_changed_share ?? null, unitless: true, format: { percent: true, decimals: 1 }, hint: hint('The share of obligors whose grade changes with the seed.', 'La parte de deudores cuyo grado cambia con la semilla.') },
        { label: { en: 'Reason codes kept', es: 'Códigos de razón que se mantienen' }, value: r?.reason_code_overlap.mean ?? null, unitless: true, format: { percent: true, decimals: 1 }, hint: hint('The mean overlap of the top four reasons across bootstrap refits.', 'El solapamiento medio de las cuatro razones principales entre reajustes bootstrap.') },
      ]}
    />
  );
}

export function NoiseReadout({ sel }: { sel: C20Sel | null }) {
  const o = asKind(sel, 'perturbation');
  const r = o?.rows[sel?.eps ?? 0] ?? null;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'The noise scale', es: 'La escala de ruido' }}
      items={[
        { label: { en: 'Noise', es: 'Ruido' }, value: r?.eps ?? null, unit: { en: 'sd of each input', es: 'desv. de cada entrada' }, format: { digits: 3 }, hint: hint('Gaussian noise proportional to the standard deviation of each input, added to the evaluation set only.', 'Ruido gaussiano proporcional a la desviación estándar de cada entrada, añadido solo al conjunto de evaluación.') },
        { label: { en: 'AUC', es: 'AUC' }, value: r?.metric.auc ?? null, unitless: true, format: { decimals: 3 }, hint: hint('The AUC under the noise.', 'El AUC bajo el ruido.') },
        { label: { en: 'AUC change', es: 'Cambio del AUC' }, value: r?.metric.auc_delta ?? null, unitless: true, format: { decimals: 4 }, hint: hint('Negative is a loss; a finding needs a loss beyond the tolerance at the preset scale.', 'Negativo es una pérdida; un hallazgo necesita una pérdida sobre la tolerancia en la escala preestablecida.') },
      ]}
    />
  );
}

export function ScreenReadout({ sel }: { sel: C20Sel | null }) {
  const o = asKind(sel, 'leakage');
  const sc = o?.screen;
  const items = {
    temporal: { label: { en: 'Violations', es: 'Violaciones' } as BiText, value: sc?.temporal_order.violations ?? null, format: { decimals: 0 }, hint: hint('Features dated after the observation date.', 'Variables con fecha posterior a la de observación.') },
    single: { label: { en: 'Largest AUC', es: 'Mayor AUC' } as BiText, value: sc?.single_feature_auc.max_auc ?? null, format: { decimals: 3 }, hint: hint('The best AUC of any single feature: a near-perfect lone feature is a suspect.', 'El mejor AUC de una sola variable: una variable aislada casi perfecta es sospechosa.') },
    overlap: { label: { en: 'Share', es: 'Parte' } as BiText, value: sc?.entity_overlap.share ?? null, format: { percent: true, decimals: 1 }, hint: hint('The share of test entities that also sit in training.', 'La parte de las entidades de prueba que también está en el entrenamiento.') },
    resemblance: { label: { en: 'AUC', es: 'AUC' } as BiText, value: sc?.resemblance_auc ?? null, format: { decimals: 3 }, hint: hint('A classifier of development against evaluation rows: above its limit the samples differ.', 'Un clasificador de filas de desarrollo contra evaluación: sobre su límite las muestras difieren.') },
  } as const;
  const it = items[sel?.screen ?? 'temporal'];
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={SCREEN_TEXT[sel?.screen ?? 'temporal']}
      items={[
        { label: it.label, value: it.value, unitless: true, format: it.format, hint: it.hint },
        { label: { en: 'Leak caught', es: 'Fuga detectada' }, text: o ? (o.caught ? { en: 'yes', es: 'sí' } : { en: 'no', es: 'no' }) : { en: formatNumber(null, 'en'), es: formatNumber(null, 'es') }, unitless: true, hint: hint('Whether the screen as a whole caught the planted leak.', 'Si el filtro en su conjunto detectó la fuga plantada.') },
      ]}
    />
  );
}

export function FairnessReadout({ sel }: { sel: C20Sel | null }) {
  const o = outputsOf(sel);
  const row = o?.fairness_battery?.rows.find((r) => r.test_id === sel?.test && r.attribute === sel?.attribute) ?? null;
  const na: BiText = { en: formatNumber(null, 'en'), es: formatNumber(null, 'es') };
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'The fairness test', es: 'La prueba de equidad' }}
      items={[
        { label: { en: 'Gap', es: 'Brecha' }, value: row?.value ?? null, unitless: true, format: { decimals: 3 }, hint: hint('The largest difference between groups, on the Taiwan model; labelled evidence, never a compliance statement.', 'La mayor diferencia entre grupos, en el modelo de Taiwán; evidencia etiquetada, nunca una declaración de cumplimiento.') },
        { label: { en: 'Light', es: 'Luz' }, text: row ? ({ green: { en: 'green', es: 'verde' }, amber: { en: 'amber', es: 'ámbar' }, red: { en: 'red', es: 'rojo' }, not_evaluated: { en: 'not evaluated', es: 'sin evaluar' }, error: { en: 'error', es: 'error' } } as Record<string, BiText>)[row.light] ?? na : na, unitless: true, hint: hint('Under the committed policy; a convention.', 'Bajo la política comprometida; una convención.') },
      ]}
    />
  );
}

