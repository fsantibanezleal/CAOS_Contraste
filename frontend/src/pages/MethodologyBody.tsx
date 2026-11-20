// The body of a registered Methodology section, loaded when its tab opens (BL-102). The page's tab list is built from the
// sections' metadata; this component imports the body file on first render, shows the shell's pending state meanwhile and, when
// the import fails (an offline reader, a stale deploy), the section's absence with the reason, never a blank tab.
import { Component, lazy, Suspense, useRef, type ComponentType, type ReactNode } from 'react';
import { Pending, Unavailable } from '../workbench/Pending';
import { REGISTERED_SECTIONS, type RegisteredSection } from './methodologyRegistry';

// the bodies already loaded: a mount that finds its body here draws it at once (a server render cannot wait for an import)
const LOADED = new Map<string, ComponentType>();

/** Loads every registered body, so the next render of the page draws them all: the tests that read the whole page use it. */
export async function preloadMethodologySections(): Promise<void> {
  await Promise.all(REGISTERED_SECTIONS.map((s) => s.load().then((Body) => void LOADED.set(s.id, Body))));
}

// one lazy component per section, so the tab keeps its identity across renders (a new lazy() per render would reload it)
const LAZY = new Map<string, ComponentType>();
function lazyBody(section: RegisteredSection): ComponentType {
  let c = LAZY.get(section.id);
  if (!c) {
    c = lazy(() =>
      section.load().then((Body) => {
        LOADED.set(section.id, Body);
        return { default: Body };
      }),
    );
    LAZY.set(section.id, c);
  }
  return c;
}

/** Catches a body that failed to load or to render and says so in both languages. */
class SectionBoundary extends Component<{ id: string; children: ReactNode }, { message: string | null }> {
  state = { message: null as string | null };
  static getDerivedStateFromError(e: unknown) {
    return { message: e instanceof Error ? e.message : String(e) };
  }
  render() {
    if (this.state.message === null) return this.props.children;
    return (
      <Unavailable
        reason={{
          en: `This section (${this.props.id}) could not be loaded (${this.state.message}). Reload the page; if it persists the deployed build may be stale.`,
          es: `No se pudo cargar esta sección (${this.props.id}): ${this.state.message}. Recargue la página; si persiste, la versión desplegada puede estar desactualizada.`,
        }}
      />
    );
  }
}

export function SectionBody({ section }: { section: RegisteredSection }) {
  // decided once per mount, so a body that finishes loading while shown is not remounted by a later render
  const ready = useRef(LOADED.get(section.id)).current;
  if (ready) {
    const Ready = ready;
    return (
      <SectionBoundary id={section.id}>
        <Ready />
      </SectionBoundary>
    );
  }
  const Body = lazyBody(section);
  return (
    <SectionBoundary id={section.id}>
      <Suspense fallback={<Pending label={{ en: 'Loading the section', es: 'Cargando la sección' }} />}>
        <Body />
      </Suspense>
    </SectionBoundary>
  );
}
