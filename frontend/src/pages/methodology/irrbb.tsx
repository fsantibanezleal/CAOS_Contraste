// The Methodology section on interest rate risk in the banking book (U10): the economic value and net interest income
// measures, the six prescribed shocks and their sizes, the standardised EVE framework of Basel SRP31 with the caps on
// non-maturity deposits and the prepayment multipliers, the behavioural models, the curve models and the dynamic NII
// simulation behind EaR and EVaR, and the Chilean standard measure of RAN 21-13 Annex 1 with the UF and the UR currency
// (cases C14 and C15). Transcribed from research dossier 05 (section D: D.1 to D.7), dossier 01 (section H: H.1 to H.5) and
// dossier 03 (F.1 and F.2), where each formula, table and threshold was read at its primary source on 2026-10-04. Every
// display equation carries a caption that defines its symbols. The registry mounts it as one tab of its group; one file
// exports one section, so the topic is one `method` section with one part per question, as sub-tabs (ADR-0017 section
// 2.1), each part with its own paragraphs, equations and figure, and one honest callout for the topic.
import { Callout, Cite, DocSection, Equation, Figure, SubTabs, formatNumber } from '@fasl-work/caos-app-shell';
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

/** The four shock shapes of SRP31.91 at a size of 100 bp for the short and the long rate, over the bucket midpoints to 25 years. */
function ShapesFigure() {
  const t = useT();
  // t in [0, 25] years to x in [50, 450]; shift v in [-70, 110] bp to y = 134 - v
  const x = (years: number) => 50 + (years / 25) * 400;
  const y = (v: number) => 134 - v;
  const grid = Array.from({ length: 101 }, (_, i) => i * 0.25);
  const short = (u: number) => 100 * Math.exp(-u / 4);
  const long = (u: number) => 100 * (1 - Math.exp(-u / 4));
  const curve = (f: (u: number) => number) => path(grid.map((u) => [x(u), y(f(u))]));
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('Four prescribed shock shapes against the term in years for a 100 bp short and long shock: parallel is flat, the short-rate shock decays with the term, the steepener falls below zero at the short end and rises towards 90 bp at the long end, and the flattener starts near 80 bp and falls below zero', 'Cuatro formas de choque prescritas contra el plazo en años para un choque corto y largo de 100 pb: el paralelo es plano, el de tasas cortas decae con el plazo, el empinamiento baja de cero en el extremo corto y sube hacia 90 pb en el largo, y el aplanamiento parte cerca de 80 pb y cae bajo cero')}>
      <line className="dg-axis" x1={x(0)} y1={y(0)} x2={x(25)} y2={y(0)} />
      <line className="dg-axis" x1={x(0)} y1={y(110)} x2={x(0)} y2={y(-70)} />
      {[0, 5, 10, 15, 20, 25].map((u) => (
        <text key={u} className="dg-tick" x={x(u)} y={y(-70) + 14} textAnchor="middle">{t(String(u), String(u))}</text>
      ))}
      {[100, 0, -50].map((v) => (
        <text key={v} className="dg-tick" x={x(0) - 6} y={y(v) + 4} textAnchor="end">{v}</text>
      ))}
      <path className="dg-curve-faint" d={curve(() => 100)} fill="none" />
      <path className="dg-curve" d={curve(short)} fill="none" />
      <path className="dg-curve-2" d={curve((u) => -0.65 * short(u) + 0.9 * long(u))} fill="none" />
      <path className="dg-curve-faint" d={curve((u) => 0.8 * short(u) - 0.6 * long(u))} fill="none" strokeDasharray="5 3" />
      <text className="dg-edge-label" x={x(0) + 4} y={y(100) - 6} textAnchor="start">{t('parallel', 'paralelo')}</text>
      <text className="dg-edge-label" x={x(5) + 6} y={y(short(5)) - 8} textAnchor="start">{t('short rates', 'tasas cortas')}</text>
      <text className="dg-edge-label" x={x(25) - 4} y={y(90) + 16} textAnchor="end">{t('steepener', 'empinamiento')}</text>
      <text className="dg-edge-label" x={x(25) - 4} y={y(-60) - 8} textAnchor="end">{t('flattener', 'aplanamiento')}</text>
      <text className="dg-axis-label" x={W / 2} y={H - 24} textAnchor="middle">{t('bucket midpoint t_k, years (x = 4)', 'punto medio del tramo t_k, años (x = 4)')}</text>
      <text className="dg-axis-label" x={8} y={20} textAnchor="start">{t('shift, bp', 'desplazamiento, pb')}</text>
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('Illustrative schematic, not a result', 'Esquema ilustrativo, no un resultado')}</text>
    </svg>
  );
}

/** The supervisory caps of SRP31 Table 4: the share of a non-maturity deposit that may be core, and the longest average maturity. */
function CapsFigure() {
  const t = useT();
  const rows = [
    { y: 36, name: t('Retail transactional', 'Minorista transaccional'), share: 90, years: '5' },
    { y: 96, name: t('Retail non-transactional', 'Minorista no transaccional'), share: 70, years: t('4.5', '4,5') },
    { y: 156, name: t('Wholesale', 'Mayorista'), share: 50, years: '4' },
  ];
  const x = (pct: number) => 150 + (pct / 100) * 280;
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('Three bars for the caps of the standardised framework on non-maturity deposits: retail transactional at most 90 percent core with an average maturity of at most 5 years, retail non-transactional 70 percent and 4.5 years, wholesale 50 percent and 4 years; the rest of each deposit goes to the overnight bucket', 'Tres barras con los topes del marco estandarizado para depósitos sin vencimiento: minorista transaccional hasta 90 por ciento estable con un plazo promedio de hasta 5 años, minorista no transaccional 70 por ciento y 4,5 años, mayorista 50 por ciento y 4 años; el resto de cada depósito va al tramo a la vista')}>
      <line className="dg-axis" x1={x(0)} y1={20} x2={x(0)} y2={196} />
      {rows.map((r) => (
        <g key={r.name}>
          <text className="dg-box-title" x={8} y={r.y + 18} textAnchor="start">{r.name}</text>
          <rect className="dg-fill-accent" x={x(0)} y={r.y} width={x(100) - x(0)} height={26} opacity={0.25} />
          <rect className="dg-fill-accent" x={x(0)} y={r.y} width={x(r.share) - x(0)} height={26} />
          <text className="dg-bar-label" x={x(r.share) - 6} y={r.y + 17} textAnchor="end">{`${r.share} %`}</text>
          <text className="dg-note" x={x(0)} y={r.y + 42} textAnchor="start">{t(`average maturity of the core at most ${r.years} years; the rest is overnight`, `plazo promedio de la parte estable hasta ${r.years} años; el resto va a la vista`)}</text>
        </g>
      ))}
      <text className="dg-axis-label" x={x(50)} y={H - 40} textAnchor="middle">{t('core share of the balance, cap', 'parte estable del saldo, tope')}</text>
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('Illustrative schematic, not a result', 'Esquema ilustrativo, no un resultado')}</text>
    </svg>
  );
}

