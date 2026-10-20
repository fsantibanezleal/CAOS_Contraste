"""The ORE 1.8.17.0 run of C12: the XML inputs (written, and committed under ``cases/c12/ore_inputs/``), the run, and the parse of
its exposure outputs (decision S2).

ORE is the reference engine the Python exposure is reconciled against. It runs natively from the ``open-source-risk-engine``
wheel (decision D4); the inputs state the model the Python run uses: an LGM with Hull-White reversion ``a`` and volatility
``sigma`` (no calibration), fitted to the zero curve of the curve date, ``MersenneTwisterAntithetic`` paths, exact discretisation.

Time. ORE measures time with the day counter of its zero curve. The case uses the 30/360 axis (months over 12, calendar days
over 360), so ORE's conventions are 30/360 throughout and its valuation date is the first of a month: every monthly grid date,
swap period and tenor then has the year fraction of the case, and the close-out offset of 14 or 28 calendar days is 14/360 or
28/360 at every grid date. The only date where a 28 day offset would cross a short month is the February of the first year,
so the valuation date is placed in a year whose next February is a leap year. The curve is a curve in relative time; the
valuation date is a calendar of convenience, stated here and in the case page.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import book

ORE_VERSION = "1.8.17.0"
INPUT_DIR = Path(__file__).resolve().parent / "ore_inputs"
CURVE_ID = "C12_ZERO"
INDEX = "USD-C12IBOR-6M"
NETTING_SET = "NS-1"
SCENARIO_TENORS = ",".join(f"{m}M" for m in range(1, 133))
MPOR_DAYS = {10: "2W", 20: "4W"}
SWAPTION_TENORS = "1Y,5Y,10Y"
SWAPTION_VOL = 0.01
TENOR_NAME = {1 / 12: "1M", 2 / 12: "2M", 0.25: "3M", 4 / 12: "4M", 0.5: "6M", 1.0: "1Y", 2.0: "2Y", 3.0: "3Y", 5.0: "5Y", 7.0: "7Y",
              10.0: "10Y", 20.0: "20Y", 30.0: "30Y"}


def asof_for(curve_month: int) -> str:
    """The valuation date ORE uses: the first of the curve's month, in a year such that the February that falls within the next
    twelve months, 12 months included, is a leap February."""
    year = 2028 if curve_month == 1 else 2027
    return f"{year}-{curve_month:02d}-01"


def _tenor(t: float) -> str:
    for k, v in TENOR_NAME.items():
        if abs(k - t) < 1e-5:
            return v
    raise ValueError(f"no ORE tenor name for {t} years")


def _grid_tenors(report: np.ndarray) -> str:
    months = np.round(report * 12).astype(int)
    if np.max(np.abs(months / 12.0 - report)) > 1e-9:
        raise ValueError("the report grid is not on month ends")
    return ",".join(f"{m}M" for m in months)


def _xml(root_tag: str, body: str) -> str:
    return f'<?xml version="1.0"?>\n<{root_tag}>\n{body}</{root_tag}>\n'


def conventions() -> str:
    return _xml("Conventions", f"""  <Zero>
    <Id>USD-ZERO-C12</Id>
    <TenorBased>true</TenorBased>
    <DayCounter>T360</DayCounter>
    <Compounding>Continuous</Compounding>
    <TenorCalendar>NullCalendar</TenorCalendar>
    <SpotLag>0</SpotLag>
    <SpotCalendar>NullCalendar</SpotCalendar>
    <RollConvention>Unadjusted</RollConvention>
    <EOM>false</EOM>
  </Zero>
  <IborIndex>
    <Id>{INDEX}</Id>
    <FixingCalendar>NullCalendar</FixingCalendar>
    <DayCounter>30/360</DayCounter>
    <SettlementDays>1</SettlementDays>
    <BusinessDayConvention>U</BusinessDayConvention>
    <EndOfMonth>false</EndOfMonth>
  </IborIndex>
  <Swap>
    <Id>USD-C12-SWAP-CONVENTIONS</Id>
    <FixedCalendar>NullCalendar</FixedCalendar>
    <FixedFrequency>Semiannual</FixedFrequency>
    <FixedConvention>U</FixedConvention>
    <FixedDayCounter>30/360</FixedDayCounter>
    <Index>{INDEX}</Index>
  </Swap>
  <SwapIndex>
    <Id>USD-CMS-1Y</Id>
    <Conventions>USD-C12-SWAP-CONVENTIONS</Conventions>
  </SwapIndex>
  <SwapIndex>
    <Id>USD-CMS-30Y</Id>
    <Conventions>USD-C12-SWAP-CONVENTIONS</Conventions>
  </SwapIndex>
