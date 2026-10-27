// A date of a document (an ISO day, YYYY-MM-DD) as the epoch seconds of the reader's local midnight, for the time axis of a
// chart. The shell formats a time in the browser's zone, so a UTC midnight reads one day early west of UTC: 2022-01-03 read
// "2 ene 2022" in Santiago (R3 c12 B1 and c15 B1).
export const daySeconds = (day: string): number => Date.parse(`${day}T00:00:00`) / 1000;
