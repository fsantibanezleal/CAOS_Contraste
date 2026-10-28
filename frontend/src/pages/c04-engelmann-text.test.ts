import { describe, expect, it } from 'vitest';
import { engelmannText } from './C04Sections';

describe('R6 c30 B2: the Benchmark papers verdict names the portfolios as symbols, never as code tokens', () => {
  it('sets W hat, W tilde, W_ttc and W_init in both languages', () => {
    const en = engelmannText('W hat: built by propagating W_ttc one year from W_init 2; W tilde too', 'en');
    expect(en).toBe('Ŵ: built by propagating W (TTC) one year from W (init) 2; W̃ too');
    expect(engelmannText('propagando W_ttc un año desde W_init', 'es')).toBe('propagando W (TTC) un año desde W (inicial)');
    expect(en).not.toMatch(/W_|W hat|W tilde/);
  });
  it('leaves other words alone', () => {
    expect(engelmannText('What the recomputation supports, Wealth', 'en')).toBe('What the recomputation supports, Wealth');
  });
});
