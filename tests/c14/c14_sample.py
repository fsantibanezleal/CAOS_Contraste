"""A call report of round numbers (thousands of USD) that satisfies the identities the slotting relies on, for the unit tests."""
from __future__ import annotations

REPORT_DATE = "2021-12-31"

VALUES = {
    "CERT": 24735, "REPDTE": "20211231", "NAME": "SAMPLE BANK", "ASSET": 1000.0, "LIAB": 900.0, "EQ": 100.0, "RBCT1J": 80.0,
    "DEP": 850.0, "DEPDOM": 750.0, "DEPFOR": 100.0, "DEPNIDOM": 400.0, "DEPIDOM": 350.0, "DEPNIFOR": 50.0, "DEPIFOR": 50.0,
    "DEPINS": 30.0, "DEPUNA": 700.0, "DEPSMAMT": 40.0, "DEPSMB": 900.0, "DEPLGAMT": 810.0, "DEPLGB": 100.0,
    "NTRTIME": 20.0, "CD3LES": 5.0, "CD3T12": 5.0, "CD1T3": 5.0, "CDOV3": 2.0, "CD3LESS": 1.0, "CD3T12S": 1.0, "CD1T3S": 1.0, "CDOV3S": 0.0,
    "CHBAL": 100.0, "FREPO": 20.0, "FREPP": 5.0, "SC": 300.0, "SCRDEBT": 300.0, "SCAF": 100.0, "SCAA": 100.0, "SCHA": 200.0, "SCHF": 190.0,
    "SCNM3LES": 30.0, "SCNM3T12": 20.0, "SCNM1T3": 30.0, "SCNM3T5": 20.0, "SCNM5T15": 30.0, "SCNMOV15": 10.0,
    "SCPT3LES": 0.0, "SCPT3T12": 0.0, "SCPT1T3": 0.0, "SCPT3T5": 0.0, "SCPT5T15": 60.0, "SCPTOV15": 80.0, "SCO3YLES": 10.0, "SCOOV3Y": 10.0,
    "LNLSGR": 500.0, "LNLSNET": 495.0, "LNATRES": 5.0,
    "LNRS3LES": 10.0, "LNRS3T12": 10.0, "LNRS1T3": 10.0, "LNRS3T5": 10.0, "LNRS5T15": 20.0, "LNRSOV15": 40.0,
    "LNOT3LES": 250.0, "LNOT3T12": 50.0, "LNOT1T3": 40.0, "LNOT3T5": 20.0, "LNOT5T15": 20.0, "LNOTOV15": 10.0,
    "OTHBFHLB": 20.0, "OTHBFH1L": 10.0, "OTBFH1T3": 5.0, "OTBFH3T5": 3.0, "OTBFHOV5": 2.0, "OTHBRF": 25.0, "OTBOT1L": 5.0,
    "OTBOT1T3": 0.0, "OTBOT3T5": 0.0, "OTBOTOV5": 0.0, "SUBND": 0.0,
    "INTINC": 30.0, "EINTEXP": 5.0, "NIM": 25.0, "EDEP": 4.0, "ISC": 6.0, "ILNDOM": 20.0, "ICHBAL": 1.0, "IFREPO": 0.0, "EFREPP": 0.0,
}


def report():
    from pipeline.cases.c14.fdic import Report

    return Report(REPORT_DATE, dict(VALUES))
