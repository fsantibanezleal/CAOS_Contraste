// The Methodology section on loss given default and exposure at default (U6): the workout LGD, the shape of its
// distribution, the model ladder, the downturn add-on and the IRB LGD floors of case C08, and the conversion factor, the
// reference-date designs, the treatments of a CCF outside [0, 1], the models with and without the CCF and the EAD floor
// of case C09. Transcribed from research dossier 04 (credit-risk models, sections F.1 to F.4 and G.1 to G.3, where the
// workout formula, the model table, the benchmarks, the CCF identity and the terminology of Qi (2009) were read at their
// primary source or, where marked UNVERIFIED, through a summary) and dossier 01 (the Basel framework, section A.5 and C:
// the LGD floors, the EAD floor and the standardised CCFs). Every display equation carries a caption that defines its
// symbols. The registry mounts it as one tab of the loss group; one file exports one section, so the topic is one
// `method` section with one part per question, as sub-tabs (ADR-0017 section 2.1), each part with its own paragraphs,
// equations and figure, and one honest callout for the topic.
import { Callout, Cite, DocSection, Equation, Figure, SubTabs } from '@fasl-work/caos-app-shell';
import { P, Ref, T, useT } from '../../content/bi';
import type { MethodologySection } from '../methodologyRegistry';

const W = 480;
const H = 276;

/** A loss given default on [0, 1] with its masses at both ends and the values outside it kept and flagged. */
function LgdFigure() {
  const t = useT();
  // value v in [-0.2, 1.2] to x in [40, 460]; the tenths are 30 px wide
  const x = (v: number) => 40 + ((v + 0.2) / 1.4) * 420;
  const base = 196;
  const heights = [96, 36, 28, 24, 22, 24, 32, 46, 74, 150];
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('A loss given default distribution on 0 to 1 with a mass at 0 and a larger mass at 1, and small bars outside the range that are flagged and not clipped', 'Una distribución de la pérdida dado el incumplimiento en 0 a 1 con una masa en 0 y una masa mayor en 1, y barras pequeñas fuera del rango que se marcan y no se recortan')}>
      <line className="dg-axis" x1={x(-0.2)} y1={base} x2={x(1.2)} y2={base} />
      {heights.map((h, i) => (
        <rect key={i} className="dg-fill-accent" x={x(i / 10) + 1} y={base - h} width={x(0.1) - x(0) - 2} height={h} />
      ))}
      <rect className="dg-fill-warn" x={x(-0.1) + 1} y={base - 14} width={x(0.1) - x(0) - 2} height={14} />
      <rect className="dg-fill-warn" x={x(1) + 1} y={base - 24} width={x(0.1) - x(0) - 2} height={24} />
      <line className="dg-marker" x1={x(0)} y1={30} x2={x(0)} y2={base + 6} />
      <line className="dg-marker" x1={x(1)} y1={30} x2={x(1)} y2={base + 6} />
      <text className="dg-marker-label" x={x(0)} y={base + 20} textAnchor="middle">0</text>
      <text className="dg-marker-label" x={x(1)} y={base + 20} textAnchor="middle">1</text>
      <text className="dg-tick" x={x(0.5)} y={base + 20} textAnchor="middle">{t('0.5', '0,5')}</text>
      <text className="dg-axis-label" x={x(0) + 6} y={32} textAnchor="start">{t('mass at 0', 'masa en 0')}</text>
      <text className="dg-axis-label" x={x(1) - 6} y={32} textAnchor="end">{t('mass at 1', 'masa en 1')}</text>
      <text className="dg-note" x={x(-0.15)} y={base - 20} textAnchor="start">{t('below 0', 'bajo 0')}</text>
      <text className="dg-note" x={x(1.15)} y={base - 30} textAnchor="end">{t('above 1', 'sobre 1')}</text>
      <text className="dg-axis-label" x={W / 2} y={base + 44} textAnchor="middle">{t('LGD, flagged and counted outside 0 and 1, never clipped', 'LGD, marcada y contada fuera de 0 y 1, nunca recortada')}</text>
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('Illustrative schematic, not a result', 'Esquema ilustrativo, no un resultado')}</text>
    </svg>
  );
}

