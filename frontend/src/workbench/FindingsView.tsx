// The Findings group: what the validation found, with its severity, its status and the evidence behind it. Severity
// follows the case's stated policy (the level of the PD weighs more than its fit across the range); a finding cites
// the tests that evidence it, a contract-1 rule of the inputs, or a design limit.
import { PlotCard, Verdict, formatNumber, pick, useShellLang, useWorkbenchState } from '@fasl-work/caos-app-shell';
import type { Finding } from '../lib/contract.types';
import { LIGHT_TEXT, relight } from '../lib/policy';
import { REPLAY, provenanceOf, type Selection } from './model';
import { Pending } from './Pending';

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

function Evidence({ f, sel }: { f: Finding; sel: Selection }) {
  const lang = useShellLang();
  return (
    <ul className="ct-evidence">
      {f.evidence.map((e) => {
        if (e.startsWith('design:')) return <li key={e}>{pick({ en: 'Design limit: ', es: 'Límite de diseño: ' }, lang)}{e.slice(7)}</li>;
        if (e.startsWith('contract:')) {
          const rule = e.slice(9);
          const n = Object.values(sel.data.manifest.contract).reduce((a, c) => a + (c.by_rule.flagged[rule] ?? 0), 0);
          return (
            <li key={e}>
              {pick({ en: 'Contract 1 rule ', es: 'Regla del contrato 1 ' }, lang)}
              {rule}: {formatNumber(n, lang)} {pick({ en: 'records flagged', es: 'registros marcados' }, lang)}
            </li>
          );
        }
        const [testId, model] = e.split('@');
        const row = sel.data.variant.tests.find((t) => t.test_id === testId && t.model_id === model && t.segment === 'portfolio');
        return (
          <li key={e}>
            {testId} ({model}): {row ? `p ${formatNumber(row.p_value, lang, { digits: 2 })}, ${pick(LIGHT_TEXT[relight(row, sel.alphas)], lang)}` : ''}
          </li>
        );
      })}
    </ul>
  );
}

export function FindingsView({ sel }: { sel: Selection | null }) {
  const lang = useShellLang();
  const stateKey = useWorkbenchState()?.stateKey;
  if (!sel) return <Pending />;
  const v = sel.data.variant;
  const order = ['S1', 'S2', 'S3', 'S4'];
  const findings = [...v.findings].sort((a, b) => order.indexOf(a.severity) - order.indexOf(b.severity));
  const worst = findings.find((f) => f.status === 'open')?.severity ?? null;
  return (
    <PlotCard
      fill
      title={{ en: 'Findings of the validation of this variant', es: 'Hallazgos de la validación de esta variante' }}
      lane={REPLAY}
      provenance={provenanceOf(v.provenance.truth_status)}
      dataKey={stateKey}
      note={{
        en: 'Severity policy: a red level test (Jeffreys, binomial) of the champion or the challenger is S2 and amber S3; a red fit test (chi-square over grades, Hosmer-Lemeshow, Spiegelhalter) S3 and amber S4, because at thousands of obligors they reject deviations too small to matter. Evidence is shown under the rail\'s policy; the findings were raised under the committed one.',
        es: 'Política de severidad: una prueba de nivel roja (Jeffreys, binomial) del campeón o del retador es S2 y ámbar S3; una prueba de ajuste roja (chi-cuadrado sobre grados, Hosmer-Lemeshow, Spiegelhalter) S3 y ámbar S4, porque con miles de deudores rechazan desvíos demasiado pequeños para importar. La evidencia se muestra con la política del panel; los hallazgos se levantaron con la comprometida.',
      }}
    >
      <div className="ct-stack">
        <Verdict
          compact
          title={{ en: 'Most severe open finding', es: 'Hallazgo abierto más severo' }}
          tone={worst === 'S1' || worst === 'S2' ? 'bad' : worst === 'S3' ? 'warn' : 'good'}
          verdict={worst ? SEVERITY_TEXT[worst as keyof typeof SEVERITY_TEXT] : { en: 'No open finding.', es: 'Ningún hallazgo abierto.' }}
        />
        <div className="ct-scroll">
          <table className="caos-table">
            <thead>
              <tr>
                <th className="ct-wide-only">{pick({ en: 'Finding', es: 'Hallazgo' }, lang)}</th>
                <th>{pick({ en: 'Severity', es: 'Severidad' }, lang)}</th>
                <th className="ct-wide-only">{pick({ en: 'Status', es: 'Estado' }, lang)}</th>
                <th className="caos-col-text">{pick({ en: 'What and why', es: 'Qué y por qué' }, lang)}</th>
              </tr>
            </thead>
            <tbody>
              {findings.map((f) => (
                <tr key={f.id} data-severity={f.severity}>
                  <td className="ct-wide-only">{f.id}</td>
                  <td>{pick(SEVERITY_TEXT[f.severity], lang)}</td>
                  <td className="ct-wide-only">{pick(STATUS_TEXT[f.status], lang)}</td>
                  <td className="caos-col-text">
                    {pick(f.title, lang)}
                    <Evidence f={f} sel={sel} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </PlotCard>
  );
}
