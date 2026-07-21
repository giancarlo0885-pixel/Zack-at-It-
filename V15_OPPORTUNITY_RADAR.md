# GARIBALDI MARKET ORACLE V15 — Opportunity Radar

V15 adds a strategy-aware Opportunity Radar to the shared Oracle decision chain.

The radar classifies every candidate as one of:

- Momentum Breakout
- Trend Continuation
- Mean Reversion
- Sector Leadership
- Event Driven
- Defensive Rotation
- Crypto Risk-On

It calculates setup strength, urgency, durability, catalyst intensity, crowding risk, a score adjustment, and a position-size multiplier. Crowded or internally conflicting setups can be reduced or vetoed before execution.

Final execution sizing now includes the Radar multiplier:

`Quant × Global × Radar × Scenario × Capital Allocation`

The dashboard exposes the same setup classification and metrics used by the workers.
