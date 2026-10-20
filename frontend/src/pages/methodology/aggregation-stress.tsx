// The Methodology section on capital aggregation and macro stress testing (U13): how the capital of four risks is added and what
// the dependence assumption hides, how it is allocated and validated, how a macro scenario reaches a bank's losses, what the
// supervisory exercises prescribe, and how the IAPE turns all of it into a capital target, a P2G proxy and a reverse stress
// (case C18). Five parts, as sub-tabs of one `method` section (ADR-0017 section 2.1): the aggregation ladder and the
// dependence band (dossier 05, G.1 to G.3; the U13 research addendum, F5); allocation, model risk and the validation tests
// (dossier 05, G.4 and G.5; dossier 06, B.12); the layers of a macro stress test and its satellites (dossier 05, H.1 to H.3;
// dossier 04, I.1); the scenarios and the supervisory exercises (dossier 05, H.2, H.4, H.6 and H.7; the addendum, F6 and F8);
// and the IAPE, the P2G proxy and the reverse stress (dossier 03, B.2 to B.5, G.4 and H.2; dossier 01, J.2 and J.4). Every
// constant and formula is transcribed from those files, each read at its primary source on 2026-10-04, 2026-10-18 or
// 2026-10-19; what the dossiers mark UNVERIFIED stays marked in the callout. Every display equation carries a caption that
// defines its symbols. The registry mounts the section as one tab of the `capital` group; one file exports one section, with
// one honest callout for the topic.
import { Callout, Cite, DocSection, Equation, Figure, SubTabs, formatNumber, useShellLang } from '@fasl-work/caos-app-shell';
import { P, T, useT } from '../../content/bi';
import type { MethodologySection } from '../methodologyRegistry';

const W = 480;
const H = 276;

/** The caption helper for the figures, outside a hook-bound component. */
function t2(en: string, es: string) {
  return <T en={en} es={es} />;
}

const r1 = (v: number) => Math.round(v * 10) / 10;

/** Figure A. The worst-case VaR bounds of eight Pareto(2) risks: the sum of the risks at perfect dependence is not the worst case. Published values (Table 4 of the paper, d = 8). */
const TABLE4: Array<{ alpha: string; lower: number; como: number; upper: number }> = [
  { alpha: '99 %', lower: 9.0, como: 72.0, upper: 141.67 },
  { alpha: '99.5 %', lower: 13.13, como: 105.14, upper: 203.66 },
  { alpha: '99.9 %', lower: 30.47, como: 244.98, upper: 465.29 },
];

function BoundsFigure() {
  const t = useT();
  const lang = useShellLang();
  const num = (v: number) => formatNumber(v, lang, { decimals: 2 });
  const lvl = (a: string) => (lang === 'es' ? a.replace('.', ',') : a);
  // value in [0, 500] to x in [140, 430]; row k of group g to y
  const x = (v: number) => 140 + (v / 500) * 290;
  const row = (g: number, k: number) => 10 + g * 84 + k * 22;
  const kinds: Array<{ key: 'lower' | 'como' | 'upper'; cls: string; en: string; es: string }> = [
    { key: 'lower', cls: 'dg-fill-accent', en: 'lower bound', es: 'cota inferior' },
    { key: 'como', cls: 'dg-fill-warn', en: 'comonotonic', es: 'comonótona' },
    { key: 'upper', cls: 'dg-bar', en: 'worst case', es: 'peor caso' },
  ];
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('Nine horizontal bars for the value at risk of the sum of eight Pareto risks with tail index 2: at 99 percent the lower bound is 9.00, the comonotonic sum 72.00 and the worst case 141.67; at 99.5 percent 13.13, 105.14 and 203.66; at 99.9 percent 30.47, 244.98 and 465.29', 'Nueve barras horizontales con el valor en riesgo de la suma de ocho riesgos de Pareto con índice de cola 2: a 99 por ciento la cota inferior es 9,00, la suma comonótona 72,00 y el peor caso 141,67; a 99,5 por ciento 13,13, 105,14 y 203,66; a 99,9 por ciento 30,47, 244,98 y 465,29')}>
      <line className="dg-axis" x1={x(0)} y1={6} x2={x(0)} y2={row(2, 2) + 20} />
      {TABLE4.map((g, gi) =>
        kinds.map((k, ki) => (
          <g key={`${g.alpha}-${k.key}`}>
            <text className="dg-edge-label" x={8} y={row(gi, ki) + 13} textAnchor="start">{`${lvl(g.alpha)}, ${t(k.en, k.es)}`}</text>
            <rect className={k.cls} x={x(0)} y={row(gi, ki)} width={Math.max(x(g[k.key]) - x(0), 2)} height={16} />
            <text className="dg-note" x={x(g[k.key]) + 4} y={row(gi, ki) + 13} textAnchor="start">{num(g[k.key])}</text>
          </g>
        )),
      )}
      <text className="dg-axis-label" x={x(250)} y={H - 20} textAnchor="middle">{t('value at risk of the sum of 8 risks', 'valor en riesgo de la suma de 8 riesgos')}</text>
      <text className="dg-note" x={W - 8} y={H - 4} textAnchor="end">{t('Published values, not a result of Contraste', 'Valores publicados, no un resultado de Contraste')}</text>
    </svg>
  );
}

/** Figure B. The Euler allocation as a shape: the stand-alone capital of each unit against what it contributes to the whole; the parts of the allocation add up to the whole and the stand-alone capitals do not. */
function EulerFigure() {
  const t = useT();
  const units = [
    { id: 'A', alone: 6, part: 4.4 },
    { id: 'B', alone: 8, part: 6.2 },
    { id: 'C', alone: 5, part: 3.9 },
    { id: 'D', alone: 3, part: 2.5 },
  ];
  const x = (v: number) => 60 + (v / 8.5) * 340;
  const row = (i: number) => 38 + i * 48;
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('Four units, each with a longer bar for its stand-alone capital and a shorter bar for its Euler contribution to the total, so that the contributions add up to the whole while the stand-alone capitals add up to more', 'Cuatro unidades, cada una con una barra más larga para su capital por sí sola y una más corta para su contribución de Euler al total, de modo que las contribuciones suman el todo mientras los capitales por sí solos suman más')}>
      <line className="dg-axis" x1={x(0)} y1={28} x2={x(0)} y2={row(3) + 40} />
      <rect className="dg-fill-warn" x={60} y={8} width={14} height={10} />
      <text className="dg-edge-label" x={80} y={17} textAnchor="start">{t('stand-alone', 'por sí sola')}</text>
      <rect className="dg-fill-accent" x={190} y={8} width={14} height={10} />
      <text className="dg-edge-label" x={210} y={17} textAnchor="start">{t('Euler contribution', 'contribución de Euler')}</text>
      {units.map((u, i) => (
        <g key={u.id}>
          <text className="dg-box-title" x={50} y={row(i) + 22} textAnchor="end">{u.id}</text>
          <rect className="dg-fill-warn" x={x(0)} y={row(i)} width={x(u.alone) - x(0)} height={16} />
          <rect className="dg-fill-accent" x={x(0)} y={row(i) + 20} width={x(u.part) - x(0)} height={16} />
        </g>
      ))}
      <text className="dg-note" x={W - 8} y={H - 22} textAnchor="end">{t('the contributions add up to the whole, the stand-alone bars do not', 'las contribuciones suman el todo, las barras por sí solas no')}</text>
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('Illustrative schematic, not a result', 'Esquema ilustrativo, no un resultado')}</text>
    </svg>
  );
}

/** Figure C. The three layers of a macro stress test and what a validator tests in each. */
function LayersFigure() {
  const t = useT();
  const boxes = [
    { x: 10, title: t('Scenario', 'Escenario'), a: t('paths of GDP,', 'trayectorias de PIB,'), b: t('jobs and rates', 'empleo y tasas'), test: t('plausible and severe', 'plausible y severo') },
    { x: 170, title: t('Satellites', 'Satélites'), a: t('path to a loss', 'trayectoria a una'), b: t('rate, per type', 'tasa de pérdida'), test: t('fit and back-cast', 'ajuste y back-cast') },
    { x: 330, title: t('Capital engine', 'Motor de capital'), a: t('losses and income', 'pérdidas e ingresos'), b: t('to CET1 ratios', 'a razones CET1'), test: t('reconciliation', 'conciliación') },
  ];
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('Three boxes in a row joined by arrows, scenario, satellites and capital engine, each with the test a validator applies below it: plausibility and severity, fit and back-cast, and reconciliation', 'Tres cajas en fila unidas por flechas, escenario, satélites y motor de capital, cada una con la prueba que aplica un validador debajo: plausibilidad y severidad, ajuste y back-cast, y conciliación')}>
      <defs>
        <marker id="u13-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 z" className="dg-arrowhead" />
        </marker>
      </defs>
      {boxes.map((b, i) => (
        <g key={b.title}>
          <rect className={i === 1 ? 'dg-box accent' : 'dg-box'} x={b.x} y={60} width={140} height={84} rx={6} />
          <text className="dg-box-title" x={b.x + 70} y={84} textAnchor="middle">{b.title}</text>
          <text className="dg-box-sub" x={b.x + 70} y={106} textAnchor="middle">{b.a}</text>
          <text className="dg-box-sub" x={b.x + 70} y={122} textAnchor="middle">{b.b}</text>
          <text className="dg-edge-label" x={b.x + 70} y={170} textAnchor="middle">{b.test}</text>
        </g>
      ))}
      <line className="dg-edge" x1={150} y1={102} x2={168} y2={102} markerEnd="url(#u13-arrow)" />
      <line className="dg-edge" x1={310} y1={102} x2={328} y2={102} markerEnd="url(#u13-arrow)" />
      <text className="dg-axis-label" x={W / 2} y={208} textAnchor="middle">{t('each layer is validated on its own', 'cada capa se valida por separado')}</text>
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('Illustrative schematic, not a result', 'Esquema ilustrativo, no un resultado')}</text>
    </svg>
  );
}

