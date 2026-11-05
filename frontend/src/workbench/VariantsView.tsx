// The Variants group: the case's regimes side by side, one row per variant, the metrics that each regime is built to
// move (discrimination under label noise, calibration under prior shift, stability under covariate drift). Picking a
// row loads that variant in every view.
import { PlotCard, ViewsRow, formatNumber, pick, useShellLang, useWorkbenchState } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { loadAllVariants, useArtifact } from '../api/artifacts';
import type { VariantArtifact } from '../lib/contract.types';
import { LIGHT_TEXT, relight } from '../lib/policy';
import { CHAMPION, REPLAY, provenanceOf, rung, shortName, test, value, type Selection } from './model';
import { Pending } from './Pending';

/** The truth status of a variant, in a word under its name. */
const TRUTH_WORD: Record<string, { en: string; es: string }> = {
  'real-outcomes': { en: 'real data', es: 'datos reales' },
  'synthetic-known-truth': { en: 'perturbed data, known truth', es: 'datos perturbados, verdad conocida' },
  'synthetic-calibrated': { en: 'synthetic data', es: 'datos sintéticos' },
  'published-answer': { en: 'a published answer', es: 'una respuesta publicada' },
};

export function VariantsView({ sel, onPick }: { sel: Selection | null; onPick: (id: string) => void }) {
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  if (!sel || all.state !== 'ready') return <Pending />;
  return <VariantsTable sel={sel} all={all.data} onPick={onPick} />;
}

/** The variants' table and its drawing, on the documents of every variant of the case (loaded by VariantsView). */
export function VariantsTable({ sel, all, onPick }: { sel: Selection; all: VariantArtifact[]; onPick: (id: string) => void }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const rows = all.map((v, i) => {
    const ch = v.model.some((m) => m.id === sel.challenger) ? sel.challenger : v.model.find((m) => m.rung === 'P4' || m.rung === 'P5')?.id ?? CHAMPION;
    const jef = test(v, 'pd.jeffreys', CHAMPION);
    const psi = test(v, 'stability.psi', CHAMPION);
    return {
      id: v.variant_id,
      title: entries[i].title,
      short: entries[i].short_title,
      truth: v.provenance.truth_status,
      dr: v.outputs.defaults / v.outputs.n,
      aucChamp: value(test(v, 'disc.auc', CHAMPION)),
      aucChall: value(test(v, 'disc.auc', ch)),
      challenger: ch,
      jef,
      psi,
    };
  });
  const x = rows.map((_, i) => i + 1);
  return (
    // the table and its drawing side by side, each filling its column (R4 c01 M2, c02 M2: stacked, the table's seven two-line rows
    // left the drawing a plot of one row of dots, its readout and its note cut); below 900 px they stack
    <ViewsRow shares={[2, 1]}>
      <PlotCard fill title={{ en: 'The variants of the case', es: 'Las variantes del caso' }} lane="live" provenance={provenanceOf(sel.data.variant.provenance.truth_status)} dataKey={stateKey}>
        <div className="ct-scroll" data-caos-flow="">
        {/* the headers wrap at a word, so the seven columns stay in the card beside the drawing (R4 c01 M2) */}
        <table className="caos-table ct-wrap-head">
          <thead>
            <tr>
              <th className="ct-wide-only">#</th>
              <th className="caos-col-text">{pick({ en: 'Variant', es: 'Variante' }, lang)}</th>
              <th className="ct-wide-only">{pick({ en: 'Default rate', es: 'Tasa de incumplimiento' }, lang)}</th>
              <th>{pick({ en: 'AUC champion', es: 'AUC campeón' }, lang)}</th>
              <th>{pick({ en: 'AUC challenger', es: 'AUC retador' }, lang)}</th>
              <th>{pick({ en: 'Jeffreys, champion', es: 'Jeffreys, campeón' }, lang)}</th>
              <th className="ct-wide-only">{pick({ en: 'PSI, champion', es: 'PSI, campeón' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.id} className={r.id === sel.data.variant.variant_id ? 'ct-current' : undefined} data-current={r.id === sel.data.variant.variant_id ? 'true' : undefined}>
                <td className="ct-wide-only">{i + 1}</td>
                <td className="caos-col-text" title={pick(r.title, lang)}>
                  <button type="button" className="ct-linkbutton" onClick={() => onPick(r.id)}>
                    {pick(r.short, lang)}
                  </button>
                  {/* the truth of each row: the card's chip is the selected variant's (R3 c02 m17) */}
                  <span className="ct-row-detail" data-truth={r.truth}>{pick(TRUTH_WORD[r.truth] ?? { en: r.truth, es: r.truth }, lang)}</span>
                </td>
                <td className="ct-wide-only">{formatNumber(r.dr, lang, { percent: true, decimals: 1 })}</td>
                <td>{formatNumber(r.aucChamp, lang, { decimals: 4 })}</td>
                <td title={pick(shortName(rung(all[i], r.challenger), r.challenger), lang)}>{formatNumber(r.aucChall, lang, { decimals: 4 })}</td>
                <td>{r.jef ? `${formatNumber(r.jef.p_value, lang, { digits: 2 })} ${pick(LIGHT_TEXT[relight(r.jef, sel.alphas)], lang)}` : '-'}</td>
                <td className="ct-wide-only">{r.psi ? `${formatNumber(value(r.psi), lang, { decimals: 4 })} ${pick(LIGHT_TEXT[relight(r.psi, sel.alphas)], lang)}` : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </PlotCard>
      <PlotCard fill title={{ en: 'AUC across the variants', es: 'AUC a través de las variantes' }} lane={REPLAY} provenance={provenanceOf(sel.data.variant.provenance.truth_status)} dataKey={stateKey} note={{ en: `The x axis is the variant number of the table: ${rows.map((r, i) => `${i + 1} ${r.short.en}`).join(', ')}.`, es: `El eje x es el número de variante de la tabla: ${rows.map((r, i) => `${i + 1} ${r.short.es}`).join(', ')}.` }}>
        <UPlotChart
          height="fill"
          x={{ values: x, label: { en: 'Variant', es: 'Variante' }, format: { decimals: 0 } }}
          y={{ label: { en: 'AUC', es: 'AUC' }, format: { decimals: 3 } }}
          series={[
            { label: { en: 'Champion', es: 'Campeón' }, values: rows.map((r) => r.aucChamp), color: '--color-accent', mode: 'points' },
            { label: { en: 'Challenger', es: 'Retador' }, values: rows.map((r) => r.aucChall), color: '--color-magenta', mode: 'points' },
          ]}
        />
      </PlotCard>
    </ViewsRow>
  );
}
