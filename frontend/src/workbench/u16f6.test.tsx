// U16-F6 (the second fix round, C01): the minors of the b01 review that belong to C01's views, on the committed documents.
import { afterEach, describe, expect, it } from 'vitest';
import { COMMITTED } from '../lib/policy';
import { committedData, render, textOf } from './c03/u16f2-kit';
import { setLang } from './c03/u6-testkit';
import { ContextView } from './ContextView';
import { ImpactView } from './ImpactView';
import { LadderView, ScorecardView } from './ModelViews';
import { defaultChallenger, type Selection } from './model';
import { BatteryView, CalibrationView, DiscriminationView, StabilityView } from './ValidationViews';

const sel = (variant = 'holdout'): Selection => {
  const data = committedData('C01', variant);
  return { data, challenger: defaultChallenger(data.variant), alphas: COMMITTED, approval: 0.8, lgd: 0.5, applicant: 0 };
};
const both = (el: (lang: 'en' | 'es') => ReturnType<typeof render>) => ({ en: textOf(el('en')), es: textOf(el('es')) });

describe('U16-F6 C01', () => {
  afterEach(() => setLang('en'));

  it('b01 m1: the Impact view says why the live and the pipeline figures differ', () => {
    const s = sel();
    expect(textOf(render(<ImpactView sel={s} />, 'en'))).toMatch(/live figures interpolate the cut-off curve/);
    expect(textOf(render(<ImpactView sel={s} />, 'es'))).toMatch(/cifras en vivo interpolan la curva de corte/);
  });

  it('b01 m3: DeLong against the champion names the direction of the test', () => {
    const t = both((l) => render(<BatteryView sel={sel()} />, l));
    expect(t.en).toMatch(/DeLong against the champion \(a difference in either direction\)/);
    expect(t.es).toMatch(/DeLong contra el campeón \(una diferencia en cualquier sentido\)/);
  });

  it('b01 m4: a note never names a column the width hides without saying from which width it shows', () => {
    const cal = both((l) => render(<CalibrationView sel={sel()} />, l));
    // R3 c01 m16 (U16-F10a): the notes say what the reader can do (a wider window; on a narrow screen under the value), not a pixel width
    expect(cal.en).toMatch(/posterior interval column, which a wide window adds/);
    expect(cal.es).toMatch(/intervalo posterior, que una ventana ancha agrega/);
    const lad = both((l) => render(<LadderView sel={sel()} />, l));
    expect(lad.en).toMatch(/on a narrow screen the interval and the ECE sit under their value/);
    expect(lad.es).toMatch(/en una pantalla angosta el intervalo y el ECE quedan bajo su valor/);
  });

  it('b01 m5: the PSI by decile says that tied values merge deciles', () => {
    const t = both((l) => render(<StabilityView sel={sel()} />, l));
    expect(t.en).toMatch(/tied values merge deciles/i);
    expect(t.es).toMatch(/valores empatados unen deciles/i);
  });

  it('b01 m16: the AUC and its interval carry the same four decimals', () => {
    const t = textOf(render(<DiscriminationView sel={sel()} />, 'en'));
    expect(t).toMatch(/\d\.\d{4} \(\d\.\d{4} - \d\.\d{4}\)/);
  });

  it('b01 m8: no loanword where Spanish has the word', () => {
    const lad = textOf(render(<LadderView sel={sel()} />, 'es')) + textOf(render(<ScorecardView sel={sel()} />, 'es'));
    expect(lad).not.toMatch(/\bodds\b/);
    expect(lad).not.toMatch(/Segmentadas/);
  });

  it('b01 m8: the licence of a source reads in Spanish, its citation as published', () => {
    const t = textOf(render(<ContextView sel={sel()} />, 'es'));
    expect(t).toContain('Creative Commons Atribución 4.0 Internacional (CC BY 4.0)');
    expect(t).not.toContain('This dataset is licensed');
    expect(textOf(render(<ContextView sel={sel()} />, 'en'))).toContain('This dataset is licensed under a Creative Commons Attribution 4.0 International (CC BY 4.0) license.');
  });
});
