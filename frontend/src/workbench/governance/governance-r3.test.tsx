// U16-F10p (the third capture review, R3 c23): the governance views on the committed governance documents
// (data/derived/governance), in both languages. Reader text carries no plan or decision code (W15-13, W15-7, W15-5), no
// engine key (risk_accepted, test_id@model, spec(), dim_cube) and no raw model id where the models document gives a name;
// the report's Spanish sentences are Spanish; the register keys of section 10 have their titles beside them; the outcome
// rows of a graded test name their grade; and the dependency map can be zoomed, panned, reset and read from the keyboard.
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { setLang } from '../c03/u6-testkit';
import { MapDrawing } from './DependencyMap';
import { RegisterSection } from './RegisterView';
import { ReportDocument, reportSentence } from './ReportView';
import { InventoryTab } from './InventoryView';
import { readerWords } from './readerText';
import type { GovFindings, GovInventory, GovReport } from './model';

const dir = new URL('../../../../data/derived/governance/', import.meta.url);
const read = <T,>(f: string): T => JSON.parse(readFileSync(new URL(f, dir), 'utf8')) as T;
const inv = read<GovInventory>('inventory.json');
const findings = read<GovFindings>('findings.json');
const german = read<GovReport>('reports/C01-german.json');
const html = (el: ReactElement) => renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);
const text = (m: string) => m.replace(/<title>[\s\S]*?<\/title>/g, ' ').replace(/<[^>]*>/g, ' ').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&').replace(/\s+/g, ' ');
const LANGS = ['en', 'es'] as const;
/** The first match of `re` in `t` with the words around it, or null. */
const none = (t: string, re: RegExp): void => {
  const m = re.exec(t);
  if (m) throw new Error(`${m[0]} :: ${t.slice(m.index - 30, m.index + 150)}`);
};

/** A plan or decision code (W15-13), an engine key or developer text, a raw rung id of the C01 ladder. */
const PLAN = /\bW15-\d+\b|\bW15\b/;
const ENGINE = /risk_accepted|test_id@|spec\(|KeyError|dim_cube|\bbake\b/;
const RUNG_ID = /\bP\d[ab]?-(constant|single|scorecard|l1|pltr|ebm|lightgbm|xgboost|tabpfn)\b/;

describe('the validation report in reader words (R3 c23 B1, B5, B6, M1)', () => {
  afterEach(() => setLang('en'));

  for (const lang of LANGS) {
    it(`${lang}: no plan code, no engine key, no raw rung id`, () => {
      setLang(lang);
      const t = text(html(<ReportDocument report={german} findings={findings} />));
      none(t, PLAN);
      none(t, ENGINE);
      // a register key beside its title is the register's key (the ruling of 2026-10-27), not a raw id
      none(findings.rows.reduce((s, r) => s.split(r.key).join(' '), t), RUNG_ID);
    });
  }

  it('es: the model-description sentence keeps the entry title and the reading in Spanish', () => {
    const block = german.sections[1].blocks[0];
    if (block.kind !== 'text') throw new Error('section 2 opens on a sentence');
    const es = reportSentence(block.text, 'C01', 'es');
    expect(es).toContain('PD de tarjetas: campeón vs retador');
    expect(es).toContain('lectura B');
    expect(es).not.toMatch(/Retail cards|reading B/);
  });

  it('section 10 puts the title of each finding beside its register key', () => {
    for (const lang of LANGS) {
      setLang(lang);
      const m = html(<ReportDocument report={german} findings={findings} />);
      const s10 = m.slice(m.indexOf('data-section="10"'), m.indexOf('data-section="11"'));
      const row = findings.rows.find((r) => r.key === 'C01/german-twin/F-CF-P4-lightgbm');
      expect(row, 'the register holds the finding').toBeTruthy();
      expect(text(s10), lang).toContain(row!.title[lang]);
    }
  });

  it('a graded test row names its grade, so the rows of one test and one model are told apart (C01 grades G08, G10, G11)', () => {
    for (const lang of LANGS) {
      setLang(lang);
      const t = text(html(<ReportDocument report={german} findings={findings} />));
      for (const g of ['G08', 'G10', 'G11']) expect(t, `${lang} ${g}`).toContain(lang === 'es' ? `grado ${g}` : `grade ${g}`);
    }
  });
});

describe('the register and the inventory in reader words (R3 c23 B3, B5)', () => {
  afterEach(() => setLang('en'));

  for (const lang of LANGS) {
    it(`${lang}: the register, its anchor reasons and its as-of basis carry no plan code and no engine key`, () => {
      setLang(lang);
      const t = text(html(<RegisterSection findings={findings} />));
      none(t, PLAN);
      none(t, ENGINE);
    });
    it(`${lang}: the inventory tab carries no plan code`, () => {
      setLang(lang);
      const t = text(html(<InventoryTab inv={inv} />));
      none(t, PLAN);
    });
  }

  it('readerWords: the codes leave the sentence whole, the engine keys become words', () => {
    expect(readerWords('W15-13: the date of the newest release heading', 'en')).toBe('The date of the newest release heading');
    expect(readerWords('open results or stated limits (W15-5)', 'es')).toBe('open results or stated limits');
    expect(readerWords('open and overdue findings, not risk_accepted', 'en')).toBe('open and overdue findings, not risk accepted');
    expect(readerWords('hallazgos abiertos y vencidos, no risk_accepted', 'es')).toBe('hallazgos abiertos y vencidos, no aceptados como riesgo');
    expect(readerWords('1 fila roja sobre el margen inicial medio frente al dim_cube de ORE', 'es')).toBe('1 fila roja sobre el margen inicial medio frente al cubo de margen inicial dinámico de ORE');
    expect(readerWords('la evidencia no es una fila test_id@modelo (es design:, contract:, rate: o un id de prueba sin modelo), por lo que no se lee estadístico', 'es')).toBe(
      'el hallazgo cita un límite de diseño, una verificación de contrato o una tasa, no una fila de prueba de un modelo, por lo que no se lee estadístico',
    );
  });
});

describe('the dependency map has the rubric interactions (R3 c23 M4)', () => {
  afterEach(() => setLang('en'));

  it('zoom in, zoom out and reset controls, focusable nodes with a name, and a read-out line', () => {
    for (const lang of LANGS) {
      setLang(lang);
      const m = html(<MapDrawing inv={inv} width={640} height={400} />);
      expect(m.match(/data-map-zoom="(in|out|reset)"/g)?.length, lang).toBe(3);
      const focusable = m.match(/<g[^>]*data-node="C\d\d\/[^"]+"[^>]*tabindex="0"/g)?.length ?? 0;
      expect(focusable, lang).toBe(inv.entries.length);
      expect(m, lang).toMatch(/data-map-readout[^>]*aria-live="polite"/);
    }
  });
});