/** Figure D. The four quadrants of the NGFS scenarios, with the scenario C18 runs highlighted. */
function NgfsFigure() {
  const t = useT();
  const q = [
    { x: 14, y: 22, title: t('Orderly', 'Ordenado'), items: ['Low Demand', 'Net Zero 2050', 'Below 2C'], hot: -1 },
    { x: 246, y: 22, title: t('Disorderly', 'Desordenado'), items: ['Delayed transition'], hot: 0 },
    { x: 14, y: 140, title: t('Hot house world', 'Mundo invernadero'), items: ['NDCs', 'Current Policies'], hot: -1 },
    { x: 246, y: 140, title: t('Too little, too late', 'Muy poco, muy tarde'), items: ['Fragmented World'], hot: -1 },
  ];
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('The seven NGFS Phase V scenarios in four quadrants: orderly with Low Demand, Net Zero 2050 and Below 2C; disorderly with Delayed transition, the scenario the case runs; hot house world with NDCs and Current Policies; and too little, too late with Fragmented World', 'Los siete escenarios de NGFS Fase V en cuatro cuadrantes: ordenado con Low Demand, Net Zero 2050 y Below 2C; desordenado con Delayed transition, el escenario que corre el caso; mundo invernadero con NDCs y Current Policies; y muy poco, muy tarde con Fragmented World')}>
      {q.map((b) => (
        <g key={b.title}>
          <rect className={b.hot >= 0 ? 'dg-box accent' : 'dg-box'} x={b.x} y={b.y} width={220} height={108} rx={6} />
          <text className="dg-box-title" x={b.x + 12} y={b.y + 22} textAnchor="start">{b.title}</text>
          {b.items.map((it, i) => (
            <text key={it} className={i === b.hot ? 'dg-marker-label' : 'dg-box-sub'} x={b.x + 12} y={b.y + 46 + i * 18} textAnchor="start">{it}</text>
          ))}
        </g>
      ))}
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('The scenario in orange is the one the case runs', 'El escenario en naranja es el que corre el caso')}</text>
    </svg>
  );
}

/** Figure E. The layers of the internal target and the legal minimum stack as blocks (not to scale). */
function StackFigure() {
  const t = useT();
  const oi = [
    { w: 84, label: '8 %', cls: 'dg-fill-accent' },
    { w: 66, label: 'D-SIB', cls: 'dg-fill-accent' },
    { w: 66, label: 'P2', cls: 'dg-fill-warn' },
    { w: 66, label: 'CCoB', cls: 'dg-fill-accent' },
    { w: 66, label: 'CCyB', cls: 'dg-fill-accent' },
    { w: 66, label: 'd', cls: 'dg-fill-warn' },
  ];
  const legal = [
    { w: 84, label: '4.5 %' },
    { w: 66, label: '2.5 %' },
    { w: 66, label: 'CCyB' },
    { w: 66, label: 'D-SIB' },
    { w: 66, label: 'P2R' },
  ];
  const bar = (items: Array<{ w: number; label: string; cls?: string }>, y: number) => {
    let x = 30;
    return items.map((b) => {
      const at = x;
      x += b.w;
      return (
        <g key={`${y}-${b.label}`}>
          <rect className={b.cls ?? 'dg-fill-accent'} x={at} y={y} width={b.w} height={34} />
          <text className="dg-bar-label" x={at + b.w / 2} y={y + 21} textAnchor="middle">{b.label === '4.5 %' ? t('4.5 %', '4,5 %') : b.label === '2.5 %' ? t('2.5 %', '2,5 %') : b.label}</text>
        </g>
      );
    });
  };
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('Two stacked bars not drawn to scale: the internal target of effective equity made of the 8 percent minimum, the D-SIB charge, the Pillar 2 of the bank, the conservation and countercyclical buffers and the voluntary stress buffer d; and the legal minimum stack of the CET1 made of 4.5 percent, the 2.5 percent conservation buffer, the countercyclical buffer, the D-SIB charge and the Pillar 2 requirement', 'Dos barras apiladas sin escala: el objetivo interno de patrimonio efectivo formado por el mínimo de 8 por ciento, el cargo D-SIB, el Pilar 2 del banco, los colchones de conservación y contracíclico y el colchón voluntario de estrés d; y el mínimo legal apilado de CET1 formado por 4,5 por ciento, el colchón de conservación de 2,5 por ciento, el contracíclico, el cargo D-SIB y el requerimiento de Pilar 2')}>
      <text className="dg-box-title" x={30} y={28} textAnchor="start">{t('Internal target OI, on effective equity', 'Objetivo interno OI, sobre patrimonio efectivo')}</text>
      {bar(oi, 40)}
      <text className="dg-box-title" x={30} y={128} textAnchor="start">{t('Legal minimum stack, on CET1', 'Mínimo legal apilado, sobre CET1')}</text>
      {bar(legal, 140)}
      <text className="dg-edge-label" x={30} y={206} textAnchor="start">{t('orange blocks are estimates of the bank, not a requirement', 'los bloques naranjos son estimaciones del banco, no una exigencia')}</text>
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('Not to scale; a schematic, not a result', 'Sin escala; un esquema, no un resultado')}</text>
    </svg>
  );
}

/** Figure F. Reverse stress as geometry: the loss threshold touches the ellipse of equal density at the most plausible scenario. */
function ReverseFigure() {
  const t = useT();
  const cx = 150;
  const cy = 150;
  const a = 96;
  const b = 52;
  const theta = (-42 * Math.PI) / 180;
  const tx = cx + a * Math.cos(theta);
  const ty = cy + b * Math.sin(theta);
  // the tangent of the ellipse at the contact point
  const dx = -a * Math.sin(theta);
  const dy = b * Math.cos(theta);
  const norm = Math.hypot(dx, dy);
  const ux = dx / norm;
  const uy = dy / norm;
  const L = 150;
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('Two ellipses of equal density around the baseline and a straight line, the loss threshold, that touches the inner ellipse at one point, the most plausible scenario that breaks the bank; the area beyond the line is the set of scenarios that do', 'Dos elipses de igual densidad alrededor de la línea base y una recta, el umbral de pérdida, que toca la elipse interior en un punto, el escenario más plausible que quiebra al banco; la zona más allá de la recta es el conjunto de escenarios que lo hacen')}>
      <ellipse className="dg-curve-faint" cx={cx} cy={cy} rx={a * 1.45} ry={b * 1.45} />
      <ellipse className="dg-curve" cx={cx} cy={cy} rx={a} ry={b} />
      <line className="dg-asymptote" x1={r1(tx - ux * L)} y1={r1(ty - uy * L)} x2={r1(tx + ux * L)} y2={r1(ty + uy * L)} />
      <line className="dg-marker" x1={cx} y1={cy} x2={r1(tx)} y2={r1(ty)} />
      <circle className="dg-node" cx={cx} cy={cy} r={4} />
      <circle className="dg-node" cx={r1(tx)} cy={r1(ty)} r={5} />
      <text className="dg-edge-label" x={cx - 8} y={cy + 20} textAnchor="end">{t('baseline', 'línea base')}</text>
      <text className="dg-marker-label" x={r1(tx) - 8} y={r1(ty) - 12} textAnchor="end">x*</text>
      <text className="dg-edge-label" x={cx + a * 1.45 + 8} y={cy - 28} textAnchor="start">{t('equal density', 'igual densidad')}</text>
      <text className="dg-edge-label" x={W - 8} y={44} textAnchor="end">{t('loss at the threshold', 'pérdida en el umbral')}</text>
      <text className="dg-edge-label" x={W - 8} y={60} textAnchor="end">{t('and beyond: failure', 'y más allá: falla')}</text>
      <text className="dg-axis-label" x={cx} y={H - 24} textAnchor="middle">{t('distance in standard deviations', 'distancia en desviaciones estándar')}</text>
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('Illustrative schematic, not a result', 'Esquema ilustrativo, no un resultado')}</text>
    </svg>
  );
}

