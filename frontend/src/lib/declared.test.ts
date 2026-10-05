// The build copies what the index declares: one artifact or several per manifest, and the index's further files.
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
// @ts-expect-error: a plain ES module shared with the build script
import { artifactPaths, declaredFiles } from '../../scripts/declared.mjs';

const root = mkdtempSync(join(tmpdir(), 'declared-'));
afterAll(() => rmSync(root, { recursive: true, force: true }));
const put = (rel: string, doc: unknown) => {
  mkdirSync(dirname(join(root, rel)), { recursive: true });
  writeFileSync(join(root, rel), JSON.stringify(doc));
};

describe('the declared files of the site', () => {
  it('reads one artifact or a list of artifacts', () => {
    expect(artifactPaths({ artifact: { path: 'A/trace.json' } })).toEqual(['A/trace.json']);
    expect(artifactPaths({ artifacts: [{ path: 'B/v1.json' }, { path: 'B/v2.json' }] })).toEqual(['B/v1.json', 'B/v2.json']);
    expect(artifactPaths({})).toEqual([]);
  });
  it('names every missing declared file, and a manifest that names no artifact', () => {
    put('manifests/index.json', {
      files: ['contract/index.json'],
      cases: [
        { case_id: 'A', manifest_path: 'manifests/A.json' },
        { case_id: 'B', manifest_path: 'manifests/B.json' },
        { case_id: 'C', manifest_path: 'manifests/C.json' },
      ],
    });
    put('manifests/A.json', { artifact: { path: 'A/trace.json' } });
    put('A/trace.json', {});
    put('manifests/B.json', { artifacts: [{ path: 'B/v1.json' }, { path: 'B/v2.json' }] });
    put('B/v1.json', {});
    put('manifests/C.json', { title: 'no artifact' });
    const { declared, missing, problems } = declaredFiles(root);
    expect(declared).toEqual([
      'manifests/index.json', 'contract/index.json', 'manifests/A.json', 'A/trace.json', 'manifests/B.json',
      'B/v1.json', 'B/v2.json', 'manifests/C.json',
    ]);
    expect(missing).toEqual(['contract/index.json', 'B/v2.json']);
    expect(problems).toEqual(['manifests/C.json: names no artifact (artifact or artifacts)']);
  });
});
