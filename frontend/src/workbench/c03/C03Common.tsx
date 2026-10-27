// C03's Findings, Variants and Context groups, and the live read-outs of its rail (ADR-0017 rule 3: every section shows
// a value that moves with its controls). The Findings card and the fixture notice are the ones C06 and C07 use.
import { BarChart, PlotCard, ViewsRow, formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { loadAllVariants, useArtifact } from '../../api/artifacts';
import type { VariantArtifact } from '../../lib/contract.types';
import { FindingsCard, FixtureNotice } from '../c06/C06Common';
import { ChartOverTable, MaybeNumber } from '../c06/format';
import { Pending } from '../Pending';
import { LiveReadout, p2, useCard } from './U6Shared';
import { REPLAY } from '../model';
import { fitOf, fyRange, outputsOf, rungLabel, type C03Outputs, type C03Sel } from './selection';
import { fyText } from './VintageViews';
import { truthText } from '../c08/words';
import { SOURCE_TEXT, reasonText } from './selection';

const CENSORING: Record<string, BiText> = {
  'exempt-right-censored': { en: 'Loans still active (EXEMPT) are right-censored: they leave the target until they resolve.', es: 'Los créditos vigentes (EXEMPT) son censurados por la derecha: salen del objetivo hasta que se resuelvan.' },
  excluded: { en: 'Loans still active are excluded from the target.', es: 'Los créditos vigentes se excluyen del objetivo.' },
};

export function C03FindingsView({ sel }: { sel: C03Sel | null }) {
  if (!sel) return <Pending />;
  return (
    <ViewsRow>
      <FindingsCard variant={sel.data.variant} />
    </ViewsRow>
  );
}

/** The test cohorts side by side: the training window, the crisis in it and the champion rung's numbers. Pick one to load it. */
export function C03VariantsTable({ variants, onPick, current, label }: { variants: Array<{ id: string; title: BiText; v: VariantArtifact<C03Outputs> }>; onPick: (id: string) => void; current: string; label?: (rungId: string) => BiText }) {
  const lang = useShellLang();
  const first = variants[0]?.v;
  const card = useCard(first as unknown as VariantArtifact | undefined);
  // the champion is the rung the calibration and the vintage views are drawn for (outputs.calibration.rung_id); the first row of the comparison is the constant
  const champion = (v: VariantArtifact<C03Outputs>) => v.outputs.rung_comparison.find((r) => r.rung_id === v.outputs.calibration.rung_id) ?? v.outputs.rung_comparison[0];
  const rungName = (id: string): string => pick(label ? label(id) : { en: id, es: id }, lang);
  const yes = pick({ en: 'yes', es: 'sí' }, lang);
  const no = pick({ en: 'no', es: 'no' }, lang);
  return (
    <PlotCard
      fill
      title={{ en: 'The test cohorts', es: 'Las cohortes de prueba' }}
      {...card}
      note={{ en: 'Each cohort is trained only on vintages whose 5-year mark closed before it starts. Pick a cohort to load it.', es: 'Cada cohorte se entrena solo con cosechas cuya marca de 5 años cerró antes de que empiece. Elija una cohorte para cargarla.' }}
    >
      <ChartOverTable
        chart={
          <BarChart
            title={{ en: 'AUC of the champion by test cohort', es: 'AUC del campeón por cohorte de prueba' }}
            height="fill"
            orientation="vertical"
            data={variants.map(({ id, title, v }) => ({ id, label: title, value: champion(v)?.auc ?? null, tone: 'accent' as const, highlight: id === current }))}
            axis={{ label: { en: 'AUC (higher is better)', es: 'AUC (más alto es mejor)' }, format: { digits: 3 } }}
          />
        }
      >
        <table className="caos-table ct-wrap-head" data-table="variants-c03">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Test cohort', es: 'Cohorte de prueba' }, lang)}</th>
              <th>{pick({ en: 'Trained on', es: 'Entrenada con' }, lang)}</th>
              <th className="ct-wide-only">{pick({ en: 'Crisis in training', es: 'Crisis en el entrenamiento' }, lang)}</th>
              <th className="ct-text ct-wide-only">{pick({ en: 'Champion', es: 'Campeón' }, lang)}</th>
              <th>AUC</th>
              <th className="ct-wide-only">{pick({ en: 'Gap at 5 years', es: 'Brecha a 5 años' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {variants.map(({ id, title, v }) => {
              const c = champion(v);
              return (
                <tr key={id} data-variant={id} className={id === current ? 'ct-current' : undefined}>
                  <td className="ct-text">
                    <button type="button" className="ct-linkbutton" onClick={() => onPick(id)}>{pick(title, lang)}</button>
                  </td>
                  <td style={{ whiteSpace: 'nowrap' }}>{fyRange(v.outputs.training.first_fy, v.outputs.training.last_fy)}</td>
                  <td className="ct-wide-only">{v.outputs.training.crisis_included ? yes : no}</td>
                  <td className="ct-text ct-wide-only">{c ? rungName(c.rung_id) : '-'}</td>
                  <td>
                    <MaybeNumber value={c?.auc ?? null} reason={c?.reason ?? null} format={(x) => formatNumber(x, lang, { digits: 3 })} />
                  </td>
                  <td className="ct-wide-only">
                    <MaybeNumber value={c?.calibration_gap_5y ?? null} reason={null} format={(x) => p2(x, lang)} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </ChartOverTable>
    </PlotCard>
  );
}

export function C03VariantsView({ sel, onPick }: { sel: C03Sel | null; onPick: (id: string) => void }) {
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  if (!sel || all.state !== 'ready') return <Pending />;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const variants = (all.data as unknown as Array<VariantArtifact<C03Outputs>>)
    .filter((v) => v.outputs.kind === 'vintage-cohort')
    .map((v) => ({ id: v.variant_id, title: entries.find((e) => e.variant_id === v.variant_id)?.short_title ?? { en: v.variant_id, es: v.variant_id }, v }));
  return (
    <ViewsRow>
      <C03VariantsTable variants={variants} onPick={onPick} current={sel.data.variant.variant_id} label={(id) => rungLabel(sel, id)} />
    </ViewsRow>
  );
}

/** The case, the data it stands on, the target, the vintage definition and the truth status of the variant. */
export function C03ContextView({ sel }: { sel: C03Sel | null }) {
  const lang = useShellLang();
  const card = useCard(sel?.data.variant);
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const m = sel.data.manifest;
  const v = sel.data.variant;
  const fit = fitOf(sel);
  const d = o.data_status;
  return (
    <div className="ct-context" data-case={m.case_id}>
      <PlotCard title={{ en: 'The case', es: 'El caso' }} {...card}>
        <FixtureNotice variant={v} />
        <p>
          <strong>{pick(m.title, lang)}</strong>. {pick(m.question, lang)}
        </p>
        <dl className="ct-defs" data-table="c03-data-status">
          <dt>{pick({ en: 'Test cohort', es: 'Cohorte de prueba' }, lang)}</dt>
          <dd>{`${pick(o.cohort.label, lang)} (${o.cohort.approval_fiscal_years.map((y) => pick(fyText(y), lang)).join(', ')})`}</dd>
          <dt>{pick({ en: 'Data', es: 'Datos' }, lang)}</dt>
          <dd data-primary-source={d.primary_source}>{pick(SOURCE_TEXT[d.primary_source] ?? { en: d.primary_source, es: d.primary_source }, lang)}</dd>
          <dt>{pick({ en: 'Files as of', es: 'Archivos al' }, lang)}</dt>
          <dd>{d.files_as_of}</dd>
          <dt>{pick({ en: 'Notice of the document', es: 'Aviso del documento' }, lang)}</dt>
          <dd>{pick(d.notice, lang)}</dd>
          <dt>{pick({ en: 'Truth status of this variant', es: 'Estado de verdad de esta variante' }, lang)}</dt>
          <dd>{truthText(v.provenance.truth_status, lang)}</dd>
        </dl>
      </PlotCard>
      <PlotCard title={{ en: 'The target and the vintage', es: 'El objetivo y la cosecha' }} {...card} note={{ en: 'A vintage is the loans approved in one SBA fiscal year. The target is read at the 5-year mark and never before.', es: 'Una cosecha son los créditos aprobados en un año fiscal de la SBA. El objetivo se lee en la marca de 5 años y nunca antes.' }}>
        <dl className="ct-defs" data-table="c03-target">
          <dt>{pick({ en: 'Target', es: 'Objetivo' }, lang)}</dt>
          <dd>{pick(o.target.definition, lang)}</dd>
          <dt>{pick({ en: 'Horizon', es: 'Horizonte' }, lang)}</dt>
          <dd data-horizon={o.target.horizon_months}>{pick({ en: `${o.target.horizon_months} months, read at month ${o.target.observed_at_months}`, es: `${o.target.horizon_months} meses, leído en el mes ${o.target.observed_at_months}` }, lang)}</dd>
          <dt>{pick({ en: 'Active loans', es: 'Créditos vigentes' }, lang)}</dt>
          <dd data-censoring={o.target.censoring}>{pick(CENSORING[o.target.censoring] ?? { en: o.target.censoring, es: o.target.censoring }, lang)}</dd>
          <dt>{pick({ en: 'Vintage', es: 'Cosecha' }, lang)}</dt>
          <dd>{fit ? pick(fit.vintage_definition.label, lang) : pick({ en: 'Approval fiscal year', es: 'Año fiscal de aprobación' }, lang)}</dd>
        </dl>
      </PlotCard>
    </div>
  );
}

/** The live read-out of the Vintage section: the five-year mark of the vintage chosen. */
export function VintageReadout({ sel }: { sel: C03Sel | null }) {
  const o = outputsOf(sel);
  const row = o?.vintage_summary.rows.find((r) => r.fiscal_year === sel?.vintage) ?? null;
  const why: BiText | undefined = row?.reason ? { en: row.reason, es: row.reason } : undefined;
  return (
    <LiveReadout
      lane={REPLAY}
      variant={sel?.data.variant}
      title={{ en: 'Five-year mark, this vintage', es: 'Marca de cinco años, esta cosecha' }}
      items={[
        { label: { en: 'Observed PD', es: 'PD observada' }, value: row?.observed_5y_pd ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: why ?? { en: 'The share charged off within 60 months, read at the mark.', es: 'La proporción castigada dentro de 60 meses, leída en la marca.' } },
        { label: { en: 'Predicted PD', es: 'PD predicha' }, value: row?.predicted_5y_pd ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'The model\'s PD at 60 months for this vintage.', es: 'La PD del modelo a 60 meses para esta cosecha.' } },
        { label: { en: 'Gap', es: 'Brecha' }, value: row?.gap ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: why ?? { en: 'Observed minus predicted.', es: 'Observada menos predicha.' } },
        { label: { en: 'Mark falls on', es: 'La marca cae el' }, text: { en: row?.five_year_mark_date ?? '-', es: row?.five_year_mark_date ?? '-' }, hint: { en: 'The date the vintage completes 60 months.', es: 'La fecha en que la cosecha cumple 60 meses.' } },
      ]}
    />
  );
}

/** The live read-out of the Horizon section: the PD of the vintage at the month chosen, predicted and observed. */
export function HorizonReadout({ sel }: { sel: C03Sel | null }) {
  const o = outputsOf(sel);
  const curve = o?.vintage_curves.find((c) => c.fiscal_year === sel?.vintage) ?? null;
  const i = curve && sel ? curve.months.indexOf(sel.horizon) : -1;
  const m = sel?.horizon ?? 0;
  const why: BiText | undefined = curve?.reason ? { en: curve.reason, es: curve.reason } : undefined;
  return (
    <LiveReadout
      lane={REPLAY}
      variant={sel?.data.variant}
      title={{ en: 'Cumulative PD at this month', es: 'PD acumulada en este mes' }}
      items={[
        { label: { en: `Predicted, ${m} m`, es: `Predicha, ${m} m` }, value: curve && i >= 0 ? curve.predicted_cumulative_pd[i] : null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'The cumulative PD the model predicts for the vintage chosen, at this month since approval.', es: 'La PD acumulada que el modelo predice para la cosecha elegida, en este mes desde la aprobación.' } },
        { label: { en: `Observed, ${m} m`, es: `Observada, ${m} m` }, value: curve && i >= 0 ? curve.observed_cumulative_pd[i] : null, unitless: true, format: { percent: true, decimals: 2 }, hint: why ?? { en: 'The cumulative share charged off by this month.', es: 'La proporción acumulada castigada hasta este mes.' } },
      ]}
    />
  );
}

/** The live read-out of the Model section: the rung chosen on this test cohort. */
export function ModelReadout({ sel }: { sel: C03Sel | null }) {
  const o = outputsOf(sel);
  const r = o?.rung_comparison.find((x) => x.rung_id === sel?.rung) ?? null;
  const why: BiText | undefined = r?.reason ? reasonText(r.reason) : undefined;
  const label = sel ? rungLabel(sel, sel.rung) : { en: '', es: '' };
  return (
    <LiveReadout
      lane={REPLAY}
      variant={sel?.data.variant}
      title={{ en: 'This model on the cohort', es: 'Este modelo en la cohorte' }}
      items={[
        { label: { en: 'AUC', es: 'AUC' }, value: r?.auc ?? null, unitless: true, format: { digits: 3 }, hint: why ?? { en: `Discrimination of ${label.en} on the vintages that reached their mark.`, es: `Discriminación de ${label.es} en las cosechas que alcanzaron su marca.` } },
        { label: { en: 'Brier', es: 'Brier' }, value: r?.brier ?? null, unitless: true, format: { digits: 3 }, hint: { en: 'Mean squared error of the predicted PD; lower is better.', es: 'Error cuadrático medio de la PD predicha; menor es mejor.' } },
        { label: { en: 'Gap at 5 years', es: 'Brecha a 5 años' }, value: r?.calibration_gap_5y ?? null, unitless: true, format: { percent: true, decimals: 2 }, hint: { en: 'The calibration gap at the 5-year mark that the engine reports for this model.', es: 'La brecha de calibración en la marca de 5 años que el motor informa para este modelo.' } },
      ]}
    />
  );
}
