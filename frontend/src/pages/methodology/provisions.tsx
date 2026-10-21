// The Methodology section on provisions (U5): lifetime PD, staging and the expected credit loss of IFRS 9, and the three
// regimes of cases C06 and C07 (IFRS 9, CMF Chapter B-1 in Chile, Banco de España Circular 4/2017 Annex 9 in Spain).
// Transcribed from research dossier 02 (IFRS 9 expected credit loss and provisioning, sections A.3, A.7, B.2 to B.5, C.1,
// C.6, C.7 and I.5) and dossier 03 (Chile CMF and Spain BdE, sections D.1 to D.6 and K.1 to K.3), where each paragraph of
// the standard, each table and each reference was read at its primary source on 2026-10-04. Every display equation
// carries a caption that defines its symbols. The registry mounts it as one tab of the models group; one file exports one
// section, so the family is one topic with one honest callout, one part per question.
import { Callout, Cite, DocSection, Equation, Figure } from '@fasl-work/caos-app-shell';
import { P, Ref, T, useT } from '../../content/bi';
import type { MethodologySection } from '../methodologyRegistry';

const W = 480;
const H = 262;

function Box({ x, y, w, h, title, sub, tone }: { x: number; y: number; w: number; h: number; title: string; sub: string; tone?: 'accent' | 'good' }) {
  return (
    <g>
      <rect className={`dg-box${tone ? ` ${tone}` : ''}`} x={x} y={y} width={w} height={h} rx={6} />
      <text className={`dg-box-title${tone === 'accent' ? ' accent' : ''}`} x={x + w / 2} y={y + h / 2 - 2} textAnchor="middle">{title}</text>
      <text className="dg-box-sub" x={x + w / 2} y={y + h / 2 + 13} textAnchor="middle">{sub}</text>
    </g>
  );
}

/** The three regimes on one portfolio: where each reads its provision, and the stage each category maps to. */
function RegimesFigure() {
  const t = useT();
  const rows = [
    { y: 14, name: t('CMF B-1', 'CMF B-1'), role: [t('statutory,', 'estatutaria,'), t('Chilean loans', 'créditos en Chile')] },
    { y: 96, name: t('IFRS 9', 'IFRS 9'), role: [t('comparison', 'medida de'), t('measure', 'comparación')] },
    { y: 178, name: t('BdE Annex 9', 'Anejo 9 BdE'), role: [t('Spanish', 'PGC'), t('GAAP', 'español')] },
  ];
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('The three regimes on one portfolio: the CMF B-1 group and individual assessment, the IFRS 9 stages and the Banco de España categories mapped to them', 'Los tres regímenes sobre una cartera: la evaluación grupal e individual de CMF B-1, las etapas de IFRS 9 y las categorías del Banco de España asignadas a ellas')}>
      {rows.map((r) => (
        <g key={r.name}>
          <text className="dg-box-title" x={8} y={r.y + 24}>{r.name}</text>
          <text className="dg-box-sub" x={8} y={r.y + 40}>{r.role[0]}</text>
          <text className="dg-box-sub" x={8} y={r.y + 53}>{r.role[1]}</text>
        </g>
      ))}
      <Box x={124} y={14} w={200} h={60} title={t('Group: PE = PI x PDI', 'Grupal: PE = PI x PDI')} sub={t('max(standard, internal)', 'el mayor: estándar o interno')} />
      <Box x={336} y={14} w={136} h={60} title={t('Individual', 'Individual')} sub="A1-A6, B1-B4, C1-C6" />
      <Box x={124} y={96} w={108} h={60} tone="accent" title={t('Stage 1', 'Etapa 1')} sub={t('12-month ECL', 'PCE a 12 meses')} />
      <Box x={244} y={96} w={108} h={60} tone="accent" title={t('Stage 2', 'Etapa 2')} sub={t('lifetime ECL', 'PCE de vida')} />
      <Box x={364} y={96} w={108} h={60} tone="accent" title={t('Stage 3', 'Etapa 3')} sub={t('credit-impaired', 'con deterioro')} />
      <Box x={124} y={178} w={108} h={60} tone="good" title={t('Normal', 'Normal')} sub={t('= Stage 1', '= Etapa 1')} />
      <Box x={244} y={178} w={108} h={60} tone="good" title={t('Special watch', 'Vigilancia')} sub={t('= Stage 2', '= Etapa 2')} />
      <Box x={364} y={178} w={108} h={60} tone="good" title={t('Doubtful', 'Dudoso')} sub={t('= Stage 3', '= Etapa 3')} />
      {[178, 298, 418].map((x) => (
        <line key={x} className="dg-edge" x1={x} y1={156} x2={x} y2={178} />
      ))}
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('Illustrative schematic, not a result', 'Esquema ilustrativo, no un resultado')}</text>
    </svg>
  );
}

