"""The cross-field checks of the C18 documents, as importable functions (as U7 M3, U10 D3 and U11 do).

JSON Schema cannot hold these: they compare values across fields, recompute numbers, or compare documents. The C18 bake (U13-P1)
calls ``violations`` on every document it writes (a non-empty list is a refusal to publish) and ``cross_violations`` on the set of its
documents; the producer tests run both over the fixtures and over ``data/derived/C18``. The formulas are written here from the
dossiers (03 B.2, B.4, G.4, H.2; 05 G.1 to G.5, H.1, H.5; 06 B.12) and the U13 research addendum (F5 to F8), and do not import the
fixture builder. Standard library only.

``violations(doc)`` takes one document (a variant or the models artifact) and returns a list of messages, empty when it conforms;
``cross_violations(docs)`` takes a mapping from a short key (``baseline``, ``eba``, ``fed``, ``ngfs``, ``aggregation``, ``reverse``,
``models``) to the documents of one bake and checks what must agree between them.
"""
from __future__ import annotations

import math
from statistics import NormalDist
from typing import Any

RISKS = ["credit", "market", "irrbb", "operational"]
FED_TYPES = ["commercial-industrial", "commercial-real-estate", "residential", "credit-cards", "other-consumer"]
CLASSES = ["commercial", "consumer", "mortgage"]
ANNEX3_ROWS = [  # F7: CMF RAN 21-13 Annex 3, Circular 2.365, the labels as printed
    ("1", "Ratios de capital"), ("1.1", "PE / APR"), ("1.2", "T1 / APR"), ("1.3", "CET1 / APR"),
    ("2", "Patrimonio efectivo"), ("2.T2", "T2"), ("2.AT1", "AT1"), ("2.CET1", "CET1"), ("3", "APR"),
    ("4", "Cuantificacion del capital necesario"), ("4.1", "Riesgo de credito"), ("4.1.1", "Metodo estandar"),
    ("4.1.2", "Modelo interno"), ("4.2", "Riesgo de mercado (ME)"), ("4.3", "Riesgo operacional (ME)"),
    ("4.4", "Riesgo de concentracion"), ("4.4.1", "Individual"), ("4.4.2", "Sectorial"), ("4.4.3", "Otro tipo"),
    ("4.5", "RMLB"), ("4.6", "Riesgo estrategico"), ("4.7", "Riesgo reputacional"), ("4.8", "Otros riesgos materiales"),
    ("5", "OI"),
    ("6", "Cuantificacion del capital necesario por riesgos no cubiertos en pilar 1 (4.4+4.5+4.6+4.7+4.8)"),
    ("7", "Exigencia minima de PE, en periodo de planificacion (8%+7.1+7.2)"),
    ("7.1", "Exigencia adicional de PE por art.66 quater (banco sistemico)"),
    ("7.2", "Exigencia adicional de PE por art.66 quinquies"),
    ("8", "Cuantificacion del capital necesario por riesgos no cubiertos en pilar 1, y no exigidos por art.66 quinquies (6-7.2)"),
    ("9", "Colchones de conservacion y contra ciclico, en periodo de planificacion (art.66 bis y 66 ter)"),
    ("10.1", "Impacto en indice de capital basico de las pruebas de tension severas, sin mitigacion"),
    ("10.2", "Impacto en indice de capital basico de las pruebas de tension severas, con mitigacion"),
    ("11", "Componente d) del OI"),
    ("12", "Holgura de indice de patrimonio efectivo respecto del OI (1.1 - 5)"),
]
NGFS_VARIABLES = [  # F8: the NiGEM variable names and units as printed (the GDP unit has two spaces)
    ("Unemployment rate ; %(combined)", "Abs. difference"),
    ("Central bank Intervention rate (policy interest rate) ; %(combined)", "Abs. difference"),
    ("Long term interest rate ; %(combined)", "Abs. difference"),
    ("Gross Domestic Product (GDP)(combined)", "% difference,  2017 PPP ; US$ Bn"),
]
EBA_PARAGRAPHS = ["24", "33", "34", "90", "91", "92"]
BAND_METHODS = ["lower-bound", "simple-sum", "variance-covariance", "gaussian-copula", "t-copula", "worst-case"]
TOL = 1e-6


# ------------------------------------------------------------------------------------------------ small numerics


def close(a: float, b: float, rel: float = TOL, abs_: float = 1e-6) -> bool:
    return abs(a - b) <= max(abs_, rel * max(abs(a), abs(b)))


def quarter_end(year: int, quarter: int) -> str:
    return f"{year:04d}-{('03-31', '06-30', '09-30', '12-31')[quarter - 1]}"


def q_index(date: str) -> int:
    y, m = int(date[:4]), int(date[5:7])
    return y * 4 + (m // 3 - 1)


def q_date(index: int) -> str:
    return quarter_end(index // 4, index % 4 + 1)


def contiguous_quarters(dates: list[str]) -> bool:
    idx = [q_index(d) for d in dates]
    return all(b - a == 1 for a, b in zip(idx, idx[1:]))


def eigenvalues_symmetric(m: list[list[float]]) -> list[float]:
    """The eigenvalues of a small symmetric matrix by cyclic Jacobi rotations."""
    n = len(m)
    a = [row[:] for row in m]
    for _ in range(100):
        off = sum(a[i][j] ** 2 for i in range(n) for j in range(n) if i != j)
        if off < 1e-22:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                if abs(a[p][q]) < 1e-300:
                    continue
                theta = (a[q][q] - a[p][p]) / (2 * a[p][q])
                t = (1.0 if theta >= 0 else -1.0) / (abs(theta) + math.sqrt(theta * theta + 1))
                c = 1 / math.sqrt(t * t + 1)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p], a[k][q] = c * akp - s * akq, s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k], a[q][k] = c * apk - s * aqk, s * apk + c * aqk
    return sorted(a[i][i] for i in range(n))


