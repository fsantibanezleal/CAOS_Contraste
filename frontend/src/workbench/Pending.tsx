// A view whose data is not there yet says so and declares data-state="loading": the measured gate waits for it,
// and a reader sees why the panel is empty.
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
