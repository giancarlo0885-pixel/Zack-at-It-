# V14 — Global Intelligence

V14 adds a cross-market confirmation layer between Market Memory and the Scenario Engine. It evaluates whether the wider financial system supports each setup using optional inputs for volatility, Treasury yields, dollar strength, market breadth, credit conditions, commodities, crypto, liquidity and sector relative strength.

## Decision chain
Quant Standard → Market Memory → Global Intelligence → Scenario Engine → Capital Allocation AI.

The layer defaults to neutral when data is unavailable. It can adjust quality by at most ±7 points and only veto a trade when multiple severe macro/cross-asset conflicts are present.
