// The governance documents in reader words (U16-F10p, the third capture review R3 c23 B3 and B5). A sentence a governance
// document carries was written by the bake or by the engine's report builder: it may open on a plan or decision code of the
// product's sizing ("W15-13: ..."), cite one in brackets ("(W15-5)"), or name an engine key ("risk_accepted", "dim_cube",
// "test_id@model"). The view reads it without the codes and with the keys in words; the bake writes the same words from its
// next run (pipeline/governance/reader.py), so the two agree.

const CODE = String.raw`W\d{2}-\d+`;
const LEADING = new RegExp(String.raw`^\s*${CODE}(?:\s*,\s*${CODE})*\s*:\s*`);
const BRACKET = new RegExp(String.raw`\s*\((?:${CODE})(?:\s*(?:,|;|and|y)\s*${CODE})*\)`, 'g');
const TRAILING = new RegExp(String.raw`\s*[;,]\s*${CODE}(?:\s*,\s*${CODE})*(?=[;,.)]|$)`, 'g');
const INLINE = new RegExp(String.raw`\s*\b${CODE}\b`, 'g');

const SENTENCES: Record<'en' | 'es', Array<[RegExp, string]>> = {
  en: [
    [/the evidence is not a test_id@model row \(it is a design:, contract:, rate: or bare test id\)/g, 'the finding cites a design limit, a contract check or a rate, not one test row of a model'],
    [/the kind is spec\(test_id\)\.decision where the test is registered \((\d+) of (\d+) rows are of tests that are not: spec\(\) raises KeyError\), and the direction is null for (\d+) rows for an inline battery string, which has no policy file/g,
      "the kind is the one the engine's test catalogue declares for each registered test ($1 of $2 rows are of tests the catalogue does not hold), and the direction is not available for $3 rows, read from an inline battery string, which has no policy file"],
  ],
  es: [
    [/la evidencia no es una fila test_id@modelo \(es design:, contract:, rate: o un id de prueba sin modelo\)/g, 'el hallazgo cita un límite de diseño, una verificación de contrato o una tasa, no una fila de prueba de un modelo'],
    [/el tipo es spec\(test_id\)\.decision donde la prueba está registrada \((\d+) de (\d+) filas son de pruebas que no lo están: spec\(\) lanza KeyError\), y la dirección es nula en (\d+) filas de una cadena de batería en línea, que no tiene archivo de política/g,
      'el tipo es el que declara el catálogo de pruebas del motor para cada prueba registrada ($1 de $2 filas son de pruebas que el catálogo no contiene), y la dirección no está disponible en $3 filas, leídas de una cadena de batería en línea, que no tiene archivo de política'],
  ],
};
const KEYS: Record<'en' | 'es', Array<[RegExp, string]>> = {
  en: [
    [/\bwhen the bake runs\b/g, 'when the documents are generated'],
    [/\bthe bake\b/g, 'the generation step'],
    [/\brisk_accepted\b/g, 'risk accepted'],
    [/\bdim_cube\b/g, 'dynamic initial margin cube'],
    [/\breading ([A-D])\b/g, 'reading $1'],
  ],
  es: [
    [/\bno risk_accepted\b/g, 'no aceptados como riesgo'],
    [/\brisk_accepted\b/g, 'riesgo aceptado'],
    [/\bdim_cube\b/g, 'cubo de margen inicial dinámico'],
    [/\breading ([A-D])\b/g, 'lectura $1'],
    // the words, never a path or a key that holds them (`data-pipeline/`, `content_hash`)
    [/(?<![\w/-])del pipeline(?![\w/-])/g, 'de la cadena de cálculo'],
    [/(?<![\w/-])el pipeline(?![\w/-])/g, 'la cadena de cálculo'],
    [/(?<![\w/-])pipeline(?![\w/-])/g, 'cadena de cálculo'],
    [/(?<![\w/-])del hash(?![\w/-])/g, 'de la huella'],
    [/(?<![\w/-])el hash(?![\w/-])/g, 'la huella'],
    [/(?<![\w/-])hashes(?![\w/-])/g, 'huellas'],
    [/(?<![\w/-])hash(?![\w/-])/g, 'huella'],
    [/\bcuando corre el bake\b/g, 'cuando se generan los documentos'],
    [/\bel bake\b/g, 'la generación'],
    [/\bbake\b/g, 'generación'],
  ],
};

/** `s` in reader words: no plan or decision code, the engine keys in words; the numbers and the rest are kept. */
export function readerWords(s: string, lang: 'en' | 'es'): string {
  let out = s;
  for (const [re, w] of SENTENCES[lang]) out = out.replace(re, w);
  const lead = LEADING.test(out);
  out = out.replace(LEADING, '').replace(BRACKET, '').replace(TRAILING, '').replace(INLINE, '');
  for (const [re, w] of KEYS[lang]) out = out.replace(re, w);
  out = out.replace(/\s{2,}/g, ' ').trim();
  return lead && out ? out[0].toUpperCase() + out.slice(1) : out;
}