/** The three reference-date designs for one defaulted facility: where each reads the drawn balance and the limit. */
function DesignsFigure() {
  const t = useT();
  const xs = (monthsBefore: number) => 450 - monthsBefore * 20;
  const rows = [
    { y: 46, name: t('Fixed horizon', 'Horizonte fijo'), note: t('one date, 12 months before default', 'una fecha, 12 meses antes del incumplimiento'), refs: [12], dflt: 0 },
    { y: 120, name: t('Cohort', 'Cohorte'), note: t('the start of the yearly cohort', 'el inicio de la cohorte anual'), refs: [14], dflt: 3 },
    { y: 194, name: t('Variable horizon', 'Horizonte variable'), note: t('quarterly dates in the year before default', 'fechas trimestrales en el año previo al incumplimiento'), refs: [12, 9, 6, 3], dflt: 0 },
  ];
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('Three timelines for one defaulted facility: a fixed horizon reads the balance and the limit once, twelve months before default; a cohort reads them at the start of the yearly cohort; a variable horizon reads them at four quarterly dates', 'Tres líneas de tiempo para una línea en incumplimiento: un horizonte fijo lee el saldo y el límite una vez, doce meses antes del incumplimiento; una cohorte los lee al inicio de la cohorte anual; un horizonte variable los lee en cuatro fechas trimestrales')}>
      {rows.map((r) => (
        <g key={r.name}>
          <text className="dg-box-title" x={8} y={r.y - 14}>{r.name}</text>
          <line className="dg-axis" x1={110} y1={r.y} x2={470} y2={r.y} />
          {r.refs.map((m) => (
            <circle key={m} className="dg-node" cx={xs(m + r.dflt)} cy={r.y} r={6} />
          ))}
          <line className="dg-asymptote" x1={xs(r.dflt)} y1={r.y - 16} x2={xs(r.dflt)} y2={r.y + 16} />
          <text className="dg-edge-label" x={xs(r.dflt)} y={r.y - 20} textAnchor="end">{t('default', 'incumplimiento')}</text>
          <text className="dg-note" x={110} y={r.y + 32} textAnchor="start">{r.note}</text>
        </g>
      ))}
      <text className="dg-edge-label" x={xs(12)} y={H - 36} textAnchor="middle">{t('reference date t_r: drawn E and limit L are read', 'fecha de referencia t_r: se leen el usado E y el límite L')}</text>
      <text className="dg-note" x={W - 8} y={H - 8} textAnchor="end">{t('Illustrative schematic, not a result', 'Esquema ilustrativo, no un resultado')}</text>
    </svg>
  );
}

