// What the two market instruments (C11 and C13) share: the one-line sign convention each view states, the table of
// back-test rows (a test that did not run shows its reason and no number, never a zero), and the label of a light. Nothing
// here computes a statistic.
import { formatNumber, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import type { TestRow } from '../../lib/contract.types';
import { LIGHT_TEXT } from '../../lib/policy';
import { referenceText, type Bi } from '../c03/U6Shared';
import { MaybeNumber } from '../c06/format';
import { noteText } from '../c08/notes';
import { CONVENTION_LINE, testName, ZONE_TEXT, text } from './selection';

/** The sign convention, said once per view (dossier 05 A.0): the engine stores returns, the documents positive losses. */
export function ConventionLine() {
  const lang = useShellLang();
  return (
    <p className="ct-note" data-convention="true">
      {pick(CONVENTION_LINE, lang)}
    </p>
  );
}

/** The minimum height of a horizontal bar chart of `n` rows: about 1.5rem a row plus 3rem, so its rows never scroll inside the drawing. */
export const rowsMin = (n: number): string => `${Math.round((Math.max(n, 1) * 1.5 + 3) * 10) / 10}rem`;

/** A light or a zone in words, capitalised; an unknown one is shown as it is. */
export const zoneText = (zone: string): Bi => text(ZONE_TEXT, zone);

/** The light of a test row in lower-case words, as the policy writes it. */
export const lightWord = (light: TestRow['light']): BiText => LIGHT_TEXT[light];

/**
 * The policy alphas of the rows, one clause per distinct pair with the tests it applies to: the Acerbi-Szekely rows carry their own alphas,
 * which are not those of the Kupiec and Christoffersen rows (U16-R2 b05 M1).
 */
export function policyOf(rows: TestRow[], lang: 'en' | 'es'): string {
  const groups = new Map<string, string[]>();
  for (const r of rows) {
    if (r.alpha_amber === null || r.alpha_red === null) continue;
    const key = `${r.alpha_amber}|${r.alpha_red}`;
    const name = pick(testName(r.test_id), lang);
    groups.set(key, [...new Set([...(groups.get(key) ?? []), name])]);
  }
  const clause = (key: string, names: string[]) => {
    const [a, b] = key.split('|').map(Number);
    const alphas = lang === 'en' ? `amber below ${formatNumber(a, lang, { digits: 3 })}, red below ${formatNumber(b, lang, { digits: 3 })}` : `ámbar bajo ${formatNumber(a, lang, { digits: 3 })}, rojo bajo ${formatNumber(b, lang, { digits: 3 })}`;
    return groups.size === 1 ? alphas : `${names.join(', ')}: ${alphas}`;
  };
  return [...groups].map(([k, n]) => clause(k, n)).join('; ');
}

/**
 * The back-test rows of one model and level: the test in words, its statistic and p-value (or "not available"), the light
 * under the committed policy and the note, which for a test that did not run is the reason. The p-value that lights a row
 * is the engine's; the policy alphas are in the row (`alpha_amber`, `alpha_red`) and printed in the header note.
 */
export function MarketTestsTable({ rows, table }: { rows: TestRow[]; table: string }) {
  const lang = useShellLang();
  const policy = policyOf(rows, lang);
  return (
    <div data-block="tests">
      <p className="ct-note">
        {pick(
          {
            en: `The tests the engine returned: the statistic and p-value when it ran and the light under the committed policy${policy ? ` (${policyOf(rows, 'en')})` : ''}. A test that did not run says why and shows no number.`,
            es: `Las pruebas que devolvió el motor: el estadístico y el valor p cuando corrió y la luz bajo la política versionada${policy ? ` (${policy})` : ''}. Una prueba que no corrió dice por qué y no muestra número.`,
          },
          lang,
        )}
      </p>
      {rows.length === 0 ? (
        <p className="ct-note" data-state="unavailable">
          {pick({ en: 'This model and level carry no test row.', es: 'Este modelo y nivel no traen filas de pruebas.' }, lang)}
        </p>
      ) : (
        <table className="caos-table ct-wrap-head" data-table={table}>
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Back-test', es: 'Backtest' }, lang)}</th>
              <th>{pick({ en: 'Statistic', es: 'Estadístico' }, lang)}</th>
              <th>p</th>
              <th className="ct-text">{pick({ en: 'Light', es: 'Luz' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Reason or note', es: 'Razón o nota' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t, i) => {
              const ran = t.light !== 'not_evaluated' && t.light !== 'error';
              return (
                <tr key={`${t.test_id}-${t.model_id}-${t.segment}-${i}`} data-test={t.test_id} data-light={t.light}>
                  <td className="ct-text" title={referenceText(t, lang)}>{pick(testName(t.test_id), lang)}</td>
                  <td>
                    <MaybeNumber value={ran ? t.statistic : null} reason={null} format={(v) => formatNumber(v, lang, { digits: 4 })} />
                  </td>
                  <td>
                    <MaybeNumber value={ran ? t.p_value : null} reason={null} format={(v) => formatNumber(v, lang, { digits: 2 })} />
                  </td>
                  <td className={`ct-text ct-light ct-light-${t.light}`}>
                    <span className="ct-light-word">{pick(lightWord(t.light), lang)}</span>
                  </td>
                  <td className="ct-text">{t.notes ? noteText(t.notes, lang) : referenceText(t, lang)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
