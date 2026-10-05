// The held-out comparisons: every rung against the champion on each case's holdout, with the interval of its AUC and
// the paired DeLong test, its calibration, and the decision it would make. Every number is read from the committed
// artifacts at load time; none is typed in. The claim each table supports is only what its test shows.
import { Cite, DocPage, DocSection, PlotCard, Verdict, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { useMemo } from 'react';
import { loadAllManifests, loadAllVariants, useArtifact } from '../api/artifacts';
import type { CaseManifest, VariantArtifact } from '../lib/contract.types';
import { COMMITTED, relight } from '../lib/policy';
import { P, useT } from '../content/bi';
import { CHAMPION, extra, test, value } from '../workbench/model';

function Comparison({ v, title }: { v: VariantArtifact; title: string }) {
  const lang = useShellLang();
  const t = useT();
  const rows = v.model
    .filter((m) => m.id !== 'P0-constant')
    .map((m) => {
      const auc = test(v, 'disc.auc', m.id);
      const dl = test(v, 'disc.delong', m.id);
      return {
        m,
        auc: value(auc),
        lo: extra(auc, 'ci95_low'),
        hi: extra(auc, 'ci95_high'),
        dl,
        brier: value(test(v, 'pd.brier', m.id)),
        jef: test(v, 'pd.jeffreys', m.id),
      };
    });
  const champ = rows.find((r) => r.m.id === CHAMPION);
  const better = rows.filter((r) => r.dl && relight(r.dl, COMMITTED) !== 'green' && (extra(r.dl, 'difference') ?? 0) > 0);
  return (
    <PlotCard title={{ en: title, es: title }} lane="replay" provenance={v.provenance.truth_status === 'real-outcomes' ? 'real' : 'synthetic'}>
      <Verdict
        compact
        title={{ en: 'What the paired test supports', es: 'Lo que respalda la prueba pareada' }}
        tone={better.length ? 'accent' : 'neutral'}
        verdict={
          better.length
            ? {
                en: `${better.map((r) => r.m.id).join(', ')} rank significantly better than the scorecard (DeLong, policy 5%) on ${formatNumber(v.outputs.n, 'en')} held-out records; the gain in AUC is ${better.map((r) => formatNumber(extra(r.dl, 'difference'), 'en', { decimals: 3 })).join(', ')}.`,
                es: `${better.map((r) => r.m.id).join(', ')} ordenan significativamente mejor que la scorecard (DeLong, política 5%) en ${formatNumber(v.outputs.n, 'es')} registros reservados; la ganancia en AUC es ${better.map((r) => formatNumber(extra(r.dl, 'difference'), 'es', { decimals: 3 })).join(', ')}.`,
              }
            : { en: 'No rung ranks significantly better than the scorecard here.', es: 'Ningún peldaño ordena significativamente mejor que la scorecard aquí.' }
        }
      />
      <table className="caos-table">
        <thead>
          <tr>
            <th className="caos-col-text">{t('Rung', 'Peldaño')}</th>
            <th>AUC</th>
            <th>{t('95% interval', 'Intervalo 95%')}</th>
            <th>{t('Difference to P1', 'Diferencia con P1')}</th>
            <th>{t('DeLong p', 'p de DeLong')}</th>
            <th>Brier</th>
            <th>{t('Jeffreys p (portfolio)', 'p de Jeffreys (cartera)')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.m.id}>
              <td className="caos-col-text">
                {r.m.rung} {pick(r.m.title, lang)}
              </td>
              <td>{formatNumber(r.auc, lang, { decimals: 4 })}</td>
              <td>{r.lo !== null && r.hi !== null ? `${formatNumber(r.lo, lang, { decimals: 4 })} - ${formatNumber(r.hi, lang, { decimals: 4 })}` : ''}</td>
              <td>{r.m.id === CHAMPION ? '' : formatNumber(r.auc !== null && champ?.auc != null ? r.auc - champ.auc : null, lang, { decimals: 4 })}</td>
              <td>{r.dl ? formatNumber(r.dl.p_value, lang, { digits: 3 }) : ''}</td>
              <td>{formatNumber(r.brier, lang, { decimals: 4 })}</td>
              <td>{formatNumber(r.jef?.p_value ?? null, lang, { digits: 3 })}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </PlotCard>
  );
}

function CaseBenchmark({ manifest }: { manifest: CaseManifest }) {
  const all = useArtifact<VariantArtifact[]>((s) => loadAllVariants(manifest, s), [manifest.case_id]);
  const t = useT();
  const picks = useMemo(() => {
    if (all.state !== 'ready') return null;
    // the variants whose rows are the data as observed: the holdout, the small sample, the twin
    return all.data.filter((v) => v.provenance.truth_status === 'real-outcomes');
  }, [all]);
  if (!picks) return <p className="caos-pending" data-state="loading">{t('Loading the comparisons', 'Cargando las comparaciones')}</p>;
  const titles = Object.fromEntries(manifest.artifacts.map((a) => [a.variant_id, a.title]));
  return (
    <div data-state="ready">
      {picks.map((v) => (
        <Comparison key={v.variant_id} v={v} title={`${manifest.case_id}, ${t(titles[v.variant_id]?.en ?? v.variant_id, titles[v.variant_id]?.es ?? v.variant_id)}`} />
      ))}
    </div>
  );
}

export function Benchmark() {
  const t = useT();
  const all = useArtifact((s) => loadAllManifests(s), []);
  return (
    <DocPage wide title={{ en: 'Benchmark', es: 'Benchmark' }} lede={t('Every rung against the champion on held-out data: discrimination with its interval and the paired test, calibration, and only the claims those tests support.', 'Cada peldaño contra el campeón en datos reservados: discriminación con su intervalo y la prueba pareada, calibración, y solo las afirmaciones que esas pruebas respaldan.')}>
      <DocSection title={{ en: 'How to read the comparisons', es: 'Cómo leer las comparaciones' }} refs={['delong1988', 'lessmann2015']}>
        <P
          en={<>A challenger beats the champion only when the paired DeLong test on the same obligors says so <Cite id="delong1988" />, and only by the difference it measures: the literature reports gains of a few AUC points for tree ensembles on retail data <Cite id="lessmann2015" />, and this page shows whether each case agrees. A significant gain in ranking says nothing of calibration, which the Jeffreys column and the Validation group of the App report separately.</>}
          es={<>Un retador supera al campeón solo cuando la prueba pareada de DeLong sobre los mismos deudores lo dice <Cite id="delong1988" />, y solo por la diferencia que mide: la literatura reporta ganancias de unos pocos puntos de AUC para los ensambles de árboles en datos minoristas <Cite id="lessmann2015" />, y esta página muestra si cada caso coincide. Una ganancia significativa en el orden no dice nada de la calibración, que la columna de Jeffreys y el grupo Validación de la App reportan por separado.</>}
        />
      </DocSection>
      {all.state === 'ready' &&
        all.data.manifests.map((m) => (
          <DocSection key={m.case_id} title={{ en: `${m.case_id}: ${m.title.en}`, es: `${m.case_id}: ${m.title.es}` }} noRefsReason={{ en: 'Read from the committed artifacts.', es: 'Leído desde los artefactos comprometidos.' }}>
            <CaseBenchmark manifest={m} />
          </DocSection>
        ))}
    </DocPage>
  );
}
