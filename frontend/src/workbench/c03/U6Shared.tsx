// What the three U6 instruments (C03, C08, C09) share: the card props of a replayed view, the live read-out, a
// proportion that may lie outside [0, 1] shown with its flag in words and never clipped, the tests table (a test that
// did not run shows its reason, never a number), and the number formats. Nothing here computes a statistic.
import { Readout, formatNumber, pick, useShellLang, useWorkbenchState, type BiText, type ReadoutItem } from '@fasl-work/caos-app-shell';
import type { Lane } from '@fasl-work/caos-app-shell';
import type { TestRow, VariantArtifact } from '../../lib/contract.types';
import { LIGHT_TEXT } from '../../lib/policy';
import { REPLAY, provenanceOf } from '../model';
import { pct } from '../c06/format';
import { WHOLE_PORTFOLIO, segmentName, testText } from '../names';

export const LIVE: Lane = 'live';

/** A text in both languages, as the maps of words here hold it (the shell's BiText may also be a plain string). */
export type Bi = { en: string; es: string };

const ACRONYMS = new Set(['sme', 'lgd', 'ead', 'ccf', 'qrre', 'usa', 'sba']);

/** An id of the documents in words: "sme-real-estate" becomes "SME real estate". */
export function humanize(id: string): string {
  const words = id.split(/[-_]/).filter(Boolean).map((w) => (ACRONYMS.has(w.toLowerCase()) ? w.toUpperCase() : w.toLowerCase()));
  const text = words.join(' ');
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/**
 * The notes the validation engine writes in English only (its `notes` field is one plain string, with no Spanish beside it),
 * read in the page's language. Only a note the engine is known to write is translated, whole; any other note is shown as it
 * comes, and English is never changed. The correlation value is formatted for the language, not copied.
 */
const ENGINE_NOTES: Array<[RegExp, (m: RegExpMatchArray, lang: 'en' | 'es') => string]> = [
  [/^assumes independent defaults; WP14: the true type I error can be much larger if defaults are correlated$/, () => 'supone incumplimientos independientes; WP14: el error tipo I verdadero puede ser mucho mayor si los incumplimientos están correlacionados'],
  [/^asset correlation (\d+(?:\.\d+)?) is a modelling assumption$/, (m, lang) => `la correlación de activos ${formatNumber(Number(m[1]), lang)} es un supuesto de modelación`],
  [/^the development AUC's variance is added to the ECB statistic \(an extension of the ECB 2019 formula\): both AUCs are estimates on independent samples$/, () => 'la varianza del AUC de desarrollo se suma al estadístico del BCE (una extensión de la fórmula del BCE de 2019): ambos AUC son estimaciones sobre muestras independientes'],
  [/^conventional band: (significant|moderate|little) change \(0\.10\/0\.25 rule of thumb, no error control\)$/, (m) => `banda convencional: cambio ${({ significant: 'significativo', moderate: 'moderado', little: 'pequeño' } as Record<string, string>)[m[1]]} (regla práctica de 0,10/0,25, sin control del error)`],
];

/**
 * The reference of a test row in the page's language: the bilingual text the producer carries in `extras.reference_text` (the citation
 * as published, its locators and the dossier's remark in Spanish), else the engine's own string (U16-F6: no English remark in a Spanish
 * reference column).
 */
export function referenceText(t: Pick<TestRow, 'reference' | 'extras'>, lang: 'en' | 'es'): string {
  const r = (t.extras as { reference_text?: { en?: unknown; es?: unknown } } | undefined)?.reference_text;
  const text = r?.[lang];
  return typeof r?.en === 'string' && typeof r?.es === 'string' && typeof text === 'string' ? text : t.reference;
}

/** The reference of a row in a language that has it: the bilingual reference, or the engine's English one on an English page; null on a
 * Spanish page when the producer gives the reference in English only (no English remark in a Spanish column; R3 c03 m11). */
export function referenceIn(t: Pick<TestRow, 'reference' | 'extras'>, lang: 'en' | 'es'): string | null {
  const r = (t.extras as { reference_text?: { en?: unknown; es?: unknown } } | undefined)?.reference_text;
  return lang === 'en' || (typeof r?.en === 'string' && typeof r?.es === 'string') ? referenceText(t, lang) : null;
}

/** An engine note in the page's language (see ENGINE_NOTES). */
export function engineNote(note: string, lang: 'en' | 'es'): string {
  if (lang === 'en') return note;
  for (const [re, make] of ENGINE_NOTES) {
    const m = note.match(re);
    if (m) return make(m, lang);
  }
  return note;
}

/** A proportion with two decimals: 9.20%, 104.00%. */
export const p2 = (v: number | null | undefined, lang: 'en' | 'es') => pct(v, lang, 2);

/** The flag of a loss given default or a conversion factor, in words. In range has none. */
export type RangeFlag = 'in-range' | 'below-zero' | 'above-one';

export const FLAG_TEXT: Record<'below-zero' | 'above-one', BiText> = {
  'below-zero': { en: 'below 0', es: 'bajo 0' },
  'above-one': { en: 'above 1', es: 'sobre 1' },
};

/** The props every replayed card takes: its lane, the truth status of the variant and the workbench state key. */
export function useCard(variant: VariantArtifact | undefined): { lane: Lane; provenance: ReturnType<typeof provenanceOf>; dataKey: string | undefined } {
  const stateKey = useWorkbenchState()?.stateKey;
  return { lane: REPLAY, provenance: provenanceOf(variant?.provenance.truth_status), dataKey: stateKey };
}

/** A live read-out of the rail: always drawn, with no row while the selection is not there. */
export function LiveReadout({ variant, title, items, lane = LIVE }: { variant: VariantArtifact | undefined; title: BiText; items: ReadoutItem[]; lane?: Lane }) {
  const stateKey = useWorkbenchState()?.stateKey;
  return <Readout title={title} lane={lane} provenance={provenanceOf(variant?.provenance.truth_status)} dataKey={stateKey} items={items} />;
}

/** The read-out row of a proportion that the contract flags: the value as it is, and its flag as the unit when outside [0, 1]. */
export function flaggedItem(label: BiText, hint: BiText, value: number | null, flag: RangeFlag | null, decimals = 2): ReadoutItem {
  const outside = flag === 'below-zero' || flag === 'above-one';
  return { label, hint, value, ...(outside ? { unit: FLAG_TEXT[flag] } : { unitless: true }), format: { percent: true, decimals } };
}

/** A proportion that may lie outside [0, 1], printed as it is with its flag in words: an LGD above one is never shown as one. */
export function Flagged({ value, flag, extreme }: { value: number; flag: RangeFlag; extreme?: string }) {
  const lang = useShellLang();
  return (
    <span data-extreme={extreme} data-flag={flag}>
      {p2(value, lang)}
      {flag === 'in-range' ? null : <span className="ct-note">{` (${pick(FLAG_TEXT[flag], lang)})`}</span>}
    </span>
  );
}

/** The words of the tests the engine returns for these cases; an id without an entry is shown as it is. */
const TEST_TEXT: Record<string, BiText> = {
  'pd.vintage_calibration': { en: 'PD calibration by vintage', es: 'Calibración de la PD por cosecha' },
  'lgd_ead.lgd_calibration_by_segment': { en: 'LGD calibration by segment', es: 'Calibración de la LGD por segmento' },
  'lgd_ead.lgd_calibration_over_time': { en: 'LGD calibration over time', es: 'Calibración de la LGD en el tiempo' },
  'lgd_ead.lgd_discrimination': { en: 'LGD discrimination', es: 'Discriminación de la LGD' },
  'lgd_ead.downturn_coverage': { en: 'Downturn coverage', es: 'Cobertura de la recesión' },
  'lgd_ead.ccf_estimator_bias': { en: 'CCF estimator bias', es: 'Sesgo del estimador de CCF' },
  'lgd_ead.ead_backtest_by_band': { en: 'EAD back-test by utilisation band', es: 'Prueba retrospectiva de la EAD por tramo de utilización' },
};

/**
 * The segment of each row of a tests table in words, on every row that has one: a vintage, a grade, a horizon, a cell, an input, and a
 * portfolio row says "portfolio" (the R4 ruling 3 on c04 M1: every tests table shows the segment on every row; labelling only the rows
 * that would otherwise read alike did not meet it). A row with no segment takes `none`, the scope of the table in words (R5 ruling 2:
 * "whole portfolio" for a credit portfolio), or null where the caller names none. A segment no form names is shown as written (the
 * names gate keeps that fallback unused).
 */
export function segmentLabels(rows: ReadonlyArray<Pick<TestRow, 'test_id' | 'model_id' | 'segment'>>, caseId: string, none: Bi | null = null): Array<Bi | null> {
  return rows.map((t) => (t.segment ? segmentName(t.segment, { caseId }) ?? { en: t.segment, es: t.segment } : none));
}

/**
 * The rows the engine returned for the tests of this variant, as a block that sits under the drawing of the view the
 * tests belong to (a table alone cannot fill a stage, ADR-0071 rule 8): a test that did not run shows its reason, not a
 * number. `only` keeps the tests of one view; each row names its segment where one is needed to tell it apart.
 */
/** A statistic at four significant digits with its trailing zeros (R5 c11 n3: "0.12" beside "0.1234"): fixed decimals in the shell's
 * notation between 1E-4 and 1,000, the shell's own form outside it (scientific below, every integer digit above). */
export function statText(x: number, lang: 'en' | 'es'): string {
  const a = Math.abs(x);
  if (a === 0 || a < 1e-4 || a >= 1000 || !Number.isFinite(x)) return formatNumber(x, lang, { digits: 4 });
  return formatNumber(x, lang, { decimals: Math.max(0, 3 - Math.floor(Math.log10(a))) });
}

export function U6TestsTable({ variant, modelLabel, only }: { variant: VariantArtifact; modelLabel?: (id: string) => string; only?: (t: TestRow) => boolean }) {
  const lang = useShellLang();
  const rows: TestRow[] = only ? variant.tests.filter(only) : variant.tests;
  // every case that draws this table is a credit portfolio: a row of no segment is the whole portfolio (R5 ruling 2)
  const segments = segmentLabels(rows, variant.case_id, WHOLE_PORTFOLIO);
  return (
    <div data-block="tests">
      <p className="ct-note">
        {pick({ en: 'The tests the engine returned: the statistic and p-value when it ran, the light under the committed policy and its reference. A test that did not run says why and shows no number.', es: 'Las pruebas que devolvió el motor: el estadístico y el valor p cuando corrió, la luz bajo la política versionada y su referencia. Una prueba que no corrió dice por qué y no muestra número.' }, lang)}
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
                  <td className="ct-text" title={t.test_id}>
                    {pick(TEST_TEXT[t.test_id] ?? testText(t.test_id), lang)}
                    {segments[i] ? <span className="ct-row-detail" data-segment={t.segment ?? 'none'}>{pick(segments[i]!, lang)}</span> : null}
                  </td>
                  <td className="ct-text ct-wide-only">{t.model_id === null ? '-' : (modelLabel?.(t.model_id) ?? t.model_id)}</td>
                  <td data-na={ran && t.statistic !== null ? undefined : 'true'}>{ran && t.statistic !== null ? statText(t.statistic, lang) : formatNumber(null, lang)}</td>
                  {/* a p-value that underflowed to 0 reads below the smallest double, never "0" (R4 c04, c10: a red row printed p 0) */}
                  <td data-na={ran && t.p_value !== null ? undefined : 'true'}>{ran && t.p_value !== null ? (t.p_value === 0 ? '< 1E-300' : formatNumber(t.p_value, lang, { digits: 2 })) : formatNumber(null, lang)}</td>
                  <td className={`ct-text ct-light ct-light-${t.light}`}>
                    <span className="ct-light-word">{pick(LIGHT_TEXT[t.light], lang)}</span>
                  </td>
                  <td className="ct-text">{t.notes ? engineNote(t.notes, lang) : referenceText(t, lang)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
