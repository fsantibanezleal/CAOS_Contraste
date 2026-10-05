// The six routes on the shared shell (ADR-0016, ADR-0057 as amended 2026-10-04): the App route is the workbench,
// the five documentation routes are DocPages. Identity, licence and visibility come from product.json (one source,
// written by scripts/instantiate.py); the version is VERSION, injected at build.
import { AppShell, CitationsProvider, STANDARD_ROUTES, type ShellConfig } from '@fasl-work/caos-app-shell';
import { Route, Routes } from 'react-router';
import product from '../../product.json';
import { architecture } from './architecture';
import { CITATIONS } from './content/citations';
import { Benchmark } from './pages/Benchmark';
import { Experiments } from './pages/Experiments';
import { Implementation } from './pages/Implementation';
import { Introduction } from './pages/Introduction';
import { Methodology } from './pages/Methodology';
import { NotFound } from './pages/NotFound';
import { Workbench } from './workbench/Workbench';

const config: ShellConfig = {
  product: { name: product.name },
  routes: STANDARD_ROUTES,
  links: { github: product.repo },
  version: __APP_VERSION__,
  build: __BUILD_ID__,
  license: { en: `${product.license} licence`, es: `Licencia ${product.license}` },
  visibility: product.visibility === 'private' ? 'private' : 'public',
  contain: true,
  architecture,
};

export function App() {
  return (
    <CitationsProvider items={CITATIONS}>
      <AppShell config={config}>
        <Routes>
          <Route path="/" element={<Workbench />} />
          <Route path="/introduction" element={<Introduction />} />
          <Route path="/methodology" element={<Methodology />} />
          <Route path="/implementation" element={<Implementation />} />
          <Route path="/experiments" element={<Experiments />} />
          <Route path="/benchmark" element={<Benchmark />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </AppShell>
    </CitationsProvider>
  );
}
