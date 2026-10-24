// The schematics of the documentation pages (ADR-0017 section 2.1: a method names a figure). Each is a small inline SVG
// on the shell's `dg-*` tokens, labelled in both languages, and says it is illustrative: the values drawn are shapes
// that show the idea, never a result of the product. Placed inside a `Figure` with a caption by the page.
import type { ReactNode } from 'react';
import { useT } from '../content/bi';

/** SVG path coordinates rounded to a tenth of a pixel (geometry, not a displayed number). */
const r1 = (x: number): string => String(Math.round(x * 10) / 10);

const W = 480;
const H = 250;
const X0 = 56;
const X1 = 456;
const Y0 = 206;
const Y1 = 24;

function Frame({ label, children }: { label: string; children: ReactNode }) {
  return (
    <svg className="ct-docfig" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}>
      {children}
    </svg>
  );
}

const px = (u: number) => X0 + u * (X1 - X0);
const py = (v: number) => Y0 - v * (Y0 - Y1);
const path = (pts: Array<[number, number]>) => pts.map(([u, v], i) => `${i ? 'L' : 'M'}${r1(px(u))} ${r1(py(v))}`).join(' ');
const range = (n: number) => Array.from({ length: n + 1 }, (_, i) => i / n);

function Axes({ x, y }: { x: string; y: string }) {
  return (
    <>
      <line className="dg-axis" x1={X0} y1={Y0} x2={X1} y2={Y0} />
      <line className="dg-axis" x1={X0} y1={Y0} x2={X0} y2={Y1} />
      <text className="dg-axis-label" x={(X0 + X1) / 2} y={Y0 + 32} textAnchor="middle">{x}</text>
      <text className="dg-axis-label" x={14} y={(Y0 + Y1) / 2} textAnchor="middle" transform={`rotate(-90 14 ${(Y0 + Y1) / 2})`}>{y}</text>
    </>
  );
}

const Note = ({ children }: { children: string }) => (
  <text className="dg-note" x={X1} y={Y1 - 8} textAnchor="end">{children}</text>
);

/** The ROC curve of a score and the area under it. */
export function RocFigure() {
  const t = useT();
  const curve = range(40).map((u): [number, number] => [u, u ** 0.42]);
  return (
    <Frame label={t('An illustrative ROC curve with the area under it', 'Una curva ROC ilustrativa con el área bajo ella')}>
      <Axes x={t('False positive rate', 'Tasa de falsos positivos')} y={t('True positive rate', 'Tasa de verdaderos positivos')} />
      <path className="dg-fill-accent" d={`${path(curve)} L${px(1)} ${py(0)} Z`} />
      <path className="dg-curve" d={path(curve)} />
      <path className="dg-curve-faint" d={path([[0, 0], [1, 1]])} />
      <text className="dg-axis-label" x={px(0.56)} y={py(0.34)}>{t('AUC: the shaded area', 'AUC: el área sombreada')}</text>
      <text className="dg-axis-label" x={px(0.52)} y={py(0.43) - 10} transform={`rotate(-30 ${px(0.52)} ${py(0.43)})`}>{t('AUC = 0.5: no ranking', 'AUC = 0,5: sin ordenamiento')}</text>
      <Note>{t('Illustrative curve', 'Curva ilustrativa')}</Note>
    </Frame>
  );
}

/** The reliability diagram: observed against predicted default rate. */
export function ReliabilityFigure() {
  const t = useT();
  const bins = [0.1, 0.3, 0.5, 0.7, 0.9];
  const observed = [0.06, 0.24, 0.5, 0.74, 0.95];
  return (
    <Frame label={t('An illustrative reliability diagram', 'Un diagrama de confiabilidad ilustrativo')}>
      <Axes x={t('Predicted PD (bin mean)', 'PD predicha (media del tramo)')} y={t('Observed default rate', 'Tasa de incumplimiento observada')} />
      <path className="dg-curve-faint" d={path([[0, 0], [1, 1]])} />
      <path className="dg-curve" d={path(bins.map((b, i): [number, number] => [b, observed[i]]))} />
      {bins.map((b, i) => (
        <circle key={b} className="dg-node" cx={px(b)} cy={py(observed[i])} r={5} />
      ))}
      <text className="dg-axis-label" x={px(0.5)} y={py(0.5) - 56} textAnchor="middle">{t('Perfect calibration: the diagonal', 'Calibración perfecta: la diagonal')}</text>
      <Note>{t('Illustrative bins', 'Tramos ilustrativos')}</Note>
    </Frame>
  );
}