/** The Nelson-Siegel loadings of the slope and the curvature factor at the Diebold-Li decay of 0.0609 per month. */
function LoadingsFigure() {
  const t = useT();
  const lambda = 0.0609;
  // maturity in [0, 120] months to x in [50, 450]; loading in [0, 1] to y = 204 - 160 v
  const x = (m: number) => 50 + (m / 120) * 400;
  const y = (v: number) => 204 - 160 * v;
  const slope = (m: number) => (m === 0 ? 1 : (1 - Math.exp(-lambda * m)) / (lambda * m));
  const curv = (m: number) => (m === 0 ? 0 : slope(m) - Math.exp(-lambda * m));
  const grid = Array.from({ length: 241 }, (_, i) => i * 0.5);
  // the curvature loading is unimodal: a ternary search finds its maximum (29.446 months at this decay)
  let lo = 1;
  let hi = 120;
  for (let i = 0; i < 80; i++) {
    const a = lo + (hi - lo) / 3;
    const b = hi - (hi - lo) / 3;
    if (curv(a) < curv(b)) lo = a;
    else hi = b;
  }
  const peak = (lo + hi) / 2;
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('The three Nelson-Siegel factor loadings against maturity in months: the level loading is one, the slope loading starts at one and decays, and the curvature loading starts at zero, peaks near 29 months and decays', 'Las tres cargas de factor de Nelson-Siegel contra el plazo en meses: la carga de nivel es uno, la de pendiente parte en uno y decae, y la de curvatura parte en cero, alcanza su máximo cerca de 29 meses y decae')}>
      <line className="dg-axis" x1={x(0)} y1={y(0)} x2={x(120)} y2={y(0)} />
      <line className="dg-axis" x1={x(0)} y1={y(1)} x2={x(0)} y2={y(0)} />
      {[0, 24, 48, 72, 96, 120].map((m) => (
        <text key={m} className="dg-tick" x={x(m)} y={y(0) + 14} textAnchor="middle">{m}</text>
      ))}
      {[0, 0.5, 1].map((v) => (
        <text key={v} className="dg-tick" x={x(0) - 6} y={y(v) + 4} textAnchor="end">{t(String(v), String(v).replace('.', ','))}</text>
      ))}
      <path className="dg-curve-faint" d={path(grid.map((m) => [x(m), y(1)]))} fill="none" />
      <path className="dg-curve" d={path(grid.map((m) => [x(m), y(slope(m))]))} fill="none" />
      <path className="dg-curve-2" d={path(grid.map((m) => [x(m), y(curv(m))]))} fill="none" />
      <line className="dg-marker" x1={x(peak)} y1={y(curv(peak))} x2={x(peak)} y2={y(0)} />
      <text className="dg-marker-label" x={x(peak)} y={y(0) - 6} textAnchor="middle">{t(`peak at ${formatNumber(peak, 'en', { decimals: 1 })} months`, `máximo a ${formatNumber(peak, 'es', { decimals: 1 })} meses`)}</text>
      <text className="dg-edge-label" x={x(60)} y={y(1) - 6} textAnchor="middle">{t('level', 'nivel')}</text>
      <text className="dg-edge-label" x={x(14) + 8} y={y(slope(14)) - 10} textAnchor="start">{t('slope', 'pendiente')}</text>
      <text className="dg-edge-label" x={x(peak) + 8} y={y(curv(peak)) - 10} textAnchor="start">{t('curvature', 'curvatura')}</text>
      <text className="dg-axis-label" x={W / 2} y={H - 24} textAnchor="middle">{t('maturity m, months (decay 0.0609 per month)', 'plazo m, meses (decaimiento 0,0609 por mes)')}</text>
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('Illustrative schematic, not a result', 'Esquema ilustrativo, no un resultado')}</text>
    </svg>
  );
}

function Box({ x, y, w, h, title, sub, tone }: { x: number; y: number; w: number; h: number; title: string; sub: string; tone?: 'accent' | 'good' }) {
  return (
    <g>
      <rect className={`dg-box${tone ? ` ${tone}` : ''}`} x={x} y={y} width={w} height={h} rx={6} />
      <text className={`dg-box-title${tone === 'accent' ? ' accent' : ''}`} x={x + w / 2} y={y + h / 2 - 2} textAnchor="middle">{title}</text>
      <text className="dg-box-sub" x={x + w / 2} y={y + h / 2 + 13} textAnchor="middle">{sub}</text>
    </g>
  );
}

/** How Annex 1 builds delta NII: two legs, the offset, the larger parallel shock, and the indexation charge added apart. */
function AnnexFigure() {
  const t = useT();
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={t('How the Chilean standard measure of net interest income is built: the CLP leg and the UF-indexed UR leg are combined with a 50 percent offset when their signs are opposite, the larger of the two parallel shocks is taken, and the indexation charge of 2.5 percent of the absolute net UF position is added apart to give delta NII', 'Cómo se construye la medida estándar chilena de margen financiero neto: el tramo CLP y el tramo UR indexado a UF se combinan con una compensación de 50 por ciento cuando sus signos son opuestos, se toma el mayor de los dos choques paralelos, y el cargo por reajustabilidad de 2,5 por ciento de la posición neta en UF en valor absoluto se suma aparte para dar el delta NII')}>
      <Box x={8} y={14} w={128} h={56} title={t('CLP leg', 'Tramo CLP')} sub={t('delta NII in CLP', 'delta NII en CLP')} />
      <Box x={8} y={100} w={128} h={56} title={t('UR leg', 'Tramo UR')} sub={t('UF-indexed, in CLF', 'indexado a UF, en CLF')} />
      <Box x={176} y={57} w={128} h={56} tone="accent" title={t('Pair CLP and CLF', 'Par CLP y CLF')} sub={t('50 % offset if signs differ', '50 % de compensación si difieren')} />
      <Box x={344} y={14} w={128} h={56} title={t('Larger parallel shock', 'Mayor choque paralelo')} sub={t('up or down, 300 bp', 'al alza o a la baja, 300 pb')} />
      <Box x={176} y={150} w={128} h={56} title={t('Indexation charge', 'Cargo por reajustabilidad')} sub={t('2.5 % of |net UF position|', '2,5 % de |posición neta UF|')} />
      <Box x={344} y={186} w={128} h={56} tone="good" title={t('Delta NII', 'Delta NII')} sub={t('rate result + charge', 'resultado de tasa + cargo')} />
      <line className="dg-edge" x1={136} y1={42} x2={176} y2={76} />
      <line className="dg-edge" x1={136} y1={128} x2={176} y2={96} />
      <line className="dg-edge" x1={304} y1={85} x2={344} y2={50} />
      <line className="dg-edge" x1={408} y1={70} x2={408} y2={186} />
      <line className="dg-edge" x1={72} y1={156} x2={176} y2={178} />
      <line className="dg-edge" x1={304} y1={178} x2={344} y2={214} />
      <text className="dg-note" x={W - 8} y={H - 6} textAnchor="end">{t('Illustrative schematic, not a result', 'Esquema ilustrativo, no un resultado')}</text>
    </svg>
  );
}

