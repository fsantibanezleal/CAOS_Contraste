// The engine's report sentences read whole in words (fix round 3, the raw-id ruling): over every committed governance report,
// no text block shows the fit id, a source id or "its 1 variants" once read, in either language.
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { reportSentence } from './ReportView';
import { sourceName } from '../names';

const dir = fileURLToPath(new URL('../../../../data/derived/governance/reports/', import.meta.url));
type Block = { kind: string; text?: { en: string; es: string } };
type Report = { entry_key: string; sections: Array<{ blocks?: Block[] }> };
const reports = readdirSync(dir)
  .filter((f) => f.endsWith('.json'))
  .map((f) => JSON.parse(readFileSync(join(dir, f), 'utf8')) as Report);

describe('the report sentences', () => {
  it('name the fit and the sources and agree their counts, in both languages, in every committed report', () => {
    const bad: string[] = [];
    for (const r of reports) {
      const [caseId, fit] = r.entry_key.split('/');
      for (const s of r.sections) {
        for (const b of s.blocks ?? []) {
          if (b.kind !== 'text' || !b.text) continue;
          for (const lang of ['en', 'es'] as const) {
            const out = reportSentence(b.text, caseId, lang);
            if (new RegExp(`(the fit|el ajuste) ${fit}\\b`).test(out)) bad.push(`${r.entry_key} ${lang}: ${out}`);
            if (/\b1 (variants|variantes|register rows|filas del registro|model records|registros de modelo)\b/.test(out)) bad.push(`${r.entry_key} ${lang}: ${out}`);
            if (/^(Sources|Fuentes): /.test(out) && /\b[a-z]+(?:-[a-z0-9]+)+\b/.test(out.replace(/^(Sources|Fuentes): /, ''))) {
              // a source id left as written means the names table lacks it
              const ids = out.replace(/^(Sources|Fuentes): /, '').replace(/\.$/, '').split('; ').filter((x) => !sourceName(x) && /^[a-z0-9-]+$/.test(x));
              if (ids.length) bad.push(`${r.entry_key} ${lang}: ${ids.join(', ')}`);
            }
          }
        }
      }
    }
    expect(bad).toEqual([]);
  });

  it('reads the scope sentence of the German fit in words', () => {
    const t = {
      en: 'Scope: the fit german of case C01; the full battery of the default variant (184 test rows) and the findings of its 1 variants.',
      es: 'Alcance: el ajuste german del caso C01; la batería completa de la variante por defecto (184 filas de prueba) y los hallazgos de sus 1 variantes.',
    };
    expect(reportSentence(t, 'C01', 'en')).toBe('Scope: C01, German Credit fit; the full battery of the default variant (184 test rows) and the findings of its one variant.');
    expect(reportSentence(t, 'C01', 'es')).toBe('Alcance: C01, Ajuste German Credit; la batería completa de la variante por defecto (184 filas de prueba) y los hallazgos de su única variante.');
  });

  it('shows any other sentence as the document writes it', () => {
    const t = { en: 'A sentence the engine may write one day.', es: 'Una frase que el motor podría escribir algún día.' };
    expect(reportSentence(t, 'C01', 'es')).toBe(t.es);
  });
});
