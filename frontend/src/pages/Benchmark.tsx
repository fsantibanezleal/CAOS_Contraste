// What each case costs: the committed artifact against its byte budget, the surrogate's held-out error, and the
// live engine timed in this browser against the run budget the lane gate set. Every number is read from the
// artifacts or measured here; none is typed in.
import { DocPage, DocSection, PlotCard, Verdict, formatNumber, useShellLang } from '@fasl-work/caos-app-shell';
import { useEffect, useState } from 'react';
import { loadAllCases, useArtifact, type CaseData } from '../api/artifacts';
import { simulate } from '../engine/sir';
import { P, useT } from '../content/bi';

interface Timing {
  caseId: string;
  medianMs: number;
}

/**
 * Times the live engine on every case, after the page has rendered, outside any animation frame. A browser coarsens
 * its clock (to 0.1 ms or more), so each sample times a batch of runs long enough to measure, and the median of seven
 * samples is divided back to one run.
 */
function useTimings(cases: CaseData[] | null): Timing[] | null {
  const [out, setOut] = useState<Timing[] | null>(null);
  useEffect(() => {
    if (!cases) return;
    const id = window.setTimeout(() => {
      setOut(
        cases.map(({ manifest }) => {
          let batch = 1;
          for (;;) {
            const t0 = performance.now();
            for (let k = 0; k < batch; k += 1) simulate(manifest.params);
            if (performance.now() - t0 >= 20 || batch >= 1 << 16) break;
            batch *= 2;
          }
          const runs: number[] = [];
          for (let k = 0; k < 7; k += 1) {
            const t0 = performance.now();
            for (let j = 0; j < batch; j += 1) simulate(manifest.params);
            runs.push((performance.now() - t0) / batch);
          }
          runs.sort((a, b) => a - b);
          return { caseId: manifest.case_id, medianMs: runs[3] };
        }),
      );
    }, 0);
    return () => window.clearTimeout(id);
  }, [cases]);
  return out;
}