""")


def curveconfig(tenors: np.ndarray) -> str:
    quotes = "\n".join(f"            <Quote>ZERO/RATE/USD/{CURVE_ID}/T360/{_tenor(t)}</Quote>" for t in tenors)
    return _xml("CurveConfiguration", f"""  <YieldCurves>
    <YieldCurve>
      <CurveId>{CURVE_ID}</CurveId>
      <CurveDescription>USD zero curve of C12 (single curve: discounting and forecasting)</CurveDescription>
      <Currency>USD</Currency>
      <DiscountCurve/>
      <Segments>
        <Direct>
          <Type>Zero</Type>
          <Quotes>
{quotes}
          </Quotes>
          <Conventions>USD-ZERO-C12</Conventions>
        </Direct>
      </Segments>
      <InterpolationVariable>Zero</InterpolationVariable>
      <InterpolationMethod>Linear</InterpolationMethod>
      <YieldCurveDayCounter>T360</YieldCurveDayCounter>
      <Tolerance>1.0e-12</Tolerance>
      <Extrapolation>true</Extrapolation>
    </YieldCurve>
  </YieldCurves>
  <SwaptionVolatilities>
    <SwaptionVolatility>
      <CurveId>USD_SW_N</CurveId>
      <CurveDescription>USD normal swaption volatilities (flat; the LGM is not calibrated, the surface only completes the market)</CurveDescription>
      <Dimension>ATM</Dimension>
      <VolatilityType>Normal</VolatilityType>
      <Extrapolation>Flat</Extrapolation>
      <DayCounter>A365</DayCounter>
      <Calendar>NullCalendar</Calendar>
      <BusinessDayConvention>Following</BusinessDayConvention>
      <OptionTenors>{SWAPTION_TENORS}</OptionTenors>
      <SwapTenors>{SWAPTION_TENORS}</SwapTenors>
      <ShortSwapIndexBase>USD-CMS-1Y</ShortSwapIndexBase>
      <SwapIndexBase>USD-CMS-30Y</SwapIndexBase>
    </SwaptionVolatility>
  </SwaptionVolatilities>
""")


def market(asof: str, tenors: np.ndarray, zeros: np.ndarray) -> str:
    d = asof.replace("-", "")
    zero = "".join(f"{d} ZERO/RATE/USD/{CURVE_ID}/T360/{_tenor(t)} {float(z)!r}\n" for t, z in zip(tenors, zeros, strict=True))
    vols = "".join(f"{d} SWAPTION/RATE_NVOL/USD/{e}/{s}/ATM {SWAPTION_VOL!r}\n" for e in SWAPTION_TENORS.split(",")
                   for s in SWAPTION_TENORS.split(","))
    return zero + vols


def first_fixing(tenors: np.ndarray, zeros: np.ndarray) -> float:
    """The simple 6 month rate of the curve at the valuation date, with the 30/360 accrual of 0.5."""
    from riskvalidation.ccr import hw1f

    p0, _ = hw1f.curve_functions(zeros, tenors)
    return float((1.0 / float(p0(np.array(0.5))) - 1.0) / 0.5)


def fixings(asof: str, tenors: np.ndarray, zeros: np.ndarray) -> str:
    """The fixing of the index at the valuation date, the simple 6 month rate of the curve (30/360 accrual of 0.5): ORE reads the
    coupon of a period already begun from the fixing, and a missing fixing is silently forecast from the scenario curve."""
    from riskvalidation.ccr import hw1f

    p0, _ = hw1f.curve_functions(zeros, tenors)
    p = float(p0(np.array(0.5)))
    return f"{asof} {INDEX} {(1.0 / p - 1.0) / 0.5!r}\n"


def todaysmarket() -> str:
    return _xml("TodaysMarket", f"""  <Configuration id="default">
    <DiscountingCurvesId>default</DiscountingCurvesId>
    <IndexForwardingCurvesId>default</IndexForwardingCurvesId>
    <YieldCurvesId>default</YieldCurvesId>
    <SwapIndexCurvesId>default</SwapIndexCurvesId>
    <SwaptionVolatilitiesId>default</SwaptionVolatilitiesId>
  </Configuration>
  <DiscountingCurves id="default">
    <DiscountingCurve currency="USD">Yield/USD/{CURVE_ID}</DiscountingCurve>
  </DiscountingCurves>
  <IndexForwardingCurves id="default">
    <Index name="{INDEX}">Yield/USD/{CURVE_ID}</Index>
  </IndexForwardingCurves>
  <YieldCurves id="default">
    <YieldCurve name="{CURVE_ID}">Yield/USD/{CURVE_ID}</YieldCurve>
  </YieldCurves>
  <SwapIndexCurves id="default">
    <SwapIndex name="USD-CMS-1Y">
      <Discounting>{INDEX}</Discounting>
    </SwapIndex>
    <SwapIndex name="USD-CMS-30Y">
      <Discounting>{INDEX}</Discounting>
    </SwapIndex>
  </SwapIndexCurves>
  <SwaptionVolatilities id="default">
    <SwaptionVolatility currency="USD">SwaptionVolatility/USD/USD_SW_N</SwaptionVolatility>
  </SwaptionVolatilities>
