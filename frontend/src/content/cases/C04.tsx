// The deep write-up of case C04, transcribed from docs/design/features/c04-transitions/design.md, Contraste research
// dossier 13 (read at the primary sources on 2026-10-06 and 2026-10-07) and riskvalidation 0.04.000's docs/transitions
// pages (estimators, embedding and EM, Markov tests, intervals and mobility, the TTC portfolio). The Context view shows
// it under the sources; the measured results are C04Results, written from the bake.
import { Cite, Equation } from '@fasl-work/caos-app-shell';
import { L, P, useT } from '../bi';

export function C04WriteUp() {
  const t = useT();
  return (
    <>
      <h3>{t('The question', 'La pregunta')}</h3>
      <P
        en={<>A migration matrix turns the agencies' published rating histories into PDs by grade, lifetime PDs and stress-test projections. The EBA lets a through-the-cycle grade's PD be estimated with "migration matrices for the purpose of estimating long-run average default rates covering the full historical observation period" and asks that the rating philosophy be analysed through migrations and yearly default rates <Cite id="ebagl201716" />. Each use rests on choices a model owner seldom shows: which default definition, what happens to a rating withdrawn during the year, which estimator, and whether the chain is Markov and the same every year. The case measures those choices on the agencies' own statistics, as ESMA publishes them <Cite id="cerep" />, and their consequences on a generator whose truth is known.</>}
        es={<>Una matriz de migración convierte las historias de calificación publicadas por las agencias en PD por grado, PD de vida y proyecciones de pruebas de tensión. La EBA permite estimar la PD de un grado a lo largo del ciclo con "matrices de migración para estimar tasas de incumplimiento promedio de largo plazo que cubren todo el período histórico de observación" y pide analizar la filosofía de calificación a través de las migraciones y de las tasas anuales de incumplimiento <Cite id="ebagl201716" />. Cada uso descansa en elecciones que el dueño del modelo rara vez muestra: qué definición de incumplimiento, qué pasa con una calificación retirada durante el año, qué estimador, y si la cadena es de Markov y la misma cada año. El caso mide esas elecciones en las estadísticas de las propias agencias, como las publica ESMA <Cite id="cerep" />, y sus consecuencias en un generador cuya verdad se conoce.</>}
      />
      <h3>{t('What CEREP counts', 'Lo que cuenta CEREP')}</h3>
      <P
        en={<>CEREP publishes aggregates only, built on "a stock concept model, so that intra-period rating activity is derived from a comparison of ratings at the beginning and the end of a period" <Cite id="cerephelp" />: cohorts, never transition times, so the cohort estimator is the only one its data allow. Three of its pages count defaults, each differently, and ESMA warns that "no deterministic definition of a default event has been set up. Therefore, the definitions might differ for various CRAs".</>}
        es={<>CEREP publica solo agregados, construidos sobre "un modelo de concepto de stock, de modo que la actividad de calificación dentro del período se deriva de comparar las calificaciones al inicio y al final de un período" <Cite id="cerephelp" />: cohortes, nunca tiempos de transición, así que el estimador de cohortes es el único que sus datos permiten. Tres de sus páginas cuentan incumplimientos, cada una de otra forma, y ESMA advierte que "no se ha establecido una definición determinista de un evento de incumplimiento. Por lo tanto, las definiciones pueden diferir entre agencias".</>}
      />
      <L
        items={[
          { en: <><strong>D2</strong>, the default-rate page: the distinct ratings of the beginning cohort with at least one default event, over the cohort "regardless of whether they include a default or not". A rating withdrawn after defaulting still counts, as EBA paragraph 76 asks of an obligor whose obligations were closed during the year.</>, es: <><strong>D2</strong>, la página de tasas de incumplimiento: las calificaciones distintas de la cohorte inicial con al menos un evento de incumplimiento, sobre la cohorte "incluyan o no un incumplimiento". Una calificación retirada después de incumplir sigue contando, como pide el párrafo 76 de la EBA para un deudor cuyas obligaciones se cerraron durante el año.</> },
          { en: <><strong>D3</strong>, the defaults-by-category page: every default event, "all default events will be counted", by the category at the start; the EBA counts each defaulted obligor once (paragraph 77), and CEREP counts ratings, not obligors.</>, es: <><strong>D3</strong>, la página de incumplimientos por categoría: cada evento de incumplimiento, "se contarán todos los eventos de incumplimiento", por la categoría al inicio; la EBA cuenta una vez a cada deudor incumplido (párrafo 77), y CEREP cuenta calificaciones, no deudores.</> },
          { en: <><strong>D4</strong>, the transition page: the ratings in a default category at the end of the period, over the cohort less its withdrawals. "If the rating is withdrawn at the end of the statistics period, it is included in the 'Withdrawals' column", whatever happened before: a rating that defaulted and was withdrawn is not a default here. Moody's transition page has no default category at all. <strong>Keep</strong> is the same column over the whole cohort, the withdrawals kept in the denominator.</>, es: <><strong>D4</strong>, la página de transiciones: las calificaciones en una categoría de incumplimiento al final del período, sobre la cohorte menos sus retiros. "Si la calificación se retira al final del período estadístico, se incluye en la columna de retiros", pase lo que haya pasado antes: una calificación que incumplió y fue retirada no es un incumplimiento aquí. La página de transiciones de Moody's no tiene categoría de incumplimiento. <strong>Keep</strong> es la misma columna sobre toda la cohorte, con los retiros en el denominador.</> },
        ]}
      />
      <P
        en={<>The industry's standard treatment of withdrawals removes them and "treats transitions to NR as non-informative" <Cite id="schuermannhanson2004" />; the EBA keeps the obligor in the denominator. Which definition a PD follows is therefore part of the PD, and the case reports every one beside the others.</>}
        es={<>El tratamiento estándar de la industria para los retiros los elimina y "trata las transiciones a NR como no informativas" <Cite id="schuermannhanson2004" />; la EBA mantiene al deudor en el denominador. Qué definición sigue una PD es por lo tanto parte de la PD, y el caso informa cada una junto a las demás.</>}
      />
      <h3>{t('The chain and its estimators', 'La cadena y sus estimadores')}</h3>
      <P
        en={<>A rating is modelled as a Markov chain on the grades with default absorbing. Pooled over the cohorts, the maximum likelihood estimate of a stationary chain's one-year matrix is the cohort estimator <Cite id="andersongoodman1957" />:</>}
        es={<>Una calificación se modela como una cadena de Markov sobre los grados con el incumplimiento absorbente. Agrupado sobre las cohortes, el estimador de máxima verosimilitud de la matriz anual de una cadena estacionaria es el estimador de cohortes <Cite id="andersongoodman1957" />:</>}
      />
      <Equation
        tex={String.raw`\hat p_{ij} = \frac{\sum_t n_{ij}(t)}{\sum_t \sum_k n_{ik}(t)}`}
        caption={t(
          'Anderson and Goodman (1957), equation (2.8): the moves from grade i to j summed over the cohorts, over the ratings that started in i. A cell never observed is zero, even where the chain reaches it through other grades.',
          'Anderson y Goodman (1957), ecuación (2.8): los movimientos del grado i al j sumados sobre las cohortes, sobre las calificaciones que partieron en i. Una celda nunca observada es cero, aunque la cadena la alcance a través de otros grados.',
        )}
      />
      <P
        en={<>With the transition times known, the generator Q of a continuous-time chain is estimated by its jumps over its holding times, the duration estimator <Cite id="landoskodeberg2002" />, and every horizon follows as P(t) = exp(tQ). CEREP's snapshots hold no times; for them the expectation-maximisation algorithm reaches the maximum likelihood generator of the counts, with a closed-form expectation step <Cite id="smithdosreis2018" />:</>}
        es={<>Con los tiempos de transición conocidos, el generador Q de una cadena en tiempo continuo se estima por sus saltos sobre sus tiempos de permanencia, el estimador de duración <Cite id="landoskodeberg2002" />, y cada horizonte sigue como P(t) = exp(tQ). Las instantáneas de CEREP no tienen tiempos; para ellas el algoritmo de esperanza-maximización alcanza el generador de máxima verosimilitud de los conteos, con un paso de esperanza en forma cerrada <Cite id="smithdosreis2018" />:</>}
      />
      <Equation
        tex={String.raw`\hat q_{ij} = \frac{K_{ij}}{S_i}, \qquad q'_{ij} = \frac{\mathbb{E}_Q\left[K_{ij}(t) \mid y\right]}{\mathbb{E}_Q\left[S_i(t) \mid y\right]}`}
        caption={t(
          'The duration estimator (K the jumps from i to j, S the time spent in i) and the EM update for snapshots y (Smith and dos Reis 2018, equation 2.3, after Bladt and Sørensen 2005): the expected jumps and holding times given the snapshots replace the unobserved ones.',
          'El estimador de duración (K los saltos de i a j, S el tiempo en i) y la actualización EM para instantáneas y (Smith y dos Reis 2018, ecuación 2.3, según Bladt y Sørensen 2005): los saltos y tiempos de permanencia esperados dadas las instantáneas reemplazan a los no observados.',
        )}
      />
      <h3>{t('The embedding problem', 'El problema de inclusión')}</h3>
      <P
        en={<>Not every one-year matrix comes from a generator. When the eigenvalues of P stay within the unit circle around 1, the logarithm's series converges to a matrix with zero row sums and exp(Q̃) = P exactly, but Q̃ may hold negative off-diagonal entries; the diagonal adjustment sets them to zero and returns their mass to the diagonal, the weighted adjustment spreads it over the row <Cite id="israel2001" />. No exact generator exists if det P ≤ 0, if det P exceeds the product of the diagonal, or if a grade is reachable from another while the move between them was never observed (Theorem 3).</>}
        es={<>No toda matriz anual proviene de un generador. Cuando los valores propios de P quedan dentro del círculo unitario en torno a 1, la serie del logaritmo converge a una matriz con filas que suman cero y exp(Q̃) = P exactamente, pero Q̃ puede tener elementos negativos fuera de la diagonal; el ajuste diagonal los lleva a cero y devuelve su masa a la diagonal, el ajuste ponderado la reparte en la fila <Cite id="israel2001" />. No existe un generador exacto si det P ≤ 0, si det P supera el producto de la diagonal, o si un grado es alcanzable desde otro mientras el movimiento entre ellos nunca se observó (Teorema 3).</>}
      />
      <Equation
        tex={String.raw`\tilde Q = \sum_{k \ge 1} \frac{(-1)^{k+1}}{k} (P - I)^k, \qquad S = \max_{a + bi \,\in\, \mathrm{eig}(P)} \left[(a - 1)^2 + b^2\right] < 1; \qquad q^{JLT}_{ii} = \log p_{ii}, \quad q^{JLT}_{ij} = \frac{p_{ij} \log p_{ii}}{p_{ii} - 1}`}
        caption={t(
          'Israel, Rosenthal and Wei (2001): the series (1), which converges when S < 1 (Theorem 1), and the approximation of Jarrow, Lando and Turnbull, equation (3), which allows one move a year at most. Each generator is judged by the L1 distance of exp(Q) to P.',
          'Israel, Rosenthal y Wei (2001): la serie (1), que converge cuando S < 1 (Teorema 1), y la aproximación de Jarrow, Lando y Turnbull, ecuación (3), que admite a lo más un movimiento al año. Cada generador se juzga por la distancia L1 de exp(Q) a P.',
        )}
      />
      <h3>{t('Is the chain Markov and the same every year?', '¿Es la cadena de Markov y la misma cada año?')}</h3>
      <P
        en={<>Each cohort's rows behave as independent multinomial samples, so the classical tests apply <Cite id="andersongoodman1957" />. Time homogeneity compares every year's matrix with the pooled one; the order test asks whether the grade before last matters, which needs three consecutive ratings of the same obligor, so it runs on the generator's paths; a matrix is tested against a reference with the likelihood ratio. Momentum, the tendency of a recently downgraded obligor to be downgraded again, is tested with a hazard whose coefficient c is zero for a Markov chain <Cite id="dosreis2020" />. The ECB's migration statistics (the weighted bandwidths above and below the diagonal, and the z-tests of each move against the initial matrix) are computed for every cohort <Cite id="ecb2019" />.</>}
        es={<>Las filas de cada cohorte se comportan como muestras multinomiales independientes, así que se aplican las pruebas clásicas <Cite id="andersongoodman1957" />. La homogeneidad temporal compara la matriz de cada año con la agrupada; la prueba de orden pregunta si importa el grado anterior al último, lo que exige tres calificaciones consecutivas del mismo deudor, así que corre sobre las trayectorias del generador; una matriz se prueba contra una de referencia con la razón de verosimilitud. El momentum, la tendencia de un deudor recién rebajado a ser rebajado otra vez, se prueba con un riesgo cuyo coeficiente c es cero en una cadena de Markov <Cite id="dosreis2020" />. Las estadísticas de migración del BCE (los anchos de banda ponderados sobre y bajo la diagonal, y las pruebas z de cada movimiento contra la matriz inicial) se calculan para cada cohorte <Cite id="ecb2019" />.</>}
      />
      <Equation
        tex={String.raw`\chi^2 = \sum_{t} \sum_{i,j} n_i(t - 1) \frac{\left[\hat p_{ij}(t) - \hat p_{ij}\right]^2}{\hat p_{ij}} \sim \chi^2_{(T - 1)\, m (m - 1)}, \qquad \lambda_{in}(t) = q_i(t)\, e^{c Z_n(t)}`}
        caption={t(
          'Time homogeneity, the chi-square form (Anderson and Goodman 3.6 and 3.8), which keeps its size where the likelihood ratio over-rejects on these sizes (measured in riskvalidation); and the momentum hazard (dos Reis, Pfeuffer and Smith, section 4.1), Z the indicator of a downgrade into the current grade, with H0: c = 0.',
          'Homogeneidad temporal, la forma chi-cuadrado (Anderson y Goodman 3.6 y 3.8), que mantiene su tamaño donde la razón de verosimilitud rechaza de más en estos tamaños (medido en riskvalidation); y el riesgo de momentum (dos Reis, Pfeuffer y Smith, sección 4.1), Z el indicador de una rebaja al grado actual, con H0: c = 0.',
        )}
      />
      <h3>{t('Intervals for a PD by grade', 'Intervalos para una PD por grado')}</h3>
      <P
        en={<>A PD by grade is a ratio of rare events. The Wald interval assumes independent draws and "will likely be too tight"; the Agresti-Coull interval adds κ²/2 defaults and κ² trials; the Jeffreys interval takes the quantiles of a Beta(D + ½, N − D + ½) <Cite id="brown2001" />. Default correlation shrinks the information in N obligors to an effective number <Cite id="schuermannhanson2004" />, and the investment grades' PDs cannot be told apart at the notch level, while the speculative grades' can.</>}
        es={<>Una PD por grado es una razón de eventos raros. El intervalo de Wald supone extracciones independientes y "probablemente será demasiado estrecho"; el de Agresti-Coull agrega κ²/2 incumplimientos y κ² ensayos; el de Jeffreys toma los cuantiles de una Beta(D + ½, N − D + ½) <Cite id="brown2001" />. La correlación de incumplimientos reduce la información de N deudores a un número efectivo <Cite id="schuermannhanson2004" />, y las PD de los grados de inversión no se distinguen a nivel de escalón, mientras las de los grados especulativos sí.</>}
      />
      <Equation
        tex={String.raw`\widehat{PD}_R \pm \kappa \sqrt{\frac{\widehat{PD}_R \left(1 - \widehat{PD}_R\right)}{N^*_R}}, \qquad N^\dagger_R = \left[\frac{1}{N_R} + \frac{2}{N_R^2} \sum_{i < j} \sqrt{N_{i,R} N_{j,R}}\, \rho_{ij}\right]^{-1}`}
        caption={t(
          'The Wald interval (Schuermann and Hanson 2.2) and the effective number of observations under default correlation (3.4, after Miao and Gastwirth 2004): with one trial per obligor and one ρ, N† = N / (1 + (N − 1)ρ), so 531 obligors at ρ = 1% count as 84.',
          'El intervalo de Wald (Schuermann y Hanson 2.2) y el número efectivo de observaciones con correlación de incumplimientos (3.4, según Miao y Gastwirth 2004): con un ensayo por deudor y un solo ρ, N† = N / (1 + (N − 1)ρ), así que 531 deudores con ρ = 1% cuentan como 84.',
        )}
      />
      <h3>{t('What a projection inherits from its matrix', 'Lo que una proyección hereda de su matriz')}</h3>
      <P
        en={<>A stress test propagates a portfolio with a migration matrix, writing defaulted balances off and re-originating them with a fixed mix. If the performing block of the matrix is primitive and nothing originates into default, the matrix has a through-the-cycle portfolio of its own, and every starting portfolio drifts towards it "independent of the stress imposed to the model" <Cite id="engelmann2024" />: the projected default rate moves with no scenario at all when the bank's portfolio is not that one.</>}
        es={<>Una prueba de tensión propaga una cartera con una matriz de migración, castigando los saldos incumplidos y reoriginándolos con una mezcla fija. Si el bloque de grados vigentes de la matriz es primitivo y nada se origina en incumplimiento, la matriz tiene una cartera a lo largo del ciclo propia, y toda cartera inicial deriva hacia ella "independientemente del estrés impuesto al modelo" <Cite id="engelmann2024" />: la tasa de incumplimiento proyectada se mueve sin escenario alguno cuando la cartera del banco no es esa.</>}
      />
      <Equation
        tex={String.raw`W'_t = W'_{t-1}\, T\, I_w + \left(W'_{t-1}\, T\, V_w\right) O', \qquad W'_{ttc} = W'_{ttc}\, T\, I_w + \left(W'_{ttc}\, T\, V_w\right) O'`}
        caption={t(
          'Engelmann (2024), equations (9) and (10): I_w the identity with its last diagonal entry zero (the write-off), V_w the default column, O the origination mix; Theorem 1 gives the unique TTC portfolio, reached from any start.',
          'Engelmann (2024), ecuaciones (9) y (10): I_w la identidad con su último elemento diagonal en cero (el castigo), V_w la columna de incumplimiento, O la mezcla de originación; el Teorema 1 da la única cartera TTC, alcanzada desde cualquier inicio.',
        )}
      />
      <h3>{t('Limits', 'Límites')}</h3>
      <L
        items={[
          { en: 'CEREP holds the statistics of the agencies\' EU entities as ESMA computes them, not the agencies\' own studies; every figure names the entity, the scope (corporate, long-term, categories), the horizon and the definition.', es: 'CEREP contiene las estadísticas de las entidades UE de las agencias como las calcula ESMA, no los estudios propios de las agencias; cada cifra nombra la entidad, el alcance (corporativo, largo plazo, categorías), el horizonte y la definición.' },
          { en: 'Agency PDs by grade are not a bank\'s PDs, and a matrix estimated here is not a supervisory parameter.', es: 'Las PD por grado de las agencias no son las PD de un banco, y una matriz estimada aquí no es un parámetro supervisor.' },
          { en: 'A Markov fit that passes on one-year aggregates says nothing about paths CEREP does not publish: order and momentum are measured on the generator, where the paths exist.', es: 'Un ajuste de Markov que pasa en agregados anuales no dice nada de trayectorias que CEREP no publica: el orden y el momentum se miden en el generador, donde las trayectorias existen.' },
          { en: 'The papers\' agency matrices (Israel et al.\'s S&P and Moody\'s, Engelmann\'s example) are read from the device data root and never enter an artifact; the case publishes the distances and portfolios recomputed from them.', es: 'Las matrices de agencias de los artículos (las de S&P y Moody\'s de Israel et al., el ejemplo de Engelmann) se leen desde la raíz de datos del dispositivo y nunca entran a un artefacto; el caso publica las distancias y carteras recalculadas desde ellas.' },
        ]}
      />
    </>
  );
}
