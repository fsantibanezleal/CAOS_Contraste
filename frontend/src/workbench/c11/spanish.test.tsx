// U16-R2 (b05 B1, B3, B5, M1, M2): the Spanish views of C11 translate the engine notes and reasons, name the units and the truth status, show
// the missing champion's reason and print the exceedance counts with their decimals. Reads the committed documents (the 1.0 bake).
import { afterEach, describe, expect, it } from 'vitest';
import { setLang } from '../c03/u6-testkit';
import { committedData, view } from '../c08/spanish-testkit';
import { C11ContextView, C11VariantsTable, COUNT_AXIS } from './C11Common';
import type { VariantArtifact } from '../../lib/contract.types';
import type { C11Outputs } from './selection';
import { ChampionView } from './ComparisonViews';
import { TimelineView, ZonesView } from './ExceedanceViews';
import { EsBacktestView, TestsView } from './BacktestViews';
import { defaultSel } from './selection';

const title = { en: 'Market VaR and ES back-testing', es: 'Backtesting de VaR y ES de mercado' };
const calm = committedData('C11', 'calm-2004-06.json', 'models-ladder.json', title);
const crisis = committedData('C11', 'equity-2007-09.json', 'models-ladder.json', title);
const ENGLISH = [
  /real-outcomes/, /\b\d+ days\b/, /\bexpected count\b/, /\bnot evaluated\b/, /\bexceedances? in\b/, /critical values are simulated/, /fewer than \d+ forecast days/,
  /no eligible model/, /derived-only source/, /challenger only/, /the model forecasts no ES/, /Weibull shape/,
];

describe('the Spanish views of C11', () => {
  afterEach(() => setLang('en'));

  it('the context names the truth status and the units in Spanish and the withheld loss series with its reason', () => {
    setLang('es');
    for (const data of [calm, crisis]) {
      const text = view(<C11ContextView sel={defaultSel(data)} />);
      for (const re of ENGLISH) expect(text, String(re)).not.toMatch(re);
    }
    expect(view(<C11ContextView sel={defaultSel(calm)} />)).toContain('Resultados reales');
    expect(view(<C11ContextView sel={defaultSel(calm)} />)).toMatch(/\d días/);
  });

  it('the backtest, zone, comparison and timeline views translate every engine note and reason', () => {
    setLang('es');
    for (const data of [calm, crisis]) {
      for (const [name, V] of [['Tests', TestsView], ['ES', EsBacktestView], ['Zones', ZonesView], ['Timeline', TimelineView], ['Champion', ChampionView]] as const) {
        const text = view(<V sel={defaultSel(data)} />);
        for (const re of ENGLISH) expect(text, `${name} ${re}`).not.toMatch(re);
      }
    }
  });

  it('the champion view says why a window has no champion', () => {
    setLang('es');
    expect(view(<ChampionView sel={defaultSel(crisis)} />)).toContain('ningún modelo es elegible: cada modelo falla al menos una compuerta');
  });

  it('the exceedance bars keep their decimals (2.49 expected, not 2)', () => {
    expect(COUNT_AXIS).toEqual({ digits: 3 });
  });

  it('the windows table gives the reason of a window with no champion (b05 M2)', () => {
    setLang('es');
    const v = crisis.variant as unknown as VariantArtifact<C11Outputs>;
    const text = view(<C11VariantsTable variants={[{ id: v.variant_id, title: { en: 'Equity 2007 to 2009', es: 'Renta variable 2007 a 2009' }, v }]} onPick={() => undefined} current={v.variant_id} />);
    expect(text).toContain('sin campeón. Motivo: ningún modelo es elegible: cada modelo falla al menos una compuerta');
  });
});
