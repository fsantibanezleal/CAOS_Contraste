// The Variants group: the case's regimes side by side, one row per variant, the metrics that each regime is built to
// move (discrimination under label noise, calibration under prior shift, stability under covariate drift). Picking a
// row loads that variant in every view.
import { PlotCard, formatNumber, pick, useShellLang, useWorkbenchState } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { loadAllVariants, useArtifact } from '../api/artifacts';
import type { VariantArtifact } from '../lib/contract.types';
import { LIGHT_TEXT, relight } from '../lib/policy';
import { CHAMPION, REPLAY, provenanceOf, rung, shortName, test, value, type Selection } from './model';
import { Pending } from './Pending';

export function VariantsView({ sel, onPick }: { sel: Selection | null; onPick: (id: string) => void }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const manifest = sel?.data.manifest;
  const all = useArtifact<VariantArtifact[]>((s) => (manifest ? loadAllVariants(manifest, s) : new Promise(() => undefined)), [manifest?.case_id]);
  if (!sel || all.state !== 'ready') return <Pending />;
  const entries = sel.data.manifest.artifacts.filter((a) => a.role === 'variant');
  const rows = all.data.map((v, i) => {
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
    <>
      <PlotCard title={{ en: 'The variants of the case', es: 'Las variantes del caso' }} lane="live" provenance={provenanceOf(sel.data.variant.provenance.truth_status)} dataKey={stateKey}>
        <table className="caos-table">
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
                </td>
                <td className="ct-wide-only">{formatNumber(r.dr, lang, { percent: true, decimals: 1 })}</td>
                <td>{formatNumber(r.aucChamp, lang, { decimals: 4 })}</td>
                <td title={pick(shortName(rung(all.data[i], r.challenger), r.challenger), lang)}>{formatNumber(r.aucChall, lang, { decimals: 4 })}</td>
                <td>{r.jef ? `${formatNumber(r.jef.p_value, lang, { digits: 2 })} ${pick(LIGHT_TEXT[relight(r.jef, sel.alphas)], lang)}` : '-'}</td>
                <td className="ct-wide-only">{r.psi ? `${formatNumber(value(r.psi), lang, { decimals: 4 })} ${pick(LIGHT_TEXT[relight(r.psi, sel.alphas)], lang)}` : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </PlotCard>
      <PlotCard fill title={{ en: 'AUC across the variants', es: 'AUC a través de las variantes' }} lane={REPLAY} provenance={provenanceOf(sel.data.variant.provenance.truth_status)} dataKey={stateKey} note={{ en: `The x axis is the variant number in the table above: ${rows.map((r, i) => `${i + 1} ${r.short.en}`).join(', ')}.`, es: `El eje x es el número de variante de la tabla de arriba: ${rows.map((r, i) => `${i + 1} ${r.short.es}`).join(', ')}.` }}>
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
    </>
  );
}
