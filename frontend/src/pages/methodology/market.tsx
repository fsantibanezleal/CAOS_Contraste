// The Methodology section on market risk (U8): the sign convention, the FZ0 score and the VaR and ES estimator ladder of
// case C11; its back-tests (Kupiec, Christoffersen, the duration test, the Basel traffic light of MAR32.9, the expected
// shortfall tests of Acerbi and Szekely and of Du and Escanciano) and the comparison under a consistent score (Diebold-Mariano
// and the model confidence set); and the FRTB desk tests of case C13 (the desk back-test of MAR32.18 to 19 and the P&L
// attribution test of MAR32.20 to 44). Transcribed from research dossier 05 (market risk, sections A.0 to A.2 and B.1 to
// B.6) and dossier 01 (the Basel framework, section D.4), where each formula, table and reference was read at its primary
// source on 2026-10-04 or, where marked unverified, through a secondary one. Every display equation carries a caption that
// defines its symbols. The registry mounts it as one tab of the tests group; one file exports one section, so the topic is
// one `method` section with one part per question, as sub-tabs (ADR-0017 section 2.1), each part with its own paragraphs,
// equations and figure, and one honest callout for the topic.
import { Callout, Cite, DocSection, Figure, SubTabs, formatNumber, useShellLang } from '@fasl-work/caos-app-shell';
import type { CSSProperties } from 'react';
import { Equation, P, Ref, T, useT } from '../../content/bi';
import type { MethodologySection } from '../methodologyRegistry';

const r1 = (v: number) => Math.round(v * 10) / 10;
const W = 480;
const H = 262;

const zoneStyle = (token: '--color-good' | '--color-warn' | '--color-bad'): CSSProperties => ({
  fill: `color-mix(in oklab, var(${token}) 18%, transparent)`,
  stroke: `var(${token})`,
  strokeWidth: 1,
});

/** A loss distribution with the VaR at the 99 percent level and the ES as the mean of the tail beyond it. */
function TailFigure() {
  const t = useT();
  const base = 190;
  const x0 = 40;
  const x1 = 450;
  // a right-skewed density on [x0, x1]: the tail beyond the VaR is shaded
  const xs = Array.from({ length: 83 }, (_, i) => x0 + (i * (x1 - x0)) / 82);
  const density = (x: number) => {
    const u = (x - x0) / (x1 - x0);
    return 150 * (Math.exp(-((u - 0.28) ** 2) / (2 * 0.12 ** 2)) * 0.9 + 0.35 * Math.exp(-((u - 0.55) ** 2) / (2 * 0.2 ** 2)));
  };
  const curve = xs.map((x) => `${r1(x)},${r1(base - density(x))}`).join(' ');
  const varX = 330;
  const esX = 380;
  const tail = xs.filter((x) => x >= varX);
  const tailPoly = `${varX},${base} ${tail.map((x) => `${r1(x)},${r1(base - density(x))}`).join(' ')} ${x1},${base}`;
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('A loss distribution with the VaR marked at the 99 percent level and the expected shortfall marked further right as the mean of the shaded tail beyond the VaR', 'Una distribución de pérdidas con el VaR marcado al nivel de 99 por ciento y la pérdida esperada marcada más a la derecha como la media de la cola sombreada más allá del VaR')}>
      <line className="dg-axis" x1={x0} y1={base} x2={x1} y2={base} />
      <polygon className="dg-fill-warn" points={tailPoly} />
      <polyline className="dg-curve" points={curve} />
      <line className="dg-asymptote" x1={varX} y1={34} x2={varX} y2={base + 6} />
      <line className="dg-marker" x1={esX} y1={34} x2={esX} y2={base + 6} />
      <text className="dg-edge-label" x={varX - 6} y={46} textAnchor="end">{t('VaR, 99 %', 'VaR, 99 %')}</text>
      <text className="dg-marker-label" x={esX + 6} y={46} textAnchor="start">ES</text>
      <text className="dg-note" x={(varX + x1) / 2} y={base - 52} textAnchor="middle">{t('tail: 1 % of days', 'cola: 1 % de los días')}</text>
      <text className="dg-axis-label" x={(x0 + x1) / 2} y={base + 30} textAnchor="middle">{t('loss, a positive number, share of the portfolio value', 'pérdida, un número positivo, parte del valor de la cartera')}</text>
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('Illustrative schematic, not a result', 'Esquema ilustrativo, no un resultado')}</text>
    </svg>
  );
}

/** The cumulative binomial probability of MAR32.9 Table 1 by number of exceptions, in the three zones. */
function ZonesFigure() {
  const t = useT();
  // P(X <= k), X ~ Bin(250, 0.01), in percent, k = 0..10 (MAR32.9 Table 1, dossier 01 D.4)
  const cum = [8.11, 28.58, 54.32, 75.81, 89.22, 95.88, 98.63, 99.6, 99.89, 99.97, 99.99];
  const left = 52;
  const bw = 32;
  const base = 200;
  const top = 36;
  const y = (v: number) => base - ((v / 100) * (base - top));
  const zone = (k: number) => (k <= 4 ? '--color-good' : k <= 9 ? '--color-warn' : '--color-bad');
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('Bars of the cumulative probability of 0 to 10 or more exceptions in 250 days at the 99 percent level: green for 0 to 4, amber for 5 to 9 and red for 10 or more', 'Barras de la probabilidad acumulada de 0 a 10 o más excepciones en 250 días al nivel de 99 por ciento: verde de 0 a 4, ámbar de 5 a 9 y rojo para 10 o más')}>
      <line className="dg-axis" x1={left - 8} y1={base} x2={W - 12} y2={base} />
      <line className="dg-grid" x1={left - 8} y1={y(95)} x2={W - 12} y2={y(95)} />
      <text className="dg-tick" x={W - 12} y={y(95) - 4} textAnchor="end">95</text>
      <text className="dg-tick" x={left - 12} y={y(100) + 4} textAnchor="end">100</text>
      <text className="dg-tick" x={left - 12} y={base + 4} textAnchor="end">0</text>
      {cum.map((v, k) => (
        <g key={k}>
          <rect style={zoneStyle(zone(k))} x={left + k * (bw + 2)} y={y(v)} width={bw} height={base - y(v)} />
          <text className="dg-tick" x={left + k * (bw + 2) + bw / 2} y={base + 15} textAnchor="middle">{k === 10 ? '10+' : k}</text>
        </g>
      ))}
      <text className="dg-axis-label" x={(left + W) / 2} y={base + 38} textAnchor="middle">{t('exceptions in 250 days', 'excepciones en 250 días')}</text>
      <text className="dg-axis-label" x={left - 8} y={22} textAnchor="start">{t('cumulative probability, %', 'probabilidad acumulada, %')}</text>
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('MAR32.9 Table 1 at 99 % coverage', 'MAR32.9 Tabla 1 a 99 % de cobertura')}</text>
    </svg>
  );
}

