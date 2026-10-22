// U16-R2 (b05 B2, B6, B7, M4): the Spanish views of C10 name the Federal Reserve series, the sectors, the rung reasons and the diagnostics in
// Spanish, and the ladder draws no scenarios for a rung that did not run. Reads the committed documents (the 1.0 bake the review read).
import { afterEach, describe, expect, it } from 'vitest';
import { html, setLang } from '../c03/u6-testkit';
import { committedData, view } from '../c08/spanish-testkit';
import { C10ContextView, C10FindingsView } from './C10Common';
import { ContributionsView, GranularityView, RungsView } from './CapitalViews';
import { LadderView, PortfolioView } from './ModelViews';
import { defaultSel } from './selection';

const title = { en: 'Portfolio credit risk', es: 'Riesgo de crédito de cartera' };
const loan = committedData('C10', 'commercial-industrial.json', 'models-c10.json', title);
const residential = committedData('C10', 'residential.json', 'models-c10.json', title);
const grid = committedData('C10', 'grid-22.json', 'models-c10.json', title);
const sel = defaultSel(loan)!;

const ENGLISH = [
  /\bcore\b/, /\bperiphery\b/, /C&amp;I|column CI|\(column \w+ of the table\)/, /\bSA, all-banks\b/, /fed-chargeoff/, /Board(&#x27;|')s table/,
  /weight on the systematic factor/, /exponential twist/, /granularity adjustment is a quantile/, /\bloss units\b/, /variance_ratio/, /tail_mass/, /\bn_max\b/,
  /unit_rounding/, /effective_sample_share/, /expected_loss/, /\d,\d{3} bytes/,
];

describe('the Spanish views of C10', () => {
  afterEach(() => setLang('en'));

  it('the context names the series, its adjustment, its source and the missing quarters in Spanish', () => {
    setLang('es');
    for (const data of [loan, residential]) {
      const text = view(<C10ContextView sel={defaultSel(data)} />);
      for (const re of ENGLISH) expect(text, String(re)).not.toMatch(re);
    }
    const text = view(<C10ContextView sel={defaultSel(residential)} />);
    expect(text).toContain('Préstamos inmobiliarios residenciales (columna RERES de la tabla)');
    expect(text).toContain('Ajustada por estacionalidad, todos los bancos');
    expect(text).toContain('la tabla de la Junta los marca n.d. para este tipo de crédito');
    setLang('en');
    expect(view(<C10ContextView sel={defaultSel(residential)} />)).toContain("the Board's table marks them n.a. for this loan type");
  });

  it('the simulator context says what the generator is shaped on in Spanish', () => {
    setLang('es');
    const text = view(<C10ContextView sel={defaultSel(grid)} />);
    expect(text).not.toMatch(/yearly default fractions|vasicek-lhp-simulator/);
    expect(text).toContain('Simulador de Vasicek de una cartera homogénea grande');
  });

  it('the portfolio names its sectors, the rungs and the granularity view state their reasons and diagnostics in Spanish', () => {
    setLang('es');
    for (const V of [PortfolioView, RungsView, GranularityView, ContributionsView, LadderView]) {
      const text = view(<V sel={sel} />);
      for (const re of ENGLISH) expect(text, `${V.name} ${re}`).not.toMatch(re);
    }
    expect(view(<PortfolioView sel={sel} />)).toMatch(/núcleo/);
    expect(view(<PortfolioView sel={sel} />)).toMatch(/periferia/);
    expect(view(<RungsView sel={sel} />)).toContain('unidades de pérdida');
  });

  it('the findings write their numbers the Spanish way', () => {
    setLang('es');
    const text = view(<C10FindingsView sel={sel} />);
    expect(text).not.toMatch(/\d\.\d{2}\b(?! %)|\d,\d{3} nombres|\d%/);
    expect(text).toContain('1.120 nombres');
  });

  it('the ladder draws no scenarios for a rung that did not run', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const markup = html(<LadderView sel={sel} />);
      const row = markup.slice(markup.indexOf('data-rung="c6-is-student-t"'));
      const cell = row.slice(0, row.indexOf('</tr>'));
      expect(cell, lang).toContain('data-na="true"');
      expect(cell, lang).not.toMatch(/100[.,]000/);
    }
  });
});