export function AggregationPart() {
  return (
    <>
      <P
        en={<>The capital of the risks of a bank is added in a ladder of rungs that admit less and less about the dependence between them. The simple sum, EC<sub>tot</sub> = &Sigma; EC<sub>k</sub>, assumes perfect dependence and, for the value at risk, is not even an upper bound in general. Variance-covariance (square-root) aggregation takes an inter-risk correlation matrix R: it is exact for elliptical losses with a common quantile scaling and an approximation otherwise. Copula aggregation draws U from a copula C, maps it through the marginal quantile functions, L<sub>k</sub> = F<sub>k</sub><sup>-1</sup>(U<sub>k</sub>), adds the losses and reads the VaR or the ES of the total; by Sklar&apos;s theorem every joint distribution is a copula of its marginals. The hybrid approximation of Rosenberg and Schuermann combines each risk&apos;s quantile with empirical correlations <Cite id="rosenberg2006" />. The IAPE of the CMF adds up the capital needed for each risk by simple addition <Cite id="ran2113" />, and the ECB does not in principle recognise inter-risk diversification in the supervisory review <Cite id="ecbicaap" />: the headline capital of C18 is therefore the simple sum, and every other rung is information for the validator, never a capital claim.</>}
        es={<>El capital de los riesgos de un banco se suma en una escalera de peldaños que admiten cada vez menos sobre la dependencia entre ellos. La suma simple, EC<sub>tot</sub> = &Sigma; EC<sub>k</sub>, supone dependencia perfecta y, para el valor en riesgo, ni siquiera es una cota superior en general. La agregación de varianza-covarianza (raíz cuadrada) toma una matriz de correlaciones entre riesgos R: es exacta para pérdidas elípticas con un escalamiento de cuantil común y una aproximación en otro caso. La agregación con cópulas sortea U de una cópula C, la lleva por las funciones cuantil marginales, L<sub>k</sub> = F<sub>k</sub><sup>-1</sup>(U<sub>k</sub>), suma las pérdidas y lee el VaR o el ES del total; por el teorema de Sklar toda distribución conjunta es una cópula de sus marginales. La aproximación híbrida de Rosenberg y Schuermann combina el cuantil de cada riesgo con correlaciones empíricas <Cite id="rosenberg2006" />. El IAPE de la CMF suma el capital necesario para cada riesgo por simple adición <Cite id="ran2113" />, y el BCE en principio no reconoce la diversificación entre riesgos en la revisión supervisora <Cite id="ecbicaap" />: el capital principal de C18 es por eso la suma simple, y todo otro peldaño es información para el validador, nunca una afirmación de capital.</>}
      />
      <P
        en={<>The copulas have standard definitions <Cite id="demartamcneil2005" />. The Gaussian copula, C(u) = &Phi;<sub>R</sub>(&Phi;<sup>-1</sup>(u<sub>1</sub>), &hellip;, &Phi;<sup>-1</sup>(u<sub>d</sub>)), has no tail dependence for a correlation below 1 in absolute value. The Student t copula with &nu; degrees of freedom has symmetric tail dependence, which grows as &nu; falls; the bivariate Clayton copula, C<sub>&theta;</sub>(u, v) = (u<sup>-&theta;</sup> + v<sup>-&theta;</sup> - 1)<sup>-1/&theta;</sup>, has lower tail dependence 2<sup>-1/&theta;</sup>. The textbook for these definitions is McNeil, Frey and Embrechts, Quantitative Risk Management (chapter number UNVERIFIED in the dossier). C18 runs the Gaussian copula and the t copula at the set of degrees of freedom 4, 8 and 30, a named convention of the case whose largest value approaches the Gaussian, over the Rosenberg and Schuermann correlations of market-credit 0.5 and market-operational and credit-operational 0.2, and again with market-credit raised to 0.8, the upper end of the published ranges. The vine copulas and the Clayton sampling are not built: they wait in the backlog.</>}
        es={<>Las cópulas tienen definiciones estándar <Cite id="demartamcneil2005" />. La cópula gaussiana, C(u) = &Phi;<sub>R</sub>(&Phi;<sup>-1</sup>(u<sub>1</sub>), &hellip;, &Phi;<sup>-1</sup>(u<sub>d</sub>)), no tiene dependencia de cola para una correlación menor que 1 en valor absoluto. La cópula t de Student con &nu; grados de libertad tiene dependencia de cola simétrica, que crece cuando &nu; baja; la cópula de Clayton bivariada, C<sub>&theta;</sub>(u, v) = (u<sup>-&theta;</sup> + v<sup>-&theta;</sup> - 1)<sup>-1/&theta;</sup>, tiene dependencia de cola inferior 2<sup>-1/&theta;</sup>. El texto de referencia para estas definiciones es McNeil, Frey y Embrechts, Quantitative Risk Management (el número de capítulo no está verificado en el dossier). C18 corre la cópula gaussiana y la cópula t con el conjunto de grados de libertad 4, 8 y 30, una convención con nombre del caso cuyo mayor valor se acerca a la gaussiana, sobre las correlaciones de Rosenberg y Schuermann de mercado-crédito 0,5 y mercado-operacional y crédito-operacional 0,2, y otra vez con mercado-crédito elevada a 0,8, el extremo superior de los rangos publicados. Las cópulas vine y el muestreo de Clayton no están construidos: esperan en el backlog.</>}
      />
      <Equation
        tex={String.raw`\mathrm{EC}_{\mathrm{tot}} = \sqrt{\mathrm{EC}^{\top} R\,\mathrm{EC}}, \qquad \lambda_{\nu}(\rho) = 2\,t_{\nu+1}\!\left(-\sqrt{\frac{(\nu+1)(1-\rho)}{1+\rho}}\right)`}
        caption={<T en={<>Two constructions of the ladder (dossier 05, G.1): the variance-covariance aggregate, with EC the vector of the stand-alone capital of each risk and R the inter-risk correlation matrix, checked to be symmetric, with a unit diagonal and positive semi-definite; and the symmetric tail dependence of the Student t copula, t<sub>&nu;+1</sub> the distribution function of a Student t variable with &nu; + 1 degrees of freedom and &rho; the correlation of the pair. With R the identity the first is the root of the sum of squares, and with R all ones it is the simple sum.</>} es={<>Dos construcciones de la escalera (dossier 05, G.1): el agregado de varianza-covarianza, con EC el vector del capital por sí solo de cada riesgo y R la matriz de correlaciones entre riesgos, verificada simétrica, con diagonal unitaria y semidefinida positiva; y la dependencia de cola simétrica de la cópula t de Student, t<sub>&nu;+1</sub> la función de distribución de una variable t de Student con &nu; + 1 grados de libertad y &rho; la correlación del par. Con R la identidad el primero es la raíz de la suma de cuadrados, y con R de unos es la suma simple.</>} />}
      />
      <P
        en={<>The evidence on how much the choice matters is mostly reassuring about the copula and sobering about the mix. In the study of Rosenberg and Schuermann, total risk given a risk type is more sensitive to differences in business mix or risk weights than to differences in inter-risk correlations; the choice between a normal and a Student t copula has a more modest effect; the approximation that uses empirical correlations and quantile estimates tracks the copula approach surprisingly well; and the additive approximation, which assumes no diversification benefit, typically overestimates risk by about 30 to 40 percent <Cite id="rosenberg2006" />. Their benchmark bank has risk weights of 4.1 percent market, 26.4 percent credit and 69.5 percent operational, a normal copula and correlations of 0.5 between market and credit and 0.2 between each of them and operational risk; the inter-risk correlation ranges they reproduce come from Kuritzkes, Schuermann and Weiner <Cite id="kuritzkes2003" />. The Joint Forum found aggregation models to be a work in progress on which supervisors generally do not rely <Cite id="jointforum2010" />. C18 shows the 30 to 40 percent overestimate and the case&apos;s own value beside it as a reference point and never as a gate.</>}
        es={<>La evidencia sobre cuánto importa la elección tranquiliza sobre la cópula y da una lección sobria sobre la mezcla. En el estudio de Rosenberg y Schuermann, el riesgo total dado un tipo de riesgo es más sensible a diferencias en la mezcla de negocios o en las ponderaciones de riesgo que a diferencias en las correlaciones entre riesgos; la elección entre una cópula normal y una t de Student tiene un efecto más modesto; la aproximación que usa correlaciones empíricas y estimaciones de cuantiles sigue sorprendentemente bien al enfoque con cópulas; y la aproximación aditiva, que supone ningún beneficio de diversificación, típicamente sobrestima el riesgo en cerca de 30 a 40 por ciento <Cite id="rosenberg2006" />. Su banco de referencia tiene ponderaciones de riesgo de 4,1 por ciento de mercado, 26,4 por ciento de crédito y 69,5 por ciento operacional, una cópula normal y correlaciones de 0,5 entre mercado y crédito y de 0,2 entre cada uno de ellos y el riesgo operacional; los rangos de correlación entre riesgos que reproducen vienen de Kuritzkes, Schuermann y Weiner <Cite id="kuritzkes2003" />. El Joint Forum encontró que los modelos de agregación son un trabajo en progreso en el que los supervisores en general no se apoyan <Cite id="jointforum2010" />. C18 muestra la sobrestimación de 30 a 40 por ciento y el valor propio del caso a su lado como un punto de referencia y nunca como un umbral.</>}
      />
      <P
        en={<>Linear correlation is a measure of dependence only within the elliptical families, and the pitfalls that follow are why C18 shows a band and not a number: marginals and correlation do not determine the joint distribution, not every correlation in [-1, 1] is attainable for given marginals, and the VaR of a sum is not largest when the correlation is largest <Cite id="embrechts2002" />. Because the VaR is not subadditive, the comonotonic sum is not a worst case. The sharp bounds of the VaR of a sum under known marginals and unknown dependence come from the rearrangement algorithm <Cite id="embrechts2013" />: the tail of each marginal is cut into N equal probability cells, the quantiles at the cell ends fill two matrices, each column is rearranged to be oppositely ordered to the sum of the others until the extreme row sum changes by less than a tolerance, and the two results bracket the bound. The authors state that a proof of convergence from every starting configuration remains open, which is why a random permutation starts the algorithm. In the figure the sum of eight Pareto risks at perfect dependence is far below the worst case.</>}
        es={<>La correlación lineal mide la dependencia solo dentro de las familias elípticas, y las trampas que siguen son la razón de que C18 muestre una banda y no un número: las marginales y la correlación no determinan la distribución conjunta, no toda correlación en [-1, 1] es alcanzable para marginales dadas, y el VaR de una suma no es el mayor cuando la correlación es la mayor <Cite id="embrechts2002" />. Como el VaR no es subaditivo, la suma comonótona no es un peor caso. Las cotas exactas del VaR de una suma con marginales conocidas y dependencia desconocida vienen del algoritmo de reordenamiento <Cite id="embrechts2013" />: la cola de cada marginal se corta en N celdas de igual probabilidad, los cuantiles en los extremos de las celdas llenan dos matrices, cada columna se reordena para quedar ordenada en sentido opuesto a la suma de las otras hasta que la suma extrema por fila cambia en menos que una tolerancia, y los dos resultados acotan el valor. Los autores señalan que una demostración de convergencia desde toda configuración inicial sigue abierta, por lo que una permutación aleatoria inicia el algoritmo. En la figura la suma de ocho riesgos de Pareto con dependencia perfecta queda muy por debajo del peor caso.</>}
      />
      <Figure caption={t2('The value at risk of the sum of eight Pareto risks with tail index 2, at three levels: the lower bound of the rearrangement algorithm (the start of its range), the comonotonic sum and the worst case. The worst case is about twice the comonotonic sum and the lower bound a small part of it. The values are the published ones (Table 4, d = 8).', 'El valor en riesgo de la suma de ocho riesgos de Pareto con índice de cola 2, en tres niveles: la cota inferior del algoritmo de reordenamiento (el inicio de su rango), la suma comonótona y el peor caso. El peor caso es cerca del doble de la suma comonótona y la cota inferior una parte pequeña de ella. Los valores son los publicados (Tabla 4, d = 8).')}>
        <BoundsFigure />
      </Figure>
    </>
  );
}

