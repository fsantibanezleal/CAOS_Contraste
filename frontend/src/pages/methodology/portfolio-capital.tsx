// The Methodology section on portfolio credit capital (U7): the Vasicek single-factor model, the large homogeneous
// portfolio and the IRB form with the fit of the correlation to a loss-rate series (research dossier 04, section C.4);
// the loss, the risk measures, the Euler contributions and the validation tests of an economic capital model (dossier 04
// H.1 and H.2, dossier 05 G.4 and G.5); and the copulas, CreditRisk+, the granularity adjustment, concentration and
// importance sampling (dossier 04 H.3 to H.8). What the dossiers mark UNVERIFIED is said so. Every display equation
// carries a caption that defines its symbols. The registry mounts it as one tab of the loss group; one file exports one
// section, so the topic is one `method` section with one part per question, as sub-tabs (ADR-0017 section 2.1), each part
// with its own paragraphs, equations and figure, and one honest callout for the topic.
import { Callout, Cite, DocSection, Equation, Figure, SubTabs } from '@fasl-work/caos-app-shell';
import { P, Ref, T, useT } from '../../content/bi';
import type { MethodologySection } from '../methodologyRegistry';

const W = 480;
const H = 276;

/** A schematic of the fitted loss-rate density with its upper quantiles, the fit-window years on it and the evaluation years in its tail. */
function FitFigure() {
  const t = useT();
  const x = (u: number) => 40 + u * 420;
  const base = 196;
  const g = (u: number) => (u / 0.12) * Math.exp(1 - u / 0.12);
  const y = (u: number) => base - 150 * g(u);
  const pts = Array.from({ length: 81 }, (_, i) => i / 80).map((u) => `${Math.round(x(u) * 10) / 10},${Math.round(y(u) * 10) / 10}`).join(' ');
  const fit = [0.05, 0.08, 0.1, 0.13, 0.17, 0.21];
  const evalYears = [0.19, 0.31, 0.52, 0.33];
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('A skewed density of the yearly loss rate with its 99 and 99.9 percent quantiles marked, grey points for the fit-window years near the body and amber points for the evaluation years in and beyond the tail', 'Una densidad asimétrica de la tasa de pérdida anual con sus cuantiles del 99 y 99,9 por ciento marcados, puntos grises para los años de la ventana de ajuste cerca del cuerpo y puntos ámbar para los años de evaluación en la cola y más allá')}>
      <line className="dg-axis" x1={x(0)} y1={base} x2={x(1)} y2={base} />
      <polyline className="dg-curve" fill="none" points={pts} />
      <line className="dg-marker" x1={x(0.31)} y1={34} x2={x(0.31)} y2={base + 6} />
      <line className="dg-marker" x1={x(0.5)} y1={34} x2={x(0.5)} y2={base + 6} />
      <text className="dg-marker-label" x={x(0.31) + 4} y={44} textAnchor="start">{t('99%', '99%')}</text>
      <text className="dg-marker-label" x={x(0.5) + 4} y={44} textAnchor="start">{t('99.9%', '99,9%')}</text>
      {fit.map((u) => (
        <circle key={`f${u}`} className="dg-node" cx={x(u)} cy={y(u)} r={5} />
      ))}
      {evalYears.map((u) => (
        <circle key={`e${u}`} className="dg-fill-warn" cx={x(u)} cy={Math.min(y(u), base - 7)} r={6} />
      ))}
      <text className="dg-axis-label" x={W / 2} y={base + 30} textAnchor="middle">{t('yearly loss rate', 'tasa de pérdida anual')}</text>
      <text className="dg-note" x={x(0.55)} y={base - 70} textAnchor="start">{t('evaluation years: where the fit said', 'años de evaluación: dónde dijo el ajuste')}</text>
      <text className="dg-note" x={x(0.55)} y={base - 54} textAnchor="start">{t('they should fall', 'que deberían caer')}</text>
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('Illustrative schematic, not a result', 'Esquema ilustrativo, no un resultado')}</text>
    </svg>
  );
}

/** A schematic of three groups of an illustrative portfolio: the share of the exposure against the shares of the VaR and the ES. */
function ContributionFigure() {
  const t = useT();
  const base = 196;
  const groups = [
    { name: t('large names', 'nombres grandes'), e: 40, v: 15, s: 16 },
    { name: t('mid-size names', 'nombres medianos'), e: 30, v: 27, s: 27 },
    { name: t('small names', 'nombres pequeños'), e: 30, v: 58, s: 57 },
  ];
  const k = 2.2;
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('For three groups of names, three bars each: the share of the exposure, the share of the VaR and the share of the expected shortfall; the small names carry far more of the tail than of the exposure', 'Para tres grupos de nombres, tres barras cada uno: la parte de la exposición, la parte del VaR y la parte del déficit esperado; los nombres pequeños cargan mucho más de la cola que de la exposición')}>
      <line className="dg-axis" x1={30} y1={base} x2={460} y2={base} />
      {groups.map((gr, i) => {
        const x0 = 56 + i * 140;
        return (
          <g key={gr.name}>
            <rect className="dg-bar" x={x0} y={base - gr.e * k} width={30} height={gr.e * k} />
            <rect className="dg-bar-2" x={x0 + 34} y={base - gr.v * k} width={30} height={gr.v * k} />
            <rect className="dg-fill-accent" x={x0 + 68} y={base - gr.s * k} width={30} height={gr.s * k} />
            <text className="dg-axis-label" x={x0 + 49} y={base + 18} textAnchor="middle">{gr.name}</text>
          </g>
        );
      })}
      <text className="dg-note" x={40} y={30} textAnchor="start">{t('grey: share of the exposure; middle: share of the VaR; right: share of the ES', 'gris: parte de la exposición; centro: parte del VaR; derecha: parte del ES')}</text>
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('Illustrative schematic, not a result', 'Esquema ilustrativo, no un resultado')}</text>
    </svg>
  );
}

