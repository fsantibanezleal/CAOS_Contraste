// A Spanish page writes decimals with a comma (G11). The pipeline writes some Spanish sentences of the findings with
// decimal points ("0.116900"); until it writes them with a comma, the view localises them: a number outside a DOI, a
// URL, a version or a range, and not a Spanish thousands group ("1.000": 1 to 3 digits, not starting with 0, then
// groups of exactly 3).
export function esDecimals(text: string, lang: 'en' | 'es'): string {
  if (lang !== 'es') return text;
  return text.replace(/(?<![\w.,/:@#-])(\d+)\.(\d+)(?![\w.])/g, (all, a: string, b: string) => (/^[1-9]\d{0,2}$/.test(a) && /^\d{3}$/.test(b) ? all : `${a},${b}`));
}