function LgdPart() {
  return (
    <>
      <P
        en={<>The realised loss of a defaulted exposure is its economic loss over the exposure at default: the recoveries, net of direct and indirect costs and of any further drawings after default, each discounted to the default date, subtracted from one. The EU guidelines on PD and LGD estimation read the discount rate as a primary interbank rate at the default date plus a 5 percentage point add-on, and require the workouts still open to be treated explicitly, because leaving them out biases LGD downward and including them needs a projection of future recoveries <Cite id="ebagl201716" />. The paragraph numbers of that reading are unverified, so Contraste carries the rate convention as a parameter and prints which one a document used.</>}
        es={<>La pérdida realizada de una exposición en incumplimiento es su pérdida económica sobre la exposición al incumplimiento: las recuperaciones, netas de costos directos e indirectos y de nuevos giros posteriores al incumplimiento, cada una descontada a la fecha de incumplimiento, restadas de uno. Las directrices de la UE sobre estimación de PD y LGD leen la tasa de descuento como una tasa interbancaria primaria a la fecha de incumplimiento más un recargo de 5 puntos porcentuales, y exigen tratar de forma explícita las recuperaciones aún abiertas, porque omitirlas sesga la LGD a la baja e incluirlas requiere proyectar las recuperaciones futuras <Cite id="ebagl201716" />. Los números de párrafo de esa lectura no están verificados, así que Contraste lleva la convención de tasa como un parámetro e imprime cuál usó un documento.</>}
      />
      <Equation
        tex={String.raw`\mathrm{LGD}_i \;=\; 1 \;-\; \frac{\sum_{t>t_d}\bigl(R_{i,t} - C_{i,t} - A_{i,t}\bigr)\,(1+r_i)^{-(t-t_d)}}{\mathrm{EAD}_i}`}
        caption={<T en={<>The workout LGD (dossier 04, F.1): EAD_i the exposure at default, R_{'{i,t}'} the recoveries, C_{'{i,t}'} the direct and indirect costs and A_{'{i,t}'} the additional drawings after default, all at time t, t_d the default date and r_i the annual discount rate, so each flow is brought back to the default date. A value below 0 or above 1 is possible with fees and costs and is kept.</>} es={<>La LGD de recuperación (dossier 04, F.1): EAD_i la exposición al incumplimiento, R_{'{i,t}'} las recuperaciones, C_{'{i,t}'} los costos directos e indirectos y A_{'{i,t}'} los giros adicionales posteriores al incumplimiento, todos en el tiempo t, t_d la fecha de incumplimiento y r_i la tasa de descuento anual, de modo que cada flujo se trae a la fecha de incumplimiento. Un valor bajo 0 o sobre 1 es posible con comisiones y costos y se conserva.</>} />}
      />
      <P
        en={<>LGD is bounded in principle, can fall slightly below 0 or rise above 1 once fees and costs are counted, and is often bimodal with a mass near 0 (cures, full recovery) and another near 1 (no recovery): Tong, Mues and Thomas find that mortgage LGD contains extensive numbers of zeroes <Cite id="tong2013" />. It also moves with the default rate, so the loss is highest when many borrowers default together <Cite id="altman2005" />. The C08 distribution therefore draws the tenths of [0, 1] with the two masses counted, and the observations outside the range as bars of their own that are flagged and never clipped into it.</>}
        es={<>La LGD está acotada en principio, puede caer algo bajo 0 o subir sobre 1 una vez contados comisiones y costos, y suele ser bimodal, con una masa cerca de 0 (curas, recuperación total) y otra cerca de 1 (sin recuperación): Tong, Mues y Thomas encuentran que la LGD hipotecaria contiene un número extenso de ceros <Cite id="tong2013" />. También se mueve con la tasa de incumplimiento, de modo que la pérdida es mayor cuando muchos deudores incumplen a la vez <Cite id="altman2005" />. La distribución de C08 dibuja por eso las décimas de [0, 1] con las dos masas contadas, y las observaciones fuera del rango como barras propias que se marcan y nunca se recortan dentro de él.</>}
      />
      <Figure caption={t2('The shape that drives the model choice: tenths of the LGD between 0 and 1 with a mass at each end, and the observations below 0 and above 1 drawn apart in the warning colour, counted and flagged.', 'La forma que guía la elección del modelo: décimas de la LGD entre 0 y 1 con una masa en cada extremo, y las observaciones bajo 0 y sobre 1 dibujadas aparte en el color de aviso, contadas y marcadas.')}>
        <LgdFigure />
      </Figure>
      <P
        en={<>The ladder starts with ordinary least squares clipped to [0, 1] as the baseline. The fractional logit models the mean through a logistic function and its Bernoulli quasi-likelihood is consistent for any response in [0, 1], endpoints included <Cite id="papke1996" />. Beta regression is defined only strictly inside (0, 1), so the endpoints are moved in by a small shift epsilon, and Qi and Zhao find the beta and inverse Gaussian methods very sensitive to it, which is why C08 tries several <Cite id="ferrari2004" /> <Cite id="qizhao2011" />. The zero-or-one inflated beta <Cite id="ospina2012" />, the two-limit Tobit <Cite id="tobin1958" />, the two-stage hurdle that multiplies the probability of a loss by the severity given a loss <Cite id="leowmues2012" /> and a cure-rate decomposition complete the families; the attribution of the last one to a single source is unverified.</>}
        es={<>La escalera parte de mínimos cuadrados ordinarios recortados a [0, 1] como línea base. El logit fraccional modela la media con una función logística y su cuasi-verosimilitud de Bernoulli es consistente para toda respuesta en [0, 1], extremos incluidos <Cite id="papke1996" />. La regresión beta se define solo estrictamente dentro de (0, 1), así que los extremos se mueven hacia adentro en un pequeño desplazamiento epsilon, y Qi y Zhao encuentran los métodos beta y gaussiano inverso muy sensibles a él, por lo que C08 prueba varios <Cite id="ferrari2004" /> <Cite id="qizhao2011" />. La beta inflada en cero o uno <Cite id="ospina2012" />, el Tobit de dos límites <Cite id="tobin1958" />, el modelo en dos etapas que multiplica la probabilidad de pérdida por la severidad dada una pérdida <Cite id="leowmues2012" /> y una descomposición por tasa de cura completan las familias; la atribución de esta última a una sola fuente no está verificada.</>}
      />
      <Equation
        tex={String.raw`\begin{aligned}\mathbb{E}[y\mid x] &= G(x^{\top}\beta), \qquad \ell_i = y_i\log G(x_i^{\top}\beta) + (1-y_i)\log\bigl(1 - G(x_i^{\top}\beta)\bigr)\\ \mathbb{E}[\mathrm{LGD}] &= \Pr(\text{loss}>0)\cdot\mathbb{E}[\mathrm{LGD}\mid \text{loss}>0]\end{aligned}`}
        caption={<T en={<>First line, the fractional response model (Papke and Wooldridge 1996): y the LGD in [0, 1], x the covariates, G the logistic function and the quasi-log-likelihood ℓ_i of observation i, which stays valid at y = 0 and y = 1. Second line, the two-stage model (Leow and Mues 2012): a logit for the probability that the loss is positive times the expected severity given a loss, which a second regression estimates.</>} es={<>Primera línea, el modelo de respuesta fraccional (Papke y Wooldridge 1996): y la LGD en [0, 1], x las covariables, G la función logística y la cuasi-log-verosimilitud ℓ_i de la observación i, que sigue válida en y = 0 e y = 1. Segunda línea, el modelo en dos etapas (Leow y Mues 2012): un logit para la probabilidad de que la pérdida sea positiva por la severidad esperada dada una pérdida, que estima una segunda regresión.</>} />}
      />
      <P
        en={<>The benchmark evidence is modest and Contraste says so. Loterman and coauthors compare 24 techniques on six real loss datasets and find average R squared between 4 % and 43 %, with non-linear techniques significantly better than linear ones <Cite id="loterman2012" />; Qi and Zhao find non-parametric methods better in and out of sample once over-fitting is controlled, and the fractional response model slightly ahead of least squares <Cite id="qizhao2011" />. Because the R squared is low everywhere, C08 judges a model also by calibration: the mean LGD realised against predicted by cohort and by bucket, not by the R squared alone. Macro covariates can enter the regression <Cite id="bellotti2012" />.</>}
        es={<>La evidencia de comparación es modesta y Contraste lo dice. Loterman y coautores comparan 24 técnicas sobre seis conjuntos reales de pérdidas y encuentran un R cuadrado promedio entre 4 % y 43 %, con técnicas no lineales significativamente mejores que las lineales <Cite id="loterman2012" />; Qi y Zhao encuentran métodos no paramétricos mejores dentro y fuera de muestra una vez controlado el sobreajuste, y el modelo de respuesta fraccional algo por delante de los mínimos cuadrados <Cite id="qizhao2011" />. Como el R cuadrado es bajo en todas partes, C08 juzga un modelo también por su calibración: la LGD media realizada contra la predicha por cohorte y por tramo, no solo por el R cuadrado. Las covariables macro pueden entrar en la regresión <Cite id="bellotti2012" />.</>}
      />
      <P
        en={<>Two regulatory ideas sit on top of the estimates. The downturn LGD is defined in the EU by the technical standard on the nature, severity and duration of a downturn and by the guidelines on LGD appropriate for an economic downturn, an addendum to the PD and LGD guidelines <Cite id="ebagl201903" />; the Basel II explanatory note explains why no supervisory mapping from long-run to downturn LGD was adopted, so banks estimate it themselves <Cite id="bcbs2005irb" />. C08 shows a cohort-based add-on over the downturn years of a supplied macro path and whether it covered the cohorts that lived the crisis; it is an illustration, not a regulatory estimate. The A-IRB floors of the final framework are 25 % unsecured and, for secured corporate loans, 0 % on financial collateral, 10 % on receivables, 10 % on real estate and 15 % on other physical collateral (<Ref>CRE32.16</Ref>); for retail, 5 % on mortgages, 50 % on revolving, 30 % on other unsecured and 0 %, 10 %, 10 % and 15 % by collateral when secured (<Ref>CRE32.58</Ref> to <Ref>CRE32.59</Ref>) <Cite id="cre32" />.</>}
        es={<>Dos ideas regulatorias se apoyan en las estimaciones. La LGD de recesión se define en la UE por la norma técnica sobre naturaleza, severidad y duración de una recesión y por las directrices sobre LGD apropiada para una recesión económica, un anexo de las directrices de PD y LGD <Cite id="ebagl201903" />; la nota explicativa de Basilea II explica por qué no se adoptó una función supervisora de paso de la LGD de largo plazo a la de recesión, de modo que los bancos la estiman por sí mismos <Cite id="bcbs2005irb" />. C08 muestra un ajuste por cohortes sobre los años de recesión de una trayectoria macro entregada y si cubrió a las cohortes que vivieron la crisis; es una ilustración, no una estimación regulatoria. Los pisos A-IRB del marco final son 25 % sin garantía y, en créditos corporativos con garantía, 0 % con garantía financiera, 10 % con cuentas por cobrar, 10 % con bienes raíces y 15 % con otra garantía física (<Ref>CRE32.16</Ref>); en minorista, 5 % en hipotecas, 50 % en revolventes, 30 % en otros sin garantía y 0 %, 10 %, 10 % y 15 % según la garantía cuando la hay (<Ref>CRE32.58</Ref> a <Ref>CRE32.59</Ref>) <Cite id="cre32" />.</>}
      />
      <Equation
        tex={String.raw`\mathrm{Floor} \;=\; \mathrm{LGD}_{U,\mathrm{floor}}\,\frac{E_U}{E\,(1+H_E)} \;+\; \mathrm{LGD}_{S,\mathrm{floor}}\,\frac{E_S}{E\,(1+H_E)}`}
        caption={<T en={<>The floor of a partially secured exposure (<Ref>CRE32.17</Ref>; dossier 01, A.5): E the exposure, H_E the haircut on it, E_S the part covered by collateral after haircuts (capped at E(1 + H_E)) and E_U the rest, with LGD_{'{U,floor}'} the floor of the unsecured part and LGD_{'{S,floor}'} that of the collateral class. An estimate below the floor is lifted to it; C08 reports how often the floor binds and the uplift it causes.</>} es={<>El piso de una exposición parcialmente garantizada (<Ref>CRE32.17</Ref>; dossier 01, A.5): E la exposición, H_E el descuento sobre ella, E_S la parte cubierta por garantía tras los descuentos (con tope en E(1 + H_E)) y E_U el resto, con LGD_{'{U,floor}'} el piso de la parte sin garantía y LGD_{'{S,floor}'} el de la clase de garantía. Una estimación bajo el piso se sube hasta él; C08 informa con qué frecuencia el piso se activa y el alza que causa.</>} />}
      />
    </>
  );
}

