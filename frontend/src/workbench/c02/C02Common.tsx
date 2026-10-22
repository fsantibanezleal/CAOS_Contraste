// C02's Findings, Variants and Context groups and the live read-outs of its rail (ADR-0017 rule 3: every section shows a
// value that moves with its controls). The Findings card and the fixture notice are the ones C06 and C07 use. The files
// carry no date and no firm identifier: the Context says so, and the Variants view says that each horizon is a different
// file, so a fall of the AUC across horizons mixes the horizon with the sample.
import { Fragment } from 'react';
import { PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { loadAllVariants, useArtifact } from '../../api/artifacts';
import type { VariantArtifact } from '../../lib/contract.types';
import { FindingsCard, FixtureNotice } from '../c06/C06Common';
import { ChartOverTable } from '../c06/format';
import { Pending } from '../Pending';
import { shortName } from '../model';
import { LiveReadout, useCard } from '../c03/U6Shared';
import { ParamTable, f3, int, pc, type NamedParam } from '../c20/U14Common';
import { HORIZON_TEXT, challengerFor, fitOf, outputsOf, rungFor, rungName, type C02Outputs, type C02Sel } from './selection';

export function C02FindingsView({ sel }: { sel: C02Sel | null }) {
  if (!sel) return <Pending />;
  return (
    <ViewsRow>
      <FindingsCard variant={sel.data.variant} />
    </ViewsRow>
  );
}

const COLORS = ['--color-accent', '--color-magenta', '--color-warn', '--color-good', '--color-bad', '--color-fg-subtle'] as const;

type Entry = { id: string; title: BiText; v: VariantArtifact<C02Outputs> };

/** The discrimination of every file: one row a horizon file and the pooled one apart, the AUC of the rung in focus across the years. */
export function C02VariantsTable({ variants, onPick, current, rung }: { variants: Entry[]; onPick: (id: string) => void; current: string; rung: string }) {
  const lang = useShellLang();
  const first = variants[0]?.v;
  const card = useCard(first as unknown as VariantArtifact | undefined);
  const files = variants.filter((e) => e.v.outputs.years !== null).sort((a, b) => (a.v.outputs.years as number) - (b.v.outputs.years as number));
  const pooled = variants.filter((e) => e.v.outputs.years === null);
  const ordered = [...files, ...pooled];
  // keyed on the model: the rung code P4 names LightGBM and XGBoost, and a find on the code returns the first of them
  const codes = [...new Set(files.flatMap((e) => e.v.outputs.rungs.map((r) => r.model_id)))];
  const auc = (e: Entry, id: string) => e.v.outputs.rungs.find((r) => r.model_id === id)?.discrimination.auc ?? null;
  const name = (id: string): BiText => {
    const m = first?.model.find((x) => x.id === id);
    const t = shortName(m, id);
    return typeof t === 'string' ? { en: t, es: t } : t;
  };
  const years = files.map((e) => e.v.outputs.years as number);
  return (
    <PlotCard
      fill
      title={{ en: 'Discrimination by horizon', es: 'Discriminación por horizonte' }}
      {...card}
      note={{
        en: 'The AUC of each rung on the holdout of each horizon file. The files are different samples with different bankruptcy rates and an unknown overlap of firms, so a fall of the AUC across horizons mixes the horizon with the sample. Pick a file to load it; the pooled file stacks the five and is not drawn on the horizon axis.',
        es: 'El AUC de cada peldaño en la muestra reservada de cada archivo de horizonte. Los archivos son muestras distintas, con tasas de quiebra distintas y un solapamiento de empresas desconocido, así que una caída del AUC entre horizontes mezcla el horizonte con la muestra. Elija un archivo para cargarlo; el archivo agrupado apila los cinco y no se dibuja en el eje de horizontes.',
      }}
    >
      <ChartOverTable
        chart={
          files.length === 0 ? (
            <p className="caos-pending" data-state="unavailable">{pick({ en: 'Not available: no horizon file in the loaded variants.', es: 'No disponible: ningún archivo de horizonte en las variantes cargadas.' }, lang)}</p>
          ) : (
            <UPlotChart
              height="fill"
              x={{ values: years, label: { en: 'Horizon of the file', es: 'Horizonte del archivo' }, unit: { en: 'years', es: 'años' }, format: { decimals: 0 } }}
              y={{ label: { en: 'AUC on the holdout', es: 'AUC en la muestra reservada' }, format: { decimals: 2 } }}
              series={codes.map((code, i) => ({ label: name(code), values: files.map((e) => auc(e, code)), color: COLORS[i % COLORS.length], dash: i >= COLORS.length ? [6, 3] : undefined, width: code === rung ? 3 : 1.6, mode: 'line' as const }))}
            />
          )
        }
      >
        <table className="caos-table ct-wrap-head" data-table="variants-c02">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'File', es: 'Archivo' }, lang)}</th>
              <th className="ct-wide-only">{pick({ en: 'Firms', es: 'Empresas' }, lang)}</th>
              <th className="ct-wide-only">{pick({ en: 'Bankruptcies', es: 'Quiebras' }, lang)}</th>
              <th>{pick({ en: 'Rate', es: 'Tasa' }, lang)}</th>
              <th>{`AUC ${pick(name(rung), lang)}`}</th>
              <th>{pick({ en: '95% interval', es: 'Intervalo 95%' }, lang)}</th>
              <th className="ct-wide-only">KS</th>
            </tr>
          </thead>
          <tbody>
            {ordered.map((e) => {
              const o = e.v.outputs;
              const r = o.rungs.find((x) => x.model_id === rung) ?? null;
              return (
                <tr key={e.id} data-variant={e.id} data-years={o.years ?? 'pooled'} className={e.id === current ? 'ct-current' : undefined}>
                  <td className="ct-text">
                    <button type="button" className="ct-linkbutton" onClick={() => onPick(e.id)}>{pick(o.years === null ? HORIZON_TEXT(null) : HORIZON_TEXT(o.years), lang)}</button>
                  </td>
                  <td className="ct-wide-only">{int(o.counts.rows, lang)}</td>
                  <td className="ct-wide-only">{int(o.counts.events, lang)}</td>
                  <td>{pc(o.counts.event_rate, lang)}</td>
                  <td data-na={r ? undefined : 'true'}>{r ? f3(r.discrimination.auc, lang) : formatNumber(null, lang)}</td>
                  <td data-na={r ? undefined : 'true'}>{r ? `${f3(r.discrimination.auc_ci.lo, lang)} - ${f3(r.discrimination.auc_ci.hi, lang)}` : formatNumber(null, lang)}</td>
                  <td className="ct-wide-only" data-na={r ? undefined : 'true'}>{r ? f3(r.discrimination.ks, lang) : formatNumber(null, lang)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </ChartOverTable>
    </PlotCard>
  );
}

export function C02VariantsView({ sel, onPick }: { sel: C02Sel | null; onPick: (id: string) => void }) {
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  if (!sel || all.state !== 'ready') return <Pending />;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const variants = (all.data as unknown as Array<VariantArtifact<C02Outputs>>)
    .filter((v) => v.outputs.kind === 'horizon')
    .map((v) => ({ id: v.variant_id, title: entries.find((e) => e.variant_id === v.variant_id)?.short_title ?? { en: v.variant_id, es: v.variant_id }, v }));
  const code = rungFor(sel)?.model_id ?? '';
  return (
    <ViewsRow>
      <C02VariantsTable variants={variants} onPick={onPick} current={sel.data.variant.variant_id} rung={code} />
    </ViewsRow>
  );
}

/** The case, the file and what it can and cannot support: counts, the leakage-safe protocol, the pooled caveat, the five files of the fit and the named parameters. */
export function C02ContextView({ sel }: { sel: C02Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const m = sel.data.manifest;
  const v = sel.data.variant;
  const fit = fitOf(sel);
  const yes = (b: boolean) => pick(b ? { en: 'yes', es: 'sí' } : { en: 'no', es: 'no' }, lang);
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case', es: 'El caso' }} {...card}>
        <FixtureNotice variant={v} />
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <dl className="ct-defs" data-table="c02-counts">
          <dt>{pick({ en: 'File', es: 'Archivo' }, lang)}</dt>
          <dd>{pick(HORIZON_TEXT(o.years), lang)}</dd>
          <dt>{pick({ en: 'Firms and bankruptcies', es: 'Empresas y quiebras' }, lang)}</dt>
          <dd>{`${int(o.counts.rows, lang)} / ${int(o.counts.events, lang)} (${pc(o.counts.event_rate, lang)})`}</dd>
          <dt>{pick({ en: 'Ratios', es: 'Razones' }, lang)}</dt>
          <dd>{int(o.counts.features, lang)}</dd>
          <dt>{pick({ en: 'Event', es: 'Evento' }, lang)}</dt>
          <dd>{pick(o.counts.event_definition, lang)}</dd>
          {o.firm_overlap_caveat ? (
            <Fragment>
              <dt>{pick({ en: 'Pooled file', es: 'Archivo agrupado' }, lang)}</dt>
              <dd data-caveat="firm-overlap">{pick(o.firm_overlap_caveat, lang)}</dd>
            </Fragment>
          ) : null}
        </dl>
      </PlotCard>
      <PlotCard title={{ en: 'The protocol', es: 'El protocolo' }} {...card} note={{ en: 'The files carry no date and no firm identifier, so every reading is a holdout within a file and none is out of time.', es: 'Los archivos no traen fecha ni identificador de empresa, así que toda lectura es una muestra reservada dentro de un archivo y ninguna es fuera del tiempo.' }}>
        <dl className="ct-defs" data-table="c02-split">
          <dt>{pick({ en: 'Split', es: 'Partición' }, lang)}</dt>
          <dd>{`${int(o.split.train_rows, lang)} / ${int(o.split.calibration_rows, lang)} / ${int(o.split.holdout_rows, lang)} (${pick({ en: 'training / calibration / holdout', es: 'entrenamiento / calibración / reservada' }, lang)})`}</dd>
          <dt>{pick({ en: 'Bankruptcies in the holdout', es: 'Quiebras en la muestra reservada' }, lang)}</dt>
          <dd>{int(o.split.holdout_events, lang)}</dd>
          <dt>{pick({ en: 'Binning, imputation and selection fitted on the training slice only', es: 'Binning, imputación y selección ajustados solo en el tramo de entrenamiento' }, lang)}</dt>
          <dd>{yes(o.split.fit_on_training_slice_only)}</dd>
          <dt>{pick({ en: 'Calibration map on a separate slice', es: 'Mapa de calibración en un tramo aparte' }, lang)}</dt>
          <dd>{yes(o.split.calibration_map_on_separate_slice)}</dd>
          <dt>{pick({ en: 'Resampling before calibration', es: 'Remuestreo antes de calibrar' }, lang)}</dt>
          <dd>{yes(o.split.resampling_before_calibration)}</dd>
          <dt>{pick({ en: 'Out-of-time claim', es: 'Afirmación fuera del tiempo' }, lang)}</dt>
          <dd data-out-of-time={o.split.out_of_time_claim}>{yes(o.split.out_of_time_claim)}</dd>
        </dl>
      </PlotCard>
      {fit ? (
        <PlotCard title={{ en: 'The five files and the ladder', es: 'Los cinco archivos y la escalera' }} {...card}>
          <div className="ct-scroll">
            <table className="caos-table ct-wrap-head" data-table="c02-files">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'File', es: 'Archivo' }, lang)}</th>
                  <th>{pick({ en: 'Firms', es: 'Empresas' }, lang)}</th>
                  <th>{pick({ en: 'Bankruptcies', es: 'Quiebras' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {fit.files.map((f) => (
                  <tr key={f.horizon_id} data-file={f.horizon_id}>
                    <td className="ct-text">{pick(HORIZON_TEXT(f.years), lang)}</td>
                    <td>{int(f.rows, lang)}</td>
                    <td>{int(f.events, lang)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <table className="caos-table ct-wrap-head" data-table="c02-ladder">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Rung', es: 'Peldaño' }, lang)}</th>
                  <th className="ct-text">{pick({ en: 'Model', es: 'Modelo' }, lang)}</th>
                  <th className="ct-text ct-wide-only">{pick({ en: 'Engine', es: 'Motor' }, lang)}</th>
                </tr>
              </thead>
              <tbody>
                {fit.ladder.map((l) => (
                  <tr key={`${l.rung}-${l.label.en}`} data-ladder={l.rung}>
                    <td className="ct-text">{l.rung}</td>
                    <td className="ct-text">{pick(l.label, lang)}</td>
                    <td className="ct-text ct-wide-only">{l.engine}</td>
                  </tr>
                ))}
              </tbody>
            </table>
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

/** The live read-out of the Rung section: the discrimination and the overfit gap of the rung in focus. */
export function RungReadout({ sel }: { sel: C02Sel | null }) {
  const r = rungFor(sel);
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel && r ? rungName(sel, r.model_id) : { en: 'The rung', es: 'El peldaño' }}
      items={[
        { label: { en: 'AUC', es: 'AUC' }, value: r?.discrimination.auc ?? null, unitless: true, format: { decimals: 3 }, hint: { en: 'Area under the ROC curve on the holdout of the file.', es: 'Área bajo la curva ROC en la muestra reservada del archivo.' } },
        { label: { en: 'Gini', es: 'Gini' }, value: r?.discrimination.gini ?? null, unitless: true, format: { decimals: 3 }, hint: { en: '2 AUC - 1.', es: '2 AUC - 1.' } },
        { label: { en: 'KS', es: 'KS' }, value: r?.discrimination.ks ?? null, unitless: true, format: { decimals: 3 }, hint: { en: 'The largest gap between the score distributions of the bankrupt and the others.', es: 'La mayor brecha entre las distribuciones del puntaje de las empresas en quiebra y las demás.' } },
        { label: { en: 'Overfit gap', es: 'Brecha de sobreajuste' }, value: r?.overfit.gap ?? null, unitless: true, format: { decimals: 3 }, hint: { en: 'Training AUC minus holdout AUC; the tolerance is a convention.', es: 'AUC de entrenamiento menos AUC reservada; la tolerancia es una convención.' } },
      ]}
    />
  );
}

/** The live read-out of the Challenger section: the AUC difference with the champion and what its interval and p-value say. */
export function ChallengerReadout({ sel }: { sel: C02Sel | null }) {
  const c = challengerFor(sel);
  return (
    <LiveReadout
      variant={sel?.data.variant}
      title={sel && c ? { en: `${rungName(sel, c.challenger).en} against ${rungName(sel, c.champion).en}`, es: `${rungName(sel, c.challenger).es} contra ${rungName(sel, c.champion).es}` } : { en: 'The challenger', es: 'El retador' }}
      items={[
        { label: { en: 'AUC difference', es: 'Diferencia de AUC' }, value: c?.auc_diff ?? null, unitless: true, format: { decimals: 3 }, hint: { en: 'Challenger minus champion, on the same holdout.', es: 'Retador menos campeón, en la misma muestra reservada.' } },
        { label: { en: 'Interval, low', es: 'Intervalo, inferior' }, value: c?.auc_diff_ci.lo ?? null, unitless: true, format: { decimals: 3 }, hint: { en: 'The lower end of the 95% DeLong interval; an interval holding zero is no evidence of a gain.', es: 'El extremo inferior del intervalo DeLong de 95%; un intervalo que contiene el cero no es evidencia de una ganancia.' } },
        { label: { en: 'p (DeLong)', es: 'p (DeLong)' }, value: c?.delong_p_value ?? null, unitless: true, format: { digits: 2 }, hint: { en: 'The DeLong test of equal AUCs.', es: 'La prueba DeLong de AUC iguales.' } },
        { label: { en: 'Grades moved', es: 'Grados movidos' }, value: c?.grade_disagreement_share ?? null, unitless: true, format: { percent: true, decimals: 1 }, hint: { en: 'The share of firms whose grade differs by two notches or more.', es: 'La parte de empresas cuyo grado difiere en dos escalones o más.' } },
      ]}
    />
  );
}

