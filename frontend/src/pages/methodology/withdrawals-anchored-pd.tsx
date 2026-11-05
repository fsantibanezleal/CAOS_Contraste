// The Methodology section on the PD anchored under informative withdrawals (case C04): the PD of a grade as a function of how
// much more likely a rating about to default is to be withdrawn, its bounds, the tipping value at which a decision flips and the
// value read off a second count of the defaults. Transcribed from the engine page docs/transitions/06_withdrawal-bounds.md of
// riskvalidation 1.1.0 (the family, the tipping value, the anchor, the limits) and from notebook 12 of the ratings-and-calibration
// topic (notebooks/en/03-ratings-and-calibration/12-an-anchored-pd-under-informative-withdrawals.ipynb), whose numbers, on S&P's
// pooled counts and on the generator of the case, are the notebook's printed outputs, which the committed C04 documents
// (data/derived/C04/sp.json and withdrawals.json) reproduce. Every display equation carries a caption that defines its symbols.
// The registry mounts it as one tab of the tests group, beside the transitions tab it extends.
import { Callout, Cite, DocSection } from '@fasl-work/caos-app-shell';
import type { ReactNode } from 'react';
import { Equation, P, Ref, T, useT } from '../../content/bi';
import type { MethodologySection } from '../methodologyRegistry';

const NB = 'https://github.com/fsantibanezleal/CAOS_Contraste/blob/main/notebooks';
const NB_PATH = '03-ratings-and-calibration/12-an-anchored-pd-under-informative-withdrawals.ipynb';

