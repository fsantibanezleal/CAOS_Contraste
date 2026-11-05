// U16-F12b (fix round 5, the R4 capture review of C04, batches c05 B1 to B3 and the Semesters table, c06 B1 and M1), on the committed
// C04 documents in both languages: the Spanish results print ESMA's attribution in Spanish, the write-up names the definition "Con
// retiros", no engine class is printed in prose, the Semesters numbers sit in a card of their own (0 of 16 rows were readable), and the
// minors of these views that are local (the correlation mark, the capital key, a singular count).
import { CitationsProvider, useLangStore } from '@fasl-work/caos-app-shell';
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import { C04Results, C04VariantsProvider } from '../../content/cases/C04Results';
import { C04WriteUp } from '../../content/cases/C04';
import { CITATIONS } from '../../content/citations';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { SemestersView } from './AgencyTestsViews';
import { keyLabel } from './LiveViews';
import { C04ContextView, sourceTextIn } from './C04Common';
import { PdByGradeView } from './AgencyValidationViews';
import { makeSel } from './selection';

type Lang = 'en' | 'es';
const LANGS: Lang[] = ['en', 'es'];
const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const manifest = read<CaseManifest>('manifests/C04.json');
const entries = manifest.artifacts.filter((a) => a.role === 'variant');
const variants = entries.map((a) => read<VariantArtifact>(a.path));
const dataOf = (id: string): CaseData => {
  const i = entries.findIndex((a) => a.variant_id === id);
  return { manifest, variant: variants[i], models: read<ModelsArtifact>(entries[i].models_ref as string) };
};
const src = (rel: string) => readFileSync(new URL(rel, import.meta.url), 'utf8');

function setLang(lang: Lang) {
  (useLangStore.getInitialState() as { lang: Lang }).lang = lang;
  useLangStore.setState({ lang });
}
afterEach(() => setLang('en'));

