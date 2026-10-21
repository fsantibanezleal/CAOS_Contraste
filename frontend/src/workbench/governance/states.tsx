// The declared "not available yet" state of a governance block, with its reason (never an empty block).
import type { Text } from '../../lib/contract.types';
import { Unavailable } from '../Pending';
import { NOT_YET } from './model';

/** A block that says it is not available yet, and why, in both languages. */
export function unavailableBlock(reason: Text) {
  return <Unavailable reason={{ en: `${NOT_YET.en}. ${reason.en}`, es: `${NOT_YET.es}. ${reason.es}` }} />;
}
