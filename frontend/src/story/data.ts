// How the story reads its artifacts: through the product's own loaders (api/artifacts.ts, workbench/governance/model.ts), never
// a fetch path of its own. An artifact that does not load is the declared "not available yet" state of that step, with the
// reason; the other steps still work (ADR-0080).
import { loadCase, useArtifact, type CaseData, type LoadedDeclared } from '../api/artifacts';
import { GOVERNANCE_FILES, loadGovernance, type GovFindings, type GovInventory } from '../workbench/governance/model';
import { buildFlow, type Flow } from './model';

export interface GovernanceDocs {
  inv: GovInventory;
  fin: GovFindings;
  flow: Flow;
}

/** The inventory and the register of findings, and the flow built from them. */
export function useGovernanceDocs(): LoadedDeclared<GovernanceDocs> {
  return useArtifact<GovernanceDocs>(
    () =>
      Promise.all([loadGovernance<GovInventory>(GOVERNANCE_FILES.inventory), loadGovernance<GovFindings>(GOVERNANCE_FILES.findings)]).then(([inv, fin]) => ({ inv, fin, flow: buildFlow(inv, fin) })),
    [],
    { unavailable: true },
  );
}

/** One window of the market case (C11): its manifest, the window document and the models document. */
export function useWindowDocs(windowId: string): LoadedDeclared<CaseData> {
  return useArtifact<CaseData>((signal) => loadCase('C11', windowId, signal), [windowId], { unavailable: true });
}
