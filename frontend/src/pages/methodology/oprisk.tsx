// The Methodology section on operational risk (U12): the loss distribution approach with its truncated severity and its
// body and tail splice, the aggregate loss by Monte Carlo, Panjer recursion and FFT with the single loss approximation,
// the combination of scenarios with loss data, the BCBS 2008 calibration targets, and the Basel III standardised approach
// of OPE25, all as case C17 runs them. Transcribed from research dossier 05 (section F: F.1 to F.6, where Shevchenko 2010
// was verified from arXiv 1008.1108 and the BCBS 160 text from the BIS PDF; the benchmark erratum of 2026-10-13 is applied)
// and dossier 01 (section F: OPE25, in force 2023-01-01, published 2024-07-05, all six formula images read). Every display
// equation carries a caption that defines its symbols. The registry mounts it as one tab of the loss group; one file
// exports one section, so the topic is one `method` section with one part per question, as sub-tabs (ADR-0017 section
// 2.1), each part with its own paragraphs, equations and figure, and one honest callout for the topic.
import { Callout, Cite, DocSection, Equation, Figure, SubTabs, formatNumber, useShellLang } from '@fasl-work/caos-app-shell';
import { P, Ref, T, useT } from '../../content/bi';
import type { MethodologySection } from '../methodologyRegistry';

const W = 480;
const H = 276;

/** The severity of a loss distribution approach: a lognormal body and a generalised Pareto tail, the collection threshold. */
function SeverityFigure() {
  const t = useT();
  const base = 210;
  // a schematic density: a hump at the left and a long tail, drawn as one path in the plane (60..460, 40..base)
  const curve = 'M 60 210 C 78 205 92 80 124 60 C 150 46 168 100 200 150 C 232 186 280 196 340 202 C 390 206 430 208 460 209';
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('A severity density with a collection threshold and a splice point: losses below the collection threshold are not recorded, the body is lognormal up to the splice point and the tail beyond it is a generalised Pareto distribution', 'Una densidad de severidad con un umbral de recolección y un punto de empalme: las pérdidas bajo el umbral de recolección no se registran, el cuerpo es lognormal hasta el punto de empalme y la cola más allá es una Pareto generalizada')}>
      <line className="dg-axis" x1={52} y1={base} x2={466} y2={base} />
      <rect className="dg-fill-warn" x={60} y={44} width={62} height={base - 44} />
      <rect className="dg-fill-accent" x={252} y={44} width={208} height={base - 44} />
      <path className="dg-curve" d={curve} />
      <line className="dg-marker" x1={122} y1={36} x2={122} y2={base + 6} />
      <line className="dg-marker" x1={252} y1={36} x2={252} y2={base + 6} />
      <text className="dg-marker-label" x={122} y={base + 20} textAnchor="middle">H</text>
      <text className="dg-marker-label" x={252} y={base + 20} textAnchor="middle">u</text>
      <text className="dg-note" x={91} y={64} textAnchor="middle">{t('not', 'no')}</text>
      <text className="dg-note" x={91} y={77} textAnchor="middle">{t('recorded', 'registradas')}</text>
      <text className="dg-axis-label" x={187} y={36} textAnchor="middle">{t('lognormal body', 'cuerpo lognormal')}</text>
      <text className="dg-axis-label" x={356} y={36} textAnchor="middle">{t('GPD tail', 'cola GPD')}</text>
      <text className="dg-axis-label" x={W / 2} y={base + 44} textAnchor="middle">{t('loss amount', 'monto de la pérdida')}</text>
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('Illustrative schematic, not a result', 'Esquema ilustrativo, no un resultado')}</text>
    </svg>
  );
}

/** The exceedance curve of the annual loss on log axes, the capital level and the places where the quantile lies. */
function ExceedanceFigure() {
  const t = useT();
  const x0 = 60;
  const x1 = 456;
  const yTop = 34;
  const yBot = 208;
  // a schematic survival function on log-log axes: nearly flat, then falling in a straight heavy-tailed line
  const curve = 'M 60 36 L 150 38 C 190 42 214 70 236 100 L 456 196';
  const level = 150;
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('The probability that the annual loss exceeds each amount on log axes: a curve that falls along a straight heavy tail, a horizontal line at the 99.9 percent level, and the true quantile and the single loss approximation marked where the curve crosses it', 'La probabilidad de que la pérdida anual supere cada monto en ejes logarítmicos: una curva que cae a lo largo de una cola pesada recta, una línea horizontal en el nivel 99,9 por ciento, y el cuantil verdadero y la aproximación de una pérdida marcados donde la curva la cruza')}>
      <line className="dg-axis" x1={x0} y1={yBot} x2={x1 + 10} y2={yBot} />
      <line className="dg-axis" x1={x0} y1={yTop - 6} x2={x0} y2={yBot} />
      {[0, 1, 2, 3].map((i) => (
        <line key={i} className="dg-grid" x1={x0} y1={yTop + i * 58} x2={x1} y2={yTop + i * 58} />
      ))}
      <path className="dg-curve" d={curve} />
      <line className="dg-asymptote" x1={x0} y1={level} x2={x1} y2={level} />
      <text className="dg-edge-label" x={x1} y={level - 6} textAnchor="end">{t('level 0.1 percent', 'nivel 0,1 por ciento')}</text>
      <line className="dg-marker" x1={327} y1={yTop} x2={327} y2={yBot + 6} />
      <line className="dg-marker" x1={346} y1={yTop} x2={346} y2={yBot + 6} />
      <text className="dg-marker-label" x={321} y={yTop + 12} textAnchor="end">{t('true', 'verdadero')}</text>
      <text className="dg-marker-label" x={352} y={yTop + 12} textAnchor="start">SLA</text>
      <text className="dg-axis-label" x={(x0 + x1) / 2} y={yBot + 34} textAnchor="middle">{t('annual loss (log scale)', 'pérdida anual (escala logarítmica)')}</text>
      <text className="dg-axis-label" x={14} y={(yTop + yBot) / 2} textAnchor="middle" transform={`rotate(-90 14 ${(yTop + yBot) / 2})`}>{t('probability of exceeding', 'probabilidad de superar')}</text>
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('Illustrative schematic, not a result', 'Esquema ilustrativo, no un resultado')}</text>
    </svg>
  );
}

