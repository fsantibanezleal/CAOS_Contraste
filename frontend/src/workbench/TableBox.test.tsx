// BL-107 (release 1.01.000): the table-heavy and bar-list views pass the gate's G6 floors at 2560 x 1440 (a drawing at least 30 % of its
// stage, the App's drawn views at least 60 % of the viewport). On a tall desktop a card's table takes its stage: it is the card body's own
// child (the shell's rule `.caos-plot.fill > .caos-plot-body > .caos-table { height: 100% }`), a card with a list or another table beside it
// shares the height among its tables, C09's bars fill their card, its floors card drops the fixed 9 rem, and C11's verdict card fills.
// Under a tall desktop (1280 x 800, 1600 x 900, a phone) every card keeps the layout it had.
import type { BarChartProps } from '@fasl-work/caos-app-shell';
import { PlotCard } from '@fasl-work/caos-app-shell';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { html, setLang } from './c03/u6-testkit';
import { committedData } from './c08/spanish-testkit';
import { ByDesignView } from './c09/CcfViews';
import { FloorsView } from './c09/EadViews';
import { defaultSel as c09Default, type C09Sel } from './c09/selection';
import { ConformalVerdictView } from './c11/ConformalViews';
import { defaultSel as c11Default, type C11Sel } from './c11/selection';
import { TALL_QUERY, TableBox } from './TableBox';

const screen = vi.hoisted(() => ({ tall: false, asked: [] as string[] }));
vi.mock('../lib/useMedia', () => ({
  useMedia: (query: string) => (screen.asked.push(query), query.includes('min-height: 1100px') ? screen.tall : false),
  useFindingsShares: () => [2, 1],
}));
const bars = vi.hoisted(() => [] as BarChartProps[]);
vi.mock('@fasl-work/caos-app-shell', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell')>();
  return { ...mod, BarChart: (p: BarChartProps) => (bars.push(p), mod.BarChart(p)) };
});

beforeEach(() => {
  screen.tall = false;
  screen.asked.length = 0;
  bars.length = 0;
});
afterEach(() => setLang('en'));

const card = { lane: 'replay', provenance: 'synthetic' } as const;
const cardOf = (children: React.ReactNode) => renderToStaticMarkup(<PlotCard fill title={{ en: 'T', es: 'T' }} {...card}>{children}</PlotCard>);
const body = (markup: string) => /<div class="caos-plot-body">([\s\S]*?)<\/div>(?:<p class="caos-plot-note">|<\/figure>)/.exec(markup)?.[1] ?? '';
const one = <table className="caos-table" data-table="one"><tbody><tr><td>1</td></tr></tbody></table>;
const two = (
  <>
    <table className="caos-table" data-table="a"><tbody><tr><td>1</td></tr></tbody></table>
    <dl className="ct-defs"><dt>k</dt><dd>v</dd></dl>
    <table className="caos-table ct-wrap-head" data-table="b"><tbody><tr><td>2</td></tr></tbody></table>
  </>
);

describe('BL-107, TableBox: the switch at the tall desktop', () => {
  it('asks for a screen at least 1100 px tall and 1280 px wide', () => {
    cardOf(<TableBox>{one}</TableBox>);
    expect(screen.asked).toContain(TALL_QUERY);
    expect(TALL_QUERY).toBe('(min-height: 1100px) and (min-width: 1280px)');
  });

  it('a table that is alone is the card body\'s own child on a tall desktop, with no scroll box', () => {
    screen.tall = true;
    const b = body(cardOf(<TableBox block="numbers">{one}</TableBox>));
    expect(b).toMatch(/^<table class="caos-table" data-table="one" data-block="numbers">/);
    expect(b).not.toContain('ct-scroll');
  });

  it('keeps the table inside the scroll box below a tall desktop', () => {
    const b = body(cardOf(<TableBox block="numbers">{one}</TableBox>));
    expect(b).toMatch(/^<div class="ct-scroll" data-caos-flow="" data-block="numbers"><table class="caos-table" data-table="one">/);
  });

  it('shares the card\'s height among several tables and keeps a list and a note at their own height on a tall desktop', () => {
    screen.tall = true;
    const b = body(cardOf(<TableBox block="numbers">{two}</TableBox>));
    expect(b).toMatch(/^<div class="ct-scroll ct-tall-tables" data-caos-flow="" data-block="numbers">/);
    expect(b).toContain('<table class="caos-table ct-fill-table" data-table="a">');
    expect(b).toContain('<table class="caos-table ct-wrap-head ct-fill-table" data-table="b">');
    expect(b).toContain('<dl class="ct-defs">');
    expect(b).not.toMatch(/<dl[^>]*ct-fill-table/);
  });

  it('keeps several tables in the one scroll box below a tall desktop', () => {
    const b = body(cardOf(<TableBox block="numbers">{two}</TableBox>));
    expect(b).toMatch(/^<div class="ct-scroll" data-caos-flow="" data-block="numbers">/);
    expect(b).not.toContain('ct-fill-table');
    expect(b).not.toContain('ct-tall-tables');
  });

  it('a component that renders one table is the body\'s child on a tall desktop when it says so (lone)', () => {
    const Reverse = () => <table className="caos-table" data-table="reverse"><tbody><tr><td>1</td></tr></tbody></table>;
    screen.tall = true;
    expect(body(cardOf(<TableBox lone><Reverse /></TableBox>))).toMatch(/^<table class="caos-table" data-table="reverse">/);
    screen.tall = false;
    expect(body(cardOf(<TableBox lone><Reverse /></TableBox>))).toMatch(/^<div class="ct-scroll" data-caos-flow=""><table/);
  });

  it('a card that does not fill below a tall desktop stays a plain box at its content\'s height (natural)', () => {
    expect(body(cardOf(<TableBox natural attrs={{ 'data-block': 'x' }}>{two}</TableBox>))).toMatch(/^<div data-block="x"><table/);
    screen.tall = true;
    expect(body(cardOf(<TableBox natural attrs={{ 'data-block': 'x' }}>{two}</TableBox>))).toMatch(/^<div class="ct-scroll ct-tall-tables" data-caos-flow="" data-block="x">/);
  });
});