export function AllocationPart() {
  return (
    <>
      <P
        en={<>Capital is allocated back to the risks by the Euler principle <Cite id="tasche2008euler" />. For a portfolio X = &Sigma; X<sub>i</sub> and a risk measure &rho; that is positively homogeneous of degree one and differentiable, Euler&apos;s theorem gives &rho;(X) = &Sigma; u<sub>i</sub> &part;f/&part;u<sub>i</sub> at u = (1, &hellip;, 1) with f(u) = &rho;(&Sigma; u<sub>i</sub> X<sub>i</sub>), so the contributions &rho;(X<sub>i</sub> | X) = d&rho;(X + hX<sub>i</sub>)/dh at h = 0 add up to the total and are the only RORAC-compatible ones. The closed forms are the standard deviation contribution c cov[L<sub>i</sub>, L] over the square root of var[L], the VaR contribution E[L<sub>i</sub> | L = q<sub>&alpha;</sub>(L)] and the ES contribution E[L<sub>i</sub> | L &ge; q<sub>&alpha;</sub>(L)]. The VaR contributions conditioned on a single point are very noisy in simulation, so the expected shortfall contributions or kernel-smoothed ones are preferred; C18 allocates the expected shortfall of the aggregate. The diversification factor is DF = &rho;(L) / &Sigma; &rho;(L<sub>i</sub>), and the Euler diversification benefit of unit i is 1 - &rho;(L<sub>i</sub> | L) / &rho;(L<sub>i</sub>). Both are information: an allocation of an aggregate that is not the capital is not an allocation of capital.</>}
        es={<>El capital se asigna de vuelta a los riesgos con el principio de Euler <Cite id="tasche2008euler" />. Para una cartera X = &Sigma; X<sub>i</sub> y una medida de riesgo &rho; positivamente homogénea de grado uno y diferenciable, el teorema de Euler da &rho;(X) = &Sigma; u<sub>i</sub> &part;f/&part;u<sub>i</sub> en u = (1, &hellip;, 1) con f(u) = &rho;(&Sigma; u<sub>i</sub> X<sub>i</sub>), de modo que las contribuciones &rho;(X<sub>i</sub> | X) = d&rho;(X + hX<sub>i</sub>)/dh en h = 0 suman el total y son las únicas compatibles con RORAC. Las formas cerradas son la contribución de la desviación estándar c cov[L<sub>i</sub>, L] sobre la raíz de var[L], la contribución del VaR E[L<sub>i</sub> | L = q<sub>&alpha;</sub>(L)] y la contribución del ES E[L<sub>i</sub> | L &ge; q<sub>&alpha;</sub>(L)]. Las contribuciones del VaR condicionadas a un solo punto son muy ruidosas en simulación, así que se prefieren las del déficit esperado o las suavizadas con núcleo; C18 asigna el déficit esperado del agregado. El factor de diversificación es DF = &rho;(L) / &Sigma; &rho;(L<sub>i</sub>), y el beneficio de diversificación de Euler de la unidad i es 1 - &rho;(L<sub>i</sub> | L) / &rho;(L<sub>i</sub>). Ambos son información: una asignación de un agregado que no es el capital no es una asignación de capital.</>}
      />
      <Equation
        tex={String.raw`\mathrm{ES}_{\alpha}(L_i \mid L) = E\bigl[L_i \mid L \ge q_{\alpha}(L)\bigr], \quad \sum_i \mathrm{ES}_{\alpha}(L_i \mid L) = \mathrm{ES}_{\alpha}(L), \quad \mathrm{DF} = \frac{\rho(L)}{\sum_i \rho(L_i)}`}
        caption={<T en={<>The Euler allocation of the expected shortfall and the diversification factor (dossier 05, G.4; Tasche): L<sub>i</sub> the loss of risk i, L their sum, q<sub>&alpha;</sub> the quantile at level &alpha; and &rho; any positively homogeneous risk measure. The contributions add up to the aggregate exactly, which C18 tests with the relative error of the sum against a tolerance; DF below one is a diversification benefit and is reported, not enforced, because a VaR aggregate can exceed the simple sum.</>} es={<>La asignación de Euler del déficit esperado y el factor de diversificación (dossier 05, G.4; Tasche): L<sub>i</sub> la pérdida del riesgo i, L su suma, q<sub>&alpha;</sub> el cuantil al nivel &alpha; y &rho; cualquier medida de riesgo positivamente homogénea. Las contribuciones suman el agregado exactamente, lo que C18 prueba con el error relativo de la suma frente a una tolerancia; un DF menor que uno es un beneficio de diversificación y se reporta, no se impone, porque un agregado de VaR puede superar la suma simple.</>} />}
      />
      <P
        en={<>The model risk of the aggregation is measured over the set of models of the band. Barrieu and Scandolo define the ambiguity measure AM as the highest risk measure over the set divided by the reference one, minus 1, so that multiplying the reference by AM + 1 reaches the worst case, and the relative measure RM as the part of the range from the lowest to the highest that the reference leaves above it <Cite id="barrieuscandolo2015" />. Glasserman and Xu take a baseline law and bound the loss over likelihood ratios within a relative-entropy budget; the worst case reweights the baseline Monte Carlo sample, so it costs little beyond the baseline simulation <Cite id="glassermanxu2014" />. These are sensitivity information and never a regulatory capital figure, and C18 shows them beside the band for that reason.</>}
        es={<>El riesgo de modelo de la agregación se mide sobre el conjunto de modelos de la banda. Barrieu y Scandolo definen la medida de ambigüedad AM como la mayor medida de riesgo del conjunto dividida por la de referencia, menos 1, de modo que multiplicar la referencia por AM + 1 llega al peor caso, y la medida relativa RM como la parte del rango, del menor al mayor, que la referencia deja sobre sí <Cite id="barrieuscandolo2015" />. Glasserman y Xu toman una ley base y acotan la pérdida sobre razones de verosimilitud dentro de un presupuesto de entropía relativa; el peor caso repondera la muestra Monte Carlo base, así que cuesta poco más que la simulación base <Cite id="glassermanxu2014" />. Son información de sensibilidad y nunca una cifra de capital regulatorio, y C18 las muestra junto a la banda por esa razón.</>}
      />
      <Equation
        tex={String.raw`\mathrm{AM} = \frac{\overline{\rho}}{\rho(X_0)} - 1, \quad \mathrm{RM} = \frac{\overline{\rho} - \rho(X_0)}{\overline{\rho} - \underline{\rho}} \in [0,1], \quad m_{\theta}^{*} = \frac{e^{\theta V(X)}}{E\bigl[e^{\theta V(X)}\bigr]}`}
        caption={<T en={<>The model risk measures (dossier 06, B.12): &rho;(X<sub>0</sub>) the risk measure of the reference model, and the overlined and underlined &rho; the highest and the lowest over the set of alternative models; and the worst-case likelihood ratio m*<sub>&theta;</sub> of the baseline law for a loss function V, with &theta; &gt; 0 chosen so that the relative entropy of m equals its budget.</>} es={<>Las medidas de riesgo de modelo (dossier 06, B.12): &rho;(X<sub>0</sub>) la medida de riesgo del modelo de referencia, y la &rho; con barra superior e inferior la mayor y la menor sobre el conjunto de modelos alternativos; y la razón de verosimilitud del peor caso m*<sub>&theta;</sub> de la ley base para una función de pérdida V, con &theta; &gt; 0 elegido de modo que la entropía relativa de m iguale su presupuesto.</>} />}
      />
      <P
        en={<>The validation of an economic capital model has seven questions, and C18 runs each as a test with a light that is a convention of the case. Is the aggregate benchmarked against the simple sum and the variance-covariance formula? How much does the copula choice move it, Gaussian against t at several degrees of freedom? What is the worst-case bracket? What happens when the market-credit correlation is raised to 0.8? Do the Euler contributions add up to the total, and what is the sign of every diversification benefit? Are the horizon and the confidence level the same across the marginals, one year and 99.9 percent? Does the Monte Carlo agree with the variance-covariance anchor where the losses are elliptical? The capital of a risk is its VaR less its expected loss; when the mean of a heavy-tailed operational marginal is infinite the expected loss is undefined and the capital is the VaR alone, which the row says. A band row above the simple sum, or a capital that falls when a correlation rises, is a result the tests exist to flag, so C18 writes it and does not repair it.</>}
        es={<>La validación de un modelo de capital económico tiene siete preguntas, y C18 corre cada una como una prueba con una luz que es una convención del caso. ¿Se contrasta el agregado con la suma simple y la fórmula de varianza-covarianza? ¿Cuánto mueve la elección de cópula, gaussiana frente a t con varios grados de libertad? ¿Cuál es el rango del peor caso? ¿Qué pasa cuando la correlación mercado-crédito sube a 0,8? ¿Suman las contribuciones de Euler el total, y cuál es el signo de cada beneficio de diversificación? ¿Son iguales el horizonte y el nivel de confianza en todas las marginales, un año y 99,9 por ciento? ¿Coincide el Monte Carlo con el ancla de varianza-covarianza donde las pérdidas son elípticas? El capital de un riesgo es su VaR menos su pérdida esperada; cuando la media de una marginal operacional de cola pesada es infinita la pérdida esperada no está definida y el capital es el VaR solo, lo que la fila dice. Una fila de la banda sobre la suma simple, o un capital que baja cuando sube una correlación, es un resultado que las pruebas existen para marcar, así que C18 lo escribe y no lo repara.</>}
      />
      <Figure caption={t2('The Euler allocation as a shape, with illustrative numbers: the stand-alone capital of four units (orange) and what each contributes to the whole (blue). The contributions add up to the whole, which is smaller than the sum of the stand-alone capitals; the difference is the diversification, and it is information, not capital.', 'La asignación de Euler como forma, con números ilustrativos: el capital por sí solo de cuatro unidades (naranja) y lo que cada una aporta al todo (azul). Las contribuciones suman el todo, que es menor que la suma de los capitales por sí solos; la diferencia es la diversificación, y es información, no capital.')}>
        <EulerFigure />
      </Figure>
    </>
  );
}

