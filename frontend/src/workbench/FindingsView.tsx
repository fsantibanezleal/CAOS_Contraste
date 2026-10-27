// The Findings group: what the validation found, with its severity, its status and the evidence behind it. Severity
// follows the case's stated policy (the level of the PD weighs more than its fit across the range); a finding cites
// the tests that evidence it, a contract-1 rule of the inputs, or a design limit.
import { PlotCard, Verdict, ViewsRow, formatNumber, pick, useShellLang, useWorkbenchState } from '@fasl-work/caos-app-shell';
import { UPlotChart } from '@fasl-work/caos-app-shell/chart';
import type { Finding, TestRow } from '../lib/contract.types';
import { LIGHT_TEXT, relight } from '../lib/policy';
import { useFindingsShares } from '../lib/useMedia';
import { REPLAY, provenanceOf, type Selection } from './model';
import { Pending } from './Pending';
import { evidenceText } from './names';

const SEVERITY_TEXT = {
  S1: { en: 'S1 critical', es: 'S1 crítico' },
  S2: { en: 'S2 significant', es: 'S2 significativo' },
  S3: { en: 'S3 moderate', es: 'S3 moderado' },
  S4: { en: 'S4 minor', es: 'S4 menor' },
} as const;

const STATUS_TEXT = {
  open: { en: 'open', es: 'abierto' },
  accepted: { en: 'accepted (a stated limit)', es: 'aceptado (un límite declarado)' },
  closed: { en: 'closed', es: 'cerrado' },
} as const;

function Evidence({ f, sel, number }: { f: Finding; sel: Selection; number: Map<string, number> }) {
  const lang = useShellLang();
  return (
    <ul className="ct-evidence">
      {f.evidence.map((e) => {
        const ctx = { caseId: 'C01', models: sel.data.variant.model };
        if (e.startsWith('design:')) return <li key={e}>{evidenceText(e, ctx, lang)}</li>;
        if (e.startsWith('contract:')) {
          const rule = e.slice(9);
          const n = Object.values(sel.data.manifest.contract).reduce((a, c) => a + (c.by_rule.flagged[rule] ?? 0), 0);
          return (
            <li key={e}>
              {evidenceText(e, ctx, lang)}: {formatNumber(n, lang)} {pick({ en: 'records flagged', es: 'registros marcados' }, lang)}
            </li>
          );
        }
        const row = cited(sel, e);
        const k = number.get(`${f.id}|${e}`);
        return (
          <li key={e}>
            {k ? `[${k}] ` : ''}
            {/* a p-value that underflowed to 0 in double precision lies below 1E-300, as the battery prints it (R3 c01 m2) */}
            {evidenceText(e, ctx, lang)}: {row ? `p ${row.p_value === 0 ? '< 1E-300' : formatNumber(row.p_value, lang, { digits: 2 })}, ${pick(LIGHT_TEXT[relight(row, sel.alphas)], lang)}` : ''}
          </li>
        );
      })}
    </ul>
  );
}

/** The portfolio row of the test a finding cites as `test@model`, or undefined for any other kind of evidence. */
function cited(sel: Selection, e: string): TestRow | undefined {
  if (e.startsWith('design:') || e.startsWith('contract:')) return undefined;
  const [testId, model] = e.split('@');
  return sel.data.variant.tests.find((t) => t.test_id === testId && t.model_id === model && t.segment === 'portfolio');
}

/** The evidence chart's points: the cited tests numbered 1 to n, each p-value at the floor when below it, and the x range that gives the
 * first and last points room, so no padding point enters the chart's data table (R3 c02 m19). */
export function evidenceSeries(ps: ReadonlyArray<number | null>, floorP = 1e-16): { x: number[]; values: number[]; range: [number, number] } {
  return { x: ps.map((_, i) => i + 1), values: ps.map((p) => Math.max(floorP, p ?? 1)), range: [0.5, ps.length + 0.5] };
}

