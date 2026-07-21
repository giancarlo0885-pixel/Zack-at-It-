# V20 — Oracle One

Oracle One is the final deterministic guardian for the complete trading pipeline.
It does not invent signals or override evidence. It verifies that every approved
BUY is internally consistent and executable.

## Final execution invariants

A BUY is blocked when any of these is true:

- `ORACLE_KILL_SWITCH=true`
- the signal exceeds `ORACLE_MAX_SIGNAL_AGE_MINUTES` (default 30)
- opportunity score or probability is outside its valid range
- risk/reward is invalid
- net expected value is not positive
- Scenario Engine, Capital Allocation AI, or Portfolio Supercomputer did not approve
- no positive exact execution-dollar ceiling exists

## Final decision chain

Quant Standard → Market Memory → Global Intelligence → Opportunity Radar →
Scenario Engine → Capital Allocation AI → Portfolio Supercomputer → Oracle One → Execution

## Railway controls

- `ORACLE_KILL_SWITCH=false`
- `ORACLE_MAX_SIGNAL_AGE_MINUTES=30`

Oracle One should be considered the final major architecture layer. Future work
should focus on live-data quality, observed performance, calibration, security,
and user testing rather than adding more decision engines.