/** The population stability index: the share of the population by score bin, at development and now. */
export function PsiFigure() {
  const t = useT();
  const dev = [0.1, 0.2, 0.4, 0.2, 0.1];
  const now = [0.05, 0.15, 0.35, 0.25, 0.2];
  const slot = (X1 - X0) / dev.length;
  const h = (v: number) => v * 2 * (Y0 - Y1);
  return (
    <Frame label={t('An illustrative comparison of two score distributions', 'Una comparación ilustrativa de dos distribuciones de puntaje')}>
      <Axes x={t('Score bin', 'Tramo de puntaje')} y={t('Share of the population', 'Fracción de la población')} />
      {dev.map((d, i) => (
        <g key={i}>
          <rect className="dg-bar" x={X0 + i * slot + slot * 0.12} y={Y0 - h(d)} width={slot * 0.36} height={h(d)} />
          <rect className="dg-bar-2" x={X0 + i * slot + slot * 0.5} y={Y0 - h(now[i])} width={slot * 0.36} height={h(now[i])} />
          <text className="dg-bar-label" x={X0 + i * slot + slot / 2} y={Y0 + 16} textAnchor="middle">{i + 1}</text>
        </g>
      ))}
      <rect className="dg-bar" x={X0 + 14} y={Y1 - 4} width={12} height={12} />
      <text className="dg-bar-label" x={X0 + 32} y={Y1 + 6}>{t('At development', 'En el desarrollo')}</text>
      <rect className="dg-bar-2" x={X0 + 150} y={Y1 - 4} width={12} height={12} />
      <text className="dg-bar-label" x={X0 + 168} y={Y1 + 6}>{t('Now', 'Ahora')}</text>
    </Frame>
  );
}

/** Size and power: the rejection rate of a test as a defect grows. */
export function PowerFigure() {
  const t = useT();
  const alpha = 0.05;
  const curve = range(40).map((u): [number, number] => [u, alpha + (1 - alpha) * (1 - Math.exp(-4.2 * u * u))]);
  return (
    <Frame label={t('An illustrative power curve', 'Una curva de potencia ilustrativa')}>
      <Axes x={t('Size of the planted defect', 'Tamaño del defecto plantado')} y={t('Rejection rate', 'Tasa de rechazo')} />
      <path className="dg-asymptote" fill="none" d={path([[0, alpha], [1, alpha]])} />
      <path className="dg-curve" d={path(curve)} />
      <text className="dg-axis-label" x={X1} y={py(alpha) - 6} textAnchor="end">{t('level α: the size, with no defect', 'nivel α: el tamaño, sin defecto')}</text>
      <text className="dg-axis-label" x={px(0.5)} y={py(0.72)}>{t('power: the rate with a defect', 'potencia: la tasa con defecto')}</text>
      <Note>{t('Illustrative curve', 'Curva ilustrativa')}</Note>
    </Frame>
  );
}

/** The weight of evidence of the bins of one variable. */
export function ScorecardFigure() {
  const t = useT();
  const woe = [-0.9, -0.35, 0.1, 0.55, 1.0];
  const slot = (X1 - X0) / woe.length;
  const mid = (Y0 + Y1) / 2;
  const scale = (Y0 - Y1) / 2.4;
  return (
    <Frame label={t('An illustrative weight of evidence by bin', 'Un peso de evidencia ilustrativo por tramo')}>
      <line className="dg-axis" x1={X0} y1={Y0} x2={X0} y2={Y1} />
      <line className="dg-axis" x1={X0} y1={mid} x2={X1} y2={mid} />
      <text className="dg-axis-label" x={(X0 + X1) / 2} y={Y0 + 32} textAnchor="middle">{t('Bins of one variable, from the riskiest to the safest', 'Tramos de una variable, del más riesgoso al más seguro')}</text>
      <text className="dg-axis-label" x={14} y={mid} textAnchor="middle" transform={`rotate(-90 14 ${mid})`}>{t('Weight of evidence', 'Peso de evidencia')}</text>
      {woe.map((w, i) => (
        <g key={i}>
          <rect className={w < 0 ? 'dg-bar-2' : 'dg-bar'} x={X0 + i * slot + slot * 0.2} y={w < 0 ? mid : mid - w * scale} width={slot * 0.6} height={Math.abs(w) * scale} />
          <text className="dg-bar-label" x={X0 + i * slot + slot / 2} y={Y0 + 16} textAnchor="middle">{i + 1}</text>
        </g>
      ))}
      <Note>{t('Illustrative values', 'Valores ilustrativos')}</Note>
    </Frame>
  );
}

