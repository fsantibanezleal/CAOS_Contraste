// The diagrams of the architecture modal, shown inline on the documentation pages. Each is a hand-authored SVG on the
// shell's tokens with both languages; the page's language decides which labels show (data-arch-lang).
import { useShellLang } from '@fasl-work/caos-app-shell';
import { SVG } from './index';

function Inline({ svg, label }: { svg: string; label: string }) {
  const lang = useShellLang();
  return <div className="ct-fig fig-svg wide" data-arch-lang={lang} role="img" aria-label={label} dangerouslySetInnerHTML={{ __html: svg }} />;
}

export const OverviewFigure = () => <Inline svg={SVG.lanes} label="Contraste end to end" />;
export const ValidationFigure = () => <Inline svg={SVG.validation} label="The validation" />;
export const ContractsFigure = () => <Inline svg={SVG.contracts} label="Data and contracts" />;
export const AppFigure = () => <Inline svg={SVG.app} label="The App" />;
export const FlowFigure = () => <Inline svg={SVG.flow} label="Web flow" />;
