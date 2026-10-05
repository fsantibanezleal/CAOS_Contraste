// Every case, read from its committed artifacts and compared with the theory. No number on this page is typed
// in: the table and the chart are computed from the index, the manifests and the traces at load time (T13).
import { DocPage, DocSection, PlotCard, formatNumber, useShellLang } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import { useMemo } from 'react';
import { loadAllCases, useArtifact } from '../api/artifacts';
import { finalSize } from '../engine/sir';
import { P, useT } from '../content/bi';

export function Experiments() {
  const lang = useShellLang();
  const t = useT();
  const all = useArtifact((s) => loadAllCases(s), []);
  const rows = useMemo(() => {
    if (all.state !== 'ready') return null;
    return all.data.cases.map(({ manifest: m, trace }) => {
      const r0 = m.params.beta / m.params.gamma;
      return { m, r0, s: trace.summary, z: finalSize(r0) };
    });
  }, [all]);
  const chart = useMemo(() => {
    if (!rows) return null;
    const grid = Array.from({ length: 61 }, (_, k) => Math.round((0.4 + k * 0.1) * 100) / 100);
    const xs = [...new Set([...grid, ...rows.map((r) => Math.round(r.r0 * 100) / 100)])].sort((a, b) => a - b);
    const caseAt = new Map(rows.map((r) => [Math.round(r.r0 * 100) / 100, r.s.attack_rate]));
    return { xs, theory: xs.map(finalSize), cases: xs.map((x) => caseAt.get(x) ?? null) };
  }, [rows]);

  return (
    <DocPage wide title={{ en: 'Experiments', es: 'Experimentos' }} lede={t('Every baked case against the final-size relation, read from the committed artifacts.', 'Cada caso precalculado contra la relación de tamaño final, leído desde los artefactos comprometidos.')}>
      <DocSection title={{ en: 'The cases', es: 'Los casos' }} refs={['km1927']}>
        <P
          en="Each row is one case of the registry: its reproduction number, the peak and the attack rate of its committed trace, the share the final-size relation predicts for a fully run epidemic, and what a reader should expect to see."
          es="Cada fila es un caso del registro: su número reproductivo, el pico y la tasa de ataque de su traza comprometida, la fracción que predice la relación de tamaño final para una epidemia completa, y lo que el lector debería esperar ver."
        />
        {rows ? (
          <table className="caos-table" data-state="ready">
            <thead>
              <tr>
                <th>{t('Case', 'Caso')}</th>
                <th>R0</th>
                <th>{t('Peak infected', 'Pico de contagiados')}</th>
                <th>{t('Peak day', 'Día del pico')}</th>
                <th>{t('Attack rate', 'Tasa de ataque')}</th>
                <th>{t('Final size', 'Tamaño final')}</th>
                <th className="caos-col-text">{t('Expected', 'Esperado')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.m.case_id}>
                  <td>{r.m.title[lang]}</td>
                  <td>{formatNumber(r.r0, lang, { decimals: 2 })}</td>
                  <td>{formatNumber(r.s.peak_I, lang, { decimals: 0 })}</td>
                  <td>{formatNumber(r.s.t_peak, lang, { decimals: 1 })}</td>
                  <td>{formatNumber(r.s.attack_rate, lang, { percent: true, decimals: 1 })}</td>
                  <td>{formatNumber(r.z, lang, { percent: true, decimals: 1 })}</td>
                  <td className="caos-col-text">{r.m.expected_band[lang]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="caos-pending" data-state={all.state === 'error' ? 'error' : 'loading'}>
            {all.state === 'error' ? all.error : t('Loading the artifacts', 'Cargando los artefactos')}
          </p>
        )}
      </DocSection>
      <DocSection title={{ en: 'Against the theory', es: 'Contra la teoría' }} refs={['km1927', 'miller2012']}>
        <P
          en="The curve is the final-size relation; the points are the cases as baked, at the end of their horizon. A point on the curve is an epidemic that ran to its end. A point below it ran out of time (the slow-spread case, close to the threshold) or never started (the control without an initial infection)."
          es="La curva es la relación de tamaño final; los puntos son los casos tal como se precalcularon, al final de su horizonte. Un punto sobre la curva es una epidemia que llegó a su fin. Un punto bajo ella se quedó sin tiempo (el caso de propagación lenta, cerca del umbral) o nunca empezó (el control sin contagio inicial)."
        />
        {chart ? (
          <PlotCard title={{ en: 'Attack rate against R0', es: 'Tasa de ataque contra R0' }} lane="replay" provenance="synthetic">
            <UPlotChart
              height={320}
              x={{ values: chart.xs, label: { en: 'Basic reproduction number', es: 'Número reproductivo básico' } }}
              y={{ label: { en: 'Attack rate', es: 'Tasa de ataque' }, range: [0, 1] }}
              series={[
                { label: { en: 'Final-size relation', es: 'Relación de tamaño final' }, values: chart.theory, color: '--color-accent' },
                { label: { en: 'Baked cases', es: 'Casos precalculados' }, values: chart.cases, color: '--color-magenta', mode: 'points' },
              ]}
            />
          </PlotCard>
        ) : (
          <p className="caos-pending" data-state={all.state === 'error' ? 'error' : 'loading'}>
            {t('Loading the artifacts', 'Cargando los artefactos')}
          </p>
        )}
      </DocSection>
    </DocPage>
  );
}