export function MeasuresPart() {
  return (
    <>
      <P
        en={<>Interest rate risk in the banking book is measured two ways, and a validator must be able to rebuild both. The change in the economic value of equity, ΔEVE, excludes the bank&apos;s own equity, includes every cash flow of the interest-rate-sensitive banking book items, discounts at a risk-free rate and runs the balance sheet off, so positions amortise and there is no new business (<Ref>DIS70.4</Ref>) <Cite id="dis70" />. The change in net interest income, ΔNII, uses expected cash flows including commercial margins, holds the balance sheet constant, so maturing or repricing cash flows are replaced by identical new ones, and compares the interest income of a rolling twelve months (<Ref>DIS70.5</Ref>). Six prescribed shocks apply to EVE and two of them, the parallel up and the parallel down, to NII (<Ref>SRP31.90</Ref>) <Cite id="srp31" />. In every document of C14 and C15 a positive Δ is a loss, and only losses are aggregated across currencies.</>}
        es={<>El riesgo de tasa de interés en el libro de banca se mide de dos maneras, y un validador debe poder reconstruir ambas. El cambio en el valor económico del patrimonio, ΔEVE, excluye el patrimonio propio del banco, incluye todos los flujos de las partidas del libro de banca sensibles a la tasa, descuenta a una tasa libre de riesgo y corre el balance hacia su extinción, de modo que las posiciones se amortizan y no hay negocio nuevo (<Ref>DIS70.4</Ref>) <Cite id="dis70" />. El cambio en el margen financiero neto, ΔNII, usa los flujos esperados incluidos los márgenes comerciales, mantiene el balance constante, de modo que los flujos que vencen o reprecian se reemplazan por otros idénticos, y compara el ingreso por intereses de doce meses móviles (<Ref>DIS70.5</Ref>). Seis choques prescritos se aplican al EVE y dos de ellos, el paralelo al alza y el paralelo a la baja, al NII (<Ref>SRP31.90</Ref>) <Cite id="srp31" />. En cada documento de C14 y C15 un Δ positivo es una pérdida, y solo las pérdidas se agregan entre monedas.</>}
      />
      <Equation
        tex={String.raw`\begin{aligned}\Delta S_{\mathrm{par},c}(t_k) &= \pm\bar S_{\mathrm{par},c}, \qquad \Delta S_{\mathrm{short},c}(t_k) = \pm\bar S_{\mathrm{short},c}\,e^{-t_k/x}, \qquad \Delta S_{\mathrm{long},c}(t_k) = \pm\bar S_{\mathrm{long},c}\bigl(1 - e^{-t_k/x}\bigr)\\ \Delta S_{\mathrm{steep},c}(t_k) &= -0.65\,\lvert\Delta S_{\mathrm{short},c}\rvert + 0.9\,\lvert\Delta S_{\mathrm{long},c}\rvert, \qquad \Delta S_{\mathrm{flat},c}(t_k) = +0.8\,\lvert\Delta S_{\mathrm{short},c}\rvert - 0.6\,\lvert\Delta S_{\mathrm{long},c}\rvert\end{aligned}`}
        caption={<T en={<>The six prescribed shocks of the Basel standard (<Ref>SRP31.90</Ref> to <Ref>SRP31.92</Ref>; dossier 01, H.2): t_k the midpoint of time bucket k in years, c the currency, the barred S the size of the shock for that currency and shape (in basis points), x = 4 for most currencies unless national supervisors determine otherwise. The long shock is used only inside the two rotations, and the sign of the parallel and short shocks gives the up and down scenarios. Supervisors may floor post-shock rates at a level not above zero (<Ref>SRP31.93</Ref>).</>} es={<>Los seis choques prescritos del estándar de Basilea (<Ref>SRP31.90</Ref> a <Ref>SRP31.92</Ref>; dossier 01, H.2): t_k el punto medio del tramo k en años, c la moneda, la S con barra el tamaño del choque para esa moneda y forma (en puntos base), x = 4 para la mayoría de las monedas salvo que los supervisores nacionales determinen otra cosa. El choque largo se usa solo dentro de las dos rotaciones, y el signo de los choques paralelo y corto da los escenarios al alza y a la baja. Los supervisores pueden fijar un piso a las tasas posteriores al choque en un nivel no superior a cero (<Ref>SRP31.93</Ref>).</>} />}
      />
      <P
        en={<>The standard gives the numbers that pin the shapes down, and the engine reproduces them as a validation test. At t_k = 3.5 years the short factor is e^(-3.5/4) = 0.417, so a +100 bp short shock moves the curve by +41.7 bp; with a short and a long size of 100 bp, the JPY case, the steepener moves it by +25.4 bp and the flattener by -1.6 bp (<Ref>SRP31.92</Ref>) <Cite id="srp31" />. A post-shock floor is a national choice: the EU applies a maturity-dependent floor that starts at -150 bp at the immediate maturity and rises 3 bp per year to 0 % at 50 years (Delegated Regulation 2024/856, <Ref>Article 3(7)</Ref>) <Cite id="eu2024856" />, and Chile floors the UR rates at -2 % and every other currency at 0 %, or at the pre-shock rate if that is lower.</>}
        es={<>El estándar da los números que fijan las formas, y el motor los reproduce como una prueba de validación. En t_k = 3,5 años el factor corto es e^(-3,5/4) = 0,417, de modo que un choque corto de +100 pb mueve la curva en +41,7 pb; con un tamaño corto y largo de 100 pb, el caso del JPY, el empinamiento la mueve en +25,4 pb y el aplanamiento en -1,6 pb (<Ref>SRP31.92</Ref>) <Cite id="srp31" />. Un piso posterior al choque es una decisión nacional: la UE aplica un piso según el plazo que parte en -150 pb al plazo inmediato y sube 3 pb por año hasta 0 % a los 50 años (Reglamento Delegado 2024/856, <Ref>Artículo 3(7)</Ref>) <Cite id="eu2024856" />, y Chile fija el piso de las tasas UR en -2 % y el de cualquier otra moneda en 0 %, o en la tasa previa al choque si es menor.</>}
      />
      <Figure caption={t2('The shapes of the parallel, short-rate, steepener and flattener shocks for a size of 100 bp at the short and the long end, over the bucket midpoints to 25 years: the short factor decays with the term, and the two rotations cross zero.', 'Las formas de los choques paralelo, de tasas cortas, de empinamiento y de aplanamiento para un tamaño de 100 pb en el extremo corto y el largo, sobre los puntos medios de los tramos hasta 25 años: el factor corto decae con el plazo, y las dos rotaciones cruzan el cero.')}>
        <ShapesFigure />
      </Figure>
      <P
        en={<>The sizes are data, and they changed. The July 2024 recalibration (d578, in force on 2026-01-01) uses data from January 2000 to December 2023, the 99.9th percentile of local rolling six-month average absolute changes, rounded to 25 bp: for USD the parallel, short and long sizes are 200, 300 and 225 bp, for EUR 225, 350 and 200 and for JPY 100, 100 and 100 <Cite id="bcbsd578" />. The original 2016 table (data 2000 to 2015, the 99th percentile of global factors, rounded to 50 bp) gave 200, 300 and 150 bp for USD and 200, 250 and 100 for EUR <Cite id="bcbsd368" />. The Chilean peso is in neither table: a jurisdiction may recalculate the shocks for its domestic currency, and a CLP size is either the one the CMF prescribes in Annex 1 or a Contraste estimate on Banco Central de Chile yields, labelled as such and never presented as a regulatory parameter. C14 runs both calibrations on the same balance sheet and shows them side by side.</>}
        es={<>Los tamaños son datos, y cambiaron. La recalibración de julio de 2024 (d578, vigente desde el 2026-01-01) usa datos de enero de 2000 a diciembre de 2023, el percentil 99,9 de los cambios absolutos promedio móviles semestrales locales, redondeado a 25 pb: para USD los tamaños paralelo, corto y largo son 200, 300 y 225 pb, para EUR 225, 350 y 200 y para JPY 100, 100 y 100 <Cite id="bcbsd578" />. La tabla original de 2016 (datos de 2000 a 2015, el percentil 99 de los factores globales, redondeado a 50 pb) daba 200, 300 y 150 pb para USD y 200, 250 y 100 para EUR <Cite id="bcbsd368" />. El peso chileno no está en ninguna tabla: una jurisdicción puede recalcular los choques para su moneda local, y un tamaño para CLP es el que la CMF prescribe en el Anexo 1 o una estimación de Contraste sobre tasas del Banco Central de Chile, rotulada como tal y nunca presentada como un parámetro regulatorio. C14 corre ambas calibraciones sobre el mismo balance y las muestra lado a lado.</>}
      />
      <Equation
        tex={String.raw`\Delta \mathrm{NII} \;\approx\; \sum_{k:\,t_k<1} G_k\,\Delta r\,(1 - t_k), \quad G_k = \mathrm{RSA}_k - \mathrm{RSL}_k, \qquad \mathrm{DGAP} = D_A - \frac{L}{A}\,D_L, \quad \Delta E \approx -\,\mathrm{DGAP}\cdot A\cdot \Delta y`}
        caption={<T en={<>The first two rungs of the ladder (dossier 05, D.1 and D.2): RSA_k and RSL_k the rate-sensitive assets and liabilities that reprice in bucket k, Δr a parallel shift, t_k the bucket midpoint in years, so each gap earns the part of the year left after it reprices; D_A and D_L the value-weighted modified durations of assets and liabilities, A and L their market values, Δy a parallel yield change. Both are textbook first-order approximations that ignore basis risk, optionality and new business, which is why the dynamic simulation exists.</>} es={<>Los dos primeros peldaños de la escalera (dossier 05, D.1 y D.2): RSA_k y RSL_k los activos y pasivos sensibles a la tasa que reprecian en el tramo k, Δr un desplazamiento paralelo, t_k el punto medio del tramo en años, de modo que cada brecha gana la parte del año que queda después de repreciar; D_A y D_L las duraciones modificadas ponderadas por valor de activos y pasivos, A y L sus valores de mercado, Δy un cambio paralelo del rendimiento. Ambas son aproximaciones de primer orden de los textos que ignoran el riesgo de base, las opciones y el negocio nuevo, por eso existe la simulación dinámica.</>} />}
      />
    </>
  );
}

