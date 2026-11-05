// The Methodology section on PC-Hazard, the neural discrete-time survival rung of the lifetime PD of case C06: a hazard that is
// piecewise constant on a grid of loan-age intervals, whose rate in every interval a feed-forward network reads from the
// loan's covariates, trained on the Poisson likelihood of the interval counts. Transcribed from the PC-Hazard step (step 8) of
// notebook 07 of the provisions topic (notebooks/en/04-provisions/07-lifetime-pd-by-survival.ipynb: the loans drawn there with
// crossing profiles and its printed outputs), from the module that fits the rung (data-pipeline/pipeline/cases/c06/neural.py:
// the likelihood, the grid, the network, the early stopping) and from the committed out-of-time evaluation at the six reporting
// dates (data/derived/C06/models-rd-<date>.json, model[].details.evaluation, the C-index and the integrated Brier score, read
// whole); the ladder of the SDD (docs/design/SDD.md, the neural discrete-time survival row) names the check. Every display
// equation carries a caption that defines its symbols. The registry mounts it as one tab of the loss group, beside provisions.
import { Callout, Cite, DocSection } from '@fasl-work/caos-app-shell';
import type { ReactNode } from 'react';
import { Equation, P, Ref, T, useT } from '../../content/bi';
import type { MethodologySection } from '../methodologyRegistry';

