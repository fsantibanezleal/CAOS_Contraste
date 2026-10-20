# Notebooks, English

The index of the English tree. Topics run from simple to complex; inside a topic the reading order is the notebook number and the
level never goes down. The Spanish counterpart of every notebook is at the same path under [`../es/`](../es/README.md). How to
install and run them is in [`../README.md`](../README.md).

Levels: 1 fundamentals, 2 the method in practice, 3 state of the art, 4 beyond the state of the art.

## Topics

A topic without a level 3 notebook says why on its row. The topics after 01 are listed with the unit that writes them and appear as
links when their folder lands.

| Topic | Needs | Level 3 |
|---|---|---|
| [01-getting-started](01-getting-started/) | none, this is the entry topic | No level 3: the topic teaches the engine's contract and the walk through the committed data, no research dossier holds state-of-the-art work on it, and the state of the art of the tests it calls is presented in topics 02, 03 and 14 |
| 02-credit-scoring (unit U17-B) | topic 01 | planned with its unit |
| 03-ratings-and-calibration (unit U17-C) | topics 01 and 02 | planned with its unit |
| 04-provisions (unit U17-D) | topics 01 and 03 | planned with its unit |
| 05-lgd-and-ead (unit U17-E) | topics 01 and 04 | planned with its unit |
| 06-portfolio-capital (unit U17-F) | topic 03 | planned with its unit |
| 07-market-risk (unit U17-G) | topic 01 | planned with its unit |
| 08-counterparty-and-regulatory-calculators (units U17-L to U17-O) | topics 06 and 07 | planned with its unit |
| 09-irrbb (unit U17-H) | topic 01 | planned with its unit |
| 10-liquidity (unit U17-K) | topics 04 and 09 | planned with its unit |
| 11-operational-risk (unit U17-I) | topic 01 | planned with its unit |
| 12-capital-and-stress (units U17-L to U17-O) | topics 06, 07, 09 and 11 | planned with its unit |
| 13-ml-and-ai-risk (units U17-L to U17-O) | topic 02 | planned with its unit |
| 14-validating-the-validator (unit U17-J) | topics 01 and 03 | planned with its unit |

## Notebooks

| Notebook | Level | What it teaches |
|---|---|---|
| [01-getting-started/01-install-the-engine-and-open-an-artifact.ipynb](01-getting-started/01-install-the-engine-and-open-an-artifact.ipynb) | 1 | install the engine, list its catalogue of validation tests and open the three kinds of committed document (the index, a case manifest and an artifact), with the engine version that baked each one |
| [01-getting-started/02-a-first-testresult-on-a-real-slice.ipynb](01-getting-started/02-a-first-testresult-on-a-real-slice.ipynb) | 1 | one engine test on 50 real cards: the AUC, the Jeffreys test and the Brier score, every field of a `TestResult`, and the same tests on the 9,000 committed cards |
| [01-getting-started/03-policies-and-traffic-lights.ipynb](01-getting-started/03-policies-and-traffic-lights.ipynb) | 1 | how a versioned policy turns a p-value into a light, why a stricter policy changes the colour and not the statistic, and why thresholds are policy and never regulation |
| [01-getting-started/04-a-battery-on-your-own-scored-sample.ipynb](01-getting-started/04-a-battery-on-your-own-scored-sample.ipynb) | 2 | the route of the bring-your-own-model door: contract 1, the master scale, a battery run with `run_suite` that never stops at the first failure, and how to read its table of lights |

## Beyond the state of the art

The SDD claims BS-1 to BS-8 (section Beyond the state of the art). Topic 01 demonstrates none of them; each claim's level 4
notebook comes with its topic's unit.