export function Benchmark() {
  const lang = useShellLang();
  const t = useT();
  const all = useArtifact((s) => loadAllCases(s), []);
  const cases = all.state === 'ready' ? all.data.cases : null;
  const timings = useTimings(cases);
  const ready = cases && timings;
  const worst = ready ? Math.max(...cases.map((c, i) => timings[i].medianMs / c.manifest.gate.run_ms_budget)) : 0;

  return (
    <DocPage wide title={{ en: 'Benchmark', es: 'Benchmark' }} lede={t('What each case costs, baked and live, against the budgets its lane was given.', 'Lo que cuesta cada caso, precalculado y en vivo, contra los presupuestos que se le asignaron a su carril.')}>
      <DocSection title={{ en: 'Budgets and timings', es: 'Presupuestos y tiempos' }} noRefsReason={{ en: 'Measures this build.', es: 'Mide esta compilación.' }}>
        <P
          en="The pipeline's lane gate decides, per case, whether the live engine may re-run it in the browser: the engine must be light, the committed trace small, and the run fast. This page reads each budget from the manifest and measures the live engine here, as the median of seven timed batches of runs, so the verdict is about this browser on this device."
          es="La compuerta de carril del pipeline decide, por caso, si el motor en vivo puede volver a correrlo en el navegador: el motor debe ser liviano, la traza comprometida pequeña y la corrida rápida. Esta página lee cada presupuesto desde el manifiesto y mide aquí el motor en vivo, como la mediana de siete lotes de corridas medidos, así que el veredicto es sobre este navegador en este dispositivo."
        />
        {ready ? (
          <>
            <PlotCard title={{ en: 'The live lane on this device', es: 'El carril en vivo en este dispositivo' }} lane="live" provenance="synthetic">
              <Verdict
                title={{ en: 'Run budget', es: 'Presupuesto de corrida' }}
                tone={worst <= 1 ? 'good' : 'bad'}
                verdict={
                  worst <= 1
                    ? { en: `Every case runs within its budget; the slowest uses ${formatNumber(worst, 'en', { percent: true, digits: 2 })} of it.`, es: `Cada caso corre dentro de su presupuesto; el más lento usa ${formatNumber(worst, 'es', { percent: true, digits: 2 })} de él.` }
                    : { en: 'A case exceeds its run budget on this device: the live lane would be slow here.', es: 'Un caso excede su presupuesto de corrida en este dispositivo: el carril en vivo sería lento aquí.' }
                }
              />
            </PlotCard>
            <table className="caos-table" data-state="ready">
              <thead>
                <tr>
                  <th>{t('Case', 'Caso')}</th>
                  <th>{t('Lane', 'Carril')}</th>
                  <th>{t('Trace (bytes)', 'Traza (bytes)')}</th>
                  <th>{t('Byte budget', 'Presupuesto de bytes')}</th>
                  <th>{t('Live run (ms)', 'Corrida en vivo (ms)')}</th>
                  <th>{t('Run budget (ms)', 'Presupuesto de corrida (ms)')}</th>
                </tr>
              </thead>
              <tbody>
                {cases.map((c, i) => (
                  <tr key={c.manifest.case_id}>
                    <td>{c.manifest.title[lang]}</td>
                    <td>{c.manifest.lane === 'live' ? t('live', 'en vivo') : t('precompute', 'precálculo')}</td>
                    <td>{formatNumber(c.manifest.artifact.bytes, lang, { decimals: 0 })}</td>
                    <td>{formatNumber(c.manifest.gate.trace_bytes_budget, lang, { decimals: 0 })}</td>
                    <td>{formatNumber(timings[i].medianMs, lang, { digits: 3 })}</td>
                    <td>{formatNumber(c.manifest.gate.run_ms_budget, lang, { decimals: 0 })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : (
          <p className="caos-pending" data-state={all.state === 'error' ? 'error' : 'loading'}>
            {all.state === 'error' ? all.error : t('Loading the artifacts and timing the live engine', 'Cargando los artefactos y midiendo el motor en vivo')}
          </p>
        )}
      </DocSection>
      <DocSection title={{ en: 'The surrogate', es: 'El sustituto' }} noRefsReason={{ en: 'Measures this build.', es: 'Mide esta compilación.' }}>
        <P
          en="The pipeline also trains a small surrogate that predicts the peak share from the case parameters, and evaluates it on twenty held-out parameter sets drawn with a seed disjoint from training. It is there to show where a learned model sits in the pipeline; its error is reported, not hidden."
          es="El pipeline también entrena un sustituto pequeño que predice la fracción del pico a partir de los parámetros del caso, y lo evalúa en veinte conjuntos de parámetros reservados, sorteados con una semilla disjunta del entrenamiento. Está ahí para mostrar dónde se ubica un modelo aprendido en el pipeline; su error se reporta, no se oculta."
        />
        {cases ? (
          (() => {
            const sets = [...new Set(cases.map((c) => JSON.stringify(c.manifest.metrics)))];
            const m = cases[0].manifest.metrics;
            return (
              <>
                {sets.length > 1 && (
                  <Verdict
                    title={{ en: 'One evaluation per bake', es: 'Una evaluación por precálculo' }}
                    tone="bad"
                    verdict={{ en: `The manifests carry ${sets.length} different evaluations: some were written by a different run than the release bake.`, es: `Los manifiestos traen ${sets.length} evaluaciones distintas: algunos los escribió una corrida distinta del precálculo de la versión.` }}
                  />
                )}
                <table className="caos-table" data-state="ready">
                  <thead>
                    <tr>
                      <th>{t('Evaluation', 'Evaluación')}</th>
                      <th>{t('Held-out R squared', 'R cuadrado reservado')}</th>
                      <th>{t('Held-out RMSE', 'RMSE reservado')}</th>
                      <th>{t('Held-out sets', 'Conjuntos reservados')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{t('This bake, all cases', 'Este precálculo, todos los casos')}</td>
                      <td>{formatNumber(m.surrogate_peakfrac_r2 ?? null, lang, { decimals: 4 })}</td>
                      <td>{formatNumber(m.surrogate_peakfrac_rmse ?? null, lang, { decimals: 5 })}</td>
                      <td>{formatNumber(m.n_holdout ?? null, lang, { decimals: 0 })}</td>
                    </tr>
                  </tbody>
                </table>
              </>
            );
          })()
        ) : (
          <p className="caos-pending" data-state={all.state === 'error' ? 'error' : 'loading'}>
            {t('Loading the artifacts', 'Cargando los artefactos')}
          </p>
        )}
      </DocSection>
    </DocPage>
  );
}
