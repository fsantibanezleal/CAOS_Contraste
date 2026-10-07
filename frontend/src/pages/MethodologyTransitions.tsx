// The Methodology's two rating-transition parts (case C04), transcribed from research dossier 13 (sections 1 to 9, 14
// and 16, read at the primary sources on 2026-10-06 and 2026-10-07) and riskvalidation 0.04.000's docs/transitions
// pages. Every display equation carries a caption that defines its symbols; every section ends with its references.
import { Cite, DocSection, Equation } from '@fasl-work/caos-app-shell';
import { L, P, useT } from '../content/bi';

/** The models part: the chain, its estimators, the embedding problem, mobility and the TTC portfolio. */
export function Migrations() {
  const t = useT();
  return (
    <>
      <DocSection title={{ en: 'The rating process as a Markov chain', es: 'El proceso de calificación como cadena de Markov' }} refs={['andersongoodman1957', 'cerephelp']}>
        <P
          en={<>A rating moves among m states, the grades and default, which is absorbing. Observed in cohorts, the ratings in grade i at the start of a period and their states at its end, the chain is estimated by counting: n_ij(t) ratings moved from i to j in period t. If the matrix is the same every period, its maximum likelihood estimate pools the periods; if not, each period has its own <Cite id="andersongoodman1957" />. Each row behaves as an independent multinomial sample of the size of its cohort, which is what makes the classical tests apply. ESMA's CEREP publishes exactly these cohorts and nothing finer: "a stock concept model, so that intra-period rating activity is derived from a comparison of ratings at the beginning and the end of a period" <Cite id="cerephelp" />.</>}
          es={<>Una calificación se mueve entre m estados, los grados y el incumplimiento, que es absorbente. Observada en cohortes, las calificaciones en el grado i al inicio de un período y sus estados al final, la cadena se estima contando: n_ij(t) calificaciones pasaron de i a j en el período t. Si la matriz es la misma en cada período, su estimador de máxima verosimilitud agrupa los períodos; si no, cada período tiene la suya <Cite id="andersongoodman1957" />. Cada fila se comporta como una muestra multinomial independiente del tamaño de su cohorte, y eso permite aplicar las pruebas clásicas. CEREP de ESMA publica exactamente estas cohortes y nada más fino: "un modelo de concepto de stock, de modo que la actividad de calificación dentro del período se deriva de comparar las calificaciones al inicio y al final de un período" <Cite id="cerephelp" />.</>}
        />
        <Equation
          tex={String.raw`\hat p_{ij} = \frac{\sum_{t=1}^{T} n_{ij}(t)}{\sum_{t=1}^{T} \sum_{k} n_{ik}(t)} \quad (2.8), \qquad \hat p_{ij}(t) = \frac{n_{ij}(t)}{n_i(t - 1)} \quad (2.9)`}
          caption={t(
            'Anderson and Goodman (1957): the stationary estimate pools the T periods (2.8); the period estimate (2.9) divides by n_i(t − 1), the ratings in i at the start of period t. A move never observed has an estimate of exactly zero.',
            'Anderson y Goodman (1957): el estimador estacionario agrupa los T períodos (2.8); el del período (2.9) divide por n_i(t − 1), las calificaciones en i al inicio del período t. Un movimiento nunca observado tiene un estimador exactamente cero.',
          )}
        />
      </DocSection>
      <DocSection title={{ en: 'Withdrawals and the default definition', es: 'Los retiros y la definición de incumplimiento' }} refs={['schuermannhanson2004', 'ebagl201716', 'cerephelp']}>
        <P
          en={<>A rating withdrawn during the period has no end state. The method that "has emerged as an industry standard treats transitions to NR as non-informative": the withdrawn ratings leave the cohort and their probability is spread over the other states in proportion <Cite id="schuermannhanson2004" />. The EBA's default rate keeps an obligor in the denominator "where the corresponding credit obligations were sold, written off, repaid or otherwise closed during the observation period", and asks institutions to analyse whether such closures bias the rate <Cite id="ebagl201716" />. CEREP holds both views: its default-rate page counts the distinct defaulted ratings over the whole cohort, its transition page puts a rating withdrawn by the end in its withdrawals column whatever happened before <Cite id="cerephelp" />. On S&P's EU entity the transition page's default column holds 10 of the 101 CCC to C defaults of 2024 (Contraste's measurement, dossier 13 section 16).</>}
          es={<>Una calificación retirada durante el período no tiene estado final. El método que "se ha convertido en estándar de la industria trata las transiciones a NR como no informativas": las calificaciones retiradas salen de la cohorte y su probabilidad se reparte entre los demás estados en proporción <Cite id="schuermannhanson2004" />. La tasa de incumplimiento de la EBA mantiene al deudor en el denominador "cuando las obligaciones crediticias correspondientes se vendieron, castigaron, pagaron o cerraron de otro modo durante el período de observación", y pide a las instituciones analizar si esos cierres sesgan la tasa <Cite id="ebagl201716" />. CEREP contiene ambas visiones: su página de tasas de incumplimiento cuenta las calificaciones incumplidas distintas sobre toda la cohorte, su página de transiciones pone una calificación retirada al final en su columna de retiros pase lo que haya pasado antes <Cite id="cerephelp" />. En la entidad UE de S&P la columna de incumplimiento de la página de transiciones contiene 10 de los 101 incumplimientos de CCC a C de 2024 (medición de Contraste, dossier 13 sección 16).</>}
        />
      </DocSection>
      <DocSection title={{ en: 'Duration and the generator', es: 'Duración y el generador' }} refs={['landoskodeberg2002', 'schuermannhanson2004', 'smithdosreis2018']}>
        <P
          en={<>In continuous time the chain has a generator Q: off-diagonal intensities q_ij ≥ 0, rows summing to zero, and P(t) = exp(tQ) at every horizon. With the transition dates known, its maximum likelihood estimate divides the jumps by the time spent in the starting grade <Cite id="smithdosreis2018" />, the duration estimator <Cite id="landoskodeberg2002" />. It sees rare moves the cohort cannot: on S&P's US ratings of 1981 to 2002 no AAA, AA+ or AA rating defaulted within a year, "the cohort estimate is identically equal to zero, in contrast to the duration estimate where PD_AAA = 0.02bp, PD_AA+ = 0.05bp and PD_AA = 0.71bp" <Cite id="schuermannhanson2004" />.</>}
          es={<>En tiempo continuo la cadena tiene un generador Q: intensidades fuera de la diagonal q_ij ≥ 0, filas que suman cero, y P(t) = exp(tQ) en todo horizonte. Con las fechas de transición conocidas, su estimador de máxima verosimilitud divide los saltos por el tiempo pasado en el grado de partida <Cite id="smithdosreis2018" />, el estimador de duración <Cite id="landoskodeberg2002" />. Ve movimientos raros que la cohorte no ve: en las calificaciones de S&P de EE. UU. de 1981 a 2002 ninguna calificación AAA, AA+ o AA incumplió dentro de un año, "la estimación de cohorte es idénticamente cero, en contraste con la estimación de duración donde PD_AAA = 0,02pb, PD_AA+ = 0,05pb y PD_AA = 0,71pb" <Cite id="schuermannhanson2004" />.</>}
        />
        <Equation
          tex={String.raw`L_t(Q) = \exp\Big(\sum_i \Big[\sum_{j \ne i} K_{ij}(t) \log q_{ij} - S_i(t) \sum_{j \ne i} q_{ij}\Big]\Big), \qquad \hat q_{ij} = \frac{K_{ij}(t)}{S_i(t)}, \qquad P(t) = e^{tQ}`}
          caption={t(
            'The likelihood of a fully observed path (Smith and dos Reis 2018, after Küchler and Sørensen): K_ij(t) the jumps from i to j up to t, S_i(t) the time spent in i; its maximiser is the duration estimator.',
            'La verosimilitud de una trayectoria observada completa (Smith y dos Reis 2018, según Küchler y Sørensen): K_ij(t) los saltos de i a j hasta t, S_i(t) el tiempo pasado en i; su maximizador es el estimador de duración.',
          )}
        />
      </DocSection>
      <DocSection title={{ en: 'A generator from snapshots: EM', es: 'Un generador desde instantáneas: EM' }} refs={['smithdosreis2018']}>
        <P
          en={<>Snapshots hide the jumps and the holding times. The expectation-maximisation algorithm replaces them with their expectations given the snapshots and the current Q, and updates Q as their ratio; the expectations have a closed form through block matrix exponentials, so the maximum likelihood generator of CEREP's annual count matrices is computable without any path. Smith and dos Reis find it "outperforms other known algorithms in several metrics, in particular, with much less overestimation of probabilities of default in higher ratings" <Cite id="smithdosreis2018" />; C04 measures that claim on a generator whose truth is known.</>}
          es={<>Las instantáneas ocultan los saltos y los tiempos de permanencia. El algoritmo de esperanza-maximización los reemplaza por sus esperanzas dadas las instantáneas y el Q actual, y actualiza Q como su cociente; las esperanzas tienen forma cerrada mediante exponenciales de matrices por bloques, así que el generador de máxima verosimilitud de las matrices de conteos anuales de CEREP se calcula sin trayectoria alguna. Smith y dos Reis encuentran que "supera a otros algoritmos conocidos en varias métricas, en particular, con mucha menos sobreestimación de las probabilidades de incumplimiento en las calificaciones altas" <Cite id="smithdosreis2018" />; C04 mide esa afirmación en un generador cuya verdad se conoce.</>}
        />
        <Equation
          tex={String.raw`q'_{ij} = \frac{\mathbb{E}_Q[K_{ij} \mid y]}{\mathbb{E}_Q[S_i \mid y]}, \qquad \mathbb{E}_Q[K_{ij} \mid y] = \sum_s \frac{\big(e^{C^{(ij)}_{\gamma} \Delta_s}\big)_{y_s,\, h + y_{s+1}}}{\big(e^{Q \Delta_s}\big)_{y_s,\, y_{s+1}}}, \qquad C^{(ij)}_{\gamma} = \begin{pmatrix} Q & q_{ij}\, e_i e_j^{\top} \\ 0 & Q \end{pmatrix}`}
          caption={t(
            'The EM update (2.3) and its E-step (Proposition 2.4, after Van Loan 1978): y_s the state at snapshot s, Δ_s the time to the next one, h the number of states; E[S_i | y] is the same with the block e_i e_i^T. For aggregated counts n_ab the sums are weighted by n_ab.',
            'La actualización EM (2.3) y su paso E (proposición 2.4, según Van Loan 1978): y_s el estado en la instantánea s, Δ_s el tiempo hasta la siguiente, h el número de estados; E[S_i | y] es igual con el bloque e_i e_i^T. Para conteos agregados n_ab las sumas se ponderan por n_ab.',
          )}
        />
      </DocSection>
      <DocSection title={{ en: 'The embedding problem', es: 'El problema de inclusión' }} refs={['israel2001']}>
        <P
          en={<>A one-year matrix P need not be the exponential of any generator. When every eigenvalue a + bi of P has (a − 1)² + b² below 1, the logarithm's series converges and gives Q̃ with exp(Q̃) = P exactly (Theorem 1); if every p_ii exceeds ½ the condition holds and P has at most one generator (Theorem 2). Q̃ may still have negative off-diagonal entries: the diagonal adjustment sets them to zero and adds them back to the diagonal (2), the weighted adjustment spreads them over the row in proportion (2′); neither keeps exp(Q) = P. No generator exists at all if det P ≤ 0, if det P exceeds the product of the diagonal, or if a state j is reachable from i while p_ij = 0 (Theorem 3), the condition all three of the paper's published matrices fail <Cite id="israel2001" />.</>}
          es={<>Una matriz anual P no tiene por qué ser la exponencial de algún generador. Cuando todo valor propio a + bi de P cumple (a − 1)² + b² bajo 1, la serie del logaritmo converge y da Q̃ con exp(Q̃) = P exactamente (Teorema 1); si todo p_ii supera ½ la condición se cumple y P tiene a lo más un generador (Teorema 2). Q̃ aún puede tener elementos negativos fuera de la diagonal: el ajuste diagonal los lleva a cero y los suma a la diagonal (2), el ajuste ponderado los reparte en la fila en proporción (2′); ninguno conserva exp(Q) = P. No existe generador alguno si det P ≤ 0, si det P supera el producto de la diagonal, o si un estado j es alcanzable desde i mientras p_ij = 0 (Teorema 3), la condición que no cumplen las tres matrices publicadas del artículo <Cite id="israel2001" />.</>}
        />
        <Equation
          tex={String.raw`q_{ij} = \max(\tilde q_{ij}, 0)\ (j \ne i), \quad q_{ii} = \tilde q_{ii} + \sum_{j \ne i} \min(\tilde q_{ij}, 0) \quad (2); \qquad \sum_{j \ge k} q_{ij} \ge \sum_{j \ge k} q_{i+1, j}\ \ (k \ne i + 1)`}
          caption={t(
            'The diagonal adjustment (2), and the stochastic monotonicity of a generator (Lemma 1, after Jarrow, Lando and Turnbull 1997): equivalent to the tail sums of exp(tQ) being nondecreasing in the starting grade, so a worse grade is never more likely to end better. The JLT approximation violates it on the paper\'s first matrix (0.9949 against 0.9885).',
            'El ajuste diagonal (2), y la monotonicidad estocástica de un generador (lema 1, según Jarrow, Lando y Turnbull 1997): equivale a que las sumas de cola de exp(tQ) no decrezcan con el grado de partida, de modo que un grado peor nunca tenga más probabilidad de terminar mejor. La aproximación JLT la viola en la primera matriz del artículo (0,9949 contra 0,9885).',
          )}
        />
        <P
          en="Contraste reproduces eight of the paper's nine published distances to the printed six digits; the ninth (the first matrix's JLT distance, 0.116900) follows only from the paper's printed four-digit generator, not from equation (3) on the printed matrix (0.116477)."
          es="Contraste reproduce ocho de las nueve distancias publicadas del artículo a los seis dígitos impresos; la novena (la distancia JLT de la primera matriz, 0,116900) resulta solo del generador impreso a cuatro dígitos del artículo, no de la ecuación (3) sobre la matriz impresa (0,116477)."
        />
      </DocSection>
      <DocSection title={{ en: 'Mobility', es: 'Movilidad' }} refs={['jafryschuermann2004']}>
        <P
          en={<>Jafry and Schuermann subtract the identity, take the singular values of the result and average them, "a metric which has an intuitively-appealing size related to the average probability of migration", chosen to be sensitive to where the off-diagonal mass sits <Cite id="jafryschuermann2004" />. The trace index, (n − tr P)/(n − 1), is the classical comparator that ignores where it sits. Contraste measured what M_SVD does not do: it is not a distance in notches (moving 0.1 of the mass one notch or five along a cycle of seven grades gives the same singular values); it does tell concentrated from spread migration at an equal trace index.</>}
          es={<>Jafry y Schuermann restan la identidad, toman los valores singulares del resultado y los promedian, "una métrica con un tamaño intuitivamente atractivo, relacionado con la probabilidad promedio de migración", elegida por ser sensible a dónde está la masa fuera de la diagonal <Cite id="jafryschuermann2004" />. El índice de traza, (n − tr P)/(n − 1), es el comparador clásico que ignora dónde está. Contraste midió lo que M_SVD no hace: no es una distancia en escalones (mover 0,1 de la masa un escalón o cinco a lo largo de un ciclo de siete grados da los mismos valores singulares); sí distingue la migración concentrada de la dispersa con igual índice de traza.</>}
        />
        <Equation
          tex={String.raw`M_{SVD}(P) = \frac{1}{n} \sum_{i=1}^{n} \sigma_i(P - I), \qquad M_{tr}(P) = \frac{n - \operatorname{tr} P}{n - 1}`}
          caption={t(
            'σ_i the singular values; n the number of states. Both are 0 for the identity (nobody moves); C04 computes them for every annual cohort of an agency, against its speculative-grade default rate.',
            'σ_i los valores singulares; n el número de estados. Ambos son 0 para la identidad (nadie se mueve); C04 los calcula para cada cohorte anual de una agencia, frente a su tasa de incumplimiento especulativa.',
          )}
        />
      </DocSection>
      <DocSection title={{ en: 'The through-the-cycle portfolio a matrix implies', es: 'La cartera a lo largo del ciclo que implica una matriz' }} refs={['engelmann2024']}>
        <P
          en={<>A stress test propagates a portfolio W with a transition matrix T each year, writes the defaulted balance off and re-originates it with a mix O. If the performing block of T is primitive (some power strictly positive) and nothing originates into default, there is a unique portfolio W_ttc that the propagation leaves unchanged, reached from any start: "the current portfolio will have a tendency to propagate towards the through-the-cycle portfolio. This could create unwanted spurious effects on projected portfolio default rates" <Cite id="engelmann2024" />. Contraste reproduces the paper's section 4 (the TTC portfolio to four decimals and its PD of 1.198%), and C04's Impact group projects a reader's portfolio under each agency's matrix to show the drift.</>}
          es={<>Una prueba de tensión propaga una cartera W con una matriz de transición T cada año, castiga el saldo incumplido y lo reorigina con una mezcla O. Si el bloque de grados vigentes de T es primitivo (alguna potencia estrictamente positiva) y nada se origina en incumplimiento, existe una única cartera W_ttc que la propagación deja igual, alcanzada desde cualquier inicio: "la cartera actual tenderá a propagarse hacia la cartera a lo largo del ciclo. Esto podría crear efectos espurios no deseados en las tasas de incumplimiento proyectadas" <Cite id="engelmann2024" />. Contraste reproduce la sección 4 del artículo (la cartera TTC a cuatro decimales y su PD de 1,198%), y el grupo Impacto de C04 proyecta una cartera del lector con la matriz de cada agencia para mostrar la deriva.</>}
        />
        <Equation
          tex={String.raw`W'_t = W'_{t-1}\, T\, I_w + \big(W'_{t-1}\, T\, V_w\big)\, O' \quad (9), \qquad \mathrm{PD}_t = \sum_i w_{t-1, i}\, T_{in}`}
          caption={t(
            'Engelmann (2024): I_w the identity whose last diagonal entry is 0 (the write-off), V_w = (0, …, 0, 1)′ the defaulted balance, O the origination mix (summing to 1); the portfolio PD is the default column weighted by the portfolio. Theorem 1 gives W_ttc as the fixed point of (9).',
            'Engelmann (2024): I_w la identidad cuyo último elemento diagonal es 0 (el castigo), V_w = (0, …, 0, 1)′ el saldo incumplido, O la mezcla de originación (suma 1); la PD de la cartera es la columna de incumplimiento ponderada por la cartera. El Teorema 1 da W_ttc como punto fijo de (9).',
          )}
        />
      </DocSection>
    </>
  );
}

/** The tests part: is the chain Markov and the same every year, the ECB statistics, and intervals for a PD by grade. */
export function TransitionTests() {
  const t = useT();
  return (
    <>
      <DocSection title={{ en: 'Time homogeneity', es: 'Homogeneidad temporal' }} refs={['andersongoodman1957']}>
        <P
          en={<>The hypothesis is that every period has the same matrix. The likelihood ratio compares each period's estimate with the pooled one, and the contingency form sums the squared departures weighted by each row's size; both are chi-square with (T − 1) m (m − 1) degrees of freedom <Cite id="andersongoodman1957" />. Their asymptotics assume every p_ij above zero, and rating tables are sparse: measured on 4,000 known-truth repetitions, the likelihood ratio rejects 7.85% of the time at 5% where the chi-square form keeps 4.85%, so the chi-square is the default (riskvalidation, dossier 13 section 14).</>}
          es={<>La hipótesis es que cada período tiene la misma matriz. La razón de verosimilitud compara la estimación de cada período con la agrupada, y la forma de contingencia suma los desvíos al cuadrado ponderados por el tamaño de cada fila; ambas son chi-cuadrado con (T − 1) m (m − 1) grados de libertad <Cite id="andersongoodman1957" />. Su asintótica supone todo p_ij sobre cero, y las tablas de calificación son ralas: medido en 4.000 repeticiones con verdad conocida, la razón de verosimilitud rechaza el 7,85% de las veces al 5% donde la forma chi-cuadrado mantiene 4,85%, así que la chi-cuadrado es la forma por defecto (riskvalidation, dossier 13 sección 14).</>}
        />
        <Equation
          tex={String.raw`-2 \log \lambda = 2 \sum_t \sum_{i,j} n_{ij}(t) \log \frac{\hat p_{ij}(t)}{\hat p_{ij}} \quad (3.5), \qquad \chi^2 = \sum_i \sum_{t,j} n_i(t - 1) \frac{\big[\hat p_{ij}(t) - \hat p_{ij}\big]^2}{\hat p_{ij}} \quad (3.8)`}
          caption={t(
            'Anderson and Goodman (1957): p̂_ij pooled (2.8), p̂_ij(t) of period t (2.9), n_i(t − 1) the ratings in i at the start of t; under the hypothesis both are chi-square with (T − 1) m (m − 1) degrees of freedom. The absorbing default row carries no information.',
            'Anderson y Goodman (1957): p̂_ij agrupado (2.8), p̂_ij(t) del período t (2.9), n_i(t − 1) las calificaciones en i al inicio de t; bajo la hipótesis ambas son chi-cuadrado con (T − 1) m (m − 1) grados de libertad. La fila absorbente de incumplimiento no aporta información.',
          )}
        />
      </DocSection>
      <DocSection title={{ en: 'Order, a reference matrix, and momentum', es: 'Orden, una matriz de referencia y momentum' }} refs={['andersongoodman1957', 'dosreis2020', 'landoskodeberg2002']}>
        <P
          en={<>The order test asks whether the grade before the last one matters: from the obligors that went from i to j and then to k, the likelihood ratio of the first-order chain against the second has m (m − 1)² degrees of freedom <Cite id="andersongoodman1957" />. It needs each obligor's three consecutive grades, which CEREP's aggregates do not hold, so it runs on the generator's paths; on rating tables the full three-way table is mostly empty, and the default groups the previous and next moves by direction (better, same, worse). A matrix is tested against a reference with the likelihood ratio on its rows. Momentum is the most important departure: "an obligor that has been recently downgraded into a certain rating is more likely to be downgraded further than other obligors currently in that rating" <Cite id="dosreis2020" />. Its test is a hazard whose coefficient c is zero for a Markov chain; on Moody's data dos Reis, Pfeuffer and Smith estimate c = 0.33010 for downgrades (p below 0.0001) and no upward momentum, consistent with Lando and Skødeberg <Cite id="landoskodeberg2002" />.</>}
          es={<>La prueba de orden pregunta si importa el grado anterior al último: desde los deudores que pasaron de i a j y luego a k, la razón de verosimilitud de la cadena de primer orden contra la de segundo tiene m (m − 1)² grados de libertad <Cite id="andersongoodman1957" />. Necesita tres grados consecutivos de cada deudor, que los agregados de CEREP no contienen, así que corre sobre las trayectorias del generador; en tablas de calificación la tabla triple completa está casi vacía, y la forma por defecto agrupa los movimientos anterior y siguiente por dirección (mejor, igual, peor). Una matriz se prueba contra una de referencia con la razón de verosimilitud sobre sus filas. El momentum es el desvío más importante: "un deudor recientemente rebajado a cierta calificación tiene más probabilidad de ser rebajado otra vez que los demás deudores en esa calificación" <Cite id="dosreis2020" />. Su prueba es un riesgo cuyo coeficiente c es cero en una cadena de Markov; con datos de Moody's dos Reis, Pfeuffer y Smith estiman c = 0,33010 para las rebajas (p bajo 0,0001) y ningún momentum al alza, en línea con Lando y Skødeberg <Cite id="landoskodeberg2002" />.</>}
        />
        <Equation
          tex={String.raw`\lambda = \prod_{i,j,k} \Big(\frac{\hat p_{jk}}{\hat p_{ijk}}\Big)^{n_{ijk}} \quad (3.12), \qquad \lambda_{in}(t) = q_i(t)\, e^{c\, Z_n(t)}, \quad H_0: c = 0`}
          caption={t(
            'The order test (Anderson and Goodman 3.12; n_ijk the obligors in i, then j, then k) and the momentum hazard (dos Reis, Pfeuffer and Smith 2020, section 4.1): Z_n(t) is 1 if obligor n was downgraded into its current grade, the baseline q_i(t) is left free, and c is fitted by partial likelihood.',
            'La prueba de orden (Anderson y Goodman 3.12; n_ijk los deudores en i, luego j, luego k) y el riesgo de momentum (dos Reis, Pfeuffer y Smith 2020, sección 4.1): Z_n(t) es 1 si el deudor n fue rebajado a su grado actual, la base q_i(t) queda libre, y c se ajusta por verosimilitud parcial.',
          )}
        />
        <P
          en="Measured on the EM generator of S&P's counts (dossier 13 section 16), the momentum strength alpha 0.125 of dos Reis et al.'s self-exciting model gives a fitted c of 0.336: C04's momentum family plants it, a fifth of it and twice it, and measures what each test sees and what a Markov projection misses."
          es="Medido en el generador EM de los conteos de S&P (dossier 13 sección 16), la fuerza de momentum alfa 0,125 del modelo autoexcitado de dos Reis et al. da un c ajustado de 0,336: la familia de momentum de C04 la planta, junto con un quinto de ella y el doble, y mide lo que ve cada prueba y lo que una proyección de Markov no ve."
        />
      </DocSection>
      <DocSection title={{ en: "The ECB's migration statistics", es: 'Las estadísticas de migración del BCE' }} refs={['ecb2019']}>
        <P
          en={<>The ECB's validation reporting asks for the matrix weighted bandwidths above and below the diagonal (how far the movers move, against the farthest they could) and for z-tests that a cell is not more populated than its neighbour closer to the diagonal <Cite id="ecb2019" />. They attach no threshold; Contraste reports both bandwidths and each cell's p-value, with a Holm adjustment it labels as its own.</>}
          es={<>El reporte de validación del BCE pide los anchos de banda ponderados de la matriz sobre y bajo la diagonal (cuánto se mueven los que se mueven, frente a lo más lejos que podrían) y pruebas z de que una celda no esté más poblada que su vecina más cercana a la diagonal <Cite id="ecb2019" />. No fijan umbral; Contraste informa ambos anchos y el valor p de cada celda, con un ajuste de Holm que identifica como propio.</>}
        />
        <Equation
          tex={String.raw`\mathrm{MWB}_{upper} = \frac{1}{M_u} \sum_{i=1}^{K-1} \sum_{j=i+1}^{K} |i - j|\, N_i\, p_{ij}, \qquad M_u = \sum_{i=1}^{K-1} \max(|i - K|, |i - 1|)\, N_i \sum_{j=i+1}^{K} p_{ij}`}
          caption={t(
            'K grades, N_i the ratings in grade i, p_ij the migration rates; MWB_lower sums below the diagonal with its own M_l. Each lies in [0, 1]: 0 when nobody moves, 1 when every mover jumps as far as its grade allows.',
            'K grados, N_i las calificaciones en el grado i, p_ij las tasas de migración; MWB_lower suma bajo la diagonal con su propio M_l. Cada uno está en [0, 1]: 0 cuando nadie se mueve, 1 cuando todo el que se mueve salta lo más lejos que su grado permite.',
          )}
        />
      </DocSection>
      <DocSection title={{ en: 'Intervals for a PD by grade', es: 'Intervalos para una PD por grado' }} refs={['schuermannhanson2004', 'brown2001']}>
        <P
          en={<>The Wald interval assumes independent draws, which "clearly seems unreasonable as there are likely to be common factors such as the state of the economy which affect all firms", so it "will likely be too tight" <Cite id="schuermannhanson2004" />. The Agresti-Coull interval adds κ²/2 defaults and κ² trials; the Jeffreys interval takes the equal tails of a Beta(D + ½, N − D + ½) <Cite id="brown2001" />. A default correlation ρ shrinks N obligors to an effective number. Exact coverage, by enumeration, of the nominal 95% intervals with one expected default (200 obligors at a PD of 0.5%): Wald 63.25%, Agresti-Coull 98.13%, Jeffreys 98.13%; with twenty (1,000 at 2%): 94.97%, 94.67% and 95.89% (riskvalidation, dossier 13 section 14).</>}
          es={<>El intervalo de Wald supone extracciones independientes, lo que "claramente parece irrazonable, pues probablemente hay factores comunes como el estado de la economía que afectan a todas las empresas", así que "probablemente será demasiado estrecho" <Cite id="schuermannhanson2004" />. El de Agresti-Coull agrega κ²/2 incumplimientos y κ² ensayos; el de Jeffreys toma las colas iguales de una Beta(D + ½, N − D + ½) <Cite id="brown2001" />. Una correlación de incumplimientos ρ reduce N deudores a un número efectivo. Cobertura exacta, por enumeración, de los intervalos nominales al 95% con un incumplimiento esperado (200 deudores con PD de 0,5%): Wald 63,25%, Agresti-Coull 98,13%, Jeffreys 98,13%; con veinte (1.000 al 2%): 94,97%, 94,67% y 95,89% (riskvalidation, dossier 13 sección 14).</>}
        />
        <Equation
          tex={String.raw`\tilde{PD}_R = \frac{N_{R,D} + \kappa^2/2}{N_R + \kappa^2}, \quad \tilde{PD}_R \pm \kappa \sqrt{\frac{\tilde{PD}_R (1 - \tilde{PD}_R)}{N_R + \kappa^2}} \quad (3.2, 3.3), \qquad N^\dagger = \frac{N}{1 + (N - 1)\rho}`}
          caption={t(
            'Agresti-Coull (Schuermann and Hanson 3.2 and 3.3): N_R,D the defaults among N_R obligors in grade R, κ the normal quantile; and the effective number under one default correlation ρ and one trial per obligor (the special case of their 3.4): 531 obligors at ρ = 1% count as 84, and Table 5\'s Wald interval for BB more than doubles.',
            'Agresti-Coull (Schuermann y Hanson 3.2 y 3.3): N_R,D los incumplimientos entre N_R deudores del grado R, κ el cuantil normal; y el número efectivo con una sola correlación de incumplimientos ρ y un ensayo por deudor (el caso particular de su 3.4): 531 deudores con ρ = 1% cuentan como 84, y el intervalo de Wald de BB de la Tabla 5 más que se duplica.',
          )}
        />
        <L
          items={[
            { en: 'Notch-level PDs of the investment grades cannot be told apart at the sizes agencies publish; past the speculative-grade barrier they can (Schuermann and Hanson, abstract). C04 measures how often adjacent grades\' intervals overlap at 50 to 1,000 obligors per grade.', es: 'Las PD por escalón de los grados de inversión no se distinguen con los tamaños que publican las agencias; pasada la barrera del grado especulativo sí (Schuermann y Hanson, resumen). C04 mide cuán a menudo se traslapan los intervalos de grados adyacentes con 50 a 1.000 deudores por grado.' },
            { en: 'A data-driven default correlation needs an estimator from the default-rate series, which the engine does not have yet; C04 offers the correction at a reader\'s ρ.', es: 'Una correlación de incumplimientos basada en datos requiere un estimador desde la serie de tasas de incumplimiento, que el motor aún no tiene; C04 ofrece la corrección con un ρ del lector.' },
          ]}
        />
      </DocSection>
    </>
  );
}