/** A small results table: a head row and the rows, the first column text and the others numbers. */
function Tbl({ head, rows, id }: { head: ReactNode[]; rows: ReactNode[][]; id: string }) {
  return (
    <table className="caos-table ct-wrap-head" data-table={id}>
      <thead>
        <tr>
          {head.map((h, i) => (
            <th key={i} className={i === 0 ? 'caos-col-text' : undefined}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            {r.map((c, j) => (
              <td key={j} className={j === 0 ? 'caos-col-text' : undefined}>{c}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Body() {
  const t = useT();
  return (
    <DocSection
      area="method"
      title={{ en: 'An anchored PD under informative withdrawals', es: 'Una PD anclada con retiros informativos' }}
      refs={['manski1989', 'cro2020', 'schuermannhanson2004', 'ebagl201716', 'brown2001', 'cerep']}
    >
      <P
        en={<>A rating withdrawn during the year leaves the cohort, and a withdrawn rating that would have defaulted is not seen to default. The usual treatments of the cohort estimator each fix one answer to what the withdrawn would have done: remove them and renormalise, the industry treatment <Cite id="schuermannhanson2004" />; keep them in the denominator unfollowed; or follow them to the year end <Cite id="ebagl201716" />. When withdrawal is informative, that is, more likely in the year before default, every one of them understates the PD, and no test of the matrix sees it. The proposed method does not choose an answer. It states the PD of a grade as a function of how informative withdrawal is, bounds it, finds the informativeness at which a decision flips, and, where a second source counts the defaults of the same grade differently, reads the informativeness off that source. Its application to rating withdrawals was not found in the literature (UNVERIFIED, search of 2026-10-28).</>}
        es={<>Una calificación retirada durante el año sale de la cohorte, y una calificación retirada que habría incumplido no se ve incumplir. Los tratamientos habituales del estimador de cohorte fijan cada uno una respuesta a lo que habrían hecho los retirados: eliminarlos y renormalizar, el tratamiento de la industria <Cite id="schuermannhanson2004" />; mantenerlos en el denominador sin seguirlos; o seguirlos hasta el fin del año <Cite id="ebagl201716" />. Cuando el retiro es informativo, es decir, más probable en el año previo al incumplimiento, todos ellos subestiman la PD, y ninguna prueba de la matriz lo ve. El método propuesto no elige una respuesta. Declara la PD de un grado como función de cuán informativo es el retiro, la acota, encuentra la informatividad en que una decisión se invierte y, donde una segunda fuente cuenta los incumplimientos del mismo grado de otro modo, lee la informatividad de esa fuente. Su aplicación a los retiros de calificaciones no se encontró en la literatura (UNVERIFIED, búsqueda del 2026-10-28).</>}
      />
      <Equation
        tex={String.raw`k = \frac{X/D}{(W - X)/S}, \qquad X(k) = W\,\frac{k\,D}{k\,D + S}, \qquad \mathrm{PD}(k) = \frac{D + X(k)}{N}, \quad N = D + S + W`}
        caption={<T en={<>The family of PDs of one grade and one period: D the ratings in default at the end, S those still rated and not in default, W those withdrawn, N the ratings at the start, X the number of the W withdrawn that would have defaulted within the period, and k the odds of withdrawal among the ratings that would default over the odds among those that would not. PD(k) increases in k. k = 0 is the unfollowed treatment, D/N; k = 1 (withdrawal independent of default) is the industry treatment D/(D + S); k tending to infinity makes every withdrawal a default in waiting, (D + W)/N, the worst-case bound of Manski for an outcome missing not at random <Cite id="manski1989" />. The family is the delta-adjusted tipping-point analysis of clinical trials with missing outcomes <Cite id="cro2020" />, with the odds ratio as the sensitivity parameter. X and k are in one-to-one correspondence for a cohort, so k states informativeness and is no extra assumption: the identifying content is in X, and the transition page alone cannot say which k.</>} es={<>La familia de PD de un grado y un período: D las calificaciones en incumplimiento al final, S las que siguen calificadas y sin incumplir, W las retiradas, N las calificaciones al inicio, X el número de las W retiradas que habrían incumplido dentro del período, y k la razón de probabilidades de retiro entre las calificaciones que incumplirían sobre la de las que no. PD(k) crece con k. k = 0 es el tratamiento sin seguimiento, D/N; k = 1 (retiro independiente del incumplimiento) es el tratamiento de la industria D/(D + S); k tendiendo a infinito hace de cada retiro un incumplimiento en espera, (D + W)/N, la cota de peor caso de Manski para un resultado faltante no al azar <Cite id="manski1989" />. La familia es el análisis de punto de inflexión con ajuste delta de los ensayos clínicos con resultados faltantes <Cite id="cro2020" />, con la razón de probabilidades como parámetro de sensibilidad. X y k están en correspondencia uno a uno para una cohorte, así que k declara la informatividad y no es un supuesto extra: el contenido que identifica está en X, y la página de transiciones sola no puede decir qué k.</>} />}
      />
      <Equation
        tex={String.raw`X^{*} = t\,N - D \in [0, W], \quad k^{*} = \frac{X^{*}\,S}{D\,(W - X^{*})}; \qquad X = \frac{N\,A}{N_a} - D \ \ (X \in [0, W])`}
        caption={<T en={<>The tipping value and the anchor. Tipping: t a decision threshold (a master-scale boundary, an IRB risk-weight step), X* the number of withdrawn defaults that brings PD(k) to t, and k* the k at which that happens; the status is flips up (the industry PD is below t and the family reaches it), flips down, or robust (never crossed). Anchor: where a second source counts the defaults of the same grade differently, for example the default page of the CEREP publication against its transition page, it gives A defaults over N<sub>a</sub> ratings; setting A/N<sub>a</sub> equal to PD(k) gives X and so the anchored k, and the Jeffreys interval of A/N<sub>a</sub> <Cite id="brown2001" /> carried through the same map gives the band of k and the anchored interval of the PD <Cite id="cerep" />. The interval counts the sampling noise of both pages, so it is conservative.</>} es={<>El valor de inflexión y el ancla. Inflexión: t un umbral de decisión (un límite de la escala maestra, un escalón de ponderador de riesgo IRB), X* el número de incumplimientos retirados que lleva PD(k) a t, y k* el k en que ocurre; el estado es se invierte al alza (la PD de la industria está bajo t y la familia la alcanza), se invierte a la baja, o robusto (nunca se cruza). Ancla: donde una segunda fuente cuenta los incumplimientos del mismo grado de otro modo, por ejemplo la página de incumplimientos de la publicación CEREP frente a su página de transiciones, da A incumplimientos sobre N<sub>a</sub> calificaciones; igualar A/N<sub>a</sub> a PD(k) da X y por tanto el k anclado, y el intervalo de Jeffreys de A/N<sub>a</sub> <Cite id="brown2001" /> llevado por la misma función da la banda de k y el intervalo anclado de la PD <Cite id="cerep" />. El intervalo cuenta el ruido de muestreo de ambas páginas, así que es conservador.</>} />}
      />
      <h3>{t('What it is compared against and what it measured', 'Con qué se compara y qué midió')}</h3>
      <P
        en={<>On S&amp;P&apos;s pooled counts for grade B (D = 372, S = 31,340, W = 4,451; the default page counts A = 993 over N<sub>a</sub> = 37,774) the family is wide: the PD is 1.029% with the withdrawn kept (k = 0), 1.173% with them removed (k = 1), 2.217% at k = 9, 7.709% at k = 100, and Manski&apos;s bound is 13.34%. Every point of the curve fits the same counts. The default page anchors k at 12.59 (band 11.18 to 14.10) and the PD at 2.629% (2.315% to 2.967%), more than twice the 1.173% of the transition page with the withdrawn removed. The tipping k to the next grade, CCC-C, whose master-scale boundary is 3.076%, is 16.81, above the anchored band, so on these counts B stays B.</>}
        es={<>Con los conteos agrupados de S&amp;P para el grado B (D = 372, S = 31.340, W = 4.451; la página de incumplimientos cuenta A = 993 sobre N<sub>a</sub> = 37.774) la familia es amplia: la PD es 1,029 % con los retirados mantenidos (k = 0), 1,173 % con ellos eliminados (k = 1), 2,217 % con k = 9, 7,709 % con k = 100, y la cota de Manski es 13,34 %. Cada punto de la curva calza con los mismos conteos. La página de incumplimientos ancla k en 12,59 (banda de 11,18 a 14,10) y la PD en 2,629 % (2,315 % a 2,967 %), más del doble del 1,173 % de la página de transiciones con los retirados eliminados. El k de inflexión hacia el grado siguiente, CCC-C, cuyo límite de escala maestra es 3,076 %, es 16,81, sobre la banda anclada, así que con estos conteos B sigue siendo B.</>}
      />
      <P
        en={<>The treatments are compared on a generator of known truth, the generator fitted to S&amp;P&apos;s pooled counts with withdrawal informative at k = 9, 200 draws per design, by the coverage of the true one-year PD of grade B (1.173%) by each treatment&apos;s interval. The oracle that follows the withdrawn to the year end needs the outcome of every withdrawn rating, which no transition page has.</>}
        es={<>Los tratamientos se comparan en un generador de verdad conocida, el generador ajustado a los conteos agrupados de S&amp;P con retiro informativo en k = 9, 200 sorteos por diseño, por la cobertura de la PD verdadera a un año del grado B (1,173 %) por el intervalo de cada tratamiento. El oráculo que sigue a los retirados hasta el fin del año necesita el resultado de cada calificación retirada, que ninguna página de transiciones tiene.</>}
      />
      <Tbl
        id="withdrawals-coverage"
        head={[t('Design', 'Diseño'), t('Removed (k = 1)', 'Eliminados (k = 1)'), t('Kept (k = 0)', 'Mantenidos (k = 0)'), t('Followed (oracle)', 'Seguidos (oráculo)'), t('Anchored', 'Anclado')]}
        rows={[
          [t('First-year cohort', 'Cohorte del primer año'), t('0.840', '0,840'), t('0.835', '0,835'), t('0.950', '0,950'), t('1.000', '1,000')],
          [t('Five cohorts pooled', 'Cinco cohortes agrupadas'), t('0.110', '0,110'), t('0.030', '0,030'), t('0.740', '0,740'), t('0.980', '0,980')],
          [t('Second source counts 70% of the defaults', 'Segunda fuente cuenta 70 % de los incumplimientos'), t('0.840', '0,840'), t('0.835', '0,835'), t('0.950', '0,950'), t('0.995', '0,995')],
          [t('First-year cohort, ten times larger', 'Cohorte del primer año, diez veces mayor'), t('0.215', '0,215'), t('0.075', '0,075'), t('0.935', '0,935'), t('1.000', '1,000')],
        ]}
      />
      <P
        en={<>The claim, fixed before any run, has three parts. The anchored interval covers the true PD in at least 90% of the draws at k = 1, 3 and 9: it does, in every design above. The existing treatments cover it in under 50% at k = 9: this holds only where the sample is large enough for the bias to outgrow the noise (pooled cohorts, ten times the cohort); in the first-year cohort of the case&apos;s size the removed and kept intervals still cover 84% and 83.5%, because the understatement of 23% to 28% is smaller than the sampling interval, so the clause as written is refuted at the size of the case. The third part is the stability of the anchored k across years, below.</>}
        es={<>La afirmación, fijada antes de toda corrida, tiene tres partes. El intervalo anclado cubre la PD verdadera en al menos 90 % de los sorteos con k = 1, 3 y 9: lo hace, en cada diseño de arriba. Los tratamientos existentes la cubren en menos de 50 % con k = 9: esto se cumple solo donde la muestra es lo bastante grande para que el sesgo supere al ruido (cohortes agrupadas, diez veces la cohorte); en la cohorte del primer año del tamaño del caso los intervalos de eliminados y mantenidos aún cubren 84 % y 83,5 %, porque la subestimación de 23 % a 28 % es menor que el intervalo de muestreo, así que la cláusula tal como está escrita se refuta al tamaño del caso. La tercera parte es la estabilidad del k anclado entre años, abajo.</>}
      />
      <h3>{t('Where it fails', 'Dónde falla')}</h3>
      <Callout variant="honest" title={t('The stability clause fails', 'La cláusula de estabilidad falla')}>
        <T
          en={<>The stability clause was fixed before the run: the anchored k is stable when at least 80% of the annual cohorts&apos; bands contain the pooled k. For grade B of S&amp;P, 17 of the 25 usable annual cohorts have a band that holds the pooled k of 12.59, a share of 0.68, under the 80%, and the clause fails; so does CCC-C (0.64, pooled k 36.25). At S&amp;P the anchored k is stable for AA, A, BBB and BB; at Fitch it is stable for BB and CCC-C and not for BBB and B. The reason is that the anchored k absorbs everything that makes the two pages count defaults differently, not only the informativeness of withdrawals, and that difference moves with the year (the default page counts every distinct rating that defaulted during the period, the transition page the ratings in a default category at its end, and ESMA sets no common definition). A k of 36 is therefore a k conditional on the two pages defining default alike, not an estimate of how informative S&amp;P&apos;s withdrawals are.</>}
          es={<>La cláusula de estabilidad se fijó antes de la corrida: el k anclado es estable cuando al menos 80 % de las bandas de las cohortes anuales contiene el k agrupado. Para el grado B de S&amp;P, 17 de las 25 cohortes anuales utilizables tienen una banda que contiene el k agrupado de 12,59, una parte de 0,68, bajo el 80 %, y la cláusula falla; también CCC-C (0,64, k agrupado 36,25). En S&amp;P el k anclado es estable para AA, A, BBB y BB; en Fitch es estable para BB y CCC-C y no para BBB y B. La razón es que el k anclado absorbe todo lo que hace que las dos páginas cuenten los incumplimientos de otro modo, no solo la informatividad de los retiros, y esa diferencia se mueve con el año (la página de incumplimientos cuenta toda calificación distinta que incumplió durante el período, la de transiciones las calificaciones en una categoría de incumplimiento al final, y ESMA no fija una definición común). Un k de 36 es entonces un k condicionado a que las dos páginas definan el incumplimiento igual, no una estimación de cuán informativos son los retiros de S&amp;P.</>}
        />
      </Callout>
      <P
        en={<>Three limits remain. The method is one period: a rating withdrawn in an earlier year is missing from a later cohort, and pooled cohorts inherit that selection, so the pooled anchored point estimate stays 16.6% low in the engine&apos;s study even though the interval covers through its width. A mismatch of definitions is not repaired by the interval: when the second source counts only 70% of the true defaults the anchored point is 22.8% low, the same as the industry treatment, and the interval is centred on the wrong value (engine study). The anchored interval is conservative, 1.9 times as wide as the oracle&apos;s Jeffreys interval at the case&apos;s size (2.14% against 1.12% at informative withdrawal 9, engine study). A grade with no observed default has no k, only Manski&apos;s bound W/N, and the result says why.</>}
        es={<>Quedan tres límites. El método es de un período: una calificación retirada en un año anterior falta en una cohorte posterior, y las cohortes agrupadas heredan esa selección, así que la estimación puntual anclada agrupada queda 16,6 % baja en el estudio del motor aunque el intervalo cubra por su ancho. Una discrepancia de definiciones no la repara el intervalo: cuando la segunda fuente cuenta solo 70 % de los incumplimientos verdaderos el punto anclado queda 22,8 % bajo, igual que el tratamiento de la industria, y el intervalo se centra en el valor equivocado (estudio del motor). El intervalo anclado es conservador, 1,9 veces el ancho del intervalo de Jeffreys del oráculo al tamaño del caso (2,14 % contra 1,12 % con retiro informativo 9, estudio del motor). Un grado sin incumplimientos observados no tiene k, solo la cota de Manski W/N, y el resultado dice por qué.</>}
      />
      <P
        en={<>The notebook that runs this method on the product&apos;s data, from the family on S&amp;P&apos;s counts to the coverage study and the stability test: <a href={`${NB}/en/${NB_PATH}`}><code>notebooks/en/{NB_PATH}</code></a>. The engine page: <Ref>docs/transitions/06_withdrawal-bounds.md</Ref> of riskvalidation 1.1.0.</>}
        es={<>El notebook que corre este método con los datos del producto, desde la familia con los conteos de S&amp;P hasta el estudio de cobertura y la prueba de estabilidad: <a href={`${NB}/es/${NB_PATH}`}><code>notebooks/es/{NB_PATH}</code></a>. La página del motor: <Ref>docs/transitions/06_withdrawal-bounds.md</Ref> de riskvalidation 1.1.0.</>}
      />
    </DocSection>
  );
}

export const methodologySection: MethodologySection = {
  id: 'withdrawals-anchored-pd',
  group: 'tests',
  order: 200,
  title: { en: 'PD under informative withdrawals', es: 'PD con retiros informativos' },
  Body,
};