export function FindingsView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  const shares = useFindingsShares();
  if (!sel) return <Pending />;
  const v = sel.data.variant;
  const order = ['S1', 'S2', 'S3', 'S4'];
  const findings = [...v.findings].sort((a, b) => order.indexOf(a.severity) - order.indexOf(b.severity));
  const worst = findings.find((f) => f.status === 'open')?.severity ?? null;
  // every cited test with a p-value, numbered in reading order: the table's [k] and the chart's x
  const points = findings.flatMap((f) => f.evidence.map((e) => ({ key: `${f.id}|${e}`, row: cited(sel, e) }))).filter((x) => x.row && x.row.p_value !== null);
  const number = new Map(points.map((x, i) => [x.key, i + 1]));
  // half a step of room on each side, so the first and last points are not cut by the plot's edges
  const evidence = evidenceSeries(points.map((x) => x.row?.p_value ?? null));
  const table = (
    <PlotCard
      fill
      title={{ en: 'Findings of the validation of this variant', es: 'Hallazgos de la validación de esta variante' }}
      lane={REPLAY}
      provenance={provenanceOf(v.provenance.truth_status)}
      dataKey={stateKey}
      note={{
        // every family the producer's policy rates (c01_retail_pd.py SEVERITY), and the reason for the fit tests said of large books only
        // (R3 c01 m15, c02 m14: the stability and discrimination findings, and the German twin of 300 obligors)
        en: 'Severity policy: a red level test (Jeffreys, binomial) of the champion or the challenger is S2 and amber S3, and so is a red or amber stability (PSI) or discrimination (AUC against the initial) test; a red fit test (chi-square over grades, Hosmer-Lemeshow, Spiegelhalter) is S3 and amber S4, because on a large book they reject deviations too small to matter. Evidence is shown under the rail\'s policy; the findings were raised under the committed one.',
        es: 'Política de severidad: una prueba de nivel roja (Jeffreys, binomial) del campeón o del retador es S2 y ámbar S3, igual que una prueba de estabilidad (PSI) o de discriminación (AUC contra el inicial) roja o ámbar; una prueba de ajuste roja (chi-cuadrado sobre grados, Hosmer-Lemeshow, Spiegelhalter) es S3 y ámbar S4, porque en una cartera grande rechazan desvíos demasiado pequeños para importar. La evidencia se muestra con la política del panel; los hallazgos se levantaron con la política versionada.',
      }}
    >
      <div className="ct-stack" data-caos-flow="">
        <Verdict
          compact
          title={{ en: 'Most severe open finding', es: 'Hallazgo abierto más severo' }}
          tone={worst === 'S1' || worst === 'S2' ? 'bad' : worst === 'S3' ? 'warn' : 'good'}
          verdict={worst ? SEVERITY_TEXT[worst as keyof typeof SEVERITY_TEXT] : { en: 'No open finding.', es: 'Ningún hallazgo abierto.' }}
        />
        <div className="ct-scroll" data-caos-flow="">
          <table className="caos-table ct-top">
            <thead>
              <tr>
                <th className="ct-wide-only ct-repeated">{pick({ en: 'Finding', es: 'Hallazgo' }, lang)}</th>
                <th>{pick({ en: 'Severity', es: 'Severidad' }, lang)}</th>
                <th className="ct-wide-only ct-repeated">{pick({ en: 'Status', es: 'Estado' }, lang)}</th>
                <th className="caos-col-text">{pick({ en: 'What and why', es: 'Qué y por qué' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {findings.map((f) => (
                <tr key={f.id} data-severity={f.severity}>
                  <td className="ct-wide-only ct-repeated">{f.id}</td>
                  <td>{pick(SEVERITY_TEXT[f.severity], lang)}</td>
                  <td className="ct-wide-only ct-repeated">{pick(STATUS_TEXT[f.status], lang)}</td>
                  <td className="caos-col-text">
                    {pick(f.title, lang)}
                    <span className="ct-narrow-only">{f.id}; {pick({ en: 'status: ', es: 'estado: ' }, lang)}{pick(STATUS_TEXT[f.status], lang)}</span>
                    <Evidence f={f} sel={sel} number={number} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </PlotCard>
  );
  if (points.length === 0) return table;
  return (
    <ViewsRow shares={shares}>
      {table}
      <PlotCard
        fill
        title={{ en: 'The evidence against the policy', es: 'La evidencia contra la política' }}
        lane={REPLAY}
        provenance={provenanceOf(v.provenance.truth_status)}
        dataKey={stateKey}
        note={{
          en: `The p-value of each cited test, numbered as in the table, on a log scale against the rail's amber (${formatNumber(sel.alphas.amber, 'en', { digits: 2 })}) and red (${formatNumber(sel.alphas.red, 'en', { digits: 2 })}) thresholds: how far past the line each finding's evidence lies. A p-value below 1e-16 is drawn at 1e-16.`,
          es: `El valor p de cada prueba citada, numerada como en la tabla, en escala logarítmica contra los umbrales ámbar (${formatNumber(sel.alphas.amber, 'es', { digits: 2 })}) y rojo (${formatNumber(sel.alphas.red, 'es', { digits: 2 })}) del panel: cuán lejos de la línea está la evidencia de cada hallazgo. Un valor p bajo 1e-16 se dibuja en 1e-16.`,
        }}
      >
        <UPlotChart
          height="fill"
          x={{ values: evidence.x, range: evidence.range, label: { en: 'Cited test (the number in the table)', es: 'Prueba citada (el número de la tabla)' }, format: { decimals: 0 } }}
          y={{ label: { en: 'p-value', es: 'Valor p' }, log: true, format: { digits: 2 } }}
          series={[
            { label: { en: 'p-value', es: 'Valor p' }, values: evidence.values, color: '--color-accent', mode: 'points' },
          ]}
          yMarks={[
            { y: sel.alphas.amber, label: { en: 'Amber threshold', es: 'Umbral ámbar' }, tone: 'warn' },
            { y: sel.alphas.red, label: { en: 'Red threshold', es: 'Umbral rojo' }, tone: 'bad' },
          ]}
        />
      </PlotCard>
    </ViewsRow>
  );
}
