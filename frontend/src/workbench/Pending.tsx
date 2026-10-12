// A view whose data is not there says so, in one of two declared states. `loading`: the data is on its way, and the
// measured gate waits for it. `unavailable`: the data is declared absent (a planned case, a manifest the readiness
// lists as missing) with a reason a reader can read; the gate accepts it as an instrument that draws nothing and never
// waits on it (ADR-0080 decision 3: a declared state, never an empty chart).
import { pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';

const LOADING: BiText = { en: 'Loading the case artifacts', es: 'Cargando los artefactos del caso' };

export function Pending({ label = LOADING }: { label?: BiText }) {
  const lang = useShellLang();
  return (
    <p className="caos-pending" data-state="loading">
      {pick(label, lang)}
    </p>
  );
}

/** The unavailable variant: the reason is required, in both languages. */
export function Unavailable({ reason }: { reason: { en: string; es: string } }) {
  const lang = useShellLang();
  return (
    <p className="caos-pending" data-state="unavailable">
      {pick(reason, lang)}
    </p>
  );
}
