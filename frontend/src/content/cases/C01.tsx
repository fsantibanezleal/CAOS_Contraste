// The deep write-up of case C01, transcribed from docs/design/features/c01-retail-pd/design.md and research dossiers
// 04 (sections A, B, J) and 06 (section C). The Context view shows it under the case's sources, split and variants.
import { Cite, Equation } from '@fasl-work/caos-app-shell';
import { L, P, useT } from '../bi';

export function C01WriteUp() {
  const t = useT();
  return (
    <>
      <h3>{t('The question', 'La pregunta')}</h3>
      <P
        en={<>A bank scores card holders with a monotone weight-of-evidence logistic scorecard, the champion a validator expects. The literature says penalised logistic trees, explainable boosting machines and monotone gradient boosting can beat it by a few AUC points on retail data <Cite id="lessmann2015" />, and that deep learning does not beat boosted trees on tabular credit data <Cite id="gunnarsson2021" />. The case asks whether that gain survives once every challenger must also be calibrated, whether it is significant on held-out data, and what the validation tests say when the evaluation population shifts.</>}
        es={<>Un banco puntúa a sus tarjetahabientes con una scorecard logística monótona de peso de evidencia, el campeón que un validador espera. La literatura dice que la regresión logística con árboles penalizada, las máquinas de boosting explicables y el gradient boosting monótono pueden superarla por unos pocos puntos de AUC en datos minoristas <Cite id="lessmann2015" />, y que el aprendizaje profundo no supera a los árboles potenciados en datos tabulares de crédito <Cite id="gunnarsson2021" />. El caso pregunta si esa ganancia sobrevive cuando todo retador debe además estar calibrado, si es significativa en datos reservados, y qué dicen las pruebas de validación cuando cambia la población evaluada.</>}
      />
      <h3>{t('The data', 'Los datos')}</h3>
      <P
        en={<>The UCI Default of Credit Card Clients data <Cite id="yeh2009" />: 30,000 card holders in Taiwan, their limit, education, six months of repayment status (September back to April 2005), bill statements and payments, and whether they defaulted the next month (22.12% did). The UCI Statlog German Credit data <Cite id="hofmann1994" />, 1,000 applicants and a cost matrix (accepting a bad applicant costs five times rejecting a good one), is the small-sample twin. Both are single snapshots, so no out-of-time validation is possible: the holdout is out of sample, never out of time.</>}
        es={<>Los datos UCI Default of Credit Card Clients <Cite id="yeh2009" />: 30.000 tarjetahabientes en Taiwán, su cupo, su educación, seis meses de estado de pago (septiembre hacia atrás hasta abril de 2005), estados de cuenta y pagos, y si incumplieron el mes siguiente (lo hizo el 22,12%). Los datos UCI Statlog German Credit <Cite id="hofmann1994" />, 1.000 solicitantes y una matriz de costos (aceptar a un mal solicitante cuesta cinco veces rechazar a uno bueno), son el gemelo de muestra pequeña. Ambos son una sola foto, así que no es posible validar fuera del tiempo: la muestra reservada está fuera de la muestra, nunca fuera del tiempo.</>}
      />
      <P
        en="Codes outside the documented scale (education 0, 5 and 6; repayment status -2 and 0) are accepted, flagged by contract 1 and counted, and kept as their own bins: recoding them would be a guess. Sex, marital status, personal status and foreign-worker status are prohibited bases in fair-lending regimes, and age is restricted; none of them is a model input. Sex is kept only to report discrimination by group."
        es="Los códigos fuera de la escala documentada (educación 0, 5 y 6; estado de pago -2 y 0) se aceptan, el contrato 1 los marca y los cuenta, y se conservan como tramos propios: recodificarlos sería adivinar. El sexo, el estado civil, el estado personal y la condición de trabajador extranjero son bases prohibidas en los regímenes de crédito justo, y la edad está restringida; ninguno es una entrada del modelo. El sexo se conserva solo para reportar la discriminación por grupo."
      />
      <h3>{t('The split', 'La partición')}</h3>
      <L
        items={[
          { en: 'A locked stratified holdout of 30%, opened only by the evaluation.', es: 'Una muestra reservada estratificada del 30%, abierta solo por la evaluación.' },
          { en: 'A calibration slice of 20% of the rest, disjoint from the holdout: every calibration map is fitted there.', es: 'Un tramo de calibración del 20% del resto, disjunto de la muestra reservada: ahí se ajusta todo mapa de calibración.' },
          { en: 'The training slice: binning, WoE, rules and hyperparameters are fitted there only, with repeated stratified five-fold cross-validation.', es: 'El tramo de entrenamiento: tramos, WoE, reglas e hiperparámetros se ajustan solo ahí, con validación cruzada estratificada repetida de cinco pliegues.' },
        ]}
      />
      <h3>{t('The ladder', 'La escalera')}</h3>
      <P
        en={<>P0 anchors the comparison (a constant PD, and the strongest single variable binned). P1 is the scorecard: optimal monotone binning <Cite id="navas2020" />, a logistic regression on the WoE, points scaled so that 600 points mean odds of 50 to 1 and 20 more points double them. P2 adds penalised logistic regression and PLTR, threshold rules from short trees as inputs of an L1 logistic regression <Cite id="dumitrescu2022" />. P3 is an explainable boosting machine, a generalised additive model with a few pairwise terms <Cite id="lou2013" />. P4 is monotone gradient boosting (LightGBM, with XGBoost as the engine cross-check) with an isotonic calibration map. P5, on the German twin only, is TabPFN v2 <Cite id="hollmann2025" />, whose weights carry their own licence.</>}
        es={<>P0 ancla la comparación (una PD constante, y la variable individual más fuerte, en tramos). P1 es la scorecard: tramos monótonos óptimos <Cite id="navas2020" />, una regresión logística sobre el WoE, puntos escalados para que 600 puntos signifiquen odds de 50 a 1 y 20 puntos más las dupliquen. P2 agrega la regresión logística penalizada y PLTR, reglas de umbral de árboles cortos como entradas de una regresión logística L1 <Cite id="dumitrescu2022" />. P3 es una máquina de boosting explicable, un modelo aditivo generalizado con algunos términos de pares <Cite id="lou2013" />. P4 es gradient boosting monótono (LightGBM, con XGBoost como contraste del motor) con un mapa de calibración isotónica. P5, solo en el gemelo alemán, es TabPFN v2 <Cite id="hollmann2025" />, cuyos pesos tienen su propia licencia.</>}
      />
      <Equation
        tex="\mathrm{WoE}_i = \ln\frac{r_i^{NE}/r_T^{NE}}{r_i^{E}/r_T^{E}}, \qquad \text{Points}_{j,b} = \frac{\text{Offset}}{k} - \Big(\beta_j\,\mathrm{WoE}_{j,b} + \frac{\beta_0}{k}\Big)\,\text{Factor}, \qquad \text{Factor} = \frac{\text{PDO}}{\ln 2}"
        caption={t(
          'Weight of evidence of bin i (non-events NE over events E, so a higher WoE is a lower risk) and the points of bin b of characteristic j among k; Offset = 600 - Factor ln 50.',
          'Peso de evidencia del tramo i (no eventos NE sobre eventos E, así un WoE mayor es un riesgo menor) y los puntos del tramo b de la característica j entre k; Offset = 600 - Factor ln 50.',
        )}
      />
      <h3>{t('What each variant shows', 'Qué muestra cada variante')}</h3>
      <L
        items={[
          { en: 'Holdout: the models as they would be validated on day one.', es: 'Muestra reservada: los modelos como se validarían el primer día.' },
          { en: 'Covariate drift, moderate and severe: real holdout rows resampled toward recent delinquency with P(default | x) unchanged. A calibrated model stays calibrated; the PSI must flag the shift.', es: 'Deriva de covariables, moderada y severa: filas reales remuestreadas hacia mora reciente con P(incumplimiento | x) sin cambio. Un modelo calibrado sigue calibrado; el PSI debe detectar el cambio.' },
          { en: 'Prior shift x1.5: 1.5 times the defaults with P(x | default) unchanged. Every PD now under-estimates the default rate, and the Jeffreys and binomial tests must reject.', es: 'Cambio de prior x1,5: 1,5 veces los incumplimientos con P(x | incumplimiento) sin cambio. Toda PD subestima ahora la tasa de incumplimiento, y las pruebas de Jeffreys y binomial deben rechazar.' },
          { en: 'Label noise 5%: discrimination falls for every rung, and the default rate rises (flipping 5% of a 22% default rate adds more defaults than it removes).', es: 'Ruido de etiqueta 5%: la discriminación cae en todo peldaño, y la tasa de incumplimiento sube (invertir el 5% de una tasa de 22% agrega más incumplimientos de los que quita).' },
          { en: 'Small sample: the ladder retrained on 2,000 rows; estimation risk, and whether the challengers\' gain survives with less data.', es: 'Muestra pequeña: la escalera reentrenada con 2.000 filas; riesgo de estimación, y si la ganancia de los retadores sobrevive con menos datos.' },
          { en: 'German twin: the whole ladder on small data, with TabPFN, and the cost matrix as the decision.', es: 'Gemelo alemán: toda la escalera con pocos datos, con TabPFN, y la matriz de costos como decisión.' },
        ]}
      />
      <h3>{t('How to read the views', 'Cómo leer las vistas')}</h3>
      <P
        en="Model shows the ladder and the internals of each rung. Validation shows the battery a validator and a supervisor would run, with every light re-computed under the policy in the rail: the thresholds are policy choices, never regulation, since the ECB's validation-reporting instructions fix the tests and no pass or fail threshold. Impact compares the champion and the challenger at the same approval rate. Findings lists what the battery found, under the case's severity policy. Variants compares the regimes. Every view carries its lane (live: recomputed in your browser; replay: read from a committed artifact) and its data (real or synthetic)."
        es="Modelo muestra la escalera y el interior de cada peldaño. Validación muestra la batería que correrían un validador y un supervisor, con cada luz recalculada con la política del panel: los umbrales son elecciones de política, nunca regulación, porque las instrucciones de reporte de validación del BCE fijan las pruebas y ningún umbral de aprobación. Impacto compara al campeón y al retador con la misma tasa de aprobación. Hallazgos lista lo que encontró la batería, con la política de severidad del caso. Variantes compara los regímenes. Cada vista lleva su carril (en vivo: recalculado en el navegador; reproducción: leído de un artefacto comprometido) y sus datos (reales o sintéticos)."
      />
    </>
  );
}