function EadPart() {
  return (
    <>
      <P
        en={<>With a reference date t_r before the default, a drawn amount E and a limit L, the EU convention defines the conversion factor on the undrawn amount: the share of the undrawn part that is drawn by the time of default. Qi, in the study of unsecured credit cards, calls that same ratio the loan equivalent, and uses CCF for the exposure at default as a share of the outstanding balance and EADF for it as a share of the credit line <Cite id="qi2009" />. The loan equivalent is undefined when the line is fully drawn and unstable when the undrawn amount is small, so Qi switches to the other ratios below an undrawn amount of USD 50; C09 carries that switch as a parameter and reports how many facilities it moved. Every page of Contraste states which convention it uses, and C09 uses the EU one.</>}
        es={<>Con una fecha de referencia t_r antes del incumplimiento, un monto utilizado E y un límite L, la convención de la UE define el factor de conversión sobre el monto no utilizado: la parte del tramo sin usar que se gira al momento del incumplimiento. Qi, en su estudio de tarjetas de crédito sin garantía, llama a esa misma razón el equivalente de crédito, y usa CCF para la exposición al incumplimiento como parte del saldo y EADF para ella como parte de la línea de crédito <Cite id="qi2009" />. El equivalente de crédito no está definido cuando la línea está totalmente usada y es inestable cuando el monto no utilizado es pequeño, de modo que Qi pasa a las otras razones bajo un monto no utilizado de USD 50; C09 lleva ese cambio como un parámetro e informa cuántas líneas movió. Cada página de Contraste declara qué convención usa, y C09 usa la de la UE.</>}
      />
      <Equation
        tex={String.raw`\mathrm{CCF}_{\mathrm{EU}} \equiv \mathrm{LEQ} = \frac{\mathrm{EAD} - E(t_r)}{L(t_r) - E(t_r)}, \qquad \mathrm{EAD} = E(t_r) + \mathrm{CCF}\,\bigl(L(t_r) - E(t_r)\bigr)`}
        caption={<T en={<>The CCF on the undrawn amount (dossier 04, G.1): E(t_r) the drawn amount and L(t_r) the limit at the reference date t_r, EAD the exposure at default. In the US terms of Qi (2009) the same ratio is the LEQ, while that paper's CCF is EAD over E(t_r) and its EADF is EAD over L(t_r). The ratio is undefined when L(t_r) = E(t_r).</>} es={<>El CCF sobre el monto no utilizado (dossier 04, G.1): E(t_r) el monto utilizado y L(t_r) el límite en la fecha de referencia t_r, EAD la exposición al incumplimiento. En los términos estadounidenses de Qi (2009) la misma razón es el LEQ, mientras que el CCF de ese artículo es EAD sobre E(t_r) y su EADF es EAD sobre L(t_r). La razón no está definida cuando L(t_r) = E(t_r).</>} />}
      />
      <P
        en={<>The reference date is a model choice. A fixed horizon reads the balance and the limit twelve months before default; the cohort approach reads them at the start of a calendar cohort, for instance a year; the variable horizon reads several dates in the year before default <Cite id="moral2006" />. The detail of these three designs comes from a summary of the chapter and is unverified. Because the generator of C09 draws every balance with one known CCF, each design can be judged against the truth, and the acceleration levels 0 to 5 make utilisation rise ever more steeply before default, the effect Qi calls the race to default, where borrowers draw down while lenders cut lines.</>}
        es={<>La fecha de referencia es una elección del modelo. Un horizonte fijo lee el saldo y el límite doce meses antes del incumplimiento; el enfoque de cohorte los lee al inicio de una cohorte calendario, por ejemplo un año; el horizonte variable lee varias fechas del año previo al incumplimiento <Cite id="moral2006" />. El detalle de estos tres diseños proviene de un resumen del capítulo y no está verificado. Como el generador de C09 simula cada saldo con un solo CCF conocido, cada diseño se puede juzgar contra la verdad, y los niveles de aceleración 0 a 5 hacen subir la utilización con fuerza creciente antes del incumplimiento, el efecto que Qi llama la carrera hacia el incumplimiento, donde los deudores giran mientras los prestamistas recortan líneas.</>}
      />
      <Figure caption={t2('Three ways to choose the date at which the drawn amount and the limit are read for one defaulted facility: one date a year before, the start of the yearly cohort, or four quarterly dates; the design is part of the model and must be justified.', 'Tres maneras de elegir la fecha en que se leen el monto utilizado y el límite de una línea en incumplimiento: una fecha un año antes, el inicio de la cohorte anual, o cuatro fechas trimestrales; el diseño es parte del modelo y debe justificarse.')}>
        <DesignsFigure />
      </Figure>
      <P
        en={<>The CCF is negative when the balance falls between the reference date and the default, through repayments or cuts of the limit, and exceeds one when the balance goes above the original limit through overlimit, capitalised interest and fees or limit increases. Leow and Crook, with UK card data, see the balance-to-limit ratio peak at one at default and a sizeable share of borrowers defaulting on either side of their limit, and they model the balance directly, with a repeated-events survival model for the overlimit and random-effects models for balance and limit, reaching an R squared of 0.49 over the life of the loan and 0.55 at default <Cite id="leowcrook2013" />. The usual treatments censor, or floor at 0 and cap at 1, which biases the EAD, or model on a bounded scale; C09 sets each against the known CCF and keeps the values outside [0, 1] flagged and counted.</>}
        es={<>El CCF es negativo cuando el saldo baja entre la fecha de referencia y el incumplimiento, por pagos o recortes del límite, y supera uno cuando el saldo pasa del límite original por sobregiro, intereses y comisiones capitalizados o aumentos de límite. Leow y Crook, con datos de tarjetas del Reino Unido, ven que la razón saldo a límite alcanza su máximo en uno al incumplir y que una parte considerable de los deudores incumple a ambos lados de su límite, y modelan el saldo directamente, con un modelo de supervivencia de eventos repetidos para el sobregiro y modelos de efectos aleatorios para saldo y límite, con un R cuadrado de 0,49 en la vida del crédito y 0,55 al incumplir <Cite id="leowcrook2013" />. Los tratamientos habituales censuran, o fijan piso en 0 y tope en 1, lo que sesga la EAD, o modelan en una escala acotada; C09 contrasta cada uno con el CCF conocido y mantiene los valores fuera de [0, 1] marcados y contados.</>}
      />
      <Equation
        tex={String.raw`\mathrm{EAD}_{\mathrm{floor}} \;=\; E \;+\; 0.5\cdot \mathrm{Off}^{\mathrm{SA}}, \qquad \mathrm{CCF}^{\mathrm{SA}} \in \{100\%,\ 50\%,\ 40\%,\ 20\%,\ 10\%\}`}
        caption={<T en={<>The EAD floor of the final framework for own estimates (<Ref>CRE32.36</Ref> for corporates, <Ref>CRE32.64</Ref> for retail; dossier 01, A.5): E the on-balance amount and Off^SA the off-balance exposure measured with the standardised CCF of <Ref>CRE20.94</Ref> to <Ref>CRE20.101</Ref>, which is 100 % for direct credit substitutes, 50 % for note issuance facilities and transaction-related contingents, 40 % for commitments, 20 % for short-term self-liquidating trade letters of credit and 10 % for commitments cancellable unconditionally. Sovereigns are exempt. The F-IRB CCF equals the standardised one (<Ref>CRE32.33</Ref>), against 75 % for commitments under Basel II.</>} es={<>El piso de EAD del marco final para estimaciones propias (<Ref>CRE32.36</Ref> para corporativos, <Ref>CRE32.64</Ref> para minorista; dossier 01, A.5): E el monto en balance y Off^SA la exposición fuera de balance medida con el CCF estandarizado de <Ref>CRE20.94</Ref> a <Ref>CRE20.101</Ref>, que es 100 % para sustitutos directos de crédito, 50 % para facilidades de emisión de pagarés y contingentes ligados a transacciones, 40 % para compromisos, 20 % para cartas de crédito comerciales de corto plazo autoliquidables y 10 % para compromisos cancelables sin condiciones. Los soberanos están exentos. El CCF de F-IRB es el estandarizado (<Ref>CRE32.33</Ref>), frente a 75 % para compromisos bajo Basilea II.</>} />}
      />
      <P
        en={<>A model does not need the CCF at all. Tong and coauthors propose direct EAD models, a mixture with the zero-adjusted gamma distribution, and compare them with three CCF variants and a utilisation-change model on UK credit card data; the direct model is more accurate in calibration, and segmenting by usage and combining the direct and the CCF models improves it further <Cite id="tong2016" />. Jacobs studies the determinants of the loan equivalent, the CCF and the EADF for defaulted firms with revolving credit <Cite id="jacobs2010" />. Validation compares predicted with realised EAD in currency by utilisation band, not only the CCF; a CCF model is fitted on defaulted facilities only, so its sample is small and the reference-date design is a material choice. C09 reports the clipped observations of a direct model and the floors with the share where they bind.</>}
        es={<>Un modelo no necesita el CCF. Tong y coautores proponen modelos directos de EAD, una mezcla con la distribución gamma ajustada en cero, y los comparan con tres variantes de CCF y un modelo de cambio de utilización sobre datos de tarjetas del Reino Unido; el modelo directo es más preciso en calibración, y segmentar por uso y combinar los modelos directo y de CCF lo mejora aún más <Cite id="tong2016" />. Jacobs estudia los determinantes del equivalente de crédito, el CCF y el EADF en empresas en incumplimiento con crédito rotativo <Cite id="jacobs2010" />. La validación compara la EAD predicha con la realizada en moneda por tramo de utilización, no solo el CCF; un modelo de CCF se ajusta solo con líneas en incumplimiento, de modo que su muestra es pequeña y el diseño de fecha de referencia es una elección material. C09 informa las observaciones recortadas de un modelo directo y los pisos con la proporción donde se activan.</>}
      />
    </>
  );
}

/** The caption helper for the figures, outside a hook-bound component. */
function t2(en: string, es: string) {
  return <T en={en} es={es} />;
}

function Body() {
  const t = useT();
  return (
    <DocSection
      area="method"
      kind="classical"
      title={{ en: 'LGD and EAD: severity, conversion factors and the IRB floors', es: 'LGD y EAD: severidad, factores de conversión y los pisos IRB' }}
      refs={['ebagl201716', 'altman2005', 'tong2013', 'papke1996', 'ferrari2004', 'ospina2012', 'tobin1958', 'leowmues2012', 'loterman2012', 'qizhao2011', 'bellotti2012', 'ebagl201903', 'bcbs2005irb', 'cre32', 'cre20', 'qi2009', 'moral2006', 'leowcrook2013', 'tong2016', 'jacobs2010', 'ebaccf2025']}
    >
      <SubTabs
        ariaLabel={t('Parts of the topic', 'Partes del tema')}
        tabs={[
          { id: 'lgd', label: t('Loss given default', 'Pérdida dado el incumplimiento'), content: <LgdPart /> },
          { id: 'ead', label: t('Exposure at default', 'Exposición al incumplimiento'), content: <EadPart /> },
        ]}
      />
      <Callout variant="honest" title={t('What is exact, what is policy and what these views are not', 'Qué es exacto, qué es política y qué no son estas vistas')}>
        <T
          en={<>The workout formula, the CCF identity, the floors and the standardised CCFs are exact as transcribed from the sources; the discount-rate convention is a parameter, the paragraph numbers of the EU reading are unverified, and the order of the collateral classes of the retail secured floors is read as the corporate order, which the source does not confirm. The LGD of C08 is a charge-off proxy on the public SBA file, not a workout LGD: it is biased low through the approved amount in its denominator, it ignores recoveries after charge-off, and it can exceed one; the downturn add-on is an illustration, not a regulatory estimate. The three reference-date designs rest on a summary of their source, the attribution of the cure-rate decomposition is unverified, and whether the EBA has published final guidelines on CCF estimation after its 2025 consultation could not be confirmed <Cite id="ebaccf2025" />. C09 runs on a generator with a known CCF, so its results say how well an estimator recovers a truth and nothing about any bank, and the schematics above are illustrative.</>}
          es={<>La fórmula de recuperación, la identidad del CCF, los pisos y los CCF estandarizados son exactos tal como se transcribieron de las fuentes; la convención de tasa de descuento es un parámetro, los números de párrafo de la lectura de la UE no están verificados, y el orden de las clases de garantía de los pisos minoristas con garantía se lee como el orden corporativo, lo que la fuente no confirma. La LGD de C08 es un proxy de castigo sobre el archivo público de la SBA, no una LGD de recuperación: tiene sesgo a la baja por el monto aprobado en su denominador, ignora las recuperaciones posteriores al castigo y puede superar uno; el ajuste de recesión es una ilustración, no una estimación regulatoria. Los tres diseños de fecha de referencia se apoyan en un resumen de su fuente, la atribución de la descomposición por tasa de cura no está verificada, y no se pudo confirmar si la EBA publicó directrices finales sobre la estimación de CCF tras su consulta de 2025 <Cite id="ebaccf2025" />. C09 corre sobre un generador con un CCF conocido, así que sus resultados dicen qué tan bien un estimador recupera una verdad y nada sobre ningún banco, y los esquemas de arriba son ilustrativos.</>}
        />
      </Callout>
    </DocSection>
  );
}

export const methodologySection: MethodologySection = {
  id: 'lgd-ead',
  group: 'loss',
  order: 110,
  title: { en: 'LGD and EAD', es: 'LGD y EAD' },
  Body,
};
