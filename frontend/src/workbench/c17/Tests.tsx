// The engine tests of operational risk under the view they belong to (ADR-0071 rule 8: a table alone cannot fill a stage,
// so the tests sit under the drawing of their view). A test that did not run shows its reason and no number; the id of
// a test is an attribute for the gate, never the text a reader sees.
import { formatNumber, pick, useShellLang } from '@fasl-work/caos-app-shell';
import type { TestRow, VariantArtifact } from '../../lib/contract.types';
import { LIGHT_TEXT } from '../../lib/policy';
import { TEST_TEXT, TEST_VIEW } from './selection';
import { es } from './localise';
import { rowWhere, testText } from '../names';

export type TestHost = 'exceedance' | 'tail' | 'method' | 'response' | 'scenario' | 'ladder';

/** The scope of a row the document gives no method and no segment: the benchmark reproduction, which checks the numerical
 * methods against the generator's true loss distribution (U16-R5 ruling 2: a row of no segment names its scope in words). */
export const NO_SEGMENT_SCOPE = { en: "the generator's true loss distribution", es: 'la distribución verdadera de pérdidas del generador' } as const;

/** The words of a test: the table above, or the part of its id after the family, in words. */
const nameOf = (id: string) => TEST_TEXT[id] ?? testText(id);

type Lang = 'en' | 'es';
const num = (v: number, lang: Lang) => formatNumber(v, lang, { digits: 4 });
const sig3 = (v: number, lang: Lang) => formatNumber(v, lang, { digits: 3 });
const eur = (v: number, lang: Lang) => formatNumber(v, lang, { decimals: 0 });
const extra = (t: TestRow, key: string): number | null => {
  const v = (t.extras as Record<string, unknown> | null | undefined)?.[key];
  return typeof v === 'number' ? v : null;
};
const threshold = (t: TestRow, key: string): number | null => {
  const th = (t.extras as { thresholds?: Record<string, unknown> } | null | undefined)?.thresholds?.[key];
  return typeof th === 'number' ? th : null;
};

/**
 * The number a row shows under "Statistic": the engine's statistic, except for the SMA ILM response, whose statistic is the ILM after the
 * added loss while its light is decided on the jump (`metric`, U16-R3 c18 M3: a reader took 1.047 for the jump).
 */
export function shownStatistic(t: TestRow): number | null {
  if (t.test_id === 'oprisk.sma_ilm_response') return t.metric ?? null;
  return t.statistic;
}

/** The numbers behind a row's light, in words (U16-R3 c18 M3, m1, m2): what the statistic is and what decides the light. */
export function lightDetail(t: TestRow, lang: Lang): string | null {
  if (t.test_id === 'oprisk.sma_ilm_response') {
    const before = extra(t, 'ilm_before');
    const after = extra(t, 'ilm_after');
    const loss = extra(t, 'added_loss');
    if (before === null || after === null || loss === null || t.metric === null || t.metric === undefined) return null;
    const amber = threshold(t, 'jump_amber');
    const green = threshold(t, 'jump_green');
    const cut = amber !== null && green !== null
      ? (lang === 'en' ? `; green below ${sig3(green, 'en')}, amber below ${sig3(amber, 'en')}` : `; verde bajo ${sig3(green, 'es')}, ámbar bajo ${sig3(amber, 'es')}`)
      : '';
    return lang === 'en'
      ? `ILM ${sig3(before, 'en')} before and ${sig3(after, 'en')} after one added loss of EUR ${eur(loss, 'en')}: a jump of ${sig3(t.metric, 'en')}${cut}`
      : `ILM ${sig3(before, 'es')} antes y ${sig3(after, 'es')} después de sumar una pérdida de EUR ${eur(loss, 'es')}: un salto de ${sig3(t.metric, 'es')}${cut}`;
  }
  if (t.test_id === 'oprisk.capital_stability' && t.statistic !== null && t.metric !== null && t.metric !== undefined) {
    return lang === 'en'
      ? `bias ${num(t.statistic, 'en')}, dispersion ${num(t.metric, 'en')}`
      : `sesgo ${num(t.statistic, 'es')}, dispersión ${num(t.metric, 'es')}`;
  }
  if (t.test_id === 'oprisk.benchmark_reproduction' && t.statistic !== null) {
    const dev = extra(t, 'max_moment_rel_dev');
    const tol = threshold(t, 'moment_rel_tol');
    if (dev === null || tol === null) return null;
    return lang === 'en'
      ? `the share of the tolerance used: the largest relative deviation of the moments ${formatNumber(dev, 'en', { digits: 4 })} against the tolerance ${formatNumber(tol, 'en', { digits: 2 })}`
      : `la parte de la tolerancia usada: la mayor desviación relativa de los momentos ${formatNumber(dev, 'es', { digits: 4 })} contra la tolerancia ${formatNumber(tol, 'es', { digits: 2 })}`;
  }
  return null;
}

/**
 * The engine tests of a view. `cell` keeps the rows of that cell only, for a view that shows one cell (U16-R3 c18 m4: a view of one
 * cell listed every cell's 24 rows, 8,099 px at 390); a row without a cell is kept.
 */
export function C17TestsTable({ variant, host, cell }: { variant: VariantArtifact; host: TestHost; cell?: string }) {
  const lang = useShellLang();
  const rows: TestRow[] = variant.tests.filter((t) => (TEST_VIEW[t.test_id] ?? 'ladder') === host && (cell === undefined || !t.segment || t.segment === 'portfolio' || t.segment === cell));
  // the ladder hosts only a test no other view takes: with none it shows no block, not a sentence that always says none (R2b c18 m-1)
  if (host === 'ladder' && rows.length === 0) return null;
  return (
    <div data-block="tests">
      <p className="ct-note">
        {pick({ en: 'The tests the engine returned for this view: the statistic and p-value when a test ran, the light under the committed policy and its reference. A test that did not run says why and shows no number.', es: 'Las pruebas que devolvió el motor para esta vista: el estadístico y el valor p cuando una prueba corrió, la luz bajo la política versionada y su referencia. Una prueba que no corrió dice por qué y no muestra número.' }, lang)}
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
              // the method and the cell a row tests, so 24 capital rows of one test can be told apart (R2b c18 M-1)
              const where = rowWhere('C17', t.model_id, t.segment === 'portfolio' ? null : t.segment, variant.model) ?? NO_SEGMENT_SCOPE;
              const shown = shownStatistic(t);
              const detail = lightDetail(t, lang);
              return (
                <tr key={`${t.test_id}-${i}`} data-test={t.test_id} data-light={t.light}>
                  <td className="ct-text" title={name}>
                    {name}
                    <span className="ct-row-detail" data-segment={t.segment ?? undefined} data-scope={t.segment ?? t.model_id ?? 'true-loss-distribution'}>{pick(where, lang)}</span>
                    {detail ? <span className="ct-row-detail" data-detail="light">{detail}</span> : null}
                  </td>
                  <td data-na={ran && shown !== null ? undefined : 'true'}>{ran && shown !== null ? formatNumber(shown, lang, { digits: 4 }) : formatNumber(null, lang)}</td>
                  <td data-na={ran && t.p_value !== null ? undefined : 'true'}>{ran && t.p_value !== null ? formatNumber(t.p_value, lang, { digits: 2 }) : formatNumber(null, lang)}</td>
                  <td className={`ct-text ct-light ct-light-${t.light}`}>
                    <span className="ct-light-word">{pick(LIGHT_TEXT[t.light], lang)}</span>
                  </td>
                  <td className="ct-text">{es(t.notes ? t.notes : t.reference, lang)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
