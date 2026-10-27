// U16-F4 (the U16-R2 capture review, batch b07): the Spanish view of C15 carries no English prose and no snake_case id, the net UF
// position and the amount column say their scale, and the formulas keep their symbols and translate their words. Every view is
// rendered on the six committed variants.
import { afterEach, describe, expect, it } from 'vitest';
import type { ReactElement } from 'react';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc, englishLeaks, fixtureData, html, setLang, visibleText } from '../c14/testkit';
import { defaultSel, type C15Sel } from './selection';
import { C15ContextView, C15FindingsView } from './C15Common';
import { DynamicLegView, EarEvarLegView, EveByLegView, PositionsView } from './LegViews';
import { IndexationView, NiiView } from './RateViews';
import { FloorsView, ThresholdsView, thresholdsChart } from './FloorViews';

const NAMES = ['clp-steepener', 'cpi-surprise', 'floors-active', 'long-uf', 'offset-on-off', 'short-uf'] as const;
const models = committedDoc<ModelsArtifact>('C15', 'models-banco-andino-2026-09');
const title = { en: 'IRRBB on a CLP and UF balance sheet', es: 'IRRBB sobre un balance en CLP y UF' };
const selOf = (name: string): C15Sel => defaultSel(fixtureData('C15', committedDoc<VariantArtifact>('C15', name), models, title)) as C15Sel;

const VIEWS: Array<[string, (p: { sel: C15Sel | null }) => ReactElement]> = [
  ['EveByLeg', EveByLegView], ['Positions', PositionsView], ['DynamicLeg', DynamicLegView], ['EarEvarLeg', EarEvarLegView], ['Nii', NiiView],
  ['Indexation', IndexationView], ['Floors', FloorsView], ['Thresholds', ThresholdsView], ['Findings', C15FindingsView], ['Context', C15ContextView],
];
const SYMBOLS = ['pn_ur', 'surprise_pp', 'apply_floor', 'nmd_segments', 'term_deposit_redemption_rate'];
const VERBATIM = ['Banco Central de Chile', 'Nelson-Siegel', 'Svensson', 'riskvalidation', 'Contraste', 'Banco Andino'];

describe('U16-F4 C15: the Spanish view', () => {
  afterEach(() => setLang('en'));

  it('V15-1 and V15-5: no view of the Spanish capture carries English prose or a snake_case id, on the six committed documents', () => {
    setLang('es');
    const all: string[] = [];
    for (const name of NAMES) {
      for (const [view, View] of VIEWS) {
        const text = visibleText(html(<View sel={selOf(name)} />));
        for (const leak of englishLeaks(text, VERBATIM)) all.push(`${name} ${view} ${leak}`);
        // a symbol or an engine function of a formula is kept; the evidence ids of the shared findings card are that card's
        if (view !== 'Findings') for (const id of text.match(/\b[a-z]+(?:_[a-z0-9]+)+\b/g) ?? []) if (!SYMBOLS.includes(id)) all.push(`${name} ${view} id ${id}`);
      }
    }
    expect([...new Set(all)]).toEqual([]);
  });

  it('V15-2: the net UF position is labelled with its scale (millions of UF), in both languages', () => {
    const en = visibleText(html(<IndexationView sel={selOf('long-uf')} />));
    expect(en).toContain('Net UF position (UF millions)');
    setLang('es');
    expect(visibleText(html(<IndexationView sel={selOf('long-uf')} />))).toContain('Posición neta en UF (millones de UF)');
  });

  it('V15-3: the formulas keep their symbols and translate their words in Spanish', () => {
    setLang('es');
    const text = visibleText(html(<IndexationView sel={selOf('cpi-surprise')} />));
    // the bilingual formulas of the c15-outputs 3.0.0 producer (pipeline/cases/c15/variant.py), re-baked
    expect(text).toContain('cargo = 0,025 × |PN_UR|, donde PN_UR es la posición neta en UF por el valor de la UF');
    // R3 c16 Q (U16-F10a): symbols with a legend, never the engine keys pn_ur and surprise_pp
    expect(text).toContain('efecto = −PN_UR × s / 100, positivo es una pérdida, donde PN_UR es la posición neta en UF en CLP y s la sorpresa de IPC en puntos porcentuales');
    expect(text).not.toMatch(/pn_ur|surprise_pp/);
    expect(text).not.toContain('charge =');
  });

  it('V15-6: the amount column of the leg items names the scale of the document', () => {
    expect(visibleText(html(<PositionsView sel={selOf('long-uf')} />))).toContain('Amount (CLP millions)');
    setLang('es');
    expect(visibleText(html(<PositionsView sel={selOf('long-uf')} />))).toContain('Monto (millones de CLP)');
  });

  it('V15-4: the y titles of the charts are short enough for a 390 px plot', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const chart = thresholdsChart(selOf('long-uf'));
      expect((chart?.y.label as { en: string; es: string } | undefined)?.[lang].length ?? 0).toBeLessThanOrEqual(24);
    }
  });
});
