// C13's Findings, Variants (the planted deficiencies) and Context groups, and the live read-outs of its rail (ADR-0017
// rule 3: every section shows a value that moves with its controls). Every view of a variant names the deficiency the
// generator planted, its mechanism and the synthetic label: the truth of this case is known, and a reader must see it.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { Fragment } from 'react';
import { loadAllVariants, useArtifact } from '../../api/artifacts';
import type { VariantArtifact } from '../../lib/contract.types';
import { FindingsCard, FixtureNotice } from '../c06/C06Common';
import { ChartOverTable } from '../c06/format';
import { Pending } from '../Pending';
import { LiveReadout, useCard, type Bi } from '../c03/U6Shared';
import { ConventionLine, rowsMin } from '../c11/MarketCommon';
import { DEFICIENCY_TEXT, INTENDED_TEXT, STATISTIC_TEXT, ZONE_TEXT, fitOf, levelLabel, outputsOf, text, type C13Outputs, type C13Sel } from './selection';

const count = (v: number, lang: 'en' | 'es') => formatNumber(v, lang, { decimals: 0 });
const pct = (v: number | null | undefined, lang: 'en' | 'es', decimals = 1) => formatNumber(v, lang, { percent: true, decimals });

/** The deficiency of a document in words: its name, or the control. */
export const deficiencyName = (o: C13Outputs): Bi => text(DEFICIENCY_TEXT, o.known_deficiency.deficiency_id);

/** The known truth of the variant and the synthetic label, at the foot of every view: the deficiency planted, how, and which test should catch it. */
export function KnownBanner({ o }: { o: C13Outputs }) {
  const lang = useShellLang();
  const k = o.known_deficiency;
  return (
    <div data-known-deficiency={k.deficiency_id} data-planted={String(k.planted)}>
      <p className="ct-note">
        <strong>{pick(k.planted ? { en: 'Known deficiency: ', es: 'Deficiencia conocida: ' } : { en: 'No deficiency planted: ', es: 'Sin deficiencia sembrada: ' }, lang)}</strong>
        {k.planted ? `${pick(deficiencyName(o), lang)}. ` : ''}
        {pick(k.mechanism, lang)}
        {k.planted ? ` ${pick({ en: 'Meant to be caught by:', es: 'Debe detectarla:' }, lang)} ${pick(text(INTENDED_TEXT, k.intended_to_fail), lang)}.` : ''}
      </p>
      <p className="ct-note" data-synthetic="true">{pick(o.generator.notice, lang)}</p>
    </div>
  );
}

/** The lines every C13 view carries under its drawing: the sign convention, once, and the known deficiency. */
export function ViewFoot({ o }: { o: C13Outputs }) {
  return (
    <>
      <ConventionLine />
      <KnownBanner o={o} />
    </>
  );
}

