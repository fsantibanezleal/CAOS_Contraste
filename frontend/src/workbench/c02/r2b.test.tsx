// U16-R2b (batch c03, B1 and B2), on the committed C02 documents: each horizon file names its models with the file's prefix
// ("h1-P2a-l1", "pooled-P2a-l1") and the transfer cells without it ("P2a-l1"). The By horizon table and chart and the Transfer
// view join a model across the files by the id without the prefix, so they show the documents' values, never "Not available"
// over a value a document holds (the first tests used fixtures whose ids matched by construction).
import { describe, expect, it } from 'vitest';
import type { components } from '../../lib/contract.gen';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc } from '../c14/testkit';
import { fixtureData, html } from '../c20/testkit';
import { C02VariantsTable } from './C02Common';
import { TransferView } from './HorizonViews';
import { bareModel, defaultSel, type C02Sel } from './selection';

type Outputs = components['schemas']['c02Outputs'];
const FILES = ['h1', 'h2', 'h3', 'h4', 'h5', 'pooled'] as const;
const docs = FILES.map((f) => committedDoc<VariantArtifact<Outputs>>('C02', f));
const models = committedDoc<ModelsArtifact>('C02', 'models-polish-horizons');
const title = { en: 'Corporate PD across horizons', es: 'PD corporativa a distintos horizontes' };
const variants = docs.map((v, i) => ({ id: FILES[i], title: { en: FILES[i], es: FILES[i] }, v }));

describe('C02 on the committed documents: a model is joined across the files by its id without the file prefix', () => {
  it('bareModel drops the prefix of a horizon file and of the pooled one, and keeps a bare id', () => {
    expect(bareModel('h1-P2a-l1')).toBe('P2a-l1');
    expect(bareModel('pooled-P4-xgboost')).toBe('P4-xgboost');
    expect(bareModel('P2a-l1')).toBe('P2a-l1');
  });

  it('the By horizon table reads every file of the rung in focus: no "not available" where a document has the AUC', () => {
    const rung = docs[0].outputs.rungs[2].model_id; // h1-P2a-l1
    const markup = html(<C02VariantsTable variants={variants} onPick={() => undefined} current="h1" rung={rung} />);
    expect(markup).not.toContain('data-na="true"');
    expect(markup).not.toMatch(/AUC h\d-/); // the column head names the model, not the first file's id
  });

  it('the Transfer view finds the cells of the model in focus in its own document', () => {
    const sel = defaultSel(fixtureData('C02', docs[0] as unknown as VariantArtifact, models, title)) as C02Sel;
    const markup = html(<TransferView sel={sel} />);
    expect(markup).not.toContain('data-state="unavailable"');
  });
});
