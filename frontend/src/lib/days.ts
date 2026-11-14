// A date of a document (an ISO day, YYYY-MM-DD) as the epoch seconds of its UTC midnight, for the time axis of a chart. From
// shell 0.26.0 a time axis reads its epochs in UTC by default (known defect 43 closed), so a UTC midnight reads as that day in
// every zone. On shell 0.25.0 the axis read the browser's zone and this helper passed the reader's local midnight instead
// (2022-01-03 read "2 ene 2022" in Santiago, R3 c12 B1 and c15 B1).
export const daySeconds = (day: string): number => Date.parse(`${day}T00:00:00Z`) / 1000;
