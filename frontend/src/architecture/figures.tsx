// The diagrams of the architecture modal, shown inline on the documentation pages. Each is a hand-authored SVG on the
// shell's tokens with both languages; the page's language decides which labels show (data-arch-lang).
import { useShellLang } from '@fasl-work/caos-app-shell';
import { SVG } from './index';

function Inline({ svg, label: labels }: { svg: string; label: { en: string; es: string } }) {
  const lang = useShellLang();
  // the figure's name in the page's language (the R2b page review c24: the label was English only)
  const label = labels[lang];
  return (
    <>
      <p className="ct-fig-hint">{lang === 'es' ? 'Deslice hacia los lados para leer el diagrama a su tamaño.' : 'Scroll sideways to read the diagram at full size.'}</p>
      <div className="ct-fig-scroll" tabIndex={0} role="group" aria-label={label}>
        <div className="ct-fig fig-svg wide" data-arch-lang={lang} role="img" aria-label={label} dangerouslySetInnerHTML={{ __html: svg }} />
      </div>
    </>
  );
}

export const OverviewFigure = () => <Inline svg={SVG.lanes} label={{ en: 'Contraste end to end', es: 'Contraste de punta a punta' }} />;
export const ValidationFigure = () => <Inline svg={SVG.validation} label={{ en: 'The validation', es: 'La validación' }} />;
export const ContractsFigure = () => <Inline svg={SVG.contracts} label={{ en: 'Data and contracts', es: 'Datos y contratos' }} />;
export const AppFigure = () => <Inline svg={SVG.app} label={{ en: 'The App', es: 'La App' }} />;
export const FlowFigure = () => <Inline svg={SVG.flow} label={{ en: 'Web flow', es: 'Flujo web' }} />;
