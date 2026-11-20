// The pointers to the methods compared (BL-113 T4): one sentence on the Introduction and one line per question in the section of each case on
// the Experiments page. Every count is read from the committed document (data/derived/benchmark/methods-compared.json) through the loader
// of the Benchmark page (lib/methodsCompared.ts); nothing is typed in. While the document is not loaded, or when it is absent, the pointer
// states the comparison with no count and keeps its link. The link opens the Benchmark page on the tab that holds the methods compared
// (`Benchmark.tsx`, `selectionFromHash`).
import { Link } from 'react-router';
import { useT } from '../../content/bi';
import { QUESTION_HOME, docText, useMethodsCompared, type McQuestion, type MethodsCompared } from '../../lib/methodsCompared';
import { useShellLang } from '@fasl-work/caos-app-shell';

/** The questions of the document and the methods it compares: each method once, however many questions run it, the rows that set the scale
 * (an oracle, a band, a baseline, the nominal count) left out because they are not methods. */
export function methodsCounts(doc: MethodsCompared): { questions: number; methods: number; leftOut: number; notBuilt: number } {
  const methods = new Set(doc.questions.flatMap((q) => q.rows.filter((r) => r.standing !== 'reference').map((r) => r.ladder_id ?? r.id)));
  return { questions: doc.questions.length, methods: methods.size, leftOut: doc.left_out.length, notBuilt: doc.not_built.length };
}

/** The route of the Benchmark page with the hash that opens the methods compared, or one question of them. */
export function benchmarkLink(question?: string): string {
  return question ? `/benchmark#methods-${question.toLowerCase()}` : '/benchmark#methods';
}

export interface CasePointer {
  question: McQuestion;
  /** The methods the question compares (each once, the reference rows aside). */
  methods: number;
}
const qn = (id: string) => Number(id.slice(1));

/** The questions of the document that a case answers (its own home, or a case the question's protocol also runs on), in order. */
export function casePointers(doc: MethodsCompared, caseId: string): CasePointer[] {
  return doc.questions
    .filter((q) => QUESTION_HOME[q.id] === caseId || q.case_ids.includes(caseId))
    .sort((a, b) => qn(a.id) - qn(b.id))
    .map((question) => ({ question, methods: new Set(question.rows.filter((r) => r.standing !== 'reference').map((r) => r.ladder_id ?? r.id)).size }));
}

/** The clause on what the document leaves out, its counts read from `left_out` and `not_built`; a count of zero drops its part, both zero drops the clause. */
function omitted(c: { leftOut: number; notBuilt: number }, lang: 'en' | 'es'): string {
  const en: string[] = [];
  const es: string[] = [];
  if (c.leftOut) {
    en.push(`${c.leftOut} ${c.leftOut === 1 ? 'method is' : 'methods are'} left out`);
    es.push(`${c.leftOut} ${c.leftOut === 1 ? 'método queda fuera' : 'métodos quedan fuera'}`);
  }
  if (c.notBuilt) {
    en.push(`${c.notBuilt} ${c.notBuilt === 1 ? 'question is' : 'questions are'} not compared`);
    es.push(`${c.notBuilt} ${c.notBuilt === 1 ? 'pregunta no se compara' : 'preguntas no se comparan'}`);
  }
  if (!en.length) return '';
  return lang === 'en' ? `${en.join(' and ')}, with their reasons on the Benchmark page. ` : `${es.join(' y ')}, con sus razones en la página Benchmark. `;
}

/** The sentence of the Introduction (the view of a loaded document, or of none). */
export function MethodsPointerView({ doc }: { doc: MethodsCompared | null }) {
  const t = useT();
  const c = doc ? methodsCounts(doc) : null;
  return (
    <p data-methods-pointer="introduction" data-state={doc ? 'ready' : 'pending'}>
      {c
        ? t(
            `The methods the product runs are compared with the published practice on one protocol per question: ${c.questions} questions and ${c.methods} methods, each long-established, recent published or proposed in this work, with its source and year, and a proposed method that loses is shown losing. ${omitted(c, 'en')}`,
            `Los métodos que el producto ejecuta se comparan con la práctica publicada con un solo protocolo por pregunta: ${c.questions} preguntas y ${c.methods} métodos, cada uno de larga data, publicado recientemente o propuesto en este trabajo, con su fuente y año, y un método propuesto que pierde se muestra perdiendo. ${omitted(c, 'es')}`,
          )
        : t(
            'The methods the product runs are compared with the published practice on one protocol per question, each long-established, recent published or proposed in this work, with its source and year. ',
            'Los métodos que el producto ejecuta se comparan con la práctica publicada con un solo protocolo por pregunta, cada uno de larga data, publicado recientemente o propuesto en este trabajo, con su fuente y año. ',
          )}
      <Link to={benchmarkLink()}>{t('Open the methods compared', 'Abrir los métodos comparados')}</Link>
    </p>
  );
}

/** The sentence of the Introduction, reading the document. */
export function MethodsPointer() {
  const loaded = useMethodsCompared();
  return <MethodsPointerView doc={loaded.state === 'ready' ? loaded.data : null} />;
}

/** The lines of one case's section (the view of a loaded document, or of none): one link per question of the document that the case answers. */
export function CasePointersView({ doc, caseId }: { doc: MethodsCompared | null; caseId: string }) {
  const lang = useShellLang();
  const t = useT();
  const pointers = doc ? casePointers(doc, caseId) : [];
  if (!pointers.length) return null;
  return (
    <div data-methods-pointer="case" data-state="ready">
      <p>{t('The methods compared on the question this case answers, on one protocol:', 'Los métodos comparados sobre la pregunta que responde este caso, con un solo protocolo:')}</p>
      <ul>
        {pointers.map((p) => (
          <li key={p.question.id}>
            <Link to={benchmarkLink(p.question.id)}>{docText(p.question.title, lang)}</Link>
            {t(` (${p.methods} methods)`, ` (${p.methods} métodos)`)}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** The lines of one case's section, reading the document; nothing while it is not loaded. */
export function CasePointers({ caseId }: { caseId: string }) {
  const loaded = useMethodsCompared();
  return <CasePointersView doc={loaded.state === 'ready' ? loaded.data : null} caseId={caseId} />;
}
