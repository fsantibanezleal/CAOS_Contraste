// A long one-of-N choice of the rail as ONE select control (ADR-0071 rule 7: chips are for a small choice; a list
// taken from the documents, segments, accounts, scenarios with long names, is a select). The option text is fitted to
// the rail's width with the shell's text kit and carries the whole label as its title; the control is registered as
// `data-control`, so the gate moves it like a chip group.
import { fitLabel, pick, useShellLang, type BiText } from '@fasl-work/caos-app-shell';
import { useId } from 'react';

export interface RailSelectOption {
  id: string;
  label: BiText;
  hint?: BiText;
}

/** The width an option may take in the 248 px rail at the select's 13 px type, less the arrow and the padding. 160 and not 176: the shell gate (G5, shell 0.17.0) measures the text against the room the select leaves and fitLabel estimated 9% short (BL-090). */
export const RAIL_OPTION_WIDTH = 160;

export function RailSelect({ id, label, options, value, onChange }: { id: string; label: BiText; options: RailSelectOption[]; value: string; onChange: (id: string) => void }) {
  const lang = useShellLang();
  const domId = useId();
  const fit = (t: string) => fitLabel(t, RAIL_OPTION_WIDTH, 13, 1).lines[0];
  const full = (o: RailSelectOption) => (o.hint ? `${pick(o.label, lang)}: ${pick(o.hint, lang)}` : pick(o.label, lang));
  const current = options.find((o) => o.id === value);
  return (
    <div className="caos-chipgroup" data-control={id}>
      <label className="caos-chipgroup-label" htmlFor={domId}>
        {pick(label, lang)}
      </label>
      <select id={domId} className="select" value={value} title={current ? full(current) : undefined} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o.id} value={o.id} title={full(o)}>
            {fit(pick(o.label, lang))}
          </option>
        ))}
      </select>
    </div>
  );
}