/** The internal loss multiplier of OPE25.8 as a function of the loss component over the business indicator component: exact. */
function IlmFigure() {
  const t = useT();
  const lang = useShellLang();
  const x0 = 64;
  const x1 = 452;
  const yTop = 34;
  const yBot = 206;
  // x = LC / BIC in [0, 3], y = ILM in [0.4, 1.6]; the points of the formula ILM = ln(e - 1 + x^0.8)
  const px = (v: number) => x0 + (v / 3) * (x1 - x0);
  const py = (v: number) => yBot - ((v - 0.4) / 1.2) * (yBot - yTop);
  const ilm = (v: number) => Math.log(Math.E - 1 + v ** 0.8);
  const points = Array.from({ length: 61 }, (_, i) => (i / 60) * 3).map((v) => `${Math.round(px(v) * 10) / 10} ${Math.round(py(ilm(v)) * 10) / 10}`);
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('The internal loss multiplier as a function of the loss component over the business indicator component: it rises steeply from just above one half, equals one when the two components are equal and keeps rising more slowly above that', 'El multiplicador de pérdidas internas en función del componente de pérdidas sobre el componente del indicador de negocio: sube con fuerza desde algo más de un medio, es igual a uno cuando los dos componentes son iguales y sigue subiendo más despacio por encima')}>
      <line className="dg-axis" x1={x0} y1={yBot} x2={x1 + 6} y2={yBot} />
      <line className="dg-axis" x1={x0} y1={yTop - 6} x2={x0} y2={yBot} />
      <line className="dg-grid" x1={x0} y1={py(1)} x2={x1} y2={py(1)} />
      <polyline className="dg-curve" fill="none" points={points.join(' ')} />
      <line className="dg-marker" x1={px(1)} y1={yTop} x2={px(1)} y2={yBot + 6} />
      <circle className="dg-node" cx={px(1)} cy={py(1)} r={5} />
      {[0, 1, 2, 3].map((v) => (
        <text key={v} className="dg-tick" x={px(v)} y={yBot + 20} textAnchor="middle">{v}</text>
      ))}
      {[0.5, 1, 1.5].map((v) => (
        <text key={v} className="dg-tick" x={x0 - 8} y={py(v) + 4} textAnchor="end">{formatNumber(v, lang, { decimals: 1 })}</text>
      ))}
      <text className="dg-marker-label" x={px(1) + 8} y={py(1) + 20} textAnchor="start">{t('ILM = 1 when LC = BIC', 'ILM = 1 cuando LC = BIC')}</text>
      <text className="dg-axis-label" x={(x0 + x1) / 2} y={yBot + 40} textAnchor="middle">{t('loss component over business indicator component, LC / BIC', 'componente de pérdidas sobre componente del indicador de negocio, LC / BIC')}</text>
      <text className="dg-axis-label" x={16} y={(yTop + yBot) / 2} textAnchor="middle" transform={`rotate(-90 16 ${(yTop + yBot) / 2})`}>ILM</text>
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('The formula of OPE25.8, drawn exactly', 'La fórmula de OPE25.8, dibujada exacta')}</text>
    </svg>
  );
}

