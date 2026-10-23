// The bars of the two waterfalls C18 builds a total from layers with: the capital stack (the layers of the internal target, the
// legal minimum stack) and the Euler allocation of the expected shortfall. The shell's BarChart draws them (D16-21, shell 0.19.0):
// each layer is a floating bar from the running sum of the layers before it, valued at its own size; a total is a floating bar from
// zero to the document's own figure, so its readout reads its two ends as a layer's does. Every number given is a field of the
// document: the running sum that places a layer is layout. The numbers also sit in a table beside the chart, so a reader without
// the drawing loses nothing.
import type { BarDatum, BiText, Tone } from '@fasl-work/caos-app-shell';

export interface StackLayer {
  id: string;
  label: BiText;
  size: number;
  tone: Tone;
  /** One line shown as the bar's title: the layer's status. */
  hint?: BiText;
}

/** The bars of a waterfall of `layers` (each a size, a span from the running sum) that ends, when given, in a total spanning zero to its value. */
export function stackBars(layers: StackLayer[], total?: { id: string; label: BiText; value: number; tone: Tone }): BarDatum[] {
  let run = 0;
  const bars: BarDatum[] = layers.map((l) => {
    const from = run;
    run += l.size;
    return { id: l.id, label: l.label, value: l.size, span: [from, run], tone: l.tone, ...(l.hint ? { hint: l.hint } : {}) };
  });
  if (total) bars.push({ id: total.id, label: total.label, value: total.value, span: [0, total.value], tone: total.tone });
  return bars;
}
