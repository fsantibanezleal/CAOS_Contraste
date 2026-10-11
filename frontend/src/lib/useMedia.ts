import { useSyncExternalStore } from 'react';

/** Whether a CSS media query matches, kept current as the window changes; `server` where there is no window (the
 * server-rendered tests). A view row's shares live on the shell's columns, which a product's media query cannot reach,
 * so a row whose split depends on the screen reads it here. */
export function useMedia(query: string, server = false): boolean {
  return useSyncExternalStore(
    (onChange) => {
      if (typeof window === 'undefined' || !window.matchMedia) return () => undefined;
      const list = window.matchMedia(query);
      list.addEventListener('change', onChange);
      return () => list.removeEventListener('change', onChange);
    },
    () => (typeof window === 'undefined' || !window.matchMedia ? server : window.matchMedia(query).matches),
    () => server,
  );
}

/** The findings views: two thirds for the table; from 2000 px wide the drawing takes two thirds, since a short table
 * cannot fill a tall stage. */
export function useFindingsShares(): [number, number] {
  return useMedia('(min-width: 2000px)') ? [1, 2] : [2, 1];
}