/** A schematic of the granularity adjustment falling as one over the number of names, with the recursion's check points on it. */
function GranularityFigure() {
  const t = useT();
  const base = 196;
  const x = (n: number) => 50 + ((Math.log10(n) - 1) / 2) * 400;
  const y = (n: number) => base - 150 * (10 / n);
  const ns = Array.from({ length: 41 }, (_, i) => 10 ** (1 + (i / 40) * 2));
  const pts = ns.map((n) => `${Math.round(x(n) * 10) / 10},${Math.round(y(n) * 10) / 10}`).join(' ');
  const checks = [10, 20, 50, 100, 200];
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('The granularity adjustment as a share of the exposure falls as one over the number of names, from ten names to a thousand on a logarithmic axis, with points from the CreditRisk+ recursion lying close to the curve for the smaller portfolios', 'El ajuste de granularidad como parte de la exposición cae como uno sobre el número de nombres, de diez nombres a mil en un eje logarítmico, con puntos de la recursión de CreditRisk+ muy cerca de la curva en las carteras menores')}>
      <line className="dg-axis" x1={x(10)} y1={base} x2={x(1000)} y2={base} />
      <polyline className="dg-curve" fill="none" points={pts} />
      {checks.map((n) => (
        <circle key={n} className="dg-node" cx={x(n)} cy={y(n) + 3} r={5} />
      ))}
      {[10, 100, 1000].map((n) => (
        <text key={n} className="dg-tick" x={x(n)} y={base + 18} textAnchor="middle">{n}</text>
      ))}
      <text className="dg-axis-label" x={W / 2} y={base + 40} textAnchor="middle">{t('number of names (logarithmic)', 'número de nombres (logarítmico)')}</text>
      <text className="dg-note" x={x(20)} y={60} textAnchor="start">{t('adjustment proportional to 1 over n', 'ajuste proporcional a 1 sobre n')}</text>
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('Illustrative schematic, not a result', 'Esquema ilustrativo, no un resultado')}</text>
    </svg>
  );
}

/** The caption helper for the figures, outside a hook-bound component. */
function t2(en: string, es: string) {
  return <T en={en} es={es} />;
}

