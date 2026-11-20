// BL-120: C08's proxy view at 390 px in Spanish. Its definition list printed the term in one column and the long text in a
// 170 px column beside it, so the view ran 2,600 px tall and the gate's centring of a view taller than the screen (G6) showed
// the middle of the text and no drawing, although the chart sits at the view's top. On a phone the five pairs whose value is a sentence stack (a
// term above its text, the text over the full width); the measured gate (390x844, dark, Spanish) is the evidence, this test holds the markup
// and the rule that make it stack.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { components } from '../../lib/contract.gen';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { fixtureData, html, readFixture } from '../c03/u6-testkit';
import { defaultSel, type C08Sel } from './selection';
import { ProxyView } from './SeverityViews';

type Outputs = components['schemas']['c08Outputs'];

const variant = readFixture<VariantArtifact<Outputs>>('c08', 'variant-default-cohort-fixture.json');
const models = readFixture<ModelsArtifact>('c08', 'models-fixture.json');
const sel = defaultSel(fixtureData('C08', variant as unknown as VariantArtifact, models, { en: 'LGD and downturn LGD', es: 'LGD y LGD de recesión' })) as C08Sel;
const css = readFileSync(new URL('../../styles/contraste.css', import.meta.url), 'utf8');

describe('the proxy view of C08 on a phone (BL-120)', () => {
  it('prints its definition list with the stacking modifier', () => {
    expect(html(<ProxyView sel={sel} />)).toMatch(/<dl class="ct-defs ct-defs-stack" data-table="lgd-proxy">/);
  });

  it('lets the five sentence values span the row, so each is read across the whole width, and keeps the short pairs in two columns', () => {
    const markup = html(<ProxyView sel={sel} />);
    const long = markup.match(/<dd class="ct-long"/g) ?? [];
    expect(long.length).toBe(5);
    expect(markup.match(/<dt class="ct-long"/g)?.length).toBe(5);
    expect(markup).toContain('data-bias=');
    expect(markup).not.toMatch(/<dd[^>]*class="ct-long"[^>]*data-bias/);
  });

  it('has a rule that spans a long pair over the row on a narrow screen only', () => {
    const block = css.match(/@media \(max-width: (\d+)px\) \{\s*\.ct-defs-stack \.ct-long \{([^}]*)\}/);
    expect(block, 'no narrow-screen rule for .ct-defs-stack .ct-long').not.toBeNull();
    expect(Number(block![1])).toBeGreaterThanOrEqual(480);
    expect(block![2]).toMatch(/grid-column:\s*1\s*\/\s*-1/);
    expect(css).not.toMatch(/\n\.ct-defs-stack[^{]*\{/);
  });
});
