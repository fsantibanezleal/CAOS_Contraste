// The engine tests of operational risk under the view they belong to (ADR-0071 rule 8: a table alone cannot fill a stage,
// so the tests sit under the drawing of their view). A test that did not run shows its reason and no number; the id of
// a test is an attribute for the gate, never the text a reader sees.
import { formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import type { TestRow, VariantArtifact } from '../../lib/contract.types';
import { LIGHT_TEXT } from '../../lib/policy';
import { humanize } from '../c03/U6Shared';
import { TEST_TEXT, TEST_VIEW } from './selection';
import { es } from './localise';

export type TestHost = 'exceedance' | 'tail' | 'method' | 'response' | 'scenario' | 'ladder';

/** The words of a test: the table above, or the part of its id after the family, in words. */
const nameOf = (id: string) => TEST_TEXT[id] ?? { en: humanize(id.split('.').pop() ?? id), es: humanize(id.split('.').pop() ?? id) };

export function C17TestsTable({ variant, host }: { variant: VariantArtifact; host: TestHost }) {
  const lang = useShellLang();
  const rows: TestRow[] = variant.tests.filter((t) => (TEST_VIEW[t.test_id] ?? 'ladder') === host);
  return (
    <div data-block="tests">
      <p className="ct-note">
        {pick({ en: 'The tests the engine returned for this view: the statistic and p-value when a test ran, the light under the committed policy and its reference. A test that did not run says why and shows no number.', es: 'Las pruebas que devolvió el motor para esta vista: el estadístico y el valor p cuando una prueba corrió, la luz bajo la política comprometida y su referencia. Una prueba que no corrió dice por qué y no muestra número.' }, lang)}
      </p>
      {rows.length === 0 ? (
        <p className="ct-note" data-state="unavailable">{pick({ en: 'This variant carries no test row for this view.', es: 'Esta variante no trae filas de pruebas para esta vista.' }, lang)}</p>
      ) : (
        <table className="caos-table ct-wrap-head" data-table="tests">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Test', es: 'Prueba' }, lang)}</th>
              <th>{pick({ en: 'Statistic', es: 'Estadístico' }, lang)}</th>
              <th>p</th>
              <th className="ct-text">{pick({ en: 'Light', es: 'Luz' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Reason or note', es: 'Razón o nota' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t, i) => {
              const ran = t.light !== 'not_evaluated' && t.light !== 'error';
              const name = pick(nameOf(t.test_id), lang);
              return (
                <tr key={`${t.test_id}-${i}`} data-test={t.test_id} data-light={t.light}>
                  <td className="ct-text" title={name}>{name}</td>
                  <td data-na={ran && t.statistic !== null ? undefined : 'true'}>{ran && t.statistic !== null ? formatNumber(t.statistic, lang, { digits: 4 }) : formatNumber(null, lang)}</td>
                  <td data-na={ran && t.p_value !== null ? undefined : 'true'}>{ran && t.p_value !== null ? formatNumber(t.p_value, lang, { digits: 2 }) : formatNumber(null, lang)}</td>
                  <td className={`ct-text ct-light ct-light-${t.light}`}>
                    <span className="ct-light-word">{pick(LIGHT_TEXT[t.light], lang)}</span>
                  </td>
                  <td className="ct-text">{t.notes === null || t.notes === undefined ? t.reference : es(t.notes, lang)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