function html(el: ReactElement, lang: Lang): string {
  setLang(lang);
  return renderToStaticMarkup(
    <MemoryRouter>
      <CitationsProvider items={CITATIONS}>
        <C04VariantsProvider variants={variants}>{el}</C04VariantsProvider>
      </CitationsProvider>
    </MemoryRouter>,
  );
}
const text = (markup: string) => markup.replace(/<[^>]*>/g, ' ').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/\s+/g, ' ');
const cardCount = (markup: string) => [...markup.matchAll(/<figure[^>]*class="caos-plot/g)].length;

describe('U16-R4 c05 and c06 on the committed C04 documents', () => {
  it('c05 B1: the Spanish results print the attribution in Spanish, never "Source:"', () => {
    const es = text(html(<C04Results manifest={manifest} />, 'es'));
    expect(es).not.toContain('Source:');
    expect(es).not.toContain('tables transformed by');
    expect(es).toContain('Fuente: ESMA CEREP; tablas transformadas por Contraste');
    expect(text(html(<C04Results manifest={manifest} />, 'en'))).toContain('Source: ESMA CEREP; tables transformed by Contraste');
  });

  it('c05 B2: the Spanish write-up names the definition with the withdrawals as the product does, "Con retiros"', () => {
    const es = html(<C04WriteUp />, 'es');
    expect(es).not.toMatch(/<strong>Keep<\/strong>/);
    expect(es).toContain('<strong>Con retiros</strong> es la misma columna sobre toda la cohorte');
    expect(html(<C04WriteUp />, 'en')).toContain('<strong>Keep</strong> is the same column over the whole cohort');
  });

  it('c05 B3 and c06 B1: no engine class in the results prose, the generator named as the source registry names it', () => {
    for (const lang of LANGS) expect(text(html(<C04Results manifest={manifest} />, lang))).not.toContain('RatingPaths');
    expect(text(html(<C04Results manifest={manifest} />, 'en'))).toContain("Rating paths drawn by riskvalidation's rating-path generator from the engine's EM generator");
    expect(text(html(<C04Results manifest={manifest} />, 'es'))).toContain('Trayectorias de calificación generadas por el generador de trayectorias de calificación de riskvalidation desde el generador EM');
    // the guard of every C04 source that prints prose
    for (const f of ['../../content/cases/C04Results.tsx', '../../content/cases/C04.tsx', './C04Common.tsx', './LiveViews.tsx', './FamilyViews.tsx', './PublishedViews.tsx']) {
      expect(src(f), f).not.toMatch(/\bRatingPaths\b/);
    }
  });

  it('c05 Semesters: the years compared sit in a card of their own, each drawing alone in its card', () => {
    for (const lang of LANGS) {
      const markup = html(<SemestersView sel={makeSel(dataOf('sp'), { grade: 6 })} />, lang);
      expect(cardCount(markup), lang).toBe(3);
      // the table is not squeezed under a drawing (a ChartOverTable box): no table in a ct-stack-table box
      expect(markup).not.toMatch(/class="ct-stack-table"[^>]*>\s*<div class="ct-scroll"[^>]*>\s*<table[^>]*data-table="semesters-(pd|l1)"/);
      expect(markup).toContain('data-table="semesters-pd"');
      for (const r of (variants.find((v) => v.variant_id === 'sp') as unknown as VariantArtifact<{ semesters_vs_year: Array<{ year: number }> }>).outputs.semesters_vs_year) {
        expect(markup).toContain(`data-year="${r.year}"`);
      }
    }
    // Moody's, with no default column, keeps its two cards: the cohorts table carries the distance
    expect(cardCount(html(<SemestersView sel={makeSel(dataOf('moodys'), { grade: 6 })} />, 'en'))).toBe(2);
  });

  it('c06 n2: the correlation mark says what it marks, never "rail"', () => {
    for (const f of ['./PublishedViews.tsx', './LiveViews.tsx']) {
      expect(src(f), f).not.toMatch(/label: \{ en: 'rail', es: 'panel' \}/);
      expect(src(f), f).not.toMatch(/\{ en: 'rail', es: 'panel' \}/);
    }
    expect(src('./selection.ts')).toContain("CORRELATION_PICKED: BiText = { en: 'Correlation picked', es: 'Correlación elegida' }");
    expect(src('./PublishedViews.tsx')).toContain('label: CORRELATION_PICKED');
  });

  it('c05 n5 and c06 n3: the capital key prints a short name only where it differs from the label', () => {
    expect(keyLabel(5, 'EM', 'EM')).toBe('5 EM');
    expect(keyLabel(6, 'diagonal', 'Diagonal')).toBe('6 Diagonal');
    expect(keyLabel(1, 'D2', 'D2 rated defaulters')).toBe('1 D2 rated defaulters');
    expect(keyLabel(4, 'Con retiros', 'Con retiros')).toBe('4 Con retiros');
    expect(keyLabel(9, 'Truth', 'The true generator')).toBe('9 Truth: The true generator');
  });

  it('c05 m11 (ruling 6): the Spanish source registry translates its locators and the word joining two authors, not the titles', () => {
    expect(sourceTextIn("Finding generators for Markov chains (authors' version), section 4", 'es')).toBe('Finding generators for Markov chains (versión de los autores), sección 4');
    expect(sourceTextIn('Estimating probabilities of default (FRBNY Staff Report 190), Table 5', 'es')).toBe('Estimating probabilities of default (FRBNY Staff Report 190), Tabla 5');
    expect(sourceTextIn('T. Schuermann and S. Hanson, Federal Reserve Bank of New York; Journal of Banking and Finance 30(8)', 'es')).toBe('T. Schuermann y S. Hanson, Federal Reserve Bank of New York; Journal of Banking and Finance 30(8)');
    expect(sourceTextIn('R. B. Israel, J. S. Rosenthal and J. Z. Wei', 'es')).toBe('R. B. Israel, J. S. Rosenthal y J. Z. Wei');
    expect(sourceTextIn("(authors' version), section 4", 'en')).toBe("(authors' version), section 4");
    const es = text(html(<C04ContextView sel={makeSel(dataOf('sp'))} />, 'es'));
    expect(es).not.toMatch(/, section \d|, Table \d|authors' version/);
  });

  it('c05 n2 and c06 n5 (ruling 6): the Spanish prints the paper symbols, never "W hat" or an English subscript', () => {
    const es = text(html(<C04Results manifest={manifest} />, 'es'));
    expect(es).not.toMatch(/W hat|W tilde|W_init/);
    expect(es).toContain('Ŵ se juzga dentro del redondeo de sus entradas impresas');
    expect(text(html(<C04Results manifest={manifest} />, 'en'))).toContain('W hat is judged within the rounding of its printed entries');
    expect(src('./C04Common.tsx')).not.toContain('W hat de Engelmann');
  });

  it('c06 n7: one lower bound reads in the singular', () => {
    const en = text(html(<PdByGradeView sel={makeSel(dataOf('moodys'))} />, 'en'));
    const es = text(html(<PdByGradeView sel={makeSel(dataOf('moodys'))} />, 'es'));
    expect(en).not.toMatch(/\b1 lower bounds\b/);
    expect(es).not.toMatch(/\b1 cotas inferiores\b/);
    expect(en).toContain('a lower bound of a grade without a default');
    expect(es).toContain('una cota inferior de un grado sin incumplimientos');
    const s = src('./AgencyValidationViews.tsx');
    expect(s).toContain("chart.zeroLower === 1 ? t(l, 'a lower bound of a grade without a default', 'una cota inferior de un grado sin incumplimientos')");
    expect(s).toContain("chart.zeroLast5 === 1 ? t(l, 'a mean of the last five cohorts', 'una media de las últimas cinco cohortes')");
  });
});