/** The PLA zones in the plane of the Kolmogorov-Smirnov statistic and the Spearman coefficient (MAR32.42). */
function PlaFigure() {
  const t = useT();
  const lang = useShellLang();
  const x = (ks: number) => 70 + (ks / 0.2) * 360;
  const y = (s: number) => 214 - ((s - 0.5) / 0.5) * 180;
  const amber = zoneStyle('--color-warn');
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('The plane of the Kolmogorov-Smirnov statistic and the Spearman coefficient split into the zones of the P&L attribution test: green for a Spearman above 0.80 and a KS below 0.09, red for a Spearman below 0.70 or a KS above 0.12, amber elsewhere', 'El plano del estadístico de Kolmogorov-Smirnov y el coeficiente de Spearman dividido en las zonas de la prueba de atribución de P&L: verde para un Spearman sobre 0,80 y un KS bajo 0,09, rojo para un Spearman bajo 0,70 o un KS sobre 0,12, ámbar en el resto')}>
      <rect style={amber} x={x(0)} y={y(1)} width={x(0.2) - x(0)} height={y(0.5) - y(1)} />
      <rect style={zoneStyle('--color-bad')} x={x(0)} y={y(0.7)} width={x(0.2) - x(0)} height={y(0.5) - y(0.7)} />
      <rect style={zoneStyle('--color-bad')} x={x(0.12)} y={y(1)} width={x(0.2) - x(0.12)} height={y(0.7) - y(1)} />
      <rect style={zoneStyle('--color-good')} x={x(0)} y={y(1)} width={x(0.09) - x(0)} height={y(0.8) - y(1)} />
      <line className="dg-axis" x1={x(0)} y1={y(0.5)} x2={x(0.2)} y2={y(0.5)} />
      <line className="dg-axis" x1={x(0)} y1={y(1)} x2={x(0)} y2={y(0.5)} />
      {[0, 0.09, 0.12, 0.2].map((v) => (
        <text key={v} className="dg-tick" x={x(v)} y={y(0.5) + 15} textAnchor="middle">{formatNumber(v, lang, { decimals: v === 0 || v === 0.2 ? 1 : 2 })}</text>
      ))}
      {[0.5, 0.7, 0.8, 1].map((v) => (
        <text key={v} className="dg-tick" x={x(0) - 14} y={y(v) + 4} textAnchor="end">{formatNumber(v, lang, { decimals: v === 0.5 || v === 1 ? 1 : 2 })}</text>
      ))}
      <text className="dg-box-title" x={(x(0) + x(0.09)) / 2} y={(y(1) + y(0.8)) / 2 + 4} textAnchor="middle">{t('green', 'verde')}</text>
      <text className="dg-box-title" x={(x(0.09) + x(0.12)) / 2} y={(y(0.8) + y(0.7)) / 2 + 4} textAnchor="middle">{t('amber', 'ámbar')}</text>
      <text className="dg-box-title" x={(x(0.12) + x(0.2)) / 2} y={(y(1) + y(0.7)) / 2} textAnchor="middle">{t('red', 'rojo')}</text>
      <text className="dg-box-title" x={(x(0) + x(0.2)) / 2} y={(y(0.7) + y(0.5)) / 2 + 4} textAnchor="middle">{t('red', 'rojo')}</text>
      <text className="dg-axis-label" x={(x(0) + x(0.2)) / 2} y={y(0.5) + 34} textAnchor="middle">{t('Kolmogorov-Smirnov statistic', 'estadístico de Kolmogorov-Smirnov')}</text>
      <text className="dg-axis-label" x={8} y={20} textAnchor="start">{t('Spearman coefficient', 'coeficiente de Spearman')}</text>
      <text className="dg-note" x={W - 8} y={20} textAnchor="end">{t('MAR32.42 zone boundaries', 'límites de zona de MAR32.42')}</text>
    </svg>
  );
}

/** The caption helper for the figures, outside a hook-bound component. */
function t2(en: string, es: string) {
  return <T en={en} es={es} />;
}

