// What each Methodology topic adds to its text to meet the method area of ADR-0017 section 2.1 (four dense paragraphs,
// two captioned equations, a captioned figure, one honest callout, a reference): the figure, the limit the method has,
// and the paragraphs that tie it to what the cases measured. Every fact below is in the case write-ups of the
// repository (docs/cases/C01.md, C04.md, C22.md) or in the sections that these blocks follow.
import { Callout, Cite, Figure } from '@fasl-work/caos-app-shell';
import { Equation, P, T, useT } from '../content/bi';
import { ChainFigure, HomogeneityFigure, LadderFigure, PowerFigure, PsiFigure, ReliabilityFigure, RocFigure, ScorecardFigure, ShapeFigure } from './DocFigures';

const Limit = ({ title, en, es }: { title: { en: string; es: string }; en: string; es: string }) => (
  <Callout variant="honest" title={<T en={title.en} es={title.es} />}>
    <T en={en} es={es} />
  </Callout>
);

export function ModelRiskExtra() {
  return (
    <>
      <P
        en="A battery changes what a single p-value means. With m tests each run at level α on a correct model, the chance that at least one of them rejects is far above α, so a battery that raises no flag is informative, while one that raises a flag is not, by itself, a defect. Contraste therefore reports every test with its p-value and its light under the reader's policy, and a finding is raised from the tests it cites and their severity, never from a single light."
        es="Una batería cambia lo que significa un solo valor p. Con m pruebas, cada una corrida al nivel α sobre un modelo correcto, la probabilidad de que al menos una rechace es muy superior a α, de modo que una batería que no levanta ninguna alerta es informativa, mientras que una que levanta una alerta no es, por sí sola, un defecto. Por eso Contraste reporta cada prueba con su valor p y su luz bajo la política del lector, y un hallazgo se levanta desde las pruebas que cita y su severidad, nunca desde una sola luz."
      />
      <Equation
        tex={String.raw`\mathrm{light}(p) = \begin{cases} \text{red} & p < \alpha_{\mathrm{red}} \\ \text{amber} & \alpha_{\mathrm{red}} \le p < \alpha_{\mathrm{amber}} \\ \text{green} & p \ge \alpha_{\mathrm{amber}} \end{cases}`}
        caption={<T en={<>The light of a test under the reader's policy: p its p-value, α<sub>red</sub> and α_amber the policy thresholds, with α<sub>red</sub> not above α_amber. They are a policy choice that the rail moves, not a regulatory threshold.</>} es={<>La luz de una prueba bajo la política del lector: p su valor p, α<sub>red</sub> y α_amber los umbrales de la política, con α<sub>red</sub> no mayor que α_amber. Son una elección de política que mueve el panel, no un umbral regulatorio.</>} />}
      />
      <Equation
        tex={String.raw`\Pr(\text{at least one rejection}) = 1 - (1-\alpha)^{m}`}
        caption={<T en={<>The false alarm of a battery of m independent tests each run at level α on a correct model: for m = 10 and α = 5% it is 40.1%. The tests of a real battery are correlated, so this is the figure to read a battery against, not its exact rate.</>} es={<>La falsa alarma de una batería de m pruebas independientes, cada una al nivel α sobre un modelo correcto: para m = 10 y α = 5% es 40,1%. Las pruebas de una batería real están correlacionadas, así que esta es la cifra con la que se lee una batería, no su tasa exacta.</>} />}
      />
      <Limit
        title={{ en: 'A light is a policy, not a verdict', es: 'Una luz es una política, no un veredicto' }}
        en="The ECB fixes the statistics and p-values an IRB validation reports and no pass or fail level, so every threshold in Contraste is labelled as a policy that the reader can move. A passed test is evidence for the model, not compliance with any regulation."
        es="El BCE fija los estadísticos y los valores p que reporta una validación IRB y ningún nivel de aprobación, así que cada umbral de Contraste se rotula como una política que el lector puede mover. Una prueba aprobada es evidencia a favor del modelo, no cumplimiento de ninguna regulación."
      />
    </>
  );
}

export function ScorecardsExtra() {
  const t = useT();
  return (
    <>
      <Figure caption={t('Weight of evidence by bin of one variable, schematic: a negative bar is a bin riskier than the average and a positive one a safer bin; a sound binning is monotone across the bins.', 'Peso de evidencia por tramo de una variable, esquemático: una barra negativa es un tramo más riesgoso que el promedio y una positiva un tramo más seguro; un buen tramado es monótono a lo largo de los tramos.')}>
        <ScorecardFigure />
      </Figure>
      <Limit
        title={{ en: 'A scorecard is a champion, not a ceiling', es: 'Una tarjeta de puntuación es un campeón, no un techo' }}
        en="The binning and the points are learned on the training slice only, and the scale of the points (600 at odds of 50 to 1 with 20 points to double the odds in case C01) is a choice, not a fact about the portfolio. A challenger earns its place only by beating the scorecard on held-out data with its interval and its paired test."
        es="El tramado y los puntos se aprenden solo en la tajada de entrenamiento, y la escala de los puntos (600 con chances de 50 a 1 y 20 puntos para duplicar las chances en el caso C01) es una elección, no un hecho de la cartera. Un retador se gana su lugar solo superando a la tarjeta de puntuación en datos reservados, con su intervalo y su prueba pareada."
      />
    </>
  );
}

export function GlassBoxExtra() {
  const t = useT();
  return (
    <>
      <P
        en={<>How the rungs are fitted in case C01: an L1-penalised logistic regression on the weight of evidence of the binned inputs, penalised logistic tree regression with the rules of short trees, and an explainable boosting machine with five pairwise terms and 64 bins. Each is fitted on the training slice only, the penalty strength is chosen by repeated stratified five-fold cross-validation inside it, and each receives an explicit calibration map fitted on the calibration slice, <Cite id="contrasteC01" />.</>}
        es={<>Cómo se ajustan los peldaños en el caso C01: una regresión logística con penalización L1 sobre el peso de evidencia de las entradas tramadas, una regresión logística con árboles penalizada con las reglas de árboles cortos, y una máquina de potenciación explicable con cinco términos de pares y 64 tramos. Cada una se ajusta solo en la tajada de entrenamiento, la fuerza de la penalización se elige con validación cruzada estratificada repetida de cinco pliegues dentro de ella, y cada una recibe un mapa de calibración explícito ajustado en la tajada de calibración, <Cite id="contrasteC01" />.</>}
      />
      <P
        en="What the bake found about these rungs, on 9,000 held-out records of the Taiwan cards: penalised logistic tree regression and the explainable boosting machine gain about as much over the scorecard as the monotone boosted model does, the L1 regression does not, and the paired test says the gain is real. On the 300 records of the German twin no rung beats the scorecard significantly, so the same method gives opposite verdicts at two sample sizes."
        es="Lo que encontró la generación sobre estos peldaños, en 9000 registros reservados de las tarjetas de Taiwán: la regresión logística con árboles penalizada y la máquina de potenciación explicable ganan tanto sobre la tarjeta de puntuación como el modelo potenciado monótono, la regresión L1 no, y la prueba pareada dice que la ganancia es real. En los 300 registros del gemelo alemán ningún peldaño supera significativamente a la tarjeta de puntuación, de modo que el mismo método da veredictos opuestos con dos tamaños de muestra."
      />
      <P
        en="Why the shape functions matter to a validator: because the model is additive, each shape function is a table of bins and points that a reviewer can read, plot and challenge against the business sense of the variable, and a pair term is a small grid. The reasons for a decision are therefore exact for the model rather than estimated, and the live scorer of the App recomputes an applicant's explainable boosting score from the committed export alone."
        es="Por qué importan las funciones de forma a un validador: como el modelo es aditivo, cada función de forma es una tabla de tramos y puntos que un revisor puede leer, graficar y contrastar con el sentido de negocio de la variable, y un término de pares es una grilla pequeña. Las razones de una decisión son entonces exactas para el modelo y no estimadas, y el evaluador en vivo de la App recalcula el puntaje de potenciación explicable de un solicitante solo desde la exportación comprometida."
      />
      <Equation
        tex={String.raw`\hat\beta = \arg\min_{\beta}\; -\sum_{i=1}^{n}\Big[y_i \log \sigma(x_i^{\top}\beta) + (1-y_i)\log\big(1-\sigma(x_i^{\top}\beta)\big)\Big] + \lambda\lVert\beta\rVert_1`}
        caption={<T en={<>The L1-penalised logistic regression behind the penalised rungs: y<sub>i</sub> the outcome of record i, x<sub>i</sub> its inputs (weights of evidence or tree rules), σ the logistic function, β the coefficients and λ the penalty strength chosen by cross-validation; the penalty sets some coefficients exactly to zero.</>} es={<>La regresión logística con penalización L1 detrás de los peldaños penalizados: y<sub>i</sub> el resultado del registro i, x<sub>i</sub> sus entradas (pesos de evidencia o reglas de árboles), σ la función logística, β los coeficientes y λ la fuerza de la penalización elegida por validación cruzada; la penalización lleva algunos coeficientes exactamente a cero.</>} />}
      />
      <Figure caption={t('A shape function of an explainable boosting machine, schematic: the contribution of one variable to the log-odds, one step per bin, which a reviewer reads directly.', 'Una función de forma de una máquina de potenciación explicable, esquemática: la contribución de una variable a el logaritmo de la razón de probabilidades, un escalón por tramo, que un revisor lee directamente.')}>
        <ShapeFigure />
      </Figure>
      <Limit
        title={{ en: 'A glass box is exact, not necessarily right', es: 'Una caja de vidrio es exacta, no necesariamente correcta' }}
        en="A glass-box model shows exactly what it does, not that what it does is right: a shape function can be smooth and wrong, and the gain of a challenger is a claim only with its interval and its paired test."
        es="Un modelo de caja de vidrio muestra exactamente lo que hace, no que lo que hace sea correcto: una función de forma puede ser suave y errada, y la ganancia de un retador es una afirmación solo con su intervalo y su prueba pareada."
      />
    </>
  );
}

export function BoostingExtra() {
  const t = useT();
  return (
    <>
      <P
        en={<>The boosted rung of case C01 is LightGBM with a monotone constraint per feature and XGBoost as its cross-check; its scores receive an isotonic calibration map fitted on the calibration slice <Cite id="zadrozny2002" />. An isotonic map is a monotone step function, so it keeps the order of the scores, and with it the ranking, except for the ties it creates: it can repair the calibration of a boosted model without paying for it in discrimination.</>}
        es={<>El peldaño potenciados del caso C01 es LightGBM con una restricción monótona por variable y XGBoost como verificación cruzada; sus puntajes reciben un mapa de calibración isotónico ajustado en la tajada de calibración <Cite id="zadrozny2002" />. Un mapa isotónico es una función escalonada monótona, así que conserva el orden de los puntajes, y con él el ordenamiento, salvo por los empates que crea: puede reparar la calibración de un modelo potenciado sin pagarlo en discriminación.</>}
      />
      <P
        en="What a better ranking is worth in capital: at 80% approved, an LGD of 50% and the Basel III function, the monotone boosted book of the Taiwan cards needs 4.2% less capital than the scorecard's, because the better ranking lets in less risk at the same approval rate. The gap grows to 10.3% under severe covariate drift and reverses to 13.5% more capital for the same model trained on 2,000 rows, so the complexity pays only where there is enough data to support it."
        es="Lo que vale en capital un mejor ordenamiento: con 80 % aprobado, una LGD de 50 % y la función de Basilea III, la cartera potenciados monótona de las tarjetas de Taiwán necesita 4,2 % menos de capital que la de la tarjeta de puntuación, porque el mejor ordenamiento deja entrar menos riesgo con la misma tasa de aprobación. La brecha crece a 10,3 % con deriva severa de covariables y se invierte a 13,5 % más de capital para el mismo modelo entrenado con 2000 filas, de modo que la complejidad rinde solo donde hay datos suficientes que la sostengan."
      />
      <Equation
        tex={String.raw`F_M(x) = F_0 + \nu\sum_{m=1}^{M} h_m(x), \qquad \frac{\partial F_M}{\partial x_j} \ge 0 \ \text{ for each constrained feature } j`}
        caption={<T en={<>The boosted model: F<sub>0</sub> the initial score, ν the learning rate, h<sub>m</sub> the m-th tree and M the number of trees; the monotone constraint asks the score never to fall as a constrained feature j grows, and Contraste checks it on individual conditional expectation curves, record by record.</>} es={<>El modelo potenciado: F<sub>0</sub> el puntaje inicial, ν la tasa de aprendizaje, h<sub>m</sub> el m-ésimo árbol y M el número de árboles; la restricción monótona pide que el puntaje no baje cuando crece una variable restringida j, y Contraste lo verifica en curvas de expectativa condicional individual, registro a registro.</>} />}
      />
      <Equation
        tex={String.raw`p(y^{\ast} \mid x^{\ast}, \mathcal{D}) = \int p(y^{\ast} \mid x^{\ast}, \phi)\, p(\phi \mid \mathcal{D})\, d\phi`}
        caption={<T en={<>The posterior predictive that a prior-data fitted network such as TabPFN approximates in one forward pass: D the training set given in context, x* and y* a new record and its outcome, φ the latent mechanism of the prior over datasets (Hollmann et al. 2025).</>} es={<>El predictivo posterior que una red ajustada a datos de un a priori como TabPFN aproxima en una sola pasada: D el conjunto de entrenamiento dado en contexto, x* e y* un registro nuevo y su resultado, φ el mecanismo latente del a priori sobre conjuntos de datos (Hollmann et al. 2025).</>} />}
      />
      <Figure caption={t('The model ladder of case C01, from the scorecard to the foundation model: every rung on the same split and under the same battery of tests.', 'La escalera de modelos del caso C01, de la tarjeta de puntuación al modelo fundacional: cada peldaño sobre la misma partición y bajo la misma batería de pruebas.')}>
        <LadderFigure />
      </Figure>
      <Limit
        title={{ en: 'A better ranking is not yet a better model', es: 'Un mejor ordenamiento aún no es un mejor modelo' }}
        en="On 300 records the boosted model beats nothing, the foundation model is shown on that one small case only and under its own licence terms, and the gain of any challenger is a claim only with its interval and its paired test."
        es="Con 300 registros el modelo potenciado no supera a nada, el modelo fundacional se muestra solo en ese único caso pequeño y bajo sus propios términos de licencia, y la ganancia de cualquier retador es una afirmación solo con su intervalo y su prueba pareada."
      />
    </>
  );
}

export function DiscriminationExtra() {
  const t = useT();
  return (
    <>
      <P
        en="Reading the AUC as a probability: it is the chance that an obligor who defaulted scores riskier than one who did not, so 0.5 is a ranking with no information. That is why case C01 carries the constant PD as a control, whose AUC is exactly 0.5, and the strongest single variable as a second one, and why the Gini coefficient, which is the same quantity rescaled to 2 AUC minus 1, is shown beside it and never as a separate piece of evidence."
        es="Leer el AUC como una probabilidad: es la probabilidad de que un deudor que incumplió puntúe como más riesgoso que uno que no, de modo que 0,5 es un ordenamiento sin información. Por eso el caso C01 lleva la PD constante como control, cuyo AUC es exactamente 0,5, y la mejor variable individual como segundo control, y por eso el coeficiente de Gini, que es la misma cantidad reescalada a 2 AUC menos 1, se muestra a su lado y nunca como una evidencia separada."
      />
      <P
        en="A caution found by measuring the test itself in case C22: the test of the AUC against the initial AUC treats the initial AUC as known, and when it is estimated on a slice less than half the size of the current one, as C01's calibration slice is, the test rejects about one time in six at the 5% level when nothing changed (about one in nine at equal sizes). Contraste therefore adds the variance of the calibration slice's AUC, an extension of the ECB formula that the result states; with it the champion's p-value on the plain holdout moved from 0.092 to 0.226."
        es="Una cautela hallada midiendo la propia prueba en el caso C22: la prueba del AUC contra el AUC inicial trata el AUC inicial como conocido, y cuando se estima en un tramo de menos de la mitad del tamaño del actual, como es el tramo de calibración de C01, la prueba rechaza cerca de una vez de cada seis al nivel de 5 % cuando nada cambió (cerca de una de cada nueve con tamaños iguales). Por eso Contraste suma la varianza del AUC del tramo de calibración, una extensión de la fórmula del BCE que el resultado declara; con ella el valor p del campeón en la muestra reservada simple pasó de 0,092 a 0,226."
      />
      <Figure caption={t('An ROC curve, schematic: the area under it is the AUC, the probability that a defaulter scores riskier than a non-defaulter; the diagonal is a ranking with no information.', 'Una curva ROC, esquemática: el área bajo ella es el AUC, la probabilidad de que un deudor que incumple puntúe como más riesgoso que uno que no; la diagonal es un ordenamiento sin información.')}>
        <RocFigure />
      </Figure>
      <Limit
        title={{ en: 'A high AUC says the model ranks, not that its PDs are right', es: 'Un AUC alto dice que el modelo ordena, no que sus PD sean correctas' }}
        en="Discrimination and calibration are separate properties: a model can rank every obligor correctly with every PD wrong, which is why each rung needs an explicit calibration map and a calibration test beside its AUC."
        es="La discriminación y la calibración son propiedades separadas: un modelo puede ordenar correctamente a todos los deudores con todas las PD erradas, y por eso cada peldaño necesita un mapa de calibración explícito y una prueba de calibración junto a su AUC."
      />
    </>
  );
}

export function CalibrationExtra() {
  const t = useT();
  return (
    <>
      <P
        en="Calibration is tested at two levels, and the severity policy of the cases weighs them differently: the level, whether the average PD is right, by the binomial, Vasicek-corrected binomial and Jeffreys tests, and the fit, whether it is right across the range, by the chi-square, Hosmer-Lemeshow and Spiegelhalter tests. At thousands of obligors the fit tests reject deviations too small to matter, so a red level test counts as a stronger finding than a red fit test."
        es="La calibración se prueba en dos niveles, y la política de severidad de los casos los pondera distinto: el nivel, si la PD promedio es correcta, con las pruebas binomial, binomial corregida de Vasicek y de Jeffreys, y el ajuste, si lo es a lo largo del rango, con las pruebas chi-cuadrado, de Hosmer-Lemeshow y de Spiegelhalter. Con miles de deudores las pruebas de ajuste rechazan desviaciones demasiado pequeñas para importar, así que una prueba de nivel en rojo cuenta como un hallazgo más fuerte que una de ajuste en rojo."
      />
      <Figure caption={t('A reliability diagram, schematic: the observed default rate of each bin of predicted PD; a calibrated model lies on the diagonal.', 'Un diagrama de confiabilidad, esquemático: la tasa de incumplimiento observada de cada tramo de PD predicha; un modelo calibrado queda sobre la diagonal.')}>
        <ReliabilityFigure />
      </Figure>
      <Limit
        title={{ en: 'A calibration test is only as good as its measured size', es: 'Una prueba de calibración vale lo que su tamaño medido' }}
        en="Hosmer-Lemeshow with the degrees of freedom of a model fitted on the same data rejected correct PDs about one time in nine at the 5% level when the PDs were fitted on other data. Case C22 found it by measurement and the product corrected it, which is why no test of the battery is read without its measured size."
        es="Hosmer-Lemeshow con los grados de libertad de un modelo ajustado sobre los mismos datos rechazó PD correctas cerca de una vez de cada nueve al nivel de 5 % cuando las PD se habían ajustado con otros datos. El caso C22 lo encontró midiendo y el producto lo corrigió, y por eso ninguna prueba de la batería se lee sin su tamaño medido."
      />
    </>
  );
}

export function StabilityExtra() {
  const t = useT();
  return (
    <>
      <P
        en="The population stability index compares the distribution of the score now with the one at development, bin by bin, as the sum of the difference of the shares times the logarithm of their ratio. On the same population it is not zero: its expected value is (1/n + 1/m)(B - 1) for n and m records and B bins, about 0.0015 on the holdout of case C01, which is why that case expects a PSI between 0 and 0.02 there and reads a shift against that expectation instead of a rule of thumb."
        es="El índice de estabilidad poblacional compara la distribución del puntaje de ahora con la del desarrollo, tramo por tramo, como la suma de la diferencia de las fracciones por el logaritmo de su razón. En la misma población no es cero: su valor esperado es (1/n + 1/m)(B - 1) para n y m registros y B tramos, cerca de 0,0015 en la muestra reservada del caso C01, y por eso ese caso espera un PSI entre 0 y 0,02 ahí y lee un desplazamiento contra esa expectativa y no contra una regla empírica."
      />
      <P
        en="What stability is worth: under covariate drift with the relation between score and default unchanged, the calibrated models stay calibrated while the PSI flags the shift, and under a prior shift or label noise every level test rejects, as it must. The PSI says that the population moved, not that the PDs are wrong; the two questions are answered by different tests, and a validator reads them together."
        es="Lo que vale la estabilidad: con deriva de covariables y la relación entre puntaje e incumplimiento sin cambios, los modelos calibrados siguen calibrados mientras el PSI señala el desplazamiento, y con un cambio de la prevalencia o ruido en las etiquetas toda prueba de nivel rechaza, como debe. El PSI dice que la población se movió, no que las PD estén erradas; las dos preguntas las responden pruebas distintas, y un validador las lee juntas."
      />
      <Figure caption={t('Two score distributions, schematic: the share of the population in each score bin at development and now; the PSI summarises how far apart they are.', 'Dos distribuciones de puntaje, esquemáticas: la fracción de la población en cada tramo de puntaje en el desarrollo y ahora; el PSI resume qué tan separadas están.')}>
        <PsiFigure />
      </Figure>
      <Limit
        title={{ en: 'A stable score is not a correct one', es: 'Un puntaje estable no es un puntaje correcto' }}
        en="The PSI looks only at the distribution of the score: a population can keep it while the relation between score and default changes, as the label-noise variant of case C01 shows, with the PSI in green and every level test in red."
        es="El PSI mira solo la distribución del puntaje: una población puede conservarla mientras cambia la relación entre puntaje e incumplimiento, como lo muestra la variante de ruido en las etiquetas del caso C01, con el PSI en verde y toda prueba de nivel en rojo."
      />
    </>
  );
}

export function MigrationsExtra() {
  const t = useT();
  return (
    <>
      <Figure caption={t('A rating chain, schematic: the grades move among themselves with probabilities p_ij, and default is the absorbing state that never leaves.', 'Una cadena de calificaciones, esquemática: los grados se mueven entre sí con probabilidades p_ij, y el incumplimiento es el estado absorbente que nunca se abandona.')}>
        <ChainFigure />
      </Figure>
      <Limit
        title={{ en: 'A matrix estimated from cohorts is an estimate, not the truth', es: 'Una matriz estimada desde cohortes es una estimación, no la verdad' }}
        en="Contraste scores the estimators against generators whose true matrix is known, and the embedding problem warns that an observed one-year matrix may have no valid generator at all, so a generator that is fitted anyway is a modelling choice to document, not a measurement."
        es="Contraste puntúa los estimadores contra generadores cuya matriz verdadera se conoce, y el problema de inmersión advierte que una matriz anual observada puede no tener ningún generador válido, así que un generador que se ajusta de todos modos es una decisión de modelación que hay que documentar, no una medición."
      />
    </>
  );
}

export function TransitionsExtra() {
  const t = useT();
  return (
    <>
      <Figure caption={t('Yearly estimates of one transition probability around the pooled estimate, schematic: time homogeneity asks whether the yearly estimates differ from the pooled one by more than chance.', 'Estimaciones anuales de una probabilidad de transición alrededor de la estimación agrupada, esquemático: la homogeneidad temporal pregunta si las estimaciones anuales difieren de la agrupada más de lo que explica el azar.')}>
        <HomogeneityFigure />
      </Figure>
      <Limit
        title={{ en: 'A rejection is the usual outcome with many ratings', es: 'Un rechazo es el resultado habitual con muchas calificaciones' }}
        en="With thousands of ratings the tests of the reference matrix reach p-values near 1e-124 and the time homogeneity test underflows to zero, so the size of the departure, not the p-value alone, is what a validator reads."
        es="Con miles de calificaciones las pruebas de la matriz de referencia llegan a valores p cercanos a 1e-124 y la prueba de homogeneidad temporal se desborda a cero, de modo que lo que lee un validador es el tamaño de la desviación, no solo el valor p."
      />
    </>
  );
}

export function SizeAndPowerExtra() {
  const t = useT();
  return (
    <>
      <Figure caption={t('A power curve, schematic: with no defect the rejection rate is the size and should sit at the level α; as the planted defect grows it is the power of the test.', 'Una curva de potencia, esquemática: sin defecto la tasa de rechazo es el tamaño y debe quedar en el nivel α; a medida que crece el defecto plantado es la potencia de la prueba.')}>
        <PowerFigure />
      </Figure>
      <Limit
        title={{ en: 'A measured size holds for its generator', es: 'Un tamaño medido vale para su generador' }}
        en="A test that holds its size on a generator holds it for that generator's assumptions, not for every portfolio; each rate names its mechanism, its sample sizes and its number of repetitions."
        es="Una prueba que mantiene su tamaño en un generador lo mantiene para los supuestos de ese generador, no para toda cartera; cada tasa nombra su mecanismo, sus tamaños de muestra y su número de repeticiones."
      />
    </>
  );
}
