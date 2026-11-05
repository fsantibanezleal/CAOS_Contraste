// What the C21 views render from the documents' own sentences: a regulation citation ("29 CFR 1607.4(D)") is kept as the
// source writes it, so it is marked `translate="no"` (the gate's decimal check, G11, reads a decimal point there as a
// Spanish number), and a short range ("36%-49%", "35-44") cannot break across two lines (G19). One helper, applied where
// the text is rendered; the documents are never edited.
import { Fragment, type ReactNode } from 'react';
import { formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import type { TestRow } from '../../lib/contract.types';
import { LIGHT_TEXT } from '../../lib/policy';
import { testName } from '../c20/U14Common';
import { modelName, segmentName } from '../names';
import { es } from './localise';

// a regulation citation ("29 CFR 1607.4(D)"), a row of a regulation's annex ("row 10.2", "fila 10.2") and the arithmetic of rows a
// label names ("(4.4+4.5+4.6)", "(8%+7.1+7.2)", "(6-7.2)", "(1.1 - 5)"): references kept as the source writes them
const CITATION = /\d+ CFR \d+(?:\.\d+)?(?:\([^)]*\))*|\b(?:row|fila) \d+(?:\.\d+)+|\((?=[^)]*\d\.\d)(?:\d+(?:\.\d+)?%?\s*[-+]\s*)+\d+(?:\.\d+)?%?\)/;
const RANGE = /\d{4}-\d{2}-\d{2}|\d+ (?:to|a) \d+|[<>]?\d+(?:\.\d+)?%?-[<>]?\d+(?:\.\d+)?%?/;
// a code of the public file in a sentence ("the markers NA and Exempt", "Yes for 62 or over", "No para menores de 62"): marked as a code
// of the source, so a Spanish sentence does not read it as an English word (U16-R4 c25 m7)
const CODE = /\b(?:NA|Exempt|Yes)\b|\bNo(?= (?:para|for)\b)/;
const TOKEN = new RegExp(`(${CITATION.source})|(${RANGE.source})|(${CODE.source})`, 'g');

/** A string with its citations marked as not to be translated and its ranges kept on one line. */
export function Marked({ children }: { children: string }): ReactNode {
  const parts: ReactNode[] = [];
  let at = 0;
  for (const m of children.matchAll(TOKEN)) {
    const i = m.index ?? 0;
    if (i > at) parts.push(children.slice(at, i));
    parts.push(
      m[3] ? (
        <code key={i} translate="no" lang="en">{m[0]}</code>
      ) : m[1] ? (
        <span key={i} translate="no" lang={/^fila /.test(m[0]) ? 'es' : /^\(/.test(m[0]) ? undefined : 'en'}>{m[0]}</span>
      ) : (
        <span key={i} style={{ whiteSpace: 'nowrap' }}>{m[0]}</span>
      ),
    );
    at = i + m[0].length;
  }
  if (at < children.length) parts.push(children.slice(at));
  return <Fragment>{parts}</Fragment>;
}

/** The engine's note of a test with its configuration key in words (U16-R3 c21 B6: "sits in extras.thresholds" in both languages): the cut
 * the key holds, read from the row. */
export function noteText(t: TestRow, lang: 'en' | 'es'): string {
  const text = es(t.notes ? t.notes : (t.reference ?? ''), lang);
  if (!text.includes('extras.thresholds')) return text;
  const amber = (t.extras as { thresholds?: { amber?: unknown } } | null | undefined)?.thresholds?.amber;
  const cut = typeof amber === 'number'
    ? (lang === 'en' ? `the amber share ${formatNumber(amber, 'en', { decimals: 2 })} of significant complainants, a convention` : `la parte ámbar ${formatNumber(amber, 'es', { decimals: 2 })} de denunciantes significativos, una convención`)
    : (lang === 'en' ? 'the convention of the case' : 'la convención del caso');
  return text.replace(/(?:sits|está) in extras\.thresholds|está en extras\.thresholds/, (m) => (m.startsWith('sits') ? `is ${cut}` : `es ${cut}`)).replace('extras.thresholds', cut);
}

/** The tests table of the shared U14 kit, with the notes of the engine marked by `Marked` (the shared table prints them as plain text). */
export function C21TestsTable({ tests, only }: { tests: TestRow[]; only?: (t: TestRow) => boolean }) {
  const lang = useShellLang();
  const rows = only ? tests.filter(only) : tests;
  return (
    <div data-block="tests">
      <p className="ct-note">
        {pick({ en: 'The tests the engine returned: the statistic when it ran, the light under the committed policy and its reference. A test that did not run says why and shows no number.', es: 'Las pruebas que devolvió el motor: el estadístico cuando corrió, la luz bajo la política versionada y su referencia. Una prueba que no corrió dice por qué y no muestra número.' }, lang)}
      </p>
      {rows.length === 0 ? (
        <p className="ct-note" data-state="unavailable">{pick({ en: 'This variant carries no test row for this view.', es: 'Esta variante no trae filas de pruebas para esta vista.' }, lang)}</p>
      ) : (
        <table className="caos-table ct-wrap-head" data-table="tests">
          <thead>
            <tr>
              <th className="ct-text">{pick({ en: 'Test', es: 'Prueba' }, lang)}</th>
              <th className="ct-text ct-wide-only">{pick({ en: 'Model', es: 'Modelo' }, lang)}</th>
              <th>{pick({ en: 'Statistic', es: 'Estadístico' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Light', es: 'Luz' }, lang)}</th>
              <th className="ct-text">{pick({ en: 'Reason or note', es: 'Razón o nota' }, lang)}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t, i) => {
              const ran = t.light !== 'not_evaluated' && t.light !== 'error';
              return (
                <tr key={`${t.test_id}-${t.model_id}-${t.segment}-${i}`} data-test={t.test_id} data-light={t.light}>
                  <td className="ct-text">
                    {pick(testName(t.test_id), lang)}
                    {/* the attribute and the contrast the row tests, so the rows can be told apart (U16-R3 c21 M1) */}
                    {t.segment ? <span className="ct-row-detail" data-segment={t.segment}>{pick(segmentName(t.segment, { caseId: 'C21' }) ?? { en: t.segment, es: t.segment }, lang)}</span> : null}
                  </td>
                  <td className="ct-text ct-wide-only">{t.model_id === null ? '-' : pick(modelName(t.model_id, { caseId: 'C21' }) ?? { en: t.model_id, es: t.model_id }, lang)}</td>
                  {/* a test that ran with no statistic shows its metric (U16-R3 c21 m1) */}
                  <td data-na={ran && (t.statistic ?? t.metric) !== null && (t.statistic ?? t.metric) !== undefined ? undefined : 'true'}>{ran && (t.statistic ?? t.metric) !== null && (t.statistic ?? t.metric) !== undefined ? formatNumber((t.statistic ?? t.metric) as number, lang, { digits: 4 }) : formatNumber(null, lang)}</td>
                  <td className={`ct-text ct-light ct-light-${t.light}`}>
                    <span className="ct-light-word">{pick(LIGHT_TEXT[t.light], lang)}</span>
                  </td>
                  <td className="ct-text"><Marked>{noteText(t, lang)}</Marked></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