export function SatellitePart() {
  return (
    <>
      <P
        en={<>A macro stress test has three layers: a scenario generator for macro-financial variables over two to three years, satellite models that map the scenario variables to risk parameters (PD, LGD, transition rates, volumes, margins, market shocks, operational losses), and a balance-sheet and capital engine that aggregates losses and revenues into capital ratios under a balance-sheet assumption, static or dynamic. Validation targets each layer separately: the plausibility and severity of the scenario, the fit and the out-of-sample performance of the satellites through past downturns, and the reconciliation of the engine. C18 draws the three layers, and its views follow the order of the questions: the capital the engine reaches, the path and the satellite that reach it, and the back-cast that tests the satellites.</>}
        es={<>Una prueba de estrés macro tiene tres capas: un generador de escenarios de variables macrofinancieras a dos o tres años, modelos satélite que llevan las variables del escenario a parámetros de riesgo (PD, LGD, tasas de transición, volúmenes, márgenes, choques de mercado, pérdidas operacionales), y un motor de balance y capital que agrega pérdidas e ingresos en razones de capital bajo un supuesto de balance, estático o dinámico. La validación apunta a cada capa por separado: la plausibilidad y severidad del escenario, el ajuste y el desempeño fuera de muestra de los satélites a través de caídas pasadas, y la conciliación del motor. C18 dibuja las tres capas, y sus vistas siguen el orden de las preguntas: el capital al que llega el motor, la trayectoria y el satélite que llegan a él, y el back-cast que prueba los satélites.</>}
      />
      <Equation
        tex={String.raw`g(\mathrm{DR}_{s,t}) = \alpha_s + \sum_{k=1}^{p}\phi_{s,k}\,g(\mathrm{DR}_{s,t-k}) + \sum_{l=0}^{q}\beta_{s,l}^{\top}X_{t-l} + \varepsilon_{s,t}, \qquad \Phi^{-1}(\mathrm{DR}_t) = \frac{\Phi^{-1}(\bar p) - \sqrt{\rho}\,Z_t}{\sqrt{1-\rho}}`}
        caption={<T en={<>The satellite and its Vasicek reading (dossier 04, I.1; a generic ARDL form, not a quoted equation): DR<sub>s,t</sub> the default or loss rate of segment s in quarter t, X<sub>t</sub> the macro variables, g the logit or the probit, &phi; and &beta; the coefficients, estimated by least squares with standard errors in an explicit sample window; and, under the Vasicek model, the probit of the rate is the latent credit cycle Z<sub>t</sub> scaled by the asset correlation &rho; around the through-the-cycle PD, p-bar, so regressing the probit on macro variables regresses the cycle on them. The scenario projection plugs the path of X<sub>t</sub> into the fitted equation and recovers DR<sub>s,t</sub>.</>} es={<>El satélite y su lectura de Vasicek (dossier 04, I.1; una forma ARDL genérica, no una ecuación citada): DR<sub>s,t</sub> la tasa de incumplimiento o de pérdida del segmento s en el trimestre t, X<sub>t</sub> las variables macro, g el logit o el probit, &phi; y &beta; los coeficientes, estimados por mínimos cuadrados con errores estándar en una ventana de muestra explícita; y, bajo el modelo de Vasicek, el probit de la tasa es el ciclo crediticio latente Z<sub>t</sub> escalado por la correlación de activos &rho; en torno a la PD a través del ciclo, p-barra, así que regresar el probit sobre variables macro regresa el ciclo sobre ellas. La proyección del escenario inserta la trayectoria de X<sub>t</sub> en la ecuación ajustada y recupera DR<sub>s,t</sub>.</>} />}
      />
      <P
        en={<>The Federal Reserve now publishes its supervisory model documentation, and its corporate credit model is the clearest public statement of a satellite structure <Cite id="fedcredit2026" />. The expected loss is EL<sub>i,t</sub> = PD<sub>i,t</sub> &times; LGD<sub>i,t</sub> &times; EAD<sub>i,t</sub> per facility and projection quarter; the PD comes from 16 least-squares regressions by four industry groups and rating groups from AAA-A to B of the quarterly vendor PD on the BBB spread and its four-quarter lag, with the CCC-C group in one pooled specification and an estimation sample from 2006 to 2023; the LGD is stressed through the BBB spread with the collateral, the lien position and the loan type; and the EAD uses a constant loan equivalent for undrawn commitments. Other families cover commercial real estate, first-lien mortgages, home equity, credit cards, auto and other retail, then the market, operational and PPNR models and the aggregation of balances, provisions, retained earnings and capital. The Board published the responses to the comments in the fall of 2026 <Cite id="fedmodelreview2026" />.</>}
        es={<>La Reserva Federal publica ahora la documentación de sus modelos supervisores, y su modelo de crédito corporativo es la declaración pública más clara de una estructura de satélite <Cite id="fedcredit2026" />. La pérdida esperada es EL<sub>i,t</sub> = PD<sub>i,t</sub> &times; LGD<sub>i,t</sub> &times; EAD<sub>i,t</sub> por facilidad y trimestre de proyección; la PD sale de 16 regresiones de mínimos cuadrados por cuatro grupos de industria y grupos de calificación de AAA-A a B de la PD trimestral de un proveedor sobre el spread BBB y su rezago de cuatro trimestres, con el grupo CCC-C en una especificación agrupada y una muestra de estimación de 2006 a 2023; la LGD se estresa mediante el spread BBB con la garantía, la posición del gravamen y el tipo de préstamo; y la EAD usa un equivalente de préstamo constante para los compromisos no utilizados. Otras familias cubren inmobiliario comercial, hipotecas de primer gravamen, crédito sobre el patrimonio de la vivienda, tarjetas, autos y otro minorista, luego los modelos de mercado, operacional y PPNR y la agregación de balances, provisiones, utilidades retenidas y capital. La Junta publicó las respuestas a los comentarios en el otoño de 2026 <Cite id="fedmodelreview2026" />.</>}
      />
      <P
        en={<>The satellites of C18 are the Federal Reserve form, one regression per Federal Reserve loan type on the Board&apos;s charge-off rate, fitted on data that end before 2020 and scored out of time on 2020 to 2025. Commercial and industrial loans, credit cards and other consumer loans start in 1985 and take the probit or logit link; the two real estate series start in 1991 because the Board&apos;s table has no earlier quarters, and they hold zero and negative quarters, net recoveries, that a probit or a logit cannot take, so they take an identity link on the signed rate. The regressors are agency series only. The classes of Banco Andino are weighted sums of those rates, a US-calibrated adaptation and not Chilean satellites, which the views label wherever they draw one. A regression of this kind fitted on one country&apos;s history is a statement about that country; the Chilean satellites are backlog. Nothing here is the credit risk model of a bank: it is the structure the supervisor publishes, run on a synthetic bank.</>}
        es={<>Los satélites de C18 son la forma de la Reserva Federal, una regresión por tipo de préstamo de la Reserva Federal sobre la tasa de castigo de la Junta, ajustada con datos que terminan antes de 2020 y evaluada fuera de tiempo en 2020 a 2025. Los préstamos comerciales e industriales, las tarjetas de crédito y los otros préstamos de consumo parten en 1985 y toman el enlace probit o logit; las dos series inmobiliarias parten en 1991 porque la tabla de la Junta no tiene trimestres anteriores, y traen trimestres en cero y negativos, recuperaciones netas, que un probit o un logit no pueden tomar, así que toman un enlace identidad sobre la tasa con signo. Los regresores son solo series de agencias. Las clases de Banco Andino son sumas ponderadas de esas tasas, una adaptación calibrada en EE. UU. y no satélites chilenos, lo que las vistas rotulan donde dibujan una. Una regresión de este tipo ajustada con la historia de un país es una afirmación sobre ese país; los satélites chilenos están en el backlog. Nada aquí es el modelo de riesgo de crédito de un banco: es la estructura que publica el supervisor, corrida sobre un banco sintético.</>}
      />
      <Figure caption={t2('The three layers of a macro stress test and the test a validator applies to each. The satellites, in blue, are the layer where the choice of link, the sample window and the out-of-time back-cast decide whether the projection can be trusted.', 'Las tres capas de una prueba de estrés macro y la prueba que un validador aplica a cada una. Los satélites, en azul, son la capa donde la elección del enlace, la ventana de la muestra y el back-cast fuera de tiempo deciden si la proyección es confiable.')}>
        <LayersFigure />
      </Figure>
    </>
  );
}

