"""The regulatory parity bake (unit U9-P2): the official worked examples and the invariant cases of the regulation page, run through
``riskvalidation.regulatory`` and written, with their paragraph and in-force date, to ``data/derived/regulatory/calculators.json``
(the ``regulatory-calculators`` contract, docs/contracts/schemas/regulatory/calculators.schema.json). The live TypeScript ports of the
regulation page and of C12 are held to that document at 1e-9 relative.

``inputs.json`` holds the inputs (the CRE99 trade inputs transcribed from the BIS page, the RBC20.13 and invariant inputs, the values the
framework publishes, the CRE20 grid keys); it holds no output. ``bake`` computes every output through the engine. The heavy modules load
when the bake runs, never at discovery.
"""
from __future__ import annotations

DOCUMENT_REL = "regulatory/calculators.json"
