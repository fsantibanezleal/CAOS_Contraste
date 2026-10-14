// The executive view of Contraste (CAOS_MANAGE conventions/problem-context-first.md, BL-073, schema 2.0.0): its data is valid against
// the shell's rules and its three illustrations meet the standard the shell's gate measures in the page.
import { readFileSync } from 'node:fs';
import { EXECUTIVE_SCHEMA_VERSION, FLIP_LIMITS, FOUR_CS, validateExecutive } from '@fasl-work/caos-app-shell';
import { describe, expect, it } from 'vitest';
import executive from '../../../content/executive.json';

const PUBLIC = new URL('../../public/', import.meta.url);
const NAMES = ['pain', 'situation', 'proposal'] as const;
const read = (name: (typeof NAMES)[number]) => readFileSync(new URL(executive.illustrations[name].file as string, PUBLIC), 'utf8');

// the shell's own analysis of an animated drawing (gate G17); the file is not in the package exports, so it is loaded by path
type Analysis = { animated: boolean; css: boolean; smil: boolean; reducedBlock: boolean; neutralises: boolean; seconds: number };
const areas = (await import(new URL('../../node_modules/@fasl-work/caos-app-shell/gate/areas.mjs', import.meta.url).href)) as {
  analyseSvgAnimation: (text: string) => Analysis;
  animationFailures: (a: Analysis, name: string) => string[];
};
const words = (text: string): number => text.split(/\s+/).filter((w) => /[\p{L}\p{N}]/u.test(w)).length;
type Bi = { en: string; es: string };

const TOKEN = /^(none|currentColor|var\(--color-[a-z0-9-]+\))$/;

/** What is wrong with one illustration, in the terms of the gate: literal colours, charts, labels without a twin, no viewBox. */
export function svgProblems(svg: string): string[] {
  const out: string[] = [];
  if (!/viewBox="[^"]+"/.test(svg)) out.push('no viewBox');
  if (/<(img|image|script|foreignObject)\b/i.test(svg)) out.push('holds an img, image, script or foreignObject');
  if (/data-chart/i.test(svg)) out.push('declares a chart (data-chart)');
  if (/#[0-9a-f]{3,8}\b|rgba?\(|hsla?\(/i.test(svg)) out.push('a literal colour');
  for (const m of svg.matchAll(/\b(fill|stroke|stop-color|flood-color)="([^"]*)"/g)) {
    if (!TOKEN.test(m[2])) out.push(`${m[1]}="${m[2]}" is not a theme token`);
  }
  for (const m of svg.matchAll(/style="([^"]*)"/g)) {
    if (/(fill|stroke|color)\s*:/.test(m[1])) out.push('a colour set in a style attribute');
  }
  const count = (lang: string) => [...svg.matchAll(new RegExp(`<text[^>]*data-lang="${lang}"`, 'g'))].length;
  if (count('en') < 4) out.push(`only ${count('en')} English label(s)`);
  if (count('en') !== count('es')) out.push(`${count('en')} English and ${count('es')} Spanish labels`);
  if (/<text(?![^>]*data-lang=)/.test(svg)) out.push('a label with no data-lang');
  if (/font-family/.test(svg)) out.push('a label sets its own font family');
  for (const m of svg.matchAll(/<text[^>]*font-size="([\d.]+)"/g)) if (Number(m[1]) < 18) out.push(`a label at ${m[1]} in a 640 wide drawing is under 9 px on a phone`);
  return [...new Set(out)];
}

/** The geometry of every rectangle, so two scenes can be compared for the setting they share. */
const rects = (svg: string) => new Set([...svg.matchAll(/<rect x="([\d.-]+)" y="([\d.-]+)" width="([\d.-]+)" height="([\d.-]+)"/g)].map((m) => m.slice(1, 5).join(',')));

