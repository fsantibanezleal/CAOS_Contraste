// The methods behind the cases, transcribed from research dossiers 04 (credit-risk models: sections A, B, J) and 06
// (model risk management and the validation test catalogue: sections A, C). Every display equation carries a
// caption that defines its symbols; every section ends with its references.
import { Cite, DocPage, DocSection, Equation, Figure, Tabs, useShellLang } from '@fasl-work/caos-app-shell';
import { ValidationFigure } from '../architecture/figures';
import { L, P, useT } from '../content/bi';

function ModelRisk() {
  const t = useT();
  return (
    <>
      <DocSection title={{ en: 'Model risk and its management', es: 'El riesgo de modelo y su gestión' }} refs={['sr117', 'sr262', 'ss123', 'egim']}>
        <P
          en={<>The 2011 US guidance defines a model as a quantitative method that applies statistical, economic, financial or mathematical theories to process input data into quantitative estimates, with an input, a processing and a reporting component, and model risk as the potential for adverse consequences from decisions based on incorrect or misused model outputs <Cite id="sr117" />. Its two sources are a model with fundamental errors and a model used incorrectly or inappropriately; the risk grows with complexity, with uncertainty about inputs and assumptions, with broader use and with larger potential impact.</>}
          es={<>La guía estadounidense de 2011 define un modelo como un método cuantitativo que aplica teorías estadísticas, económicas, financieras o matemáticas para transformar datos de entrada en estimaciones cuantitativas, con un componente de entrada, uno de procesamiento y uno de reporte, y el riesgo de modelo como las posibles consecuencias adversas de decisiones basadas en resultados de modelos incorrectos o mal usados <Cite id="sr117" />. Sus dos fuentes son un modelo con errores fundamentales y un modelo usado de forma incorrecta o inapropiada; el riesgo crece con la complejidad, con la incertidumbre sobre entradas y supuestos, con un uso más amplio y con un impacto potencial mayor.</>}
        />
        <P
          en={<>Validation has three core elements: the evaluation of conceptual soundness, ongoing monitoring (including process verification and benchmarking), and outcomes analysis (including back-testing), which "should involve a range of tests because any individual test will have weaknesses" <Cite id="sr117" />. The guidance of 17 April 2026 superseded the 2011 text in the United States: it narrows the definition (it excludes simple arithmetic and deterministic rules), states that it sets no enforceable standards, and leaves generative and agentic AI out of its scope <Cite id="sr262" />. The PRA's five principles keep the structure, with a firm-wide tiering by materiality and complexity <Cite id="ss123" />, and the ECB guide to internal models adds the expectations for machine learning in IRB models <Cite id="egim" />.</>}
          es={<>La validación tiene tres elementos centrales: la evaluación de la solidez conceptual, el monitoreo continuo (con verificación de procesos y comparación con referencias) y el análisis de resultados (con backtesting), que "debe incluir un abanico de pruebas, porque cualquier prueba individual tiene debilidades" <Cite id="sr117" />. La guía del 17 de abril de 2026 reemplazó al texto de 2011 en Estados Unidos: estrecha la definición (excluye la aritmética simple y las reglas deterministas), declara que no fija estándares exigibles y deja fuera de su alcance la IA generativa y agéntica <Cite id="sr262" />. Los cinco principios de la PRA mantienen la estructura, con una clasificación de toda la entidad por materialidad y complejidad <Cite id="ss123" />, y la guía del BCE sobre modelos internos agrega las expectativas para el aprendizaje automático en modelos IRB <Cite id="egim" />.</>}
        />
        <Figure caption={t('How Contraste reads a model: the ladder, the battery, the findings and the impact.', 'Cómo lee Contraste un modelo: la escalera, la batería, los hallazgos y el impacto.')}>
          <ValidationFigure />
        </Figure>
      </DocSection>
      <DocSection title={{ en: 'What a passed test means', es: 'Qué significa una prueba aprobada' }} refs={['ecb2019', 'wp14']}>
        <P
          en={<>A test result is evidence, not a verdict. The ECB's validation-reporting instructions fix the statistics and the p-values an IRB validation reports and no pass or fail threshold <Cite id="ecb2019" />; BCBS Working Paper 14 warns that "at present no really powerful tests of adequate calibration are currently available" once defaults are correlated <Cite id="wp14" />. The thresholds that turn a p-value into a light are therefore a policy, versioned and shown as policy, and a reader can change them in the App.</>}
          es={<>El resultado de una prueba es evidencia, no un veredicto. Las instrucciones del BCE para reportar validaciones fijan los estadísticos y los valores p que reporta una validación IRB y ningún umbral de aprobación <Cite id="ecb2019" />; el Working Paper 14 del BCBS advierte que "por ahora no existen pruebas realmente potentes de una calibración adecuada" cuando los incumplimientos están correlacionados <Cite id="wp14" />. Los umbrales que convierten un valor p en una luz son por eso una política, versionada y mostrada como política, y el lector puede cambiarlos en la App.</>}
        />
      </DocSection>
    </>
  );
}

function Scorecards() {
  const t = useT();
  return (
    <>
      <DocSection title={{ en: 'Weight of evidence and information value', es: 'Peso de evidencia y valor de información' }} refs={['navas2020', 'siddiqi2017']}>
        <P
          en={<>A variable is cut into bins; with non-event (good) and event (default) counts in each bin, the weight of evidence is the log of the share of goods over the share of bads, so a higher WoE is a lower risk, and it is an affine, decreasing transform of the bin's log-odds of default <Cite id="navas2020" />. The information value is Jeffreys' divergence between the two distributions across bins; it is undefined when a bin has no events or no non-events, which is why each bin holds at least 5% of the records.</>}
          es={<>Una variable se corta en tramos; con los conteos de no eventos (buenos) y eventos (incumplimientos) de cada tramo, el peso de evidencia es el logaritmo de la fracción de buenos sobre la fracción de malos, así un WoE mayor es un riesgo menor, y es una transformación afín y decreciente de las log-odds de incumplimiento del tramo <Cite id="navas2020" />. El valor de información es la divergencia de Jeffreys entre ambas distribuciones a través de los tramos; no está definido cuando un tramo no tiene eventos o no eventos, por eso cada tramo contiene al menos el 5% de los registros.</>}
        />
        <Equation
          tex="\mathrm{WoE}_i = \ln\frac{r_i^{NE}/r_T^{NE}}{r_i^{E}/r_T^{E}} = \ln\frac{r_T^{E}}{r_T^{NE}} - \mathrm{logit}(D_i), \qquad \mathrm{IV} = \sum_{i=1}^{n}\left(p_i - q_i\right)\ln\frac{p_i}{q_i}"
          caption={t('r_i^NE and r_i^E: non-events and events in bin i; r_T: their totals; D_i: the bin default rate; p_i and q_i: the bin shares of non-events and events (Navas-Palencia 2020, section 2.1).', 'r_i^NE y r_i^E: no eventos y eventos del tramo i; r_T: sus totales; D_i: la tasa de incumplimiento del tramo; p_i y q_i: las fracciones de no eventos y de eventos del tramo (Navas-Palencia 2020, sección 2.1).')}
        />
        <P
          en="Optimal binning is a mathematical programme: pre-bins from a tree are merged into bins that maximise the information value under constraints on the number of bins, their minimum size and a monotone trend of the default rate (ascending, descending, peak or valley). Contraste declares the direction of every variable before fitting, from its meaning (more delinquency raises risk; a larger limit and larger payments lower it), and lets the solver choose where no direction is declared. The IV screen keeps variables with an information value of at least 0.02, the rule of thumb attributed to Siddiqi, whose exact source page is not verified."
          es="El tramado óptimo es un programa matemático: los pretramos de un árbol se unen en tramos que maximizan el valor de información con restricciones sobre el número de tramos, su tamaño mínimo y una tendencia monótona de la tasa de incumplimiento (creciente, decreciente, pico o valle). Contraste declara la dirección de cada variable antes de ajustar, según su significado (más mora sube el riesgo; un cupo mayor y pagos mayores lo bajan), y deja elegir al solver donde no se declara dirección. El filtro de IV conserva las variables con valor de información de al menos 0,02, la regla práctica atribuida a Siddiqi, cuya página exacta no está verificada."
        />
      </DocSection>
      <DocSection title={{ en: 'The logistic scorecard and its points', es: 'La scorecard logística y sus puntos' }} refs={['siddiqi2017']}>
        <P
          en={<>A logistic regression on the WoE inputs gives the log-odds of default; every coefficient of a sound scorecard is negative on WoE, and a variable whose sign comes out wrong is dropped and the model refitted. The score is scaled so that a reference score means reference odds of good and a fixed number of points doubles the odds <Cite id="siddiqi2017" />, and the points of each bin follow from splitting the offset and the intercept across the k characteristics.</>}
          es={<>Una regresión logística sobre las entradas WoE da las log-odds de incumplimiento; todo coeficiente de una scorecard sólida es negativo sobre el WoE, y una variable cuyo signo resulta errado se elimina y el modelo se reajusta. El puntaje se escala para que un puntaje de referencia signifique odds de buenos de referencia y una cantidad fija de puntos duplique las odds <Cite id="siddiqi2017" />, y los puntos de cada tramo resultan de repartir el offset y el intercepto entre las k características.</>}
        />
        <Equation
          tex="\text{Score} = \text{Offset} + \text{Factor}\,\ln(\text{odds}), \quad \text{Factor} = \frac{\text{PDO}}{\ln 2}, \quad \text{Offset} = \text{Score}_{\text{ref}} - \text{Factor}\,\ln(\text{odds}_{\text{ref}}), \quad \text{Points}_{j,b} = \frac{\text{Offset}}{k} - \Big(\beta_j\,\mathrm{WoE}_{j,b} + \frac{\beta_0}{k}\Big)\text{Factor}"
          caption={t('Odds of good; PDO: points to double the odds (20 in C01); Score_ref = 600 at odds_ref = 50; β_0 and β_j: the intercept and the coefficient of characteristic j; the points are rounded and the score is their sum (formula verified in ING skorecard, dossier 04 A.3).', 'Odds de buenos; PDO: puntos para duplicar las odds (20 en C01); Score_ref = 600 con odds_ref = 50; β_0 y β_j: el intercepto y el coeficiente de la característica j; los puntos se redondean y el puntaje es su suma (fórmula verificada en skorecard de ING, dossier 04 A.3).')}
        />
      </DocSection>
      <DocSection title={{ en: 'Class imbalance and calibration', es: 'Desbalance de clases y calibración' }} refs={['kingzeng2001', 'goorbergh2022', 'zadrozny2002']}>
        <P
          en={<>A PD is a probability used in capital, pricing and provisions, so it must be calibrated, not only ranked. Resampling for imbalance (under-sampling, over-sampling, SMOTE) produces strongly miscalibrated models without a higher AUC <Cite id="goorbergh2022" />; Contraste never resamples before calibration is measured. When a sample is balanced on purpose, the prior correction shifts the intercept back to the population <Cite id="kingzeng2001" />. A model whose scores are not probabilities gets a calibration map fitted on its own slice, never on the test set: Platt scaling or isotonic regression <Cite id="zadrozny2002" />.</>}
          es={<>Una PD es una probabilidad que se usa en capital, precios y provisiones, así que debe estar calibrada, no solo ordenar. El remuestreo por desbalance (submuestreo, sobremuestreo, SMOTE) produce modelos muy mal calibrados sin una AUC mayor <Cite id="goorbergh2022" />; Contraste nunca remuestrea antes de medir la calibración. Cuando una muestra se balancea a propósito, la corrección de prior devuelve el intercepto a la población <Cite id="kingzeng2001" />. Un modelo cuyos puntajes no son probabilidades recibe un mapa de calibración ajustado en su propio tramo, nunca en el de prueba: escalamiento de Platt o regresión isotónica <Cite id="zadrozny2002" />.</>}
        />
        <Equation
          tex="\tilde\beta_0 = \hat\beta_0 - \ln\!\left[\left(\frac{1-\tau}{\tau}\right)\left(\frac{\bar y}{1-\bar y}\right)\right]"
          caption={t('The prior correction of King and Zeng (2001, eq. 7): ȳ is the event share of the sample, τ the event share of the population.', 'La corrección de prior de King y Zeng (2001, ec. 7): ȳ es la fracción de eventos de la muestra, τ la de la población.')}
        />
      </DocSection>
    </>
  );
}

function MachineLearning() {
  const t = useT();
  return (
    <>
      <DocSection title={{ en: 'What the evidence says', es: 'Lo que dice la evidencia' }} refs={['lessmann2015', 'gunnarsson2021', 'grinsztajn2022']}>
        <L
          items={[
            { en: <>Tree ensembles beat plain logistic regression on most retail benchmarks, by a few AUC points; well-binned logistic regression remains competitive, and "outperforming LR can no longer be accepted as a signal of methodological advancement" <Cite id="lessmann2015" />.</>, es: <>Los ensambles de árboles superan a la regresión logística simple en la mayoría de los benchmarks minoristas, por unos pocos puntos de AUC; la regresión logística bien tramada sigue siendo competitiva, y "superar a la RL ya no puede aceptarse como señal de avance metodológico" <Cite id="lessmann2015" />.</> },
            { en: <>Deep networks have not shown an advantage over boosted trees on tabular credit data <Cite id="gunnarsson2021" />, nor on medium-sized tabular data in general <Cite id="grinsztajn2022" />.</>, es: <>Las redes profundas no han mostrado ventaja sobre los árboles potenciados en datos tabulares de crédito <Cite id="gunnarsson2021" />, ni en datos tabulares medianos en general <Cite id="grinsztajn2022" />.</> },
            { en: 'Discrimination and calibration are separate properties: every machine-learning rung needs an explicit calibration map and a calibration test, and the gain of a challenger is a claim only with its interval and its paired test.', es: 'La discriminación y la calibración son propiedades distintas: todo peldaño de aprendizaje automático necesita un mapa de calibración explícito y una prueba de calibración, y la ganancia de un retador es una afirmación solo con su intervalo y su prueba pareada.' },
          ]}
        />
      </DocSection>
      <DocSection title={{ en: 'Glass-box challengers: PLTR and EBM', es: 'Retadores de caja de cristal: PLTR y EBM' }} refs={['dumitrescu2022', 'lou2013', 'nori2019']}>
        <P
          en={<>Penalised logistic tree regression takes threshold rules from short trees, one split per variable and two splits per pair, as inputs of an L1 logistic regression, and keeps the interpretability of a logistic model while competing with random forests <Cite id="dumitrescu2022" />. The explainable boosting machine is a generalised additive model with a few pairwise terms, its shape functions learned by cyclic gradient boosting with a low learning rate <Cite id="lou2013" /> <Cite id="nori2019" />; each term reads as a points table, so its reasons are exact.</>}
          es={<>La regresión logística penalizada con árboles toma reglas de umbral de árboles cortos, una división por variable y dos por par, como entradas de una regresión logística L1, y conserva la interpretabilidad de un modelo logístico mientras compite con los bosques aleatorios <Cite id="dumitrescu2022" />. La máquina de boosting explicable es un modelo aditivo generalizado con algunos términos de pares, cuyas funciones de forma se aprenden con gradient boosting cíclico de tasa baja <Cite id="lou2013" /> <Cite id="nori2019" />; cada término se lee como una tabla de puntos, así sus razones son exactas.</>}
        />
        <Equation
          tex="g\big(\mathbb{E}[y]\big) = \beta_0 + \sum_j f_j(x_j) + \sum_{(i,j)} f_{ij}(x_i, x_j)"
          caption={t('The EBM: g is the logit link; f_j the shape function of feature j; f_ij a pairwise term. In C01: monotone where a direction is declared, five pairs, at most 64 bins per main term.', 'El EBM: g es el enlace logit; f_j la función de forma de la variable j; f_ij un término de pares. En C01: monótono donde se declara una dirección, cinco pares, a lo más 64 tramos por término principal.')}
        />
      </DocSection>
      <DocSection title={{ en: 'Monotone gradient boosting and its reasons', es: 'Gradient boosting monótono y sus razones' }} refs={['lundberg2017', 'lundberg2020', 'regb']}>
        <P
          en={<>LightGBM and XGBoost accept a monotone constraint per feature; Contraste verifies it on individual conditional expectation curves, record by record, rather than trusting the flag. Reasons for an adverse decision come from Shapley values on the log-odds scale <Cite id="lundberg2017" />, computed exactly for trees by TreeSHAP <Cite id="lundberg2020" />: the four features that raise the risk most, the number Regulation B says is likely to be helpful <Cite id="regb" />. Their stability is measured by refitting on bootstrap samples, because correlated features split credit arbitrarily.</>}
          es={<>LightGBM y XGBoost aceptan una restricción monótona por variable; Contraste la verifica en las curvas de expectativa condicional individual, registro por registro, en vez de confiar en la opción. Las razones de una decisión adversa vienen de los valores de Shapley en la escala de log-odds <Cite id="lundberg2017" />, calculados de forma exacta para árboles por TreeSHAP <Cite id="lundberg2020" />: las cuatro variables que más suben el riesgo, el número que según Regulation B probablemente ayude <Cite id="regb" />. Su estabilidad se mide reajustando en muestras bootstrap, porque las variables correlacionadas reparten el crédito de forma arbitraria.</>}
        />
        <Equation tex="f(x) = \phi_0 + \sum_{j} \phi_j(x)" caption={t('Additive attribution: φ_0 is the expected log-odds over the background data, φ_j the Shapley value of feature j for record x.', 'Atribución aditiva: φ_0 es la log-odds esperada sobre los datos de fondo, φ_j el valor de Shapley de la variable j para el registro x.')} />
      </DocSection>
      <DocSection title={{ en: 'The tabular foundation model', es: 'El modelo fundacional tabular' }} refs={['hollmann2025']}>
        <P
          en={<>TabPFN learns in context, with no per-dataset training, and is strongest on small data <Cite id="hollmann2025" />. The package's default weights carry a non-commercial licence; Contraste uses the v2 weights, under the Prior Labs License v1.1 (Apache 2.0 with an attribution clause), only on the small German case; its own view shows the licence of the weights and the attribution, and the Context group lists it with every engine.</>}
          es={<>TabPFN aprende en contexto, sin entrenamiento por conjunto de datos, y es más fuerte con pocos datos <Cite id="hollmann2025" />. Los pesos por defecto del paquete tienen una licencia no comercial; Contraste usa los pesos v2, bajo la Prior Labs License v1.1 (Apache 2.0 con una cláusula de atribución), solo en el caso alemán pequeño; su propia vista muestra la licencia de los pesos y la atribución, y el grupo Contexto la lista junto a cada motor.</>}
        />
      </DocSection>
    </>
  );
}

function Discrimination() {
  const t = useT();
  return (
    <>
      <DocSection title={{ en: 'AUC and its variance', es: 'AUC y su varianza' }} refs={['ecb2019', 'hanley1982', 'wp14']}>
        <P
          en={<>The AUC is the probability that a randomly chosen defaulter is ranked riskier than a randomly chosen non-defaulter, ties counting one half <Cite id="hanley1982" />. Its variance comes from DeLong-type structural components, as the ECB instructions write it <Cite id="ecb2019" />. The accuracy ratio of the CAP curve and the Gini coefficient equal 2 AUC - 1 when both are computed on the same ranking with consistent ties <Cite id="wp14" />.</>}
          es={<>La AUC es la probabilidad de que un incumplidor elegido al azar quede ordenado como más riesgoso que un no incumplidor elegido al azar, contando los empates como la mitad <Cite id="hanley1982" />. Su varianza viene de los componentes estructurales de tipo DeLong, como las escriben las instrucciones del BCE <Cite id="ecb2019" />. La razón de precisión de la curva CAP y el coeficiente de Gini valen 2 AUC - 1 cuando ambos se calculan sobre el mismo orden con empates consistentes <Cite id="wp14" />.</>}
        />
        <Equation
          tex="\mathrm{AUC} = \frac{1}{|A|\,|B|}\sum_{a\in A}\sum_{b\in B} u_{a,b}, \qquad s^2 = \frac{\widehat{\mathrm{var}}(V_{10})}{|A|} + \frac{\widehat{\mathrm{var}}(V_{01})}{|B|}"
          caption={t('A: defaulters; B: non-defaulters; u_ab = 1 when a is ranked riskier than b, 1/2 on a tie, 0 otherwise; V_10 and V_01: the structural components, the mean of u over the other group (ECB 2019, Annex 3.1).', 'A: incumplidores; B: no incumplidores; u_ab = 1 cuando a queda como más riesgoso que b, 1/2 en un empate, 0 si no; V_10 y V_01: los componentes estructurales, la media de u sobre el otro grupo (BCE 2019, Anexo 3.1).')}
        />
      </DocSection>
      <DocSection title={{ en: 'Has discrimination deteriorated, and is a challenger better?', es: '¿Se deterioró la discriminación, y es mejor un retador?' }} refs={['ecb2019', 'delong1988']}>
        <P
          en={<>The ECB test compares the current AUC with the AUC at initial validation, taken as known; a small p-value says the ranking deteriorated <Cite id="ecb2019" />. In Contraste the initial AUC is the one on the calibration slice, the development's first out-of-sample measurement. A challenger and the champion scored on the same obligors are compared with the DeLong test, whose covariance accounts for the pairing <Cite id="delong1988" />.</>}
          es={<>La prueba del BCE compara la AUC actual con la AUC de la validación inicial, tomada como conocida; un valor p pequeño dice que el orden se deterioró <Cite id="ecb2019" />. En Contraste la AUC inicial es la del tramo de calibración, la primera medición fuera de muestra del desarrollo. Un retador y el campeón puntuados sobre los mismos deudores se comparan con la prueba de DeLong, cuya covarianza considera el pareo <Cite id="delong1988" />.</>}
        />
        <Equation
          tex="S = \frac{\mathrm{AUC}_{init} - \mathrm{AUC}_{curr}}{s}, \quad p = 1 - \Phi(S); \qquad z = \frac{\widehat{\mathrm{AUC}}_1 - \widehat{\mathrm{AUC}}_2}{\sqrt{\mathbf{S}_{11} + \mathbf{S}_{22} - 2\,\mathbf{S}_{12}}}, \quad \mathbf{S} = \frac{S_{10}}{|A|} + \frac{S_{01}}{|B|}"
          caption={t('Left: the ECB test against the initial AUC, H0: the development AUC is not above the current one. Right: DeLong, H0: equal AUCs; S_10 and S_01 are the covariance matrices of the two models\' structural components.', 'Izquierda: la prueba del BCE contra la AUC inicial, H0: la AUC de desarrollo no supera a la actual. Derecha: DeLong, H0: AUC iguales; S_10 y S_01 son las matrices de covarianza de los componentes estructurales de ambos modelos.')}
        />
        <Equation
          tex="\mathrm{KS} = \sup_s \left| F_D(s) - F_{ND}(s) \right|"
          caption={t('Kolmogorov-Smirnov: the largest gap between the score distributions of defaulters (F_D) and non-defaulters (F_ND); reported as a separation measure.', 'Kolmogorov-Smirnov: la mayor brecha entre las distribuciones del puntaje de incumplidores (F_D) y no incumplidores (F_ND); se reporta como medida de separación.')}
        />
      </DocSection>
    </>
  );
}

function Calibration() {
  const t = useT();
  return (
    <>
      <DocSection title={{ en: 'The level: is the average PD right?', es: 'El nivel: ¿es correcta la PD media?' }} refs={['ecb2019', 'brown2001', 'wp14', 'cre31']}>
        <P
          en={<>The ECB's back-test is the Jeffreys test, per grade and for the portfolio: with N obligors, D defaults and the PD applied at the start, the p-value is the posterior probability, under the Jeffreys prior, that the true PD is below the PD applied <Cite id="ecb2019" /> <Cite id="brown2001" />. A small p-value says the PD is under-estimated. The binomial test asks the same question by counting; its type I error "can be much larger than the nominal level" when defaults are correlated, and the Vasicek-adjusted version with an asset correlation corrects for that <Cite id="wp14" />. Contraste uses the QRRE correlation of the Basel framework, R = 0.04 <Cite id="cre31" />.</>}
          es={<>El backtest del BCE es la prueba de Jeffreys, por grado y para la cartera: con N deudores, D incumplimientos y la PD aplicada al inicio, el valor p es la probabilidad posterior, con la prior de Jeffreys, de que la PD verdadera sea menor que la aplicada <Cite id="ecb2019" /> <Cite id="brown2001" />. Un valor p pequeño dice que la PD está subestimada. La prueba binomial hace la misma pregunta contando; su error de tipo I "puede ser mucho mayor que el nivel nominal" cuando los incumplimientos están correlacionados, y la versión ajustada de Vasicek con una correlación de activos lo corrige <Cite id="wp14" />. Contraste usa la correlación QRRE del marco de Basilea, R = 0,04 <Cite id="cre31" />.</>}
        />
        <Equation
          tex="p = F_{\mathrm{Beta}\left(D+\frac12,\; N-D+\frac12\right)}(\mathrm{PD}), \qquad \frac{k^*}{n} \approx \Phi\!\left(\frac{\Phi^{-1}(\mathrm{PD}) + \sqrt{\rho}\,\Phi^{-1}(q)}{\sqrt{1-\rho}}\right)"
          caption={t('Left: the Jeffreys p-value (ECB 2019, 2.5.3.1). Right: the large-portfolio critical default rate of the Vasicek-adjusted binomial test at confidence q and asset correlation ρ; WP14 gives 19, 35, 49, 63 and 77 defaults out of 1,000 at a PD of 1% and ρ = 0, 5, 10, 15 and 20%.', 'Izquierda: el valor p de Jeffreys (BCE 2019, 2.5.3.1). Derecha: la tasa crítica de incumplimiento de la prueba binomial ajustada de Vasicek para una cartera grande, con confianza q y correlación de activos ρ; WP14 da 19, 35, 49, 63 y 77 incumplimientos de 1.000 con PD de 1% y ρ = 0, 5, 10, 15 y 20%.')}
        />
      </DocSection>
      <DocSection title={{ en: 'The fit: is the PD right across the range?', es: 'El ajuste: ¿es correcta la PD en todo el rango?' }} refs={['wp14', 'hosmer1980', 'spiegelhalter1986']}>
        <P
          en={<>The chi-square over grades sums the standardised gaps of the K + 1 grades <Cite id="wp14" />; Hosmer-Lemeshow does the same over deciles of the predicted risk <Cite id="hosmer1980" />; Spiegelhalter's test works at obligor level, without bins, on the Brier score <Cite id="spiegelhalter1986" />. At thousands of obligors these tests reject deviations too small to matter, and WP14 warns that the chi-square under-states its type I error under default dependence. This is why Contraste's severity policy weighs a failed level test more than a failed fit test.</>}
          es={<>El chi-cuadrado sobre grados suma las brechas estandarizadas de los K + 1 grados <Cite id="wp14" />; Hosmer-Lemeshow hace lo mismo sobre deciles del riesgo predicho <Cite id="hosmer1980" />; la prueba de Spiegelhalter trabaja a nivel de deudor, sin tramos, sobre el puntaje de Brier <Cite id="spiegelhalter1986" />. Con miles de deudores estas pruebas rechazan desvíos demasiado pequeños para importar, y WP14 advierte que el chi-cuadrado subestima su error de tipo I con dependencia entre incumplimientos. Por eso la política de severidad de Contraste pesa más una prueba de nivel fallida que una de ajuste.</>}
        />
        <Equation
          tex="T_K = \sum_{i=0}^{K}\frac{(n_i p_i - \theta_i)^2}{n_i p_i (1-p_i)}, \qquad Z = \frac{O(\mathrm{Brier}) - \frac1N\sum_j f_j(1-f_j)}{\sqrt{\frac{1}{N^2}\sum_j f_j(1-f_j)(1-2f_j)^2}}"
          caption={t('Left: n_i obligors, θ_i defaults and PD p_i in grade i; under H0, T_K tends to a chi-square with K + 1 degrees of freedom. Right: Spiegelhalter, forecasts f_j; Z is standard normal under H0: p_j = f_j for all j.', 'Izquierda: n_i deudores, θ_i incumplimientos y PD p_i en el grado i; bajo H0, T_K tiende a una chi-cuadrado con K + 1 grados de libertad. Derecha: Spiegelhalter, pronósticos f_j; Z es normal estándar bajo H0: p_j = f_j para todo j.')}
        />
      </DocSection>
      <DocSection title={{ en: 'Brier score, its decomposition, and ECE', es: 'Puntaje de Brier, su descomposición y ECE' }} refs={['brier1950', 'murphy1973', 'naeini2015']}>
        <Equation
          tex="\mathrm{BS} = \frac1N\sum_j (f_j - d_j)^2 = \underbrace{\frac1N\sum_k n_k(\bar f_k - \bar d_k)^2}_{\text{reliability}} - \underbrace{\frac1N\sum_k n_k(\bar d_k - \bar d)^2}_{\text{resolution}} + \underbrace{\bar d(1-\bar d)}_{\text{uncertainty}}, \qquad \mathrm{ECE} = \sum_{m}\frac{|B_m|}{n}\left|\bar y(B_m) - \bar p(B_m)\right|"
          caption={t('Brier (1950) and Murphy\'s partition (1973), exact when the forecast is constant within each grade k; d_j: the outcome; ECE over M bins B_m of the predicted PD (Pakdaman Naeini et al. 2015). Both are descriptive.', 'Brier (1950) y la partición de Murphy (1973), exacta cuando el pronóstico es constante dentro de cada grado k; d_j: el resultado; ECE sobre M tramos B_m de la PD predicha (Pakdaman Naeini et al. 2015). Ambas son descriptivas.')}
        />
      </DocSection>
    </>
  );
}

function Stability() {
  const t = useT();
  return (
    <>
      <DocSection title={{ en: 'Population and characteristic stability', es: 'Estabilidad de la población y de las características' }} refs={['yurdakul2020']}>
        <P
          en={<>The population stability index compares the distribution of a score (or, as the CSI, of an input) between a development sample and a current one, over bins fixed in advance. The bands 0.10 and 0.25 are a convention with no control of the type I error; Yurdakul and Naranjo show that, scaled by the sample sizes, the PSI is approximately chi-square, which gives a benchmark with a known error rate <Cite id="yurdakul2020" />. Their Table 2 gives 0.338, 0.169, 0.085 and 0.034 for ten bins at 5% with 100, 200, 400 and 1,000 records in each sample.</>}
          es={<>El índice de estabilidad poblacional compara la distribución de un puntaje (o, como CSI, de una entrada) entre una muestra de desarrollo y una actual, sobre tramos fijados de antemano. Las bandas 0,10 y 0,25 son una convención sin control del error de tipo I; Yurdakul y Naranjo muestran que, escalado por los tamaños de muestra, el PSI es aproximadamente chi-cuadrado, lo que da un umbral con una tasa de error conocida <Cite id="yurdakul2020" />. Su Tabla 2 da 0,338, 0,169, 0,085 y 0,034 para diez tramos al 5% con 100, 200, 400 y 1.000 registros en cada muestra.</>}
        />
        <Equation
          tex="\mathrm{PSI} = \sum_{i=1}^{B}(a_i - e_i)\ln\frac{a_i}{e_i}, \qquad \text{reject when}\;\; \mathrm{PSI} > \left(\frac1n + \frac1m\right)\chi^2_{1-\alpha,\,B-1}"
          caption={t('e_i and a_i: the development and current shares of bin i; n and m: the two sample sizes; B: the number of bins (Yurdakul and Naranjo 2020, Theorem 3.3).', 'e_i y a_i: las fracciones de desarrollo y actual del tramo i; n y m: los dos tamaños de muestra; B: el número de tramos (Yurdakul y Naranjo 2020, Teorema 3.3).')}
        />
      </DocSection>
      <DocSection title={{ en: 'Concentration in the grades', es: 'Concentración en los grados' }} refs={['ecb2019']}>
        <P
          en={<>The ECB measures concentration with a Herfindahl index of the grade frequencies and tests whether it rose since the development <Cite id="ecb2019" />; a rating system that piles obligors into few grades loses its ability to differentiate risk.</>}
          es={<>El BCE mide la concentración con un índice de Herfindahl de las frecuencias de los grados y prueba si aumentó desde el desarrollo <Cite id="ecb2019" />; un sistema de calificación que amontona deudores en pocos grados pierde su capacidad de diferenciar el riesgo.</>}
        />
        <Equation
          tex="CV = \sqrt{K\sum_{i=1}^{K}\Big(R_i - \frac1K\Big)^2}, \qquad HI = 1 + \frac{\ln\big((CV^2 + 1)/K\big)}{\ln K}, \qquad p = 1 - \Phi\!\left(\frac{\sqrt{K-1}\,(CV_{curr} - CV_{init})}{\sqrt{CV_{curr}^2\,(0.5 + CV_{curr}^2)}}\right)"
          caption={t('R_i: the relative frequency of grade i among K; H0: the current index is not above the index at development (ECB 2019, 2.5.5.3).', 'R_i: la frecuencia relativa del grado i entre K; H0: el índice actual no supera al de desarrollo (BCE 2019, 2.5.5.3).')}
        />
      </DocSection>
    </>
  );
}

export function Methodology() {
  const lang = useShellLang();
  const t = useT();
  return (
    <DocPage
      wide
      title={{ en: 'Methodology', es: 'Metodología' }}
      lede={t('The model families and the validation tests behind the cases, with their equations, assumptions and sources.', 'Las familias de modelos y las pruebas de validación detrás de los casos, con sus ecuaciones, supuestos y fuentes.')}
    >
      <Tabs
        ariaLabel={lang === 'es' ? 'Partes de la metodología' : 'Parts of the methodology'}
        tabs={[
          { id: 'model-risk', label: t('Model risk', 'Riesgo de modelo'), content: <ModelRisk /> },
          { id: 'scorecards', label: t('Scorecards', 'Scorecards'), content: <Scorecards /> },
          { id: 'machine-learning', label: t('Machine learning', 'Aprendizaje automático'), content: <MachineLearning /> },
          { id: 'discrimination', label: t('Discrimination', 'Discriminación'), content: <Discrimination /> },
          { id: 'calibration', label: t('Calibration', 'Calibración'), content: <Calibration /> },
          { id: 'stability', label: t('Stability', 'Estabilidad'), content: <Stability /> },
        ]}
      />
    </DocPage>
  );
}
