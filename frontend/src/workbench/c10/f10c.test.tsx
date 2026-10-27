// U16-F10c (R3 batch c11, C10): every tests table shows the segment of its rows (n3, ruled major: twelve Euler rows read the same),
// the Spanish page writes the words the view owns in Spanish (no "Backtest", "bootstrap", "kernel"), the ladder's inputs write the
// Greek parameters as symbols and no repeated unit word, the references of the ladder join their authors with "y" in Spanish, the
// percent literals take the shell's no-break space, the grid estimates print the RMSE as the bias is printed, and the Variants card
// carries the truth status of the loaded variant. Reads the committed documents, in both languages.
import { formatNumber } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { fixtureData, html, setLang } from '../c03/u6-testkit';
import { committed, committedData, view } from '../c08/spanish-testkit';
import { ContributionsView, GranularityView, RungsView } from './CapitalViews';
import { C10TestsTable, C10VariantsTable } from './C10Common';
import { CorrelationView, FittedView, IrbView, BacktestView } from './FitViews';
import { LadderView } from './ModelViews';
import { EstimatesView, SizePowerView } from './SimulatorViews';
import { useInstrument as useC10Instrument } from './instrument';
import { defaultSel, measureText, PARAMETER_TEXT, DIAGNOSTIC_TEXT, referenceNote, type C10Sel } from './selection';

