// The coverage of the 22 cases and, case by case, every variant read from its committed artifacts. No number on this
// page is typed in: whether a case is built comes from the index, every metric from the variant artifacts (T13).
import { DocPage, DocSection, PlotCard, formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useMemo } from 'react';
import { loadAllManifests, loadAllVariants, useArtifact } from '../api/artifacts';
import type { CaseManifest, VariantArtifact } from '../lib/contract.types';
import { COMMITTED, LIGHT_TEXT, relight } from '../lib/policy';
import { CASES, CATEGORY_TITLES } from '../content/coverage';
import { P, useT } from '../content/bi';
import { CHAMPION, test, value } from '../workbench/model';

function CaseVariants({ manifest }: { manifest: CaseManifest }) {
  const lang = useShellLang();
  const t = useT();
  const all = useArtifact<VariantArtifact[]>((s) => loadAllVariants(manifest, s), [manifest.case_id]);
  const rows = useMemo(() => {
    if (all.state !== 'ready') return null;
    return all.data.map((v) => {
      const ids = v.model.map((m) => m.id);
      const best = ids
        .filter((id) => id !== 'P0-constant')
        .map((id) => ({ id, auc: value(test(v, 'disc.auc', id)) ?? 0 }))
        .sort((a, b) => b.auc - a.auc)[0];
      const jef = test(v, 'pd.jeffreys', CHAMPION);
      const psi = test(v, 'stability.psi', CHAMPION);
      return { v, best, jef, psi, auc: value(test(v, 'disc.auc', CHAMPION)) };
    });
  }, [all]);
  if (!rows) return <p className="caos-pending" data-state="loading">{t('Loading the variants', 'Cargando las variantes')}</p>;
  const entries = manifest.artifacts.filter((a) => a.role === 'variant');
  const x = rows.map((_, i) => i + 1);
  return (
    <>
      <table className="caos-table" data-state="ready">
        <thead>
          <tr>
            <th>#</th>
            <th className="caos-col-text">{t('Variant', 'Variante')}</th>
            <th>{t('Records', 'Registros')}</th>
            <th>{t('Default rate', 'Tasa de incumplimiento')}</th>
            <th>{t('AUC, scorecard', 'AUC, scorecard')}</th>
            <th>{t('Best rung by AUC', 'Mejor peldaño por AUC')}</th>
            <th>{t('Jeffreys, scorecard', 'Jeffreys, scorecard')}</th>
            <th>{t('PSI, scorecard', 'PSI, scorecard')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.v.variant_id}>
              <td>{i + 1}</td>
              <td className="caos-col-text">{pick(entries[i].title, lang)}</td>
              <td>{formatNumber(r.v.outputs.n, lang)}</td>
              <td>{formatNumber(r.v.outputs.defaults / r.v.outputs.n, lang, { percent: true, decimals: 1 })}</td>
              <td>{formatNumber(r.auc, lang, { decimals: 4 })}</td>
              <td>
                {r.best.id} ({formatNumber(r.best.auc, lang, { decimals: 4 })})
              </td>
              <td>{r.jef ? `p ${formatNumber(r.jef.p_value, lang, { digits: 3 })}, ${pick(LIGHT_TEXT[relight(r.jef, COMMITTED)], lang)}` : '-'}</td>
              <td>{r.psi ? `${formatNumber(value(r.psi), lang, { decimals: 4 })}, ${pick(LIGHT_TEXT[relight(r.psi, COMMITTED)], lang)}` : '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <PlotCard title={{ en: 'Discrimination of the scorecard and of the best rung, variant by variant', es: 'Discriminación de la scorecard y del mejor peldaño, variante por variante' }} lane="replay" provenance="real">
        <UPlotChart
          height={260}
          x={{ values: x, label: { en: 'Variant (the number in the table)', es: 'Variante (el número de la tabla)' }, format: { decimals: 0 } }}
          y={{ label: { en: 'AUC', es: 'AUC' }, format: { decimals: 3 } }}
          series={[
            { label: { en: 'Scorecard (P1)', es: 'Scorecard (P1)' }, values: rows.map((r) => r.auc), color: '--color-accent', mode: 'points' },
            { label: { en: 'Best rung', es: 'Mejor peldaño' }, values: rows.map((r) => r.best.auc), color: '--color-magenta', mode: 'points' },
          ]}
        />
      </PlotCard>
    </>
  );
}

export function Experiments() {
  const lang = useShellLang();
  const t = useT();
  const all = useArtifact((s) => loadAllManifests(s), []);
  const built = all.state === 'ready' ? new Set(all.data.index.cases.map((c) => c.case_id)) : null;
  return (
    <DocPage wide title={{ en: 'Experiments', es: 'Experimentos' }} lede={t('The coverage of the 22 cases, and every built case variant by variant, read from the committed artifacts.', 'La cobertura de los 22 casos, y cada caso construido variante por variante, leído desde los artefactos comprometidos.')}>
      <DocSection title={{ en: 'Coverage', es: 'Cobertura' }} noRefsReason={{ en: 'The plan of this product.', es: 'El plan de este producto.' }}>
        <P
          en="Twenty-two cases in eleven categories, each with its data and licence class, the status of its truth, and the unit of the plan that builds it. A case is marked built only when the committed index holds it; every other one is the plan, stated as such."
          es="Veintidós casos en once categorías, cada uno con sus datos y su clase de licencia, el estado de su verdad y la unidad del plan que lo construye. Un caso se marca construido solo cuando el índice comprometido lo contiene; todos los demás son el plan, declarado como tal."
        />
        <table className="caos-table" data-state={built ? 'ready' : 'loading'}>
          <thead>
            <tr>
              <th>{t('Case', 'Caso')}</th>
              <th>{t('Category', 'Categoría')}</th>
              <th className="caos-col-text">{t('Question', 'Pregunta')}</th>
              <th className="caos-col-text">{t('Data', 'Datos')}</th>
              <th>{t('Truth', 'Verdad')}</th>
              <th>{t('Status', 'Estado')}</th>
            </tr>
          </thead>
          <tbody>
            {CASES.map((c) => (
              <tr key={c.id} data-built={built?.has(c.id) ? 'true' : 'false'}>
                <td>{c.id}</td>
                <td>{pick(CATEGORY_TITLES[c.category], lang)}</td>
                <td className="caos-col-text">{pick(c.title, lang)}</td>
                <td className="caos-col-text">{pick(c.data, lang)}</td>
                <td>{pick(c.truth, lang)}</td>
                <td>{built?.has(c.id) ? t('built', 'construido') : `${t('planned', 'planificado')} (${c.unit})`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </DocSection>
      {all.state === 'ready' &&
        all.data.manifests.map((m) => (
          <DocSection key={m.case_id} title={{ en: `${m.case_id}: ${m.title.en}`, es: `${m.case_id}: ${m.title.es}` }} noRefsReason={{ en: 'Read from the committed artifacts; the methods are cited in Methodology.', es: 'Leído desde los artefactos comprometidos; los métodos se citan en Metodología.' }}>
            <P en={m.question.en} es={m.question.es} />
            <CaseVariants manifest={m} />
          </DocSection>
        ))}
    </DocPage>
  );
}