export function EstimatorsPart() {
  return (
    <>
      <P
        en={<>Contraste fixes one sign convention and states it on every view. The literature has two. In the loss convention of McNeil, Frey and Embrechts and of Basel the loss is L = -X for a P&amp;L or a return X, the VaR at a level α near 1 (0.99, 0.975) is the smallest ℓ with P(L &gt; ℓ) ≤ 1 - α, and the ES is the average of the VaR above α. In the return convention of Patton, Ziegel and Chen the returns are Y, the tail level α is small (0.01, 0.025), v is the α-quantile and e the average of the quantiles below α, both negative in practice <Cite id="patton2019" />. The engine stores the return convention, because the FZ0 score below needs it, and every document and every view of C11 and C13 shows positive losses as decimals of the portfolio value.</>}
        es={<>Contraste fija una convención de signo y la declara en cada vista. La literatura tiene dos. En la convención de pérdidas de McNeil, Frey y Embrechts y de Basilea la pérdida es L = -X para un P&amp;L o un retorno X, el VaR a un nivel α cercano a 1 (0,99; 0,975) es el menor ℓ con P(L &gt; ℓ) ≤ 1 - α, y la ES es el promedio del VaR sobre α. En la convención de retornos de Patton, Ziegel y Chen los retornos son Y, el nivel de cola α es pequeño (0,01; 0,025), v es el cuantil α y e el promedio de los cuantiles bajo α, ambos negativos en la práctica <Cite id="patton2019" />. El motor guarda la convención de retornos, porque el puntaje FZ0 de más abajo la necesita, y cada documento y cada vista de C11 y C13 muestra pérdidas positivas como decimales del valor de la cartera.</>}
      />
      <Equation
        tex={String.raw`v = F^{-1}(\alpha), \qquad e = \frac{1}{\alpha}\int_0^{\alpha} F^{-1}(u)\,du, \qquad \mathrm{VaR}^{\mathrm{rep}} = -v, \quad \mathrm{ES}^{\mathrm{rep}} = -e`}
        caption={<T en={<>The return convention (Patton, Ziegel and Chen 2019, equations <Ref>1</Ref> and <Ref>2</Ref> of arXiv <Ref>1707.05108</Ref>): F the distribution of the return Y, α the tail level, v the VaR and e the ES, both negative; the reporting layer converts them to the positive loss numbers of the documents.</>} es={<>La convención de retornos (Patton, Ziegel y Chen 2019, ecuaciones <Ref>1</Ref> y <Ref>2</Ref> de arXiv <Ref>1707.05108</Ref>): F la distribución del retorno Y, α el nivel de cola, v el VaR y e la ES, ambos negativos; la capa de reporte los convierte a los números de pérdida positivos de los documentos.</>} />}
      />
      <Figure caption={t2('A loss distribution with the VaR at the 99 % level and the ES as the mean of the tail beyond it; the documents show both as positive losses.', 'Una distribución de pérdidas con el VaR al nivel de 99 % y la ES como la media de la cola más allá de él; los documentos muestran ambos como pérdidas positivas.')}>
        <TailFigure />
      </Figure>
      <P
        en={<>VaR is not subadditive in general, so it is not a coherent measure of risk <Cite id="artzner1999" />; the ES defined by the tail integral, which also handles atoms, is coherent <Cite id="acerbitasche2002" />. A functional is elicitable when it is the unique minimiser of the expected value of a strictly consistent scoring function. Gneiting shows that quantiles are elicitable and that the ES alone is not <Cite id="gneiting2011" />; Fissler and Ziegel prove that the pair (VaR, ES) is jointly elicitable and characterise the whole class of strictly consistent joint scores <Cite id="fisslerziegel2016" />. This is why a model that forecasts both numbers can be compared on one score, and why a model that forecasts only the VaR has no such score.</>}
        es={<>El VaR no es subaditivo en general, así que no es una medida de riesgo coherente <Cite id="artzner1999" />; la ES definida por la integral de la cola, que además maneja átomos, es coherente <Cite id="acerbitasche2002" />. Un funcional es elicitable cuando es el único minimizador del valor esperado de una función de puntaje estrictamente consistente. Gneiting muestra que los cuantiles son elicitables y que la ES sola no lo es <Cite id="gneiting2011" />; Fissler y Ziegel prueban que el par (VaR, ES) es conjuntamente elicitable y caracterizan toda la clase de puntajes conjuntos estrictamente consistentes <Cite id="fisslerziegel2016" />. Por eso un modelo que pronostica ambos números se puede comparar con un solo puntaje, y por eso un modelo que pronostica solo el VaR no tiene tal puntaje.</>}
      />
      <P
        en={<>Patton, Ziegel and Chen write the Fissler-Ziegel class with two functions, G1 weakly increasing and G2 strictly increasing and positive. With the VaR and the ES strictly negative, the only member whose loss differences are homogeneous of degree zero takes G1 = 0 and G2(x) = -1/x, which gives the FZ0 loss of the display below <Cite id="patton2019" />. FZ0 has no tuning parameter, which makes it the default score of Contraste for comparing models, in the Diebold-Mariano test and in the model confidence set. A model is never ranked on FZ0 alone: the traditional back-tests decide eligibility first, and FZ0 ranks the eligible.</>}
        es={<>Patton, Ziegel y Chen escriben la clase de Fissler y Ziegel con dos funciones, G1 débilmente creciente y G2 estrictamente creciente y positiva. Con el VaR y la ES estrictamente negativos, el único miembro cuyas diferencias de pérdida son homogéneas de grado cero toma G1 = 0 y G2(x) = -1/x, lo que da la pérdida FZ0 de la ecuación siguiente <Cite id="patton2019" />. FZ0 no tiene parámetro de ajuste, lo que la hace el puntaje por defecto de Contraste para comparar modelos, en la prueba de Diebold-Mariano y en el conjunto de confianza de modelos. Un modelo nunca se ordena solo por FZ0: las pruebas retrospectivas tradicionales deciden primero la elegibilidad, y FZ0 ordena a los elegibles.</>}
      />
      <Equation
        tex={String.raw`L_{FZ0}(Y, v, e; \alpha) = -\frac{1}{\alpha\, e}\,\mathbb{1}\{Y \le v\}\,(v - Y) + \frac{v}{e} + \log(-e) - 1`}
        caption={<T en={<>The FZ0 loss (arXiv <Ref>1707.05108</Ref>, equation <Ref>6</Ref>): Y the realised return, v &lt; 0 the VaR forecast, e &lt; 0 the ES forecast with e ≤ v, α the tail probability; lower is better. A model that forecasts no ES has no FZ0 and says why.</>} es={<>La pérdida FZ0 (arXiv <Ref>1707.05108</Ref>, ecuación <Ref>6</Ref>): Y el retorno realizado, v &lt; 0 el pronóstico de VaR, e &lt; 0 el pronóstico de ES con e ≤ v, α la probabilidad de cola; menor es mejor. Un modelo que no pronostica la ES no tiene FZ0 y dice por qué.</>} />}
      />
      <P
        en={<>The ladder runs from the textbook to the current research. Historical simulation takes the empirical α-quantile of the last K scenarios and reacts slowly to a change of regime <Cite id="pritsker2001" />; the age-weighted version gives the observation i days old the weight (1 - λ)λ^(i-1)/(1 - λ^K) <Cite id="bwr1998" />; filtered historical simulation rescales standardised residuals by the new volatility <Cite id="bgv1999" /> <Cite id="hullwhite1998" />. The parametric rungs are delta-normal <Cite id="riskmetrics1996" />, Cornish-Fisher, whose expansion is not monotone for a large skewness and kurtosis so its validity domain is reported <Cite id="cornishfisher1938" />, and the EWMA with λ = 0.94 for daily data. GARCH(1,1), GJR and EGARCH with Student-t innovations follow <Cite id="bollerslev1986" /> <Cite id="gjr1993" /> <Cite id="nelson1991" />, then conditional extreme value theory <Cite id="mcneilfrey2000" />, CAViaR, which forecasts the VaR only <Cite id="engle2004" /> and gets an ES from the extension of Taylor <Cite id="taylor2019" />, and the GAS models estimated on FZ0 <Cite id="patton2019" />. A neural quantile model enters as a challenger only: no supervisor recognises it, and it must earn a place in the confidence set out of sample.</>}
        es={<>La escalera va del texto de referencia a la investigación actual. La simulación histórica toma el cuantil α empírico de los últimos K escenarios y reacciona lento a un cambio de régimen <Cite id="pritsker2001" />; la versión ponderada por edad da a la observación de i días de antigüedad el peso (1 - λ)λ^(i-1)/(1 - λ^K) <Cite id="bwr1998" />; la simulación histórica filtrada reescala residuos estandarizados con la nueva volatilidad <Cite id="bgv1999" /> <Cite id="hullwhite1998" />. Los escalones paramétricos son delta-normal <Cite id="riskmetrics1996" />, Cornish-Fisher, cuya expansión no es monótona para una asimetría y una curtosis grandes y por eso se informa su dominio de validez <Cite id="cornishfisher1938" />, y el EWMA con λ = 0,94 para datos diarios. Siguen GARCH(1,1), GJR y EGARCH con innovaciones t de Student <Cite id="bollerslev1986" /> <Cite id="gjr1993" /> <Cite id="nelson1991" />, luego la teoría de valores extremos condicional <Cite id="mcneilfrey2000" />, CAViaR, que pronostica solo el VaR <Cite id="engle2004" /> y obtiene una ES con la extensión de Taylor <Cite id="taylor2019" />, y los modelos GAS estimados sobre FZ0 <Cite id="patton2019" />. Un modelo neuronal de cuantiles entra solo como retador: ningún supervisor lo reconoce y debe ganarse un lugar en el conjunto de confianza fuera de muestra.</>}
      />
      <Equation
        tex={String.raw`\sigma^2_{t+1\mid t} = \lambda\,\sigma^2_{t\mid t-1} + (1-\lambda)\,r_t^2, \qquad K_{\varepsilon} = \frac{\ln \varepsilon}{\ln \lambda}`}
        caption={<T en={<>The EWMA of RiskMetrics (technical document, section <Ref>5.3.2</Ref>): λ the decay factor, 0.94 for daily data and 0.97 for monthly, r<sub>t</sub> the return, K_ε the effective number of days at tolerance ε: 74 days at 1 % for 0.94 and 151 days for 0.97. The zero mean is part of the method.</>} es={<>El EWMA de RiskMetrics (documento técnico, sección <Ref>5.3.2</Ref>): λ el factor de decaimiento, 0,94 para datos diarios y 0,97 para mensuales, r<sub>t</sub> el retorno, K_ε el número efectivo de días a la tolerancia ε: 74 días al 1 % para 0,94 y 151 días para 0,97. La media cero es parte del método.</>} />}
      />
      <Equation
        tex={String.raw`\hat z_q = u + \frac{\hat\beta}{\hat\xi}\Bigl[\Bigl(\tfrac{n}{N_u}(1-q)\Bigr)^{-\hat\xi} - 1\Bigr], \quad \widehat{\mathrm{ES}}_q(z) = \frac{\hat z_q}{1-\hat\xi} + \frac{\hat\beta - \hat\xi\, u}{1-\hat\xi}, \quad \mathrm{VaR}_{t+1} = \mu_{t+1} + \sigma_{t+1}\,\hat z_q`}
        caption={<T en={<>Conditional extreme value theory (McNeil and Frey 2000), in the loss convention with q near 1: z the standardised residuals of the AR-GARCH filter, u the threshold, N<sub>u</sub> the excesses out of n, β̂ and ξ̂ the scale and shape of the generalised Pareto fit. The ES formula holds for ξ̂ &lt; 1; on a day with ξ̂ at or above 1 the ES is undefined and is a gap in the series, never a number.</>} es={<>Teoría de valores extremos condicional (McNeil y Frey 2000), en la convención de pérdidas con q cercano a 1: z los residuos estandarizados del filtro AR-GARCH, u el umbral, N<sub>u</sub> los excesos de n, β̂ y ξ̂ la escala y la forma del ajuste de Pareto generalizada. La fórmula de la ES vale para ξ̂ &lt; 1; en un día con ξ̂ igual o mayor que 1 la ES no está definida y es un hueco en la serie, nunca un número.</>} />}
      />
    </>
  );
}

