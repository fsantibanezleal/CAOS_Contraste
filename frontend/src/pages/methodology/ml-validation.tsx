// The Methodology section on ML model validation and fairness (U14): the tests a validator runs on a machine learning
// model that has no closed form (cases C02 and C20), the explainers and the reason codes they feed, and the fairness
// metrics with the legal sentences that bound what they mean (case C21). Three parts, as sub-tabs of one `method` section
// (ADR-0017 section 2.1): the ML test catalogue (dossier 06, C.7 and I.1, with the conformal and CBPE constructions); the
// explainers and the reason codes (dossier 06, C.7; dossier 04, J.1 and J.2); the fairness metrics, the four-fifths
// benchmark and the legal sentences (dossier 06, C.7, A.7 to A.9 and I.6; dossier 04, J.3; the U14 research addendum, H3
// and H4; dossier 07, the SGCD card). Every constant and formula is transcribed from those files, each read at its primary
// source on 2026-10-04, 2026-10-17 or 2026-10-18; what is a convention of Contraste (the tolerances, the seeds, the cut-offs)
// is said to be one and what the dossiers mark UNVERIFIED stays marked in the callout. Every display equation carries a
// caption that defines its symbols. One file exports one section, with one honest callout for the topic.
import { Callout, Cite, DocSection, Equation, Figure, SubTabs } from '@fasl-work/caos-app-shell';
import { P, Ref, T, useT } from '../../content/bi';
import type { MethodologySection } from '../methodologyRegistry';

const W = 480;
const H = 276;

/** The caption helper for the figures, outside a hook-bound component. */
function t2(en: string, es: string) {
  return <T en={en} es={es} />;
}

