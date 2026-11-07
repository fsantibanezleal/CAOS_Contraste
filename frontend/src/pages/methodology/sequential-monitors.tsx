// The Methodology section on the sequential monitors (cases C22, C11 and C03): e-processes that read a back-test of the VaR
// or a calibration of the PD every day or every vintage and keep their size. Transcribed from the engine page
// docs/sequential/README.md of riskvalidation 1.1.0 (the idea, the assumptions, what is refused) and from notebook 09 of the
// validating-the-validator topic (notebooks/en/14-validating-the-validator/10-sequential-monitors-that-keep-their-size-when-read-every-day.ipynb).
// The numbers are the notebook's, which read the committed documents of C22 (data/derived/C22/other-families.json, the study
// of 2,000 series per scenario), C11 and C03, not the engine page's own run, whose seed and tables differ (for instance 12.2
// points of power cost at three times the hit rate there, 11.9 here). Every display equation carries a caption that defines
// its symbols. The second equation is the grade monitor of riskvalidation 1.1.0 (validation/sequential/pd_grades.py, its module text), and the figure draws the size column of the table beside it. The registry mounts it as one tab of the market group, beside the VaR recalibration and the PLA complement.
import { Callout, Cite, DocSection, Figure } from '@fasl-work/caos-app-shell';
import type { ReactNode } from 'react';
import { Equation, P, Ref, T, useT } from '../../content/bi';
import type { MethodologySection } from '../methodologyRegistry';
import { GroupedBars } from '../MethodFigures';