export function C13FindingsView({ sel }: { sel: C13Sel | null }) {
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  return (
    <div className="ct-stack" data-block="c13-findings">
      <KnownBanner o={o} />
      <div style={{ flex: '1 1 0', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <ViewsRow>
          <FindingsCard variant={sel.data.variant} />
        </ViewsRow>
      </div>
    </div>
  );
}

/** The planted deficiencies side by side: the share of replications where the PLA caught each, with its interval. Pick one to load it. */
export function C13VariantsTable({ variants, onPick, current }: { variants: Array<{ id: string; title: BiText; v: VariantArtifact<C13Outputs> }>; onPick: (id: string) => void; current: string }) {
  const lang = useShellLang();
  const card = useCard(variants[0]?.v as unknown as VariantArtifact | undefined);
  const first = variants[0]?.v.outputs;
  return (
    <PlotCard
      fill
      title={{ en: 'The planted deficiencies', es: 'Las deficiencias sembradas' }}
      {...card}
      note={{
        en: 'Each variant plants one deficiency in the desk risk model and runs the PLA test on independent replications. The bars are the replications where the PLA zone was amber or red: the power for a planted deficiency, the false-alarm rate for the control. Pick one to load it.',
        es: 'Cada variante siembra una deficiencia en el modelo de riesgo de la mesa y corre la prueba PLA en replicaciones independientes. Las barras son las replicaciones en que la zona PLA fue ámbar o roja: la potencia para una deficiencia sembrada, la tasa de falsas alarmas para el control. Elija una para cargarla.',
      }}
    >
      <ChartOverTable
        chartMin={rowsMin(variants.length)}
        chart={
          <BarChart
            title={{ en: 'Replications where the PLA zone is amber or red', es: 'Replicaciones donde la zona PLA es ámbar o roja' }}
            height="fill"
            orientation="horizontal"
            data={variants.map(({ id, title, v }) => ({ id, label: title, value: v.outputs.detection.n_amber_or_red, tone: v.outputs.known_deficiency.planted ? ('accent' as const) : ('neutral' as const), highlight: id === current }))}
            axis={{ label: { en: 'Replications', es: 'Replicaciones' }, format: { decimals: 0 }, range: [0, Math.max(1, ...variants.map(({ v }) => v.outputs.detection.n_replications))] }}
          />
        }
      >
        <ConventionLine />
        {first ? <p className="ct-note" data-synthetic="true">{pick(first.generator.notice, lang)}</p> : null}
        <table className="caos-table ct-wrap-head" data-table="variants-c13">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Deficiency', es: 'Deficiencia' }, lang)}</th>
              <th className="ct-text ct-wide-only">{pick({ en: 'Meant to be caught by', es: 'La debe detectar' }, lang)}</th>
              <th>{pick({ en: 'Caught', es: 'Detectada' }, lang)}</th>
              <th className="ct-wide-only">{pick({ en: 'Interval', es: 'Intervalo' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Role', es: 'Papel' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {variants.map(({ id, title, v }) => {
              const d = v.outputs.detection;
              return (
                <tr key={id} data-variant={id} data-deficiency={v.outputs.known_deficiency.deficiency_id} className={id === current ? 'ct-current' : undefined}>
                  <td className="ct-text">
                    <button type="button" className="ct-linkbutton" onClick={() => onPick(id)}>{pick(title, lang)}</button>
                  </td>
                  <td className="ct-text ct-wide-only">{pick(text(INTENDED_TEXT, v.outputs.known_deficiency.intended_to_fail), lang)}</td>
                  <td>{pct(d.share_amber_or_red, lang)}</td>
                  <td className="ct-wide-only">{`${pct(d.ci_low, lang)} - ${pct(d.ci_high, lang)}`}</td>
                  <td className="ct-text">{d.role === 'power' ? pick({ en: 'power', es: 'potencia' }, lang) : pick({ en: 'size', es: 'tamaño' }, lang)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </ChartOverTable>
    </PlotCard>
  );
}

export function C13VariantsView({ sel, onPick }: { sel: C13Sel | null; onPick: (id: string) => void }) {
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  if (!sel || all.state !== 'ready') return <Pending />;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const variants = (all.data as unknown as Array<VariantArtifact<C13Outputs>>)
    .filter((v) => v.outputs.kind === 'deficiency')
    .map((v) => ({ id: v.variant_id, title: entries.find((e) => e.variant_id === v.variant_id)?.short_title ?? text(DEFICIENCY_TEXT, v.outputs.known_deficiency.deficiency_id), v }));
  return (
    <ViewsRow>
      <C13VariantsTable variants={variants} onPick={onPick} current={sel.data.variant.variant_id} />
    </ViewsRow>
  );
}

/** The case, the generator and its true model, the MAR32.42 thresholds, the desk limits and the six deficiencies. */
export function C13ContextView({ sel }: { sel: C13Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const m = sel.data.manifest;
  const v = sel.data.variant;
  const fit = fitOf(sel);
  const t = o.pla.thresholds;
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case and its sign convention', es: 'El caso y su convención de signo' }} {...card}>
        <FixtureNotice variant={v} />
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <dl className="ct-defs" data-table="c13-convention">
          <dt>{pick({ en: 'Convention', es: 'Convención' }, lang)}</dt>
          <dd data-convention="definition">{pick(o.sign_convention.definition, lang)}</dd>
          <dt>{pick({ en: 'Truth status of this variant', es: 'Estado de verdad de esta variante' }, lang)}</dt>
          <dd>{v.provenance.truth_status}</dd>
        </dl>
        <KnownBanner o={o} />
      </PlotCard>
      <PlotCard title={{ en: 'The desk P&L generator', es: 'El generador de P&L de la mesa' }} {...card}>
        <dl className="ct-defs" data-table="c13-generator">
          <dt>{pick({ en: 'Generator', es: 'Generador' }, lang)}</dt>
          <dd>{fit?.generator.name ?? o.generator.name}</dd>
          {fit ? (
            <>
              <dt>{pick({ en: 'True risk model', es: 'Modelo de riesgo verdadero' }, lang)}</dt>
              <dd>{pick(fit.generator.true_risk_model, lang)}</dd>
              {fit.generator.parameters.map((p) => (
                <Fragment key={p.name}>
                  <dt>{p.name}</dt>
                  <dd>{`${formatNumber(p.value, lang, { digits: 4 })} ${p.unit}`}</dd>
                </Fragment>
              ))}
            </>
          ) : null}
          <dt>{pick({ en: 'Risk factors', es: 'Factores de riesgo' }, lang)}</dt>
          <dd>{count(o.generator.n_risk_factors, lang)}</dd>
          <dt>{pick({ en: 'Window', es: 'Ventana' }, lang)}</dt>
          <dd>{pick({ en: `${count(o.generator.window_days, 'en')} days, P&L as a decimal of the desk notional`, es: `${count(o.generator.window_days, 'es')} días, P&L como decimal del nocional de la mesa` }, lang)}</dd>
          <dt>{pick({ en: 'Replications', es: 'Replicaciones' }, lang)}</dt>
          <dd>{pick({ en: `${count(o.generator.n_replications, 'en')}, seed ${count(o.generator.seed_base, 'en')} plus the index`, es: `${count(o.generator.n_replications, 'es')}, semilla ${count(o.generator.seed_base, 'es')} más el índice` }, lang)}</dd>
          <dt>{pick({ en: 'Notice of the models document', es: 'Aviso del documento de modelos' }, lang)}</dt>
          <dd>{pick((fit?.generator ?? o.generator).notice, lang)}</dd>
        </dl>
      </PlotCard>
      <PlotCard title={{ en: 'The tests and their thresholds', es: 'Las pruebas y sus umbrales' }} {...card} note={{ en: 'Transcribed from the Basel framework: these are regulatory zone boundaries, applied to the most recent 250 days of the desk.', es: 'Transcritos del marco de Basilea: son límites de zona regulatorios, aplicados a los 250 días más recientes de la mesa.' }}>
        <dl className="ct-defs" data-table="c13-thresholds">
          <dt>{pick({ en: 'Spearman zones', es: 'Zonas de Spearman' }, lang)}</dt>
          <dd>{pick({ en: `green above ${formatNumber(t.spearman_green, 'en', { decimals: 2 })}, red below ${formatNumber(t.spearman_red, 'en', { decimals: 2 })}`, es: `verde sobre ${formatNumber(t.spearman_green, 'es', { decimals: 2 })}, rojo bajo ${formatNumber(t.spearman_red, 'es', { decimals: 2 })}` }, lang)}</dd>
          <dt>{pick({ en: 'Kolmogorov-Smirnov zones', es: 'Zonas de Kolmogorov-Smirnov' }, lang)}</dt>
          <dd>{pick({ en: `green below ${formatNumber(t.ks_green, 'en', { decimals: 2 })}, red above ${formatNumber(t.ks_red, 'en', { decimals: 2 })}`, es: `verde bajo ${formatNumber(t.ks_green, 'es', { decimals: 2 })}, rojo sobre ${formatNumber(t.ks_red, 'es', { decimals: 2 })}` }, lang)}</dd>
          <dt>{pick({ en: 'ECDF step', es: 'Paso de la ECDF' }, lang)}</dt>
          <dd>{formatNumber(t.ecdf_step, lang, { decimals: 3 })}</dd>
          <dt>{pick({ en: 'Reference', es: 'Referencia' }, lang)}</dt>
          <dd>{t.reference}</dd>
          {(fit?.desk_limits ?? []).map((l) => (
            <Fragment key={l.alpha}>
              <dt>{levelLabel(l.alpha, lang)}</dt>
              <dd>{pick({ en: `more than ${count(l.limit_exceptions, 'en')} exceptions in 250 days moves the desk to the standardised approach (${l.reference})`, es: `más de ${count(l.limit_exceptions, 'es')} excepciones en 250 días pasa la mesa al método estandarizado (${l.reference})` }, lang)}</dd>
            </Fragment>
          ))}
        </dl>
      </PlotCard>
      {fit ? (
        <PlotCard title={{ en: 'The six planted deficiencies', es: 'Las seis deficiencias sembradas' }} {...card}>
          <table className="caos-table ct-wrap-head" data-table="c13-deficiencies">
            <thead>
              <tr>
                <th className="ct-text">{pick({ en: 'Deficiency', es: 'Deficiencia' }, lang)}</th>
                <th className="ct-text">{pick({ en: 'How the generator plants it', es: 'Cómo la siembra el generador' }, lang)}</th>
                <th className="ct-text ct-wide-only">{pick({ en: 'Meant to be caught by', es: 'La debe detectar' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {fit.deficiencies.map((d) => (
                <tr key={d.deficiency_id} data-deficiency={d.deficiency_id} className={d.deficiency_id === o.known_deficiency.deficiency_id ? 'ct-current' : undefined}>
                  <td className="ct-text">{pick(text(DEFICIENCY_TEXT, d.deficiency_id), lang)}</td>
                  <td className="ct-text">
                    {pick(d.mechanism, lang)}
                    {d.parameters.length > 0 ? ` (${d.parameters.map((p) => `${p.name} ${formatNumber(p.value, lang, { digits: 3 })} ${p.unit}`).join(', ')})` : ''}
                  </td>
                  <td className="ct-text ct-wide-only">{pick(text(INTENDED_TEXT, d.intended_to_fail), lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </PlotCard>
      ) : null}
    </div>
  );
}

/** The live read-out of the Level section: the desk exceptions against the MAR32.18 limit. */
export function LevelReadout({ sel }: { sel: C13Sel | null }) {
  const o = outputsOf(sel);
  const lvl = o?.desk_backtest.find((l) => l.alpha === sel?.alpha) ?? null;
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel ? { en: levelLabel(sel.alpha, 'en'), es: levelLabel(sel.alpha, 'es') } : { en: 'This level', es: 'Este nivel' }}
      items={[
        { label: { en: 'Limit', es: 'Límite' }, value: lvl?.limit_exceptions ?? null, unitless: true, format: { decimals: 0 }, hint: { en: 'Exceptions in 250 days beyond which the desk moves to the standardised approach (MAR32.18).', es: 'Excepciones en 250 días sobre las cuales la mesa pasa al método estandarizado (MAR32.18).' } },
        { label: { en: 'Median exceptions', es: 'Excepciones medianas' }, value: lvl?.exceptions.q50 ?? null, unitless: true, format: { decimals: 1 }, hint: { en: 'Across the replications of this deficiency.', es: 'Entre las replicaciones de esta deficiencia.' } },
        { label: { en: 'Over the limit', es: 'Sobre el límite' }, value: lvl?.share_over_limit ?? null, unitless: true, format: { percent: true, decimals: 1 }, hint: { en: 'Share of replications with more exceptions than the limit.', es: 'Proporción de replicaciones con más excepciones que el límite.' } },
      ]}
    />
  );
}

/** The live read-out of the Statistic section: the zone counts of the statistic in focus across the replications. */
export function StatisticReadout({ sel }: { sel: C13Sel | null }) {
  const o = outputsOf(sel);
  const z = o ? o.pla.zones[sel?.statistic ?? 'overall'] : null;
  const item = (zone: 'green' | 'amber' | 'red'): BiText => text(ZONE_TEXT, zone);
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel ? STATISTIC_TEXT[sel.statistic] : { en: 'This statistic', es: 'Este estadístico' }}
      items={(['green', 'amber', 'red'] as const).map((zone) => ({
        label: item(zone),
        value: z ? z[zone] : null,
        unitless: true,
        format: { decimals: 0 },
        hint: { en: `Replications whose ${zone} zone this statistic gives, out of ${o ? count(o.pla.zones.n, 'en') : formatNumber(null, 'en')}.`, es: `Replicaciones en que este estadístico da la zona ${text({ green: { en: '', es: 'verde' }, amber: { en: '', es: 'ámbar' }, red: { en: '', es: 'roja' } }, zone).es}, de ${o ? count(o.pla.zones.n, 'es') : formatNumber(null, 'es')}.` },
      }))}
    />
  );
}