export function ScenarioPart() {
  return (
    <>
      <P
        en={<>Scenarios are generated by vector autoregressions and by quantile methods. A VAR, y<sub>t</sub> = c + &Sigma; A<sub>l</sub> y<sub>t-l</sub> + u<sub>t</sub>, with Minnesota-type priors that shrink the coefficients toward random walks <Cite id="litterman1986" />, forecasts well even with many variables when the shrinkage is appropriate <Cite id="banbura2010" />; a stress scenario is then a conditional forecast given a path for a subset of variables such as GDP and unemployment. A global VAR stacks country models whose foreign variables are trade-weighted averages of the others and solves them as one model <Cite id="pesaran2004" /> <Cite id="dees2007" />. Growth-at-risk first runs quantile regressions of average annualised GDP growth on a constant, current growth and a financial conditions index, then fits the Azzalini-Capitanio skewed t density to the estimated 5, 25, 75 and 95 percent quantiles by squared distance; its lower quantiles move strongly with financial conditions and its upper quantiles are stable, which makes it a severity calibrator <Cite id="adrian2019" />. A panel quantile satellite for bank outcomes is the dynamic extension <Cite id="covas2014" />. The engine implements the conditional VAR forecast and the growth-at-risk calibration with their own acceptance tests; no variant of C18 bakes them, and the Bayesian VAR and the panel quantile satellite wait.</>}
        es={<>Los escenarios se generan con vectores autorregresivos y con métodos de cuantiles. Un VAR, y<sub>t</sub> = c + &Sigma; A<sub>l</sub> y<sub>t-l</sub> + u<sub>t</sub>, con previas de tipo Minnesota que encogen los coeficientes hacia caminatas aleatorias <Cite id="litterman1986" />, pronostica bien incluso con muchas variables cuando el encogimiento es apropiado <Cite id="banbura2010" />; un escenario de estrés es entonces un pronóstico condicional dada una trayectoria para un subconjunto de variables como el PIB y el desempleo. Un VAR global apila modelos de países cuyas variables externas son promedios ponderados por comercio de los demás y los resuelve como un solo modelo <Cite id="pesaran2004" /> <Cite id="dees2007" />. El crecimiento en riesgo primero corre regresiones de cuantiles del crecimiento anualizado promedio del PIB sobre una constante, el crecimiento actual y un índice de condiciones financieras, luego ajusta la densidad t sesgada de Azzalini-Capitanio a los cuantiles estimados de 5, 25, 75 y 95 por ciento por distancia cuadrática; sus cuantiles inferiores se mueven mucho con las condiciones financieras y los superiores son estables, lo que lo hace un calibrador de severidad <Cite id="adrian2019" />. Un satélite de cuantiles en panel para resultados bancarios es la extensión dinámica <Cite id="covas2014" />. El motor implementa el pronóstico VAR condicional y la calibración del crecimiento en riesgo con sus propias pruebas de aceptación; ninguna variante de C18 los hornea, y el VAR bayesiano y el satélite de cuantiles en panel esperan.</>}
      />
      <P
        en={<>The EBA 2025 exercise fixes the rules a balance-sheet engine must respect <Cite id="eba2025note" />. The scenarios apply over three years, 2025 to 2027, from year-end 2024 figures (paragraph 24); the balance sheet is static, with maturing assets and liabilities replaced by similar instruments, no workout or cure of Stage 3 assets and no capital measure after the reference date (paragraph 33); the business mix and model stay the same, so revenues and costs follow zero growth and a stable mix (paragraph 34); and new Stage 3 exposures move into the stock of Stage 3 without cures, charge-offs or write-offs inside the horizon (paragraph 90). The exercise is a constrained bottom-up test with some top-down elements, and its results for 64 banks showed an aggregate CET1 depletion of 370 basis points in the adverse scenario <Cite id="eba2025results" />. C18 applies the same static rules by paragraph number to the synthetic bank over three years, transposes the shape of each published path onto the last observed value of Banco Andino, and refuses a path whose vintage postdates the observation date.</>}
        es={<>El ejercicio EBA 2025 fija las reglas que debe respetar un motor de balance <Cite id="eba2025note" />. Los escenarios se aplican a tres años, 2025 a 2027, desde cifras de fin de 2024 (párrafo 24); el balance es estático, con activos y pasivos que vencen reemplazados por instrumentos similares, sin recuperación ni cura de activos de Etapa 3 y sin medidas de capital después de la fecha de referencia (párrafo 33); la mezcla y el modelo de negocios se mantienen, de modo que ingresos y costos siguen crecimiento cero y una mezcla estable (párrafo 34); y las nuevas exposiciones de Etapa 3 pasan al stock de Etapa 3 sin curas, castigos ni bajas dentro del horizonte (párrafo 90). El ejercicio es una prueba ascendente restringida con algunos elementos descendentes, y sus resultados para 64 bancos mostraron una caída agregada del CET1 de 370 puntos base en el escenario adverso <Cite id="eba2025results" />. C18 aplica las mismas reglas estáticas por número de párrafo al banco sintético a tres años, transpone la forma de cada trayectoria publicada al último valor observado de Banco Andino, y rechaza una trayectoria cuya versión es posterior a la fecha de observación.</>}
      />
      <Equation
        tex={String.raw`\ell_t = b_t + d_t \quad\text{or}\quad \ell_t = b_t\,\Bigl(1 + \frac{d_t}{100}\Bigr), \qquad \ell_t^{\mathrm{bank}} = \ell_{0}^{\mathrm{bank}} + \bigl(\ell_t - \ell_{0}\bigr)`}
        caption={<T en={<>How a published path becomes a path for the bank (the U13 research addendum, F8, and the case&apos;s transposition rule): the NGFS scenario runs hold deviations d<sub>t</sub> from the Baseline run, so a level &ell;<sub>t</sub> is the baseline level b<sub>t</sub> plus the deviation for a rate, or the baseline times one plus the percent deviation for GDP; and the shape of the path, its change from the jump-off &ell;<sub>0</sub>, is carried onto the last observed value of the bank. The Federal Reserve and EBA paths are published as levels and are only transposed.</>} es={<>Cómo una trayectoria publicada se vuelve una trayectoria del banco (el adendum de investigación de U13, F8, y la regla de transposición del caso): las corridas de escenario de NGFS traen desviaciones d<sub>t</sub> de la corrida Baseline, así que un nivel &ell;<sub>t</sub> es el nivel base b<sub>t</sub> más la desviación para una tasa, o la base por uno más la desviación porcentual para el PIB; y la forma de la trayectoria, su cambio desde el punto de partida &ell;<sub>0</sub>, se lleva al último valor observado del banco. Las trayectorias de la Reserva Federal y de la EBA se publican como niveles y solo se transponen.</>} />}
      />
      <P
        en={<>The NGFS long-term scenarios of Phase V, published in November 2024, group seven scenarios into four quadrants <Cite id="ngfs5" /> <Cite id="ngfstech" />. Orderly are Low Demand, Net Zero 2050 and Below 2C; disorderly is Delayed transition, in which countries keep current policies until 2030 and the change of regime is unanticipated and disruptive; hot house world holds the Nationally Determined Contributions and Current Policies; and Fragmented World belongs to too little, too late. NGFS therefore classes exactly one scenario as disorderly, and the variant of C18 runs it, in the three years 2031 to 2033 in which its policy shock acts. The ECB climate stress test of 2022 found credit and market losses of around 70 billion EUR for 41 banks and said this substantially understates the risk, with data gaps, rudimentary models and about a third of exposures covered <Cite id="ecbclimate2022" />. A climate scenario is not a forecast. What a validator tests in a stress model is the same in every case: back-cast the satellites through 2008 to 2009 and 2020 with data that end before the episode and compare the predicted and realised peaks and their timing; check the sign and monotonicity of every sensitivity; check that the static rules are applied; compare the bottom-up result with a top-down challenger; and document the severity of each path against the global financial crisis.</>}
        es={<>Los escenarios de largo plazo de NGFS de la Fase V, publicados en noviembre de 2024, agrupan siete escenarios en cuatro cuadrantes <Cite id="ngfs5" /> <Cite id="ngfstech" />. Ordenados son Low Demand, Net Zero 2050 y Below 2C; desordenado es Delayed transition, en el que los países mantienen las políticas actuales hasta 2030 y el cambio de régimen es imprevisto y disruptivo; el mundo invernadero reúne las Contribuciones Determinadas a Nivel Nacional y Current Policies; y Fragmented World pertenece a muy poco, muy tarde. NGFS clasifica por tanto exactamente un escenario como desordenado, y la variante de C18 lo corre, en los tres años 2031 a 2033 en que actúa su choque de política. La prueba de estrés climática del BCE de 2022 encontró pérdidas de crédito y de mercado de unos 70 mil millones de EUR para 41 bancos y dijo que esto subestima sustancialmente el riesgo, con brechas de datos, modelos rudimentarios y cerca de un tercio de las exposiciones cubiertas <Cite id="ecbclimate2022" />. Un escenario climático no es un pronóstico. Lo que un validador prueba en un modelo de estrés es lo mismo en todo caso: retro-proyectar los satélites a través de 2008 a 2009 y 2020 con datos que terminan antes del episodio y comparar los máximos predichos y realizados y su desfase; revisar el signo y la monotonía de cada sensibilidad; revisar que se apliquen las reglas estáticas; comparar el resultado ascendente con un desafiante descendente; y documentar la severidad de cada trayectoria frente a la crisis financiera global.</>}
      />
      <Figure caption={t2('The four quadrants of the NGFS Phase V scenarios and the seven scenarios in them. Delayed transition, in orange, is the only one NGFS classes as disorderly and the one the NGFS variant of the case runs; Fragmented World is too little, too late and is not run.', 'Los cuatro cuadrantes de los escenarios de NGFS Fase V y los siete escenarios en ellos. Delayed transition, en naranja, es el único que NGFS clasifica como desordenado y el que corre la variante NGFS del caso; Fragmented World es muy poco, muy tarde y no se corre.')}>
        <NgfsFigure />
      </Figure>
    </>
  );
}