const TITLE = { en: 'Portfolio credit risk', es: 'Riesgo de crédito de cartera' };
const LOANS = ['commercial-industrial', 'commercial-real-estate', 'credit-cards', 'other-consumer', 'residential'];
const GRIDS = ['grid-22', 'grid-40'];
const selOf = (v: string) => defaultSel(committedData('C10', `${v}.json`, 'models-c10.json', TITLE)) as C10Sel;
const rowsOf = (m: string, table: string) => {
  const t = new RegExp(`<table[^>]*data-table="${table}"[^>]*>(.*?)</table>`, 's').exec(m)?.[1] ?? '';
  return [...t.matchAll(/<tr[^>]*data-test="[^"]*"[^>]*>(.*?)<\/tr>/gs)].map((r) => r[1].replace(/<[^>]*>/g, '|').replace(/\|+/g, '|'));
};

function viewWordsOnly(v: string) {
  const blank = (x: unknown): unknown => {
    if (Array.isArray(x)) return x.map(blank);
    if (x && typeof x === 'object') {
      const o = x as Record<string, unknown>;
      if (typeof o.en === 'string' && typeof o.es === 'string') return { ...o, es: '·' };
      return Object.fromEntries(Object.entries(o).map(([k, val]) => [k, blank(val)]));
    }
    return x;
  };
  return defaultSel(fixtureData('C10', blank(committed<VariantArtifact>('C10', `${v}.json`)) as VariantArtifact, blank(committed<ModelsArtifact>('C10', 'models-c10.json')) as ModelsArtifact, TITLE)) as C10Sel;
}
function Groups({ sel }: { sel: C10Sel }) {
  const inst = useC10Instrument(sel.data, () => undefined);
  // the Findings card prints the evidence names of the shared names module (names/tests.ts, U16-F10a's file)
  const groups = inst ? inst.groups.filter((g) => g.id !== 'findings') : [];
  return <div>{inst ? [...groups.map((g) => <section key={g.id}>{g.content}</section>), ...inst.rail.map((r) => <section key={r.id}>{r.content}</section>)] : null}</div>;
}

describe('U16-F10c, C10 (R3 c11)', () => {
  afterEach(() => setLang('en'));

  it('n3: the tests table shows the segment of each row, so no two rows read the same', () => {
    for (const v of [...LOANS, ...GRIDS]) {
      const variant = committed<VariantArtifact>('C10', `${v}.json`);
      for (const lang of ['en', 'es'] as const) {
        setLang(lang);
        const markup = html(<C10TestsTable variant={variant} />);
        expect(markup, v).toMatch(lang === 'en' ? /<th[^>]*>Segment<\/th>/ : /<th[^>]*>Segmento<\/th>/);
        const rows = rowsOf(markup, 'tests');
        expect(rows.length, v).toBe(variant.tests.length);
        expect(new Set(rows).size, `${v} ${lang}: rows that read the same`).toBe(rows.length);
        expect(markup).not.toMatch(/>(var|es)-0\.99+</);
      }
    }
    setLang('en');
    // view() reads the text as a reader does (a no-break space is a space)
    const euler = view(<ContributionsView sel={selOf('commercial-industrial')} />);
    expect(euler).toContain('VaR at 99.9 %');
    expect(euler).toContain('ES at 99 %');
    setLang('es');
    expect(view(<ContributionsView sel={selOf('commercial-industrial')} />)).toContain('ES al 99,9 %');
  });

  it('the Spanish page writes the words the view owns in Spanish: no Backtest, bootstrap or kernel', () => {
    setLang('es');
    for (const v of ['commercial-industrial', 'grid-22']) {
      const sel = viewWordsOnly(v);
      const own = [<Groups key="g" sel={sel} />, <CorrelationView key="c" sel={sel} />, <BacktestView key="b" sel={sel} />, <RungsView key="r" sel={sel} />, <GranularityView key="gr" sel={sel} />, <SizePowerView key="s" sel={sel} />, <EstimatesView key="e" sel={sel} />]
        .map((el) => view(el))
        .join(' ');
      expect(own, v).not.toMatch(/\bback-?tests?\b/i);
      expect(own, v).not.toMatch(/\bbootstrap\b/i);
      expect(own, v).not.toMatch(/\bkernel\b/i);
    }
    expect(view(<C10TestsTable variant={committed<VariantArtifact>('C10', 'commercial-industrial.json')} />)).toContain('Prueba retrospectiva de cola de los años de evaluación');
  });

  it('n4 and n5: a parameter or diagnostic is written once, with its symbol, never with a repeated unit word', () => {
    expect(measureText(DIAGNOSTIC_TEXT, 'variance_ratio_vs_plain_mc', 388.7, 'ratio', 'en')).toBe('variance ratio against plain Monte Carlo 388.7');
    expect(measureText(DIAGNOSTIC_TEXT, 'effective_sample_share', 0.0001666, 'share', 'es')).toBe('proporción de muestra efectiva 0,0001666');
    expect(measureText(DIAGNOSTIC_TEXT, 'n_max', 12728, 'loss units', 'en')).toBe('maximum loss units 12,728');
    expect(measureText(PARAMETER_TEXT, 'pd', 0.009105, 'decimal', 'en')).toBe('PD 0.009105');
    expect(measureText(PARAMETER_TEXT, 'rho', 0.06368, '-', 'en')).toBe('ρ 0.06368');
    for (const [k, s] of [['nu', 'ν'], ['xi', 'ξ'], ['gamma', 'γ'], ['sigma2', 'σ²']]) expect(PARAMETER_TEXT[k]?.en, k).toBe(s);
    const ladder = view(<LadderView sel={selOf('commercial-real-estate')} />);
    expect(ladder).not.toMatch(/\b(rho|nu|xi|gamma|sigma2) \d/);
    expect(ladder).not.toMatch(/\d decimal\b/);
  });

  it('n1: the ladder references join their authors with "y" in Spanish; the English stays as published', () => {
    const fit = committed<ModelsArtifact>('C10', 'models-c10.json') as unknown as { fit: { ladder: Array<{ reference: string }> } };
    for (const r of fit.fit.ladder) {
      expect(referenceNote(r.reference, 'en')).toBe(r.reference);
      expect(referenceNote(r.reference, 'es'), r.reference).not.toMatch(/ and |December/);
    }
    setLang('es');
    expect(view(<LadderView sel={selOf('commercial-industrial')} />)).toContain('Frey y McNeil (2003)');
    expect(view(<GranularityView sel={selOf('commercial-industrial')} />)).not.toMatch(/Gordy and Lutkebohmert/);
  });

  it('n7: a percent literal takes the no-break space the shell writes ("99.9 %", never "99.9%")', () => {
    const sel = selOf('commercial-industrial');
    const markup = [<FittedView key="f" sel={sel} />, <IrbView key="i" sel={sel} />].map((el) => view(el)).join(' ');
    expect(markup).not.toMatch(/\d%/);
  });

  it('m-U: the grid estimates print the RMSE in percent, as the bias beside it', () => {
    const sel = selOf('grid-22');
    const markup = view(<EstimatesView sel={sel} />);
    const g = committed<{ outputs: { cells: Array<{ estimators: Array<{ rmse: number }> }> } }>('C10', 'grid-22.json').outputs;
    for (const c of g.cells) for (const e of c.estimators) expect(markup).toContain(formatNumber(e.rmse, 'en', { percent: true, decimals: 2 }).replace(/\s/g, ' '));
  });

  it('m-P: the Variants card carries the truth status of the loaded variant', () => {
    const variants = [...LOANS, ...GRIDS].map((id) => ({ id, title: { en: id, es: id }, v: committed<VariantArtifact>("C10", `${id}.json`) })) as unknown as Parameters<typeof C10VariantsTable>[0]['variants'];
    for (const current of ['commercial-industrial', 'grid-22']) {
      const markup = html(<C10VariantsTable variants={variants} onPick={() => undefined} current={current} />);
      const prov = /data-provenance="([^"]+)"/.exec(markup)?.[1];
      expect(prov, current).toBe(current.startsWith('grid') ? 'synthetic' : 'real');
    }
  });

  it('m8: the ladder note says why an analytic rung has no bar', () => {
    expect(view(<LadderView sel={selOf('commercial-industrial')} />)).toContain('its bar reads not available');
  });
});