const r1 = (v: number) => Math.round(v * 10) / 10;
const path = (pts: Array<[number, number]>) => pts.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${r1(x)} ${r1(y)}`).join(' ');

/** An illustrative performance curve against the noise scale: the AUC falls as the noise grows; the finding is raised only where the loss at the preset scale is beyond the tolerance. */
function NoiseFigure() {
  const t = useT();
  // eps in [0, 1] to x in [60, 440]; AUC in [0.60, 0.80] to y = 230 - 800 (auc - 0.60)
  const x = (e: number) => 60 + e * 380;
  const y = (a: number) => 206 - 700 * (a - 0.6);
  const auc = (e: number) => 0.78 - 0.1 * e - 0.07 * e * e;
  const grid = Array.from({ length: 41 }, (_, i) => i / 40);
  const preset = 0.25;
  const tolerance = 0.02;
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('A schematic curve of the AUC against the noise scale: the AUC starts at 0.78 and falls as noise proportional to each input standard deviation grows; a marker at the preset scale and a dashed line at the tolerated loss below the clean AUC show where a finding would be raised', 'Una curva esquemática del AUC contra la escala de ruido: el AUC parte en 0,78 y baja al crecer el ruido proporcional a la desviación estándar de cada entrada; un marcador en la escala preestablecida y una línea punteada en la pérdida tolerada bajo el AUC limpio muestran dónde se levantaría un hallazgo')}>
      <line className="dg-axis" x1={x(0)} y1={y(0.6)} x2={x(1)} y2={y(0.6)} />
      <line className="dg-axis" x1={x(0)} y1={y(0.8)} x2={x(0)} y2={y(0.6)} />
      {[0, 0.25, 0.5, 0.75, 1].map((e) => (
        <text key={e} className="dg-tick" x={x(e)} y={y(0.6) + 16} textAnchor="middle">{t(String(e), String(e).replace('.', ','))}</text>
      ))}
      <path className="dg-curve-faint" d={path([[x(0), y(0.78 - tolerance)], [x(1), y(0.78 - tolerance)]])} fill="none" strokeDasharray="5 3" />
      <path className="dg-curve" d={path(grid.map((e) => [x(e), y(auc(e))]))} fill="none" />
      <line className="dg-marker" x1={x(preset)} y1={y(0.8)} x2={x(preset)} y2={y(0.6)} />
      <text className="dg-marker-label" x={x(preset) + 4} y={y(0.8) + 10} textAnchor="start">{t('preset scale', 'escala preestablecida')}</text>
      <text className="dg-edge-label" x={x(1) - 4} y={y(0.78 - tolerance) - 6} textAnchor="end">{t('clean AUC less the tolerance', 'AUC limpio menos la tolerancia')}</text>
      <text className="dg-edge-label" x={x(1) - 4} y={y(auc(1)) - 8} textAnchor="end">{t('AUC under noise', 'AUC bajo ruido')}</text>
      <text className="dg-axis-label" x={W / 2} y={H - 26} textAnchor="middle">{t('noise scale, in standard deviations of each input', 'escala de ruido, en desviaciones estándar de cada entrada')}</text>
      <text className="dg-axis-label" x={W - 8} y={14} textAnchor="end">AUC</text>
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('Illustrative schematic, not a result', 'Esquema ilustrativo, no un resultado')}</text>
    </svg>
  );
}

/** The reason-code selection as shapes: the four features with the largest contribution toward default are the reasons, the rest are not. */
function ReasonFigure() {
  const t = useT();
  const rows: Array<[string, number]> = [['feature A', 0.42], ['feature B', 0.31], ['feature C', 0.24], ['feature D', 0.17], ['feature E', 0.08], ['feature F', -0.05], ['feature G', -0.19]];
  const zero = 250;
  const x = (v: number) => zero + v * 380;
  const row = (i: number) => 14 + i * 28;
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('Seven horizontal bars for the contribution of seven features to the log-odds of default of one applicant, four positive bars selected as the reasons and the others not, one of them negative', 'Siete barras horizontales con la contribución de siete variables a las log-odds de incumplimiento de un solicitante, cuatro barras positivas elegidas como razones y las otras no, una de ellas negativa')}>
      <line className="dg-axis" x1={zero} y1={8} x2={zero} y2={row(6) + 24} />
      {rows.map(([name, v], i) => (
        <g key={name}>
          <text className="dg-edge-label" x={8} y={row(i) + 14} textAnchor="start">{name.replace('feature', t('feature', 'variable'))}</text>
          <rect className={i < 4 ? 'dg-fill-accent' : 'dg-fill-warn'} x={v >= 0 ? zero : x(v)} y={row(i)} width={Math.abs(x(v) - zero)} height={18} opacity={i < 4 ? 1 : 0.5} />
          <text className="dg-note" x={v >= 0 ? x(v) + 4 : x(v) - 4} y={row(i) + 14} textAnchor={v >= 0 ? 'start' : 'end'}>{i < 4 ? t('reason', 'razón') : ''}</text>
        </g>
      ))}
      <text className="dg-axis-label" x={W / 2} y={H - 24} textAnchor="middle">{t('contribution to the log-odds of default', 'contribución a las log-odds de incumplimiento')}</text>
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('Illustrative schematic, not a result', 'Esquema ilustrativo, no un resultado')}</text>
    </svg>
  );
}

/** The four-fifths line as shapes: the rate of each group over the highest group's rate, a line at 4/5, and the group below it flagged. */
function FourFifthsFigure() {
  const t = useT();
  const rows: Array<[string, number, boolean]> = [['group 1', 0.9, false], ['group 2', 0.82, false], ['group 3', 0.66, true]];
  const x = (s: number) => 120 + s * 320;
  const row = (i: number) => 40 + i * 44;
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('Three horizontal bars for the approval rate of three groups, 90, 82 and 66 percent; a vertical line at four fifths of the highest rate, 72 percent, an employment benchmark; the third bar falls short of it and is flagged', 'Tres barras horizontales con la tasa de aprobación de tres grupos, 90, 82 y 66 por ciento; una línea vertical en cuatro quintos de la mayor tasa, 72 por ciento, una referencia laboral; la tercera barra no la alcanza y se marca')}>
      <line className="dg-axis" x1={x(0)} y1={20} x2={x(0)} y2={row(2) + 36} />
      {rows.map(([name, v, flag], i) => (
        <g key={name}>
          <text className="dg-edge-label" x={8} y={row(i) + 18} textAnchor="start">{name.replace('group', t('group', 'grupo'))}</text>
          <rect className={flag ? 'dg-fill-warn' : 'dg-fill-accent'} x={x(0)} y={row(i)} width={x(v) - x(0)} height={26} />
          <text className="dg-note" x={x(v) + 4} y={row(i) + 18} textAnchor="start">{`${Math.round(v * 100)} %`}</text>
        </g>
      ))}
      <line className="dg-marker" x1={x(0.9 * 0.8)} y1={26} x2={x(0.9 * 0.8)} y2={row(2) + 40} />
      <text className="dg-marker-label" x={x(0.9 * 0.8) - 4} y={22} textAnchor="end">{t('4/5 of the highest rate: 72 %', '4/5 de la mayor tasa: 72 %')}</text>
      <text className="dg-axis-label" x={W / 2} y={H - 24} textAnchor="middle">{t('approval rate', 'tasa de aprobación')}</text>
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('Employment benchmark, illustrative schematic, not a result', 'Referencia laboral, esquema ilustrativo, no un resultado')}</text>
    </svg>
  );
}

function TestsPart() {
  return (
    <>
      <P
        en={<>A machine learning model has no coefficient to read, so its validation rests on tests that probe it from outside. The supervisory anchors are the ECB guide to internal models, which asks for complexity to be justified, for the randomness of training to be controlled and the seeds stored, and for overfitting, out-of-sample and out-of-time behaviour to be examined <Cite id="egim" />, the EBA report on machine learning for IRB models, whose first recommendations are to avoid complexity that a significant gain in predictive capacity does not justify and to detect overfitting <Cite id="ebarep202328" />, and the PRA statement SS1/23 on model risk <Cite id="ss123" />. None of them sets a pass mark: every tolerance below is a convention of Contraste, stated as a named parameter in each document and never presented as regulatory.</>}
        es={<>Un modelo de aprendizaje automático no tiene coeficientes que leer, así que su validación descansa en pruebas que lo sondean desde afuera. Los anclajes supervisores son la guía del BCE sobre modelos internos, que pide justificar la complejidad, controlar el azar del entrenamiento y guardar las semillas, y examinar el sobreajuste y el comportamiento fuera de muestra y fuera del tiempo <Cite id="egim" />, el informe de la EBA sobre aprendizaje automático para modelos IRB, cuyas primeras recomendaciones son evitar la complejidad que una mejora significativa de la capacidad predictiva no justifica y detectar el sobreajuste <Cite id="ebarep202328" />, y la declaración SS1/23 de la PRA sobre riesgo de modelos <Cite id="ss123" />. Ninguno fija una nota de aprobación: toda tolerancia de abajo es una convención de Contraste, declarada como parámetro con nombre en cada documento y nunca presentada como regulatoria.</>}
      />
      <P
        en={<>Robustness to input perturbation adds noise of scale epsilon, for example Gaussian noise proportional to each feature&apos;s standard deviation, to the evaluation inputs only, and plots the AUC and the Brier score against epsilon; a finding is raised when the degradation exceeds a tolerance at a preset epsilon, which echoes the SR 11-7 remark that unexpectedly large changes in outputs in response to small changes in inputs can indicate an unstable model <Cite id="sr117" />. Resilience to distribution shift evaluates the model on the worst subsamples by a shift score, the worst 10 percent being the dossier&apos;s example, and on out-of-time windows. Seed stability retrains the model across seeds and reports the dispersion of the AUC, of the grade assigned to each obligor and of the attribution ranks. The overfit gap is the difference between training and test performance, overall and by slice, and the weak spots are slices where the test error exceeds a multiple of the average. In the C20 documents the grid, the tolerance of 0.02 AUC points, the 20 seeds, the 100 bootstrap refits and the multiple of 2 are named conventions.</>}
        es={<>La robustez ante perturbaciones de las entradas añade ruido de escala epsilon, por ejemplo ruido gaussiano proporcional a la desviación estándar de cada variable, solo a las entradas de evaluación, y grafica el AUC y el puntaje de Brier contra epsilon; se levanta un hallazgo cuando la degradación supera una tolerancia en un epsilon preestablecido, lo que hace eco de la observación de SR 11-7 de que cambios inesperadamente grandes en las salidas ante cambios pequeños en las entradas pueden indicar un modelo inestable <Cite id="sr117" />. La resiliencia ante un cambio de distribución evalúa el modelo en las peores submuestras según un puntaje de cambio, siendo el peor 10 por ciento el ejemplo del dossier, y en ventanas fuera del tiempo. La estabilidad de semillas reentrena el modelo con varias semillas e informa la dispersión del AUC, del grado asignado a cada deudor y de los rangos de atribución. La brecha de sobreajuste es la diferencia entre el desempeño de entrenamiento y el de prueba, en total y por segmento, y los puntos débiles son segmentos donde el error de prueba supera un múltiplo del promedio. En los documentos de C20 la grilla, la tolerancia de 0,02 puntos de AUC, las 20 semillas, los 100 reajustes bootstrap y el múltiplo de 2 son convenciones con nombre.</>}
      />
      <Figure caption={t2('A schematic of the perturbation test: the AUC falls as the noise grows and a finding is raised only when the loss at the preset scale exceeds the tolerance. The numbers are illustrative and not a result of any model.', 'Un esquema de la prueba de perturbación: el AUC baja al crecer el ruido y se levanta un hallazgo solo cuando la pérdida en la escala preestablecida supera la tolerancia. Los números son ilustrativos y no son un resultado de ningún modelo.')}>
        <NoiseFigure />
      </Figure>
      <P
        en={<>Split conformal prediction gives a distribution-free statement about reliability <Cite id="angelopoulos2021" /> <Cite id="vovk2022" />. Scores are computed on n calibration points, the threshold is the empirical quantile of order ceil((n + 1)(1 - alpha))/n, and the set C(x) holds the labels whose score does not exceed it; under exchangeability the set covers the true label with probability at least 1 - alpha. The validation test is the empirical coverage on out-of-time or shifted data against 1 - alpha, with a binomial test on the coverage indicators, and a loss of coverage reads as an exchangeability violation, that is, as drift. The label-free performance estimate of NannyML, CBPE, is the early-warning companion while defaults mature: from calibrated probabilities it estimates the confusion matrix, and so the AUC, without labels <Cite id="nannyml" />. It is always flagged as an estimate and rests on four assumptions: calibrated probabilities, no concept drift, no extrapolation into unseen regions and an adequate sample. It complements back-testing and never replaces it.</>}
        es={<>La predicción conforme dividida da un enunciado de confiabilidad libre de distribución <Cite id="angelopoulos2021" /> <Cite id="vovk2022" />. Los puntajes se calculan en n puntos de calibración, el umbral es el cuantil empírico de orden ceil((n + 1)(1 - alfa))/n, y el conjunto C(x) reúne las etiquetas cuyo puntaje no lo supera; bajo intercambiabilidad el conjunto cubre la etiqueta verdadera con probabilidad de al menos 1 - alfa. La prueba de validación es la cobertura empírica en datos fuera del tiempo o con cambio contra 1 - alfa, con una prueba binomial sobre los indicadores de cobertura, y una pérdida de cobertura se lee como una violación de intercambiabilidad, es decir, como deriva. La estimación de desempeño sin etiquetas de NannyML, CBPE, es la compañera de alerta temprana mientras maduran los incumplimientos: a partir de probabilidades calibradas estima la matriz de confusión, y con ella el AUC, sin etiquetas <Cite id="nannyml" />. Siempre se marca como estimación y descansa en cuatro supuestos: probabilidades calibradas, sin deriva de concepto, sin extrapolación a regiones no vistas y una muestra adecuada. Complementa al backtesting y nunca lo reemplaza.</>}
      />
      <Equation
        tex={String.raw`\hat q = \text{the } \tfrac{\lceil (n+1)(1-\alpha)\rceil}{n} \text{ empirical quantile of } \{s_i\}_{i=1}^{n}, \qquad C(x) = \{\,y : s(x,y) \le \hat q\,\}, \qquad \Pr\bigl(Y_{n+1} \in C(X_{n+1})\bigr) \ge 1-\alpha`}
        caption={<T en={<>Split conformal prediction (dossier 06, C.7): s_i = s(x_i, y_i) the score of calibration point i (for classes, 1 minus the probability given to the true class), n the number of calibration points, alpha the miscoverage level (a convention, 0.10 in the C20 documents), q-hat the threshold and C(x) the set of labels whose score is within it. The guarantee holds when calibration and test points are exchangeable, so the coverage on shifted data is the test: a coverage below 1 - alpha is evidence that they are not.</>} es={<>Predicción conforme dividida (dossier 06, C.7): s_i = s(x_i, y_i) el puntaje del punto de calibración i (para clases, 1 menos la probabilidad dada a la clase verdadera), n el número de puntos de calibración, alfa el nivel de no cobertura (una convención, 0,10 en los documentos de C20), q-gorro el umbral y C(x) el conjunto de etiquetas cuyo puntaje está dentro de él. La garantía vale cuando los puntos de calibración y de prueba son intercambiables, así que la cobertura en datos con cambio es la prueba: una cobertura bajo 1 - alfa es evidencia de que no lo son.</>} />}
      />
      <P
        en={<>The remaining tests are screens. The leakage screen checks the temporal order (no feature dated after the observation date), the AUC of each feature alone (a lone feature with a near-perfect AUC is a leakage suspect), the overlap of entities between training and test, and a resemblance model, an adversarial validation classifier separating development from out-of-time samples whose AUC near 0.5 indicates similar samples; these are conventions, and no regulatory text prescribes them. Data quality counts completeness, validity ranges, uniqueness, consistency, timeliness and label consistency. The challenger comparison sets the DeLong test <Cite id="delong1988" /> beside the paired bootstrap of the Brier difference and the share of obligors whose grade differs by two notches or more. In the C20 leakage variant a feature is planted to leak the outcome: the screen should catch it while performance collapses at decision time, which is how the screen itself is validated.</>}
        es={<>Las pruebas restantes son filtros. El filtro de fuga revisa el orden temporal (ninguna variable con fecha posterior a la de observación), el AUC de cada variable sola (una variable aislada con AUC casi perfecto es sospechosa de fuga), el solapamiento de entidades entre entrenamiento y prueba, y un modelo de parecido, un clasificador de validación adversarial que separa muestras de desarrollo de muestras fuera del tiempo cuyo AUC cercano a 0,5 indica muestras similares; son convenciones, y ningún texto regulatorio las prescribe. La calidad de datos cuenta completitud, rangos de validez, unicidad, consistencia, oportunidad y consistencia de etiquetas. La comparación con el retador pone la prueba de DeLong <Cite id="delong1988" /> junto al bootstrap pareado de la diferencia de Brier y la parte de deudores cuyo grado difiere en dos escalones o más. En la variante de fuga de C20 se planta una variable que filtra el resultado: el filtro debe detectarla mientras el desempeño se desploma en el momento de la decisión, que es cómo se valida el propio filtro.</>}
      />
      <Equation
        tex={String.raw`P(\hat y = y)_j = 1 - \lvert \hat y_j - \hat p_j \rvert, \qquad \mathrm{TP}_j = P(\hat y = y)_j \ \text{if } \hat y_j = 1 \ \text{else } 0`}
        caption={<T en={<>The label-free estimate CBPE (dossier 06, C.7; NannyML): p-hat_j the calibrated probability of observation j, y-hat_j the predicted label at the threshold and P(y-hat = y)_j the probability that the prediction is right; the expected true positives and true negatives are summed over observations, and repeating the construction over thresholds gives an estimated ROC and AUC. It is an estimate under the four assumptions above and is never labelled measured.</>} es={<>La estimación sin etiquetas CBPE (dossier 06, C.7; NannyML): p-gorro_j la probabilidad calibrada de la observación j, y-gorro_j la etiqueta predicha en el umbral y P(y-gorro = y)_j la probabilidad de que la predicción sea correcta; los verdaderos positivos y negativos esperados se suman sobre las observaciones, y repetir la construcción sobre los umbrales da una ROC y un AUC estimados. Es una estimación bajo los cuatro supuestos de arriba y nunca se rotula como medida.</>} />}
      />
    </>
  );
}

function ExplainPart() {
  return (
    <>
      <P
        en={<>The explainers turn a score into reasons. SHAP assigns each feature its Shapley value, and the attributions add up to the prediction <Cite id="lundberg2017" />; TreeSHAP computes the exact values for tree ensembles in polynomial time <Cite id="lundberg2020" />. Each is a global and a local contribution in the sense of the ECB guide. The partial dependence plot averages the prediction over the data while one feature is fixed <Cite id="friedman2001" />, assuming weak dependence between that feature and the others, the individual conditional expectation draws one curve per observation and so reveals the heterogeneity the average hides <Cite id="goldstein2015" />, and the accumulated local effect sums local differences inside neighbourhoods of the feature, then centres the result to mean zero, which avoids the extrapolation into unsupported regions that correlated features cause in the partial dependence <Cite id="apleyzhu2020" />. Glass-box models, the explainable boosting machine among them, are additive in the features by construction <Cite id="lou2013" /> <Cite id="nori2019" />.</>}
        es={<>Los explicadores convierten un puntaje en razones. SHAP asigna a cada variable su valor de Shapley, y las atribuciones suman la predicción <Cite id="lundberg2017" />; TreeSHAP calcula los valores exactos para ensambles de árboles en tiempo polinomial <Cite id="lundberg2020" />. Cada uno es una contribución global y local en el sentido de la guía del BCE. El gráfico de dependencia parcial promedia la predicción sobre los datos mientras se fija una variable <Cite id="friedman2001" />, suponiendo una dependencia débil entre esa variable y las demás, la expectativa condicional individual dibuja una curva por observación y así revela la heterogeneidad que el promedio oculta <Cite id="goldstein2015" />, y el efecto local acumulado suma diferencias locales dentro de vecindades de la variable y luego centra el resultado en media cero, lo que evita la extrapolación a regiones sin soporte que las variables correlacionadas causan en la dependencia parcial <Cite id="apleyzhu2020" />. Los modelos de caja de cristal, entre ellos la máquina de boosting explicable, son aditivos en las variables por construcción <Cite id="lou2013" /> <Cite id="nori2019" />.</>}
      />
      <Equation
        tex={String.raw`\phi_i = \sum_{S \subseteq F\setminus\{i\}} \frac{|S|!\,(|F|-|S|-1)!}{|F|!}\bigl[f_x(S\cup\{i\}) - f_x(S)\bigr], \qquad f(x) = \phi_0 + \sum_i \phi_i`}
        caption={<T en={<>The Shapley value and its additivity (dossier 06, C.7; Lundberg and Lee 2017): F the set of features, S a subset not holding i, f_x(S) the expected model output given the features in S (interventional or observational, a choice to document), phi_i the contribution of feature i and phi_0 the base value. Additivity is a test of its own: the attributions of an observation must add to its prediction.</>} es={<>El valor de Shapley y su aditividad (dossier 06, C.7; Lundberg y Lee 2017): F el conjunto de variables, S un subconjunto que no contiene a i, f_x(S) la salida esperada del modelo dadas las variables de S (intervencional u observacional, una decisión por documentar), phi_i la contribución de la variable i y phi_0 el valor base. La aditividad es una prueba por sí misma: las atribuciones de una observación deben sumar su predicción.</>} />}
      />
      <P
        en={<>The explainers are themselves validated, as the ECB guide asks: the stability of the attributions across seeds and resamples, the rank agreement between SHAP and the accumulated local effect or the partial dependence, the monotonicity and sign checks against the expected economic rationale, which the EBA recommends, and the documented weaknesses of each. In C20 the agreement is the Spearman correlation between the mean absolute SHAP importance of each feature and the range of its effect curve, and a null correlation says why it is null. A low agreement does not say which explainer is right; it says the two tell different stories about one model, which a validator must resolve before the reasons reach a customer.</>}
        es={<>Los propios explicadores se validan, como pide la guía del BCE: la estabilidad de las atribuciones entre semillas y remuestreos, el acuerdo de rangos entre SHAP y el efecto local acumulado o la dependencia parcial, las verificaciones de monotonía y signo contra la lógica económica esperada, que recomienda la EBA, y las debilidades documentadas de cada uno. En C20 el acuerdo es la correlación de Spearman entre la importancia SHAP absoluta media de cada variable y el rango de su curva de efecto, y una correlación nula dice por qué es nula. Un acuerdo bajo no dice qué explicador tiene razón; dice que los dos cuentan historias distintas de un mismo modelo, lo que un validador debe resolver antes de que las razones lleguen a un cliente.</>}
      />
      <Figure caption={t2('A schematic of the reason codes of one applicant: the four features with the largest contribution toward default are the reasons, and a feature that lowers the risk is never one. The numbers are illustrative and not a result.', 'Un esquema de los códigos de razón de un solicitante: las cuatro variables con mayor contribución hacia el incumplimiento son las razones, y una variable que baja el riesgo nunca lo es. Los números son ilustrativos y no son un resultado.')}>
        <ReasonFigure />
      </Figure>
      <P
        en={<>For adverse-action reasons, Regulation B says that disclosing more than four reasons is not likely to be helpful and describes two acceptable methods for credit scoring systems, the factors where the score fell furthest below the average of applicants at or slightly above the minimum passing score or below the average of all applicants <Cite id="regb" />. For a points scorecard the shortfall of characteristic j is directly computable; for a machine learning score the Shapley shortfall plays that role, and the dossier&apos;s design rules are that the background distribution mirrors the Regulation B reference population, that attributions are computed on the log-odds scale and aggregated over the features derived from one characteristic, that correlated features split credit arbitrarily so the stability of the top four must be tested by bootstrap, and that monotone constraints or glass-box models keep the reasons consistent with the sign a reviewer expects. The first rule follows from the wording of comment 9(b)(2)-5; the other three are methodological recommendations and not regulatory text.</>}
        es={<>Para las razones de una acción adversa, la Regulación B dice que revelar más de cuatro razones probablemente no ayude y describe dos métodos aceptables para sistemas de puntaje de crédito: los factores donde el puntaje cayó más por debajo del promedio de los solicitantes en o apenas sobre el puntaje mínimo de aprobación, o por debajo del promedio de todos los solicitantes <Cite id="regb" />. Para una scorecard de puntos el déficit de la característica j se calcula directamente; para un puntaje de aprendizaje automático el déficit de Shapley cumple ese papel, y las reglas de diseño del dossier son que la distribución de fondo refleje la población de referencia de la Regulación B, que las atribuciones se calculen en escala de log-odds y se agreguen sobre las variables derivadas de una característica, que las variables correlacionadas repartan el crédito arbitrariamente por lo que la estabilidad de las cuatro principales debe probarse por bootstrap, y que las restricciones monótonas o los modelos de caja de cristal mantengan las razones coherentes con el signo que espera un revisor. La primera regla se sigue del texto del comentario 9(b)(2)-5; las otras tres son recomendaciones metodológicas y no texto regulatorio.</>}
      />
    </>
  );
}

function FairnessPart() {
  return (
    <>
      <P
        en={<>With a protected attribute A, a decision and an outcome, the catalogue is: demographic (statistical) parity, equal approval rates across groups; equalized odds, equal decision rates across groups conditional on the outcome, and equal opportunity for the positive outcome only <Cite id="hardt2016" />; calibration within groups and the AUC by group <Cite id="kozodoi2022" />; and the adverse impact ratio, the selection rate of the protected group over that of the reference group. The tests on the rates are the two-sample proportion z-test and the Fisher exact test, and a small difference can matter when it is statistically significant. The outcome-conditioned metrics need an outcome: Contraste runs them as a labelled battery on the Taiwan card-default model in C20, which has one, and never in C21, because the public HMDA release has no performance outcome. Disparate-impact repair is a separate literature <Cite id="feldman2015" />.</>}
        es={<>Con un atributo protegido A, una decisión y un resultado, el catálogo es: la paridad demográfica (estadística), tasas de aprobación iguales entre grupos; las probabilidades igualadas, tasas de decisión iguales entre grupos condicionadas al resultado, y la igualdad de oportunidades solo para el resultado positivo <Cite id="hardt2016" />; la calibración dentro de los grupos y el AUC por grupo <Cite id="kozodoi2022" />; y la razón de impacto adverso, la tasa de selección del grupo protegido sobre la del grupo de referencia. Las pruebas sobre las tasas son la prueba z de dos proporciones y la prueba exacta de Fisher, y una diferencia pequeña puede importar cuando es estadísticamente significativa. Las métricas condicionadas al resultado necesitan un resultado: Contraste las corre como una batería etiquetada en el modelo de incumplimiento de tarjetas de Taiwán en C20, que lo tiene, y nunca en C21, porque la publicación pública de HMDA no tiene un resultado de desempeño. La reparación del impacto dispar es una literatura aparte <Cite id="feldman2015" />.</>}
      />
      <Equation
        tex={String.raw`\mathrm{AIR}_g = \frac{x_g/n_g}{x_h/n_h}, \qquad \text{flag when } \mathrm{AIR}_g < \tfrac{4}{5} \iff 5\,x_g\,n_h < 4\,x_h\,n_g`}
        caption={<T en={<>The adverse impact ratio against the highest-rate group and the four-fifths flag (dossier 06, C.7 and I.6; 29 CFR <Ref>1607.4(D)</Ref>): x_g approvals and n_g decided applications of group g, h the group with the highest approval rate. A rate less than four-fifths (or eighty percent) of the highest group&apos;s rate is generally regarded as evidence of adverse impact in US employment selection. Contraste decides the flag on the counts in exact arithmetic, the second form, so that a ratio of exactly 4/5 is never flagged by a rounding error of a float.</>} es={<>La razón de impacto adverso contra el grupo de mayor tasa y la alerta de cuatro quintos (dossier 06, C.7 e I.6; 29 CFR <Ref>1607.4(D)</Ref>): x_g aprobaciones y n_g solicitudes decididas del grupo g, h el grupo con la mayor tasa de aprobación. Una tasa de menos de cuatro quintos (u ochenta por ciento) de la tasa del grupo mayor se considera en general evidencia de impacto adverso en la selección laboral de Estados Unidos. Contraste decide la alerta sobre los conteos en aritmética exacta, la segunda forma, de modo que una razón de exactamente 4/5 nunca se marca por un error de redondeo de un flotante.</>} />}
      />
      <Figure caption={t2('A schematic of the four-fifths line: the approval rate of three groups and the line at four fifths of the highest rate. The line is an employment-selection benchmark, not a credit-law threshold, and the numbers are illustrative.', 'Un esquema de la línea de cuatro quintos: la tasa de aprobación de tres grupos y la línea en cuatro quintos de la mayor tasa. La línea es una referencia de selección laboral, no un umbral de la ley de crédito, y los números son ilustrativos.')}>
        <FourFifthsFigure />
      </Figure>
      <P
        en={<>The four-fifths line comes from US employment selection rules <Cite id="cfr1607" /> and is used by analogy in credit; it is not a credit-law standard, so every view labels it an employment benchmark. The legal frame of C21 is stated in sentences the views repeat. Regulation B as amended, effective 2026-07-21, says <Ref>&quot;The Act does not provide that the &apos;effects test&apos; applies for determining whether there is discrimination in violation of the Act&quot;</Ref> (12 CFR <Ref>1002.6(a)</Ref>) <Cite id="fr202607804" />; the Fair Housing Act is a separate statute, and the Supreme Court held that disparate-impact claims are cognizable under it <Cite id="fha3605" />; and the Interagency Fair Lending Examination Procedures state <Ref>&quot;Gross HMDA denial or approval rate disparities are not appropriate for disproportionate adverse impact analysis because they typically cannot be attributed to a specific policy or criterion&quot;</Ref> <Cite id="interagency2009" />. For that reason every C21 view says no legal claim: the unconditional rates are indicators only, and the disparity that persists after the permitted underwriting controls is an approximation of comparative evidence with its missing controls named, the credit score being the one the public data lack.</>}
        es={<>La línea de cuatro quintos viene de las reglas de selección laboral de Estados Unidos <Cite id="cfr1607" /> y se usa por analogía en crédito; no es un estándar de la ley de crédito, así que toda vista la rotula una referencia laboral. El marco legal de C21 se enuncia en frases que las vistas repiten. La Regulación B enmendada, vigente desde 2026-07-21, dice <Ref>&quot;The Act does not provide that the &apos;effects test&apos; applies for determining whether there is discrimination in violation of the Act&quot;</Ref> (12 CFR <Ref>1002.6(a)</Ref>) <Cite id="fr202607804" />; la Ley de Vivienda Justa es una ley aparte, y la Corte Suprema sostuvo que los reclamos de impacto dispar son admisibles bajo ella <Cite id="fha3605" />; y los Procedimientos interagenciales de examen de crédito justo señalan <Ref>&quot;Gross HMDA denial or approval rate disparities are not appropriate for disproportionate adverse impact analysis because they typically cannot be attributed to a specific policy or criterion&quot;</Ref> <Cite id="interagency2009" />. Por eso toda vista de C21 dice sin afirmación legal: las tasas incondicionales son solo indicadores, y la disparidad que persiste tras los controles de suscripción permitidos es una aproximación de evidencia comparativa con sus controles faltantes nombrados, siendo el puntaje de crédito el que los datos públicos no tienen.</>}
      />
      <P
        en={<>Two further boundaries apply. The SGCD stressed German credit data of SantanderAI is a research and benchmarking dataset whose card forbids real-world credit scoring and production decisions about individuals, so every C20 view that shows it repeats that sentence; Contraste claims no affiliation with Santander AI Lab beyond factual attribution <Cite id="sgcd" />. And the supervisory frames are read without compliance claims: the EU AI Act lists the evaluation of the creditworthiness of natural persons among the high-risk uses of Annex III, with the obligations of Chapter III applying from 2027-12-02 on the adopted Digital Omnibus text <Cite id="aiact" />, the EBA report sets the principle-based recommendations on machine learning <Cite id="ebarep202328" />, and the NIST AI risk management framework names the functions govern, map, measure and manage <Cite id="nistai1001" />. A passed test is evidence, not compliance.</>}
        es={<>Se aplican dos límites más. Los datos de crédito alemán estresados SGCD de SantanderAI son un conjunto de investigación y comparación cuya ficha prohíbe el puntaje de crédito en el mundo real y las decisiones de producción sobre personas, así que toda vista de C20 que lo muestra repite esa frase; Contraste no declara afiliación con Santander AI Lab más allá de la atribución factual <Cite id="sgcd" />. Y los marcos supervisores se leen sin afirmaciones de cumplimiento: la Ley de IA de la UE incluye la evaluación de la solvencia de personas naturales entre los usos de alto riesgo del Anexo III, con las obligaciones del Capítulo III aplicables desde 2027-12-02 según el texto adoptado del Ómnibus Digital <Cite id="aiact" />, el informe de la EBA fija las recomendaciones basadas en principios sobre aprendizaje automático <Cite id="ebarep202328" />, y el marco de gestión de riesgos de IA del NIST nombra las funciones gobernar, mapear, medir y gestionar <Cite id="nistai1001" />. Una prueba aprobada es evidencia, no cumplimiento.</>}
      />
    </>
  );
}

function Body() {
  const t = useT();
  return (
    <DocSection
      area="method"
      kind="classical"
      title={{ en: 'ML model validation and fairness', es: 'Validación de modelos de ML y equidad' }}
      refs={['egim', 'ebarep202328', 'ss123', 'sr117', 'angelopoulos2021', 'vovk2022', 'nannyml', 'delong1988', 'lundberg2017', 'lundberg2020', 'friedman2001', 'goldstein2015', 'apleyzhu2020', 'lou2013', 'nori2019', 'regb', 'hardt2016', 'kozodoi2022', 'feldman2015', 'cfr1607', 'fr202607804', 'fha3605', 'interagency2009', 'sgcd', 'aiact', 'nistai1001']}
    >
      <SubTabs
        ariaLabel={t('Parts of the topic', 'Partes del tema')}
        tabs={[
          { id: 'tests', label: t('The ML test catalogue', 'El catálogo de pruebas de ML'), content: <TestsPart /> },
          { id: 'explainers', label: t('Explainers and reason codes', 'Explicadores y códigos de razón'), content: <ExplainPart /> },
          { id: 'fairness', label: t('Fairness metrics and the legal frame', 'Métricas de equidad y marco legal'), content: <FairnessPart /> },
        ]}
      />
      <Callout variant="honest" title={t('What is exact, what is a choice and what these views are not', 'Qué es exacto, qué es una decisión y qué no son estas vistas')}>
        <T
          en={<>The formulas of the Shapley value, the accumulated local effect, split conformal prediction, CBPE and the adverse impact ratio, the legal sentences and the SGCD card sentence are exact as transcribed from the sources. The tolerances, the noise grid, the number of seeds and refits, the worst-subsample share, the conformal level, the decision cut-off, the lights, the situation-testing distance and the encoding of the HMDA decision (approval, denial, and the codes left out) are conventions of Contraste, named and labelled convention wherever they appear, and none is a regulatory threshold. The four-fifths line is an employment benchmark and not a credit-law threshold. The HMDA data licence sentence, the overlap of firms across the five Polish horizon files, the transfer of the SGCD shock protocol to loan-level data and the published version of the situation-testing counts remain UNVERIFIED. The views are statistical evidence about a model or about public decisions: they certify no model, claim no compliance with the AI Act, ECOA or Regulation B, make no legal claim and score nobody.</>}
          es={<>Las fórmulas del valor de Shapley, el efecto local acumulado, la predicción conforme dividida, CBPE y la razón de impacto adverso, las frases legales y la frase de la ficha de SGCD son exactas tal como se transcribieron de las fuentes. Las tolerancias, la grilla de ruido, el número de semillas y reajustes, la parte de la peor submuestra, el nivel conforme, el corte de decisión, las luces, la distancia de las pruebas de situación y la codificación de la decisión de HMDA (aprobación, rechazo y los códigos excluidos) son convenciones de Contraste, con nombre y rotuladas convención donde aparecen, y ninguna es un umbral regulatorio. La línea de cuatro quintos es una referencia de selección laboral y no un umbral de la ley de crédito. La frase de licencia de los datos de HMDA, el solapamiento de empresas entre los cinco archivos polacos de horizonte, la transferencia del protocolo de choques de SGCD a datos a nivel de préstamo y la versión publicada de los conteos de las pruebas de situación siguen SIN VERIFICAR. Las vistas son evidencia estadística sobre un modelo o sobre decisiones públicas: no certifican ningún modelo, no afirman cumplimiento de la Ley de IA, de ECOA ni de la Regulación B, no hacen ninguna afirmación legal y no puntúan a nadie.</>}
        />
      </Callout>
    </DocSection>
  );
}

export const methodologySection: MethodologySection = {
  id: 'ml-validation',
  group: 'tests',
  order: 100,
  title: { en: 'ML validation and fairness', es: 'Validación de ML y equidad' },
  Body,
};