export function IapePart() {
  return (
    <>
      <P
        en={<>The IAPE is the self-assessment of effective equity that the CMF requires of Chilean banks <Cite id="ran2113" />. Its internal target OI, in terms of RWA, is at least the sum of the minimum of 8 percent and the D-SIB charge, the bank&apos;s own estimate of capital for risks outside Pillar 1, which must at least include the additional capital the CMF requires under article 66 quinquies, the conservation and countercyclical buffers, and a voluntary stress buffer d, sized so that the CET1 absorbs a severe stress scenario without breaching the legal minima and which may be zero; every component is set over a forward horizon of three years. The capital needed for each risk is added by simple addition, and the planning period of at least three years projects retained earnings, dividends and issues. Banks must project their capital needs to meet the OI under normal scenarios and at least the legal minimum under a stress scenario, in three projections, the base, the stress without mitigation actions and the stress with mitigation actions, and a deficit of effective equity with the remediation actions. Annex 3 summarises them in a table of rows by four columns: the share of RWA, the amount, the legal requirement and the internal measurement.</>}
        es={<>El IAPE es la autoevaluación de patrimonio efectivo que la CMF exige a los bancos chilenos <Cite id="ran2113" />. Su objetivo interno OI, en términos de APR, es al menos la suma del mínimo de 8 por ciento y el cargo D-SIB, la estimación propia del banco del capital para riesgos fuera del Pilar 1, que debe incluir a lo menos el capital adicional que la CMF exige por el artículo 66 quinquies, los colchones de conservación y contracíclico, y un colchón voluntario de estrés d, dimensionado para que el CET1 absorba un escenario de estrés severo sin quebrantar los mínimos legales y que puede ser nulo; todo componente se fija sobre un horizonte prospectivo de tres años. El capital necesario para cada riesgo se suma por simple adición, y el periodo de planificación de al menos tres años proyecta utilidades retenidas, dividendos y emisiones. Los bancos deben proyectar sus necesidades de capital para cumplir el OI en escenarios normales y al menos el mínimo legal en un escenario de tensión, en tres proyecciones, la base, la de tensión sin acciones de mitigación y la de tensión con acciones de mitigación, y un déficit de patrimonio efectivo con las acciones de remediación. El Anexo 3 las resume en una tabla de filas por cuatro columnas: la parte de los APR, el monto, la exigencia legal y la medición interna.</>}
      />
      <Equation
        tex={String.raw`\mathrm{OI} \ge \underbrace{8\% + c_{\mathrm{DSIB}}}_{\text{arts. 66, 66 quater}} + \underbrace{c_{\mathrm{P2,bank}}}_{\ge\, c_{66\,\mathrm{quinquies}}} + \underbrace{c_{\mathrm{CCoB}} + c_{\mathrm{CCyB}}}_{\text{arts. 66 bis, 66 ter}} + \underbrace{c_{d}}_{\text{voluntary}}, \qquad \frac{\mathrm{CET1}}{\mathrm{RWA}} \ge 4.5\% + 2.5\% + c_{\mathrm{CCyB}} + c_{\mathrm{DSIB}} + c_{\mathrm{P2}}^{\mathrm{CET1}}`}
        caption={<T en={<>The internal capital target and the legal CET1 stack (dossier 03, B.2 and G.4): every term a percentage of RWA net of required provisions; c<sub>DSIB</sub> between 0 and 1.5 percent; c<sub>P2,bank</sub> the bank&apos;s own estimate, at least the art. 66 quinquies requirement, which the CMF caps at 4 percent of RWA; c<sub>CCoB</sub> the 2.5 percent conservation buffer and c<sub>CCyB</sub> the countercyclical one, 0.5 or 1 percent; and c<sub>P2</sub><sup>CET1</sup> the CET1 share of Pillar 2, bank specific. In C18 the values of c<sub>P2,bank</sub> and c<sub>d</sub> are labelled assumptions of the case.</>} es={<>El objetivo interno de capital y el apilado legal de CET1 (dossier 03, B.2 y G.4): todo término un porcentaje de los APR netos de provisiones exigidas; c<sub>DSIB</sub> entre 0 y 1,5 por ciento; c<sub>P2,bank</sub> la estimación propia del banco, al menos la exigencia del art. 66 quinquies, que la CMF limita a 4 por ciento de los APR; c<sub>CCoB</sub> el colchón de conservación de 2,5 por ciento y c<sub>CCyB</sub> el contracíclico, 0,5 o 1 por ciento; y c<sub>P2</sub><sup>CET1</sup> la parte CET1 del Pilar 2, específica de cada banco. En C18 los valores de c<sub>P2,bank</sub> y c<sub>d</sub> están rotulados como supuestos del caso.</>} />}
      />
      <Figure caption={t2('The two stacks as blocks, not to scale: the internal target OI on effective equity, and the legal minimum stack on the CET1. The orange blocks, the Pillar 2 of the bank and the voluntary buffer d, are estimates of the bank; the other blocks are rules.', 'Los dos apilados como bloques, sin escala: el objetivo interno OI sobre patrimonio efectivo, y el mínimo legal apilado sobre el CET1. Los bloques naranjos, el Pilar 2 del banco y el colchón voluntario d, son estimaciones del banco; los otros bloques son reglas.')}>
        <StackFigure />
      </Figure>
      <P
        en={<>The P2G is the international name for component d <Cite id="cmfp2faq" />. The CMF calls it a consumable layer of capital that absorbs a severe stress scenario without breaching the legal minimum, which includes the P2R; it may suggest an amount in line with the ECB methodology, considering the fall of the capital ratios in the stress test, the risk profile and the supervisory judgement; it is not part of the 4 percent cap, is non-binding, is not disclosed by the CMF and should be made only of CET1. The measurement guidance uses severe scenarios, the maximum deterioration inside the three-year projection horizon, referenced to CET1 over RWA, and a dynamic balance sheet may reflect mitigation actions. The CMF calibration grid itself is not public, so C18 computes a Contraste approximation consistent with that guidance and labels it so wherever it appears: the largest fall of the CET1 ratio from the jump-off in any year of the severe scenario, less the usable buffers and the mitigation, floored at zero.</>}
        es={<>La P2G es el nombre internacional del componente d <Cite id="cmfp2faq" />. La CMF la llama una capa consumible de capital que absorbe un escenario de estrés severo sin quebrantar el mínimo legal, que incluye el P2R; puede sugerir un monto en línea con la metodología del BCE, considerando la caída de las razones de capital en la prueba de estrés, el perfil de riesgo y el juicio supervisor; no forma parte del tope de 4 por ciento, no es vinculante, no es divulgada por la CMF y debería constituirse solo con CET1. La guía de medición usa escenarios severos, el máximo deterioro dentro del horizonte de proyección de tres años, referido al CET1 sobre APR, y un balance dinámico puede reflejar acciones de mitigación. La grilla de calibración de la CMF no es pública, así que C18 calcula una aproximación de Contraste consistente con esa guía y la rotula así donde aparece: la mayor caída de la razón CET1 desde el punto de partida en cualquier año del escenario severo, menos los colchones usables y la mitigación, con piso en cero.</>}
      />
      <Equation
        tex={String.raw`\mathrm{P2G}_{\mathrm{bank}} \approx \max_{t\in\{1,2,3\}}\Bigl[\Bigl(\tfrac{\mathrm{CET1}}{\mathrm{RWA}}\Bigr)_{0} - \Bigl(\tfrac{\mathrm{CET1}}{\mathrm{RWA}}\Bigr)^{\mathrm{severe}}_{t}\Bigr] - \text{usable buffers and mitigation}`}
        caption={<T en={<>The P2G proxy (dossier 03, H.2): the CET1 ratio at the jump-off less the CET1 ratio in year t of the severe scenario, the maximum over the three years of the planning period, less the usable buffers and the mitigation. It is a Contraste approximation consistent with the CMF guidance, not the CMF calibration.</>} es={<>El proxy de la P2G (dossier 03, H.2): la razón CET1 en el punto de partida menos la razón CET1 en el año t del escenario severo, el máximo sobre los tres años del periodo de planificación, menos los colchones usables y la mitigación. Es una aproximación de Contraste consistente con la guía de la CMF, no la calibración de la CMF.</>} />}
      />
      <P
        en={<>A reverse stress test starts from a pre-defined outcome, the point at which the business model becomes unviable or the institution fails or is likely to fail, and explores the scenarios that might cause it; the EBA guidelines ask all institutions to perform it regularly and to use it to assess the severity of the ICAAP and ILAAP scenarios <Cite id="ebagl201804" />. A stress scenario approach should reach a conservatism comparable to the 99.9 percent economic capital concept <Cite id="ecbicaap" />, and the Basel principles ask for scenarios severe enough to threaten the viability of the bank <Cite id="bcbsd450" />. The formal statement used here is Contraste&apos;s and not regulatory text: given a loss model L over standardised risk factors z with density &phi;, the most plausible scenario that reaches the failure point maximises &phi;(z) subject to the loss reaching the threshold, which for Gaussian factors is the scenario of minimum Mahalanobis distance. C18 takes the failure point as the CET1 at the Chilean legal minimum stack at the end of three years, the factors as the standardised regressors of the satellites with their covariance of 1985 to 2019, and reports the distance, its chi-square tail probability as a plausibility, and the search from several starts. The empirical-likelihood method of Glasserman, Kang and Kang is not used: only its abstract was read <Cite id="glassermankang2015" />.</>}
        es={<>Una prueba de estrés inversa parte de un resultado predefinido, el punto en que el modelo de negocios se vuelve inviable o la institución quiebra o es probable que quiebre, y explora los escenarios que podrían causarlo; las directrices de la EBA piden a todas las instituciones hacerla regularmente y usarla para evaluar la severidad de los escenarios del ICAAP y del ILAAP <Cite id="ebagl201804" />. Un enfoque de escenarios de estrés debería alcanzar un conservadurismo comparable al concepto de capital económico de 99,9 por ciento <Cite id="ecbicaap" />, y los principios de Basilea piden escenarios lo bastante severos para amenazar la viabilidad del banco <Cite id="bcbsd450" />. El planteamiento formal que se usa aquí es de Contraste y no texto regulatorio: dada una pérdida L sobre factores de riesgo estandarizados z con densidad &phi;, el escenario más plausible que llega al punto de falla maximiza &phi;(z) sujeto a que la pérdida llegue al umbral, que para factores gaussianos es el escenario de mínima distancia de Mahalanobis. C18 toma el punto de falla como el CET1 en el mínimo legal apilado chileno al cabo de tres años, los factores como los regresores estandarizados de los satélites con su covarianza de 1985 a 2019, y reporta la distancia, su probabilidad de cola chi cuadrado como plausibilidad, y la búsqueda desde varios inicios. No se usa el método de verosimilitud empírica de Glasserman, Kang y Kang: solo se leyó su resumen <Cite id="glassermankang2015" />.</>}
      />
      <Equation
        tex={String.raw`\mathbf z^{*} = \arg\min_{\mathbf z}\ \mathbf z^{\top}\Sigma^{-1}\mathbf z \ \ \text{s.t.}\ \ L(\mathbf z) \ge \ell, \qquad \mathbf x^{*} = \frac{\ell\,\Sigma\mathbf g}{\mathbf g^{\top}\Sigma\mathbf g}\ \text{ for } L(\mathbf x) = \mathbf g^{\top}\mathbf x, \qquad p = \Pr\bigl[\chi^{2}_{k} \ge \mathbf x^{*\top}\Sigma^{-1}\mathbf x^{*}\bigr]`}
        caption={<T en={<>Reverse stress (dossier 01, J.4, a Contraste formulation, not regulatory text; the closed form is derived here by a Lagrange condition): z the factors, &Sigma; their covariance, L the loss and &ell; its threshold, the one at which the CET1 reaches the legal minimum stack; for a linear loss with gradient g the solution is x* above, at distance &ell; over the root of g&prime;&Sigma;g; and p the tail probability of a chi-square variable with k degrees of freedom, k the number of factors, at the squared distance of the solution, the plausibility that C18 reports.</>} es={<>Estrés inverso (dossier 01, J.4, una formulación de Contraste, no texto regulatorio; la forma cerrada se deriva aquí con una condición de Lagrange): z los factores, &Sigma; su covarianza, L la pérdida y &ell; su umbral, aquel en que el CET1 llega al mínimo legal apilado; para una pérdida lineal con gradiente g la solución es x* de arriba, a distancia &ell; sobre la raíz de g&prime;&Sigma;g; y p la probabilidad de cola de una variable chi cuadrado con k grados de libertad, k el número de factores, a la distancia al cuadrado de la solución, la plausibilidad que reporta C18.</>} />}
      />
      <Figure caption={t2('Reverse stress as geometry: the ellipses are sets of scenarios of equal plausibility around the baseline, and the straight line is the loss that takes the CET1 to the legal minimum. The most plausible scenario that breaks the bank is the point where the line first touches an ellipse, at the smallest distance from the baseline.', 'El estrés inverso como geometría: las elipses son conjuntos de escenarios de igual plausibilidad alrededor de la línea base, y la recta es la pérdida que lleva el CET1 al mínimo legal. El escenario más plausible que quiebra al banco es el punto donde la recta toca primero una elipse, a la menor distancia de la línea base.')}>
        <ReverseFigure />
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
      title={{ en: 'Capital aggregation and macro stress testing', es: 'Agregación de capital y pruebas de estrés macro' }}
      refs={['rosenberg2006', 'kuritzkes2003', 'jointforum2010', 'embrechts2002', 'embrechts2013', 'demartamcneil2005', 'tasche2008euler', 'barrieuscandolo2015', 'glassermanxu2014', 'fedcredit2026', 'fedmodelreview2026', 'litterman1986', 'banbura2010', 'pesaran2004', 'dees2007', 'adrian2019', 'covas2014', 'eba2025note', 'eba2025results', 'ngfs5', 'ngfstech', 'ecbclimate2022', 'ran2113', 'ecbicaap', 'cmfp2faq', 'ebagl201804', 'bcbsd450', 'glassermankang2015']}
    >
      <SubTabs
        ariaLabel={t('Parts of the topic', 'Partes del tema')}
        tabs={[
          { id: 'aggregation', label: t('Aggregation and its band', 'Agregación y su banda'), content: <AggregationPart /> },
          { id: 'allocation', label: t('Allocation and validation', 'Asignación y validación'), content: <AllocationPart /> },
          { id: 'satellites', label: t('Macro stress and satellites', 'Estrés macro y satélites'), content: <SatellitePart /> },
          { id: 'scenarios', label: t('Scenarios and exercises', 'Escenarios y ejercicios'), content: <ScenarioPart /> },
          { id: 'iape', label: t('The IAPE and reverse stress', 'El IAPE y el estrés inverso'), content: <IapePart /> },
        ]}
      />
      <Callout variant="honest" title={t('What is exact, what is a choice and what these views are not', 'Qué es exacto, qué es una decisión y qué no son estas vistas')}>
        <T
          en={<>The formulas of the ladder, the t tail dependence, the Euler contributions, the OI, the legal CET1 stack, the EBA paragraphs and the NGFS classification are exact as transcribed from the sources, and the values of the rearrangement figure are the published ones. The set of degrees of freedom, the inter-risk correlations beyond the three published values, the horizon and level scaling of the market marginal, the PPNR ratios, the Pillar 2 of the bank and the stress buffer d are conventions or case assumptions, labelled as such wherever they appear, and the minimum ratio of the severity test is a convention. The headline capital is the simple sum and every diversified or bound figure is information, never capital. The scenarios and satellites are US-calibrated adaptations transposed onto a synthetic bank, so a result says what the structure does and nothing about any real bank, and the P2G figure is a Contraste approximation, not the CMF calibration. Several items of the sources stay unverified: the correlation ranges of Kuritzkes, Schuermann and Weiner, the Joint Forum wording, the wording of the three fallacies of Embrechts, McNeil and Straumann, the chapter of the McNeil textbook, the details of the empirical-likelihood method and the attribution of the Mahalanobis rule, the inter-risk correlation for the banking-book rate risk, and the Pillar 2 phase-in percentage. The vine copulas, the Clayton sampling, the Bayesian VAR and the panel quantile satellite are not built. The views replicate published methods and run tests; they do not show that a model is approved or regulatory-compliant.</>}
          es={<>Las fórmulas de la escalera, la dependencia de cola t, las contribuciones de Euler, el OI, el apilado legal de CET1, los párrafos de la EBA y la clasificación de NGFS son exactos tal como se transcribieron de las fuentes, y los valores de la figura del reordenamiento son los publicados. El conjunto de grados de libertad, las correlaciones entre riesgos más allá de los tres valores publicados, el escalamiento de horizonte y nivel de la marginal de mercado, las razones de PPNR, el Pilar 2 del banco y el colchón de estrés d son convenciones o supuestos del caso, rotulados como tales donde aparecen, y la razón mínima de la prueba de severidad es una convención. El capital principal es la suma simple y toda cifra diversificada o acotada es información, nunca capital. Los escenarios y los satélites son adaptaciones calibradas en EE. UU. transpuestas a un banco sintético, así que un resultado dice lo que hace la estructura y nada de ningún banco real, y la cifra de P2G es una aproximación de Contraste, no la calibración de la CMF. Varios puntos de las fuentes siguen sin verificar: los rangos de correlación de Kuritzkes, Schuermann y Weiner, la redacción del Joint Forum, la redacción de las tres falacias de Embrechts, McNeil y Straumann, el capítulo del texto de McNeil, los detalles del método de verosimilitud empírica y la atribución de la regla de Mahalanobis, la correlación entre riesgos para el riesgo de tasa del libro de banca, y el porcentaje de la gradualidad del Pilar 2. Las cópulas vine, el muestreo de Clayton, el VAR bayesiano y el satélite de cuantiles en panel no están construidos. Las vistas replican métodos publicados y corren pruebas; no muestran que un modelo esté aprobado ni que cumpla la regulación.</>}
        />
      </Callout>
    </DocSection>
  );
}

export const methodologySection: MethodologySection = {
  id: 'aggregation-stress',
  group: 'capital',
  order: 140,
  title: { en: 'Aggregation and stress testing', es: 'Agregación y pruebas de estrés' },
  Body,
};
