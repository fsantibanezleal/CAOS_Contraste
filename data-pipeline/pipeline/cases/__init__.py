"""The cases (SDD section 5). Each case module exposes ``CASE``, an object with ``id``, ``slug``, ``title``,
``category_id``, ``question``, ``sources`` and ``bake(seed, paths, data_root) -> manifest``; the registry lists
them in ``CASES``. A case is added by the unit that builds it, end to end, never as a placeholder."""
from __future__ import annotations

from .c01_retail_pd import CASE as C01
from .c05_ldp_calibration import CASE as C05
from .c22_validator import CASE as C22

CASES: list = [C01, C05, C22]
