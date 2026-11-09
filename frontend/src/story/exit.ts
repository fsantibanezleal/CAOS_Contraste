// The exit of the story carries the step's state (ADR-0082 rule 3: "the exit lands on the App with the step's state"). The story's
// state is a market window and a model; the App's C11 instrument reads them as `variant` (the window document) and `model`. A route
// the reader came from (`from`, an App route) keeps its own parameters and gains the two; without one the exit is the C11 case.
const SAFE_ID = /^[a-z0-9][a-z0-9._-]*$/i;
const APP_FALLBACK = '/app?case=C11';

/** The App route the exit lands on: `from` when it is an App route, else the C11 case, with the window and model of the step. */
export function exitTarget(from: string | null, windowId: string, modelId: string): string {
  const safe = from && from.startsWith('/app') && !from.startsWith('//') && !from.includes('\\') ? from : null;
  const url = new URL(safe ?? APP_FALLBACK, 'https://story.invalid');
  url.searchParams.set('variant', windowId);
  url.searchParams.set('model', modelId);
  return `${url.pathname}${url.search}`;
}

/** The window and model the App was asked to open on, read from its query string; a value that is not an id is dropped. */
export function seedOfQuery(search: string): { variant: string | null; model: string | null } {
  const q = new URLSearchParams(search);
  const id = (key: string): string | null => {
    const v = q.get(key);
    return v && SAFE_ID.test(v) ? v : null;
  };
  return { variant: id('variant'), model: id('model') };
}
