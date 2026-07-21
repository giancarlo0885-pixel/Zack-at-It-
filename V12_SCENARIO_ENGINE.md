# GARIBALDI MARKET ORACLE V12 — Scenario Engine

V12 adds probability-weighted bull, base and bear cases to every ranked opportunity and every automatic entry decision.

## What it measures

- Probability of a profitable path
- Expected and median return over a configurable horizon
- Bull, base and bear return/price targets
- 95% value at risk and expected shortfall
- Outcome uncertainty
- Scenario-aware position multiplier
- Scenario veto for weak probability or excessive tail loss

The simulation uses deterministic seeded paths, light fat-tail shocks, volatility clustering, current trend/momentum, market regime, trading costs, quant quality and Market Memory evidence. It is scenario analysis—not a guarantee or a literal prediction.

## Worker behavior

A BUY must now pass the V10 Quant Standard, V11 Market Memory, and V12 Scenario Engine. Position size is multiplied by the scenario sizing factor, so uncertain or high-tail-risk trades receive less capital even when they pass.

## Optional Railway variables

- `SCENARIO_PATHS=2500`
- `SCENARIO_MIN_PROBABILITY=0.52`
- `SCENARIO_MAX_TAIL_LOSS_PCT=0.12`
- `SCENARIO_MAX_POSITION_MULTIPLIER=1.15`
