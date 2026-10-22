// C09's Validation, Variants and Context groups, and the live read-outs of its rail (ADR-0017 rule 3: every section
// shows a value that moves with its controls). The Findings card and the fixture notice are the ones C06 and C07 use.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { loadAllVariants, useArtifact } from '../../api/artifacts';
import type { VariantArtifact } from '../../lib/contract.types';
import { LIGHT_TEXT } from '../../lib/policy';
import { FindingsCard, FixtureNotice } from '../c06/C06Common';
import { ChartOverTable, compactMoney } from '../c06/format';
import { Pending } from '../Pending';
import { Flagged, LiveReadout, flaggedItem, p2, useCard } from '../c03/U6Shared';
import { truthText } from '../c08/words';
import { SHAPED_ON_TEXT, bandLabel, bandsOf, ccfRow, fitOf, kindText, outputsOf, text, type C09Outputs, type C09Sel } from './selection';

const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });

export function C09FindingsView({ sel }: { sel: C09Sel | null }) {
  if (!sel) return <Pending />;
  return (
    <ViewsRow>
      <FindingsCard variant={sel.data.variant} />
    </ViewsRow>
  );
}

/** The acceleration levels side by side: the bias of the untreated fixed-horizon CCF at each. Pick one to load it. */
export function C09VariantsTable({ variants, onPick, current }: { variants: Array<{ id: string; title: BiText; v: VariantArtifact<C09Outputs> }>; onPick: (id: string) => void; current: string }) {
  const lang = useShellLang();
  const first = variants[0]?.v;
  const card = useCard(first as unknown as VariantArtifact | undefined);
  const untreated = (v: VariantArtifact<C09Outputs>) => v.outputs.ccf_by_design.rows.find((r) => r.design === 'fixed-horizon' && r.treatment === 'none') ?? null;
  return (
    <PlotCard
      fill
      title={{ en: 'The acceleration levels', es: 'Los niveles de aceleración' }}
      {...card}
      note={{
        en: 'A higher level draws utilisation up more steeply before default, so the CCF measured a fixed year before default drifts from the truth. Pick a level to load it.',
        es: 'Un nivel más alto sube la utilización con más fuerza antes del incumplimiento, así que el CCF medido un año fijo antes del incumplimiento se aleja de la verdad. Elija un nivel para cargarlo.',
      }}
    >
      <ChartOverTable
        chart={
          <BarChart
            title={{ en: 'Bias of the untreated fixed-horizon CCF by level', es: 'Sesgo del CCF a horizonte fijo sin tratar por nivel' }}
            height="fill"
            orientation="vertical"
            data={variants.map(({ id, title, v }) => ({ id, label: title, value: untreated(v)?.bias ?? null, tone: 'accent' as const, highlight: id === current }))}
            axis={{ label: { en: 'Estimate minus known CCF', es: 'Estimación menos CCF conocido' }, format: { percent: true, digits: 2 } }}
          />
        }
      >
        <table className="caos-table ct-wrap-head" data-table="variants-c09">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Level', es: 'Nivel' }, lang)}</th>
              <th className="ct-wide-only">{pick({ en: 'Acceleration', es: 'Aceleración' }, lang)}</th>
              <th>{pick({ en: 'Known CCF', es: 'CCF conocido' }, lang)}</th>
              <th>{pick({ en: 'Untreated estimate', es: 'Estimación sin tratar' }, lang)}</th>
              <th>{pick({ en: 'Bias', es: 'Sesgo' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {variants.map(({ id, title, v }) => {
              const r = untreated(v);
              const g = v.outputs.generator;
              return (
                <tr key={id} data-variant={id} data-level={v.outputs.level} className={id === current ? 'ct-current' : undefined}>
                  <td className="ct-text">
                    <button type="button" className="ct-linkbutton" onClick={() => onPick(id)}>{pick(title, lang)}</button>
                  </td>
                  <td className="ct-wide-only">{pick({ en: `x${formatNumber(g.acceleration_factor, 'en', { digits: 3 })} over ${g.acceleration_window_months} months`, es: `x${formatNumber(g.acceleration_factor, 'es', { digits: 3 })} en ${g.acceleration_window_months} meses` }, lang)}</td>
                  <td>
                    <Flagged value={g.true_ccf.value} flag={g.true_ccf.flag} />
                  </td>
                  <td>{r ? <Flagged value={r.estimate.value} flag={r.estimate.flag} /> : formatNumber(null, lang)}</td>
                  <td>{r ? p2(r.bias, lang) : formatNumber(null, lang)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </ChartOverTable>
    </PlotCard>
  );
}

export function C09VariantsView({ sel, onPick }: { sel: C09Sel | null; onPick: (id: string) => void }) {
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  if (!sel || all.state !== 'ready') return <Pending />;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const variants = (all.data as unknown as Array<VariantArtifact<C09Outputs>>)
    .filter((v) => v.outputs.kind === 'acceleration-level')
    .map((v) => ({ id: v.variant_id, title: entries.find((e) => e.variant_id === v.variant_id)?.short_title ?? { en: v.variant_id, es: v.variant_id }, v }));
  return (
    <ViewsRow>
      <C09VariantsTable variants={variants} onPick={onPick} current={sel.data.variant.variant_id} />
    </ViewsRow>
  );
}

/** The case, the convention with its US terms, the generator and its level, the replications and the designs. */
export function C09ContextView({ sel }: { sel: C09Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const m = sel.data.manifest;
  const v = sel.data.variant;
  const fit = fitOf(sel);
  const g = o.generator;
  const r = o.replications;
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case', es: 'El caso' }} {...card}>
        <FixtureNotice variant={v} />
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <dl className="ct-defs" data-table="c09-convention">
          <dt>{pick({ en: 'Level', es: 'Nivel' }, lang)}</dt>
          <dd data-level={o.level}>{pick(o.level_description, lang)}</dd>
          <dt>{pick({ en: 'Convention', es: 'Convención' }, lang)}</dt>
          <dd>{pick(o.convention.definition, lang)}</dd>
          <dt>{pick({ en: 'Formula', es: 'Fórmula' }, lang)}</dt>
          <dd translate="no">{o.convention.formula}</dd>
          <dt>{pick({ en: 'In US terms', es: 'En términos de EE.UU.' }, lang)}</dt>
          <dd>{pick(o.convention.us_terms, lang)}</dd>
          <dt>{pick({ en: 'Truth status of this variant', es: 'Estado de verdad de esta variante' }, lang)}</dt>
          <dd data-truth-status={v.provenance.truth_status}>{truthText(v.provenance.truth_status, lang)}</dd>
        </dl>
      </PlotCard>
      <PlotCard title={{ en: 'The generator and the replications', es: 'El generador y las replicaciones' }} {...card} note={{ en: 'The truth is the CCF the generator draws balances with. Development and test replications use independent seeds.', es: 'La verdad es el CCF con que el generador simula los saldos. Las replicaciones de desarrollo y de prueba usan semillas independientes.' }}>
        <dl className="ct-defs" data-table="c09-generator">
          <dt>{pick({ en: 'Shaped on', es: 'Con la forma de' }, lang)}</dt>
          <dd data-shaped-on={g.shaped_on}>{pick(text(SHAPED_ON_TEXT, g.shaped_on), lang)}</dd>
          <dt>{pick({ en: 'Known CCF', es: 'CCF conocido' }, lang)}</dt>
          <dd>
            <Flagged value={g.true_ccf.value} flag={g.true_ccf.flag} />
          </dd>
          <dt>{pick({ en: 'Acceleration', es: 'Aceleración' }, lang)}</dt>
          <dd>{pick({ en: `x${formatNumber(g.acceleration_factor, 'en', { digits: 3 })} over the last ${g.acceleration_window_months} months`, es: `x${formatNumber(g.acceleration_factor, 'es', { digits: 3 })} en los últimos ${g.acceleration_window_months} meses` }, lang)}</dd>
          <dt>{pick({ en: 'Test replications', es: 'Replicaciones de prueba' }, lang)}</dt>
          <dd data-seeds="test">{`${count(r.test.n_replications, lang)} (${pick({ en: 'seeds', es: 'semillas' }, lang)} ${r.test.seeds.join(', ')}); ${count(r.test.n_facilities, lang)} ${pick({ en: 'facilities', es: 'líneas' }, lang)}, ${count(r.test.n_defaults, lang)} ${pick({ en: 'defaults', es: 'incumplimientos' }, lang)}`}</dd>
          <dt>{pick({ en: 'Development replications', es: 'Replicaciones de desarrollo' }, lang)}</dt>
          <dd data-seeds="development">{`${count(r.development.n_replications, lang)} (${pick({ en: 'seeds', es: 'semillas' }, lang)} ${r.development.seeds.join(', ')}); ${count(r.development.n_facilities, lang)} ${pick({ en: 'facilities', es: 'líneas' }, lang)}, ${count(r.development.n_defaults, lang)} ${pick({ en: 'defaults', es: 'incumplimientos' }, lang)}`}</dd>
          <dt>{pick({ en: 'Notice of the document', es: 'Aviso del documento' }, lang)}</dt>
          <dd>{pick(g.notice, lang)}</dd>
        </dl>
        {fit ? (
          <table className="caos-table ct-wrap-head" data-table="c09-designs">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Reference-date design', es: 'Diseño de fecha de referencia' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {fit.designs.map((d) => (
                <tr key={d.design} data-design={d.design}>
                  <td className="ct-text">{pick(d.label, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="ct-note" data-state="unavailable">{pick({ en: 'Not available: the models artifact carries no designs.', es: 'No disponible: el artefacto de modelos no trae los diseños.' }, lang)}</p>
        )}
      </PlotCard>
    </div>
  );
}

/** The live read-out of the Design section: the estimate of the design and treatment chosen against the known CCF. */
export function DesignReadout({ sel }: { sel: C09Sel | null }) {
  const lang = useShellLang();
  const o = outputsOf(sel);
  const r = o && sel ? ccfRow(o, sel.design, sel.treatment) : null;
  const truth = o?.generator.true_ccf ?? null;
  const none: BiText = { en: 'This document has no estimate for this design and treatment.', es: 'Este documento no trae estimación para este diseño y tratamiento.' };
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'The estimate against the truth', es: 'La estimación contra la verdad' }}
      items={[
        flaggedItem({ en: 'Estimate', es: 'Estimación' }, r ? { en: 'The CCF this design and treatment estimate; outside 0 to 1 it keeps its flag.', es: 'El CCF que estiman este diseño y tratamiento; fuera de 0 a 1 conserva su marca.' } : none, r?.estimate.value ?? null, r?.estimate.flag ?? null),
        flaggedItem({ en: 'Known CCF', es: 'CCF conocido' }, { en: 'The CCF the generator draws balances with.', es: 'El CCF con que el generador simula los saldos.' }, truth?.value ?? null, truth?.flag ?? null),
        { label: { en: 'Bias', es: 'Sesgo' }, value: r?.bias ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'Estimate minus the known CCF.', es: 'Estimación menos el CCF conocido.' } },
        { label: { en: 'Within tolerance', es: 'Dentro de la tolerancia' }, text: r ? (r.within_tolerance ? { en: 'yes', es: 'sí' } : { en: 'no', es: 'no' }) : { en: formatNumber(null, 'en'), es: formatNumber(null, 'es') }, hint: { en: `Whether the estimate recovers the known CCF within ${p2(o?.ccf_by_design.tolerance ?? null, lang)}.`, es: `Si la estimación recupera el CCF conocido dentro de ${p2(o?.ccf_by_design.tolerance ?? null, lang)}.` } },
      ]}
    />
  );
}

/** The live read-out of the Treatment section: how much of the design falls outside 0 to 1. */
export function TreatmentReadout({ sel }: { sel: C09Sel | null }) {
  const o = outputsOf(sel);
  const r = o && sel ? ccfRow(o, sel.design, sel.treatment) : null;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'Defaults outside 0 to 1', es: 'Incumplimientos fuera de 0 a 1' }}
      items={[
        { label: { en: 'Below 0', es: 'Bajo 0' }, value: r?.share_below_zero ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'Share of the defaults whose realised CCF is below 0, before the treatment.', es: 'Proporción de los incumplimientos cuyo CCF realizado es menor que 0, antes del tratamiento.' } },
        { label: { en: 'Above 1', es: 'Sobre 1' }, value: r?.share_above_one ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'Share of the defaults whose realised CCF is above 1, before the treatment.', es: 'Proporción de los incumplimientos cuyo CCF realizado es mayor que 1, antes del tratamiento.' } },
        { label: { en: 'RMSE', es: 'RMSE' }, value: r?.rmse ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'Root mean squared error of the estimate against the known CCF.', es: 'Raíz del error cuadrático medio de la estimación contra el CCF conocido.' } },
        { label: { en: 'Defaults', es: 'Incumplimientos' }, value: r?.n_defaults ?? null, unitless: true, format: { decimals: 0 }, hint: { en: 'The defaults the estimate rests on.', es: 'Los incumplimientos en que se apoya la estimación.' } },
      ]}
    />
  );
}

