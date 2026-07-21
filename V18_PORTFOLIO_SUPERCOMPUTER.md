# GARIBALDI MARKET ORACLE V18 — Portfolio Supercomputer

V18 adds the final portfolio-level gate between opportunity analysis and execution.

## Decision chain

Quant Standard → Market Memory → Global Intelligence → Opportunity Radar → Scenario Engine → Capital Allocation AI → Portfolio Supercomputer → Execution

## Controls

- Preserves a 10% target cash reserve.
- Caps projected single-symbol exposure near 22%.
- Caps projected sector exposure near 40%.
- Evaluates diversification, liquidity, concentration, drawdown resilience, candidate fit, and portfolio correlation.
- Identifies the weakest current holding and potential rotation candidates.
- Supplies an exact maximum trade dollar value to the execution function.
- Withholds capital when the candidate would violate portfolio limits or simulated tail risk is excessive.

## Audit corrections

- Fixed the `cash` versus `stock` worker heartbeat migration mismatch.
- Execution now respects the Portfolio Supercomputer's exact recommended trade value.
- Candidate exposure limits no longer incorrectly veto a trade because of an unrelated large holding.