export function BacktestsPart() {
  return (
    <>
      <P
        en={<>A back-test counts the days on which the loss exceeded the VaR: I<sub>t</sub> = 1{'{'}loss<sub>t</sub> &gt; VaR<sub>t</sub>{'}'}, with p = 1 - α the nominal exceedance probability and x the number of exceedances in T days. The proportion-of-failures test of Kupiec compares x/T with p and is χ² with one degree of freedom, with critical value 3.841 at 5 % <Cite id="kupiec1995" />. Its weakness is power: with T = 250 and p = 0.01 only 2.5 exceedances are expected, so Contraste prints the exact binomial p-value next to the asymptotic one. Christoffersen adds independence, a test that exceedances do not cluster, built on the transitions between exceedance and no exceedance; the sum of the two is the conditional coverage test, with 2 degrees of freedom and critical value 5.991 <Cite id="christoffersen1998" />. With no exceedance, or with all, there is nothing to test for clustering and the row says not evaluated.</>}
        es={<>Una prueba retrospectiva cuenta los días en que la pérdida superó al VaR: I<sub>t</sub> = 1{'{'}pérdida<sub>t</sub> &gt; VaR<sub>t</sub>{'}'}, con p = 1 - α la probabilidad nominal de excedencia y x el número de excedencias en T días. La prueba de proporción de fallas de Kupiec compara x/T con p y es χ² con un grado de libertad, con valor crítico 3,841 al 5 % <Cite id="kupiec1995" />. Su debilidad es la potencia: con T = 250 y p = 0,01 solo se esperan 2,5 excedencias, así que Contraste imprime el valor p binomial exacto junto al asintótico. Christoffersen agrega independencia, una prueba de que las excedencias no se agrupan, construida sobre las transiciones entre excedencia y no excedencia; la suma de ambas es la prueba de cobertura condicional, con 2 grados de libertad y valor crítico 5,991 <Cite id="christoffersen1998" />. Sin ninguna excedencia, o con todas, no hay nada que probar sobre agrupamiento y la fila dice no evaluada.</>}
      />
      <Equation
        tex={String.raw`LR_{POF} = -2\ln\frac{(1-p)^{T-x}\,p^{x}}{(1-\hat\pi)^{T-x}\,\hat\pi^{x}}, \quad \hat\pi = \frac{x}{T}, \qquad LR_{cc} = LR_{POF} + LR_{ind}`}
        caption={<T en={<>Kupiec (1995) and Christoffersen (1998): p the nominal exceedance probability, π̂ the observed one; LR<sub>POF</sub> is χ² with 1 degree of freedom, LR<sub>ind</sub> (the independence statistic built on the transition counts n<sub>ij</sub> between exceedance states) is χ² with 1, and LR<sub>cc</sub> is χ² with 2. The convention 0<sup>0</sup> = 1 applies when n<sub>11</sub> = 0.</>} es={<>Kupiec (1995) y Christoffersen (1998): p la probabilidad nominal de excedencia, π̂ la observada; LR<sub>POF</sub> es χ² con 1 grado de libertad, LR<sub>ind</sub> (el estadístico de independencia construido sobre los conteos de transición n<sub>ij</sub> entre estados de excedencia) es χ² con 1, y LR<sub>cc</sub> es χ² con 2. Se aplica la convención 0<sup>0</sup> = 1 cuando n<sub>11</sub> = 0.</>} />}
      />
      <P
        en={<>The duration test of Christoffersen and Pelletier looks at the days between exceedances: under correct conditional coverage the durations are memoryless, which in a Weibull hazard means that the shape parameter equals 1, and a likelihood ratio tests it with Monte Carlo p-values for small samples <Cite id="cp2004" />. The Weibull parameterisation is the usual one of the later literature; the exact form in the paper was not read in full and is unverified. The Basel traffic light turns the count of exceedances in the last 250 days at the 99 % level into a zone. The boundary between green and amber sits where the binomial cumulative probability first reaches 95 %, the red zone where it reaches 99.99 %, and the framework gives each count its multiplier: 1.50 for 0 to 4 exceptions, 1.70, 1.76, 1.83, 1.88 and 1.92 for 5 to 9, and 2.00 for 10 or more <Cite id="mar32" /> <Cite id="bcbs22" />.</>}
        es={<>La prueba de duración de Christoffersen y Pelletier mira los días entre excedencias: con cobertura condicional correcta las duraciones no tienen memoria, lo que en un riesgo de Weibull significa que el parámetro de forma vale 1, y una razón de verosimilitud lo prueba con valores p de Monte Carlo para muestras pequeñas <Cite id="cp2004" />. La parametrización de Weibull es la habitual de la literatura posterior; la forma exacta del artículo no se leyó completa y no está verificada. El semáforo de Basilea convierte la cuenta de excedencias de los últimos 250 días al nivel de 99 % en una zona. El límite entre verde y ámbar está donde la probabilidad binomial acumulada alcanza por primera vez 95 %, la zona roja donde alcanza 99,99 %, y el marco da a cada cuenta su multiplicador: 1,50 para 0 a 4 excepciones, 1,70, 1,76, 1,83, 1,88 y 1,92 para 5 a 9, y 2,00 para 10 o más <Cite id="mar32" /> <Cite id="bcbs22" />.</>}
      />
      <Equation
        tex={String.raw`P(X \le x) = \sum_{i=0}^{x}\binom{250}{i}(0.01)^{i}(0.99)^{250-i}, \qquad X \sim \mathrm{Bin}(250,\, 0.01)`}
        caption={<T en={<>The cumulative probability of <Ref>MAR32.9</Ref> Table 1: 8.11, 28.58, 54.32, 75.81 and 89.22 % for 0 to 4 exceptions (green), 95.88, 98.63, 99.60, 99.89 and 99.97 % for 5 to 9 (amber), 99.99 % for 10 (red). The US implementation (<Ref>12 CFR 217.204</Ref>, <Cite id="cfr217204" paren={false} />) uses the factors 3.00 in green, 3.40, 3.50, 3.65, 3.75 and 3.85 in amber and 4.00 in red.</>} es={<>La probabilidad acumulada de la Tabla 1 de <Ref>MAR32.9</Ref>: 8,11; 28,58; 54,32; 75,81 y 89,22 % para 0 a 4 excepciones (verde), 95,88; 98,63; 99,60; 99,89 y 99,97 % para 5 a 9 (ámbar), 99,99 % para 10 (rojo). La implementación de EE.UU. (<Ref>12 CFR 217.204</Ref>, <Cite id="cfr217204" paren={false} />) usa los factores 3,00 en verde, 3,40; 3,50; 3,65; 3,75 y 3,85 en ámbar y 4,00 en rojo.</>} />}
      />
      <Figure caption={t2('The cumulative probability of each exception count in 250 days for a correct 99 % VaR: green up to 4, amber from 5 and red from 10, where the probability reaches 99.99 %.', 'La probabilidad acumulada de cada cuenta de excepciones en 250 días para un VaR correcto de 99 %: verde hasta 4, ámbar desde 5 y rojo desde 10, donde la probabilidad alcanza 99,99 %.')}>
        <ZonesFigure />
      </Figure>
      <P
        en={<>The ES needs its own tests. Acerbi and Szekely define, with X<sub>t</sub> the P&amp;L, the VaR and ES as positive numbers and N<sub>T</sub> the number of exceedances, the statistics Z1 and Z2, which have expectation zero under the null and are negative when the risk is underestimated <Cite id="acerbiszekely2014" />. Their critical values depend on the model, so Contraste simulates the null distribution of Z2 per model from its predictive distribution and draws the realised statistic against the model&apos;s own 5 % and 0.01 % critical values. The values -0.70 and -1.8 that the authors suggest for 250 days at 2.5 % are drawn only as a published reference, never as a threshold: the primary text is gated and the values are confirmed through a secondary source <Cite id="moldenhauer2018" />. Du and Escanciano test the cumulative violation process, unconditionally and with a Box-Pierce statistic on its autocorrelations <Cite id="duescanciano2017" />; McNeil and Frey test the residuals on exceedance days <Cite id="mcneilfrey2000" />.</>}
        es={<>La ES necesita sus propias pruebas. Acerbi y Szekely definen, con X<sub>t</sub> el P&amp;L, el VaR y la ES como números positivos y N<sub>T</sub> el número de excedencias, los estadísticos Z1 y Z2, que tienen esperanza cero bajo la nula y son negativos cuando el riesgo está subestimado <Cite id="acerbiszekely2014" />. Sus valores críticos dependen del modelo, así que Contraste simula la distribución nula de Z2 por modelo desde su distribución predictiva y dibuja el estadístico realizado contra los valores críticos propios del modelo al 5 % y al 0,01 %. Los valores -0,70 y -1,8 que sugieren los autores para 250 días al 2,5 % se dibujan solo como una referencia publicada, nunca como un umbral: el texto primario es de acceso restringido y los valores se confirman por una fuente secundaria <Cite id="moldenhauer2018" />. Du y Escanciano prueban el proceso de violación acumulada, de forma incondicional y con un estadístico de Box-Pierce sobre sus autocorrelaciones <Cite id="duescanciano2017" />; McNeil y Frey prueban los residuos de los días de excedencia <Cite id="mcneilfrey2000" />.</>}
      />
      <Equation
        tex={String.raw`Z_2 = \sum_{t=1}^{T}\frac{X_t\, I_t}{T\,\alpha\,\mathrm{ES}_{\alpha,t}} + 1`}
        caption={<T en={<>Z2 of Acerbi and Szekely (2014): X<sub>t</sub> the P&amp;L, I<sub>t</sub> the exceedance indicator, ES_(α,t) the positive ES forecast, T the days and α the tail level (2.5 %); E[Z2] = 0 under the null, and a negative value means the ES is too low.</>} es={<>Z2 de Acerbi y Szekely (2014): X<sub>t</sub> el P&amp;L, I<sub>t</sub> el indicador de excedencia, ES_(α,t) el pronóstico positivo de ES, T los días y α el nivel de cola (2,5 %); E[Z2] = 0 bajo la nula, y un valor negativo significa que la ES es demasiado baja.</>} />}
      />
      <P
        en={<>Eligibility is only half of a validation. Nolde and Ziegel separate the traditional back-test, whose null is that the model is correct, from the comparative back-test, whose null is that the model is at least as good as a standard one under a consistent score <Cite id="nolde2017" />. Contraste applies both: the traditional tests of a model are its eligibility gates, and among the eligible the champion is the one with the lowest average FZ0. The Diebold-Mariano test compares each model with the champion on the loss differential, with a long-run variance robust to autocorrelation (Bartlett kernel, zero lags for one-step forecasts) <Cite id="dm1995" />, using the tick loss for the VaR and FZ0 for the pair. The model confidence set eliminates models one by one with a bootstrap test and returns the set that contains the best model with the stated confidence <Cite id="hln2011" />; a model outside it is statistically worse than the rest.</>}
        es={<>La elegibilidad es solo la mitad de una validación. Nolde y Ziegel separan la prueba retrospectiva tradicional, cuya nula es que el modelo es correcto, de la prueba retrospectiva comparativa, cuya nula es que el modelo es al menos tan bueno como uno estándar bajo un puntaje consistente <Cite id="nolde2017" />. Contraste aplica ambos: las pruebas tradicionales de un modelo son sus compuertas de elegibilidad, y entre los elegibles el campeón es el de menor FZ0 medio. La prueba de Diebold-Mariano compara cada modelo con el campeón sobre el diferencial de pérdida, con una varianza de largo plazo robusta a la autocorrelación (núcleo de Bartlett, cero rezagos para pronósticos a un paso) <Cite id="dm1995" />, con la pérdida cuantílica para el VaR y FZ0 para el par. El conjunto de confianza de modelos elimina modelos uno a uno con una prueba remuestreo con reposición y devuelve el conjunto que contiene al mejor modelo con la confianza declarada <Cite id="hln2011" />; un modelo fuera de él es estadísticamente peor que el resto.</>}
      />
      <Equation
        tex={String.raw`DM = \frac{\bar d}{\sqrt{\widehat{\mathrm{LRV}}(d)\,/\,T}} \overset{a}{\sim} N(0,1), \qquad d_t = L(Y_t, f^{A}_t) - L(Y_t, f^{B}_t)`}
        caption={<T en={<>Diebold-Mariano (1995): d<sub>t</sub> the loss differential of model A against model B (the champion) on the days both are defined, d̄ its mean, LRV its long-run variance; the statistic is asymptotically standard normal, and a negative value favours model A. L is the tick loss for the VaR or the FZ0 loss for the pair.</>} es={<>Diebold-Mariano (1995): d<sub>t</sub> el diferencial de pérdida del modelo A contra el modelo B (el campeón) en los días en que ambos están definidos, d̄ su media, LRV su varianza de largo plazo; el estadístico es asintóticamente normal estándar, y un valor negativo favorece al modelo A. L es la pérdida cuantílica para el VaR o la pérdida FZ0 para el par.</>} />}
      />
    </>
  );
}