export function EvePart() {
  return (
    <>
      <P
        en={<>The standardised EVE of the Basel framework slots the net notional repricing cash flows of each currency with material exposure, more than 5 % of banking book assets or liabilities, into 19 time buckets whose midpoints run from 0.0028 years for overnight to 25 years for over twenty years (<Ref>SRP31.96</Ref>, Table 3) <Cite id="srp31" />. Assets exclude fixed assets and banking book equity, and liabilities include non-remunerated deposits and exclude CET1 (<Ref>SRP31.97</Ref>). Each bucket is discounted with a continuously compounded factor that reflects the shock scenario, the add-on KAO covers automatic interest rate options, and the risk measure is the largest, over the six scenarios, of the summed positive losses across currencies (<Ref>SRP31.129</Ref>). Cash flows are themselves scenario dependent, because non-maturity deposits, prepayment and term-deposit redemption move them, which is where the behavioural assumptions enter.</>}
        es={<>El EVE estandarizado del marco de Basilea ubica los flujos nocionales netos de reprecio de cada moneda con exposición material, más de 5 % de los activos o pasivos del libro de banca, en 19 tramos de tiempo cuyos puntos medios van de 0,0028 años para a la vista a 25 años para más de veinte años (<Ref>SRP31.96</Ref>, Tabla 3) <Cite id="srp31" />. Los activos excluyen los activos fijos y el patrimonio del libro de banca, y los pasivos incluyen los depósitos no remunerados y excluyen el CET1 (<Ref>SRP31.97</Ref>). Cada tramo se descuenta con un factor de capitalización continua que refleja el escenario de choque, el complemento KAO cubre las opciones automáticas de tasa, y la medida de riesgo es la mayor, entre los seis escenarios, de las pérdidas positivas sumadas entre monedas (<Ref>SRP31.129</Ref>). Los flujos dependen a su vez del escenario, porque los depósitos sin vencimiento, el prepago y el rescate de depósitos a plazo los mueven, y ahí entran los supuestos conductuales.</>}
      />
      <Equation
        tex={String.raw`\begin{aligned}DF_{i,c}(t_k) &= \exp\bigl(-R_{i,c}(t_k)\,t_k\bigr), \qquad \mathrm{EVE}_{i,c} = \sum_{k=1}^{K} CF_{i,c}(k)\,DF_{i,c}(t_k)\\ \Delta \mathrm{EVE}_{i,c} &= \sum_{k=1}^{K} CF_{0,c}(k)\,DF_{0,c}(t_k) - \sum_{k=1}^{K} CF_{i,c}(k)\,DF_{i,c}(t_k) + KAO_{i,c}\\ \text{risk measure} &= \max_{i\in\{1,\dots,6\}}\Bigl\{\max\Bigl(0;\ \sum_{c:\,\Delta \mathrm{EVE}_{i,c}>0}\Delta \mathrm{EVE}_{i,c}\Bigr)\Bigr\}\end{aligned}`}
        caption={<T en={<>The standardised EVE (<Ref>SRP31.129</Ref>; dossier 01, H.4): CF_{'{i,c}'}(k) the net notional repricing cash flow of currency c in bucket k under scenario i (scenario 0 is the base), R_{'{i,c}'}(t_k) the shocked continuously compounded zero rate, DF the discount factor, K = 19, and KAO the fair-value change of sold minus bought automatic options. A positive ΔEVE is a loss and only losses are summed across currencies. C14 holds the cash flows by bucket for each shock and prints the EVE, the KAO and ΔEVE for the six.</>} es={<>El EVE estandarizado (<Ref>SRP31.129</Ref>; dossier 01, H.4): CF_{'{i,c}'}(k) el flujo nocional neto de reprecio de la moneda c en el tramo k bajo el escenario i (el escenario 0 es la base), R_{'{i,c}'}(t_k) la tasa cero con capitalización continua con choque, DF el factor de descuento, K = 19, y KAO el cambio de valor razonable de las opciones automáticas vendidas menos las compradas. Un ΔEVE positivo es una pérdida y solo las pérdidas se suman entre monedas. C14 guarda los flujos por tramo de cada choque e imprime el EVE, el KAO y el ΔEVE de los seis.</>} />}
      />
      <P
        en={<>Non-maturity deposits (<Ref>SRP31.107</Ref> to <Ref>SRP31.112</Ref>) are split into a stable part from ten years of volume history, the core, which is unlikely to reprice, and a non-core part that is slotted in the overnight bucket. Table 4 caps the core proportion and its average maturity: at most 90 % and 5 years for retail transactional deposits, 70 % and 4.5 years for retail non-transactional, and 50 % and 4 years for wholesale <Cite id="srp31" />. The caps bind the supervisory number, not the bank&apos;s model, so C14 keeps for every segment the share the validator asked for, the cap, the value used and a flag that says the cap bit. The result can then be read with the cap, which is what the standard prescribes, and without it, which is what the bank&apos;s own assumption would have given. The technique behind the replicating portfolio is described in the 2016 standard (footnote 38): one sixtieth of the balance reinvested monthly in a five-year fixed rate gives a weighted average maturity of 2.5 years <Cite id="bcbsd368" />.</>}
        es={<>Los depósitos sin vencimiento (<Ref>SRP31.107</Ref> a <Ref>SRP31.112</Ref>) se dividen en una parte estable a partir de diez años de historia de volumen, la parte estable (core), que es poco probable que reprecie, y una parte no estable que se ubica en el tramo a la vista. La Tabla 4 limita la proporción estable y su plazo promedio: hasta 90 % y 5 años para depósitos minoristas transaccionales, 70 % y 4,5 años para minoristas no transaccionales, y 50 % y 4 años para mayoristas <Cite id="srp31" />. Los topes atan al número supervisor, no al modelo del banco, así que C14 guarda para cada segmento la parte que el validador pidió, el tope, el valor usado y una marca que dice que el tope se aplicó. El resultado puede leerse entonces con el tope, que es lo que prescribe el estándar, y sin él, que es lo que habría dado el supuesto propio del banco. La técnica detrás de la cartera replicante se describe en el estándar de 2016 (nota 38): una sexagésima parte del saldo reinvertida cada mes a cinco años a tasa fija da un plazo promedio ponderado de 2,5 años <Cite id="bcbsd368" />.</>}
      />
      <Figure caption={t2('The supervisory caps on non-maturity deposits: the longest bar of each category is the cap on the core share of the balance, and the line under it gives the cap on the average maturity of the core; the part above the cap is slotted overnight.', 'Los topes supervisores de los depósitos sin vencimiento: la barra larga de cada categoría es el tope de la parte estable del saldo, y la línea bajo ella da el tope del plazo promedio de la parte estable; lo que excede el tope se ubica a la vista.')}>
        <CapsFigure />
      </Figure>
      <P
        en={<>Prepayment and early redemption are multiplied by the scenario. In a rising-rate scenario prepayment slows and in a falling-rate one it speeds up, so the prepayment rate of scenario i is the base rate times a multiplier gamma of 0.8, 1.2, 0.8, 1.2, 0.8 and 1.2 for the six shocks in the order parallel up, parallel down, steepener, flattener, short up and short down, capped at one (<Ref>SRP31.119</Ref>, Table 5); term-deposit early redemption uses the multiplier u of 1.2, 0.8, 0.8, 1.2, 1.2 and 0.8 in the same order (<Ref>SRP31.125</Ref>, Table 6) <Cite id="srp31" />. Behind the base rate sit the single monthly mortality and the conditional prepayment rate, and the PSA benchmark for mortgages, 0.2 % in month 1 rising by 0.2 % a month to 6 % at month 30 and flat after, scaled by the PSA percentage <Cite id="fuster2022" />. Rational option-exercise, proportional-hazard and competing-risks models of prepayment are the families a validator meets <Cite id="stanton1995" /> <Cite id="schwartztorous1989" /> <Cite id="deng2000" />; for Chilean mortgages, mostly UF-indexed with prepayment fees, no primary calibration source was checked.</>}
        es={<>El prepago y el rescate anticipado se multiplican por el escenario. En un escenario de alza de tasas el prepago se frena y en uno de baja se acelera, así que la tasa de prepago del escenario i es la tasa base por un multiplicador gamma de 0,8, 1,2, 0,8, 1,2, 0,8 y 1,2 para los seis choques en el orden paralelo al alza, paralelo a la baja, empinamiento, aplanamiento, corto al alza y corto a la baja, con tope en uno (<Ref>SRP31.119</Ref>, Tabla 5); el rescate anticipado de depósitos a plazo usa el multiplicador u de 1,2, 0,8, 0,8, 1,2, 1,2 y 0,8 en el mismo orden (<Ref>SRP31.125</Ref>, Tabla 6) <Cite id="srp31" />. Detrás de la tasa base están la mortalidad mensual simple y la tasa de prepago condicional, y la referencia PSA para hipotecas, 0,2 % en el mes 1 que sube 0,2 % por mes hasta 6 % en el mes 30 y plana después, escalada por el porcentaje PSA <Cite id="fuster2022" />. Los modelos de ejercicio racional de la opción, de riesgos proporcionales y de riesgos competitivos son las familias que un validador encuentra <Cite id="stanton1995" /> <Cite id="schwartztorous1989" /> <Cite id="deng2000" />; para las hipotecas chilenas, en su mayoría indexadas a UF y con comisiones de prepago, no se revisó una fuente primaria de calibración.</>}
      />
      <Equation
        tex={String.raw`\begin{aligned}CPR^{p}_{i,c} &= \min\bigl(1,\ \gamma_i\,CPR^{p}_{0,c}\bigr), \qquad CF^{p}_{i,c}(k) = CF^{s}_{i,c}(k) + CPR^{p}_{i,c}\,N^{p}_{i,c}(k-1)\\ TDRR^{p}_{i,c} &= \min\bigl(1,\ u_i\,TDRR^{p}_{0,c}\bigr), \qquad \mathrm{SMM} = 1 - (1-\mathrm{CPR})^{1/12}, \qquad \mathrm{CPR}_m = \tfrac{x}{100}\min(0.2\%\cdot m,\ 6\%)\end{aligned}`}
        caption={<T en={<>The behavioural multipliers (<Ref>SRP31.119</Ref> to <Ref>SRP31.126</Ref>; dossier 01, H.4, and dossier 05, D.4): CPR^p the conditional prepayment rate of portfolio p, gamma_i the multiplier of scenario i, CF^s the scheduled and N^p the outstanding notional of the previous bucket, so the prepaid flow is added to the scheduled one; TDRR the term-deposit early redemption rate and u_i its multiplier; SMM the single monthly mortality implied by an annual CPR; and the PSA curve at x percent PSA in month m. The PSA primary definition (SIFMA) was not retrieved and the formula follows secondary sources.</>} es={<>Los multiplicadores conductuales (<Ref>SRP31.119</Ref> a <Ref>SRP31.126</Ref>; dossier 01, H.4, y dossier 05, D.4): CPR^p la tasa de prepago condicional de la cartera p, gamma_i el multiplicador del escenario i, CF^s el flujo programado y N^p el nocional vigente del tramo anterior, de modo que el flujo prepagado se suma al programado; TDRR la tasa de rescate anticipado de depósitos a plazo y u_i su multiplicador; SMM la mortalidad mensual simple implícita en una CPR anual; y la curva PSA al x por ciento PSA en el mes m. La definición primaria de PSA (SIFMA) no se obtuvo y la fórmula sigue fuentes secundarias.</>} />}
      />
      <P
        en={<>The outlier test is the supervisor&apos;s reading of the result. The Basel framework requires at least one test comparing the largest ΔEVE under the six shocks with 15 % of Tier 1 capital, and any additional test must be at least as stringent (<Ref>SRP31.82</Ref> to <Ref>SRP31.83</Ref>); the supervisory actions on an outlier range from reducing exposure to raising capital (<Ref>SRP31.88</Ref>) <Cite id="srp31" />. In the EU the earnings test reads the one-year NII under the two parallel scenarios with a constant balance sheet and calls a decline of more than 5 % of Tier 1 large (Delegated Regulation 2024/856, <Ref>Article 5</Ref>) <Cite id="eu2024856" />. C14 draws the 15 % as a line against the ratio of every shock, with and without the behavioural deposit assumptions, so the question of whether the test would have fired is answered by where the point sits and not by a flag alone.</>}
        es={<>La prueba de valor atípico es la lectura del supervisor sobre el resultado. El marco de Basilea exige al menos una prueba que compare el mayor ΔEVE bajo los seis choques con el 15 % del capital de nivel 1, y toda prueba adicional debe ser al menos igual de exigente (<Ref>SRP31.82</Ref> a <Ref>SRP31.83</Ref>); las acciones supervisoras ante un valor atípico van de reducir la exposición a aumentar el capital (<Ref>SRP31.88</Ref>) <Cite id="srp31" />. En la UE la prueba de ganancias lee el NII a un año bajo los dos escenarios paralelos con balance constante y llama grande a una caída de más de 5 % del capital de nivel 1 (Reglamento Delegado 2024/856, <Ref>Artículo 5</Ref>) <Cite id="eu2024856" />. C14 dibuja el 15 % como una línea contra la razón de cada choque, con y sin los supuestos conductuales de depósitos, de modo que la pregunta de si la prueba se habría activado se responde por dónde queda el punto y no solo por una marca.</>}
      />
    </>
  );
}