function LdaPart() {
  return (
    <>
      <P
        en={<>In a loss distribution approach the capital is the 99.9 percent quantile of the annual loss of a unit of measure, a business line by event type. The annual loss is the sum of the severities of a random number of losses, with the severities independent of the count. The frequency is Poisson, or negative binomial when the counts are more dispersed than a Poisson allows; the severity is lognormal, Weibull or a spliced model with a body and a tail. The Basel Committee removed the advanced measurement approach because its complexity and the wide range of internal modelling practices made risk-weighted assets hard to compare <Cite id="bcbsd355" />, <Cite id="bcbsd424" />, so Contraste presents the LDA as the economic-capital and ICAAP model and as the natural object of model validation, not as a Pillar 1 model.</>}
        es={<>En un enfoque de distribución de pérdidas el capital es el cuantil 99,9 por ciento de la pérdida anual de una unidad de medida, una línea de negocio por tipo de evento. La pérdida anual es la suma de las severidades de un número aleatorio de pérdidas, con las severidades independientes de la cantidad. La frecuencia es Poisson, o binomial negativa cuando las cantidades están más dispersas de lo que admite una Poisson; la severidad es lognormal, Weibull o un modelo empalmado con cuerpo y cola. El Comité de Basilea retiró el enfoque de medición avanzada porque su complejidad y la gran variedad de prácticas internas de modelación hacían difícil comparar los activos ponderados por riesgo <Cite id="bcbsd355" />, <Cite id="bcbsd424" />, así que Contraste presenta el LDA como el modelo de capital económico y de ICAAP y como el objeto natural de la validación de modelos, no como un modelo del Pilar 1.</>}
      />
      <Equation
        tex={String.raw`\begin{aligned} Z &= \sum_{i=1}^{N} X_i, \qquad N \sim \mathrm{Poisson}(\lambda)\\ f(x) &= \begin{cases} w\,\dfrac{f_b(x)}{F_b(u)}, & x \le u\\[6pt] (1-w)\,g_{\xi,\beta}(x-u), & x > u \end{cases} \qquad G_{\xi,\beta}(y) = 1 - \Bigl(1 + \dfrac{\xi\,y}{\beta}\Bigr)^{-1/\xi} \end{aligned}`}
        caption={<T en={<>The annual loss and the spliced severity (dossier 05, F.2): Z the annual loss, N the annual count of losses with rate λ, X_i the independent severities. For the splice, u is the threshold between body and tail, w = P(X ≤ u) the weight of the body, f_b and F_b the density and distribution of the body (lognormal), g the density of the generalised Pareto distribution G with tail index ξ and scale β, applied to the excess x − u.</>} es={<>La pérdida anual y la severidad empalmada (dossier 05, F.2): Z la pérdida anual, N la cantidad anual de pérdidas con tasa λ, X_i las severidades independientes. Para el empalme, u es el umbral entre cuerpo y cola, w = P(X ≤ u) el peso del cuerpo, f_b y F_b la densidad y la distribución del cuerpo (lognormal), g la densidad de la distribución de Pareto generalizada G con índice de cola ξ y escala β, aplicada al exceso x − u.</>} />}
      />
      <P
        en={<>The splice is the standard construction of extreme value theory: the body carries the bulk of the losses and the generalised Pareto distribution carries the tail, with the tail index ξ setting how heavy it is. Chavez-Demoulin, Embrechts and Neslehova discuss tails with an infinite mean and the failure of the subadditivity of the value at risk when ξ exceeds 1 <Cite id="chavez2006" />: from ξ = 1 the severity has no mean, so the annual loss has none, and every quantity that needs the mean is undefined. Contraste draws its histories from tail indices of 0.6, 0.8, 0.96 and 1.1, and for the last it flags the infinite mean and computes no mean-based quantity.</>}
        es={<>El empalme es la construcción estándar de la teoría de valores extremos: el cuerpo lleva la mayor parte de las pérdidas y la distribución de Pareto generalizada lleva la cola, con el índice de cola ξ fijando cuán pesada es. Chavez-Demoulin, Embrechts y Neslehova tratan las colas de media infinita y el fallo de la subaditividad del valor en riesgo cuando ξ supera 1 <Cite id="chavez2006" />: desde ξ = 1 la severidad no tiene media, así que la pérdida anual tampoco, y toda cantidad que necesite la media queda indefinida. Contraste simula sus historias con índices de cola de 0,6, 0,8, 0,96 y 1,1, y para el último marca la media infinita y no calcula ninguna cantidad basada en la media.</>}
      />
      <Figure caption={<T en="A severity with a body and a tail: losses under the collection threshold H are not recorded (amber), the body is lognormal up to the splice point u and the generalised Pareto tail carries everything beyond it (blue). A fit that ignores H, or a tail forced onto the body, moves the capital." es="Una severidad con cuerpo y cola: las pérdidas bajo el umbral de recolección H no se registran (ámbar), el cuerpo es lognormal hasta el punto de empalme u y la cola de Pareto generalizada lleva todo lo que está más allá (azul). Un ajuste que ignora H, o una cola forzada sobre el cuerpo, mueve el capital." />}>
        <SeverityFigure />
      </Figure>
      <P
        en={<>A bank records only the losses above a collection threshold H, for example EUR 20,000 or EUR 10,000. The severity must then be fitted as a distribution truncated at H, and the observed frequency must be scaled up by the share of losses the threshold hides; ignoring this biases the capital <Cite id="mignola2007" />, <Cite id="cope2009" />. Case C17 makes the bias visible. Its first rung fits a lognormal to the recorded losses as if the threshold did not exist, the biased baseline; the second fits the truncated lognormal and rescales the frequency; the third fits the spliced severity. Every history is drawn by a generator whose annual loss distribution is known, with the losses under the threshold removed as a bank would not record them, so each rung is judged against the true 99.9 percent quantile.</>}
        es={<>Un banco registra solo las pérdidas sobre un umbral de recolección H, por ejemplo EUR 20.000 o EUR 10.000. La severidad debe entonces ajustarse como una distribución truncada en H, y la frecuencia observada debe escalarse por la parte de las pérdidas que el umbral oculta; ignorarlo sesga el capital <Cite id="mignola2007" />, <Cite id="cope2009" />. El caso C17 hace visible el sesgo. Su primer peldaño ajusta una lognormal a las pérdidas registradas como si el umbral no existiera, la línea base sesgada; el segundo ajusta la lognormal truncada y reescala la frecuencia; el tercero ajusta la severidad empalmada. Cada historia la simula un generador cuya distribución de pérdida anual se conoce, con las pérdidas bajo el umbral eliminadas como un banco no las registraría, así que cada peldaño se juzga contra el cuantil verdadero al 99,9 por ciento.</>}
      />
      <Equation
        tex={String.raw`f_H(x) = \frac{f(x)}{1 - F(H)}, \quad x > H, \qquad \lambda_{\mathrm{full}} = \frac{\lambda_{\mathrm{obs}}}{1 - F(H)}`}
        caption={<T en={<>The truncated severity and the rescaled frequency (dossier 05, F.2): f and F the density and distribution of the severity before truncation, H the collection threshold, f_H the density of the recorded losses, λ_obs the rate of recorded losses per year and λ_full the rate of all losses, recorded or not, that the aggregate loss needs.</>} es={<>La severidad truncada y la frecuencia reescalada (dossier 05, F.2): f y F la densidad y la distribución de la severidad antes del truncamiento, H el umbral de recolección, f_H la densidad de las pérdidas registradas, λ_obs la tasa de pérdidas registradas por año y λ_full la tasa de todas las pérdidas, registradas o no, que necesita la pérdida agregada.</>} />}
      />
    </>
  );
}

