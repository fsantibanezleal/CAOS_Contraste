// Shell 0.11.0 defect, worked around until the base ships the fix (ADR-0078 section 5: remove this file then): the
// end-of-page references block prints the bibliographic records verbatim ("section 1.4", arXiv numbers, DOIs) without
// translate="no", so the gate's G11 reads their decimal points as Spanish numbers. A bibliographic record is kept as the
// source writes it, so the block is marked here, once it is in the page.
import { useEffect } from 'react';

export function NoTranslateRefs() {
  useEffect(() => {
    const mark = () => document.querySelectorAll('[data-doc-references]:not([translate])').forEach((el) => el.setAttribute('translate', 'no'));
    mark();
    const observer = new MutationObserver(mark);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);
  return null;
}