/** The live read-out of the Model section: what the EAD model chosen is, and what it clipped. */
export function ModelReadout({ sel }: { sel: C09Sel | null }) {
  const o = outputsOf(sel);
  const m = o?.ead_models.find((x) => x.model_id === sel?.model) ?? null;
  const why: BiText = { en: 'Only a direct EAD model clips observations for its fit.', es: 'Solo un modelo directo de EAD recorta observaciones para su ajuste.' };
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={{ en: 'This EAD model', es: 'Este modelo de EAD' }}
      items={[
        { label: { en: 'Kind', es: 'Tipo' }, text: m ? kindText(m.kind) : { en: formatNumber(null, 'en'), es: formatNumber(null, 'es') }, hint: { en: 'What the model estimates: a conversion factor by design, the exposure itself, or the change in utilisation.', es: 'Lo que estima el modelo: un factor de conversión por diseño, la exposición misma, o el cambio de utilización.' } },
        { label: { en: 'Clipped below', es: 'Recortados abajo' }, value: m?.n_clipped_below ?? null, unitless: true, format: { decimals: 0 }, hint: why },
        { label: { en: 'Clipped above', es: 'Recortados arriba' }, value: m?.n_clipped_above ?? null, unitless: true, format: { decimals: 0 }, hint: why },
      ]}
    />
  );
}

