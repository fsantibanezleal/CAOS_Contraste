// S-4 of the method tiers plan, the L3 PC-Hazard rung beside Cox: calibration at 12, 24 and 36 months per predicted-risk decile
// against the Aalen-Johansen cumulative incidence, the c-index and the integrated Brier score, and the verdict at this reporting
// date. The numbers are read from the model records of the models artifact (`details.decile_calibration`, `details.evaluation`);
// nothing is computed here. A cell the follow-up has not reached is "not available" with its reason, never filled.
import { PlotCard, ViewsRow, formatNumber, pick, useShellLang, useWorkbenchState, type BiText, type ShellColorToken } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { REPLAY, provenanceOf } from '../model';
import { Pending } from '../Pending';
import { MaybeNumber, pct, unionX } from './format';
import { PCT_AXIS, rungName } from './ValidationViews';
import { outputsOf, type C06Sel } from './selection';

interface DecileCell {
  months: number;
  decile: number;
  n: number;
  predicted_cumulative_pd: number;
  observed_kaplan_meier: number | null;
  observed_aalen_johansen: number | null;
  gap_kaplan_meier: number | null;
  gap_aalen_johansen: number | null;
  reason: BiText | null;
}

interface Pair {
  pch: number | null;
  cox: number | null;
}

export interface PchEvaluation {
  comparator: string;
  hypothesis: BiText;
  eligible_accounts: number;
  defaults_followed: number;
  follow_up_months: number;
  c_index: Pair;
  integrated_brier: Pair;
  mean_abs_decile_gap_aalen_johansen: { months: number[]; pch: Array<number | null>; cox: Array<number | null>; pch_mean: number | null; cox_mean: number | null };
  criteria: { lower_integrated_brier: boolean | null; smaller_decile_gap: boolean | null; higher_c_index: boolean | null };
  holds_at_date: boolean | null;
}

interface PchRecord {
  id: string;
  details?: { evaluated?: boolean; decile_calibration?: DecileCell[]; evaluation?: PchEvaluation; training?: { best_epoch: number; epochs_run: number; holdout_loans: number; train_loans: number } };
}

const HORIZON_COLOR: Record<number, ShellColorToken> = { 12: '--color-accent', 24: '--color-warn', 36: '--color-magenta' };

/** The model records of the models artifact that the S-4 evaluation lives in. */
export function pchRecords(sel: Pick<C06Sel, 'data'> | null): { pch: PchRecord | null; cox: PchRecord | null } {
  const models = ((sel?.data.models as unknown as { model?: PchRecord[] } | undefined)?.model ?? []) as PchRecord[];
  return { pch: models.find((m) => m.id === 'L3-pch') ?? null, cox: models.find((m) => m.id === 'L2-cox') ?? null };
}

const VERDICT: Record<'true' | 'false' | 'null', BiText> = {
  true: { en: 'holds at this date', es: 'se cumple en esta fecha' },
  false: { en: 'does not hold at this date', es: 'no se cumple en esta fecha' },
  null: { en: 'cannot be judged at this date', es: 'no se puede juzgar en esta fecha' },
};
const CRITERIA: Array<{ key: keyof PchEvaluation['criteria']; label: BiText }> = [
  { key: 'lower_integrated_brier', label: { en: 'Lower integrated Brier score than Cox', es: 'Puntaje de Brier integrado menor que el de Cox' } },
  { key: 'smaller_decile_gap', label: { en: 'Smaller mean decile gap against Aalen-Johansen', es: 'Brecha media por decil menor frente a Aalen-Johansen' } },
  { key: 'higher_c_index', label: { en: 'Higher c-index (reported, not in the verdict)', es: 'Índice c mayor (se informa, no entra en el veredicto)' } },
];
const yesNo = (v: boolean | null): BiText => (v === null ? { en: 'not observed', es: 'sin observar' } : v ? { en: 'yes', es: 'sí' } : { en: 'no', es: 'no' });