/** One shape function of an additive model: the contribution of a variable, one step per bin. */
export function ShapeFigure() {
  const t = useT();
  const steps = [-0.7, -0.45, -0.2, -0.05, 0.1, 0.35, 0.6, 0.8];
  const slot = (X1 - X0) / steps.length;
  const mid = (Y0 + Y1) / 2;
  const scale = (Y0 - Y1) / 2.2;
  const d = steps.map((s, i) => `${i ? 'L' : 'M'}${r1(X0 + i * slot)} ${r1(mid - s * scale)} L${r1(X0 + (i + 1) * slot)} ${r1(mid - s * scale)}`).join(' ');
  return (
    <Frame label={t('An illustrative shape function of an explainable boosting machine', 'Una función de forma ilustrativa de una explainable boosting machine')}>
      <line className="dg-axis" x1={X0} y1={Y0} x2={X0} y2={Y1} />
      <line className="dg-grid" x1={X0} y1={mid} x2={X1} y2={mid} />
      <text className="dg-axis-label" x={(X0 + X1) / 2} y={Y0 + 32} textAnchor="middle">{t('Value of one variable (64 bins in the case)', 'Valor de una variable (64 tramos en el caso)')}</text>
      <text className="dg-axis-label" x={14} y={mid} textAnchor="middle" transform={`rotate(-90 14 ${mid})`}>{t('Contribution to the log-odds', 'Contribución a las log-odds')}</text>
      <path className="dg-curve" d={d} />
      <Note>{t('Illustrative: one step per bin', 'Ilustrativo: un escalón por tramo')}</Note>
    </Frame>
  );
}

/** The model ladder: the same split and the same tests for every rung. */
export function LadderFigure() {
  const t = useT();
  const rungs = [
    [t('P1 Scorecard', 'P1 Scorecard'), t('WoE and logistic', 'WoE y logística')],
    [t('P3 EBM', 'P3 EBM'), t('additive, pairs', 'aditivo, pares')],
    [t('P4 Boosting', 'P4 Boosting'), t('monotone trees', 'árboles monótonos')],
    [t('P5 TabPFN', 'P5 TabPFN'), t('in-context', 'en contexto')],
  ];
  const w = 96;
  const gap = 18;
  return (
    <Frame label={t('The model ladder, from the scorecard to the foundation model', 'La escalera de modelos, de la scorecard al modelo fundacional')}>
      {rungs.map(([name, sub], i) => (
        <g key={name}>
          <rect className={i === 0 ? 'dg-box accent' : 'dg-box'} x={X0 - 30 + i * (w + gap)} y={150 - i * 28} width={w} height={54} rx={4} />
          <text className="dg-box-title" x={X0 - 30 + i * (w + gap) + w / 2} y={174 - i * 28} textAnchor="middle">{name}</text>
          <text className="dg-box-sub" x={X0 - 30 + i * (w + gap) + w / 2} y={192 - i * 28} textAnchor="middle">{sub}</text>
        </g>
      ))}
      <text className="dg-axis-label" x={W / 2} y={Y0 + 36} textAnchor="middle">{t('One split, one battery of tests, every rung', 'Una partición, una batería de pruebas, cada peldaño')}</text>
      <text className="dg-axis-label" x={X0 - 30} y={Y1 + 4}>{t('more flexible, harder to audit', 'más flexible, más difícil de auditar')}</text>
    </Frame>
  );
}