export function DeskPart() {
  return (
    <>
      <P
        en={<>The Basel framework back-tests at two levels. Bank-wide (<Ref>MAR32.4</Ref> to <Ref>MAR32.9</Ref>) the one-day 99 % VaR is compared with both the actual and the hypothetical P&amp;L of the last 250 days, the exceptions are counted separately for each, the larger count sets the zone, and a missing P&amp;L or VaR counts as an exception <Cite id="mar32" />. At desk level (<Ref>MAR32.18</Ref> to <Ref>MAR32.19</Ref>) the 97.5 % and the 99 % VaR of each desk are compared with at least one year of its actual and hypothetical P&amp;L: a desk with more than 12 exceptions at 99 % or more than 30 at 97.5 % in the last 12 months moves to the standardised approach. C13 runs this test on every replication of a desk with a planted deficiency and reports the share of replications over the limit.</>}
        es={<>El marco de Basilea hace pruebas retrospectivas en dos niveles. A nivel de banco (<Ref>MAR32.4</Ref> a <Ref>MAR32.9</Ref>) el VaR a un día de 99 % se compara con el P&amp;L real y con el hipotético de los últimos 250 días, las excepciones se cuentan por separado para cada uno, la cuenta mayor fija la zona, y un P&amp;L o un VaR faltante cuenta como excepción <Cite id="mar32" />. A nivel de mesa (<Ref>MAR32.18</Ref> a <Ref>MAR32.19</Ref>) el VaR de 97,5 % y de 99 % de cada mesa se compara con al menos un año de su P&amp;L real e hipotético: una mesa con más de 12 excepciones al 99 % o más de 30 al 97,5 % en los últimos 12 meses pasa al método estandarizado. C13 corre esta prueba en cada replicación de una mesa con una deficiencia sembrada e informa la parte de replicaciones sobre el límite.</>}
      />
      <P
        en={<>The P&amp;L attribution test compares the hypothetical P&amp;L (HPL) with the risk-theoretical P&amp;L (RTPL) that the risk model produces, on the most recent 250 trading days (<Ref>MAR32.20</Ref> to <Ref>MAR32.44</Ref>). Two statistics decide. The Spearman coefficient is the correlation of the two series after replacing each value by its rank (<Ref>MAR32.36</Ref> to <Ref>MAR32.38</Ref>), so it measures whether the model orders the days as the desk&apos;s own revaluation does. The Kolmogorov-Smirnov statistic is the largest vertical gap between the empirical distribution functions of the two series, each rising by 0.004 per observation (<Ref>MAR32.39</Ref> to <Ref>MAR32.41</Ref>), so it measures whether the model reproduces the distribution of the P&amp;L, not only its order.</>}
        es={<>La prueba de atribución de P&amp;L compara el P&amp;L hipotético (HPL) con el P&amp;L teórico del riesgo (RTPL) que produce el modelo de riesgo, en los 250 días hábiles más recientes (<Ref>MAR32.20</Ref> a <Ref>MAR32.44</Ref>). Deciden dos estadísticos. El coeficiente de Spearman es la correlación de las dos series tras reemplazar cada valor por su rango (<Ref>MAR32.36</Ref> a <Ref>MAR32.38</Ref>), así que mide si el modelo ordena los días como lo hace la revaluación propia de la mesa. El estadístico de Kolmogorov-Smirnov es la mayor brecha vertical entre las funciones de distribución empíricas de las dos series, cada una subiendo 0,004 por observación (<Ref>MAR32.39</Ref> a <Ref>MAR32.41</Ref>), así que mide si el modelo reproduce la distribución del P&amp;L, no solo su orden.</>}
      />
      <Equation
        tex={String.raw`r_S = \frac{\operatorname{cov}(R_{HPL},\, R_{RTPL})}{\sigma_{R_{HPL}}\,\sigma_{R_{RTPL}}}, \qquad KS = \sup_x \bigl|F_{RTPL}(x) - F_{HPL}(x)\bigr|, \quad F(x) = 0.004 \times \#\{\text{obs} \le x\}`}
        caption={<T en={<>The two PLA statistics (<Ref>MAR32.36</Ref> to <Ref>MAR32.41</Ref>): R the rank series of the HPL and the RTPL, F the empirical distribution function in steps of 1/250. The largest gap is an exact count of steps over 250, so 30 steps are exactly 0.12.</>} es={<>Los dos estadísticos del PLA (<Ref>MAR32.36</Ref> a <Ref>MAR32.41</Ref>): R las series de rangos del HPL y del RTPL, F la función de distribución empírica en pasos de 1/250. La mayor brecha es una cuenta exacta de pasos sobre 250, así que 30 pasos son exactamente 0,12.</>} />}
      />
      <P
        en={<>The zones are a joint rule (<Ref>MAR32.42</Ref>). Green needs a Spearman above 0.80 and a KS below 0.09 (p-value 0.264); red is a Spearman below 0.70 or a KS above 0.12 (p-value 0.055); amber is everything else. A red desk is not eligible for the internal models approach and returns only after a green PLA and satisfied back-testing over 12 months (<Ref>MAR32.43</Ref>); an amber desk stays in the approach with a capital surcharge (<Ref>MAR32.44</Ref> and <Ref>MAR33.43</Ref>). These boundaries are regulatory and transcribed; the levels that turn a p-value into a light for the traditional back-tests are an institution&apos;s policy.</>}
        es={<>Las zonas son una regla conjunta (<Ref>MAR32.42</Ref>). Verde exige un Spearman sobre 0,80 y un KS bajo 0,09 (valor p 0,264); rojo es un Spearman bajo 0,70 o un KS sobre 0,12 (valor p 0,055); ámbar es todo lo demás. Una mesa roja no es elegible para el método de modelos internos y vuelve solo tras un PLA verde y una prueba retrospectiva satisfactoria durante 12 meses (<Ref>MAR32.43</Ref>); una mesa ámbar sigue en el método con un recargo de capital (<Ref>MAR32.44</Ref> y <Ref>MAR33.43</Ref>). Estos límites son regulatorios y están transcritos; los niveles que convierten un valor p en una luz para las pruebas retrospectivas tradicionales son una política de la institución.</>}
      />
      <Equation
        tex={String.raw`\text{green: } r_S > 0.80 \,\wedge\, KS < 0.09, \qquad \text{red: } r_S < 0.70 \,\vee\, KS > 0.12, \qquad \text{amber: otherwise}`}
        caption={<T en={<>The PLA zones of <Ref>MAR32.42</Ref> for the 250 days of one desk: both statistics must be green for a green desk, and one red statistic makes the desk red.</>} es={<>Las zonas del PLA de <Ref>MAR32.42</Ref> para los 250 días de una mesa: ambos estadísticos deben ser verdes para una mesa verde, y un estadístico rojo vuelve roja a la mesa.</>} />}
      />
      <Figure caption={t2('The zones of the P&L attribution test in the plane of the two statistics: a desk is green only inside the small corner, and red as soon as one statistic crosses its red boundary.', 'Las zonas de la prueba de atribución de P&L en el plano de los dos estadísticos: una mesa es verde solo dentro de la esquina pequeña, y roja apenas un estadístico cruza su límite rojo.')}>
        <PlaFigure />
      </Figure>
      <P
        en={<>C13 does not test a bank: it tests the test. A generator draws the desk P&amp;L from a known risk model, plants one of six cases in the model that produces the RTPL (no deficiency, which is the control, a missing basis, a stale volatility, a wrong correlation, an omitted risk factor or a time misalignment), and runs the PLA and the desk back-test on independent replications with fixed seeds. Because the truth is known, the share of replications in which the desk lands amber or red is the power of the PLA against that deficiency, and for the control desk it is the false-alarm rate, the size. The P&amp;L is synthetic and every view of C13 says so.</>}
        es={<>C13 no prueba un banco: prueba la prueba. Un generador simula el P&amp;L de la mesa desde un modelo de riesgo conocido, siembra uno de seis casos en el modelo que produce el RTPL (ninguna deficiencia, que es el control, una base omitida, una volatilidad desactualizada, una correlación errónea, un factor de riesgo omitido o un desfase temporal), y corre el PLA y la prueba retrospectiva de mesa en replicaciones independientes con semillas fijas. Como la verdad es conocida, la parte de replicaciones en que la mesa cae en ámbar o rojo es la potencia del PLA contra esa deficiencia, y para la mesa de control es la tasa de falsas alarmas, el tamaño. El P&amp;L es sintético y cada vista de C13 lo dice.</>}
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
      title={{ en: 'Market risk: VaR and ES, their back-tests and the FRTB desk tests', es: 'Riesgo de mercado: VaR y ES, sus pruebas retrospectivas y las pruebas de mesa FRTB' }}
      refs={['mar32', 'bcbs22', 'cfr217204', 'artzner1999', 'acerbitasche2002', 'gneiting2011', 'fisslerziegel2016', 'patton2019', 'pritsker2001', 'bwr1998', 'bgv1999', 'hullwhite1998', 'riskmetrics1996', 'cornishfisher1938', 'bollerslev1986', 'gjr1993', 'nelson1991', 'mcneilfrey2000', 'engle2004', 'taylor2019', 'kupiec1995', 'christoffersen1998', 'cp2004', 'acerbiszekely2014', 'moldenhauer2018', 'duescanciano2017', 'nolde2017', 'dm1995', 'hln2011']}
    >
      <SubTabs
        ariaLabel={t('Parts of the topic', 'Partes del tema')}
        tabs={[
          { id: 'estimators', label: t('VaR and ES estimators', 'Estimadores de VaR y ES'), content: <EstimatorsPart /> },
          { id: 'backtests', label: t('Back-tests and comparison', 'Pruebas retrospectivas y comparación'), content: <BacktestsPart /> },
          { id: 'desk', label: t('FRTB desk tests', 'Pruebas de mesa FRTB'), content: <DeskPart /> },
        ]}
      />
      <Callout variant="honest" title={t('What is exact, what is policy and what these views are not', 'Qué es exacto, qué es política y qué no son estas vistas')}>
        <T
          en={<>The formulas, the <Ref>MAR32.9</Ref> Table 1 and the <Ref>MAR32.42</Ref> boundaries are exact as transcribed from the sources; the amber and red levels that light a traditional back-test are an institution&apos;s policy, not regulation. Four details are unverified: the Weibull parameterisation of the duration test, the exact top fraction of residuals that McNeil and Frey use for the threshold (about 10 %), the origin of Cornish-Fisher VaR in the RiskMetrics Monitor of 1996, and the reference values of Acerbi and Szekely, which come through a secondary source; the 1996 Basel plus factors were cross-checked against <Ref>12 CFR 217.204</Ref> and the exact binomial probabilities because the BIS file could not be fetched. C11 forecasts real public series for a portfolio stated in each window, not the book of any bank, with the hyperparameters fixed on 1995 to 2003 and never tuned on a test window; the Kenneth French returns are derived-only, so only results are committed. C13 is synthetic, with a known truth. Neither is a regulatory submission, and the neural challenger of the ladder is not trained.</>}
          es={<>Las fórmulas, la Tabla 1 de <Ref>MAR32.9</Ref> y los límites de <Ref>MAR32.42</Ref> son exactos tal como se transcribieron de las fuentes; los niveles ámbar y rojo que encienden la luz de una prueba retrospectiva tradicional son política de la institución, no regulación. Cuatro detalles no están verificados: la parametrización de Weibull de la prueba de duración, la fracción superior exacta de residuos que McNeil y Frey usan para el umbral (cerca de 10 %), el origen del VaR de Cornish-Fisher en el RiskMetrics Monitor de 1996, y los valores de referencia de Acerbi y Szekely, que llegan por una fuente secundaria; los factores adicionales de Basilea de 1996 se contrastaron con <Ref>12 CFR 217.204</Ref> y con las probabilidades binomiales exactas porque no se pudo descargar el archivo del BIS. C11 pronostica series públicas reales para una cartera declarada en cada ventana, no el libro de ningún banco, con los hiperparámetros fijados en 1995 a 2003 y nunca ajustados en una ventana de prueba; los retornos de Kenneth French son solo derivados, así que solo se publican resultados. C13 es sintético, con una verdad conocida. Ninguno es una presentación regulatoria, y el retador neuronal de la escalera no está entrenado.</>}
        />
      </Callout>
    </DocSection>
  );
}

export const methodologySection: MethodologySection = {
  id: 'market',
  group: 'market',
  order: 120,
  title: { en: 'Market risk', es: 'Riesgo de mercado' },
  Body,
};