describe('BL-107, the views of the classes B1, B2 and N1', () => {
  const C09_TITLE = { en: 'EAD and CCF for revolving lines', es: 'EAD y CCF de líneas rotativas' };
  const c09 = () => c09Default(committedData('C09', 'level-3.json', 'models-generator.json', C09_TITLE)) as C09Sel;
  const C11_TITLE = { en: 'Market VaR and ES back-testing', es: 'Pruebas retrospectivas de VaR y ES de mercado' };
  const c11 = () => c11Default(committedData('C11', 'equity-2007-09.json', 'models-ladder.json', C11_TITLE)) as C11Sel;
  const cards = (m: string) => m.split('<figure class="caos-plot').slice(1);

  it('B1: C09 By design draws its bars as the card body\'s child with height fill on a tall desktop, in a scroll box below it', () => {
    screen.tall = true;
    const tall = cards(html(<ByDesignView sel={c09()} />))[0];
    expect(tall).not.toContain('data-scroll-box');
    expect(body(tall)).toMatch(/^<div class="caos-bars-host fill">/);
    expect(bars.at(-1)?.height).toBe('fill');
    expect(bars.at(-1)?.orientation).toBe('horizontal');
    // its table is the second card's own child
    expect(cards(html(<ByDesignView sel={c09()} />))[1]).toMatch(/<div class="caos-plot-body"><table class="caos-table ct-wrap-head" data-table="ccf-by-design"/);
    screen.tall = false;
    bars.length = 0;
    const short = cards(html(<ByDesignView sel={c09()} />));
    expect(short[0]).toMatch(/data-scroll-box=""[^>]*data-block="ccf-chart"/);
    expect(bars.at(-1)?.height).toBeUndefined();
    expect(short[1]).toMatch(/<div class="caos-plot-body"><div class="ct-scroll" data-caos-flow=""><table class="caos-table ct-wrap-head" data-table="ccf-by-design"/);
  });

  it('B2: C09 floors lets its drawing take the height the table leaves on a tall desktop, not 9 rem', () => {
    screen.tall = true;
    const tall = cards(html(<FloorsView sel={c09()} />))[0];
    expect(tall).toContain('ct-stack-chart');
    expect(tall).toContain('ct-stack-table');
    expect(tall).not.toContain('ct-stack-fixed');
    expect(tall).not.toContain('ct-stack-rest');
    screen.tall = false;
    const short = cards(html(<FloorsView sel={c09()} />))[0];
    expect(short).toContain('ct-stack-fixed');
    expect(short).toContain('ct-stack-rest');
    expect(short).not.toContain('ct-stack-chart');
  });

  it('B2: its supervisory card holds the small-undrawn list and the table as the one box that shares the height', () => {
    screen.tall = true;
    const card2 = cards(html(<FloorsView sel={c09()} />))[1];
    expect(card2).toContain('ct-scroll ct-tall-tables');
    expect(card2).toMatch(/<table class="caos-table ct-wrap-head ct-fill-table" data-table="supervisory-ccfs"/);
  });

  it('N1: C11\'s verdict card fills its stage on a tall desktop, its two tables sharing the height the prose leaves; below it the card is as tall as its content', () => {
    screen.tall = true;
    const tall = cards(html(<ConformalVerdictView sel={c11()} />))[0];
    expect(tall.split('"')[0]).toContain(' fill');
    expect(tall).toMatch(/class="ct-scroll ct-tall-tables"[^>]*data-block="conformal-hypothesis"/);
    expect(tall).toMatch(/<table class="caos-table ct-wrap-head ct-fill-table" data-table="c11-conformal-cells"/);
    expect(tall).toMatch(/<table class="caos-table ct-wrap-head ct-fill-table" data-table="c11-conformal-independence"/);
    screen.tall = false;
    const short = cards(html(<ConformalVerdictView sel={c11()} />))[0];
    expect(short.split('"')[0]).not.toContain(' fill');
    expect(short).toMatch(/<div data-block="conformal-hypothesis" data-holds=/);
    expect(short).not.toContain('ct-fill-table');
  });
});

