- Tests: the capture tool's test stops a run after 540 s instead of 240 s and says so when it does; inside the whole vitest run
  on every core the variants-all run of C18 and C20 had gone past 240 s and been read as an empty output (the file alone passes, 274 s).
