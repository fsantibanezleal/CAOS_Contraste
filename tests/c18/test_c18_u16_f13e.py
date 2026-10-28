"""U16-F13e (fix round 6, the fifth capture review R5, batch c25 n1): the NGFS policy-shock window names the scenario, not the provider,
as the one Phase 5 scenario NGFS classes as disorderly ("NGFS is the only Phase 5 scenario NGFS itself classes as disorderly")."""
from __future__ import annotations

import inspect

from pipeline.cases.c18 import params as P
from pipeline.cases.c18 import scenarios, spanish

LABEL = ("The policy shock acts in 2031 to 2033: zero deviation through 2030 and the first deviation in 2031 (F8 of the research "
         "addendum). The delayed transition is the only Phase 5 scenario that NGFS classes as disorderly.")


def test_n1_the_window_names_the_scenario_as_the_disorderly_one() -> None:
    src = inspect.getsource(scenarios)
    assert "NGFS is the only Phase 5 scenario" not in src
    assert "The delayed transition is the only Phase 5 scenario that NGFS classes as disorderly." in src
    es = P.text(LABEL)["es"]
    assert es.endswith("La transición tardía es el único escenario de la Fase 5 que la NGFS clasifica como desordenado."), es
    assert not any(k.endswith("NGFS itself classes as disorderly.") for k in spanish.SPANISH)