function VasicekPart() {
  return (
    <>
      <P
        en={<>Vasicek's model, with the foundation Gordy gave it, writes the asset return of obligor i as A_i = sqrt(rho) Z + sqrt(1 - rho) e_i, with the systematic factor Z and the obligor's own term e_i independent standard normals, and the obligor defaults when A_i falls below the normal quantile of its probability of default p. Given the factor, defaults are independent, each with the conditional probability below, so every correlation between defaults runs through Z. Vasicek's three notes of 1987, 1991 and 2002 are reprinted in one volume <Cite id="vasicek2015" /> <Cite id="vasicek2002" />, and Gordy shows that portfolio-invariant, ratings-based capital, a requirement that does not depend on what else the bank holds, is essentially obtainable only from an asymptotic single risk factor model <Cite id="gordy2003" />.</>}
        es={<>El modelo de Vasicek, con el fundamento que le dio Gordy, escribe el retorno de activos del deudor i como A_i = sqrt(rho) Z + sqrt(1 - rho) e_i, con el factor sistemático Z y el término propio del deudor e_i normales estándar independientes, y el deudor incumple cuando A_i cae bajo el cuantil normal de su probabilidad de incumplimiento p. Dado el factor, los incumplimientos son independientes, cada uno con la probabilidad condicional de abajo, de modo que toda correlación entre incumplimientos pasa por Z. Las tres notas de Vasicek de 1987, 1991 y 2002 están reeditadas en un solo volumen <Cite id="vasicek2015" /> <Cite id="vasicek2002" />, y Gordy muestra que un capital basado en calificaciones e invariante a la cartera, un requerimiento que no depende de qué más tenga el banco, solo se obtiene en esencia de un modelo asintótico de un solo factor de riesgo <Cite id="gordy2003" />.</>}
      />
      <Equation
        tex={String.raw`p(z)=\Phi\!\left(\frac{\Phi^{-1}(p)-\sqrt{\rho}\,z}{\sqrt{1-\rho}}\right),\qquad \Pr(L_\infty\le x)=\Phi\!\left(\frac{\sqrt{1-\rho}\,\Phi^{-1}(x)-\Phi^{-1}(p)}{\sqrt{\rho}}\right),\qquad \mathrm{VaR}_q(L_\infty)=\Phi\!\left(\frac{\Phi^{-1}(p)+\sqrt{\rho}\,\Phi^{-1}(q)}{\sqrt{1-\rho}}\right)`}
        caption={<T en={<>The conditional probability of default, the distribution function of the large-portfolio loss and its VaR (dossier 04, C.4): Phi the standard normal distribution function and Phi^-1 its inverse, p the unconditional probability of default, rho the asset correlation, z the value of the systematic factor, L_inf the loss fraction of the infinitely large homogeneous portfolio, x a loss fraction and q the confidence level.</>} es={<>La probabilidad condicional de incumplimiento, la función de distribución de la pérdida de la cartera grande y su VaR (dossier 04, C.4): Phi la función de distribución normal estándar y Phi^-1 su inversa, p la probabilidad de incumplimiento no condicional, rho la correlación de activos, z el valor del factor sistemático, L_inf la fracción de pérdida de la cartera homogénea infinitamente grande, x una fracción de pérdida y q el nivel de confianza.</>} />}
      />
      <P
        en={<>In a large homogeneous portfolio the obligors' own terms average out and the portfolio default fraction converges to p(Z). Because p(z) falls as the factor rises, the distribution function of the limit and its quantile follow from that monotonicity, which gives the two closed forms above. This large-portfolio loss is the infinitely granular approximation: the loss views of C10 draw it dashed over every other rung of the ladder, and it is never the true loss distribution of a finite portfolio, because it leaves out the name concentration that a handful of large exposures adds to the tail. Its quantile at a high level is the single-factor capital whose error the case measures.</>}
        es={<>En una cartera homogénea grande los términos propios de los deudores se compensan y la fracción de incumplimiento de la cartera converge a p(Z). Como p(z) baja cuando sube el factor, la función de distribución del límite y su cuantil se siguen de esa monotonía, lo que da las dos formas cerradas de arriba. Esta pérdida de cartera grande es la aproximación infinitamente granular: las vistas de pérdidas de C10 la dibujan punteada sobre cada otro escalón de la escalera, y nunca es la distribución de pérdidas verdadera de una cartera finita, porque omite la concentración por nombre que unas pocas exposiciones grandes agregan a la cola. Su cuantil en un nivel alto es el capital de un solo factor cuyo error mide el caso.</>}
      />
      <Equation
        tex={String.raw`\begin{aligned}K&=\Bigl[\mathrm{LGD}\cdot N\!\Bigl(\tfrac{G(\mathrm{PD})}{\sqrt{1-R}}+\sqrt{\tfrac{R}{1-R}}\,G(0.999)\Bigr)-\mathrm{PD}\cdot\mathrm{LGD}\Bigr]\cdot\frac{1+(M-2.5)\,b(\mathrm{PD})}{1-1.5\,b(\mathrm{PD})},\qquad \mathrm{RWA}=12.5\,K\,\mathrm{EAD}\\ b(\mathrm{PD})&=\bigl(0.11852-0.05478\ln \mathrm{PD}\bigr)^2,\qquad R_{\mathrm{corp}}=0.12\,\tfrac{1-e^{-50\mathrm{PD}}}{1-e^{-50}}+0.24\Bigl[1-\tfrac{1-e^{-50\mathrm{PD}}}{1-e^{-50}}\Bigr]-0.04\Bigl(1-\tfrac{S-5}{45}\Bigr)\end{aligned}`}
        caption={<T en={<>The Basel II IRB capital requirement per unit of exposure and the corporate asset correlation (BCBS 2005 explanatory note, sections 4.2 to 5.2, dossier 04 C.4): N and G the standard normal distribution function and its inverse, R the asset correlation, M the effective maturity, b the maturity-adjustment slope, S the annual sales in EUR million (the size adjustment applies for S between 5 and 50) and 12.5 the factor that turns capital into risk-weighted assets. The bracket is the VaR at 99.9 percent less the expected loss, so the requirement is unexpected loss.</>} es={<>El requerimiento de capital IRB de Basilea II por unidad de exposición y la correlación de activos corporativa (nota explicativa BCBS 2005, secciones <Ref>4.2</Ref> a <Ref>5.2</Ref>, dossier 04 C.4): N y G la función de distribución normal estándar y su inversa, R la correlación de activos, M el plazo efectivo, b la pendiente del ajuste por plazo, S las ventas anuales en millones de EUR (el ajuste por tamaño rige para S entre 5 y 50) y 12,5 el factor que convierte capital en activos ponderados por riesgo. El paréntesis es el VaR al 99,9 por ciento menos la pérdida esperada, así que el requerimiento es pérdida inesperada.</>} />}
      />
      <P
        en={<>In the IRB formula the correlation R is set by the framework and is not fitted; this is the Basel II calibration of the explanatory note <Cite id="bcbs2005irb" />, and the current Basel framework and local rules such as those of the CMF are covered by the regulatory research.</>}
        es={<>En la fórmula IRB la correlación R la fija el marco y no se ajusta; esta es la calibración de Basilea II de la nota explicativa <Cite id="bcbs2005irb" />, y el marco de Basilea vigente y las normas locales, como las de la CMF, se cubren en la investigación regulatoria.</>}
      />
      <P
        en={<>The relation of the large portfolio can also be turned around: a systematic factor implied by an observed default rate DR_t is z_t = (Phi^-1(p) - sqrt(1 - rho) Phi^-1(DR_t)) / sqrt(rho), a derivation and not a quoted formula. C10 fits p and rho to the yearly net charge-off rates of each loan type of the Federal Reserve release <Cite id="fedchargeoff" /> for 1985 to 2006, by maximum likelihood on the density of the large-portfolio distribution with a profile-likelihood interval for the correlation, and by the method of moments with a parametric bootstrap interval. It then places the years 2007 to 2012, which the fit never saw, in the fitted distribution and counts those above its 95, 99 and 99.9 percent quantiles. With 22 yearly points the correlation interval is wide, and how sure the correlation is, is itself a result; the fitted correlation is finally compared with the IRB correlation of the loan type's regulatory class, with the same loss given default, probability of default and maturity treatment on both sides.</>}
        es={<>La misma relación puede invertirse: un factor sistemático implícito en una tasa de incumplimiento observada DR_t es z_t = (Phi^-1(p) - sqrt(1 - rho) Phi^-1(DR_t)) / sqrt(rho), una derivación y no una fórmula citada. C10 ajusta p y rho a las tasas anuales de castigo neto de cada tipo de crédito de la publicación de la Reserva Federal <Cite id="fedchargeoff" /> para 1985 a 2006, por máxima verosimilitud sobre la densidad de la distribución de cartera grande con un intervalo de verosimilitud perfilada para la correlación, y por el método de momentos con un intervalo de bootstrap paramétrico. Luego ubica los años 2007 a 2012, que el ajuste nunca vio, en la distribución ajustada y cuenta los que superan sus cuantiles del 95, 99 y 99,9 por ciento. Con 22 puntos anuales el intervalo de la correlación es ancho, y qué tan segura es la correlación es en sí un resultado; la correlación ajustada se compara por último con la correlación IRB de la clase regulatoria del tipo de crédito, con la misma pérdida dado el incumplimiento, probabilidad de incumplimiento y tratamiento del plazo en ambos lados.</>}
      />
      <Figure caption={t2('The fitted density of the yearly loss rate with its 99 and 99.9 percent quantiles: grey points are years of the fit window, amber points the evaluation years, which fall in and beyond the tail the fit drew and are counted against each quantile.', 'La densidad ajustada de la tasa de pérdida anual con sus cuantiles del 99 y 99,9 por ciento: los puntos grises son años de la ventana de ajuste, los puntos ámbar los años de evaluación, que caen en la cola que dibujó el ajuste y más allá de ella, y se cuentan contra cada cuantil.')}>
        <FitFigure />
      </Figure>
    </>
  );
}

function CapitalPart() {
  return (
    <>
      <P
        en={<>The default-mode loss of a portfolio of n obligors over the horizon is the sum, over obligors, of the exposure at default times the loss given default times the default indicator, and its expected value is the sum of exposure, expected loss given default and probability of default when the loss given default is independent of the default. The VaR at level q is the smallest loss the portfolio stays below with probability at least q, and the expected shortfall averages the VaR above q, which for a continuous loss equals the mean loss given that it reaches the VaR; the expected shortfall is coherent <Cite id="acerbitasche2002" />. Economic capital on an unexpected-loss basis is the VaR less the expected loss, the same concept as the IRB requirement <Cite id="bcbs2005irb" />, whose note writes the expected loss as the product of probability of default, exposure and loss given default.</>}
        es={<>La pérdida en modo de incumplimiento de una cartera de n deudores en el horizonte es la suma, sobre los deudores, de la exposición al incumplimiento por la pérdida dado el incumplimiento por el indicador de incumplimiento, y su valor esperado es la suma de exposición, pérdida dado el incumplimiento esperada y probabilidad de incumplimiento cuando la pérdida dado el incumplimiento es independiente del incumplimiento. El VaR de nivel q es la menor pérdida bajo la cual queda la cartera con probabilidad al menos q, y el déficit esperado promedia el VaR sobre q, lo que para una pérdida continua es la pérdida media dado que alcanza el VaR; el déficit esperado es coherente <Cite id="acerbitasche2002" />. El capital económico sobre la base de pérdida inesperada es el VaR menos la pérdida esperada, el mismo concepto del requerimiento IRB <Cite id="bcbs2005irb" />, cuya nota escribe la pérdida esperada como el producto de probabilidad de incumplimiento, exposición y pérdida dado el incumplimiento.</>}
      />
      <Equation
        tex={String.raw`L=\sum_{i=1}^{n}\mathrm{EAD}_i\,\mathrm{LGD}_i\,D_i,\quad \mathrm{EL}=\sum_i \mathrm{EAD}_i\,\mathbb{E}[\mathrm{LGD}_i]\,\mathrm{PD}_i,\quad \mathrm{VaR}_q=\inf\{\ell:\Pr(L\le\ell)\ge q\},\quad \mathrm{ES}_q=\frac{1}{1-q}\int_q^1 \mathrm{VaR}_u\,du,\quad \mathrm{EC}_q=\mathrm{VaR}_q-\mathrm{EL}`}
        caption={<T en={<>The portfolio loss and its measures (dossier 04, H.1): EAD_i, LGD_i and D_i the exposure at default, loss given default and default indicator of obligor i, PD_i its probability of default, EL the expected loss, VaR_q and ES_q the value at risk and the expected shortfall at level q, and EC_q the economic capital on an unexpected-loss basis.</>} es={<>La pérdida de la cartera y sus medidas (dossier 04, H.1): EAD_i, LGD_i y D_i la exposición al incumplimiento, la pérdida dado el incumplimiento y el indicador de incumplimiento del deudor i, PD_i su probabilidad de incumplimiento, EL la pérdida esperada, VaR_q y ES_q el valor en riesgo y el déficit esperado al nivel q, y EC_q el capital económico sobre la base de pérdida inesperada.</>} />}
      />
      <P
        en={<>Capital is allocated to groups of obligors by the Euler principle. For a risk measure that is positively homogeneous of degree one and differentiable, Euler's theorem makes the total equal the sum of the derivatives of the measure with respect to the weight of each unit, and these contributions, which add up to the total, are the only ones compatible with return on risk-adjusted capital <Cite id="tasche2008euler" />. For the VaR the contribution of a unit is its expected loss given that the portfolio loss sits at the VaR, and for the expected shortfall it is the expected loss given that the portfolio loss reaches the VaR (equations <Ref>3.7</Ref> and <Ref>3.11</Ref> of that paper, read from the arXiv text in the validation research; the numbering in the credit research is unverified). The diversification factor is the measure of the portfolio over the sum of the measures of its units.</>}
        es={<>El capital se asigna a grupos de deudores por el principio de Euler. Para una medida de riesgo positivamente homogénea de grado uno y diferenciable, el teorema de Euler hace que el total sea la suma de las derivadas de la medida respecto del peso de cada unidad, y estas contribuciones, que suman el total, son las únicas compatibles con el retorno sobre capital ajustado por riesgo <Cite id="tasche2008euler" />. Para el VaR, la contribución de una unidad es su pérdida esperada dado que la pérdida de la cartera está en el VaR, y para el déficit esperado es la pérdida esperada dado que la pérdida de la cartera alcanza el VaR (las ecuaciones <Ref>3.7</Ref> y <Ref>3.11</Ref> de ese artículo, leídas del texto de arXiv en la investigación de validación; la numeración en la investigación de crédito no está verificada). El factor de diversificación es la medida de la cartera sobre la suma de las medidas de sus unidades.</>}
      />
      <Equation
        tex={String.raw`\rho(L)=\sum_i u_i\,\frac{\partial\rho(L(u))}{\partial u_i}\Big|_{u=1},\qquad \mathrm{RC}^{\mathrm{VaR}}_i=\mathbb{E}\bigl[L_i\mid L=\mathrm{VaR}_q(L)\bigr],\qquad \mathrm{RC}^{\mathrm{ES}}_i=\mathbb{E}\bigl[L_i\mid L\ge\mathrm{VaR}_q(L)\bigr]`}
        caption={<T en={<>The Euler contributions (Tasche 2008; dossier 04, H.2, and dossier 05, G.4): rho a positively homogeneous risk measure, L(u) the portfolio loss with weight u_i on unit i, L_i the loss of unit i, and RC the contribution of unit i to the VaR or the expected shortfall at level q. The contributions of all units add up to the measure of the whole portfolio.</>} es={<>Las contribuciones de Euler (Tasche 2008; dossier 04, H.2, y dossier 05, G.4): rho una medida de riesgo positivamente homogénea, L(u) la pérdida de la cartera con peso u_i en la unidad i, L_i la pérdida de la unidad i y RC la contribución de la unidad i al VaR o al déficit esperado al nivel q. Las contribuciones de todas las unidades suman la medida de la cartera completa.</>} />}
      />
      <P
        en={<>Estimating the contributions by simulation is uneven. The VaR contribution conditions on a single loss level and is very noisy, so the expected shortfall contributions or kernel-smoothed VaR contributions are preferred <Cite id="tasche2009kernel" />, and the closed-form one-factor contributions of Emmer and Tasche give an anchor to check them against <Cite id="emmertasche2005" />. C10 takes the expected shortfall contributions from the tail sample and the VaR contributions from a kernel estimator, and draws beside them the asymptotic one-factor contribution, the first term of the closed form, which belongs to the infinitely granular portfolio: the sample VaR sits near it, not on it. A group's share of the tail can be far from its share of the exposure, and that gap is what the contributions view shows for the illustrative portfolio.</>}
        es={<>Estimar las contribuciones por simulación es desigual. La contribución al VaR condiciona en un solo nivel de pérdida y es muy ruidosa, por lo que se prefieren las contribuciones al déficit esperado o las del VaR suavizadas con kernel <Cite id="tasche2009kernel" />, y las contribuciones de forma cerrada de un factor de Emmer y Tasche dan un ancla contra la cual verificarlas <Cite id="emmertasche2005" />. C10 toma las contribuciones al déficit esperado de la muestra de la cola y las del VaR de un estimador de kernel, y dibuja a su lado la contribución asintótica de un factor, el primer término de la forma cerrada, que corresponde a la cartera infinitamente granular: el VaR de la muestra queda cerca de ella, no sobre ella. La parte de un grupo en la cola puede estar lejos de su parte en la exposición, y esa brecha es lo que muestra la vista de contribuciones para la cartera ilustrativa.</>}
      />
      <P
        en={<>The validation of an economic capital model benchmarks the aggregation against simpler ones, reports the sensitivity to the copula (Gaussian against Student-t with several degrees of freedom), checks that the allocation sums to the total and that the sign of every diversification benefit is right, and checks that the horizon and the confidence level are consistent across risk types. C10 runs the tests that apply to a credit portfolio: the tail back-test, in which the number of evaluation years above a fitted quantile should follow a binomial law with the expected rate and is judged by its upper-tail probability; the convergence of a Monte Carlo VaR to its analytic anchor within its standard error; and the additivity of the Euler contributions within a stated tolerance. The lights are Contraste's internal gates at 5 and 1 percent, not regulatory thresholds, and with six evaluation years the back-test has little power, so its p-value is read beside the counts.</>}
        es={<>La validación de un modelo de capital económico compara la agregación con otras más simples, informa la sensibilidad a la cópula (gaussiana frente a t de Student con varios grados de libertad), verifica que la asignación sume el total y que el signo de cada beneficio de diversificación sea correcto, y verifica que el horizonte y el nivel de confianza sean coherentes entre tipos de riesgo. C10 corre las pruebas que valen para una cartera de crédito: el backtest de cola, en que el número de años de evaluación sobre un cuantil ajustado debería seguir una ley binomial con la tasa esperada y se juzga por su probabilidad de cola superior; la convergencia de un VaR de Monte Carlo a su ancla analítica dentro de su error estándar; y la aditividad de las contribuciones de Euler dentro de una tolerancia declarada. Las luces son umbrales internos de Contraste al 5 y 1 por ciento, no umbrales regulatorios, y con seis años de evaluación el backtest tiene poca potencia, por lo que su valor p se lee junto a los conteos.</>}
      />
      <Figure caption={t2('For three groups of an illustrative portfolio, the share of the exposure, of the VaR and of the expected shortfall: the small names carry far more of the tail than of the exposure, which is what an Euler allocation shows and an exposure share hides.', 'Para tres grupos de una cartera ilustrativa, la parte de la exposición, del VaR y del déficit esperado: los nombres pequeños cargan mucho más de la cola que de la exposición, que es lo que muestra una asignación de Euler y no se ve en la parte de la exposición.')}>
        <ContributionFigure />
      </Figure>
    </>
  );
}

function TailPart() {
  return (
    <>
      <P
        en={<>Beyond one factor, the structural models write the asset return of obligor i on several factors, A_i = b_i'Z + sqrt(1 - b_i'b_i) e_i with Z normal with covariance matrix Sigma, and the obligor defaults when A_i falls below the normal quantile of its probability of default; the copula view of default correlation is Li's <Cite id="li2000" />. Replacing the normal with a Student-t, by multiplying the return by the square root of W = nu / chi-square(nu), adds tail dependence, so joint defaults cluster more than in the Gaussian case for the same asset correlation <Cite id="freymcneil2003" /> <Cite id="demartamcneil2005" />. The CreditMetrics document adds migrations with mark-to-market losses <Cite id="gupton1997" />; C10 stays in default mode. Gordy shows that the structural and the actuarial families can be mapped into each other, the differences coming from distributional assumptions and parameters (a result recalled from the abstract; the wording is unverified) <Cite id="gordy2000" />.</>}
        es={<>Más allá de un factor, los modelos estructurales escriben el retorno de activos del deudor i sobre varios factores, A_i = b_i'Z + sqrt(1 - b_i'b_i) e_i con Z normal de matriz de covarianza Sigma, y el deudor incumple cuando A_i cae bajo el cuantil normal de su probabilidad de incumplimiento; la mirada de cópula a la correlación de incumplimiento es la de Li <Cite id="li2000" />. Reemplazar la normal por una t de Student, multiplicando el retorno por la raíz de W = nu / chi cuadrado(nu), agrega dependencia de cola, de modo que los incumplimientos conjuntos se agrupan más que en el caso gaussiano para la misma correlación de activos <Cite id="freymcneil2003" /> <Cite id="demartamcneil2005" />. El documento de CreditMetrics agrega migraciones con pérdidas a valor de mercado <Cite id="gupton1997" />; C10 se queda en modo de incumplimiento. Gordy muestra que las familias estructural y actuarial pueden mapearse una en otra, y que las diferencias vienen de los supuestos distribucionales y de los parámetros (un resultado recordado del resumen; la redacción no está verificada) <Cite id="gordy2000" />.</>}
      />
      <Equation
        tex={String.raw`\begin{aligned}A_i&=\beta_i^{\top}Z+\sqrt{1-\beta_i^{\top}\beta_i}\,\varepsilon_i,\quad Z\sim N(0,\Sigma),\quad \text{default iff } A_i<\Phi^{-1}(\mathrm{PD}_i)\\ A_i&=\sqrt{W}\Bigl(\beta_i^{\top}Z+\sqrt{1-\beta_i^{\top}\beta_i}\,\varepsilon_i\Bigr),\quad W=\nu/\chi^2_\nu,\quad \text{default iff } A_i<t_\nu^{-1}(\mathrm{PD}_i)\end{aligned}`}
        caption={<T en={<>The Gaussian and the Student-t copula in default mode (dossier 04, H.3): beta_i the vector of factor loadings of obligor i, Z the vector of systematic factors with covariance Sigma, epsilon_i the obligor's own standard normal term, W the common mixing variable with nu degrees of freedom independent of the rest, and t_nu^-1 the Student-t quantile function.</>} es={<>La cópula gaussiana y la t de Student en modo de incumplimiento (dossier 04, H.3): beta_i el vector de cargas factoriales del deudor i, Z el vector de factores sistemáticos con covarianza Sigma, epsilon_i el término normal estándar propio del deudor, W la variable mezcladora común con nu grados de libertad independiente del resto, y t_nu^-1 la función cuantil de la t de Student.</>} />}
      />
      <P
        en={<>CreditRisk+ takes the actuarial road: exposures are integer multiples of a loss unit, defaults are Poisson with a stochastic intensity driven by independent Gamma sector factors with mean one, and the probability generating function of the loss is available in closed form. The original document of Credit Suisse First Boston could not be accessed and is unverified as a primary source; the model statement and the generating function below are verified from Haaf, Reiss and Schoenmakers <Cite id="haaf2004" />. The Panjer recursion advocated in the original is numerically unstable, because it sums terms of opposite sign, and those authors give a stable recursion based on series expansions of the logarithm and the exponential. The model is default-mode only, has deterministic recoveries in its basic form, and its Poisson approximation can produce more than one default per obligor when probabilities are large.</>}
        es={<>CreditRisk+ toma el camino actuarial: las exposiciones son múltiplos enteros de una unidad de pérdida, los incumplimientos son de Poisson con una intensidad estocástica guiada por factores sectoriales Gamma independientes de media uno, y la función generadora de probabilidades de la pérdida existe en forma cerrada. El documento original de Credit Suisse First Boston no pudo consultarse y no está verificado como fuente primaria; el planteo del modelo y la función generadora de abajo están verificados en Haaf, Reiss y Schoenmakers <Cite id="haaf2004" />. La recursión de Panjer que propone el original es numéricamente inestable, porque suma términos de signo opuesto, y esos autores dan una recursión estable basada en desarrollos en serie del logaritmo y de la exponencial. El modelo es solo de modo de incumplimiento, tiene recuperaciones deterministas en su forma básica, y su aproximación de Poisson puede producir más de un incumplimiento por deudor cuando las probabilidades son grandes.</>}
      />
      <Equation
        tex={String.raw`G(z)=\exp\!\Biggl(\sum_{i=1}^{N}w_{0,i}\,p_i\,(z^{\nu_i}-1)-\sum_{k=1}^{K}\frac{1}{\sigma_k^2}\ln\Bigl[1-\sigma_k^2\sum_{i=1}^{N}w_{k,i}\,p_i\,(z^{\nu_i}-1)\Bigr]\Biggr)`}
        caption={<T en={<>The probability generating function of the CreditRisk+ loss (Haaf, Reiss and Schoenmakers 2004; dossier 04, H.4): N the number of obligors, K the number of Gamma sectors, p_i the probability of default of obligor i, nu_i its exposure in loss units, w_0,i the weight on the idiosyncratic part and w_k,i the weight on sector k, and sigma_k^2 the variance of the mean-one Gamma factor of sector k.</>} es={<>La función generadora de probabilidades de la pérdida de CreditRisk+ (Haaf, Reiss y Schoenmakers 2004; dossier 04, H.4): N el número de deudores, K el número de sectores Gamma, p_i la probabilidad de incumplimiento del deudor i, nu_i su exposición en unidades de pérdida, w_0,i el peso de la parte idiosincrática y w_k,i el peso del sector k, y sigma_k^2 la varianza del factor Gamma de media uno del sector k.</>} />}
      />
      <P
        en={<>The granularity adjustment corrects the single-factor capital for the finite number of names. The general result of Gordy and Lutkebohmert (their equation <Ref>9</Ref>) gives the adjustment as a derivative of the product of the factor density and the conditional loss variance over the slope of the conditional mean, evaluated at the quantile of the factor; the Basel form is built on single-factor CreditRisk+ with a Gamma factor and gives the simplified expression below (equation <Ref>17</Ref>), driven by the squared exposure shares, with delta from equation <Ref>15</Ref> <Cite id="gordylutkebohmert2013" />. The paper's test vector, xi 0.25 and q 0.999, gives delta 4.83, which the engine must reproduce; the usual industry setting of the loss-given-default dispersion is 0.25, and the exact adjustment adds second-order terms. In C10 the adjustment is a share of the exposure added to the VaR of the infinitely granular portfolio, with the capital K_i of each name taken from the IRB formula at the regulatory correlation, as the paper's algorithm does. Related work extends it to mark-to-market models <Cite id="gordymarrone2012" />.</>}
        es={<>El ajuste de granularidad corrige el capital de un solo factor por el número finito de nombres. El resultado general de Gordy y Lutkebohmert (su ecuación <Ref>9</Ref>) da el ajuste como una derivada del producto de la densidad del factor y la varianza condicional de la pérdida sobre la pendiente de la media condicional, evaluada en el cuantil del factor; la forma de Basilea se construye sobre CreditRisk+ de un factor con un factor Gamma y da la expresión simplificada de abajo (ecuación <Ref>17</Ref>), guiada por las partes de exposición al cuadrado, con delta de la ecuación <Ref>15</Ref> <Cite id="gordylutkebohmert2013" />. El vector de prueba del artículo, xi 0,25 y q 0,999, da delta 4,83, que el motor debe reproducir; el valor habitual de la industria para la dispersión de la pérdida dado el incumplimiento es 0,25, y el ajuste exacto agrega términos de segundo orden. En C10 el ajuste es una parte de la exposición que se suma al VaR de la cartera infinitamente granular, con el capital K_i de cada nombre tomado de la fórmula IRB a la correlación regulatoria, como lo hace el algoritmo del artículo. Trabajo relacionado lo extiende a modelos a valor de mercado <Cite id="gordymarrone2012" />.</>}
      />
      <Equation
        tex={String.raw`\widetilde{\mathrm{GA}}=\frac{1}{2\mathcal{K}^{*}}\sum_{i=1}^{n}s_i^{2}\,\mathcal{C}_i\bigl(\delta(\mathcal{K}_i+\mathcal{R}_i)-\mathcal{K}_i\bigr),\quad \delta=(\alpha_q(X)-1)\Bigl(\xi+\frac{1-\xi}{\alpha_q(X)}\Bigr),\quad \mathcal{C}_i=\frac{\mathrm{V}[\mathrm{LGD}_i]+\mathbb{E}[\mathrm{LGD}_i]^2}{\mathbb{E}[\mathrm{LGD}_i]}`}
        caption={<T en={<>The simplified granularity adjustment of Gordy and Lutkebohmert 2013 (equations 17, 15 and 11; dossier 04, H.5): s_i the exposure share of name i, K_i its capital and R_i its reserve (expected loss given default times probability of default), K* the capital of the portfolio, alpha_q(X) the q-quantile of the Gamma factor with shape and rate xi, and C_i a loss-given-default term in which the variance is gamma E(1 - E) (equation 16).</>} es={<>El ajuste de granularidad simplificado de Gordy y Lutkebohmert 2013 (ecuaciones 17, 15 y 11; dossier 04, H.5): s_i la parte de exposición del nombre i, K_i su capital y R_i su reserva (pérdida dado el incumplimiento esperada por probabilidad de incumplimiento), K* el capital de la cartera, alpha_q(X) el cuantil q del factor Gamma de forma y tasa xi, y C_i un término de pérdida dado el incumplimiento cuya varianza es gamma E(1 - E) (ecuación 16).</>} />}
      />
      <P
        en={<>Concentration is also measured directly. The Herfindahl-Hirschman index is the sum of the squared exposure shares, and one over it is the effective number of names; the granularity adjustment is an s_i squared weighted sum, so it is a model-based refinement of that index. Sector concentration has its own tractable model <Cite id="dullmann2007" />, with a multi-factor adjustment of Pykhtin whose bibliographic details are unverified, and the Basel Committee's task-force studies give the supervisory overview <Cite id="bcbs2006wp15" />. For the tail at 99.9 percent plain Monte Carlo is noisy, and importance sampling for the normal copula twists the conditional default probabilities and shifts the factor mean, then reweights by the likelihood ratio <Cite id="glassermanli2005" /> <Cite id="glassermanheidelberger2002" />. The transcription of the twist is unverified against the paper, so the engine checks it for unbiasedness against plain Monte Carlo instead of trusting it. No maintained, permissively licensed Python implementation of CreditMetrics or CreditRisk+ was found, so the engine is its own and is validated against analytic anchors.</>}
        es={<>La concentración también se mide directamente. El índice de Herfindahl-Hirschman es la suma de las partes de exposición al cuadrado, y uno sobre él es el número efectivo de nombres; el ajuste de granularidad es una suma ponderada por s_i al cuadrado, así que es un refinamiento basado en modelo de ese índice. La concentración sectorial tiene su propio modelo tratable <Cite id="dullmann2007" />, con un ajuste multifactorial de Pykhtin cuyos datos bibliográficos no están verificados, y los estudios del grupo de trabajo del Comité de Basilea dan la visión supervisora <Cite id="bcbs2006wp15" />. Para la cola al 99,9 por ciento el Monte Carlo simple es ruidoso, y el muestreo por importancia para la cópula normal tuerce las probabilidades condicionales de incumplimiento y desplaza la media del factor, y luego repondera por la razón de verosimilitud <Cite id="glassermanli2005" /> <Cite id="glassermanheidelberger2002" />. La transcripción de la torsión no está verificada contra el artículo, así que el motor la verifica por insesgamiento contra el Monte Carlo simple en vez de confiar en ella. No se encontró una implementación en Python mantenida y de licencia permisiva de CreditMetrics ni de CreditRisk+, así que el motor es propio y se valida contra anclas analíticas.</>}
      />
      <Figure caption={t2('The granularity adjustment as a share of the exposure for n identical names, on a logarithmic axis: it falls as one over n, and points from the CreditRisk+ recursion of the same single-factor model sit close to it for the smaller portfolios, where the approximation is most tested.', 'El ajuste de granularidad como parte de la exposición para n nombres idénticos, en un eje logarítmico: cae como uno sobre n, y puntos de la recursión de CreditRisk+ del mismo modelo de un factor quedan cerca de él en las carteras menores, donde la aproximación se pone más a prueba.')}>
        <GranularityFigure />
      </Figure>
    </>
  );
}

function Body() {
  const t = useT();
  return (
    <DocSection
      area="method"
      kind="classical"
      title={{ en: 'Portfolio credit capital: Vasicek, Euler contributions, copulas and granularity', es: 'Capital de crédito de cartera: Vasicek, contribuciones de Euler, cópulas y granularidad' }}
      refs={['vasicek2002', 'vasicek2015', 'gordy2003', 'bcbs2005irb', 'fedchargeoff', 'acerbitasche2002', 'tasche2008euler', 'tasche2009kernel', 'emmertasche2005', 'li2000', 'freymcneil2003', 'demartamcneil2005', 'gupton1997', 'gordy2000', 'haaf2004', 'gordylutkebohmert2013', 'gordymarrone2012', 'dullmann2007', 'bcbs2006wp15', 'glassermanli2005', 'glassermanheidelberger2002']}
    >
      <SubTabs
        ariaLabel={t('Parts of the topic', 'Partes del tema')}
        tabs={[
          { id: 'vasicek', label: t('Vasicek and the fit', 'Vasicek y el ajuste'), content: <VasicekPart /> },
          { id: 'capital', label: t('Loss, capital and contributions', 'Pérdida, capital y contribuciones'), content: <CapitalPart /> },
          { id: 'tail', label: t('Copulas, CreditRisk+ and granularity', 'Cópulas, CreditRisk+ y granularidad'), content: <TailPart /> },
        ]}
      />
      <Callout variant="honest" title={t('What is exact, what is policy and what these views are not', 'Qué es exacto, qué es política y qué no son estas vistas')}>
        <T
          en={<>The Vasicek and large-portfolio formulas, the IRB form, the loss measures, the Euler definitions, the generating function of CreditRisk+ and the granularity expression with its test value are exact as transcribed from the sources; what the research marks unverified stays so here: the equation numbering of Tasche in the credit research (the validation research confirms <Ref>3.4</Ref>, <Ref>3.7</Ref> and <Ref>3.11</Ref>), the original CreditRisk+ document, the wording of Gordy's mapping of model families, the CreditMetrics page references, Pykhtin's multi-factor adjustment and the transcription of the importance-sampling twist. The Federal Reserve rates are loss rates of a whole loan type, net of recoveries, so the fit gives the correlation of the type's yearly losses and not of any bank's obligors, and 22 yearly points are few. The portfolio of the loss distributions is illustrative and constructed, never a bank's; the large homogeneous portfolio is an approximation and not the true distribution of that portfolio; the lights are Contraste's internal gates and not regulatory thresholds; a six-year back-test has little power. The simulator says how well the estimates recover a known correlation and nothing about any bank, and the schematics above are illustrative.</>}
          es={<>Las fórmulas de Vasicek y de cartera grande, la forma IRB, las medidas de pérdida, las definiciones de Euler, la función generadora de CreditRisk+ y la expresión de granularidad con su valor de prueba son exactas tal como se transcribieron de las fuentes; lo que la investigación marca como no verificado sigue así aquí: la numeración de las ecuaciones de Tasche en la investigación de crédito (la investigación de validación confirma <Ref>3.4</Ref>, <Ref>3.7</Ref> y <Ref>3.11</Ref>), el documento original de CreditRisk+, la redacción del mapeo de familias de modelos de Gordy, las referencias de página de CreditMetrics, el ajuste multifactorial de Pykhtin y la transcripción de la torsión del muestreo por importancia. Las tasas de la Reserva Federal son tasas de pérdida de un tipo de crédito completo, netas de recuperaciones, así que el ajuste da la correlación de las pérdidas anuales del tipo y no de los deudores de ningún banco, y 22 puntos anuales son pocos. La cartera de las distribuciones de pérdidas es ilustrativa y construida, nunca la de un banco; la cartera homogénea grande es una aproximación y no la distribución verdadera de esa cartera; las luces son umbrales internos de Contraste y no umbrales regulatorios; un backtest de seis años tiene poca potencia. El simulador dice qué tan bien las estimaciones recuperan una correlación conocida y nada sobre ningún banco, y los esquemas de arriba son ilustrativos.</>}
        />
      </Callout>
    </DocSection>
  );
}

export const methodologySection: MethodologySection = {
  id: 'portfolio-capital',
  group: 'loss',
  order: 120,
  title: { en: 'Portfolio credit capital', es: 'Capital de crédito de cartera' },
  Body,
};