""")


def pricingengine() -> str:
    return _xml("PricingEngines", """  <Product type="Swap">
    <Model>DiscountedCashflows</Model>
    <ModelParameters/>
    <Engine>DiscountingSwapEngine</Engine>
    <EngineParameters/>
  </Product>
""")


def _rules(start: str, end: str) -> str:
    return f"""            <Rules>
              <StartDate>{start}</StartDate>
              <EndDate>{end}</EndDate>
              <Tenor>6M</Tenor>
              <Calendar>NullCalendar</Calendar>
              <Convention>U</Convention>
              <TermConvention>U</TermConvention>
              <Rule>Forward</Rule>
              <EndOfMonth/>
              <FirstDate/>
              <LastDate/>
            </Rules>"""


def _fixed_leg(payer: bool, notional: float, rate: float, start: str, end: str) -> str:
    return f"""      <LegData>
        <LegType>Fixed</LegType>
        <Payer>{str(payer).lower()}</Payer>
        <Currency>USD</Currency>
        <Notionals>
          <Notional>{notional:.6f}</Notional>
        </Notionals>
        <DayCounter>30/360</DayCounter>
        <PaymentConvention>U</PaymentConvention>
        <FixedLegData>
          <Rates>
            <Rate>{rate!r}</Rate>
          </Rates>
        </FixedLegData>
        <ScheduleData>
{_rules(start, end)}
        </ScheduleData>
      </LegData>
"""


def _floating_leg(payer: bool, notional: float, start: str, end: str) -> str:
    return f"""      <LegData>
        <LegType>Floating</LegType>
        <Payer>{str(payer).lower()}</Payer>
        <Currency>USD</Currency>
        <Notionals>
          <Notional>{notional:.6f}</Notional>
        </Notionals>
        <DayCounter>30/360</DayCounter>
        <PaymentConvention>U</PaymentConvention>
        <FloatingLegData>
          <Index>{INDEX}</Index>
          <Spreads>
            <Spread>0.000000</Spread>
          </Spreads>
          <IsInArrears>false</IsInArrears>
          <FixingDays>1</FixingDays>
        </FloatingLegData>
        <ScheduleData>
{_rules(start, end)}
        </ScheduleData>
      </LegData>
"""


def _month_date(asof: str, months: int) -> str:
    y, m, _ = (int(x) for x in asof.split("-"))
    idx = y * 12 + (m - 1) + months
    return f"{idx // 12}{idx % 12 + 1:02d}01"


def portfolio(trades: list[book.Trade], asof: str, first_fixing: float) -> str:
    """The swaps as ORE trades. A swap of the case has its first floating coupon fixed at origination (the rate of the curve of
    the valuation date). ORE does not read the fixing of the valuation date inside a simulation (it forecasts it from the
    scenario curve of the next grid date), so the first floating period is written as a one-period fixed leg at that rate and the
    floating leg starts at the first reset after it: the same cash flows, with the fixing known."""
    start = _month_date(asof, 0)
    out = []
    for t in trades:
        months = int(round(t.maturity * 12))
        end = _month_date(asof, months)
        pay_fixed = t.side == "payer"
        legs = _fixed_leg(pay_fixed, t.notional, t.fixed_rate, start, end)
        legs += _fixed_leg(not pay_fixed, t.notional, first_fixing, start, _month_date(asof, 6))
        if months > 6:
            legs += _floating_leg(not pay_fixed, t.notional, _month_date(asof, 6), end)
        out.append(f"""  <Trade id="{t.trade_id}">
    <TradeType>Swap</TradeType>
    <Envelope>
      <CounterParty>CPTY-1</CounterParty>
      <NettingSetId>{NETTING_SET}</NettingSetId>
      <AdditionalFields/>
    </Envelope>
    <SwapData>
{legs}    </SwapData>
  </Trade>
