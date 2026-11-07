// The Methodology section on the adaptive conformal recalibration of the VaR (case C11): a wrapper that moves the tail level
// a VaR model is asked for after every day, so that the coverage a back-test asks for is restored in a stress window without
// the model's FZ0 score worsening. Transcribed from the engine page docs/market/08_conformal-recalibration.md of riskvalidation
// 1.1.0 (the method, the decisions D-1 to D-3 and the limits) and from notebook 09 of the market-risk topic
// (notebooks/en/07-market-risk/09-adaptive-conformal-recalibration-of-the-var.ipynb), whose numbers are read from the committed
// C11 documents and from the generator of the engine's study (seed 20261030); the numbers of the tables are the notebook's
// printed outputs, which the C11 documents reproduce. Every display equation carries a caption that defines its symbols. The
// figure draws the table of the phases of the crisis beside it. The registry mounts it as one tab of the market group.
import { Callout, Cite, DocSection, Figure } from '@fasl-work/caos-app-shell';
import type { ReactNode } from 'react';
import { Equation, P, Ref, T, useT } from '../../content/bi';
import type { MethodologySection } from '../methodologyRegistry';
import { GroupedBars } from '../MethodFigures';

const NB = 'https://github.com/fsantibanezleal/CAOS_Contraste/blob/main/notebooks';
const NB_PATH = '07-market-risk/09-adaptive-conformal-recalibration-of-the-var.ipynb';

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
      title={{ en: 'Adaptive conformal recalibration of the VaR', es: 'Recalibración conforme adaptativa del VaR' }}
      refs={['gibbscandes2021', 'kupiec1995', 'christoffersen1998', 'patton2019']}
    >
      <P
        en={<>A VaR model that falls behind a crisis keeps asking the same tail level of a distribution that has moved. The proposed method wraps the model and moves the level it is asked for. The wrapper keeps a working tail level a<sub>t</sub>, which starts at the target α, asks the model for its VaR at a<sub>t</sub> and, after the day, lowers the level when the day was an exception and raises it a little when it was not. The update is the adaptive conformal inference of Gibbs and Candes <Cite id="gibbscandes2021" />. Conformal layers on VaR forecasts exist in working papers; what the engine adds is the wrapper as a tested function that takes any forecaster, and its comparison, wrapped against unwrapped, on the same back-tests and the same score as the rest of case C11: the Kupiec test <Cite id="kupiec1995" />, the conditional coverage test of Christoffersen <Cite id="christoffersen1998" /> and the FZ0 score <Cite id="patton2019" />. The forecast for day t uses only the returns before t, the model is not touched, and the expected shortfall is the model&apos;s own tail mean at the working level.</>}
        es={<>Un modelo de VaR que se queda atrás en una crisis sigue pidiendo el mismo nivel de cola a una distribución que se movió. El método propuesto envuelve el modelo y mueve el nivel que se le pide. El envoltorio mantiene un nivel de trabajo a<sub>t</sub>, que parte en el objetivo α, le pide al modelo su VaR en a<sub>t</sub> y, después del día, baja el nivel cuando el día fue una excepción y lo sube un poco cuando no lo fue. La actualización es la inferencia conforme adaptativa de Gibbs y Candes <Cite id="gibbscandes2021" />. Las capas conformes sobre pronósticos de VaR existen en documentos de trabajo; lo que el motor agrega es el envoltorio como función probada que recibe cualquier pronosticador, y su comparación, envuelto frente a sin envolver, con las mismas pruebas retrospectivas y el mismo puntaje que el resto del caso C11: la prueba de Kupiec <Cite id="kupiec1995" />, la prueba de cobertura condicional de Christoffersen <Cite id="christoffersen1998" /> y el puntaje FZ0 <Cite id="patton2019" />. El pronóstico del día t usa solo los retornos anteriores a t, el modelo no se toca, y la pérdida esperada es la media de cola del propio modelo en el nivel de trabajo.</>}
      />
      <Equation
        tex={String.raw`a_{t+1} = \min\!\Big(\max\big(a_t + \gamma\,(\alpha - \mathrm{err}_t),\ a_{\min}\big),\ a_{\max}\Big), \qquad \mathrm{err}_t = \mathbb{1}\{\,y_t < \mathrm{VaR}_t(a_t)\,\}`}
        caption={<T en={<>The level update (Gibbs and Candes 2021): a<sub>t</sub> the working tail level on day t, α the target level (0.01 or 0.025), γ the step (0.005, fixed before any run and never tuned), y<sub>t</sub> the return of day t, VaR<sub>t</sub>(a) the model&apos;s VaR at level a from the returns before t, err<sub>t</sub> equal to 1 when day t is an exception and 0 otherwise, and [a<sub>min</sub>, a<sub>max</sub>] = [0.001, 0.25] the band the level is held in. An exception lowers the level by γ(1 - α) and a quiet day raises it by γα.</>} es={<>La actualización del nivel (Gibbs y Candes 2021): a<sub>t</sub> el nivel de cola de trabajo del día t, α el nivel objetivo (0,01 o 0,025), γ el paso (0,005, fijado antes de toda corrida y nunca ajustado), y<sub>t</sub> el retorno del día t, VaR<sub>t</sub>(a) el VaR del modelo en el nivel a con los retornos anteriores a t, err<sub>t</sub> igual a 1 cuando el día t es una excepción y 0 en otro caso, y [a<sub>min</sub>, a<sub>max</sub>] = [0,001; 0,25] la banda en que se mantiene el nivel. Una excepción baja el nivel en γ(1 - α) y un día sin excepción lo sube en γα.</>} />}
      />
      <P
        en={<>At 1% a quiet day adds 0.005 percentage points to the level and an exception takes 0.495 away, so one exception needs 99 quiet days to be undone: the level reacts at once to a cluster of exceptions and relaxes slowly. For the unclipped recursion Gibbs and Candes prove a long-run guarantee, with nothing about the independence of the exceptions.</>}
        es={<>Al 1 % un día sin excepción suma 0,005 puntos porcentuales al nivel y una excepción le quita 0,495, así que deshacer una excepción toma 99 días sin excepción: el nivel reacciona de inmediato a un grupo de excepciones y se relaja lento. Para la recursión sin acotar, Gibbs y Candes prueban una garantía de largo plazo, sin nada sobre la independencia de las excepciones.</>}
      />
      <Equation
        tex={String.raw`\Big|\,\frac{1}{T}\sum_{t=1}^{T}\mathrm{err}_t - \alpha\,\Big| \;\le\; \frac{\max(a_1,\,1-a_1) + \gamma}{\gamma\,T}`}
        caption={<T en={<>The guarantee of Gibbs and Candes for the unclipped recursion and any order of the data: T the number of days, a<sub>1</sub> the first working level, and the other symbols as above. With γ = 0.005 and a<sub>1</sub> = 0.01 the right side is 0.796 over 250 days, 0.395 over the 504 days of equity 2007 to 2009, 0.080 over 2,500 days and 0.005 only over 39,800 days: inside a stress window it allows any exception rate from 0 to about 40%, so the effect of the wrapper there is measured, not promised.</>} es={<>La garantía de Gibbs y Candes para la recursión sin acotar y cualquier orden de los datos: T el número de días, a<sub>1</sub> el primer nivel de trabajo, y los demás símbolos como arriba. Con γ = 0,005 y a<sub>1</sub> = 0,01 el lado derecho vale 0,796 en 250 días, 0,395 en los 504 días de la renta variable 2007 a 2009, 0,080 en 2.500 días y 0,005 solo en 39.800 días: dentro de una ventana de estrés admite cualquier tasa de excepciones de 0 a cerca de 40 %, así que el efecto del envoltorio allí se mide, no se promete.</>} />}
      />
      <P
        en={<>The decisions that bound the method are three. The working level is held inside the band after each update, which the paper does not do, so the guarantee holds only while the level stays in the band and the number of clipped days is reported. No conformal guarantee is claimed for the expected shortfall. A rounding excess of the expected shortfall over the VaR of one unit in the last place is set equal to the VaR, and a larger excess or a non-finite forecast is refused.</>}
        es={<>Las decisiones que acotan el método son tres. El nivel de trabajo se mantiene dentro de la banda tras cada actualización, lo que el artículo no hace, así que la garantía vale solo mientras el nivel esté en la banda y se informa el número de días recortados. No se reclama garantía conforme para la pérdida esperada. Un exceso de redondeo de la pérdida esperada sobre el VaR de una unidad en el último lugar se iguala al VaR, y un exceso mayor o un pronóstico no finito se rechaza.</>}
      />
      <Equation
        tex={String.raw`\Delta_{\mathrm{FZ0}} = \frac{\overline{L}_{\mathrm{FZ0}}^{\,w} - \overline{L}_{\mathrm{FZ0}}^{\,u}}{\big|\overline{L}_{\mathrm{FZ0}}^{\,u}\big|}`}
        caption={<T en={<>The cost of the wrapper in the score: the mean FZ0 loss of the wrapped forecasts (w) minus that of the unwrapped ones (u), over the absolute value of the latter; a positive change is worse. The claim allows at most +5%.</>} es={<>El costo del envoltorio en el puntaje: la pérdida FZ0 media de los pronósticos envueltos (w) menos la de los sin envolver (u), sobre el valor absoluto de esta última; un cambio positivo es peor. La afirmación admite a lo más +5 %.</>} />}
      />
      <h3>{t('What it is compared against and what it measured', 'Con qué se compara y qué midió')}</h3>
      <P
        en={<>The comparison is each model of the ladder as it runs, at a fixed level, against the same model wrapped: historical simulation over 250 days (HS-250), GARCH-t and filtered historical simulation (FHS), at the 1% and 2.5% levels, in the three stress windows of C11 (equity 2007 to 2009, equity 2020, rates 2022). The claim was fixed before any run: wrapped, the three pass the Kupiec and conditional coverage tests (both p at least 0.05) in at least one more of the three windows than unwrapped, with the mean FZ0 worsening by no more than 5%; it is refuted if a wrapped model fails the independence test in equity 2007 to 2009. A pass is counted per model, level and window, 18 runs in all.</>}
        es={<>La comparación es cada modelo de la escalera tal como corre, en un nivel fijo, frente al mismo modelo envuelto: simulación histórica de 250 días (HS-250), GARCH-t y simulación histórica filtrada (FHS), en los niveles de 1 % y 2,5 %, en las tres ventanas de estrés de C11 (renta variable 2007 a 2009, renta variable 2020, tasas 2022). La afirmación se fijó antes de toda corrida: envueltos, los tres pasan las pruebas de Kupiec y de cobertura condicional (ambas con p de al menos 0,05) en al menos una ventana más de las tres que sin envolver, con el FZ0 medio empeorando no más de 5 %; se refuta si un modelo envuelto falla la prueba de independencia en la renta variable 2007 a 2009. Un paso se cuenta por modelo, nivel y ventana, 18 corridas en total.</>}
      />
      <Tbl
        id="conformal-stress"
        head={[t('Model and level', 'Modelo y nivel'), t('Windows passed, unwrapped / wrapped', 'Ventanas pasadas, sin envolver / envuelto'), t('Worst FZ0 change', 'Peor cambio de FZ0'), t('Wrapped independence p, equity 2007 to 2009', 'p de independencia envuelto, renta variable 2007 a 2009')]}
        rows={[
          [t('HS-250, 1%', 'HS-250, 1 %'), '0 / 1', t('-5.8%', '-5,8 %'), t('0.483', '0,483')],
          [t('HS-250, 2.5%', 'HS-250, 2,5 %'), '0 / 2', t('-3.3%', '-3,3 %'), t('0.275', '0,275')],
          [t('GARCH-t, 1%', 'GARCH-t, 1 %'), '2 / 3', t('+3.0%', '+3,0 %'), t('0.703', '0,703')],
          [t('GARCH-t, 2.5%', 'GARCH-t, 2,5 %'), '1 / 3', t('-0.3%', '-0,3 %'), t('0.371', '0,371')],
          [t('FHS, 1%', 'FHS, 1 %'), '2 / 3', t('+3.4%', '+3,4 %'), t('0.657', '0,657')],
          [t('FHS, 2.5%', 'FHS, 2,5 %'), '1 / 3', t('+1.5%', '+1,5 %'), t('0.371', '0,371')],
        ]}
      />
      <P
        en={<>Unwrapped, the six model-and-level cells pass 6 of their 18 stress runs; wrapped, 15, so the wrapped models gain 9 passes, and the claim holds in 6 of 6 cells with the worst FZ0 change at +3.4% (FHS at 1%), inside the 5% allowed. The wrapped independence p-values in equity 2007 to 2009 run from 0.275 to 0.703, so the refutation condition does not occur. In rates 2022 the wrapper halves the exceptions of HS-250 (8 to 4 at 1%, 14 to 8 at 2.5%) and improves its FZ0 by 5.8% and 3.3%. On GARCH-t at 1% in equity 2007 to 2009 the unwrapped model has 16 exceptions in 504 days against 5.04 expected and the wrapped one 6.</>}
        es={<>Sin envolver, las seis celdas de modelo y nivel pasan 6 de sus 18 corridas de estrés; envueltas, 15, así que los modelos envueltos ganan 9 pasos, y la afirmación se cumple en 6 de 6 celdas con el peor cambio de FZ0 en +3,4 % (FHS al 1 %), dentro del 5 % admitido. Los valores p de independencia envueltos en la renta variable 2007 a 2009 van de 0,275 a 0,703, así que la condición de refutación no ocurre. En tasas 2022 el envoltorio reduce a la mitad las excepciones de HS-250 (de 8 a 4 al 1 %, de 14 a 8 al 2,5 %) y mejora su FZ0 en 5,8 % y 3,3 %. En GARCH-t al 1 % en la renta variable 2007 a 2009 el modelo sin envolver tiene 16 excepciones en 504 días contra 5,04 esperadas y el envuelto 6.</>}
      />
      <P
        en={<>A real window has one path and no known VaR, so the notebook also runs a generator whose true VaR is known: a Student-t(5) GARCH(1,1) after a calm history of 1,000 days, then 500 days whose volatility ramps to three times, holds and decays to 1.5 times. Over thirty paths (seed 20261030) the true probability that a forecast is hit, which only a generator can give, falls for HS-250 from 2.40% to 1.37% and its pass rate rises from 0.23 to 0.83 with a median FZ0 change of -8.5%; for GARCH-t the probability falls from 1.73% to 1.15% and the pass rate rises from 0.60 to 0.97, with a median change of -0.2%. The engine&apos;s own study, with 100 paths per scenario, measures pass rates of 0.18 to 0.87 for HS-250 at 1% and 0.44 to 0.97 for GARCH-t at 1% in the same persistent-crisis scenario.</>}
        es={<>Una ventana real tiene una trayectoria y ningún VaR conocido, así que el notebook corre además un generador cuyo VaR verdadero se conoce: un GARCH(1,1) con t de Student(5) tras una historia calma de 1.000 días, y luego 500 días cuya volatilidad sube a tres veces, se mantiene y decae a 1,5 veces. Sobre treinta trayectorias (semilla 20261030) la probabilidad verdadera de que un pronóstico sea superado, que solo un generador puede dar, baja para HS-250 de 2,40 % a 1,37 % y su tasa de aprobación sube de 0,23 a 0,83 con un cambio mediano de FZ0 de -8,5 %; para GARCH-t la probabilidad baja de 1,73 % a 1,15 % y la tasa de aprobación sube de 0,60 a 0,97, con un cambio mediano de -0,2 %. El estudio propio del motor, con 100 trayectorias por escenario, mide tasas de aprobación de 0,18 a 0,87 para HS-250 al 1 % y de 0,44 a 0,97 para GARCH-t al 1 % en el mismo escenario de crisis persistente.</>}
      />
      <h3>{t('Where it fails', 'Dónde falla')}</h3>
      <Tbl
        id="conformal-phases"
        head={[t('True probability of a hit, by phase of the crisis', 'Probabilidad verdadera de ser superado, por fase de la crisis'), t('Ramp', 'Subida'), t('Plateau', 'Meseta'), t('Decay', 'Decaimiento')]}
        rows={[
          [t('HS-250, unwrapped / wrapped', 'HS-250, sin envolver / envuelto'), t('3.43% / 1.90%', '3,43 % / 1,90 %'), t('2.25% / 1.25%', '2,25 % / 1,25 %'), t('0.79% / 0.57%', '0,79 % / 0,57 %')],
          [t('GARCH-t, unwrapped / wrapped', 'GARCH-t, sin envolver / envuelto'), t('1.78% / 1.33%', '1,78 % / 1,33 %'), t('1.90% / 1.13%', '1,90 % / 1,13 %'), t('1.55% / 0.88%', '1,55 % / 0,88 %')],
        ]}
      />
      <Figure
        caption={t(
          'The true probability that a forecast is hit, by phase of the crisis, for HS-250 and GARCH-t unwrapped and wrapped (thirty paths of the generator with a known VaR, seed 20261030; the table above), against the 1% target: the wrapper brings the ramp and the plateau toward the target and, in the decay, takes both models under it.',
          'La probabilidad verdadera de que un pronóstico sea superado, por fase de la crisis, para HS-250 y GARCH-t sin envolver y envueltos (treinta trayectorias del generador de VaR conocido, semilla 20261030; la tabla de arriba), contra el objetivo de 1 %: el envoltorio acerca la subida y la meseta al objetivo y, en el decaimiento, deja ambos modelos bajo él.',
        )}
      >
        <GroupedBars
          groups={[
            { en: 'HS-250|ramp', es: 'HS-250|subida' },
            { en: 'HS-250|plateau', es: 'HS-250|meseta' },
            { en: 'HS-250|decay', es: 'HS-250|decaimiento' },
            { en: 'GARCH-t|ramp', es: 'GARCH-t|subida' },
            { en: 'GARCH-t|plateau', es: 'GARCH-t|meseta' },
            { en: 'GARCH-t|decay', es: 'GARCH-t|decaimiento' },
          ]}
          series={[
            { id: 'unwrapped', label: { en: 'Unwrapped', es: 'Sin envolver' }, token: '--color-magenta', values: [3.43, 2.25, 0.79, 1.78, 1.9, 1.55] },
            { id: 'wrapped', label: { en: 'Wrapped', es: 'Envuelto' }, token: '--color-good', values: [1.9, 1.25, 0.57, 1.33, 1.13, 0.88] },
          ]}
          axis={{ min: 0, max: 4, decimals: 2, percent: true, tickDecimals: 0, title: { en: 'Probability of a hit', es: 'Probabilidad de ser superado' } }}
          reference={{ value: 1, label: { en: 'Target', es: 'Objetivo' } }}
          label={{ en: 'Grouped bars of the true probability of a hit by phase of the crisis, unwrapped and wrapped, for two models, against the 1 percent target', es: 'Barras agrupadas de la probabilidad verdadera de ser superado por fase de la crisis, sin envolver y envuelto, para dos modelos, contra el objetivo de 1 por ciento' }}
        />
      </Figure>
      <P
        en={<>The wrapper corrects the level a model gets wrong on average and does not tell the phases apart. In the decay both models fall below the 1% target, because the level recovers by only 0.005 points a day and a crisis level is kept for months after the crisis; there it makes an already conservative model more conservative. The wrapped HS-250 still fails equity 2020 at both levels: the wrapper narrows a crash it does not see coming, it does not remove it. On the first generator path HS-250 wrapped still has 10 exceptions in 500 days (Kupiec p 0.048) and a true hit probability of 2.27% against 3.66% unwrapped, above the target, and no step brings it to the target: 3.08%, 2.83%, 2.27%, 2.08% and 2.32% at steps of 0.001, 0.002, 0.005, 0.01 and 0.02. The engine page adds that the wrapper repairs coverage, not clustering, and that in the crash-decay scenario, a 100-day window dominated by a transient, the wrapped HS-250 pass rate is only 0.60 at 1% and 0.73 at 2.5%.</>}
        es={<>El envoltorio corrige el nivel que un modelo yerra en promedio y no distingue las fases. En el decaimiento los dos modelos caen bajo el objetivo de 1 %, porque el nivel se recupera solo 0,005 puntos por día y un nivel de crisis se conserva durante meses tras la crisis; allí vuelve más conservador a un modelo que ya lo era. HS-250 envuelto sigue fallando la renta variable 2020 en ambos niveles: el envoltorio estrecha una caída que no ve venir, no la elimina. En la primera trayectoria del generador HS-250 envuelto aún tiene 10 excepciones en 500 días (p de Kupiec 0,048) y una probabilidad verdadera de ser superado de 2,27 % contra 3,66 % sin envolver, sobre el objetivo, y ningún paso lo lleva al objetivo: 3,08 %, 2,83 %, 2,27 %, 2,08 % y 2,32 % con pasos de 0,001, 0,002, 0,005, 0,01 y 0,02. La página del motor agrega que el envoltorio repara la cobertura, no el agrupamiento, y que en el escenario de caída con decaimiento, una ventana de 100 días dominada por un transitorio, la tasa de aprobación de HS-250 envuelto es solo 0,60 al 1 % y 0,73 al 2,5 %.</>}
      />
      <P
        en={<>The counts of windows passed overstate the repair, and the paper that tests the wrapper measures by how much. The update holds the hit count near its target, so the count is less variable than a binomial count (a standard deviation of 0.37 to 0.70 times the binomial one in the generators), and the Kupiec and conditional coverage tests accept it too easily: a correct model passes in 99.8% of simulated runs of 500 days when wrapped against 92.6% unwrapped at 1%, and in 99.5% against 92.9% at 2.5%. On the ten models the wrapped runs pass 45 of 60 model, level and window cells against 17, but with each count tested against its own null, on coverage alone, 35 against 12; and the claim as stated for HS-250, GARCH-t and FHS, which holds in all six cells with the engine&apos;s tests, holds in five of them on coverage alone (FHS at 1% falls). What survives is the movement of the hit rate toward the target (the mean distance falls from 4.02 to 1.83 points on the ten models) and a score change of at most +4.3%; the delta-normal model gains no window at 1%, the expected shortfall stays understated (mean Z<sub>2</sub> -1.91 wrapped against -3.52), and a rolling split-conformal scale passes as many cells with 10 of them over the score tolerance.</>}
        es={<>Los conteos de ventanas aprobadas exageran la reparación, y el artículo que prueba el envoltorio mide cuánto. La actualización mantiene el conteo de excepciones cerca de su objetivo, así que el conteo es menos variable que uno binomial (una desviación estándar de 0,37 a 0,70 veces la binomial en los generadores), y las pruebas de Kupiec y de cobertura condicional lo aceptan con demasiada facilidad: un modelo correcto pasa en 99,8 % de las corridas simuladas de 500 días cuando está envuelto contra 92,6 % sin envolver al 1 %, y en 99,5 % contra 92,9 % al 2,5 %. En los diez modelos las corridas envueltas pasan 45 de 60 celdas de modelo, nivel y ventana contra 17, pero con cada conteo puesto a prueba contra su propia nula, solo en cobertura, 35 contra 12; y la afirmación tal como se enunció para HS-250, GARCH-t y FHS, que se cumple en las seis celdas con las pruebas del motor, se cumple en cinco solo en cobertura (FHS al 1 % cae). Lo que sobrevive es el movimiento de la tasa de excepciones hacia el objetivo (la distancia media baja de 4,02 a 1,83 puntos en los diez modelos) y un cambio de puntaje de a lo más +4,3 %; el modelo delta-normal no gana ninguna ventana al 1 %, la pérdida esperada sigue subestimada (Z<sub>2</sub> medio -1,91 envuelto contra -3,52), y una escala conforme dividida móvil aprueba tantas celdas con 10 de ellas sobre la tolerancia de puntaje.</>}
      />
      <Callout variant="honest" title={t('What is measured, what is a guarantee and what is not', 'Qué se midió, qué es una garantía y qué no')}>
        <T
          en={<>The long-run guarantee is on the frequency of exceptions, not on the expected shortfall, and over a window of a few hundred days it gives no usable bound; every effect shown here is measured. The windows are one realised path each, two of them of 104 and 64 days with a handful of exceptions, and the p-values are asymptotic, so Kupiec&apos;s small-count caution applies at 1%. The step γ is a free parameter fixed at the Gibbs and Candes default and not tuned on these windows. The forecaster must not read day t or later, which the wrapper cannot check. A level pinned at the lower edge of the band is reported in the clipped-days count, not hidden. The engine page&apos;s offline run refits GARCH-t and FHS every fifth forecast day while the C11 documents refit daily, so its table differs from the one above by a few tenths (for instance +3.6% against +3.4% for FHS at 1%); the table above reads the C11 documents. The wrapper is an engine method, not a recommendation to a bank, and no supervisor recognises it.</>}
          es={<>La garantía de largo plazo es sobre la frecuencia de excepciones, no sobre la pérdida esperada, y en una ventana de pocos cientos de días no da una cota útil; todo efecto mostrado aquí se midió. Las ventanas son una trayectoria realizada cada una, dos de ellas de 104 y 64 días con un puñado de excepciones, y los valores p son asintóticos, así que la cautela de Kupiec con conteos pequeños rige al 1 %. El paso γ es un parámetro libre fijado en el valor por defecto de Gibbs y Candes y no ajustado con estas ventanas. El pronosticador no debe leer el día t ni los siguientes, lo que el envoltorio no puede verificar. Un nivel pegado al borde inferior de la banda se informa en el conteo de días recortados, no se oculta. La corrida fuera de línea de la página del motor reajusta GARCH-t y FHS cada cinco días de pronóstico mientras los documentos de C11 reajustan a diario, así que su tabla difiere de la de arriba en unas décimas (por ejemplo +3,6 % contra +3,4 % para FHS al 1 %); la tabla de arriba lee los documentos de C11. El envoltorio es un método del motor, no una recomendación a un banco, y ningún supervisor lo reconoce.</>}
        />
      </Callout>
      <P
        en={<>The notebook that runs this method on the product&apos;s data, from the update by hand to the thirty-path study and the claim: <a href={`${NB}/en/${NB_PATH}`}><code>notebooks/en/{NB_PATH}</code></a>. The engine page: <Ref>docs/market/08_conformal-recalibration.md</Ref> of riskvalidation 1.1.0.</>}
        es={<>El notebook que corre este método con los datos del producto, desde la actualización a mano hasta el estudio de treinta trayectorias y la afirmación: <a href={`${NB}/es/${NB_PATH}`}><code>notebooks/es/{NB_PATH}</code></a>. La página del motor: <Ref>docs/market/08_conformal-recalibration.md</Ref> de riskvalidation 1.1.0.</>}
      />
    </DocSection>
  );
}

export const methodologySection: MethodologySection = {
  id: 'conformal-var',
  group: 'market',
  order: 150,
  title: { en: 'Adaptive conformal recalibration of the VaR', es: 'Recalibración conforme adaptativa del VaR' },
  Body,
};
