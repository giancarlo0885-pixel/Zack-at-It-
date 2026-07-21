# GARIBALDI MARKET ORACLE V13 — Capital Allocation AI

V13 adds a portfolio-aware capital layer after the Quant Standard, Market Memory, and Scenario Engine.

## Decision chain

1. Quantitative trade quality
2. Historical Market Memory
3. Bull/base/bear Scenario Engine
4. Capital Allocation AI
5. Final worker approval and position size

## Capital formula

The allocator combines:

- opportunity quality and net expected value
- probability and risk/reward
- execution quality and liquidity
- market regime
- cash reserve
- existing symbol exposure
- sector concentration
- estimated portfolio correlation
- competing opportunities
- weakest-position rotation edge

The final position multiplier is the product of scenario, regime, liquidity, edge, concentration, correlation, and cash-capacity multipliers.

## Safety rules

The allocator can veto a trade when:

- the final recommendation is not BUY
- a single position is already too large
- sector exposure is excessive
- correlation is high while the portfolio is crowded
- the trade would leave too little cash
- portfolio-fit priority is too low

## Railway variables

- `CAPITAL_MAX_SINGLE_POSITION_PCT=0.22`
- `CAPITAL_MAX_SECTOR_EXPOSURE_PCT=0.38`
- `CAPITAL_TARGET_CASH_RESERVE_PCT=0.10`
- `CAPITAL_MAX_CORRELATION=0.82`
- `CAPITAL_MIN_ROTATION_EDGE=8.0`