const NB = 'https://github.com/fsantibanezleal/CAOS_Contraste/blob/main/notebooks';
const NB_PATH = '04-provisions/07-lifetime-pd-by-survival.ipynb';

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
  const d = (en: string) => t(en, en.replace('.', ','));
  const dates: Array<[string, string, string, string, string]> = [
    ['2006-12', '0.775', '0.559', '0.0416', '0.0414'],
    ['2008-12', '0.809', '0.590', '0.0620', '0.0615'],
    ['2010-12', '0.745', '0.635', '0.0272', '0.0274'],
    ['2019-12', '0.754', '0.611', '0.0115', '0.0117'],
    ['2020-06', '0.753', '0.644', '0.0124', '0.0126'],
    ['2023-06', '0.730', '0.634', '0.0135', '0.0136'],
  ];
  return (
    <DocSection
      area="method"
      title={{ en: 'PC-Hazard: a neural discrete-time survival model for the lifetime PD', es: 'PC-Hazard: un modelo neuronal de supervivencia en tiempo discreto para la PD de vida completa' }}
      refs={['kvamme2019', 'cox1972']}
    >
      <P
        en={<>The lifetime PD of a loan is the probability that it defaults before its term ends, read from a survival curve. The Cox model <Cite id="cox1972" /> and the discrete-time logit of the other rungs share one restriction: every loan&apos;s hazard is the same age profile scaled up or down. PC-Hazard relaxes it <Cite id="kvamme2019" />. The hazard is piecewise constant on a grid of loan-age intervals (in the product 60 intervals of 3 months, 15 years, the last interval open so that its rate holds for every older age), and a feed-forward network (two hidden layers of 32 units with a rectified linear activation, a softplus output so that every rate is positive, the bias of the output starting at the pooled rate of each interval) maps the covariates of a loan to the rate of every interval, so that each loan class has an age profile of its own. The covariates are the four static ones of the Cox rung, size, term, sector and revolver, a class of loans being one cell of them; the time scale is loan age in months, and prepayment and maturity are censoring.</>}
        es={<>La PD de vida completa de un préstamo es la probabilidad de que incumpla antes de que termine su plazo, leída de una curva de supervivencia. El modelo de Cox <Cite id="cox1972" /> y el logit de tiempo discreto de los otros peldaños comparten una restricción: el riesgo instantáneo de cada préstamo es el mismo perfil por edad escalado hacia arriba o hacia abajo. PC-Hazard la relaja <Cite id="kvamme2019" />. El riesgo instantáneo es constante por tramos sobre una grilla de intervalos de edad del préstamo (en el producto 60 intervalos de 3 meses, 15 años, con el último intervalo abierto de modo que su tasa rige para toda edad mayor), y una red de alimentación hacia adelante (dos capas ocultas de 32 unidades con activación lineal rectificada, una salida softplus para que cada tasa sea positiva, con el sesgo de la salida partiendo en la tasa agrupada de cada intervalo) lleva las covariables de un préstamo a la tasa de cada intervalo, de modo que cada clase de préstamos tiene su propio perfil por edad. Las covariables son las cuatro estáticas del peldaño de Cox, tamaño, plazo, sector y revolvente, y una clase de préstamos es una celda de ellas; la escala de tiempo es la edad del préstamo en meses, y el prepago y el vencimiento son censura.</>}
      />
      <Equation
        tex={String.raw`\ell(\theta) = \sum_{s,\,j}\Big( d_{sj}\,\log \lambda_{sj}(\theta) - e_{sj}\,\lambda_{sj}(\theta) \Big), \qquad \lambda_{s\cdot}(\theta) = \mathrm{softplus}\big(f_\theta(x_s)\big)`}
        caption={<T en={<>The training objective: s a loan class and j an age interval, d<sub>sj</sub> the defaults that fall in interval j among the loans of class s and e<sub>sj</sub> the months of observation those loans spent in it (a full interval for each interval before the one that holds the loan&apos;s last observed age, and the part of it up to that age in that one), λ<sub>sj</sub> the hazard rate per month, f<sub>θ</sub> the network with weights θ and x<sub>s</sub> the covariates of class s. ℓ is the Poisson likelihood of the interval counts, so the data enter only through the two tables d and e: the training is exact, full batch and deterministic, and costs the same on 1.7 million loans as on a few thousand. The loss is the negative of ℓ per training default; a seeded fifth of the loans is held out and the epoch of the lowest held-out loss is kept (early stopping).</>} es={<>El objetivo de entrenamiento: s una clase de préstamos y j un intervalo de edad, d<sub>sj</sub> los incumplimientos que caen en el intervalo j entre los préstamos de la clase s y e<sub>sj</sub> los meses de observación que esos préstamos pasaron en él (un intervalo completo por cada intervalo anterior al que contiene la última edad observada del préstamo, y la parte de él hasta esa edad en ese), λ<sub>sj</sub> la tasa de riesgo instantáneo por mes, f<sub>θ</sub> la red con pesos θ y x<sub>s</sub> las covariables de la clase s. ℓ es la verosimilitud de Poisson de los conteos por intervalo, así que los datos entran solo por las dos tablas d y e: el entrenamiento es exacto, de lote completo y determinista, y cuesta lo mismo con 1,7 millones de préstamos que con unos pocos miles. La pérdida es el negativo de ℓ por incumplimiento de entrenamiento; un quinto de los préstamos, elegido con semilla, se reserva y se conserva la época de menor pérdida reservada (detención temprana).</>} />}
      />
      <Equation
        tex={String.raw`\mathrm{PD}(a, h) = 1 - \exp\!\big(-(\Lambda_s(a + h) - \Lambda_s(a))\big), \qquad \Lambda_s(u) = \int_0^{u} \lambda_s(v)\,dv`}
        caption={<T en={<>The cumulative PD the rung reports: the probability of default within h more months for a loan of class s that is alive at age a, with Λ<sub>s</sub> the cumulative hazard, which for a piecewise constant hazard is the sum of each rate times the time spent in its interval. The observed side of its calibration is the Aalen-Johansen cumulative incidence, which counts prepayment as an exit that ends the loan&apos;s exposure, the incidence a provision needs.</>} es={<>La PD acumulada que informa el peldaño: la probabilidad de incumplir dentro de h meses más para un préstamo de la clase s vivo a la edad a, con Λ<sub>s</sub> el riesgo instantáneo acumulado, que para un riesgo constante por tramos es la suma de cada tasa por el tiempo pasado en su intervalo. El lado observado de su calibración es la incidencia acumulada de Aalen-Johansen, que cuenta el prepago como una salida que termina la exposición del préstamo, la incidencia que necesita una provisión.</>} />}
      />
      <h3>{t('What it is compared against and what it measured', 'Con qué se compara y qué midió')}</h3>
      <P
        en={<>The comparison is proportional hazards, one baseline per interval times one factor per class, in two settings. On loans drawn in the notebook, where the answer is known (four classes with crossing profiles, flat, an early peak, rising and a hump at two years, 24,000 loans of which 1,535 default, prepayment at 0.8% a month as a competing exit, a follow-up of 2 to 5 years, seed 20261030), the network keeps the epoch with the lowest held-out loss, the 11th of 71 run, with 1,876 weights for 80 rates. Its 12-month PD is off the truth by 0.131 points on average over the four classes against 1.015 for proportional hazards, which gives the early-peak class 2.11% where the truth is 4.04%; the mean absolute errors at 12, 24 and 36 months are 0.131, 0.163 and 0.508 points for PC-Hazard and 1.015, 0.728 and 0.481 for proportional hazards, so the error narrows by 36 months for both because the cumulative PD averages the profile over the years.</>}
        es={<>La comparación es riesgos proporcionales, una línea base por intervalo por un factor por clase, en dos escenarios. Con préstamos sorteados en el notebook, donde la respuesta se conoce (cuatro clases con perfiles que se cruzan, plano, un pico temprano, creciente y una joroba a los dos años, 24.000 préstamos de los cuales 1.535 incumplen, prepago de 0,8 % mensual como salida competidora, un seguimiento de 2 a 5 años, semilla 20261030), la red conserva la época de menor pérdida reservada, la 11 de 71 corridas, con 1.876 pesos para 80 tasas. Su PD a 12 meses yerra la verdad en 0,131 puntos en promedio sobre las cuatro clases contra 1,015 de los riesgos proporcionales, que da a la clase de pico temprano 2,11 % donde la verdad es 4,04 %; los errores absolutos medios a 12, 24 y 36 meses son 0,131; 0,163 y 0,508 puntos para PC-Hazard y 1,015; 0,728 y 0,481 para los riesgos proporcionales, así que el error se estrecha a los 36 meses para ambos porque la PD acumulada promedia el perfil a lo largo de los años.</>}
      />
      <P
        en={<>On the 1.7 million SBA 7(a) loans of case C06 the evaluation is out of time at the six reporting dates, beside the Cox rung. The hypothesis fixed before the run was a better calibration than Cox at most of the dates.</>}
        es={<>Con los 1,7 millones de préstamos SBA 7(a) del caso C06 la evaluación es fuera de tiempo en las seis fechas de reporte, junto al peldaño de Cox. La hipótesis fijada antes de la corrida fue una mejor calibración que Cox en la mayoría de las fechas.</>}
      />
      <Tbl
        id="pc-hazard-dates"
        head={[t('Reporting date', 'Fecha de reporte'), t('C-index, PC-Hazard', 'Índice C, PC-Hazard'), t('C-index, Cox', 'Índice C, Cox'), t('Integrated Brier score, PC-Hazard', 'Puntaje de Brier integrado, PC-Hazard'), t('Integrated Brier score, Cox', 'Puntaje de Brier integrado, Cox')]}
        rows={dates.map(([date, cp, cc, bp, bc]) => [date, d(cp), d(cc), d(bp), d(bc)])}
      />
      <P
        en={<>On the real loans the network ranks borrowers much better than Cox at every reporting date, with a C-index from 0.73 to 0.81 against 0.56 to 0.64, and its integrated Brier score is lower at four of the six dates (2010-12, 2019-12, 2020-06 and 2023-06). The hypothesis therefore holds at four of six.</>}
        es={<>Con los préstamos reales la red ordena a los deudores mucho mejor que Cox en cada fecha de reporte, con un índice C de 0,73 a 0,81 contra 0,56 a 0,64, y su puntaje de Brier integrado es menor en cuatro de las seis fechas (2010-12, 2019-12, 2020-06 y 2023-06). La hipótesis se cumple entonces en cuatro de seis.</>}
      />
      <h3>{t('Where it fails', 'Dónde falla')}</h3>
      <Callout variant="honest" title={t('What the shape buys and what it does not', 'Qué compra la forma y qué no')}>
        <T
          en={<>At 2006-12 and 2008-12 the integrated Brier score of PC-Hazard is higher than Cox&apos;s, by a few ten-thousandths (0.0416 against 0.0414 and 0.0620 against 0.0615): the two dates whose loans lived through the 2008 crisis, where no rung trained on the years before saw the age profile of a recession. A free age profile does not give a model a recession it has not seen. The network reads four static loan covariates, so it carries no macroeconomic path, which the discrete-time logit rung does; its calibration advantage is therefore a statement about the shape of the age profile, not about the cycle. Prepayment and maturity are treated as censoring in the fit, and the observed side of the calibration, Aalen-Johansen, treats prepayment as a competing exit, so the two differ by construction: on the drawn loans the Aalen-Johansen incidence is below the truth for that reason. At 36 months the network is not better than proportional hazards on the drawn loans (0.508 points against 0.481), and its last intervals widen where few loans are still observed. The network has 1,876 weights for 80 rates, and it is the early stop that keeps a model of this size from fitting the noise of 1,500 defaults. The covariates, the prepayment hazard and the follow-up of the drawn loans are inputs of the lesson, not estimates. Deep survival, mixture cure and multistate methods of the published literature are not run by the product.</>}
          es={<>En 2006-12 y 2008-12 el puntaje de Brier integrado de PC-Hazard es mayor que el de Cox, por unas diezmilésimas (0,0416 contra 0,0414 y 0,0620 contra 0,0615): las dos fechas cuyos préstamos vivieron la crisis de 2008, donde ningún peldaño entrenado con los años previos vio el perfil por edad de una recesión. Un perfil por edad libre no da a un modelo una recesión que no ha visto. La red lee cuatro covariables estáticas del préstamo, así que no lleva ninguna trayectoria macroeconómica, que el peldaño de logit de tiempo discreto sí lleva; su ventaja de calibración es entonces una afirmación sobre la forma del perfil por edad, no sobre el ciclo. El prepago y el vencimiento se tratan como censura en el ajuste, y el lado observado de la calibración, Aalen-Johansen, trata el prepago como una salida competidora, así que los dos difieren por construcción: en los préstamos sorteados la incidencia de Aalen-Johansen queda bajo la verdad por esa razón. A los 36 meses la red no es mejor que los riesgos proporcionales en los préstamos sorteados (0,508 puntos contra 0,481), y sus últimos intervalos se ensanchan donde pocos préstamos siguen observados. La red tiene 1.876 pesos para 80 tasas, y es la detención temprana la que impide que un modelo de este tamaño ajuste el ruido de 1.500 incumplimientos. Las covariables, el riesgo de prepago y el seguimiento de los préstamos sorteados son insumos de la lección, no estimaciones. Los métodos de supervivencia profunda, de cura mixta y multiestado de la literatura publicada no los corre el producto.</>}
        />
      </Callout>
      <P
        en={<>The notebook that runs this method on the product&apos;s data, in its step on the neural rung (the drawn loans with crossing profiles, the two fits, the cumulative PD against Aalen-Johansen and the out-of-time comparison with Cox): <a href={`${NB}/en/${NB_PATH}`}><code>notebooks/en/{NB_PATH}</code></a>. The rung is fitted by <Ref>pipeline.cases.c06.neural</Ref>, and the check the design document names is the C06 calibration at 12, 24 and 36 months against Aalen-Johansen per decile, the C-index and the integrated Brier score beside Cox, at the six reporting dates.</>}
        es={<>El notebook que corre este método con los datos del producto, en su paso sobre el peldaño neuronal (los préstamos sorteados con perfiles que se cruzan, los dos ajustes, la PD acumulada frente a Aalen-Johansen y la comparación fuera de tiempo con Cox): <a href={`${NB}/es/${NB_PATH}`}><code>notebooks/es/{NB_PATH}</code></a>. El peldaño lo ajusta <Ref>pipeline.cases.c06.neural</Ref>, y la verificación que nombra el documento de diseño es la calibración de C06 a 12, 24 y 36 meses frente a Aalen-Johansen por decil, el índice C y el puntaje de Brier integrado junto a Cox, en las seis fechas de reporte.</>}
      />
    </DocSection>
  );
}

export const methodologySection: MethodologySection = {
  id: 'pc-hazard',
  group: 'loss',
  order: 150,
  title: { en: 'PC-Hazard', es: 'PC-Hazard' },
  Body,
};
