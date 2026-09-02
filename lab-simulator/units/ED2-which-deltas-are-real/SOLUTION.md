# ED2 · solution

**Rows 1 and 3.** Their intervals exclude zero. Rows 2 and 4 straddle it.

Row 4 is the trap: +0.0048 looks like a small win and the interval (−0.0024, +0.0145) says it is
not a win at all. Row 3 is the other trap: a *negative* delta with an interval entirely below
zero is every bit as real as row 1 — it is a regression, and it is the one this repository ships,
because the gated metric (full-chain recall) is identical across those arms and nDCG is not gated.

"Inside the noise band" is not a small difference. It is not a difference, and shipping
complexity to buy one is how a system accretes.
