// The governance tabs of the Experiments design group (U15-W, decision W15-10): Inventory and tiers, Findings and
// appetite, Reports. The design group then holds Coverage, Protocol and metrics, these three and the C22 tab: six, the
// ADR-0071 limit. The group is relabelled "How are the experiments designed and governed?". Experiments.tsx registers
// these tabs (the patch in changes/U15-W.md); each tab reads its governance document and says "not available yet",
// with the reason, while the bake has not written it.
import type { BiText } from '@fasl-work/caos-app-shell';
import type { ReactNode } from 'react';
import { DocSection } from '@fasl-work/caos-app-shell';
import { InventoryTabLoader } from '../../workbench/governance/InventoryView';
import { FindingsTabLoader } from '../../workbench/governance/RegisterView';
import { ReportsTabLoader } from '../../workbench/governance/ReportView';

export const DESIGN_GROUP_LABEL: { en: string; es: string } = { en: 'How are the experiments designed and governed?', es: '¿Cómo se diseñan y gobiernan los experimentos?' };

const NO_REFS: BiText = { en: 'Read from the governance documents; the rules are cited in Methodology.', es: 'Leído de los documentos de gobernanza; las reglas se citan en Metodología.' };

function Section({ title, children }: { title: BiText; children: ReactNode }) {
  return (
    <DocSection area="question" title={title} noRefsReason={NO_REFS}>
      {children}
    </DocSection>
  );
}

/** The three governance tabs, labelled in the interface language. */
export function governanceTabs(lang: 'en' | 'es'): Array<{ id: string; label: string; content: ReactNode }> {
  const l = (en: string, es: string) => (lang === 'es' ? es : en);
  return [
    {
      id: 'inventory',
      label: l('Inventory and tiers', 'Inventario y niveles'),
      content: (
        <Section title={{ en: 'The model inventory, its dependencies and its tiers', es: 'El inventario de modelos, sus dependencias y sus niveles' }}>
          <InventoryTabLoader />
        </Section>
      ),
    },
    {
      id: 'findings',
      label: l('Findings and appetite', 'Hallazgos y apetito'),
      content: (
        <Section title={{ en: 'The findings register and the model risk appetite', es: 'El registro de hallazgos y el apetito de riesgo de modelo' }}>
          <FindingsTabLoader />
        </Section>
      ),
    },
    {
      id: 'reports',
      label: l('Reports', 'Informes'),
      content: (
        <Section title={{ en: 'The validation report of an inventory entry', es: 'El informe de validación de una entrada del inventario' }}>
          <ReportsTabLoader />
        </Section>
      ),
    },
  ];
}