""")
    return _xml("Portfolio", "".join(out))


def netting(mpor_business_days: int | None, im: bool, mta: float) -> str:
    csa = mpor_business_days is not None
    if csa:
        body = f"""      <Bilateral>Bilateral</Bilateral>
      <CSACurrency>USD</CSACurrency>
      <Index>{INDEX}</Index>
      <ThresholdPay>{book.CSA['threshold']:.0f}</ThresholdPay>
      <ThresholdReceive>{book.CSA['threshold']:.0f}</ThresholdReceive>
      <MinimumTransferAmountPay>{mta:.0f}</MinimumTransferAmountPay>
      <MinimumTransferAmountReceive>{mta:.0f}</MinimumTransferAmountReceive>
      <IndependentAmount>
        <IndependentAmountHeld>{book.CSA['independent_amount']:.0f}</IndependentAmountHeld>
        <IndependentAmountType>FIXED</IndependentAmountType>
      </IndependentAmount>
      <MarginingFrequency>
        <CallFrequency>1D</CallFrequency>
        <PostFrequency>1D</PostFrequency>
      </MarginingFrequency>
      <MarginPeriodOfRisk>{MPOR_DAYS[mpor_business_days]}</MarginPeriodOfRisk>
      <CollateralCompoundingSpreadReceive>0.0</CollateralCompoundingSpreadReceive>
      <CollateralCompoundingSpreadPay>0.0</CollateralCompoundingSpreadPay>
      <EligibleCollaterals>
        <Currencies>
          <Currency>USD</Currency>
        </Currencies>
      </EligibleCollaterals>
"""
        if im:
            body += "      <ApplyInitialMargin>true</ApplyInitialMargin>\n"
    else:
        body = f"""      <Bilateral>Bilateral</Bilateral>
      <CSACurrency>USD</CSACurrency>
      <Index>{INDEX}</Index>
      <ThresholdPay>0</ThresholdPay>
      <ThresholdReceive>0</ThresholdReceive>
      <MinimumTransferAmountPay>0</MinimumTransferAmountPay>
      <MinimumTransferAmountReceive>0</MinimumTransferAmountReceive>
      <IndependentAmount>
        <IndependentAmountHeld>0</IndependentAmountHeld>
        <IndependentAmountType>FIXED</IndependentAmountType>
      </IndependentAmount>
      <MarginingFrequency>
        <CallFrequency>1D</CallFrequency>
        <PostFrequency>1D</PostFrequency>
      </MarginingFrequency>
      <MarginPeriodOfRisk>0W</MarginPeriodOfRisk>
      <CollateralCompoundingSpreadReceive>0.0</CollateralCompoundingSpreadReceive>
      <CollateralCompoundingSpreadPay>0.0</CollateralCompoundingSpreadPay>
      <EligibleCollaterals>
        <Currencies>
          <Currency>USD</Currency>
        </Currencies>
      </EligibleCollaterals>
"""
    return _xml("NettingSetDefinitions", f"""  <NettingSet>
    <NettingSetId>{NETTING_SET}</NettingSetId>
    <ActiveCSAFlag>{str(csa).lower()}</ActiveCSAFlag>
    <CSADetails>
{body}    </CSADetails>
  </NettingSet>