/** The four flip groups of the executive view: each card's title and the text of its back (labels and values, counted as the gate counts the back). */
function flipGroups(): Array<{ group: string; cards: Array<{ title: Bi; back: Bi }> }> {
  const L = { cost: { en: 'Cost', es: 'Costo' }, measure: { en: 'Measure', es: 'Medida' }, decides: { en: 'Decides', es: 'Decide' }, needs: { en: 'Needs', es: 'Necesita' }, achieves: { en: 'Achieves', es: 'Logra' }, falls: { en: 'Falls short', es: 'No alcanza' }, source: { en: 'Source', es: 'Fuente' } };
  const join = (...parts: Bi[]): Bi => ({ en: parts.map((p) => p.en).join(' '), es: parts.map((p) => p.es).join(' ') });
  const e = executive as unknown as {
    pain: { bearers: Array<{ who: Bi; cost: Bi; measure: Bi }> };
    situation: { roles: Array<{ role: Bi; decides: Bi; needs: Bi }>; state_of_the_art: Array<{ approach: Bi; achieves: Bi; falls_short: Bi }> };
    proposal: { four_cs: Array<{ c: Bi; applies: Bi }> };
  };
  const cite: Bi = { en: '[1]', es: '[1]' };
  return [
    { group: 'pain.bearers', cards: e.pain.bearers.map((b) => ({ title: b.who, back: join(L.cost, b.cost, L.measure, b.measure) })) },
    { group: 'situation.roles', cards: e.situation.roles.map((r) => ({ title: r.role, back: join(L.decides, r.decides, L.needs, r.needs) })) },
    { group: 'situation.state_of_the_art', cards: e.situation.state_of_the_art.map((a) => ({ title: a.approach, back: join(L.achieves, a.achieves, L.falls, a.falls_short, L.source, cite) })) },
    { group: 'proposal.four_cs', cards: e.proposal.four_cs.map((c) => ({ title: c.c, back: c.applies })) },
  ];
}

describe('the flip cards of the executive view (shell 0.14.0, G16)', () => {
  it('has the four flip groups, bearers and roles with five cards each (a carousel)', () => {
    const g = Object.fromEntries(flipGroups().map((x) => [x.group, x.cards.length]));
    expect(g['pain.bearers']).toBe(5);
    expect(g['situation.roles']).toBe(5);
    expect(g['proposal.four_cs']).toBe(4);
  });

  it('every flip title is within 8 words in English and 10 in Spanish, and every back within 40 and 50', () => {
    for (const { group, cards } of flipGroups()) {
      cards.forEach((c, i) => {
        expect(words(c.title.en), `${group}[${i}] title en: ${c.title.en}`).toBeLessThanOrEqual(FLIP_LIMITS.title.en);
        expect(words(c.title.es), `${group}[${i}] title es: ${c.title.es}`).toBeLessThanOrEqual(FLIP_LIMITS.title.es);
        expect(words(c.back.en), `${group}[${i}] back en`).toBeLessThanOrEqual(FLIP_LIMITS.back.en);
        expect(words(c.back.es), `${group}[${i}] back es`).toBeLessThanOrEqual(FLIP_LIMITS.back.es);
      });
    }
  });

  it('each state-of-the-art card keeps a cited source and a Spanish title of its own', () => {
    const sota = (executive as unknown as { situation: { state_of_the_art: Array<{ approach: Bi; source: string }> } }).situation.state_of_the_art;
    expect(sota.length).toBeGreaterThanOrEqual(3);
    for (const a of sota) {
      expect((executive.sources as Array<{ id: string }>).some((s) => s.id === a.source), a.source).toBe(true);
      expect(a.approach.es).not.toBe(a.approach.en);
    }
  });
});

describe('the animated illustrations (shell 0.14.0, G17)', () => {
  it('each animated illustration carries its reduced-motion block, stops its CSS animation and plays at most ten seconds', () => {
    for (const name of NAMES) expect(areas.animationFailures(areas.analyseSvgAnimation(read(name)), name), name).toEqual([]);
  });

  it('the pain, the situation and the proposal are animated: they explain a change, a flow and a before and after', () => {
    for (const name of NAMES) expect(areas.analyseSvgAnimation(read(name)).animated, name).toBe(true);
  });

  it('adversarial: an animation with no reduced-motion block, or one that does not stop, is refused', () => {
    const svg = read('pain');
    const noBlock = svg.replace(/@media \(prefers-reduced-motion: reduce\)\s*\{[\s\S]*?\}\s*\}/, '');
    expect(areas.animationFailures(areas.analyseSvgAnimation(noBlock), 'pain').join()).toMatch(/no @media/);
    const keeps = svg.replace(/animation:\s*none/g, 'opacity: 1');
    expect(areas.animationFailures(areas.analyseSvgAnimation(keeps), 'pain').join()).toMatch(/does not stop/);
  });

  it('the labels never move: no label carries a class', () => {
    for (const name of NAMES) expect(read(name), name).not.toMatch(/<text[^>]*\sclass=/);
  });
});

