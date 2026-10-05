// C05's sections of the cross-case pages: Experiments (every variant, read from its artifact) and Benchmark (the
// calibration approaches compared by the paper's own test on 2010 and 2011, and the low-default estimators compared on
// known truth). Every number is read from the committed artifacts at load time.
import { PlotCard, Verdict, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { loadAllVariants, useArtifact } from '../api/artifacts';
import type { CaseManifest, VariantArtifact } from '../lib/contract.types';
import { COMMITTED, LIGHT_TEXT, relight } from '../lib/policy';
import { useT } from '../content/bi';
import { CASE1, isLdp, isSp, type LdpVariant, type SpVariant } from '../workbench/c05/selection';

const pct = (lang: 'en' | 'es', v: number | null | undefined, decimals = 2) => formatNumber(v, lang, { percent: true, decimals });

function useVariants(manifest: CaseManifest) {
  return useArtifact<VariantArtifact[]>((s) => loadAllVariants(manifest, s), [manifest.case_id]);
}

export function C05ExperimentsSection({ manifest }: { manifest: CaseManifest }) {
  const lang = useShellLang();
  const t = useT();
  const all = useVariants(manifest);
  if (all.state !== 'ready') return <p className="caos-pending" data-state="loading">{t('Loading the variants', 'Cargando las variantes')}</p>;
  const entries = Object.fromEntries(manifest.artifacts.map((a) => [a.variant_id, a]));
  const vs = all.data as VariantArtifact<unknown>[];
  return (
    <table className="caos-table" data-state="ready">
      <thead>
        <tr>
          <th className="caos-col-text">{t('Variant', 'Variante')}</th>
          <th>{t('Truth', 'Verdad')}</th>
          <th className="caos-col-text">{t('Observed', 'Observado')}</th>
          <th className="caos-col-text">{t('What the variant shows', 'Lo que muestra la variante')}</th>
        </tr>
      </thead>
      <tbody>
        {vs.map((v) => {
          let observed = '';
          let shows = '';
          if (isSp(v)) {
            const best = CASE1.map((id) => ({ id, p: v.tests.find((x) => x.test_id === 'pd.default_profile' && x.model_id === id)?.p_value ?? 0 })).sort((a, b) => b.p - a.p)[0];
            const name = v.model.find((m) => m.id === best.id)?.short_title ?? { en: best.id, es: best.id };
            observed = `PD ${pct(lang, v.outputs.pd1)}, AR ${pct(lang, v.outputs.ar1, 1)}`;
            shows = `${pick({ en: 'best default-profile fit: ', es: 'mejor ajuste del perfil: ' }, lang)}${pick(name, lang)} (p ${formatNumber(best.p, lang, { digits: 2 })}); ${pick({ en: 'least squares forecasts ', es: 'mínimos cuadrados pronostica ' }, lang)}${pct(lang, v.outputs.approaches['C2-ls'].pd)}`;
          } else if (isLdp(v)) {
            const k = v.outputs.gammas.indexOf(0.75);
            const vas = v.tests.find((x) => x.test_id === 'pd.binomial_vasicek');
            observed = `${pick({ en: 'defaults ', es: 'incumplimientos ' }, lang)}${v.outputs.defaults.join(', ')}`;
            shows = `${pick({ en: 'bounds at 75%: ', es: 'cotas al 75%: ' }, lang)}${v.outputs.bounds.independent[k].map((b) => pct(lang, b, 3)).join(', ')}; Vasicek ${vas ? pick(LIGHT_TEXT[relight(vas, COMMITTED)], lang) : '-'}`;
          }
          return (
            <tr key={v.variant_id}>
              <td className="caos-col-text">{pick(entries[v.variant_id].title, lang)}</td>
              <td>{v.provenance.truth_status}</td>
              <td className="caos-col-text">{observed}</td>
              <td className="caos-col-text">{shows}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export function C05BenchmarkSection({ manifest }: { manifest: CaseManifest }) {
  const lang = useShellLang();
  const t = useT();
  const all = useVariants(manifest);
  if (all.state !== 'ready') return <p className="caos-pending" data-state="loading">{t('Loading the comparisons', 'Cargando las comparaciones')}</p>;
  const vs = all.data as VariantArtifact<unknown>[];
  const sp = vs.filter(isSp) as SpVariant[];
  const sim = (vs.filter(isLdp) as LdpVariant[]).find((v) => v.outputs.known_truth);
  const kt = sim?.outputs.known_truth;
  const p = (v: SpVariant, id: string) => v.tests.find((x) => x.test_id === 'pd.default_profile' && x.model_id === id);
  return (
    <div data-state="ready">
      <PlotCard title={{ en: 'C05, the case 1 approaches by the paper\'s own test', es: 'C05, los enfoques del caso 1 según la prueba del propio artículo' }} lane="replay" provenance="published">
        <Verdict
          compact
          title={{ en: 'What the test supports', es: 'Lo que respalda la prueba' }}
          tone="accent"
          verdict={{
            en: 'In 2010 the scaled likelihood ratio and the invariant accuracy ratio fit the default profile, scaled PDs and the invariant default profile do not at 5%; in 2011 all four fit. One forecast year each: anecdotal evidence, as the paper says of its own example.',
            es: 'En 2010 la razón de verosimilitud escalada y la razón de precisión invariante ajustan el perfil de incumplimiento, las PD escaladas y el perfil invariante no al 5%; en 2011 los cuatro ajustan. Un año pronosticado cada uno: evidencia anecdótica, como dice el artículo de su propio ejemplo.',
          }}
        />
        <table className="caos-table">
          <thead>
            <tr>
              <th className="caos-col-text">{t('Approach', 'Enfoque')}</th>
              {sp.map((v) => (
                <th key={v.variant_id}>{`p ${v.outputs.year}`}</th>
              ))}
              {sp.map((v) => (
                <th key={`rw-${v.variant_id}`}>{`${t('Risk weight', 'Ponderador')} ${v.outputs.year}`}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {CASE1.map((id) => (
              <tr key={id}>
                <td className="caos-col-text">{sp[0] ? pick(sp[0].model.find((m) => m.id === id)?.title ?? { en: id, es: id }, lang) : id}</td>
                {sp.map((v) => {
                  const r = p(v, id);
                  const l = r ? relight(r, COMMITTED) : 'not_evaluated';
                  return (
                    <td key={v.variant_id} className={`ct-light ct-light-${l}`}>
                      {formatNumber(r?.p_value, lang, { digits: 2 })}
                    </td>
                  );
                })}
                {sp.map((v) => (
                  <td key={`rw-${v.variant_id}`}>{pct(lang, v.impact[`rw_${id}`]?.value, 1)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </PlotCard>
      {kt && (
        <PlotCard title={{ en: 'C05, the low-default estimators on known truth', es: 'C05, los estimadores de bajo incumplimiento con verdad conocida' }} lane="replay" provenance="synthetic">
          <Verdict
            compact
            title={{ en: 'What the generator supports', es: 'Lo que respalda el generador' }}
            tone="accent"
            verdict={{
              en: `Over ${formatNumber(kt.years, 'en')} generated years the bounds cover the truth from 75% up, at a cost in conservatism; the tests that ignore the correlation reject true PDs too often, and the one that keeps its size seldom sees a model at half the truth.`,
              es: `En ${formatNumber(kt.years, 'es')} años generados las cotas cubren la verdad desde el 75%, a costa de conservadurismo; las pruebas que ignoran la correlación rechazan PD verdaderas demasiado seguido, y la que mantiene su tamaño rara vez ve un modelo a la mitad de la verdad.`,
            }}
          />
          <table className="caos-table">
            <thead>
              <tr>
                <th className="caos-col-text">{t('Estimator, grade C', 'Estimador, grado C')}</th>
                <th>{t('Coverage at 50%', 'Cobertura al 50%')}</th>
                <th>{t('Coverage at 75%', 'Cobertura al 75%')}</th>
                <th>{t('Median / truth at 75%', 'Mediana / verdad al 75%')}</th>
              </tr>
            </thead>
            <tbody>
              {(['independent', 'correlated', 'scaled', 'scaled_correlated'] as const).map((m) => {
                const rows = kt.coverage[m].C;
                const at = (g: number) => rows.find((r) => r.gamma === g);
                return (
                  <tr key={m}>
                    <td className="caos-col-text">{m.replace('_', ', ')}</td>
                    <td>{pct(lang, at(0.5)?.coverage, 1)}</td>
                    <td>{pct(lang, at(0.75)?.coverage, 1)}</td>
                    <td>{formatNumber(at(0.75)?.ratio_median, lang, { decimals: 2 })}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <table className="caos-table">
            <thead>
              <tr>
                <th className="caos-col-text">{t('Test at 5%', 'Prueba al 5%')}</th>
                <th>{t('Size (true PDs)', 'Tamaño (PD verdaderas)')}</th>
                <th>{t('Power (expert PDs)', 'Potencia (PD expertas)')}</th>
              </tr>
            </thead>
            <tbody>
              {Object.keys(kt.tests.true).map((k) => (
                <tr key={k}>
                  <td className="caos-col-text">{k.replace('_', ', ')}</td>
                  <td>{pct(lang, kt.tests.true[k].reject_5, 1)}</td>
                  <td>{pct(lang, kt.tests.expert[k].reject_5, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </PlotCard>
      )}
    </div>
  );
}