export function DynamicsPart() {
  return (
    <>
      <P
        en={<>The behavioural models decide what the standardised caps leave open, and a validator checks them rung by rung. The static replicating portfolio chooses non-negative weights summing to one on rolling tranches so that the margin between the replicating yield and the client rate has minimal volatility, and its implied duration follows from the weights; the check is the stability of the weights across estimation windows <Cite id="bcbsd368" />. The contingent-claim valuation of the deposit franchise prices balances and client rates as functions of the short rate under the risk-neutral measure <Cite id="jarrow1998" />, and the three-factor model adds a stochastic volume factor, although the exact equations were not read in full text <Cite id="kalkbrener2004" />. The deposit beta, the pass-through of the market rate to the client rate, can be asymmetric in the direction of the move, and a low beta makes deposits behave like long-duration fixed-rate liabilities <Cite id="drechsler2021" />.</>}
        es={<>Los modelos conductuales deciden lo que los topes estandarizados dejan abierto, y un validador los revisa peldaño por peldaño. La cartera replicante estática elige pesos no negativos que suman uno sobre tramos rodantes de modo que el margen entre el rendimiento replicante y la tasa al cliente tenga volatilidad mínima, y su duración implícita sale de los pesos; la revisión es la estabilidad de los pesos entre ventanas de estimación <Cite id="bcbsd368" />. La valoración como derecho contingente de la franquicia de depósitos modela saldos y tasas al cliente como funciones de la tasa corta bajo la medida neutral al riesgo <Cite id="jarrow1998" />, y el modelo de tres factores agrega un factor estocástico de volumen, aunque las ecuaciones exactas no se leyeron en el texto completo <Cite id="kalkbrener2004" />. El beta de depósitos, el traspaso de la tasa de mercado a la tasa al cliente, puede ser asimétrico según la dirección del movimiento, y un beta bajo hace que los depósitos se comporten como pasivos a tasa fija de larga duración <Cite id="drechsler2021" />.</>}
      />
      <Equation
        tex={String.raw`m_t = \sum_{j} w_j\,\bar y_{j,t} - i_t, \quad w_j \ge 0,\ \sum_j w_j = 1, \quad \min_{w}\ \mathrm{Var}(m_t), \qquad \Delta i_t = \beta\,\Delta r_t`}
        caption={<T en={<>The two behavioural parameters that C14 and C15 report (dossier 05, D.3): w_j the weight of the rolling tranche of maturity m_j, ȳ_{'{j,t}'} its yield at time t, i_t the client rate, so m_t is the margin the replication tries to stabilise, and Var its variance over the estimation window; beta the pass-through of a change in the market rate r_t to the client rate, with one value for rises and another for falls. The weighted average maturity of a rolling tranche of maturity m is m over two.</>} es={<>Los dos parámetros conductuales que informan C14 y C15 (dossier 05, D.3): w_j el peso del tramo rodante de plazo m_j, ȳ_{'{j,t}'} su rendimiento en el tiempo t, i_t la tasa al cliente, de modo que m_t es el margen que la réplica intenta estabilizar, y Var su varianza en la ventana de estimación; beta el traspaso de un cambio de la tasa de mercado r_t a la tasa al cliente, con un valor para las alzas y otro para las bajas. El plazo promedio ponderado de un tramo rodante de plazo m es m sobre dos.</>} />}
      />
      <P
        en={<>Scenarios need curves. The Nelson-Siegel family fits a yield curve with a level, a slope and a curvature loading and one decay <Cite id="nelsonsiegel1987" />; Svensson adds a second hump term <Cite id="svensson1994" />; the dynamic version of Diebold and Li fixes the decay and models the three coefficients as autoregressive factors, which gives a forecasting model for rate scenarios <Cite id="dieboldli2006" />. The decay of 0.0609 per month, in months, puts the maximum of the curvature loading near 29 months, a figure that was recomputed in this build because the first reading said 30. Interpolation choices change forward curves materially <Cite id="hagan2006" />. For the distribution of earnings and value the scenarios are the deterministic shocks, historical simulation of the factor changes, and a Hull-White one-factor or Vasicek Monte Carlo, the Gaussian model of Vasicek allowing negative rates but not fitting today&apos;s curve <Cite id="vasicek1977" />.</>}
        es={<>Los escenarios necesitan curvas. La familia de Nelson-Siegel ajusta una curva de rendimientos con una carga de nivel, una de pendiente y una de curvatura y un decaimiento <Cite id="nelsonsiegel1987" />; Svensson agrega un segundo término de joroba <Cite id="svensson1994" />; la versión dinámica de Diebold y Li fija el decaimiento y modela los tres coeficientes como factores autorregresivos, lo que da un modelo de pronóstico para escenarios de tasas <Cite id="dieboldli2006" />. El decaimiento de 0,0609 por mes, con plazos en meses, pone el máximo de la carga de curvatura cerca de los 29 meses, una cifra que se recalculó en esta construcción porque la primera lectura decía 30. Las elecciones de interpolación cambian de manera material las curvas a plazo <Cite id="hagan2006" />. Para la distribución de ganancias y valor los escenarios son los choques determinísticos, la simulación histórica de los cambios de factores, y un Monte Carlo de Hull-White de un factor o de Vasicek, con el modelo gaussiano de Vasicek que admite tasas negativas pero no ajusta la curva de hoy <Cite id="vasicek1977" />.</>}
      />
      <Equation
        tex={String.raw`y(m) = \beta_0 + \beta_1\,\frac{1 - e^{-\lambda m}}{\lambda m} + \beta_2\left(\frac{1 - e^{-\lambda m}}{\lambda m} - e^{-\lambda m}\right), \qquad \mathrm{EaR}_q = \mathrm{NII}_0 - Q_{1-q}(\mathrm{NII}), \quad \mathrm{EVaR}_q = \mathrm{EVE}_0 - Q_{1-q}(\mathrm{EVE})`}
        caption={<T en={<>The curve and the distribution measures (dossier 05, D.5 and D.6): y(m) the zero yield at maturity m, β_0, β_1 and β_2 the level, slope and curvature coefficients and λ = 1/τ the decay (0.0609 per month in the dynamic version); NII_0 and EVE_0 the base values, Q_{'{1-q}'} the lower quantile of the simulated NII or EVE at confidence level q (95 and 99 percent). EaR and EVaR are loss-positive, and every document gives the number of paths, the seed and the Monte Carlo standard error of both.</>} es={<>La curva y las medidas de distribución (dossier 05, D.5 y D.6): y(m) el rendimiento cero al plazo m, β_0, β_1 y β_2 los coeficientes de nivel, pendiente y curvatura y λ = 1/τ el decaimiento (0,0609 por mes en la versión dinámica); NII_0 y EVE_0 los valores base, Q_{'{1-q}'} el cuantil inferior del NII o del EVE simulado al nivel de confianza q (95 y 99 por ciento). El EaR y el EVaR son positivos en pérdida, y cada documento da el número de trayectorias, la semilla y el error estándar de Monte Carlo de ambos.</>} />}
      />
      <Figure caption={t2('The three Nelson-Siegel factor loadings against maturity for the decay of the dynamic version: the level loading is one at every maturity, the slope loading decays from one, and the curvature loading rises from zero to a maximum near 29 months and decays.', 'Las tres cargas de factor de Nelson-Siegel contra el plazo para el decaimiento de la versión dinámica: la carga de nivel es uno en todo plazo, la de pendiente decae desde uno, y la de curvatura sube desde cero hasta un máximo cerca de 29 meses y decae.')}>
        <LoadingsFigure />
      </Figure>
      <P
        en={<>The dynamic simulation projects net interest income month by month over twelve to thirty-six months: the existing book runs off by its contractual and behavioural cash flows, new business replaces it under a stated balance-sheet assumption, constant or with a growth plan, new and repricing volumes are priced from the scenario curve plus margins, and administered rates follow the market rate through the deposit beta. NII is compared across the base path and the regulatory parallel shocks. C14 states that assumption, the betas and the horizon next to every projection and compares the NII projected from the first valuation date with the NII the call reports later realised, which is the out-of-sample check of the method. The lessons of the 2023 failure become tests <Cite id="fedsvb2023" />: the supervisor&apos;s review found that the bank had breached its long-term interest rate risk limits on and off since 2017 and then adopted assumptions on the duration of its deposits that addressed the breach and not the risk. A validation test therefore flags any change in the behavioural parameters that coincides with a limit breach, and every result is reported with and without the behavioural assumptions.</>}
        es={<>La simulación dinámica proyecta el margen financiero neto mes a mes sobre doce a treinta y seis meses: la cartera existente se extingue por sus flujos contractuales y conductuales, el negocio nuevo la reemplaza bajo un supuesto de balance declarado, constante o con un plan de crecimiento, los volúmenes nuevos y los que reprecian se valoran con la curva del escenario más los márgenes, y las tasas administradas siguen la tasa de mercado a través del beta de depósitos. El NII se compara entre la trayectoria base y los choques paralelos regulatorios. C14 declara ese supuesto, los betas y el horizonte junto a cada proyección y compara el NII proyectado desde la primera fecha de valoración con el NII que los reportes de condición realizaron después, que es la verificación fuera de muestra del método. Las lecciones de la quiebra de 2023 se vuelven pruebas <Cite id="fedsvb2023" />: la revisión del supervisor halló que el banco había excedido sus límites de riesgo de tasa de interés de largo plazo de manera intermitente desde 2017 y luego adoptó supuestos sobre la duración de sus depósitos que atendían el exceso y no el riesgo. Una prueba de validación marca entonces todo cambio de los parámetros conductuales que coincida con un exceso de límite, y todo resultado se informa con y sin los supuestos conductuales.</>}
      />
    </>
  );
}