""")


def simulation(report: np.ndarray, a: float, sigma: float, samples: int, seed: int, mpor_business_days: int | None = None) -> str:
    closeout = (f"    <CloseOutLag>{MPOR_DAYS[mpor_business_days]}</CloseOutLag>\n    <MporMode>StickyDate</MporMode>\n"
                if mpor_business_days is not None else "")
    return _xml("Simulation", f"""  <Parameters>
    <Discretization>Exact</Discretization>
    <Grid>{_grid_tenors(report)}</Grid>
    <Calendar>NullCalendar</Calendar>
    <Sequence>MersenneTwisterAntithetic</Sequence>
    <Scenario>Simple</Scenario>
    <Seed>{seed}</Seed>
    <Samples>{samples}</Samples>
    <Ordering>Steps</Ordering>
    <DirectionIntegers>JoeKuoD7</DirectionIntegers>
{closeout}  </Parameters>
  <CrossAssetModel>
    <DomesticCcy>USD</DomesticCcy>
    <Currencies>
      <Currency>USD</Currency>
    </Currencies>
    <BootstrapTolerance>0.0001</BootstrapTolerance>
    <InterestRateModels>
      <LGM ccy="default">
        <CalibrationType>None</CalibrationType>
        <Volatility>
          <Calibrate>N</Calibrate>
          <VolatilityType>HullWhite</VolatilityType>
          <ParamType>Constant</ParamType>
          <TimeGrid/>
          <InitialValue>{sigma!r}</InitialValue>
        </Volatility>
        <Reversion>
          <Calibrate>N</Calibrate>
          <ReversionType>HullWhite</ReversionType>
          <ParamType>Constant</ParamType>
          <TimeGrid/>
          <InitialValue>{a!r}</InitialValue>
        </Reversion>
        <ParameterTransformation>
          <ShiftHorizon>0.0</ShiftHorizon>
          <Scaling>1.0</Scaling>
        </ParameterTransformation>
      </LGM>
    </InterestRateModels>
    <InstantaneousCorrelations/>
  </CrossAssetModel>
  <Market>
    <BaseCurrency>USD</BaseCurrency>
    <Currencies>
      <Currency>USD</Currency>
    </Currencies>
    <YieldCurves>
      <Configuration>
        <Tenors>{SCENARIO_TENORS}</Tenors>
        <Interpolation>LogLinear</Interpolation>
        <Extrapolation>Y</Extrapolation>
      </Configuration>
    </YieldCurves>
    <Indices>
      <Index>{INDEX}</Index>
    </Indices>
    <SwapIndices>
      <SwapIndex>
        <Name>USD-CMS-1Y</Name>
        <DiscountingIndex>{INDEX}</DiscountingIndex>
      </SwapIndex>
      <SwapIndex>
        <Name>USD-CMS-30Y</Name>
        <DiscountingIndex>{INDEX}</DiscountingIndex>
      </SwapIndex>
    </SwapIndices>
    <DefaultCurves>
      <SimulateSurvivalProbabilities>false</SimulateSurvivalProbabilities>
      <Names/>
      <Tenors>1Y</Tenors>
    </DefaultCurves>
    <SwaptionVolatilities>
      <Simulate>false</Simulate>
      <ReactionToTimeDecay>ForwardVariance</ReactionToTimeDecay>
      <Currencies>
        <Currency>USD</Currency>
      </Currencies>
      <Expiries>{SWAPTION_TENORS}</Expiries>
      <Terms>{SWAPTION_TENORS}</Terms>
    </SwaptionVolatilities>
    <AggregationScenarioDataCurrencies>
      <Currency>USD</Currency>
    </AggregationScenarioDataCurrencies>
    <AggregationScenarioDataIndices>
      <Index>{INDEX}</Index>
    </AggregationScenarioDataIndices>
  </Market>
""")


def ore_xml(asof: str, im: bool, mpor_business_days: int | None) -> str:
    dim = ""
    if im:
        dim = """
      <Parameter name="dim">Y</Parameter>
      <Parameter name="mva">N</Parameter>
      <Parameter name="dimQuantile">0.99</Parameter>
      <Parameter name="dimModel">Regression</Parameter>
      <Parameter name="dimScaling">1.0</Parameter>
      <Parameter name="dimRegressionOrder">2</Parameter>
      <Parameter name="dimOutputNettingSet">NS-1</Parameter>
      <Parameter name="dimEvolutionFile">dim_evolution.csv</Parameter>"""
    return f"""<?xml version="1.0"?>
