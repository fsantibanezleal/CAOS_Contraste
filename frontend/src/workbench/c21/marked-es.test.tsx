// The release gate's Spanish-rendering fixes: a source reference (a regulation citation, a row of an annex, the sum of rows a label
// names) is marked translate="no" and nothing else is; an engine note is read in Spanish with its number written with a comma.
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { Marked } from './Marked';
import { engineNote } from '../c03/U6Shared';

const html = (text: string): string => renderToStaticMarkup(<Marked>{text}</Marked>);

describe('Marked marks only the source reference', () => {
  it('keeps a CFR citation as the source writes it', () => {
    expect(html('Raza: marcado Black (4/5, 29 CFR 1607.4)')).toContain('<span translate="no" lang="en">29 CFR 1607.4</span>');
  });
  it('marks a row of an annex in both languages and leaves the words around it translatable', () => {
    expect(html('and row 10.2 of the Annex 3 is N/A')).toBe('and <span translate="no" lang="en">row 10.2</span> of the Annex 3 is N/A');
    expect(html('la fila 10.2 del Anexo 3 es N/A')).toBe('la <span translate="no" lang="es">fila 10.2</span> del Anexo 3 es N/A');
  });
  it('marks the sum of rows a label names, not the label', () => {
    expect(html('Cuantificación del capital necesario por riesgos no cubiertos en pilar 1 (4.4+4.5+4.6)')).toBe(
      'Cuantificación del capital necesario por riesgos no cubiertos en pilar 1 <span translate="no">(4.4+4.5+4.6)</span>',
    );
  });
  it('marks the row arithmetic of the Annex 3 labels but keeps a short percent range a plain no-break range', () => {
    for (const sum of ['(8%+7.1+7.2)', '(6-7.2)', '(1.1 - 5)']) expect(html(`Exigencia ${sum}`)).toBe(`Exigencia <span translate="no">${sum}</span>`);
    expect(html('de (36%-49%) a')).toContain('white-space:nowrap');
    expect(html('de (36%-49%) a')).not.toContain('translate="no"');
  });
  it('does not wrap a sentence that holds no reference', () => {
    expect(html('Sin referencias en este texto')).toBe('Sin referencias en este texto');
  });
});

describe('engineNote reads the engine notes of the validation in Spanish', () => {
  it('writes the correlation with a decimal comma in Spanish and leaves English as it is', () => {
    expect(engineNote('asset correlation 0.12 is a modelling assumption', 'es')).toBe('la correlación de activos 0,12 es un supuesto de modelación');
    expect(engineNote('asset correlation 0.12 is a modelling assumption', 'en')).toBe('asset correlation 0.12 is a modelling assumption');
  });
  it('translates the conventional bands whole', () => {
    expect(engineNote('conventional band: moderate change (0.10/0.25 rule of thumb, no error control)', 'es')).toBe(
      'banda convencional: cambio moderado (regla práctica de 0,10/0,25, sin control del error)',
    );
  });
  it('shows a note it does not know as it comes', () => {
    expect(engineNote('a note the engine may write tomorrow, 1.5', 'es')).toBe('a note the engine may write tomorrow, 1.5');
  });
});