function Body() {
  const t = useT();
  return (
    <DocSection
      area="method"
      kind="classical"
      title={{ en: 'Provisions: lifetime PD, staging, ECL and three regimes', es: 'Provisiones: PD de vida, etapas, PCE y tres regímenes' }}
      refs={['ifrs9', 'gppc2016', 'botha2025', 'finegray1999', 'gordy2003', 'vasicek2002', 'bcbs2005irb', 'perederiy2015', 'bcbsd350', 'ebagl201706', 'eba2021ifrs9', 'eba2023ifrs9', 'ecb2024overlays', 'abadsuarez2017', 'cmfcncb', 'cmfinforme2019', 'bdecirc42017', 'bdecirc62021']}
    >
      <h3 className="ct-sub">
        <T en="The lifetime PD and the expected loss" es="La PD de vida y la pérdida esperada" />
      </h3>
      <P
        en={<>IFRS 9 prescribes the measurement objective, not a formula: the expected credit loss is an unbiased, probability-weighted amount, determined by evaluating a range of possible outcomes, that reflects the time value of money and the reasonable and supportable information available about past events, current conditions and forecasts (paragraph <Ref>5.5.17</Ref>) <Cite id="ifrs9" />. The usual decomposition meets it as a sum of marginal losses <Cite id="gppc2016" />. With periods t = 1, ..., T after the reporting date, the survival function S(t), the conditional PD h(t) and the unconditional PD q(t) of period t obey the identities of discrete-time survival analysis <Cite id="botha2025" />. The GPPC calls h(t) the marginal probability of default; Contraste reserves marginal for q(t) and prints both names wherever either appears.</>}
        es={<>IFRS 9 prescribe el objetivo de medición, no una fórmula: la pérdida crediticia esperada es un monto insesgado y ponderado por probabilidad, determinado evaluando un rango de resultados posibles, que refleja el valor del dinero en el tiempo y la información razonable y sustentable disponible sobre hechos pasados, condiciones actuales y pronósticos (párrafo <Ref>5.5.17</Ref>) <Cite id="ifrs9" />. La descomposición habitual lo cumple como una suma de pérdidas marginales <Cite id="gppc2016" />. Con períodos t = 1, ..., T después de la fecha de reporte, la función de supervivencia S(t), la PD condicional h(t) y la PD incondicional q(t) del período t cumplen las identidades del análisis de supervivencia en tiempo discreto <Cite id="botha2025" />. El GPPC llama a h(t) la probabilidad marginal de incumplimiento; Contraste reserva marginal para q(t) e imprime ambos nombres donde aparece cualquiera.</>}
      />
      <Equation
        tex={String.raw`S(t) = \prod_{u=1}^{t}\bigl(1 - h(u)\bigr), \qquad q(t) = S(t-1)\,h(t), \qquad F(t) = \sum_{u=1}^{t} q(u), \qquad h(t) = \frac{q(t)}{S(t-1)}`}
        caption={<T en={<>The term-structure identities (Botha and Verster 2025): S(t) = P(τ &gt; t) is the survival function with S(0) = 1; h(t) the conditional PD of period t given survival to t - 1; q(t) its unconditional (marginal) PD; F(t) = 1 - S(t) the cumulative PD. The C06 term structures carry h, q and F on the same months, and F is strictly increasing.</>} es={<>Las identidades de la estructura de plazo (Botha y Verster 2025): S(t) = P(τ &gt; t) es la función de supervivencia con S(0) = 1; h(t) la PD condicional del período t dada la supervivencia hasta t - 1; q(t) su PD incondicional (marginal); F(t) = 1 - S(t) la PD acumulada. Las estructuras de plazo de C06 traen h, q y F en los mismos meses, y F es estrictamente creciente.</>} />}
      />
      <P
        en={<>A competing exit changes the arithmetic. With full prepayment or maturity before default, the cause-specific conditional probabilities of default and of prepayment give the probability of still being active, and the default increment of period t is that probability at the start of the period times the cause-specific default hazard; ignoring prepayment overstates the lifetime ECL, and the standard asks for the effect of expected prepayments (<Ref>B5.5.51</Ref>) <Cite id="finegray1999" />. The loss of period t is the default probability times the loss given default and the exposure at default, discounted from the assumed loss date to the reporting date at the effective interest rate (<Ref>B5.5.44</Ref>). Contraste discounts at the middle of the period and states it as a model setting, never as a requirement of the standard.</>}
        es={<>Una salida competidora cambia la aritmética. Con prepago total o vencimiento antes del incumplimiento, las probabilidades condicionales específicas de incumplimiento y de prepago dan la probabilidad de seguir activo, y el incremento de incumplimiento del período t es esa probabilidad al inicio del período por el riesgo de incumplimiento específico; ignorar el prepago sobreestima la PCE de vida, y la norma pide el efecto de los prepagos esperados (<Ref>B5.5.51</Ref>) <Cite id="finegray1999" />. La pérdida del período t es la probabilidad de incumplimiento por la pérdida dado el incumplimiento y la exposición al incumplimiento, descontada desde la fecha de pérdida supuesta hasta la fecha de reporte a la tasa de interés efectiva (<Ref>B5.5.44</Ref>). Contraste descuenta a mitad del período y lo declara como un parámetro del modelo, nunca como un requisito de la norma.</>}
      />
      <Equation
        tex={String.raw`\mathrm{ECL}_{i,s}(T) = \sum_{t=1}^{T} q^{D}_{i,s}(t)\; LGD_{i,s}(t)\; EAD_{i,s}(t)\; DF_i(t), \qquad DF_i(t) = (1 + r_i)^{-\delta(t)}`}
        caption={<T en={<>The expected loss of exposure i in scenario s over T periods (GPPC <Ref>2.1.1.2</Ref>; paragraphs <Ref>B5.5.28</Ref>, <Ref>B5.5.43</Ref> and <Ref>B5.5.44</Ref>): q^D the default increment of the period, LGD the loss as a share of the exposure at default, EAD the exposure at default, DF the discount factor at the effective interest rate r_i from the assumed loss date, δ(t) the years from the reporting date to it. T is 12 months for Stage 1 and the expected life for Stage 2.</>} es={<>La pérdida esperada de la exposición i en el escenario s a lo largo de T períodos (GPPC <Ref>2.1.1.2</Ref>; párrafos <Ref>B5.5.28</Ref>, <Ref>B5.5.43</Ref> y <Ref>B5.5.44</Ref>): q^D el incremento de incumplimiento del período, LGD la pérdida como fracción de la exposición al incumplimiento, EAD la exposición al incumplimiento, DF el factor de descuento a la tasa de interés efectiva r_i desde la fecha de pérdida supuesta, δ(t) los años desde la fecha de reporte hasta ella. T es 12 meses en la Etapa 1 y la vida esperada en la Etapa 2.</>} />}
      />

      <h3 className="ct-sub">
        <T en="Scenarios, the factor model and non-linearity" es="Escenarios, el modelo de factor y la no linealidad" />
      </h3>
      <P
        en={<>The through-the-cycle PD becomes a point-in-time PD with the one-factor model behind the Basel risk-weight function: the asset return is the square root of the correlation times a systematic factor z plus the square root of its complement times an idiosyncratic term, and the obligor defaults below the threshold of the through-the-cycle PD <Cite id="vasicek2002" /> <Cite id="gordy2003" />. The IRB formula evaluates it at a conservative quantile <Cite id="bcbs2005irb" />; IFRS 9 needs the probability-weighted value over forecast paths of z, without conservatism, and the satellite model projects z from the macroeconomic scenarios <Cite id="perederiy2015" />. The correlation of the capital formula is calibrated for capital, not for point-in-time dynamics, and is not reused blindly.</>}
        es={<>La PD a través del ciclo se convierte en una PD puntual con el modelo de un factor detrás de la función de ponderación de riesgo de Basilea: el retorno de activos es la raíz de la correlación por un factor sistemático z más la raíz de su complemento por un término idiosincrático, y el deudor incumple bajo el umbral de la PD a través del ciclo <Cite id="vasicek2002" /> <Cite id="gordy2003" />. La fórmula IRB lo evalúa en un cuantil conservador <Cite id="bcbs2005irb" />; IFRS 9 necesita el valor ponderado por probabilidad sobre las trayectorias pronosticadas de z, sin conservadurismo, y el modelo satélite proyecta z desde los escenarios macroeconómicos <Cite id="perederiy2015" />. La correlación de la fórmula de capital está calibrada para capital, no para la dinámica puntual, y no se reutiliza a ciegas.</>}
      />
      <Equation
        tex={String.raw`PD^{\mathrm{PIT}}(z) = \Phi\!\left(\frac{\Phi^{-1}(PD^{\mathrm{TTC}}) - \sqrt{\rho}\, z}{\sqrt{1-\rho}}\right), \qquad \mathrm{ECL} = \sum_{s=1}^{N_s} w_s\, \mathrm{ECL}_s, \quad w_s \ge 0, \; \sum_s w_s = 1, \; N_s \ge 2`}
        caption={<T en={<>The conditional PD given the factor (BCBS 2005; Vasicek 2002): Φ the standard normal distribution, ρ the asset correlation, z the systematic factor (negative is adverse). The weighted ECL (paragraphs <Ref>5.5.17(a)</Ref> and <Ref>B5.5.42</Ref>): w_s the probability weight of scenario s, ECL_s its ECL at full weight, and at least two outcomes when scenarios are used.</>} es={<>La PD condicional dado el factor (BCBS 2005; Vasicek 2002): Φ la distribución normal estándar, ρ la correlación de activos, z el factor sistemático (negativo es adverso). La PCE ponderada (párrafos <Ref>5.5.17(a)</Ref> y <Ref>B5.5.42</Ref>): w_s el peso de probabilidad del escenario s, ECL_s su PCE con peso completo, y al menos dos resultados cuando se usan escenarios.</>} />}
      />
      <P
        en={<>Because the ECL is a convex function of the factor in the adverse direction, the weighted ECL is not the ECL of the average scenario, and a base scenario read as the expectation is biased: it is the median, not the mean. The worked example of dossier 02, with illustrative parameters (PD through the cycle 2 %, correlation 12 %, factors +1, 0 and -2 at weights 25 %, 50 % and 25 %), gives conditional PDs of 0.526 %, 1.429 % and 7.342 %, a weighted PD of 2.681 % against 1.800 % at the weighted-average factor, and a 12-month loss rate of 1.07 % against 0.72 % with a loss given default of 40 %. The ECB criticises macro overlays that ignore it <Cite id="ecb2024overlays" />. The C06 non-linearity panel draws this curve.</>}
        es={<>Como la PCE es una función convexa del factor en la dirección adversa, la PCE ponderada no es la PCE del escenario promedio, y un escenario base leído como la esperanza está sesgado: es la mediana, no la media. El ejemplo resuelto del dossier 02, con parámetros ilustrativos (PD a través del ciclo 2 %, correlación 12 %, factores +1, 0 y -2 con pesos 25 %, 50 % y 25 %), da PD condicionales de 0,526 %, 1,429 % y 7,342 %, una PD ponderada de 2,681 % contra 1,800 % en el factor promedio ponderado, y una tasa de pérdida a 12 meses de 1,07 % contra 0,72 % con una pérdida dado el incumplimiento de 40 %. El BCE critica los ajustes macro que lo ignoran <Cite id="ecb2024overlays" />. El panel de no linealidad de C06 dibuja esta curva.</>}
      />

      <h3 className="ct-sub">
        <T en="Staging: the SICR rule" es="Etapas: la regla de SICR" />
      </h3>
      <P
        en={<>Each reporting date the stage compares the risk of default over the remaining life with the risk at initial recognition (paragraph <Ref>5.5.9</Ref>), on the same remaining window: the PD at origination for the window is the forward PD from the origination term structure, and the current one comes from the term structure at the reporting date, probability-weighted <Cite id="gppc2016" />. The change is relative, because the same absolute rise matters more at a low initial PD (<Ref>B5.5.9</Ref>). Contraste annualises both with the geometric form and rules: a multiplier that falls as the origination PD rises, an absolute floor against trivial transfers, and the threefold increase the EBA uses as a diagnostic <Cite id="eba2021ifrs9" /> <Cite id="eba2023ifrs9" />.</>}
        es={<>En cada fecha de reporte la etapa compara el riesgo de incumplimiento en la vida restante con el riesgo en el reconocimiento inicial (párrafo <Ref>5.5.9</Ref>), sobre la misma ventana restante: la PD de originación para la ventana es la PD a plazo de la estructura de originación, y la actual sale de la estructura de plazo a la fecha de reporte, ponderada por probabilidad <Cite id="gppc2016" />. El cambio es relativo, porque el mismo aumento absoluto pesa más con una PD inicial baja (<Ref>B5.5.9</Ref>). Contraste anualiza ambas con la forma geométrica y aplica reglas: un multiplicador que baja al subir la PD de originación, un piso absoluto contra traspasos triviales, y el triple que la EBA usa como diagnóstico <Cite id="eba2021ifrs9" /> <Cite id="eba2023ifrs9" />.</>}
      />
      <Equation
        tex={String.raw`\overline{PD} = 1 - (1 - PD)^{1/H}, \qquad \mathrm{SICR} = \mathbb{1}\Bigl[\tfrac{\overline{PD}^{\,\mathrm{rep}}}{\overline{PD}^{\,\mathrm{orig}}} \ge m\bigl(\overline{PD}^{\,\mathrm{orig}}\bigr) \wedge \overline{PD}^{\,\mathrm{rep}} - \overline{PD}^{\,\mathrm{orig}} \ge \delta\Bigr] \vee \mathbb{1}\Bigl[\tfrac{\overline{PD}^{\,\mathrm{rep}}}{\overline{PD}^{\,\mathrm{orig}}} \ge 3\Bigr]`}
        caption={<T en={<>The quantitative SICR indicator (dossier 02, B.5; EBA/Rep/2023/36): H the remaining life in years, the overlined PD the annualised PD at the reporting date (rep) and at origination (orig), m(·) the multiplier schedule, δ the absolute floor. Stage = 3 if the account is in default, else 2 if any trigger fires (this indicator, 30 days past due, forbearance, watch list, collective), else 1. The annualisation is Contraste's convention, not the EBA's.</>} es={<>El indicador cuantitativo de SICR (dossier 02, B.5; EBA/Rep/2023/36): H la vida restante en años, la PD con barra la PD anualizada a la fecha de reporte (rep) y en la originación (orig), m(·) la tabla de multiplicadores, δ el piso absoluto. Etapa = 3 si la cuenta está en incumplimiento, si no 2 si se activa algún gatillo (este indicador, 30 días de mora, refinanciación, lista de vigilancia, colectivo), si no 1. La anualización es convención de Contraste, no de la EBA.</>} />}
      />
      <P
        en={<>Only two thresholds are in the standard: the rebuttable presumption of a significant increase at 30 days past due, a backstop and not a primary indicator (<Ref>5.5.11</Ref>, <Ref>B5.5.19</Ref>), and the 90 days past due presumption of default (<Ref>B5.5.37</Ref>). The multipliers, the floor, the probation before a return to Stage 1 and the choice of the discounting convention are documented policy parameters of the model, and the C06 view marks which is which. The transfer from Stage 1 to Stage 2 is a cliff, the difference between the lifetime and the 12-month ECL, and it grows with the remaining life, which is the source of the procyclicality that Abad and Suarez analyse <Cite id="abadsuarez2017" />.</>}
        es={<>Solo dos umbrales están en la norma: la presunción refutable de aumento significativo a 30 días de mora, un respaldo y no un indicador primario (<Ref>5.5.11</Ref>, <Ref>B5.5.19</Ref>), y la presunción de incumplimiento a 90 días de mora (<Ref>B5.5.37</Ref>). Los multiplicadores, el piso, la prueba antes de volver a la Etapa 1 y la elección de la convención de descuento son parámetros de política documentados del modelo, y la vista de C06 marca cuál es cuál. El traspaso de la Etapa 1 a la Etapa 2 es un acantilado, la diferencia entre la PCE de vida y la de 12 meses, y crece con la vida restante, que es el origen de la prociclicidad que analizan Abad y Suarez <Cite id="abadsuarez2017" />.</>}
      />

      <h3 className="ct-sub">
        <T en="Chile and Spain: one portfolio under three regimes" es="Chile y España: una cartera bajo tres regímenes" />
      </h3>
      <P
        en={<>Chilean banks adopted IFRS 9 in the 2022 compendium except the impairment chapter for loans: Chapter A-2 states that section <Ref>5.5</Ref> does not apply to loans and contingent credits, whose criteria are in Chapters B-1 to B-3, an exception the CMF attributes mainly to prudential criteria <Cite id="cmfcncb" /> <Cite id="cmfinforme2019" />. The provision on loans is therefore the B-1 expected loss, not Stage 1, 2 and 3. Individual assessment places the debtor in Normal (A1 to A6), Substandard (B1 to B4) or Default (C1 to C6) with the PI, PDI and PE of the table, and the normal portfolio carries a minimum provision of 0.50 per cent.</>}
        es={<>Los bancos chilenos adoptaron IFRS 9 en el compendio de 2022 salvo el capítulo de deterioro para colocaciones: el Capítulo A-2 dice que la sección <Ref>5.5</Ref> no se aplica a las colocaciones ni a los créditos contingentes, cuyos criterios están en los Capítulos B-1 a B-3, una excepción que la CMF atribuye principalmente a criterios prudenciales <Cite id="cmfcncb" /> <Cite id="cmfinforme2019" />. La provisión sobre colocaciones es entonces la pérdida esperada de B-1, no las Etapas 1, 2 y 3. La evaluación individual ubica al deudor en Normal (A1 a A6), Subestándar (B1 a B4) o Incumplimiento (C1 a C6) con la PI, la PDI y la PE de la tabla, y la cartera normal lleva una provisión mínima de 0,50 por ciento.</>}
      />
      <Equation
        tex={String.raw`PE = PI \times PDI, \qquad \mathrm{Prov}_{\mathrm{group}} = \max\bigl(\mathrm{Prov}^{\mathrm{ME}},\ \mathrm{Prov}^{\mathrm{MI}}\bigr) \ \text{unless the internal method has the CMF no-objection}`}
        caption={<T en={<>CMF CNCB Chapter B-1: PE the provision factor, PI the probability of default and PDI the loss given default, each a share (the mortgage table gives PI 1.0916 per cent and PDI 0.0225 per cent for a loan under 40 per cent of the appraisal at no arrears); the group provision is the larger of the standard method ME and the internal method MI unless the CMF has not objected to the internal one, and the CMF notes that no institution uses internal methods for provisions, so in practice the larger of the two applies.</>} es={<>CMF CNCB Capítulo B-1: PE el factor de provisión, PI la probabilidad de incumplimiento y PDI la pérdida dado el incumplimiento, cada una una fracción (la tabla hipotecaria da PI 1,0916 por ciento y PDI 0,0225 por ciento para un crédito bajo 40 por ciento de la tasación sin mora); la provisión grupal es la mayor entre el método estándar ME y el interno MI salvo que la CMF no haya objetado el interno, y la CMF señala que ninguna institución usa métodos internos para provisiones, así que en la práctica rige la mayor de las dos.</>} />}
      />
      <P
        en={<>Spanish GAAP applies the IFRS 9 model. Circular 4/2017 of the Banco de España, Annex 9, sorts operations into normal risk with 12-month expected losses, normal risk under special watch with lifetime losses, doubtful risk for operations with a default event, and written-off risk, and Circular 6/2021 states the mapping to Stages 1, 2 and 3 for reporting <Cite id="bdecirc42017" /> <Cite id="bdecirc62021" />. Banks choose between internal methodologies and the alternative solutions, a percentage by risk segment and category applied to the amount not covered by effective guarantees, from the tables recalibrated for 30 June 2022. Contraste reads the alternative solutions; its coverage of a normal mortgage is 0.7 per cent and of one under special watch 18.0 per cent.</>}
        es={<>El PGC español aplica el modelo de IFRS 9. La Circular 4/2017 del Banco de España, Anejo 9, ordena las operaciones en riesgo normal con pérdidas esperadas a 12 meses, riesgo normal en vigilancia especial con pérdidas de vida, riesgo dudoso para operaciones con un evento de incumplimiento, y riesgo fallido, y la Circular 6/2021 declara la correspondencia con las Fases 1, 2 y 3 para el reporte <Cite id="bdecirc42017" /> <Cite id="bdecirc62021" />. Las entidades eligen entre metodologías internas y las soluciones alternativas, un porcentaje por segmento de riesgo y categoría aplicado al importe no cubierto con garantías eficaces, de las tablas recalibradas para el 30 de junio de 2022. Contraste lee las soluciones alternativas; su cobertura de una hipoteca normal es 0,7 por ciento y la de una en vigilancia especial 18,0 por ciento.</>}
      />
      <Equation
        tex={String.raw`\mathrm{Cobertura}_j = c_{s,k}\cdot \max\Bigl(0,\ EAD_j - \sum_{g} \mathrm{ValorAjustado}_{g}\Bigr)`}
        caption={<T en={<>The alternative solutions of Annex 9: c_{'{s,k}'} the percentage of the Banco de España for risk segment s and category or arrears bucket k, EAD_j the exposure and the sum the effective collateral g after the haircuts of the Annex, so the coverage applies to the uncovered amount only.</>} es={<>Las soluciones alternativas del Anejo 9: c_{'{s,k}'} el porcentaje del Banco de España para el segmento de riesgo s y la categoría o tramo de mora k, EAD_j la exposición y la suma las garantías eficaces g después de los descuentos del Anejo, de modo que la cobertura se aplica solo al importe no cubierto.</>} />}
      />
      <Figure caption={t('One portfolio, three ways to a provision: CMF B-1 reads group and individual categories, IFRS 9 reads stages, and the Banco de España reads categories that Circular 6/2021 maps to the stages.', 'Una cartera, tres caminos a una provisión: CMF B-1 lee categorías grupales e individuales, IFRS 9 lee etapas, y el Banco de España lee categorías que la Circular 6/2021 asigna a las etapas.')}>
        <RegimesFigure />
      </Figure>
      <P
        en={<>C07 compares the three on one synthetic portfolio and explains the gap as a bridge of exhaustive steps from the B-1 comparable total to the IFRS 9 total: the lifetime loss on Stage 2, the forward-looking scenarios, the discounting, the B-1 minimum top-up that IFRS 9 does not have, and the overlays. The B-1 additional provisions are counter-cyclical, set by board policy within a minimum and a maximum, and may never cover model deficiencies, so they sit outside both totals. An overlay is judgement on top of the model, kept as a line of its own with its rationale and review date <Cite id="ecb2024overlays" />, never merged into the model ECL or a segment. The IFRS 9 column is always the probability-weighted measure.</>}
        es={<>C07 compara los tres sobre una cartera sintética y explica la brecha como un puente de pasos exhaustivos desde el total comparable de B-1 hasta el total de IFRS 9: la pérdida de vida en la Etapa 2, los escenarios prospectivos, el descuento, el complemento del mínimo de B-1 que IFRS 9 no tiene, y los ajustes. Las provisiones adicionales de B-1 son contracíclicas, fijadas por política del directorio entre un mínimo y un máximo, y nunca pueden cubrir deficiencias de los modelos, así que quedan fuera de ambos totales. Un ajuste es juicio sobre el modelo, guardado como una línea propia con su justificación y fecha de revisión <Cite id="ecb2024overlays" />, nunca mezclado en la PCE del modelo ni en un segmento. La columna IFRS 9 es siempre la medida ponderada por probabilidad.</>}
      />
      <Callout variant="honest" title={t('What is exact, what is policy and what these views are not', 'Qué es exacto, qué es política y qué no son estas vistas')}>
        <T
          en={<>The identities, the discounting and the weighted sum are exact; the multipliers, the floor, the probation, the mid-period convention and the behavioural lives are policy parameters of the model, not requirements of IFRS 9, and only the 30 and 90 days past due presumptions are in the standard. The engine is not an IFRS 9 compliant or audited implementation for any entity and its outputs are not IFRS 7 disclosures. Chilean bank loan provisions follow CMF B-1, not IFRS 9, so the IFRS 9 column of C07 is a comparison. The portfolios are synthetic or public, no number describes any bank, and the schematic above is illustrative.</>}
          es={<>Las identidades, el descuento y la suma ponderada son exactos; los multiplicadores, el piso, la prueba, la convención de mitad de período y las vidas conductuales son parámetros de política del modelo, no requisitos de IFRS 9, y solo las presunciones de 30 y 90 días de mora están en la norma. El motor no es una implementación conforme ni auditada de IFRS 9 para ninguna entidad y sus salidas no son revelaciones de IFRS 7. Las provisiones de colocaciones bancarias chilenas siguen CMF B-1, no IFRS 9, así que la columna IFRS 9 de C07 es una comparación. Las carteras son sintéticas o públicas, ningún número describe a un banco, y el esquema de arriba es ilustrativo.</>}
        />
      </Callout>
    </DocSection>
  );
}

export const methodologySection: MethodologySection = {
  id: 'provisions',
  group: 'loss',
  order: 100,
  title: { en: 'Provisions', es: 'Provisiones' },
  Body,
};