function AggregationPart() {
  return (
    <>
      <P
        en={<>The distribution of the annual loss has no closed form, and three computations are standard. Monte Carlo simulates the count, then that many severities, and sums them; the error of a quantile falls as the inverse square root of the number of simulated years, so the 99.9 percent quantile needs a very large number of years. The Panjer recursion computes the compound probabilities exactly on a discretised severity for a frequency in the (a, b, 0) class <Cite id="panjer1981" />, <Cite id="shevchenko2010" />. The fast Fourier transform discretises the severity on a grid, transforms it, applies the probability generating function of the frequency and inverts; it needs zero padding against aliasing and, optionally, an exponential tilt (Shevchenko, section 6.2). Contraste reports all three on the same distribution, so a disagreement is a defect of a method and not a feature of the data.</>}
        es={<>La distribución de la pérdida anual no tiene forma cerrada, y hay tres cálculos estándar. Monte Carlo simula la cantidad, luego esa cantidad de severidades, y las suma; el error de un cuantil cae como la inversa de la raíz cuadrada del número de años simulados, así que el cuantil 99,9 por ciento necesita una cantidad muy grande de años. La recursión de Panjer calcula las probabilidades compuestas de forma exacta sobre una severidad discretizada para una frecuencia de la clase (a, b, 0) <Cite id="panjer1981" />, <Cite id="shevchenko2010" />. La transformada rápida de Fourier discretiza la severidad en una grilla, la transforma, aplica la función generadora de probabilidad de la frecuencia y la invierte; necesita relleno con ceros contra el aliasing y, de forma opcional, una inclinación exponencial (Shevchenko, sección 6.2). Contraste informa las tres sobre la misma distribución, así que un desacuerdo es un defecto de un método y no una propiedad de los datos.</>}
      />
      <Equation
        tex={String.raw`\begin{aligned} h_n &= \frac{1}{1 - a f_0}\sum_{j=1}^{n}\Bigl(a + \frac{b\,j}{n}\Bigr) f_j\, h_{n-j}, \qquad h_0 = \sum_{k=0}^{\infty} f_0^{\,k}\, p_k\\ \text{Poisson}(\lambda):&\ a = 0,\ b = \lambda,\ h_0 = e^{\lambda (f_0 - 1)}\\ \text{NegBin}(r, q):&\ a = 1 - q,\ b = (1-q)(r-1),\ h_0 = \Bigl(1 + (1 - f_0)\tfrac{1-q}{q}\Bigr)^{-r} \end{aligned}`}
        caption={<T en={<>The Panjer recursion (Shevchenko, Theorem 5.2, <Ref>(36)</Ref>, and Table 1; dossier 05, F.3): h_n = P(Z = nΔ) the compound probabilities on a grid of step Δ, f_j = P(X = jΔ) the discretised severity, p_n = (a + b/n) p(n−1) the frequency in the (a, b, 0) class. The cost is of order n², and the recursion is numerically stable for the Poisson and negative binomial frequencies.</>} es={<>La recursión de Panjer (Shevchenko, Teorema 5.2, <Ref>(36)</Ref>, y Tabla 1; dossier 05, F.3): h_n = P(Z = nΔ) las probabilidades compuestas en una grilla de paso Δ, f_j = P(X = jΔ) la severidad discretizada, p_n = (a + b/n) p(n−1) la frecuencia de la clase (a, b, 0). El costo es de orden n², y la recursión es numéricamente estable para las frecuencias Poisson y binomial negativa.</>} />}
      />
      <P
        en={<>The engine is validated on the benchmark of Shevchenko, Example 9.4 and Table 2: a Poisson frequency with rate 100 and a lognormal severity with parameters 0 and 2 have an annual loss with mean 738.9056, variance 298,095.7987 and skewness 40.3428. Panjer with a central-difference discretisation of step 1 gives a distribution function of 0.998999329 at 5,847 and of 0.999000217 at 5,849, so the 99.9 percent quantile is 5,849; the first value had been read at 5,849 in an earlier dossier and was corrected on 2026-10-13 after re-reading the table. Monte Carlo, Panjer and FFT must reproduce these numbers to a stated tolerance, and the first test of the case, the benchmark reproduction, is that reproduction.</>}
        es={<>El motor se valida con el benchmark de Shevchenko, Ejemplo 9.4 y Tabla 2: una frecuencia Poisson de tasa 100 y una severidad lognormal con parámetros 0 y 2 tienen una pérdida anual de media 738,9056, varianza 298.095,7987 y asimetría 40,3428. Panjer con una discretización de diferencia central de paso 1 da una función de distribución de 0,998999329 en 5.847 y de 0,999000217 en 5.849, así que el cuantil 99,9 por ciento es 5.849; el primer valor se había leído en 5.849 en un dossier anterior y se corrigió el 2026-10-13 al releer la tabla. Monte Carlo, Panjer y FFT deben reproducir estos números dentro de una tolerancia declarada, y la primera prueba del caso, la reproducción del benchmark, es esa reproducción.</>}
      />
      <Figure caption={<T en="The probability that the annual loss exceeds each amount, on log axes: after the flat part the curve falls along a straight heavy tail. The capital is where it crosses the 0.1 percent level; the single loss approximation reads that crossing from the severity alone and lands near the true quantile when the tail is heavy." es="La probabilidad de que la pérdida anual supere cada monto, en ejes logarítmicos: tras el tramo plano la curva cae a lo largo de una cola pesada recta. El capital está donde cruza el nivel de 0,1 por ciento; la aproximación de una pérdida lee ese cruce desde la severidad sola y cae cerca del cuantil verdadero cuando la cola es pesada." />}>
        <ExceedanceFigure />
      </Figure>
      <P
        en={<>For a subexponential severity the tail of the annual loss behaves like the expected count times the tail of one loss, which gives the single loss approximation of the quantile (Shevchenko, equation 70, after Embrechts, Kluppelberg and Mikosch, Theorem 1.3.9, and Bocker and Kluppelberg 2005). For a Poisson frequency and a generalised Pareto severity it is closed-form and scales like λ to the power ξ, so it is extremely sensitive to the tail index. Shevchenko shows that it converges to the exact quantile for heavy tails but is poor for a lognormal severity with parameter 1 at practical quantiles <Cite id="shevchenko2010" />. A correction by the mean of the severity for finite-mean laws is attributed to Bocker and Sprittulla (Risk, 2006), and Degen studies the approximation as a function of the tail index and finds a problematic zone near ξ = 1 <Cite id="degen2010" />; second-order expansions are reviewed by Peters, Targino and Shevchenko <Cite id="peters2013" />. The commonly quoted corrected form was not checked against either primary text, and the case labels it UNVERIFIED wherever it appears.</>}
        es={<>Para una severidad subexponencial la cola de la pérdida anual se comporta como la cantidad esperada por la cola de una sola pérdida, lo que da la aproximación de una pérdida del cuantil (Shevchenko, ecuación 70, siguiendo a Embrechts, Kluppelberg y Mikosch, Teorema 1.3.9, y a Bocker y Kluppelberg 2005). Para una frecuencia Poisson y una severidad de Pareto generalizada es de forma cerrada y escala como λ elevado a ξ, así que es extremadamente sensible al índice de cola. Shevchenko muestra que converge al cuantil exacto en colas pesadas pero es pobre para una severidad lognormal con parámetro 1 en cuantiles prácticos <Cite id="shevchenko2010" />. Una corrección por la media de la severidad para leyes de media finita se atribuye a Bocker y Sprittulla (Risk, 2006), y Degen estudia la aproximación en función del índice de cola y halla una zona problemática cerca de ξ = 1 <Cite id="degen2010" />; las expansiones de segundo orden las revisan Peters, Targino y Shevchenko <Cite id="peters2013" />. La forma corregida que se cita comúnmente no se verificó contra ninguno de los textos primarios, y el caso la rotula UNVERIFIED dondequiera que aparece.</>}
      />
      <Equation
        tex={String.raw`\mathrm{VaR}_{\alpha}[Z] \approx F^{-1}\!\Bigl(1 - \frac{1-\alpha}{\mathbb{E}[N]}\Bigr), \qquad \mathrm{VaR}_{\alpha}[Z] \approx \frac{\beta}{\xi}\Bigl[\Bigl(\frac{\lambda}{1-\alpha}\Bigr)^{\xi} - 1\Bigr]`}
        caption={<T en={<>The single loss approximation (Shevchenko, <Ref>(70)</Ref>; dossier 05, F.4), valid as α tends to 1: α the level (0.999), F the distribution of one severity, E[N] the expected annual count. Second form: the case of a Poisson frequency with rate λ and a generalised Pareto severity with tail index ξ and scale β, taken from the excess over the severity threshold. The mean-corrected variant F⁻¹(1 − (1 − α)/λ) + λ E[X] is UNVERIFIED and exists only for ξ below 1.</>} es={<>La aproximación de una pérdida (Shevchenko, <Ref>(70)</Ref>; dossier 05, F.4), válida cuando α tiende a 1: α el nivel (0,999), F la distribución de una severidad, E[N] la cantidad anual esperada. Segunda forma: el caso de una frecuencia Poisson de tasa λ y una severidad de Pareto generalizada con índice de cola ξ y escala β, tomada sobre el exceso del umbral de la severidad. La variante corregida por la media F⁻¹(1 − (1 − α)/λ) + λ E[X] es UNVERIFIED y existe solo para ξ menor que 1.</>} />}
      />
    </>
  );
}