<ORE>
  <Setup>
    <Parameter name="asofDate">{asof}</Parameter>
    <Parameter name="inputPath">.</Parameter>
    <Parameter name="outputPath">output</Parameter>
    <Parameter name="logFile">log.txt</Parameter>
    <Parameter name="logMask">31</Parameter>
    <Parameter name="marketDataFile">market.txt</Parameter>
    <Parameter name="fixingDataFile">fixings.txt</Parameter>
    <Parameter name="implyTodaysFixings">N</Parameter>
    <Parameter name="curveConfigFile">curveconfig.xml</Parameter>
    <Parameter name="conventionsFile">conventions.xml</Parameter>
    <Parameter name="marketConfigFile">todaysmarket.xml</Parameter>
    <Parameter name="pricingEnginesFile">pricingengine.xml</Parameter>
    <Parameter name="portfolioFile">portfolio.xml</Parameter>
    <Parameter name="observationModel">None</Parameter>
    <Parameter name="continueOnError">false</Parameter>
  </Setup>
  <Markets>
    <Parameter name="lgmcalibration">default</Parameter>
    <Parameter name="fxcalibration">default</Parameter>
    <Parameter name="eqcalibration">default</Parameter>
    <Parameter name="pricing">default</Parameter>
    <Parameter name="simulation">default</Parameter>
  </Markets>
  <Analytics>
    <Analytic type="npv">
      <Parameter name="active">Y</Parameter>
      <Parameter name="baseCurrency">USD</Parameter>
      <Parameter name="outputFileName">npv.csv</Parameter>
    </Analytic>
    <Analytic type="curves">
      <Parameter name="active">Y</Parameter>
      <Parameter name="configuration">default</Parameter>
      <Parameter name="grid">132,1M</Parameter>
      <Parameter name="outputFileName">curves.csv</Parameter>
    </Analytic>
    <Analytic type="simulation">
      <Parameter name="active">Y</Parameter>
      <Parameter name="simulationConfigFile">simulation.xml</Parameter>
      <Parameter name="pricingEnginesFile">pricingengine.xml</Parameter>
      <Parameter name="baseCurrency">USD</Parameter>
      <Parameter name="observationModel">Disable</Parameter>
      <Parameter name="cubeFile">cube.csv.gz</Parameter>
      <Parameter name="aggregationScenarioDataFileName">scenariodata.csv.gz</Parameter>
    </Analytic>
    <Analytic type="xva">
      <Parameter name="active">Y</Parameter>
      <Parameter name="useXvaRunner">N</Parameter>
      <Parameter name="csaFile">netting.xml</Parameter>
      <Parameter name="cubeFile">cube.csv.gz</Parameter>
      <Parameter name="scenarioFile">scenariodata.csv.gz</Parameter>
      <Parameter name="baseCurrency">USD</Parameter>
      <Parameter name="exposureProfiles">Y</Parameter>
      <Parameter name="exposureProfilesByTrade">N</Parameter>
      <Parameter name="cva">N</Parameter>
      <Parameter name="rawCubeOutputFile">rawcube.csv</Parameter>
      <Parameter name="netCubeOutputFile">netcube.csv</Parameter>{dim}
    </Analytic>
  </Analytics>
