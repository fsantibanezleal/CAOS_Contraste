// The readiness document as this side reads it: the generated type of docs/contracts/schemas/common/readiness.schema.json.
import type { components } from '../lib/contract.gen';

export type Readiness = components['schemas']['common-readiness'];
export type ReadinessEntry = components['schemas']['entry'];
export type ContractState = ReadinessEntry['state'];
export type Provenance = NonNullable<ReadinessEntry['provenance']>;