/** A rating chain: grades that move among themselves, and default as the absorbing state. */
export function ChainFigure() {
  const t = useT();
  const nodes = ['A', 'B', 'C', t('D', 'D')];
  const xs = nodes.map((_, i) => X0 + 36 + i * 120);
  const y = 120;
  return (
    <Frame label={t('An illustrative rating chain with default as the absorbing state', 'Una cadena de calificaciones ilustrativa con el incumplimiento como estado absorbente')}>
      <defs>
        <marker id="ct-chain-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path className="dg-arrowhead" d="M0 0 L10 5 L0 10 z" />
        </marker>
      </defs>
      {nodes.slice(0, 3).map((_, i) => (
        <path key={i} className="dg-edge" d={`M${xs[i] + 22} ${y - 8} Q${(xs[i] + xs[i + 1]) / 2} ${y - 52} ${xs[i + 1] - 22} ${y - 8}`} markerEnd="url(#ct-chain-arrow)" />
      ))}
      {nodes.slice(1, 3).map((_, i) => (
        <path key={i} className="dg-edge" d={`M${xs[i + 1] - 22} ${y + 8} Q${(xs[i] + xs[i + 1]) / 2} ${y + 52} ${xs[i] + 22} ${y + 8}`} markerEnd="url(#ct-chain-arrow)" />
      ))}
      {nodes.map((n, i) => (
        <g key={n}>
          <circle className={i === 3 ? 'dg-box accent' : 'dg-node'} cx={xs[i]} cy={y} r={22} />
          <text className="dg-node-label" x={xs[i]} y={y + 4} textAnchor="middle">{n}</text>
        </g>
      ))}
      <text className="dg-edge-label" x={(xs[0] + xs[1]) / 2} y={y - 58} textAnchor="middle">p<sub>ij</sub></text>
      <text className="dg-axis-label" x={W / 2} y={Y0 + 36} textAnchor="middle">{t('Grades move among themselves; default (D) never leaves', 'Los grados se mueven entre sí; el incumplimiento (D) nunca sale')}</text>
      <Note>{t('Illustrative chain', 'Cadena ilustrativa')}</Note>
    </Frame>
  );
}

/** Time homogeneity: yearly estimates of one transition probability around the pooled one. */
export function HomogeneityFigure() {
  const t = useT();
  const years = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9];
  const est = [0.34, 0.4, 0.36, 0.52, 0.66, 0.48, 0.38, 0.35, 0.41];
  return (
    <Frame label={t('Illustrative yearly estimates of one transition probability and the pooled estimate', 'Estimaciones anuales ilustrativas de una probabilidad de transición y la estimación agrupada')}>
      <Axes x={t('Year of the cohort', 'Año de la cohorte')} y={t('Estimate of one pᵢⱼ', 'Estimación de un pᵢⱼ')} />
      <path className="dg-asymptote" fill="none" d={path([[0, 0.43], [1, 0.43]])} />
      <path className="dg-curve" d={path(years.map((u, i): [number, number] => [u, est[i]]))} />
      {years.map((u, i) => (
        <circle key={u} className="dg-node" cx={px(u)} cy={py(est[i])} r={4} />
      ))}
      <text className="dg-axis-label" x={px(0.02)} y={py(0.43) - 6}>{t('pooled: the same matrix every year', 'agrupada: la misma matriz cada año')}</text>
      <Note>{t('Illustrative estimates', 'Estimaciones ilustrativas')}</Note>
    </Frame>
  );
}

/** The leakage-safe protocol: what each part of the data may be used for, and the forbidden path. */
export function ProtocolFigure() {
  const t = useT();
  const parts = [
    { x: 8, w: 236, cls: 'dg-box accent', title: t('Training slice', 'Tajada de entrenamiento'), sub: t('binning, fits, cross-validation', 'tramado, ajustes, validación cruzada') },
    { x: 252, w: 104, cls: 'dg-box', title: t('Calibration', 'Calibración'), sub: t('calibration map', 'mapa de calib.') },
    { x: 364, w: 108, cls: 'dg-box good', title: t('Locked holdout', 'Reservada'), sub: t('tests, once', 'pruebas, una vez') },
  ];
  return (
    <Frame label={t('The leakage-safe protocol: training, calibration and a locked holdout, and the forbidden path', 'El protocolo sin fugas: entrenamiento, calibración y una muestra reservada bloqueada, y el camino prohibido')}>
      {parts.map((p) => (
        <g key={p.title}>
          <rect className={p.cls} x={p.x} y={60} width={p.w} height={64} rx={4} />
          <text className="dg-box-title" x={p.x + p.w / 2} y={86} textAnchor="middle">{p.title}</text>
          <text className="dg-box-sub" x={p.x + p.w / 2} y={106} textAnchor="middle">{p.sub}</text>
        </g>
      ))}
      <path className="dg-asymptote" fill="none" d={`M418 130 C 418 190, 126 190, 126 130`} />
      <text className="dg-axis-label" x={W / 2} y={196} textAnchor="middle">{t('forbidden: choosing or fitting with the holdout', 'prohibido: elegir o ajustar con la muestra reservada')}</text>
      <text className="dg-axis-label" x={W / 2} y={Y0 + 36} textAnchor="middle">{t('30% locked holdout; 20% of the rest for calibration', '30% de muestra reservada; 20% del resto para calibración')}</text>
    </Frame>
  );
}