</ORE>
"""


@dataclass
class Spec:
    """Everything an ORE run of one variant depends on."""

    name: str
    asof: str
    tenors: np.ndarray
    zeros: np.ndarray
    a: float
    sigma: float
    trades: list[book.Trade]
    mpor_business_days: int | None
    im: bool
    report: np.ndarray
    samples: int
    seed: int
    mta: float = book.CSA["mta"]


def write_inputs(spec: Spec, root: Path) -> dict[str, str]:
    """Write the input files of one run under ``root`` and return ``{file name: sha256}``."""
    root.mkdir(parents=True, exist_ok=True)
    files = {
        "ore.xml": ore_xml(spec.asof, spec.im, spec.mpor_business_days), "market.txt": market(spec.asof, spec.tenors, spec.zeros),
        "fixings.txt": fixings(spec.asof, spec.tenors, spec.zeros), "curveconfig.xml": curveconfig(spec.tenors), "conventions.xml": conventions(),
        "todaysmarket.xml": todaysmarket(), "pricingengine.xml": pricingengine(),
        "portfolio.xml": portfolio(spec.trades, spec.asof, first_fixing(spec.tenors, spec.zeros)), "netting.xml": netting(spec.mpor_business_days, spec.im, spec.mta),
        "simulation.xml": simulation(spec.report, spec.a, spec.sigma, spec.samples, spec.seed, spec.mpor_business_days),
    }
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8", newline="\n")
    return {n: hashlib.sha256(t.encode("utf-8")).hexdigest() for n, t in files.items()}


RUNNER = (
    "import sys\n"
    "from ORE import Parameters, OREApp\n"
    "p = Parameters()\n"
    "p.fromFile(sys.argv[1])\n"
    "app = OREApp(p, False)\n"
    "app.run()\n"
)


def run(root: Path, timeout: float = 3600.0) -> tuple[float, str]:
    """Run ORE on ``root/ore.xml`` in a child process (isolated, the working directory the input folder); return the seconds it
    took and its platform string. A failure raises with the tail of the log."""
    (root / "output").mkdir(exist_ok=True)
    log = root / "run.log"
    t0 = time.perf_counter()
    with open(log, "wb") as fh:
        proc = subprocess.run([sys.executable, "-I", "-c", RUNNER, "ore.xml"], cwd=root, stdout=fh, stderr=subprocess.STDOUT,
                              timeout=timeout, check=False)
    seconds = time.perf_counter() - t0
    if proc.returncode != 0:
        tail = log.read_bytes()[-1500:].decode("utf-8", "replace")
        raise RuntimeError(f"ORE failed in {root} (exit {proc.returncode}): {tail}")
    return seconds, platform_string()


def platform_string() -> str:
    import importlib.metadata as md
    import platform

    return (f"open-source-risk-engine {md.version('open-source-risk-engine')} wheel, CPython {platform.python_version()}, "
            f"{platform.system()} {platform.release()} {platform.machine()}, native (no WSL)")


# ------------------------------------------------------------------------------------------------------- outputs


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    lines[0] = lines[0].lstrip("#")
    return list(csv.DictReader(io.StringIO("\n".join(lines))))


def read_exposures(root: Path) -> dict[str, np.ndarray]:
    """ORE's exposure profile of the netting set on its grid: time, discounted EPE and ENE, the Basel (undiscounted) EE and ENE."""
    rows = read_csv_rows(root / "output" / f"exposure_nettingset_{NETTING_SET}.csv")
    cols = {k: np.array([float(r[k]) for r in rows]) for k in ("Time", "EPE", "ENE", "PFE", "ExpectedCollateral", "BaselEE")}
    return cols


def read_cube(root: Path, name: str = "netcube.csv") -> tuple[np.ndarray, np.ndarray]:
    """(dates, values (samples, dates)) of a cube file: sample 0 is the valuation date."""
    rows: dict[int, dict[int, float]] = {}
    with open(root / "output" / name, encoding="utf-8") as fh:
        next(fh)
        for line in fh:
            parts = line.rstrip("\n").split(",")
            di, sample, val = int(parts[2]), int(parts[4]), float(parts[6])
            rows.setdefault(di, {})[sample] = val
    dates = sorted(rows)
    n = max(max(v) for v in rows.values())
    out = np.zeros((n, len(dates)))
    for j, di in enumerate(dates):
        for s in range(1, n + 1):
            out[s - 1, j] = rows[di].get(s, rows[di].get(0, 0.0))
    return np.array(dates), out


def read_numeraire(root: Path, n_dates: int) -> np.ndarray:
    """(samples, dates) the numeraire of the scenarios (the key of kind 4 of the aggregation scenario data)."""
    with gzip.open(root / "output" / "scenariodata.csv.gz", "rt", encoding="utf-8") as fh:
        head: list[str] = []
        line = fh.readline()
        while line.startswith("#") and "date,sample" not in line:
            head.append(line)
            line = fh.readline()
        keys = [h.strip("# \n").split(",", 1) for h in head if h.startswith("# ") and "," in h and h.strip("# \n")[0].isdigit()]
        num_idx = next(int(i) for i, name in keys if name.strip() == "" and int(i) == max(int(k) for k, _ in keys))
        samples = int([h for h in head if "dimSamples" in h][0].split(":")[1])
        out = np.zeros((samples, n_dates))
        for line in fh:
            d, s, k, v = line.rstrip("\n").split(",")
            if int(k) == num_idx:
                out[int(s), int(d) - 1] = float(v)
    return out