export function PchView({ sel }: { sel: C06Sel | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const o = outputsOf(sel);
  if (!sel || !o) return <Pending />;
  const prov = provenanceOf(sel.data.variant.provenance.truth_status);
  const { pch, cox } = pchRecords(sel);
  const ev = pch?.details?.evaluation;
  const pchRows = pch?.details?.decile_calibration ?? [];
  const coxRows = cox?.details?.decile_calibration ?? [];
  if (!pch || !ev || pchRows.length === 0) {
    return (
      <PlotCard fill title={{ en: 'PC-Hazard against Cox', es: 'PC-Hazard frente a Cox' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
        <p className="ct-note" data-reason="pch">
          {pick(
            { en: 'The PC-Hazard rung was not fitted at this reporting date (too few loans or defaults); the rung table says how many it stood on.', es: 'El peldaño PC-Hazard no se ajustó en esta fecha de reporte (muy pocos préstamos o incumplimientos); la tabla de peldaños dice en cuántos se apoyaba.' },
            lang,
          )}
        </p>
      </PlotCard>
    );
  }
  const horizons = [...new Set(pchRows.map((r) => r.months))].sort((a, b) => a - b);
  const observed = horizons.filter((h) => pchRows.some((r) => r.months === h && r.gap_aalen_johansen !== null));
  const deciles = unionX(pchRows.map((r) => r.decile));
  const gap = (rows: DecileCell[], h: number) => deciles.map((d) => rows.find((r) => r.months === h && r.decile === d)?.gap_aalen_johansen ?? null);
  const series = observed.flatMap((h) => [
    { label: { en: `PC-Hazard, ${h} m`, es: `PC-Hazard, ${h} m` }, values: gap(pchRows, h), color: HORIZON_COLOR[h] ?? ('--color-accent' as ShellColorToken), width: 2.6 },
    { label: { en: `Cox, ${h} m`, es: `Cox, ${h} m` }, values: gap(coxRows, h), color: HORIZON_COLOR[h] ?? ('--color-accent' as ShellColorToken), width: 1.8, dash: [6, 3] },
  ]);
  const names = { pch: pick(rungName(sel, 'L3-pch'), lang), cox: pick(rungName(sel, 'L2-cox'), lang) };
  const verdictKey = String(ev.holds_at_date) as 'true' | 'false' | 'null';
  return (
    <>
      <ViewsRow shares={[1, 1]}>
        <PlotCard
          fill
          title={{ en: 'Calibration gap against Aalen-Johansen, by risk decile', es: 'Brecha de calibración frente a Aalen-Johansen, por decil de riesgo' }}
          lane={REPLAY}
          provenance={prov}
          dataKey={stateKey}
          note={{
            en: 'Predicted minus observed cumulative PD; zero is calibrated. Solid is PC-Hazard, dashed is Cox. The observed side counts a prepayment as a competing exit, so both rungs sit above zero where many loans prepay.',
            es: 'PD acumulada predicha menos observada; cero es calibrado. La línea continua es PC-Hazard y la punteada es Cox. El lado observado cuenta un prepago como salida competidora, así que ambos peldaños quedan sobre cero donde muchos préstamos se prepagan.',
          }}
        >
          {observed.length === 0 ? (
            <p className="ct-note" data-reason="pch-unobserved">
              {pick({ en: 'No horizon of 12, 24 or 36 months is observed yet at this date.', es: 'Ningún horizonte de 12, 24 o 36 meses está observado aún en esta fecha.' }, lang)}
            </p>
          ) : (
            <UPlotChart
              height="fill"
              x={{ values: deciles, label: { en: 'Predicted-risk decile', es: 'Decil de riesgo predicho' }, format: { decimals: 0 } }}
              y={{ label: { en: 'Predicted minus observed', es: 'Predicha menos observada' }, format: PCT_AXIS }}
              series={series}
            />
          )}
        </PlotCard>
        <PlotCard fill title={{ en: 'PC-Hazard beside Cox at this date', es: 'PC-Hazard junto a Cox en esta fecha' }} lane={REPLAY} provenance={prov} dataKey={stateKey}>
          <div className="ct-scroll" data-caos-flow="">
            <table className="caos-table ct-wrap-head" data-table="pch-summary">
              <thead>
                <tr>
                  <th className="ct-text">{pick({ en: 'Measure', es: 'Medida' }, lang)}</th>
                  <th>{names.pch}</th>
                  <th>{names.cox}</th>
                </tr>
              </thead>
              <tbody>
                <tr data-measure="c-index">
                  <td className="ct-text">{pick({ en: 'Concordance index (12-month PD)', es: 'Índice de concordancia (PD a 12 meses)' }, lang)}</td>
                  <td><MaybeNumber value={ev.c_index.pch} reason={null} format={(v) => formatNumber(v, lang, { decimals: 4 })} /></td>
                  <td><MaybeNumber value={ev.c_index.cox} reason={null} format={(v) => formatNumber(v, lang, { decimals: 4 })} /></td>
                </tr>
                <tr data-measure="integrated-brier">
                  <td className="ct-text">{pick({ en: 'Integrated Brier score', es: 'Puntaje de Brier integrado' }, lang)}</td>
                  <td><MaybeNumber value={ev.integrated_brier.pch} reason={null} format={(v) => formatNumber(v, lang, { decimals: 5 })} /></td>
                  <td><MaybeNumber value={ev.integrated_brier.cox} reason={null} format={(v) => formatNumber(v, lang, { decimals: 5 })} /></td>
                </tr>
                {ev.mean_abs_decile_gap_aalen_johansen.months.map((m, i) => (
                  <tr key={m} data-measure={`decile-gap-${m}`}>
                    <td className="ct-text">{pick({ en: `Mean absolute decile gap, ${m} months`, es: `Brecha absoluta media por decil, ${m} meses` }, lang)}</td>
                    <td><MaybeNumber value={ev.mean_abs_decile_gap_aalen_johansen.pch[i]} reason={null} format={(v) => pct(v, lang, 3)} /></td>
                    <td><MaybeNumber value={ev.mean_abs_decile_gap_aalen_johansen.cox[i]} reason={null} format={(v) => pct(v, lang, 3)} /></td>
                  </tr>
                ))}
                <tr data-measure="decile-gap-mean">
                  <td className="ct-text">{pick({ en: 'Mean absolute decile gap, observed horizons', es: 'Brecha absoluta media por decil, horizontes observados' }, lang)}</td>
                  <td><MaybeNumber value={ev.mean_abs_decile_gap_aalen_johansen.pch_mean} reason={null} format={(v) => pct(v, lang, 3)} /></td>
                  <td><MaybeNumber value={ev.mean_abs_decile_gap_aalen_johansen.cox_mean} reason={null} format={(v) => pct(v, lang, 3)} /></td>
                </tr>
              </tbody>
            </table>
            <ul className="ct-note" data-verdict={String(ev.holds_at_date)} style={{ whiteSpace: 'normal' }}>
              {CRITERIA.map((c) => (
                <li key={c.key} data-criterion={c.key}>
                  {pick(c.label, lang)}: {pick(yesNo(ev.criteria[c.key]), lang)}
                </li>
              ))}
              <li>
                {pick({ en: 'Hypothesis', es: 'Hipótesis' }, lang)}: {pick(VERDICT[verdictKey], lang)}.{' '}
                {pick(
                  {
                    en: `Measured on ${formatNumber(ev.eligible_accounts, 'en', { decimals: 0 })} accounts and ${formatNumber(ev.defaults_followed, 'en', { decimals: 0 })} defaults over ${formatNumber(ev.follow_up_months, 'en', { decimals: 1 })} months of follow-up.`,
                    es: `Medida en ${formatNumber(ev.eligible_accounts, 'es', { decimals: 0 })} cuentas y ${formatNumber(ev.defaults_followed, 'es', { decimals: 0 })} incumplimientos en ${formatNumber(ev.follow_up_months, 'es', { decimals: 1 })} meses de seguimiento.`,
                  },
                  lang,
                )}
              </li>
            </ul>
          </div>
        </PlotCard>
      </ViewsRow>
      <ViewsRow>
      <PlotCard
        fill
        title={{ en: 'The deciles of the PC-Hazard rung in numbers', es: 'Los deciles del peldaño PC-Hazard en números' }}
        lane={REPLAY}
        provenance={prov}
        dataKey={stateKey}
        note={ev.hypothesis}
      >
        <div className="ct-scroll" data-caos-flow="">
          <table className="caos-table ct-wrap-head" data-table="pch-deciles">
            <thead>
              <tr>
                <th>{pick({ en: 'Months', es: 'Meses' }, lang)}</th>
                <th>{pick({ en: 'Decile', es: 'Decil' }, lang)}</th>
                <th>{pick({ en: 'Accounts', es: 'Cuentas' }, lang)}</th>
                <th>{pick({ en: 'Predicted', es: 'Predicha' }, lang)}</th>
                <th>{pick({ en: 'Observed, Kaplan-Meier', es: 'Observada, Kaplan-Meier' }, lang)}</th>
                <th>{pick({ en: 'Observed, Aalen-Johansen', es: 'Observada, Aalen-Johansen' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {pchRows.map((r) => (
                <tr key={`${r.months}-${r.decile}`} data-months={r.months} data-decile={r.decile}>
                  <td>{r.months}</td>
                  <td>{r.decile}</td>
                  <td>{formatNumber(r.n, lang, { decimals: 0 })}</td>
                  <td>{pct(r.predicted_cumulative_pd, lang, 3)}</td>
                  <td><MaybeNumber value={r.observed_kaplan_meier} reason={r.reason ? pick(r.reason, lang) : null} format={(v) => pct(v, lang, 3)} /></td>
                  <td><MaybeNumber value={r.observed_aalen_johansen} reason={r.reason ? pick(r.reason, lang) : null} format={(v) => pct(v, lang, 3)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlotCard>
      </ViewsRow>
    </>
  );
}