export function ChilePart() {
  return (
    <>
      <P
        en={<>Chile adds a unit of account and a risk. The Unidad de Fomento is an index of adjustment (reajustabilidad) that the Banco Central de Chile calculates and authorises for money-credit operations in national currency, and it is adjusted daily from the tenth day of a month to the ninth of the next at the geometric rate of the previous month&apos;s change in the consumer price index <Cite id="bcchuf" />. A UF-denominated balance therefore carries a deterministic, one-month-lagged inflation accrual, and Chilean net interest income is the interest margin plus the indexation margin, the reajustes. A bank with a net long UF position, UF assets such as mortgages funded partly by CLP liabilities, earns reajustes when inflation is high, so IRRBB in Chile has a separate indexation risk: the standard defines the risk of reajustabilidad as the exposure to losses from adverse changes in the units or indices of adjustment defined in national currency <Cite id="ran2113" />. The compendium does not treat UF indexation as an embedded derivative <Cite id="cmfcncb" />.</>}
        es={<>Chile agrega una unidad de cuenta y un riesgo. La Unidad de Fomento es un índice de reajustabilidad que el Banco Central de Chile calcula y autoriza para las operaciones de crédito de dinero en moneda nacional, y se reajusta diariamente desde el día diez de un mes hasta el nueve del siguiente a la tasa geométrica de la variación del índice de precios al consumidor del mes anterior <Cite id="bcchuf" />. Un saldo en UF lleva entonces un devengo de inflación determinístico, rezagado un mes, y el margen financiero neto chileno es el margen de intereses más el margen de reajustes. Un banco con posición neta larga en UF, activos en UF como hipotecarios financiados en parte con pasivos en CLP, gana reajustes cuando la inflación es alta, de modo que el IRRBB en Chile tiene un riesgo de reajustabilidad separado: el estándar define el riesgo de reajustabilidad como la exposición a pérdidas ocasionadas por cambios adversos en las unidades o índices de reajustabilidad definidos en moneda nacional <Cite id="ran2113" />. El compendio no trata la indexación en UF como un derivado incorporado <Cite id="cmfcncb" />.</>}
      />
      <Equation
        tex={String.raw`f = \Bigl(1 + \tfrac{\Delta IPC_{t-1}}{100}\Bigr)^{1/D}, \qquad UF_d = UF_0\,\Bigl(1 + \tfrac{\Delta IPC_{t-1}}{100}\Bigr)^{d/D}, \quad d = 1,\dots,D`}
        caption={<T en={<>The daily accrual of the UF (BCCh methodology note; dossier 03, F.1): D the number of days from day 10 of month t to day 9 of month t + 1, ΔIPC_{'{t-1}'} the previous calendar month&apos;s change of the consumer price index in percent, UF_0 the last published value and UF_d the value d days later, rounded to two decimals, published in the Diario Oficial by day 9 and never revised. C15 converts the UF leg to CLP at the value of one stated date.</>} es={<>El devengo diario de la UF (nota metodológica del BCCh; dossier 03, F.1): D el número de días desde el día 10 del mes t hasta el día 9 del mes t + 1, ΔIPC_{'{t-1}'} la variación del índice de precios al consumidor del mes calendario anterior en porcentaje, UF_0 el último valor publicado y UF_d el valor d días después, redondeado a dos decimales, publicado en el Diario Oficial el día 9 y nunca revisado. C15 convierte el tramo UF a CLP al valor de una fecha declarada.</>} />}
      />
      <P
        en={<>The standard measure of RAN 21-13 Annex 1 follows the Basel structure with Chilean choices <Cite id="ran2113" />. It defines ΔNII, with a constant balance and the repricing flows up to one year, and ΔEVE, with a run-off balance and all repricing flows, by each significant currency, and it treats every local currency flow adjusted by an index as one currency, UR, which is the CLF. The 19 bands and their midpoints are the Basel ones, the stable share and maturity caps for non-maturity deposits are 90 % and 5 years for retail with an operational relationship, 70 % and 4.5 years for retail without one, and 50 % and 4 years for wholesale, with at least five years of data to split stable from non-stable, and the prepayment and redemption multipliers are the same gamma and u. The shock sizes of the Annex are 300, 400 and 200 bp for CLP, 300 bp for the UR delta NII and 200, 250 and 150 bp for the UR delta EVE, and the floors are -2 % for UR rates and 0 % for the others.</>}
        es={<>La medida estándar del RAN 21-13 Anexo 1 sigue la estructura de Basilea con decisiones chilenas <Cite id="ran2113" />. Define el ΔNII, con balance constante y los flujos de reprecio hasta un año, y el ΔEVE, con balance en extinción y todos los flujos de reprecio, por cada moneda significativa, y trata todo flujo en moneda local reajustado por un índice como una sola moneda, UR, que es la CLF. Las 19 bandas y sus puntos medios son los de Basilea, los topes de proporción estable y plazo para los depósitos sin vencimiento son 90 % y 5 años para minoristas con relación operacional, 70 % y 4,5 años para minoristas sin ella, y 50 % y 4 años para mayoristas, con al menos cinco años de datos para separar lo estable de lo no estable, y los multiplicadores de prepago y rescate son los mismos gamma y u. Los tamaños de choque del Anexo son 300, 400 y 200 pb para CLP, 300 pb para el delta NII de UR y 200, 250 y 150 pb para el delta EVE de UR, y los pisos son -2 % para las tasas UR y 0 % para las demás.</>}
      />
      <Equation
        tex={String.raw`\Delta \mathrm{NII}_{i,c} = \sum_{k=1}^{6} CF_{i,c}(t_k)\bigl(r_{0,c}(t_k) - r_{i,c}(t_k)\bigr)(1 - t_k), \qquad \Delta \mathrm{NII} = \max_{i\in\{1,2\}}\Bigl\{\sum_{c\notin\{\mathrm{CLP},\mathrm{CLF}\}}\max\{\Delta \mathrm{NII}_{i,c};0\} + \Delta \mathrm{NII}_{i,(\mathrm{CLP}+\mathrm{CLF})}\Bigr\} + 2.5\%\cdot\lvert PN_{UR}\rvert`}
        caption={<T en={<>The Annex 1 delta NII (RAN 21-13 Annex 1, sheets 10 to 12; dossier 03, F.2): CF_{'{i,c}'}(t_k) the net repricing flow of currency c in bucket k under parallel scenario i (1 up, 2 down), r_0 and r_i the base and shocked rates, so each flow earns the part of the year left after it reprices, PN_UR the net UF position when the functional currency is CLP, and 2.5 % of its absolute value the standardised indexation charge, an implied 2.5 percent inflation surprise. CLP and CLF form one pair with a single 300 bp shock: if the two deltas have the same sign the pair is the sum of their positive parts, and otherwise half of the CLP delta is offset against the CLF one, and the reverse, floored at zero. Delta EVE takes the same pair rule over the six shocks and has no indexation charge.</>} es={<>El delta NII del Anexo 1 (RAN 21-13 Anexo 1, hojas 10 a 12; dossier 03, F.2): CF_{'{i,c}'}(t_k) el flujo neto de reprecio de la moneda c en el tramo k bajo el escenario paralelo i (1 al alza, 2 a la baja), r_0 y r_i las tasas base y con choque, de modo que cada flujo gana la parte del año que queda después de repreciar, PN_UR la posición neta en UF cuando la moneda funcional es CLP, y el 2,5 % de su valor absoluto el cargo estándar por reajustabilidad, una sorpresa de inflación implícita de 2,5 por ciento. CLP y CLF forman un par con un solo choque de 300 pb: si los dos deltas tienen el mismo signo el par es la suma de sus partes positivas, y si no, se compensa la mitad del delta CLP contra el de CLF, y a la inversa, con piso en cero. El delta EVE toma la misma regla de par sobre los seis choques y no tiene cargo por reajustabilidad.</>} />}
      />
      <Figure caption={t2('How the delta NII of Annex 1 is built: the CLP leg and the UR leg are paired with the 50 percent offset, the larger of the two parallel shocks is the rate result, and the indexation charge, derived from the net UF position, is added apart; C15 draws the two parts separately.', 'Cómo se construye el delta NII del Anexo 1: el tramo CLP y el tramo UR se emparejan con la compensación de 50 por ciento, el mayor de los dos choques paralelos es el resultado de tasa, y el cargo por reajustabilidad, derivado de la posición neta en UF, se suma aparte; C15 dibuja las dos partes por separado.')}>
        <AnnexFigure />
      </Figure>
      <P
        en={<>A bank is prioritised when any of three tests is breached: ΔNII above 5 % of Tier 1, ΔEVE above 15 % of Tier 1, or ΔNII above 18 % of the cumulative twelve-month net interest and indexation margin. Prioritisation brings a detailed review and may bring a capital requirement, and internal IRRBB models need no supervisory approval but are examined in the supervisory review <Cite id="ran2113" />. The board sets annual limits on ΔNII as a share of the margin and on ΔEVE as a share of Tier 1. C15 shows the three ratios against their three thresholds as lines, the effect of every binding floor on each leg and shock, the CLP and UR legs apart, the 50 % offset on and off and the indexation charge beside the rate result and never inside it, with a CPI-surprise variant that applies a stated inflation surprise to the same net UF position.</>}
        es={<>Un banco es priorizado cuando se supera cualquiera de tres pruebas: ΔNII sobre 5 % del capital de nivel 1, ΔEVE sobre 15 % del capital de nivel 1, o ΔNII sobre 18 % del margen neto de intereses y reajustes acumulado de doce meses. La priorización trae una revisión detallada y puede traer un requerimiento de capital, y los modelos internos de IRRBB no requieren aprobación supervisora pero se examinan en la revisión supervisora <Cite id="ran2113" />. El directorio fija límites anuales para el ΔNII como parte del margen y para el ΔEVE como parte del capital de nivel 1. C15 muestra las tres razones contra sus tres umbrales como líneas, el efecto de cada piso que rige en cada tramo y choque, los tramos CLP y UR por separado, la compensación de 50 % activa e inactiva y el cargo por reajustabilidad junto al resultado de tasa y nunca dentro de él, con una variante de sorpresa de IPC que aplica una sorpresa de inflación declarada a la misma posición neta en UF.</>}
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
      title={{ en: 'Interest rate risk in the banking book: EVE, NII, behaviour and the UF', es: 'Riesgo de tasa de interés en el libro de banca: EVE, NII, conducta y la UF' }}
      refs={['srp31', 'bcbsd368', 'bcbsd578', 'dis70', 'eu2024856', 'fuster2022', 'stanton1995', 'schwartztorous1989', 'deng2000', 'jarrow1998', 'kalkbrener2004', 'drechsler2021', 'nelsonsiegel1987', 'svensson1994', 'dieboldli2006', 'hagan2006', 'vasicek1977', 'fedsvb2023', 'bcchuf', 'ran2113', 'cmfcncb']}
    >
      <SubTabs
        ariaLabel={t('Parts of the topic', 'Partes del tema')}
        tabs={[
          { id: 'measures', label: t('Measures and shocks', 'Medidas y choques'), content: <MeasuresPart /> },
          { id: 'eve', label: t('Standardised EVE', 'EVE estandarizado'), content: <EvePart /> },
          { id: 'dynamics', label: t('Behaviour and dynamics', 'Conducta y dinámica'), content: <DynamicsPart /> },
          { id: 'chile', label: t('Chile: the UF and Annex 1', 'Chile: la UF y el Anexo 1'), content: <ChilePart /> },
        ]}
      />
      <Callout variant="honest" title={t('What is exact, what is a choice and what these views are not', 'Qué es exacto, qué es una decisión y qué no son estas vistas')}>
        <T
          en={<>The shapes, the bucket midpoints, the caps, the multipliers, the 15 % test and the Annex 1 formulas are exact as transcribed from the sources, and the engine reproduces the golden values of the standard and of the Annex as tests. The behavioural assumptions are not the standard&apos;s: the core shares, the replicating weights, the betas and the prepayment rates are stated choices, the PSA formula follows secondary sources, the exact equations of the three-factor deposit model and a Chilean prepayment calibration were not read, and whether Annex 1 applies the pre-shock clause of the floor to the UR rates is unverified. C14 stands on the real aggregates of the FDIC call reports and on synthetic behaviour, and C15 on a synthetic bank calibrated to CMF aggregates with Banco Central de Chile curves that Contraste fits, an adaptation under the BCCh terms; until the BCCh account exists C15 shows its fixtures. Neither case is a supervisory submission or an approved internal model, no number describes any bank, and the schematics above are illustrative.</>}
          es={<>Las formas, los puntos medios de los tramos, los topes, los multiplicadores, la prueba de 15 % y las fórmulas del Anexo 1 son exactos tal como se transcribieron de las fuentes, y el motor reproduce como pruebas los valores de referencia del estándar y del Anexo. Los supuestos conductuales no son los del estándar: las partes estables, los pesos de la réplica, los betas y las tasas de prepago son decisiones declaradas, la fórmula PSA sigue fuentes secundarias, las ecuaciones exactas del modelo de depósitos de tres factores y una calibración chilena de prepago no se leyeron, y si el Anexo 1 aplica la cláusula de tasa previa al choque al piso de las tasas UR no está verificado. C14 se apoya en los agregados reales de los reportes de condición de la FDIC y en conducta sintética, y C15 en un banco sintético calibrado a agregados de la CMF con curvas del Banco Central de Chile que Contraste ajusta, una adaptación bajo los términos del BCCh; mientras no exista la cuenta del BCCh C15 muestra sus ejemplos. Ningún caso es una presentación supervisora ni un modelo interno aprobado, ningún número describe a un banco, y los esquemas de arriba son ilustrativos.</>}
        />
      </Callout>
    </DocSection>
  );
}

export const methodologySection: MethodologySection = {
  id: 'irrbb',
  group: 'tests',
  order: 120,
  title: { en: 'Interest rate risk (IRRBB)', es: 'Riesgo de tasa (IRRBB)' },
  Body,
};