describe('the Contraste executive view', () => {
  it('the data is valid against the shell schema 2.0.0 and the 4 CS are present in order', () => {
    expect(EXECUTIVE_SCHEMA_VERSION).toBe('2.0.0');
    expect(validateExecutive(executive)).toEqual([]);
    expect(executive.proposal.four_cs.map((c) => c.c.en)).toEqual(FOUR_CS.map((c) => c.name.en));
  });

  it('keeps the supervisor figure as a headline, with its linked source and no bank named', () => {
    const cmf = executive.headline_figures.find((f) => f.value.en === '571');
    expect(cmf, 'the 571 million figure').toBeDefined();
    expect(cmf!.unit.en).toMatch(/million US dollars/);
    expect(cmf!.unit.en).toMatch(/January 2031/);
    const src = executive.sources.find((s) => s.id === cmf!.source);
    expect(src!.url).toMatch(/^https:\/\/www\.cmfchile\.cl\//);
  });

  it('every source is an https link whose title and note are not a file name', () => {
    expect(executive.sources.length).toBeGreaterThanOrEqual(8);
    for (const s of executive.sources) {
      expect(s.url, s.id).toMatch(/^https:\/\/[^\s]+$/);
      expect(`${s.title.en} ${s.title.es} ${'note' in s ? JSON.stringify(s.note) : ''}`, s.id).not.toMatch(/\bfile\s*\d|\barchivo\s*\d|\.pdf\b/i);
    }
  });

  it('is general: no named bank, no first person, no offer, no price', () => {
    const text = JSON.stringify({ ...executive, sources: [] });
    expect(text).not.toMatch(/Contraste|Banco Andino|Santander|BancoEstado|Itaú|Scotiabank|Banco de Chile|BBVA|HSBC|\bour\b|\bwe\b|nuestro|nosotros/i);
  });

  it('has more than the floors: the five sections read as a document', () => {
    const words = (v: unknown): number => (typeof v === 'string' ? v.split(/\s+/).filter(Boolean).length : v && typeof v === 'object' ? Object.entries(v as object).reduce((n, [k, x]) => n + (k === 'es' ? 0 : words(x)), 0) : 0);
    const total = words({ ...executive, sources: [], illustrations: [] });
    expect(total).toBeGreaterThan(1500);
    expect(total).toBeLessThan(3200);
  });

  it('the three illustrations use only theme tokens, big labels and both languages', () => {
    expect(Object.keys(executive.illustrations).sort()).toEqual(['pain', 'proposal', 'situation']);
    for (const name of NAMES) expect(svgProblems(read(name)), name).toEqual([]);
  });

  it('the illustrations name no organisation and none is a chart', () => {
    for (const name of NAMES) {
      const svg = read(name);
      expect(svg, name).not.toMatch(/\bCMF\b|\bECB\b|\bBCE\b|\bEBA\b|\bPRA\b|\bOSFI\b|\bFed\b|Basel|Basilea/);
      expect(svg, name).not.toMatch(/<(polyline|axis)\b|tick|axis/i);
    }
  });

  it('the pain and the proposal share the setting', () => {
    const [pain, , proposal] = NAMES.map((n) => rects(read(n)));
    const shared = [...pain].filter((r) => proposal.has(r)).length / Math.min(pain.size, proposal.size);
    expect(shared).toBeGreaterThan(0.6);
  });

  it('adversarial: planted literal colours, charts, missing labels and long sentences are refused', () => {
    const svg = read('pain');
    expect(svgProblems(svg.replace('var(--color-bad)', '#ff0000'))).toContain('a literal colour');
    expect(svgProblems(svg.replace('var(--color-bad)', 'red')).join()).toMatch(/not a theme token/);
    expect(svgProblems(svg.replace('<svg ', '<svg data-chart="line" '))).toContain('declares a chart (data-chart)');
    expect(svgProblems(svg.replace(/<text data-lang="es"[^>]*>[^<]*<\/text>/, ''))[0]).toMatch(/English and \d+ Spanish/);
    expect(svgProblems(svg.replace(/ viewBox="[^"]*"/, ''))).toContain('no viewBox');
    const long = JSON.parse(JSON.stringify(executive));
    long.key_statement.en = Array.from({ length: 31 }, () => 'word').join(' ') + '.';
    expect(validateExecutive(long).map((p) => p.path)).toContain('key_statement.en');
    const unsourced = JSON.parse(JSON.stringify(executive));
    unsourced.sources.pop();
    expect(validateExecutive(unsourced).length).toBeGreaterThan(0);
    const promo = JSON.parse(JSON.stringify(executive));
    promo.proposal.paragraphs[0].en += ' Contact us to buy it.';
    expect(validateExecutive(promo).length).toBeGreaterThan(0);
  });
});
