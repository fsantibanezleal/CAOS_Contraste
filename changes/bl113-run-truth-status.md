- Methods compared (contract `benchmark-methods` 2.0.0, api 42.0.0): every run of the document states `truth_status`, copied by the builder from the
  `provenance.truth_status` of the case documents it cites (a run whose documents disagree, or a document without a status, stops the build; the six runs that
  cite manuscript result files only declare it in the specification with a reason). The Benchmark page labels each chart from that field with `provenanceOf`
  and keeps no list of run ids: Q10's labelled run now reads synthetic and Q12's twin real, which the typed list had the wrong way round (requirements BM-018, BM-115).
- The reader texts of the document no longer carry a backlog id, a computation id or the method list by its process name; the pointer is the structured field
  `backlog` of each `absent[]` and `left_out[]` entry (BM-019, BM-117). A negative result carries the concept DOI of its manuscript and the page shows the
  published title linked to it instead of a file path (BM-020, BM-116).