/** The live read-out of the Band section: predicted against realised EAD of the model in the band, in currency. */
export function BandReadout({ sel }: { sel: C09Sel | null }) {
  const o = outputsOf(sel);
  const r = o?.ead_backtest.rows.find((x) => x.model_id === sel?.model && x.band_id === sel?.band) ?? null;
  const ccy = o?.ead_backtest.currency ?? '';
  const amount = (v: number | null) => compactMoney(v, ccy);
  const band = o && sel ? bandsOf(o).find((b) => b.id === sel.band) : undefined;
  const light = r ? LIGHT_TEXT[r.light] : null;
  const outside = r?.prediction_flag === 'outside-range';
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={band ? { en: `EAD at ${bandLabel(band).en} utilisation`, es: `EAD con utilización de ${bandLabel(band).es}` } : { en: 'EAD in this band', es: 'EAD en este tramo' }}
      items={[
        { label: { en: 'Predicted', es: 'Predicha' }, ...amount(r?.predicted_ead ?? null), ...(outside ? { unit: { en: `${ccy}, outside range`, es: `${ccy}, fuera de rango` } } : {}), hint: { en: 'The exposure at default the model predicts for the facilities of this band.', es: 'La exposición al incumplimiento que predice el modelo para las líneas de este tramo.' } },
        { label: { en: 'Realised', es: 'Realizada' }, ...amount(r?.realised_ead ?? null), hint: { en: 'The exposure at default the defaults of this band drew.', es: 'La exposición al incumplimiento que usaron los incumplimientos de este tramo.' } },
        { label: { en: 'Relative gap', es: 'Brecha relativa' }, value: r?.relative_gap ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'The gap over the realised exposure.', es: 'La brecha sobre la exposición realizada.' } },
        { label: { en: 'Light', es: 'Luz' }, text: light ?? { en: formatNumber(null, 'en'), es: formatNumber(null, 'es') }, hint: { en: 'The light the engine gives this band.', es: 'La luz que da el motor a este tramo.' } },
      ]}
    />
  );
}