def solve(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        m[col], m[piv] = m[piv], m[col]
        for r in range(col + 1, n):
            f = m[r][col] / m[col][col]
            for c in range(col, n + 1):
                m[r][c] -= f * m[col][c]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (m[i][n] - sum(m[i][j] * x[j] for j in range(i + 1, n))) / m[i][i]
    return x


def gamma_q(a: float, x: float) -> float:
    """The regularised upper incomplete gamma function Q(a, x) (series for x < a + 1, continued fraction otherwise)."""
    if x <= 0:
        return 1.0
    gln = math.lgamma(a)
    if x < a + 1:
        ap, s, d = a, 1.0 / a, 1.0 / a
        for _ in range(500):
            ap += 1
            d *= x / ap
            s += d
            if abs(d) < abs(s) * 1e-15:
                break
        return 1.0 - s * math.exp(-x + a * math.log(x) - gln)
    b = x + 1 - a
    c = 1e300
    d = 1.0 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = 1e-300 if abs(d) < 1e-300 else d
        c = b + an / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return math.exp(-x + a * math.log(x) - gln) * h


def chi2_sf(x: float, df: int) -> float:
    return gamma_q(df / 2.0, x / 2.0)


def link(name: str, p: float) -> float:
    return NormalDist().inv_cdf(p) if name == "probit" else math.log(p / (1 - p))


def varcov(ec: list[float], r: list[list[float]]) -> float:
    return math.sqrt(sum(ec[i] * r[i][j] * ec[j] for i in range(len(ec)) for j in range(len(ec))))


def matrix_problems(m: list[list[float]], name: str) -> list[str]:
    out = []
    n = len(m)
    if any(len(r) != n for r in m):
        return [f"{name}: not square"]
    for i in range(n):
        if not close(m[i][i], 1.0, 1e-9, 1e-9):
            out.append(f"{name}: diagonal {i} is {m[i][i]}, not 1")
        for j in range(i + 1, n):
            if not close(m[i][j], m[j][i], 1e-12, 1e-12):
                out.append(f"{name}: not symmetric at ({i}, {j})")
    if not out and min(eigenvalues_symmetric(m)) < -1e-9:
        out.append(f"{name}: not positive semi-definite (smallest eigenvalue {min(eigenvalues_symmetric(m)):.6f})")
    return out


def cov_problems(cov: list[list[float]], sd: list[float], name: str) -> list[str]:
    out = []
    n = len(cov)
    if any(len(r) != n for r in cov) or n != len(sd):
        return [f"{name}: the covariance is not square or does not match the factors"]
    for i in range(n):
        if not close(cov[i][i], sd[i] ** 2, 1e-6, 1e-9):
            out.append(f"{name}: variance {i} is {cov[i][i]}, the sd squared is {sd[i] ** 2}")
        for j in range(i + 1, n):
            if not close(cov[i][j], cov[j][i], 1e-12, 1e-12):
                out.append(f"{name}: not symmetric at ({i}, {j})")
    if not out and min(eigenvalues_symmetric(cov)) < -1e-12:
        out.append(f"{name}: not positive semi-definite")
    return out


# ------------------------------------------------------------------------------------------------ the aggregation block


def ref_row(band: list[dict], ref: dict) -> dict | None:
    for r in band:
        if r["method"] == ref["method"] and (r["method"] != "t-copula" or r["nu"] == ref["nu"]):
            return r
    return None


def aggregation_violations(agg: dict, where: str) -> list[str]:
    out: list[str] = []
    marg = agg["marginals"]
    if [m["risk"] for m in marg] != RISKS:
        out.append(f"{where}: the marginals are not credit, market, irrbb, operational in that order")
        return out
    for m in marg:
        r = m["risk"]
        if not close(m["ec_clp_m"], m["var_clp_m"] - m["el_clp_m"]):
            out.append(f"{where}: marginal {r}: ec {m['ec_clp_m']} is not var - el = {m['var_clp_m'] - m['el_clp_m']}")
        if m["var_clp_m"] < m["el_clp_m"] - 1e-6:
            out.append(f"{where}: marginal {r}: var is below the expected loss")
        if m["es_clp_m"] < m["var_clp_m"] - 1e-6:
            out.append(f"{where}: marginal {r}: es is below var")
    ec = [m["ec_clp_m"] for m in marg]
    total = sum(ec)
    if not close(agg["headline"]["capital_clp_m"], total):
        out.append(f"{where}: the headline capital {agg['headline']['capital_clp_m']} is not the simple sum {total}")
    corr = agg["correlation"]
    out += matrix_problems(corr["matrix"], f"{where}: correlation")
    nus = sorted(agg["nu_set"]["values"])
    if len(set(nus)) != len(nus) or any(v <= 2 for v in nus):
        out.append(f"{where}: the nu set must be distinct values above 2")
    band = agg["band"]
    by_method = {m: [r for r in band if r["method"] == m] for m in BAND_METHODS}
    for m in BAND_METHODS:
        if m != "t-copula" and len(by_method[m]) != 1:
            out.append(f"{where}: the band has {len(by_method[m])} rows of {m}, expected one")
    t_nus = sorted(r["nu"] for r in by_method["t-copula"])
    if t_nus != nus:
        out.append(f"{where}: the t rows {t_nus} are not the nu set {nus}")
    for r in band:
        if total > 0 and not close(r["diversification_factor"], r["capital_clp_m"] / total):
            out.append(f"{where}: band row {r['method']} {r['nu']}: diversification_factor {r['diversification_factor']} is not capital / simple sum")
    simple = by_method["simple-sum"]
    if simple and not close(simple[0]["capital_clp_m"], total):
        out.append(f"{where}: the simple-sum row {simple[0]['capital_clp_m']} is not the sum of the marginals {total}")
    vc = by_method["variance-covariance"]
    if vc and not matrix_problems(corr["matrix"], "r") and not close(vc[0]["capital_clp_m"], varcov(ec, corr["matrix"]), 1e-5):
        out.append(f"{where}: the variance-covariance row {vc[0]['capital_clp_m']} is not sqrt(EC' R EC) = {varcov(ec, corr['matrix']):.6f}")
    lower, worst = by_method["lower-bound"], by_method["worst-case"]
    others = [r["capital_clp_m"] for r in band if r["method"] not in ("lower-bound", "worst-case")]
    if lower and others and lower[0]["capital_clp_m"] > min(others) + 1e-6:
        out.append(f"{where}: the lower bound is above another row of the band")
    if worst and others and worst[0]["capital_clp_m"] < max(others) - 1e-6:
        out.append(f"{where}: the worst case is below another row of the band")
    if lower and worst and lower[0]["capital_clp_m"] > worst[0]["capital_clp_m"] + 1e-6:
        out.append(f"{where}: the lower bound is above the worst case")
    for r in band:
        if r["method"] in ("variance-covariance", "gaussian-copula", "t-copula") and r["capital_clp_m"] > total * (1 + 1e-9) + 1e-6:
            out.append(f"{where}: band row {r['method']} {r['nu']} is above the simple sum: a diversification benefit with the wrong sign")
    # model risk (06 l.692-698)
    mr = agg["model_risk"]
    x0 = ref_row(band, mr["reference_model"])
    caps = [r["capital_clp_m"] for r in band]
    if x0 is None:
        out.append(f"{where}: the model risk reference model is not a row of the band")
    else:
        hi, lo = max(caps), min(caps)
        bs = mr["barrieu_scandolo"]
        for k, v in (("rho_x0_clp_m", x0["capital_clp_m"]), ("rho_max_clp_m", hi), ("rho_min_clp_m", lo)):
            if not close(bs[k], v):
                out.append(f"{where}: model risk {k} {bs[k]} is not {v}")
        if x0["capital_clp_m"] > 0 and not close(bs["am"], hi / x0["capital_clp_m"] - 1, 1e-5, 1e-7):
            out.append(f"{where}: model risk AM {bs['am']} is not max / rho(X0) - 1 = {hi / x0['capital_clp_m'] - 1:.6f}")
        rm = 0.0 if hi == lo else (hi - x0["capital_clp_m"]) / (hi - lo)
        if not close(bs["rm"], rm, 1e-5, 1e-7):
            out.append(f"{where}: model risk RM {bs['rm']} is not (max - rho(X0)) / (max - min) = {rm:.6f}")
    gx = mr["glasserman_xu"]
    if gx["worst_case_clp_m"] < gx["baseline_clp_m"] - 1e-6:
        out.append(f"{where}: the Glasserman and Xu worst case is below its baseline")
    # Euler allocation (05 G.4) and the diversification
    eu = agg["euler"]
    contribs = [a["contribution_clp_m"] for a in eu["allocation"]]
    if [a["risk"] for a in eu["allocation"]] != RISKS:
        out.append(f"{where}: the Euler allocation is not in the order of the marginals")
    s = sum(contribs)
    if not close(eu["additivity"]["sum_clp_m"], s):
        out.append(f"{where}: euler.additivity.sum_clp_m {eu['additivity']['sum_clp_m']} is not the sum of the contributions {s}")
    if not close(s, eu["es_total_clp_m"], eu["additivity"]["tolerance"], 1e-6):
        out.append(f"{where}: the Euler contributions add up to {s}, not to the aggregate ES {eu['es_total_clp_m']}")
    rel = abs(s - eu["es_total_clp_m"]) / eu["es_total_clp_m"] if eu["es_total_clp_m"] else 0.0
    if not close(eu["additivity"]["relative_error"], rel, 1e-6, 1e-9):
        out.append(f"{where}: euler relative_error {eu['additivity']['relative_error']} is not {rel}")
    if eu["es_total_clp_m"] > sum(m["es_clp_m"] for m in marg) * (1 + 1e-9) + 1e-6:
        out.append(f"{where}: the aggregate ES is above the sum of the marginal ES (ES is subadditive)")
    for a in eu["allocation"]:
        if eu["es_total_clp_m"] and not close(a["share"], a["contribution_clp_m"] / eu["es_total_clp_m"], 1e-6, 1e-9):
            out.append(f"{where}: euler share of {a['risk']} is not its contribution over the total")
    cop = eu["copula"]
    if cop["family"] == "gaussian":
        if cop["nu"] is not None or not by_method["gaussian-copula"]:
            out.append(f"{where}: a Gaussian Euler allocation has no nu and needs the Gaussian row")
    elif not any(r["nu"] == cop["nu"] for r in by_method["t-copula"]):
        out.append(f"{where}: the Euler allocation names a t copula that is not a row of the band")
    dv = agg["diversification"]
    row = ref_row(band, dv["reference_row"])
    if row is None:
        out.append(f"{where}: the diversification reference row is not a row of the band")
    else:
        if not close(dv["factor"], row["diversification_factor"]):
            out.append(f"{where}: the diversification factor {dv['factor']} is not that of its reference row {row['diversification_factor']}")
        if not close(dv["benefit"], 1 - dv["factor"]):
            out.append(f"{where}: the diversification benefit is not 1 - factor")
        if dv["factor"] > 1 + 1e-9:
            out.append(f"{where}: the diversification factor is above 1: a diversification benefit with the wrong sign")
    for b, a, m in zip(dv["euler_benefit_by_risk"], eu["allocation"], marg):
        if [b["risk"]] != [a["risk"]] or (m["es_clp_m"] and not close(b["benefit"], 1 - a["contribution_clp_m"] / m["es_clp_m"], 1e-6, 1e-9)):
            out.append(f"{where}: the Euler diversification benefit of {b['risk']} is not 1 - contribution / standalone ES")
    return out


# ------------------------------------------------------------------------------------------------ the scenario variant


def annex_value(rows: dict[str, dict], row_id: str, col: str) -> float | None:
    cell = rows[row_id][col]
    return cell["value"] if cell["status"] == "value" else None


def path_violations(o: dict) -> list[str]:
    out: list[str] = []
    sc, as_of = o["scenario"], o["bank"]["as_of"]
    if sc["vintage_date"] > as_of:
        out.append(f"scenario: the vintage {sc['vintage_date']} postdates the observation date {as_of}")
    for i, p in enumerate(sc["paths"]):
        where = f"scenario.paths[{i}] {p['variable']}"
        if p["vintage_date"] > as_of:
            out.append(f"{where}: the vintage {p['vintage_date']} postdates the observation date {as_of}")
        kind, base = p["level_rule"]["kind"], p["level_rule"]["baseline"]
        src, lev = p["source"], p["levels"]
        if len(lev) != len(src):
            out.append(f"{where}: levels and source differ in length")
            continue
        for k, (s, lv) in enumerate(zip(src, lev)):
            if s["date"] != lv["date"]:
                out.append(f"{where}: levels[{k}] and source[{k}] differ in date")
            if kind == "level":
                want = s["value"]
            else:
                if base is None or len(base) != len(src) or base[k]["date"] != s["date"]:
                    out.append(f"{where}: the baseline does not match the deviation path in length and dates")
                    break
                want = base[k]["value"] + s["value"] if kind == "baseline-plus-deviation" else base[k]["value"] * (1 + s["value"] / 100)
            if not close(lv["value"], want, 1e-6, 1e-6):
                out.append(f"{where}: levels[{k}] {lv['value']} is not {want} ({kind})")
        tr = p["transposition"]
        t = p["transposed"]
        dates = [q["date"] for q in t]
        if q_index(tr["target"]["date"]) + 1 != q_index(dates[0]) or not contiguous_quarters(dates):
            out.append(f"{where}: the transposed quarters are not the 12 quarters after the target date")
        if p["frequency"] == "quarterly":
            for k in range(min(len(t), len(lev))):
                want = tr["target"]["value"] + (lev[k]["value"] - tr["source_jump_off"]["value"])
                if not close(t[k]["value"], want, 1e-6, 1e-6):
                    out.append(f"{where}: transposed[{k}] {t[k]['value']} is not the target plus the change of the source from its jump-off ({want})")
        elif kind != "baseline-times-percent-deviation":
            prev = tr["source_jump_off"]["value"]
            for y, lv in enumerate(lev):
                for k in range(1, 5):
                    idx = 4 * y + k - 1
                    if idx >= len(t):
                        break
                    shape = prev + (lv["value"] - prev) * k / 4 - tr["source_jump_off"]["value"]
                    want = tr["target"]["value"] + shape
                    if not close(t[idx]["value"], want, 1e-6, 1e-6):
                        out.append(f"{where}: transposed[{idx}] {t[idx]['value']} is not the year-end join of the shape ({want})")
                prev = lv["value"]
    if sc["provider"] == "ngfs":
        names = sorted((p["variable"], p["unit"]) for p in sc["paths"])
        if names != sorted(NGFS_VARIABLES):
            out.append("scenario: the NGFS paths are not the four NiGEM variables of the record, named and with their units exactly")
        w = sc["policy_shock_window"]
        if w is None or w["end_year"] - w["start_year"] != 2:
            out.append("scenario: the NGFS policy shock window is not three calendar years")
        elif any(not (w["start_year"] <= int(q["date"][:4]) <= w["end_year"]) for p in sc["paths"] for q in p["source"]):
            out.append("scenario: an NGFS path point lies outside the policy shock window")
    return out


def satellite_violations(o: dict) -> list[str]:
    out: list[str] = []
    sat = o["satellites"]
    rates: dict[str, list[float]] = {}
    first = None
    for p in sat["fed_loan_types"]:
        qs = p["quarters"]
        dates = [q["quarter_end"] for q in qs]
        if not contiguous_quarters(dates):
            out.append(f"satellites: {p['fed_loan_type']}: the quarters are not contiguous")
        first = dates[0] if first is None else first
        if dates[0] != first:
            out.append(f"satellites: {p['fed_loan_type']}: the projection starts in another quarter")
        rates[p["fed_loan_type"]] = [q["rate"] for q in qs]
        for q in qs:
            if not close(q["link_value"], link(p["link"], q["rate"]), 1e-6, 1e-9):
                out.append(f"satellites: {p['fed_loan_type']} {q['quarter_end']}: link_value is not the {p['link']} of the rate")
                break
    tr_dates = {path["transposition"]["target"]["date"] for path in o["scenario"]["paths"]}
    if first is not None and len(tr_dates) == 1 and q_index(first) != q_index(next(iter(tr_dates))) + 1:
        out.append("satellites: the projection does not start the quarter after the transposition target date")
    for c in sat["banco_andino_classes"]:
        w = c["weights"]
        if len(w) != len(c["maps_from"]) or not close(sum(w), 1.0, 1e-9, 1e-9):
            out.append(f"satellites: class {c['banco_andino_class']}: the weights do not sum to 1")
            continue
        if any(t not in rates for t in c["maps_from"]):
            out.append(f"satellites: class {c['banco_andino_class']} maps from a type that has no projection")
            continue
        for k, q in enumerate(c["quarters"]):
            want = sum(wi * rates[t][k] for wi, t in zip(w, c["maps_from"]))
            if not close(q["rate"], want, 1e-6, 1e-9):
                out.append(f"satellites: class {c['banco_andino_class']} {q['quarter_end']}: rate {q['rate']} is not the weighted mix {want}")
                break
    return out


def capital_violations(o: dict) -> list[str]:
    out: list[str] = []
    cs_ = o["capital_start"]
    rwa = cs_["rwa_clp_m"]
    if not close(sum(cs_["rwa_by_risk"].values()), rwa):
        out.append("capital_start: rwa_by_risk does not add up to the RWA")
    if not close(cs_["pe_clp_m"], cs_["cet1_clp_m"] + cs_["at1_clp_m"] + cs_["t2_clp_m"]):
        out.append("capital_start: pe is not CET1 + AT1 + T2")
    if not close(cs_["cet1_ratio"], cs_["cet1_clp_m"] / rwa, 1e-6, 1e-9):
        out.append("capital_start: cet1_ratio is not CET1 over RWA")
    if not close(cs_["pe_ratio"], cs_["pe_clp_m"] / rwa, 1e-6, 1e-9):
        out.append("capital_start: pe_ratio is not PE over RWA")
    oi = o["internal_capital_target"]
    want_oi = oi["min_pe"] + oi["c_dsib"] + oi["c_p2"]["value"] + oi["c_ccob"] + oi["c_ccyb"] + oi["c_d"]["value"]
    if not close(oi["oi"], want_oi, 1e-9, 1e-9):
        out.append(f"internal_capital_target: oi {oi['oi']} is not 8% + c_DSIB + c_P2 + c_CCoB + c_CCyB + c_d = {want_oi}")
    for k in ("c_p2", "c_d"):
        if oi[k]["value"] < 0:
            out.append(f"internal_capital_target: {k} is negative")
    losses = o["losses"]["scenario_losses"]
    for y in losses:
        if not close(y["total"], y["credit"] + y["market"] + y["irrbb"] + y["operational"]):
            out.append(f"losses: year {y['year']}: total is not the sum of the four risks")
    if [y["year"] for y in losses] != [1, 2, 3] and sorted(y["year"] for y in losses) != [1, 2, 3]:
        out.append("losses: the years are not 1, 2, 3")
    losses = sorted(losses, key=lambda y: y["year"])
    # headline and PPNR
    h = o["headline_cet1"]
    cum, prev = 0.0, cs_["cet1_clp_m"]
    cet1_path = []
    for y, row in zip(losses, h["rows"]):
        cum += y["total"]
        want = cs_["cet1_clp_m"] - cum
        cet1_path.append(want)
        if not close(row["cumulative_loss_clp_m"], cum):
            out.append(f"headline_cet1: year {row['year']}: cumulative loss {row['cumulative_loss_clp_m']} is not {cum}")
        if not close(row["cet1_clp_m"], want):
            out.append(f"headline_cet1: year {row['year']}: cet1 {row['cet1_clp_m']} is not the loss-only depletion {want}")
        if not close(row["cet1_start_clp_m"], prev):
            out.append(f"headline_cet1: year {row['year']}: cet1_start is not the previous year end")
        if not close(row["rwa_clp_m"], rwa):
            out.append(f"headline_cet1: year {row['year']}: the RWA changes: the balance sheet is static")
        if not close(row["cet1_ratio"], row["cet1_clp_m"] / row["rwa_clp_m"], 1e-6, 1e-9):
            out.append(f"headline_cet1: year {row['year']}: cet1_ratio is not CET1 over RWA")
        prev = row["cet1_clp_m"]
    pp = h["ppnr"]
    fee, cost = pp["fee_ratio"]["value"], pp["cost_ratio"]["value"]
    cum_ppnr = 0.0
    for row, base_cet1 in zip(pp["rows"], cet1_path):
        want_fee = fee * row["nii_clp_m"]
        want_cost = cost * (row["nii_clp_m"] + want_fee)
        want_ppnr = row["nii_clp_m"] + want_fee - want_cost
        cum_ppnr += row["ppnr_clp_m"]
        for k, v in (("fee_income_clp_m", want_fee), ("operating_cost_clp_m", want_cost), ("ppnr_clp_m", want_ppnr)):
            if not close(row[k], v):
                out.append(f"headline_cet1.ppnr: year {row['year']}: {k} {row[k]} is not {v}")
        if not close(row["cet1_with_ppnr_clp_m"], base_cet1 + cum_ppnr):
            out.append(f"headline_cet1.ppnr: year {row['year']}: cet1_with_ppnr is not the loss-only path plus the cumulated PPNR")
        if not close(row["cet1_ratio_with_ppnr"], row["cet1_with_ppnr_clp_m"] / rwa, 1e-6, 1e-9):
            out.append(f"headline_cet1.ppnr: year {row['year']}: cet1_ratio_with_ppnr is not CET1 over RWA")
    # P2G proxy (03 l.1001-1005)
    p2g = o["p2g_proxy"]
    depletion = [cs_["cet1_ratio"] - c / rwa for c in cet1_path]
    peak = max(depletion)
    if not close(p2g["peak_depletion"], peak, 1e-6, 1e-9):
        out.append(f"p2g_proxy: peak_depletion {p2g['peak_depletion']} is not the maximum over the years of the CET1/RWA fall {peak}")
    if p2g["peak_year"] != depletion.index(peak) + 1:
        out.append("p2g_proxy: peak_year is not the year of the peak depletion")
    if not close(p2g["value"], max(0.0, p2g["peak_depletion"] - p2g["usable_buffers_and_mitigation"]), 1e-9, 1e-9):
        out.append("p2g_proxy: value is not max(0, peak depletion - usable buffers and mitigation)")
    # the capital plan
    plan = {c["case"]: c for c in o["capital_plan"]["cases"]}
    rows = {r["row_id"]: r for r in o["annex3"]["rows"]}
    legal = annex_value(rows, "7", "a") if "7" in rows else None
    mit = o["capital_plan"]["mitigation"]
    actions_cum = [0.0, 0.0, 0.0]
    if mit["applies"]:
        running = 0.0
        for k in range(3):
            running += sum(a["cet1_effect_clp_m"][k] for a in mit["actions"])
            actions_cum[k] = running
    for name, case in plan.items():
        for k, y in enumerate(sorted(case["years"], key=lambda x: x["year"])):
            where = f"capital_plan.{name} year {y['year']}"
            if not close(y["rwa_clp_m"], rwa):
                out.append(f"{where}: the RWA changes: the balance sheet is static (EBA para 33)")
            for t in ("cet1", "at1", "t2", "pe"):
                if not close(y[t]["pct_of_rwa"], y[t]["available_clp_m"] / y["rwa_clp_m"], 1e-6, 1e-9):
                    out.append(f"{where}: {t}.pct_of_rwa is not available over RWA")
            if not close(y["pe"]["available_clp_m"], y["cet1"]["available_clp_m"] + y["at1"]["available_clp_m"] + y["t2"]["available_clp_m"]):
                out.append(f"{where}: pe is not CET1 + AT1 + T2")
            req = y["requirement"]["pct_of_rwa"]
            if y["pe"]["need_clp_m"] is None or not close(y["pe"]["need_clp_m"], req * y["rwa_clp_m"]):
                out.append(f"{where}: the PE need is not the requirement times RWA")
            if not close(y["headroom_pct_of_rwa"], y["pe"]["pct_of_rwa"] - req, 1e-6, 1e-9):
                out.append(f"{where}: headroom is not the PE ratio less the requirement")
            deficit = max(0.0, req * y["rwa_clp_m"] - y["pe"]["available_clp_m"])
            if not close(y["deficit_clp_m"], deficit):
                out.append(f"{where}: deficit {y['deficit_clp_m']} is not max(0, need - available) = {deficit}")
            if name == "base" and not close(req, oi["oi"], 1e-9, 1e-9):
                out.append(f"{where}: the base requirement is not the internal target")
            if name != "base" and legal is not None and not close(req, legal, 1e-9, 1e-9):
                out.append(f"{where}: the stress requirement is not the legal minimum of Annex 3 row 7")
            if name == "stress-without-mitigation" and not close(y["cet1"]["available_clp_m"], cet1_path[k]):
                out.append(f"{where}: CET1 is not the loss-only headline path")
            if name == "stress-with-mitigation" and not close(y["cet1"]["available_clp_m"], cet1_path[k] + actions_cum[k]):
                out.append(f"{where}: CET1 is not the loss-only path plus the mitigation actions")
            if name == "stress-without-mitigation" and (not close(y["at1"]["available_clp_m"], cs_["at1_clp_m"]) or not close(y["t2"]["available_clp_m"], cs_["t2_clp_m"])):
                out.append(f"{where}: AT1 and T2 change under stress: no capital measure after the reference date (EBA para 33)")
    if o["scenario"]["scenario_id"] == "baseline" and "base" in plan:
        cet1 = cs_["cet1_clp_m"]
        for k, y in enumerate(sorted(plan["base"]["years"], key=lambda x: x["year"])):
            cet1 += pp["rows"][k]["ppnr_clp_m"] - losses[k]["total"]
            if not close(y["cet1"]["available_clp_m"], cet1):
                out.append(f"capital_plan.base year {y['year']}: CET1 is not the previous CET1 plus the baseline PPNR less the baseline losses")
    return out


def annex3_violations(o: dict) -> list[str]:
    out: list[str] = []
    rws = o["annex3"]["rows"]
    if [(r["row_id"], r["label_cmf"]) for r in rws] != ANNEX3_ROWS:
        out.append("annex3: the rows or their labels differ from the CMF form (Annex 3, Circular 2.365)")
        return out
    rows = {r["row_id"]: r for r in rws}
    cs_, oi = o["capital_start"], o["internal_capital_target"]
    rwa = cs_["rwa_clp_m"]
    checks = [
        ("3", "b", rwa), ("2", "b", cs_["pe_clp_m"]), ("2.CET1", "b", cs_["cet1_clp_m"]), ("2.AT1", "b", cs_["at1_clp_m"]),
        ("2.T2", "b", cs_["t2_clp_m"]), ("1.1", "a", cs_["pe_ratio"]), ("1.2", "a", (cs_["cet1_clp_m"] + cs_["at1_clp_m"]) / rwa),
        ("1.3", "a", cs_["cet1_ratio"]), ("5", "a", oi["oi"]), ("11", "a", oi["c_d"]["value"]), ("9", "a", oi["c_ccob"] + oi["c_ccyb"]),
        ("7.1", "a", oi["c_dsib"]),
    ]
    for rid, col, want in checks:
        got = annex_value(rows, rid, col)
        if got is None or not close(got, want, 1e-6, 1e-9):
            out.append(f"annex3: row {rid} column {col} is {got}, expected {want}")
    r71, r72, r7 = annex_value(rows, "7.1", "a"), annex_value(rows, "7.2", "a"), annex_value(rows, "7", "a")
    if None in (r71, r72, r7) or not close(r7, 0.08 + r71 + r72, 1e-9, 1e-9):
        out.append("annex3: row 7 is not 8% + 7.1 + 7.2")
    if r72 is not None and oi["c_p2"]["value"] < r72 - 1e-12:
        out.append("annex3: c_P2 of the internal target is below the art. 66 quinquies requirement of row 7.2")
    r11, r5 = annex_value(rows, "1.1", "a"), annex_value(rows, "5", "a")
    r12 = annex_value(rows, "12", "a")
    if None in (r11, r5, r12) or not close(r12, r11 - r5, 1e-9, 1e-9):
        out.append("annex3: row 12 is not row 1.1 less row 5")
    r6, r8 = annex_value(rows, "6", "a"), annex_value(rows, "8", "a")
    if r6 is not None and r8 is not None and r72 is not None and not close(r8, r6 - r72, 1e-9, 1e-9):
        out.append("annex3: row 8 is not row 6 less row 7.2")
    plan = {c["case"]: c for c in o["capital_plan"]["cases"]}
    for rid, case in (("10.1", "stress-without-mitigation"), ("10.2", "stress-with-mitigation")):
        years = sorted(plan[case]["years"], key=lambda y: y["year"])
        impact = max(cs_["cet1_ratio"] - y["cet1"]["pct_of_rwa"] for y in years)
        cell = rows[rid]["a"]
        if rid == "10.2" and not o["capital_plan"]["mitigation"]["applies"]:
            if cell["status"] != "not-applicable":
                out.append("annex3: row 10.2 is not N/A though no mitigation applies")
        elif cell["status"] != "value" or not close(cell["value"], impact, 1e-6, 1e-9):
            out.append(f"annex3: row {rid} is {cell['value']}, expected the largest CET1/RWA fall {impact}")
    for rid in ("4.1.1", "4.1.2", "4.2", "4.3", "4.4.1", "4.4.2", "4.4.3", "4.5", "4.6", "4.7", "4.8"):
        a, b = annex_value(rows, rid, "a"), annex_value(rows, rid, "b")
        if a is not None and b is not None and not close(a, b / rwa, 1e-6, 1e-9):
            out.append(f"annex3: row {rid}: column A is not column B over RWA")
    return out


def backcast_violations(o: dict) -> list[str]:
    out: list[str] = []
    b = o["backcast"]
    for t in b["per_loan_type"]:
        qs = t["quarters"]
        dates = [q["quarter_end"] for q in qs]
        if dates[0] != "2020-03-31" or dates[-1] != "2025-12-31" or not contiguous_quarters(dates):
            out.append(f"backcast: {t['fed_loan_type']}: the quarters are not 2020 Q1 to 2025 Q4")
            continue
        m = t["metrics"]
        pred, real = [q["predicted"] for q in qs], [q["realised"] for q in qs]
        rmse = math.sqrt(sum((p - r) ** 2 for p, r in zip(pred, real)) / len(qs))
        if not close(m["rmse"], rmse, 1e-6, 1e-9):
            out.append(f"backcast: {t['fed_loan_type']}: rmse {m['rmse']} is not {rmse}")
        ip, ir = pred.index(max(pred)), real.index(max(real))
        if m["peak_predicted_quarter"] != dates[ip] or not close(m["peak_predicted"], pred[ip], 1e-9, 1e-12):
            out.append(f"backcast: {t['fed_loan_type']}: the predicted peak is not the maximum of the predicted rates")
        if m["peak_realised_quarter"] != dates[ir] or not close(m["peak_realised"], real[ir], 1e-9, 1e-12):
            out.append(f"backcast: {t['fed_loan_type']}: the realised peak is not the maximum of the realised rates")
        if m["peak_timing_error_quarters"] != ip - ir:
            out.append(f"backcast: {t['fed_loan_type']}: the timing error is not the predicted peak quarter less the realised one")
        w = t["fit_window"]
        if w["start"] > w["end"]:
            out.append(f"backcast: {t['fed_loan_type']}: the fit window ends before it starts")
    return out


def scenario_violations(doc: dict) -> list[str]:
    o = doc["outputs"]
    out = aggregation_violations(o["aggregation"], "aggregation")
    out += path_violations(o)
    out += satellite_violations(o)
    out += capital_violations(o)
    out += annex3_violations(o)
    out += backcast_violations(o)
    ids = {"baseline", "eba-2025-adverse", "fed-2026-severely-adverse", "ngfs-delayed-transition"}
    if o["scenario"]["scenario_id"] not in ids:
        out.append("scenario: unknown scenario id")
    imp = doc["impact"]
    plan = {c["case"]: c for c in o["capital_plan"]["cases"]}
    sw = sorted(plan["stress-without-mitigation"]["years"], key=lambda y: y["year"])
    want = {
        "capital_simple_sum": o["aggregation"]["headline"]["capital_clp_m"],
        "cet1_ratio_end_stress": sw[-1]["cet1"]["pct_of_rwa"],
        "oi_headroom_min": min(y["pe"]["pct_of_rwa"] for y in sw) - o["internal_capital_target"]["oi"],
        "p2g_proxy": o["p2g_proxy"]["value"],
    }
    for k, v in want.items():
        if imp[k]["value"] is None or not close(imp[k]["value"], v, 1e-6, 1e-9):
            out.append(f"impact.{k}: {imp[k]['value']} is not {v}")
    return out


# ------------------------------------------------------------------------------------------------ the aggregation variant


def aggregation_variant_violations(doc: dict) -> list[str]:
    o = doc["outputs"]
    out = aggregation_violations(o["aggregation"], "aggregation")
    stress = o["correlation_stress"]["aggregation"]
    out += aggregation_violations(stress, "correlation_stress.aggregation")
    base, st = o["aggregation"], stress
    bm, sm_ = base["correlation"]["matrix"], st["correlation"]["matrix"]
    order = base["correlation"]["order"]
    mi, ci = order.index("market"), order.index("credit")
    for i in range(4):
        for j in range(4):
            want = 0.8 if {i, j} == {mi, ci} else bm[i][j]
            if not close(sm_[i][j], want, 1e-12, 1e-12):
                out.append(f"correlation_stress: the stressed matrix differs from the base outside the market-credit pair at ({i}, {j})")
    if [m for m in base["marginals"]] != [m for m in st["marginals"]]:
        out.append("correlation_stress: the marginals differ from the base: only the correlation is stressed")
    if base["nu_set"] != st["nu_set"]:
        out.append("correlation_stress: the nu set differs from the base")
    for r in base["band"]:
        s = ref_row(st["band"], r)
        if s is None:
            continue
        if r["method"] in ("variance-covariance", "gaussian-copula", "t-copula") and s["capital_clp_m"] < r["capital_clp_m"] - 1e-6:
            out.append(f"correlation_stress: {r['method']} {r['nu']} falls when a correlation is raised")
    gauss = ref_row(base["band"], {"method": "gaussian-copula", "nu": None})
    for s in o["copula_sensitivity"]:
        t_row = next((r for r in base["band"] if r["method"] == "t-copula" and r["nu"] == s["nu"]), None)
        if t_row is None or gauss is None:
            out.append(f"copula_sensitivity: nu {s['nu']} is not a t row of the band")
            continue
        if not close(s["gaussian_capital_clp_m"], gauss["capital_clp_m"]) or not close(s["t_capital_clp_m"], t_row["capital_clp_m"]):
            out.append(f"copula_sensitivity: nu {s['nu']}: the capitals are not the band rows")
        rel = s["t_capital_clp_m"] / s["gaussian_capital_clp_m"] - 1 if s["gaussian_capital_clp_m"] else 0.0
        if not close(s["relative_difference"], rel, 1e-6, 1e-9):
            out.append(f"copula_sensitivity: nu {s['nu']}: relative_difference is not t over Gaussian less one")
    if sorted(s["nu"] for s in o["copula_sensitivity"]) != sorted(base["nu_set"]["values"]):
        out.append("copula_sensitivity: the rows are not the nu set")
    rs = o["rosenberg_schuermann"]
    total = sum(m["ec_clp_m"] for m in base["marginals"])
    if gauss is not None and gauss["capital_clp_m"] > 0:
        over = total / gauss["capital_clp_m"] - 1
        if not close(rs["case_additive_overestimate"], over, 1e-6, 1e-9):
            out.append(f"rosenberg_schuermann: case_additive_overestimate {rs['case_additive_overestimate']} is not simple sum / Gaussian - 1 = {over}")
        within = rs["published_additive_overestimate"]["low"] <= over <= rs["published_additive_overestimate"]["high"]
        if rs["within_published_range"] != within:
            out.append("rosenberg_schuermann: within_published_range does not follow the figure")
    return out


# ------------------------------------------------------------------------------------------------ the reverse variant


def reverse_violations(doc: dict) -> list[str]:
    o = doc["outputs"]
    out: list[str] = []
    fp, fs, sol = o["failure_point"], o["factor_space"], o["solution"]
    st = fp["stack"]
    want_total = st["cet1_min"] + st["c_ccob"] + st["c_ccyb"] + st["c_dsib"] + st["p2_cet1"]["value"]
    if not close(st["total"], want_total, 1e-9, 1e-9):
        out.append(f"failure_point: the stack total {st['total']} is not the sum of its components {want_total}")
    loss_threshold = (fp["cet1_ratio_start"] - st["total"]) * fp["rwa_clp_m"]
    if not close(sol["loss_threshold_clp_m"], loss_threshold, 1e-6, 1e-6):
        out.append(f"solution: loss_threshold {sol['loss_threshold_clp_m']} is not (CET1 ratio - stack) x RWA = {loss_threshold}")
    if fs["window"]["start"] > fs["window"]["end"]:
        out.append("factor_space: the window ends before it starts")
    sd = [f["sd"] for f in fs["factors"]]
    n = len(sd)
    out += cov_problems(fs["covariance"], sd, "factor_space")
    if len(sol["z_star"]) != n or len(sol["x_star"]) != n:
        out.append("solution: z_star and x_star do not match the factors")
        return out
    for z, x, s in zip(sol["z_star"], sol["x_star"], sd):
        if not close(z, x / s, 1e-6, 1e-9):
            out.append("solution: z_star is not x_star over the factor sd")
            break
    if not any(m.startswith("factor_space") for m in out):
        d2 = sum(a * b for a, b in zip(sol["x_star"], solve(fs["covariance"], sol["x_star"])))
        if not close(sol["mahalanobis_distance"], math.sqrt(d2), 1e-6, 1e-9):
            out.append(f"solution: the distance {sol['mahalanobis_distance']} is not sqrt(x' Sigma^-1 x) = {math.sqrt(d2)}")
        pl = sol["plausibility"]
        if pl["chi_square_df"] != n:
            out.append("solution: the chi-square degrees of freedom are not the number of factors")
        want_p = chi2_sf(sol["mahalanobis_distance"] ** 2, n)
        if not close(pl["tail_probability"], want_p, 1e-4, 1e-9):
            out.append(f"solution: the tail probability {pl['tail_probability']} is not P(chi2 >= d^2) = {want_p}")
        lm = o["loss_model"]
        if lm["kind"] == "linear":
            g = lm["gradient_clp_m_per_unit"]
            if len(g) != n:
                out.append("loss_model: the gradient does not match the factors")
            else:
                sg = [sum(fs["covariance"][i][j] * g[j] for j in range(n)) for i in range(n)]
                gsg = sum(g[i] * sg[i] for i in range(n))
                lstar = sol["loss_threshold_clp_m"]
                want_x = [sg[i] * lstar / gsg for i in range(n)]
                for a, b in zip(sol["x_star"], want_x):
                    if not close(a, b, 1e-4, 1e-6):
                        out.append("solution: x_star is not the closed form Sigma g l / (g' Sigma g) of a linear loss")
                        break
                if not close(sol["mahalanobis_distance"], lstar / math.sqrt(gsg), 1e-4, 1e-6):
                    out.append("solution: the distance is not l / sqrt(g' Sigma g), the closed form of a linear loss")
                if not close(sum(gi * xi for gi, xi in zip(g, sol["x_star"])), sol["loss_at_z_star_clp_m"], 1e-4, 1e-3):
                    out.append("solution: the loss at z* is not g'x* for a linear loss")
    gap = abs(sol["loss_at_z_star_clp_m"] - sol["loss_threshold_clp_m"]) / sol["loss_threshold_clp_m"]
    if not close(sol["relative_gap"], gap, 1e-6, 1e-9):
        out.append("solution: relative_gap is not |loss - threshold| / threshold")
    if gap > sol["tolerance"]:
        out.append(f"solution: the loss at z* is not the threshold within the tolerance (gap {gap})")
    for s in o["starts"]:
        if s["converged"] and s["distance"] < sol["mahalanobis_distance"] * (1 - 1e-6):
            out.append(f"starts: {s['start_id']} found a closer point than the solution")
    if not any(s["converged"] for s in o["starts"]):
        out.append("starts: no start converged")
    if o["factor_space"]["factors"] and len(o["loss_model"]["description"]["en"]) == 0:
        out.append("loss_model: the description is empty")
    return out


# ------------------------------------------------------------------------------------------------ the models artifact


def models_violations(doc: dict) -> list[str]:
    f = doc["fit"]
    out: list[str] = []
    for s in f["satellites"]:
        w = s["sample_window"]
        where = f"satellites {s['fed_loan_type']}"
        if w["start"] > w["end"]:
            out.append(f"{where}: the window ends before it starts")
            continue
        nq = q_index(w["end"]) - q_index(w["start"]) + 1
        lag = max([s["ar_order"]] + [r["lag"] for r in s["regressors"]])
        if s["n_obs"] != nq - lag:
            out.append(f"{where}: n_obs {s['n_obs']} is not the quarters of the window {nq} less the largest lag {lag}")
        names = {c["name"] for c in s["coefficients"]}
        want = {"intercept"} | {f"ar_{k}" for k in range(1, s["ar_order"] + 1)} | {f"{r['name']}_lag{r['lag']}" for r in s["regressors"]}
        if names != want:
            out.append(f"{where}: the coefficients {sorted(names)} are not {sorted(want)}")
        for c in s["coefficients"]:
            if (c["expected_sign"] == "positive" and c["estimate"] <= 0) or (c["expected_sign"] == "negative" and c["estimate"] >= 0):
                out.append(f"{where}: coefficient {c['name']} {c['estimate']} has not its expected sign {c['expected_sign']}")
    for m in f["class_mapping"]:
        if len(m["weights"]) != len(m["fed_loan_types"]) or not close(sum(m["weights"]), 1.0, 1e-9, 1e-9):
            out.append(f"class_mapping {m['banco_andino_class']}: the weights do not sum to 1")
    fs = f["factor_space"]
    if fs["window"]["start"] > fs["window"]["end"]:
        out.append("factor_space: the window ends before it starts")
    out += cov_problems(fs["covariance"], [x["sd"] for x in fs["factors"]], "factor_space")
    a = f["bank_anchors"]
    if not close(sum(a["rwa_mix"].values()), 1.0, 1e-9, 1e-9):
        out.append("bank_anchors: the RWA mix does not sum to 1")
    b = a["rwa_basis"]
    if not close(b["rwa_total_clp_m"], b["tier1_proxy_clp_m"] / b["cet1_ratio_anchor"], 1e-6, 1e-6):
        out.append("bank_anchors: the RWA is not the Tier 1 proxy over the CET1 ratio anchor")
    exps = a["loan_exposures"]
    tot = sum(e["exposure_clp_m"] for e in exps)
    if not close(sum(e["share"] for e in exps), 1.0, 1e-9, 1e-9):
        out.append("bank_anchors: the loan shares do not sum to 1")
    for e in exps:
        if tot and not close(e["share"], e["exposure_clp_m"] / tot, 1e-6, 1e-9):
            out.append(f"bank_anchors: the share of {e['banco_andino_class']} is not its exposure over the total")
    n = f["named_parameters"]
    nu = n["nu_set"]["values"]
    if sorted(nu) != nu or len(set(nu)) != len(nu) or any(v <= 2 for v in nu):
        out.append("named_parameters: the nu set is not ascending, distinct and above 2")
    base, stress = n["correlation_matrix_base"], n["correlation_matrix_stress"]
    out += matrix_problems(base["matrix"], "correlation_matrix_base") + matrix_problems(stress["matrix"], "correlation_matrix_stress")
    order = base["order"]
    mi, ci = order.index("market"), order.index("credit")
    for i in range(4):
        for j in range(4):
            want = 0.8 if {i, j} == {mi, ci} else base["matrix"][i][j]
            if not close(stress["matrix"][i][j], want, 1e-12, 1e-12):
                out.append("named_parameters: the stressed matrix is not the base with market-credit raised to 0.8")
    for k in ("ppnr_fee_ratio", "ppnr_cost_ratio"):
        if not 0 <= n[k]["value"] <= 1:
            out.append(f"named_parameters: {k} is outside [0, 1]")
    for k in ("operational_conversion_rate", "asset_scaling", "market_horizon_scaling"):
        if n[k]["value"] <= 0:
            out.append(f"named_parameters: {k} is not positive")
    if n["c_p2"]["value"] < a["chilean_stack"]["p2r"] - 1e-12:
        out.append("named_parameters: c_P2 is below the Pillar 2 requirement (c_P2 >= c_66 quinquies)")
    if not close(n["market_rwa_share"]["value"], a["rwa_mix"]["market"], 1e-6, 1e-9):
        out.append("named_parameters: market_rwa_share is not the market share of the RWA mix")
    if n["reverse_p2_cet1"]["value"] > a["chilean_stack"]["p2r"] + 1e-12:
        out.append("named_parameters: the CET1 share of Pillar 2 exceeds the Pillar 2 requirement")
    rules = {r["paragraph"] for r in f["capital_engine"]["rules"]}
    for p in EBA_PARAGRAPHS:
        if p not in rules:
            out.append(f"capital_engine: the EBA rule of paragraph {p} is missing")
    for s in f["scenario_sources"]:
        if s["provider"] == "ngfs":
            if [(v["name"], v["unit"]) for v in s["variables"]] != NGFS_VARIABLES:
                out.append("scenario_sources: the NGFS variables are not the four NiGEM names of the record")
            if s["licence_class"] != "derived-only":
                out.append("scenario_sources: NGFS is derived-only")
        elif s["variables"]:
            out.append(f"scenario_sources: {s['scenario_id']} lists NGFS variables")
    if sorted(s["scenario_id"] for s in f["scenario_sources"]) != sorted({"baseline", "eba-2025-adverse", "fed-2026-severely-adverse", "ngfs-delayed-transition"}):
        out.append("scenario_sources: not one source per scenario")
    if sorted(r["method"] for r in f["aggregation"]["ladder"]) != sorted(BAND_METHODS):
        out.append("aggregation: the ladder is not the six band methods")
    return out


def violations(doc: dict) -> list[str]:
    """Every cross-field problem of one C18 document (a variant or the models artifact); empty when it conforms."""
    if "fit" in doc:
        return models_violations(doc)
    kind = doc["outputs"]["kind"]
    return {"scenario": scenario_violations, "aggregation": aggregation_variant_violations, "reverse": reverse_violations}[kind](doc)


# ------------------------------------------------------------------------------------------------ across documents


def _named_eq(a: dict, b: dict) -> bool:
    return a == b


def cross_violations(docs: dict[str, dict]) -> list[str]:
    out: list[str] = []
    models = docs.get("models")
    scen = {k: docs[k] for k in ("baseline", "eba", "fed", "ngfs") if k in docs}
    if models is None:
        return ["the models document is missing"]
    f = models["fit"]
    named, anchors = f["named_parameters"], f["bank_anchors"]
    ref_start = next(iter(scen.values()))["outputs"]["capital_start"] if scen else None
    for k, d in scen.items():
        o = d["outputs"]
        oi = o["internal_capital_target"]
        for key in ("c_p2", "c_d"):
            if oi[key] != named[key]:
                out.append(f"{k}: internal_capital_target.{key} differs from the models named parameter")
        if o["headline_cet1"]["ppnr"]["fee_ratio"] != named["ppnr_fee_ratio"] or o["headline_cet1"]["ppnr"]["cost_ratio"] != named["ppnr_cost_ratio"]:
            out.append(f"{k}: the PPNR ratios differ from the models named parameters")
        agg = o["aggregation"]
        if agg["correlation"] != named["correlation_matrix_base"]:
            out.append(f"{k}: the correlation matrix differs from the models named parameter")
        if agg["nu_set"] != named["nu_set"]:
            out.append(f"{k}: the nu set differs from the models named parameter")
        scal = {p["name"]: p for m in agg["marginals"] for p in m["scaling"]["parameters"]}
        for key in ("asset_scaling", "operational_conversion_rate", "market_rwa_share", "market_horizon_scaling"):
            if key not in scal:
                out.append(f"{k}: the scaling parameter {key} is not recorded on a marginal")
            elif scal[key] != named[key]:
                out.append(f"{k}: the scaling parameter {key} differs from the models named parameter")
        if o["capital_start"] != ref_start:
            out.append(f"{k}: capital_start differs from the other scenario documents")
        if not close(o["capital_start"]["rwa_clp_m"], anchors["rwa_basis"]["rwa_total_clp_m"]):
            out.append(f"{k}: the RWA is not the models anchor")
        mix = anchors["rwa_mix"]
        for risk in ("credit", "market", "operational"):
            if not close(o["capital_start"]["rwa_by_risk"][risk], o["capital_start"]["rwa_clp_m"] * mix[risk], 1e-5, 1e-3):
                out.append(f"{k}: the RWA of {risk} is not the RWA times the anchor mix")
        st = f["bank_anchors"]["chilean_stack"]
        if oi["c_dsib"] != st["c_dsib"] or oi["c_ccyb"] != st["c_ccyb"]:
            out.append(f"{k}: the internal target buffers differ from the models anchors")
        rows = {r["row_id"]: r for r in o["annex3"]["rows"]}
        a72 = annex_value(rows, "7.2", "a")
        if a72 is not None and not close(a72, st["p2r"], 1e-9, 1e-12):
            out.append(f"{k}: Annex 3 row 7.2 is not the Pillar 2 requirement of the anchors")
        sources = {s["scenario_id"]: s for s in f["scenario_sources"]}
        src = sources.get(o["scenario"]["scenario_id"])
        if src is None or src["document"] != o["scenario"]["source_document"] or src["vintage_date"] != o["scenario"]["vintage_date"] or src["provider"] != o["scenario"]["provider"]:
            out.append(f"{k}: the scenario source differs from the models scenario_sources")
        for p in o["backcast"]["per_loan_type"]:
            sat = next(s for s in f["satellites"] if s["fed_loan_type"] == p["fed_loan_type"])
            if p["fit_window"] != sat["sample_window"]:
                out.append(f"{k}: the back-cast fit window of {p['fed_loan_type']} is not the satellite sample window of the models")
        for c in o["satellites"]["banco_andino_classes"]:
            cm = next(m for m in f["class_mapping"] if m["banco_andino_class"] == c["banco_andino_class"])
            ex = next(e for e in anchors["loan_exposures"] if e["banco_andino_class"] == c["banco_andino_class"])
            if c["maps_from"] != cm["fed_loan_types"] or c["weights"] != cm["weights"]:
                out.append(f"{k}: class {c['banco_andino_class']} mapping differs from the models")
            if not close(c["exposure_clp_m"], ex["exposure_clp_m"]):
                out.append(f"{k}: class {c['banco_andino_class']} exposure differs from the models anchor")
        for p in o["satellites"]["fed_loan_types"]:
            sat = next(s for s in f["satellites"] if s["fed_loan_type"] == p["fed_loan_type"])
            if p["model_id"] != sat["model_id"] or p["link"] != sat["link"]:
                out.append(f"{k}: the projection of {p['fed_loan_type']} names another model or link than the models")
        # every regressor a satellite reads has a scenario path that maps to it
        regs = {r["name"] for s in f["satellites"] for r in s["regressors"]}
        mapped = {p["maps_to_regressor"] for p in o["scenario"]["paths"]}
        for name in sorted(regs - mapped):
            out.append(f"{k}: no path of the scenario maps to {name}, which a satellite reads")
    keys = list(scen)
    for k in keys[1:]:
        a, b = scen[keys[0]]["outputs"], scen[k]["outputs"]
        if a["backcast"] != b["backcast"]:
            out.append(f"{k}: the back-cast differs from {keys[0]}: it does not depend on the scenario")
        if a["internal_capital_target"] != b["internal_capital_target"]:
            out.append(f"{k}: the internal capital target differs from {keys[0]}")
        base_a = next(c for c in a["capital_plan"]["cases"] if c["case"] == "base")
        base_b = next(c for c in b["capital_plan"]["cases"] if c["case"] == "base")
        if base_a != base_b:
            out.append(f"{k}: the base case of the capital plan differs from {keys[0]}")
    if "baseline" in docs and "aggregation" in docs:
        bm = docs["baseline"]["outputs"]["aggregation"]["marginals"]
        am = docs["aggregation"]["outputs"]["aggregation"]["marginals"]
        if bm != am:
            out.append("aggregation: the marginals differ from the baseline variant (the t-copula variant runs the baseline scenario)")
        if docs["aggregation"]["outputs"]["aggregation"]["correlation"] != named["correlation_matrix_base"]:
            out.append("aggregation: the base correlation differs from the models named parameter")
        if docs["aggregation"]["outputs"]["correlation_stress"]["aggregation"]["correlation"] != named["correlation_matrix_stress"]:
            out.append("aggregation: the stressed correlation differs from the models named parameter")
        if docs["aggregation"]["outputs"]["aggregation"]["nu_set"] != named["nu_set"]:
            out.append("aggregation: the nu set differs from the models named parameter")
    if "reverse" in docs:
        o = docs["reverse"]["outputs"]
        if ref_start is not None and (not close(o["failure_point"]["rwa_clp_m"], ref_start["rwa_clp_m"]) or not close(o["failure_point"]["cet1_ratio_start"], ref_start["cet1_ratio"], 1e-9, 1e-12)):
            out.append("reverse: the RWA or the CET1 ratio at the start differ from the scenario documents")
        st = o["failure_point"]["stack"]
        a_st = anchors["chilean_stack"]
        if st["c_ccyb"] != a_st["c_ccyb"] or st["c_dsib"] != a_st["c_dsib"] or st["p2_cet1"] != named["reverse_p2_cet1"]:
            out.append("reverse: the stack differs from the models anchors and named parameter")
        if o["factor_space"]["window"] != f["factor_space"]["window"] or o["factor_space"]["covariance"] != f["factor_space"]["covariance"]:
            out.append("reverse: the factor window or covariance differs from the models")
        if [(x["id"], x["sd"]) for x in o["factor_space"]["factors"]] != [(x["id"], x["sd"]) for x in f["factor_space"]["factors"]]:
            out.append("reverse: the factors differ from the models")
    return out