function StandardisedPart() {
  return (
    <>
      <P
        en={<>Scenario analysis supplies what a short history cannot: expert estimates of the frequency and severity of rare large events, as individual scenarios, intervals or percentiles. Three methods combine them with the loss data: the scenario points are appended to the tail sample as pseudo-observations; the body is fitted to the internal data and the tail to the quantiles the scenarios imply; or a Bayesian credibility model uses the scenarios as the prior of the tail parameters and updates it with the losses <Cite id="shevchenko2006" />, <Cite id="shevchenko2011" />. A validation must test the sensitivity of the capital to each scenario point, which is the scenario influence of the case. The prior in Contraste is its own construction on that method: a Gamma prior on the Pareto shape 1/ξ, not restricted to a finite mean, with its mean and its 90 percent interval taken from a generalised Pareto fitted to the scenario points; every result says so.</>}
        es={<>El análisis de escenarios aporta lo que una historia corta no puede: estimaciones de expertos de la frecuencia y la severidad de eventos raros y grandes, como escenarios individuales, intervalos o percentiles. Tres métodos los combinan con los datos de pérdidas: los puntos de escenario se agregan a la muestra de la cola como pseudo-observaciones; el cuerpo se ajusta a los datos internos y la cola a los cuantiles que implican los escenarios; o un modelo de credibilidad bayesiana usa los escenarios como a priori de los parámetros de la cola y lo actualiza con las pérdidas <Cite id="shevchenko2006" />, <Cite id="shevchenko2011" />. Una validación debe probar la sensibilidad del capital a cada punto de escenario, que es la influencia de escenario del caso. El a priori de Contraste es una construcción propia sobre ese método: una a priori Gamma sobre la forma de Pareto 1/ξ, sin restricción a una media finita, con su media y su intervalo del 90 por ciento tomados de una Pareto generalizada ajustada a los puntos de escenario; cada resultado lo dice.</>}
      />
      <P
        en={<>The generator is calibrated to the 2008 Loss Data Collection Exercise of the Basel Committee: 121 banks from 17 countries, of which 119 submitted internal loss data <Cite id="bcbs160" />. The median bank has 0.82 losses of EUR 20,000 or more per year per EUR billion of consolidated assets (interquartile range 0.36 to 1.66), and the median across banks of the 25th, 50th, 75th and 95th percentiles of those losses is EUR 27,632, 41,916, 82,608 and 418,400. Only these four quantiles are used, and they are derived statistics: medians of per-bank percentiles are not the percentiles of any one bank. A generalised Pareto fitted to them by least squares on the log quantiles gives a tail index near 0.96 and a scale near EUR 22,350, a calculation made for this project and not a published result; for a bank of EUR 50 billion the single loss approximation then gives an annual value at risk of about EUR 647 million, extremely sensitive to the tail index, which is the instability that motivated the move away from the advanced approach.</>}
        es={<>El generador se calibra al Ejercicio de Recolección de Datos de Pérdida 2008 del Comité de Basilea: 121 bancos de 17 países, de los cuales 119 entregaron datos internos de pérdidas <Cite id="bcbs160" />. El banco mediano tiene 0,82 pérdidas de EUR 20.000 o más por año por cada mil millones de EUR de activos consolidados (rango intercuartil 0,36 a 1,66), y la mediana entre bancos de los percentiles 25, 50, 75 y 95 de esas pérdidas es EUR 27.632, 41.916, 82.608 y 418.400. Solo se usan estos cuatro cuantiles, y son estadísticas derivadas: las medianas de percentiles por banco no son los percentiles de ningún banco. Una Pareto generalizada ajustada a ellos por mínimos cuadrados sobre los log cuantiles da un índice de cola cercano a 0,96 y una escala cercana a EUR 22.350, un cálculo hecho para este proyecto y no un resultado publicado; para un banco de EUR 50 mil millones la aproximación de una pérdida da entonces un valor en riesgo anual de unos EUR 647 millones, extremadamente sensible al índice de cola, que es la inestabilidad que motivó el abandono del enfoque avanzado.</>}
      />
      <Equation
        tex={String.raw`\begin{aligned} \mathrm{BI} &= \mathrm{ILDC} + \mathrm{SC} + \mathrm{FC}\\ \mathrm{BIC} &= 0.12\,\min(\mathrm{BI}, 1) + 0.15\,\bigl(\min(\mathrm{BI}, 30) - 1\bigr)^{+} + 0.18\,(\mathrm{BI} - 30)^{+} \quad (\text{EUR bn}) \end{aligned}`}
        caption={<T en={<>The business indicator and its component (<Ref>OPE25.4</Ref>, <Ref>OPE25.5</Ref> and <Ref>OPE25.7</Ref> Table 1; dossier 01, F): BI the sum of ILDC, built from interest income and expense and dividend income, SC, built from other operating and fee income and expense, and FC, built from the results of the trading and banking books, each a three-year average with the absolute values of net items taken year by year. BIC applies marginal coefficients of 12 percent up to EUR 1 billion of BI, 15 percent from 1 to 30 billion and 18 percent above; (x)⁺ is the positive part. Golden value of footnote 2: BI = EUR 35 billion gives 1 × 12 percent + 29 × 15 percent + 5 × 18 percent = EUR 5.37 billion.</>} es={<>El indicador de negocio y su componente (<Ref>OPE25.4</Ref>, <Ref>OPE25.5</Ref> y <Ref>OPE25.7</Ref> Tabla 1; dossier 01, F): BI la suma de ILDC, construido con los ingresos y gastos por intereses y los ingresos por dividendos, SC, construido con los ingresos y gastos operativos y por comisiones, y FC, construido con los resultados de las carteras de negociación y bancaria, cada uno un promedio de tres años con los valores absolutos de las partidas netas tomados año a año. BIC aplica coeficientes marginales de 12 por ciento hasta EUR 1 mil millones de BI, 15 por ciento de 1 a 30 mil millones y 18 por ciento sobre eso; (x)⁺ es la parte positiva. Valor de referencia de la nota 2: BI = EUR 35 mil millones da 1 × 12 por ciento + 29 × 15 por ciento + 5 × 18 por ciento = EUR 5,37 mil millones.</>} />}
      />
      <P
        en={<>The standardised approach multiplies that component by an internal loss multiplier that reads the bank&apos;s own losses: fifteen times the average annual loss over the previous ten years, compared with the component. The multiplier is 1 when the two are equal and above 1 when the losses are larger. Ten years of high-quality loss data are expected; a transitional minimum of five years applies, and with fewer than five years the capital is the component alone <Ref>OPE25.10</Ref>, <Ref>OPE25.15</Ref>. Losses are net of recoveries, the collection threshold is EUR 20,000 (a national discretion allows EUR 100,000 for buckets 2 and 3), banks of bucket 1 have a multiplier of 1 unless national discretion includes them, and supervisors may set it to 1 for every bank of the jurisdiction <Ref>OPE25.11</Ref>, <Ref>OPE25.18</Ref> <Cite id="ope25" />.</>}
        es={<>El enfoque estandarizado multiplica ese componente por un multiplicador de pérdidas internas que lee las pérdidas propias del banco: quince veces la pérdida anual promedio de los diez años previos, comparada con el componente. El multiplicador es 1 cuando ambos son iguales y mayor que 1 cuando las pérdidas son mayores. Se esperan diez años de datos de pérdidas de alta calidad; rige un mínimo transitorio de cinco años, y con menos de cinco años el capital es solo el componente <Ref>OPE25.10</Ref>, <Ref>OPE25.15</Ref>. Las pérdidas son netas de recuperaciones, el umbral de recolección es EUR 20.000 (una discreción nacional permite EUR 100.000 para los tramos 2 y 3), los bancos del tramo 1 tienen un multiplicador de 1 salvo que la discreción nacional los incluya, y los supervisores pueden fijarlo en 1 para todos los bancos de la jurisdicción <Ref>OPE25.11</Ref>, <Ref>OPE25.18</Ref> <Cite id="ope25" />.</>}
      />
      <Equation
        tex={String.raw`\mathrm{ORC} = \mathrm{BIC}\times\mathrm{ILM}, \quad \mathrm{RWA}_{\mathrm{op}} = 12.5\times\mathrm{ORC}, \qquad \mathrm{ILM} = \ln\!\Bigl(e - 1 + \Bigl(\frac{\mathrm{LC}}{\mathrm{BIC}}\Bigr)^{0.8}\Bigr), \quad \mathrm{LC} = 15\times\overline{L}_{10}`}
        caption={<T en={<>The capital and the multiplier (<Ref>OPE25.2</Ref> and <Ref>OPE25.8</Ref>; dossier 01, F): ORC the operational risk capital, RWA_op the risk-weighted assets, ILM the internal loss multiplier, LC the loss component, and L̄₁₀ the average annual operational risk loss over the previous ten years. ILM = 1 when LC = BIC and above 1 when LC is larger (<Ref>OPE25.9</Ref>).</>} es={<>El capital y el multiplicador (<Ref>OPE25.2</Ref> y <Ref>OPE25.8</Ref>; dossier 01, F): ORC el capital por riesgo operacional, RWA_op los activos ponderados por riesgo, ILM el multiplicador de pérdidas internas, LC el componente de pérdidas, y L̄₁₀ la pérdida anual promedio por riesgo operacional de los diez años previos. ILM = 1 cuando LC = BIC y mayor que 1 cuando LC es mayor (<Ref>OPE25.9</Ref>).</>} />}
      />
      <Figure caption={<T en="The internal loss multiplier as a function of the loss component over the business indicator component, drawn from the formula: it equals one when the two are equal (the marked point), and one large loss that lifts the loss component moves it. The SMA is not calibrated to the 99.9 percent quantile of any bank." es="El multiplicador de pérdidas internas en función del componente de pérdidas sobre el componente del indicador de negocio, dibujado desde la fórmula: es igual a uno cuando ambos son iguales (el punto marcado), y una pérdida grande que sube el componente de pérdidas lo mueve. El SMA no está calibrado al cuantil 99,9 por ciento de ningún banco." />}>
        <IlmFigure />
      </Figure>
      <P
        en={<>The case sets the two approaches side by side on the same histories of a synthetic bank whose business indicator is stated, never a real bank&apos;s. A critical academic response to the standardised measurement approach argues that it is less risk sensitive and can be unstable <Cite id="peters2016" />, <Cite id="mignola2016" />, and the case lets a reader test that: how the multiplier and the capital move when one large loss is added to the latest year, against how the LDA capital of the same history moves, and how far each is from the known true quantile.</>}
        es={<>El caso pone los dos enfoques lado a lado sobre las mismas historias de un banco sintético cuyo indicador de negocio se declara, nunca el de un banco real. Una respuesta académica crítica al enfoque estandarizado de medición sostiene que es menos sensible al riesgo y puede ser inestable <Cite id="peters2016" />, <Cite id="mignola2016" />, y el caso deja a quien lee ponerlo a prueba: cómo se mueven el multiplicador y el capital cuando se suma una pérdida grande al último año, frente a cómo se mueve el capital LDA de la misma historia, y cuán lejos está cada uno del cuantil verdadero conocido.</>}
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
      title={{ en: 'Operational risk: the loss distribution approach, its aggregation and the standardised approach', es: 'Riesgo operacional: el enfoque de distribución de pérdidas, su agregación y el enfoque estandarizado' }}
      refs={['bcbsd355', 'bcbsd424', 'peters2016', 'mignola2016', 'chavez2006', 'mignola2007', 'cope2009', 'panjer1981', 'shevchenko2010', 'degen2010', 'peters2013', 'shevchenko2006', 'shevchenko2011', 'bcbs160', 'ope25']}
    >
      <SubTabs
        ariaLabel={t('Parts of the topic', 'Partes del tema')}
        tabs={[
          { id: 'lda', label: t('Loss distribution approach', 'Enfoque de distribución de pérdidas'), content: <LdaPart /> },
          { id: 'aggregation', label: t('Aggregation and the single loss approximation', 'Agregación y aproximación de una pérdida'), content: <AggregationPart /> },
          { id: 'sma', label: t('Scenarios, calibration and the standardised approach', 'Escenarios, calibración y enfoque estandarizado'), content: <StandardisedPart /> },
        ]}
      />
      <Callout variant="honest" title={t('What is exact, what is Contraste\'s construction and what these views are not', 'Qué es exacto, qué es construcción de Contraste y qué no son estas vistas')}>
        <T
          en={<>The recursion, the single loss approximation and the benchmark numbers are exact as transcribed from Shevchenko; the formulas of OPE25 and the golden value are exact as transcribed from the standard. The mean-corrected single loss approximation is UNVERIFIED against its primary texts and is labelled so everywhere. The Bayesian prior on the scenarios is Contraste&apos;s own reading of the method, the generalised Pareto fit to the calibration percentiles is a calculation of this project and not a published result, and the four percentiles are derived statistics of a survey, medians of per-bank values, so they describe no real bank. The bank of the SMA is synthetic and its business indicator is stated, the SMA is not calibrated to the 99.9 percent quantile of any bank, and the LDA is shown as an economic-capital and validation tool, not as a Pillar 1 model. The histories are simulated from a known truth, so the case measures how far a method falls from that truth with a few years of data; it does not measure any real bank&apos;s operational risk.</>}
          es={<>La recursión, la aproximación de una pérdida y los números del benchmark son exactos tal como se transcribieron de Shevchenko; las fórmulas de OPE25 y el valor de referencia son exactos tal como se transcribieron de la norma. La aproximación de una pérdida corregida por la media es UNVERIFIED contra sus textos primarios y se rotula así en todas partes. El a priori bayesiano sobre los escenarios es la lectura propia de Contraste del método, el ajuste de la Pareto generalizada a los percentiles de calibración es un cálculo de este proyecto y no un resultado publicado, y los cuatro percentiles son estadísticas derivadas de una encuesta, medianas de valores por banco, así que no describen ningún banco real. El banco del SMA es sintético y su indicador de negocio se declara, el SMA no está calibrado al cuantil 99,9 por ciento de ningún banco, y el LDA se muestra como herramienta de capital económico y de validación, no como un modelo del Pilar 1. Las historias se simulan desde una verdad conocida, así que el caso mide cuán lejos cae un método de esa verdad con pocos años de datos; no mide el riesgo operacional de ningún banco real.</>}
        />
      </Callout>
    </DocSection>
  );
}

export const methodologySection: MethodologySection = {
  id: 'oprisk',
  group: 'loss',
  order: 210,
  title: { en: 'Operational risk', es: 'Riesgo operacional' },
  Body,
};
