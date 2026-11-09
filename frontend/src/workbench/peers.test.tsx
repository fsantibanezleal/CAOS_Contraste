// ADR-0071 rule 5 (gate G3): no row of sub-tabs holds more than six peers. Every group of every registered instrument, on every
// committed variant of every case, is rendered and its peer tabs counted; and the views that moved to make the rows fit are
// still reachable (the validation row of an agency keeps its seven views across the two rows that hold them now).
import { afterEach, describe, expect, it } from 'vitest';
import { setLang } from './c03/u6-testkit';
import { committedData, manifestOf, render, variantIds } from './c03/u16f2-kit';
import { useRegisteredInstrument } from './registry';

const CASES = ['C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08', 'C09', 'C10', 'C11', 'C12', 'C13', 'C14', 'C15', 'C16', 'C17', 'C18', 'C20', 'C21', 'C22'];
const MAX_PEERS = 6;
afterEach(() => setLang('en'));

/** The labels of the peer tabs of every group of a case's variant, by group id. */
function Groups({ caseId, variant }: { caseId: string; variant: string }) {
  const inst = useRegisteredInstrument(committedData(caseId, variant), () => undefined);
  return (
    <div>
      {(inst?.groups ?? []).map((g) => (
        <section key={g.id} data-group={g.id}>
          {g.content}
        </section>
      ))}
    </div>
  );
}

function peersOf(caseId: string, variant: string, lang: 'en' | 'es'): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  const markup = render(<Groups caseId={caseId} variant={variant} />, lang);
  for (const section of markup.split('<section data-group="').slice(1)) {
    const id = section.slice(0, section.indexOf('"'));
    out[id] = [...section.matchAll(/role="tab"[^>]*>([^<]*)</g)].map((m) => m[1]);
  }
  return out;
}

describe('every row of sub-tabs holds at most six peers (ADR-0071 rule 5, gate G3)', () => {
  for (const caseId of CASES) {
    it(`${caseId}: every group of every variant, in both languages`, () => {
      for (const variant of variantIds(caseId)) {
        for (const lang of ['en', 'es'] as const) {
          const groups = peersOf(caseId, variant, lang);
          for (const [id, tabs] of Object.entries(groups)) expect(tabs.length, `${caseId} ${variant} ${lang} ${id}: ${tabs.join(', ')}`).toBeLessThanOrEqual(MAX_PEERS);
        }
      }
    });
  }

  it('the C04 agency keeps all its views: Markov tests sit with the model, the six PD views stay in Validation', () => {
    const groups = peersOf('C04', 'sp', 'en');
    expect(groups.model).toEqual(['Matrix', 'Generators', 'Mobility', 'Markov tests']);
    expect(groups.validation).toEqual(['PD by grade', 'By year', 'Definitions', 'Lifetime', 'Anchored k', 'Semesters']);
  });

  it('the C18 scenario keeps all its views: Losses sit with the capital, the other six stay in Stress', () => {
    const scenario = manifestOf('C18').artifacts.filter((a) => a.role === 'variant').map((a) => a.variant_id).find((id) => peersOf('C18', id, 'en').stress);
    expect(scenario).toBeDefined();
    const groups = peersOf('C18', scenario as string, 'en');
    expect(groups.capital).toEqual(['CET1 fan', 'Capital stack', 'Annex 3', 'Losses']);
    expect(groups.stress).toEqual(['Scenario path', 'Satellites', 'Back-cast', 'VAR forecast', 'Growth-at-risk', 'Severity']);
  });
});