const NB = 'https://github.com/fsantibanezleal/CAOS_Contraste/blob/main/notebooks';
const NB_PATH = '14-validating-the-validator/10-sequential-monitors-that-keep-their-size-when-read-every-day.ipynb';

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
      kind="classical"
      title={{ en: 'Sequential monitors that keep their size', es: 'Monitores secuenciales que mantienen su tamaño' }}
      refs={['ramdas2023', 'wang2022ebacktesting', 'kupiec1995', 'christoffersen1998', 'bcbs22', 'mar32']}
    >
      <P
        en={<>A fixed-window test is valid when it is read once, on a window fixed in advance: Kupiec&apos;s test <Cite id="kupiec1995" />, the independence test of Christoffersen <Cite id="christoffersen1998" /> and the Basel traffic light <Cite id="bcbs22" /> are valid in that use. A desk reads them every morning, on the trailing 250 days or on all the days so far, and acts on the first red; each reading is another chance of a false alarm, and over 1,000 mornings the chances add up. The proposed method is a set of monitors, built as e-processes <Cite id="ramdas2023" />, that can be read every day, or every vintage, without losing their size, for the VaR exception rate, for clustering of exceptions, for the defaults of each PD grade, and for a battery of them. E-values for the back-testing of the VaR and the ES are the line of work of Wang, Wang and Ziegel <Cite id="wang2022ebacktesting" />; the application to PD calibration by vintage and to a validator&apos;s battery was not found in the literature (UNVERIFIED, the engine page records that the search was not run in its unit).</>}
        es={<>Una prueba de ventana fija es válida cuando se lee una vez, sobre una ventana fijada de antemano: la prueba de Kupiec <Cite id="kupiec1995" />, la prueba de independencia de Christoffersen <Cite id="christoffersen1998" /> y el semáforo de Basilea <Cite id="bcbs22" /> son válidas en ese uso. Una mesa las lee cada mañana, sobre los últimos 250 días o sobre todos los días hasta hoy, y actúa con el primer rojo; cada lectura es otra oportunidad de una falsa alarma, y en 1.000 mañanas las oportunidades se suman. El método propuesto es un conjunto de monitores, construidos como procesos e <Cite id="ramdas2023" />, que pueden leerse cada día, o cada cosecha, sin perder su tamaño, para la tasa de excepciones del VaR, para el agrupamiento de excepciones, para los incumplimientos de cada grado de PD, y para una batería de ellos. Los valores e para las pruebas retrospectivas del VaR y de la pérdida esperada son la línea de trabajo de Wang, Wang y Ziegel <Cite id="wang2022ebacktesting" />; la aplicación a la calibración de la PD por cosecha y a la batería de un validador no se encontró en la literatura (UNVERIFIED, la página del motor registra que la búsqueda no se corrió en su unidad).</>}
      />
      <Equation
        tex={String.raw`E_t(m) = \prod_{s \le t} \Big( m^{h_s}\Big(\frac{1 - m\alpha}{1 - \alpha}\Big)^{1 - h_s} \Big), \qquad E_t = \frac{1}{|M|}\sum_{m \in M} E_t(m), \qquad P\Big(\sup_t E_t \ge \frac{1}{a}\Big) \le a`}
        caption={<T en={<>The e-process of the exception rate: h<sub>s</sub> equal to 1 when day s is an exception and 0 otherwise, α the target rate (0.01), m the multiple of the target that one bet stakes on, so that E<sub>t</sub>(m) is the likelihood ratio of the alternative rate mα against α, a non-negative process with mean 1 under the null at every day; M the set of eight multiples 0.25, 0.5, 1.5, 2, 3, 4, 6 and 10 with equal weights, and E<sub>t</sub> their average, which has mean 1 under the null too. Ville&apos;s inequality bounds the chance that such a process ever reaches 1/a, so rejecting the first time E<sub>t</sub> is at least 20 (a = 0.05) has a size of at most 5% however often it is read and whenever the desk stops. The anytime-valid p-value is min(1, 1/sup<sub>t</sub> E<sub>t</sub>). The mixture is what makes the monitor useful when the size of the defect is unknown, and it is also the price: it spreads the bet, so the power at a fixed horizon is below that of a likelihood ratio test that knows the alternative.</>} es={<>El proceso e de la tasa de excepciones: h<sub>s</sub> igual a 1 cuando el día s es una excepción y 0 en otro caso, α la tasa objetivo (0,01), m el múltiplo del objetivo sobre el que apuesta una apuesta, de modo que E<sub>t</sub>(m) es la razón de verosimilitud de la tasa alternativa mα contra α, un proceso no negativo con media 1 bajo la nula en cada día; M el conjunto de ocho múltiplos 0,25; 0,5; 1,5; 2; 3; 4; 6 y 10 con pesos iguales, y E<sub>t</sub> su promedio, que también tiene media 1 bajo la nula. La desigualdad de Ville acota la probabilidad de que tal proceso llegue alguna vez a 1/a, así que rechazar la primera vez que E<sub>t</sub> es al menos 20 (a = 0,05) tiene un tamaño de a lo más 5 % por muchas veces que se lea y cuando sea que la mesa se detenga. El valor p válido en todo momento es min(1, 1/sup<sub>t</sub> E<sub>t</sub>). La mezcla es lo que hace útil al monitor cuando se desconoce el tamaño del defecto, y es también el precio: reparte la apuesta, así que la potencia a un horizonte fijo queda bajo la de una prueba de razón de verosimilitud que conoce la alternativa.</>} />}
      />
      <P
        en={<>The same construction gives the other monitors: a first-order Markov alternative for a hit after a hit (P(hit given hit) = mα, with m = 3, 6, 12, 25, 50); for the defaults of a grade, a multiplicative miscalibration mp of the predicted PD p on a 16-point grid between 1/4 and 4, the grades combined by the product (independent grades) or by the average, which is an e-process whatever the dependence, at a cost in power when one grade carries the signal; and a battery that averages monitors of the same steps. The mixture weights are fixed before any outcome, which keeps the process an e-process. Each monitor is registered in the test catalogue with its own null hypothesis and returns the engine&apos;s result record, red when the monitor rejected.</>}
        es={<>La misma construcción da los demás monitores: una alternativa markoviana de primer orden para una excepción tras una excepción (P(excepción dada una excepción) = mα, con m = 3, 6, 12, 25, 50); para los incumplimientos de un grado, una descalibración multiplicativa mp de la PD predicha p en una grilla de 16 puntos entre 1/4 y 4, con los grados combinados por el producto (grados independientes) o por el promedio, que es un proceso e sea cual sea la dependencia, con un costo en potencia cuando un grado lleva la señal; y una batería que promedia monitores de los mismos pasos. Los pesos de la mezcla se fijan antes de todo resultado, lo que mantiene al proceso como proceso e. Cada monitor está registrado en el catálogo de pruebas con su propia hipótesis nula y devuelve el registro de resultado del motor, rojo cuando el monitor rechazó.</>}
      />
      <Equation
        tex={String.raw`\log \mathrm{LR}_k(s) = d_s \log m_k + (n_s - d_s)\log\frac{1 - m_k p_g}{1 - p_g}, \qquad E_{t,g} = \sum_{k} w_k \exp\Big(\sum_{s \le t}\log \mathrm{LR}_k(s)\Big), \qquad E_t^{\mathrm{prod}} = \prod_{g} E_{t,g}, \quad E_t^{\mathrm{avg}} = \frac{1}{G}\sum_{g} E_{t,g}`}
        caption={<T en={<>The monitor of the defaults of a grade: n<sub>s</sub> the obligors of the grade at step s and d<sub>s</sub> those that default, p<sub>g</sub> the predicted PD of grade g, m<sub>k</sub> one of the 16 multipliers of the grid between 1/4 and 4 (1 excluded) that bets on a true PD of m<sub>k</sub> p<sub>g</sub>, w<sub>k</sub> the mixture weights fixed before any outcome (proportional to the square root of m<sub>k</sub> p<sub>g</sub> over 1 minus m<sub>k</sub> p<sub>g</sub>, the Jeffreys density on the log grid), LR<sub>k</sub> the likelihood ratio of that alternative to the null of a binomial with the predicted PD, and G the number of grades. The grades combine by the product, which is an e-process when their defaults are independent given the past, or by the average, which is one with no assumption on the dependence (riskvalidation 1.1.0, <Ref>validation/sequential/pd_grades.py</Ref>).</>} es={<>El monitor de los incumplimientos de un grado: n<sub>s</sub> los deudores del grado en el paso s y d<sub>s</sub> los que incumplen, p<sub>g</sub> la PD predicha del grado g, m<sub>k</sub> uno de los 16 multiplicadores de la grilla entre 1/4 y 4 (sin el 1) que apuesta a una PD verdadera de m<sub>k</sub> p<sub>g</sub>, w<sub>k</sub> los pesos de la mezcla fijados antes de todo resultado (proporcionales a la raíz de m<sub>k</sub> p<sub>g</sub> sobre 1 menos m<sub>k</sub> p<sub>g</sub>, la densidad de Jeffreys en la grilla logarítmica), LR<sub>k</sub> la razón de verosimilitud de esa alternativa a la nula de una binomial con la PD predicha, y G el número de grados. Los grados se combinan por el producto, que es un proceso e cuando sus incumplimientos son independientes dado el pasado, o por el promedio, que lo es sin supuesto sobre la dependencia (riskvalidation 1.1.0, <Ref>validation/sequential/pd_grades.py</Ref>).</>} />}
      />
      <h3>{t('What it is compared against and what it measured', 'Con qué se compara y qué midió')}</h3>
      <P
        en={<>The comparators are the published tests read as a desk reads them: Kupiec on the trailing 250 days and on all the days so far, both read every day; the traffic light, the first day the trailing count leaves the green zone (5 exceptions in 250 days at 99%); Christoffersen&apos;s independence test on the trailing 250 days; and, as the reference for power, Kupiec read once on the first 250 days. The study is the one of case C22: 2,000 series of 1,000 days per scenario from the engine&apos;s hit generator, a correct VaR at 1%, a hit rate 2, 3 and 4 times too high, and exceptions at the right rate that cluster.</>}
        es={<>Los comparadores son las pruebas publicadas leídas como las lee una mesa: Kupiec sobre los últimos 250 días y sobre todos los días hasta hoy, ambas leídas cada día; el semáforo, el primer día en que el conteo de la ventana sale de la zona verde (5 excepciones en 250 días al 99 %); la prueba de independencia de Christoffersen sobre los últimos 250 días; y, como referencia de potencia, Kupiec leída una vez sobre los primeros 250 días. El estudio es el del caso C22: 2.000 series de 1.000 días por escenario del generador de excepciones del motor, un VaR correcto al 1 %, una tasa de excepciones 2, 3 y 4 veces demasiado alta, y excepciones a la tasa correcta que se agrupan.</>}
      />
      <Tbl
        id="sequential-size-delay"
        head={[t('Rule, read every day', 'Regla, leída cada día'), t('Share of correct VaRs rejected within 1,000 days', 'Parte de los VaR correctos rechazados en 1.000 días'), t('Median day to detect 3 times the hit rate', 'Día mediano de detección con 3 veces la tasa'), t('Median day to detect 4 times the hit rate', 'Día mediano de detección con 4 veces la tasa')]}
        rows={[
          [t('E-process of the rate', 'Proceso e de la tasa'), t('1.8%', '1,8 %'), '244', '129'],
          [t('Battery (rate and clustering)', 'Batería (tasa y agrupamiento)'), t('1.3%', '1,3 %'), '299', '156'],
          [t('Kupiec, trailing 250 days', 'Kupiec, últimos 250 días'), t('66.5%', '66,5 %'), '250', '250'],
          [t('Kupiec, all days so far', 'Kupiec, todos los días hasta hoy'), t('33.8%', '33,8 %'), '114', '68'],
          [t('Traffic light', 'Semáforo'), t('58.7%', '58,7 %'), '250', '250'],
          [t('Independence, trailing 250 days', 'Independencia, últimos 250 días'), t('7.6%', '7,6 %'), '-', '-'],
        ]}
      />
      <P
        en={<>On a correct VaR the e-process rejects 1.8% of the series, against a bound of 6.5% (5% plus three standard errors), where Kupiec rejects 66.5% on the trailing window and 33.8% on all the days so far, and the traffic light leaves green in 58.7%. Kupiec&apos;s test on all the days so far is the fastest to detect (114 and 68 days), but that speed is bought with its 33.8% false alarms. The e-process detects a hit rate 3 and 4 times too high at a median of 244 and 129 days, against 250 for the light and the trailing test, which is their first possible day, so the margin at three times is small. The same question for a PD, with five grades of 0.5% to 10%, 2,000 obligors each per year and ten years, with every PD multiplied by a factor, gives the same shape with a larger price: on a correct PD the e-process rejects 0.0% (product) and 0.7% (average) of the books where the chi-square across grades read every year rejects 20.1%; at a factor of 1.05 the chi-square read once at year 10 detects 68% and the e-process 4.4% at best (average); at 1.1 the chi-square detects every book and the e-process 24.7% (product) and 60.0% (average); from 1.25 the e-process detects every book, in two years.</>}
        es={<>Sobre un VaR correcto el proceso e rechaza 1,8 % de las series, contra una cota de 6,5 % (5 % más tres errores estándar), donde Kupiec rechaza 66,5 % con la ventana móvil y 33,8 % con todos los días hasta hoy, y el semáforo sale del verde en 58,7 %. La prueba de Kupiec sobre todos los días hasta hoy es la más rápida en detectar (114 y 68 días), pero esa rapidez se compra con sus 33,8 % de falsas alarmas. El proceso e detecta una tasa de excepciones 3 y 4 veces demasiado alta en una mediana de 244 y 129 días, contra 250 del semáforo y de la prueba con ventana móvil, que es su primer día posible, así que el margen con 3 veces es pequeño. La misma pregunta para una PD, con cinco grados de 0,5 % a 10 %, 2.000 deudores cada uno por año y diez años, con cada PD multiplicada por un factor, da la misma forma con un precio mayor: sobre una PD correcta el proceso e rechaza 0,0 % (producto) y 0,7 % (promedio) de las carteras donde el chi-cuadrado entre grados leído cada año rechaza 20,1 %; con un factor de 1,05 el chi-cuadrado leído una vez en el año 10 detecta 68 % y el proceso e 4,4 % como mucho (promedio); con 1,1 el chi-cuadrado detecta todas las carteras y el proceso e 24,7 % (producto) y 60,0 % (promedio); desde 1,25 el proceso e detecta todas las carteras, en dos años.</>}
      />
      <P
        en={<>On the real windows of case C11, with the 18 models of the ladder at 1%: in equity 2007 to 2009 (504 days) the e-process flags all 18 at a median of day 24 and the traffic light all 18 at day 250, the first day it can speak; in the euro in 2008 (251 days) the e-process flags 9 models at a median of day 68 and the light 11 at day 250. In the case C03 vintages of SBA loans (the vintages of a cohort are the grades and the ages of 12 to 60 months the steps, the upper direction, the average over vintages) the cohorts of 2006 to 2007 and 2008 to 2010 are rejected at the first age, 12 months, with a log E that reaches 11,631 and 6,363; the cohorts of 2011 to 2014 and 2015 to 2017, which the model over-predicts, fall far below zero and are never rejected, and the 2018 to 2020 cohort peaks at a log E of 2.4, under the threshold of 3.0 (log 20).</>}
        es={<>En las ventanas reales del caso C11, con los 18 modelos de la escalera al 1 %: en la renta variable 2007 a 2009 (504 días) el proceso e marca los 18 en una mediana del día 24 y el semáforo los 18 el día 250, el primer día en que puede hablar; en el euro en 2008 (251 días) el proceso e marca 9 modelos en una mediana del día 68 y el semáforo 11 el día 250. En las cosechas de préstamos SBA del caso C03 (las cosechas de una cohorte son los grados y las edades de 12 a 60 meses los pasos, la dirección superior, el promedio entre cosechas) las cohortes de 2006 a 2007 y de 2008 a 2010 se rechazan en la primera edad, 12 meses, con un log E que llega a 11.631 y 6.363; las cohortes de 2011 a 2014 y de 2015 a 2017, que el modelo sobrepredice, caen muy bajo cero y nunca se rechazan, y la cohorte de 2018 a 2020 alcanza un máximo de log E de 2,4, bajo el umbral de 3,0 (log 20).</>}
      />
      <Figure
        caption={t(
          'The share of correct VaRs each rule rejects within 1,000 days when it is read every day (the size column of the table above), against the 6.5% bound (5% plus three standard errors): the e-process and the battery stay far under it, the fixed-window tests read every day do not.',
          'La parte de los VaR correctos que cada regla rechaza en 1.000 días cuando se lee cada día (la columna de tamaño de la tabla de arriba), contra la cota de 6,5 % (5 % más tres errores estándar): el proceso e y la batería quedan muy bajo ella, las pruebas de ventana fija leídas cada día no.',
        )}
      >
        <GroupedBars
          groups={[
            { en: 'E-process|of the rate', es: 'Proceso e|de la tasa' },
            { en: 'Battery', es: 'Batería' },
            { en: 'Kupiec|250 days', es: 'Kupiec|250 días' },
            { en: 'Kupiec|all days', es: 'Kupiec|todos los días' },
            { en: 'Traffic|light', es: 'Semáforo' },
            { en: 'Independence|250 days', es: 'Independencia|250 días' },
          ]}
          series={[{ id: 'size', label: { en: 'Share of correct VaRs rejected', es: 'Parte de VaR correctos rechazados' }, token: '--color-accent', values: [1.8, 1.3, 66.5, 33.8, 58.7, 7.6] }]}
          axis={{ min: 0, max: 80, decimals: 1, tickDecimals: 0, percent: true, title: { en: 'Rejected within 1,000 days', es: 'Rechazados en 1.000 días' } }}
          reference={{ value: 6.5, label: { en: 'Size bound', es: 'Cota de tamaño' } }}
          label={{ en: 'Bars of the share of correct VaRs that six rules reject within 1,000 days, against the 6.5 percent size bound', es: 'Barras de la parte de VaR correctos que seis reglas rechazan en 1.000 días, contra la cota de tamaño de 6,5 por ciento' }}
        />
      </Figure>
      <h3>{t('Where it fails', 'Dónde falla')}</h3>
      <Callout variant="honest" title={t('The claim as stated fails on power', 'La afirmación tal como se enunció falla en potencia')}>
        <T
          en={<>The claim, fixed before any run, has three parts. Size holds: 1.8% against the 6.5% bound. Delay holds: median days of 244 and 129 against the light&apos;s 250. The power cost does not hold: one Kupiec reading at 250 days has 62.2% power against 50.3% for the e-process at three times the hit rate, a loss of 11.9 points where the rule allowed 10 (at four times the cost is 8.9 points). So the claim as stated fails, it is reported that way, and the monitors were not retuned. One qualification belongs beside that number: the single Kupiec reading is not a clean 5% test, since the committed study has it rejecting 10.35% of correct series at 250 days, so part of its power is size. The price is larger for a small PD error (60.0% at best at a factor of 1.1, where one chi-square detects every book), and for clustering the repeated independence test is faster, at a size of 7.6%. The comparison with the traffic light on the real windows favours the e-process by construction, since the light reads nothing before day 250; on the euro in 2008 the e-process misses two models the light flags (caviar-sav and caviar-es, 5 exceptions in 251 days, exactly the amber threshold, which is not enough evidence for a bet at 20 to 1).</>}
          es={<>La afirmación, fijada antes de toda corrida, tiene tres partes. El tamaño se cumple: 1,8 % contra la cota de 6,5 %. La demora se cumple: días medianos de 244 y 129 contra el 250 del semáforo. El costo de potencia no se cumple: una lectura de Kupiec a 250 días tiene 62,2 % de potencia contra 50,3 % del proceso e con 3 veces la tasa de excepciones, una pérdida de 11,9 puntos donde la regla admitía 10 (con 4 veces el costo es de 8,9 puntos). Así que la afirmación tal como se enunció falla, se informa así, y los monitores no se reajustaron. Una salvedad va junto a ese número: la lectura única de Kupiec no es una prueba limpia de 5 %, pues el estudio versionado la hace rechazar 10,35 % de las series correctas a los 250 días, así que parte de su potencia es tamaño. El precio es mayor para un error pequeño de PD (60,0 % como mucho con un factor de 1,1, donde un solo chi-cuadrado detecta todas las carteras), y para el agrupamiento la prueba de independencia repetida es más rápida, con un tamaño de 7,6 %. La comparación con el semáforo en las ventanas reales favorece al proceso e por construcción, pues el semáforo no lee nada antes del día 250; en el euro en 2008 el proceso e pierde dos modelos que el semáforo marca (caviar-sav y caviar-es, 5 excepciones en 251 días, justo el umbral ámbar, que no es evidencia suficiente para una apuesta de 20 a 1).</>}
        />
      </Callout>
      <P
        en={<>The null of the monitors is binomial with no asset correlation, like the binomial test beside them, so a rejection says the counts are too high for independent defaults, not that the model is wrong by that much; a correlated portfolio would be over-rejected, and the Vasicek-corrected tests exist for that reason. The product of grades also assumes independent grades, and the average is the one to prefer under cross-grade dependence. The e-process is conservative (1.8% against 5%), which is the mixture and the discrete jumps of a rare event, not a defect. The C03 run is an illustration on the committed curves, with two to four vintages per cohort, not a validation of power.</>}
        es={<>La nula de los monitores es binomial sin correlación de activos, igual que la prueba binomial a su lado, así que un rechazo dice que los conteos son demasiado altos para incumplimientos independientes, no que el modelo yerre en tanto; una cartera correlacionada sería rechazada en exceso, y las pruebas corregidas de Vasicek existen por eso. El producto de grados supone además grados independientes, y el promedio es el que se prefiere bajo dependencia entre grados. El proceso e es conservador (1,8 % contra 5 %), lo que se debe a la mezcla y a los saltos discretos de un evento raro, no es un defecto. La corrida de C03 es una ilustración sobre las curvas versionadas, con dos a cuatro cosechas por cohorte, no una validación de potencia.</>}
      />
      <P
        en={<>The notebook that runs this method on the product&apos;s data, from one correct VaR read three ways to the case&apos;s claim and the real windows: <a href={`${NB}/en/${NB_PATH}`}><code>notebooks/en/{NB_PATH}</code></a>. The engine page: <Ref>docs/sequential/README.md</Ref> of riskvalidation 1.1.0; the traffic light is <Cite id="mar32" /> and <Cite id="bcbs22" />.</>}
        es={<>El notebook que corre este método con los datos del producto, desde un VaR correcto leído de tres formas hasta la afirmación del caso y las ventanas reales: <a href={`${NB}/es/${NB_PATH}`}><code>notebooks/es/{NB_PATH}</code></a>. La página del motor: <Ref>docs/sequential/README.md</Ref> de riskvalidation 1.1.0; el semáforo es <Cite id="mar32" /> y <Cite id="bcbs22" />.</>}
      />
    </DocSection>
  );
}

export const methodologySection: MethodologySection = {
  id: 'sequential-monitors',
  group: 'market',
  order: 210,
  title: { en: 'Sequential monitors', es: 'Monitores secuenciales' },
  Body,
};
