# GARIBALDI MARKET ORACLE™ V11 — Market Memory

V11 adds evidence-based historical analog matching to the V10 Oracle Core.

## What changed

- Every setup receives a normalized fingerprint built from score, confidence, trend, 5-day and 20-day momentum, volatility, volume, news sentiment, relative strength, and event risk.
- The Oracle compares the fingerprint with completed trades stored in `trade_dna`.
- Similar trades are weighted by closeness, not counted equally.
- Market Memory calculates weighted win rate, average return, median return, effective sample size, and average similarity.
- Historical evidence can adjust the final opportunity score by a bounded amount.
- A repeated, high-confidence negative pattern can veto an entry only after the minimum sample requirement is met.
- Every completed position automatically writes a Trade DNA record for future comparisons.
- The dashboard now has a dedicated **Market Memory** workspace and opportunity-level analog metrics.

## Default safety settings

```text
MEMORY_MIN_ANALOGS=5
MEMORY_MAX_ADJUSTMENT=8.0
MEMORY_LOOKBACK_LIMIT=300
MEMORY_VETO_WIN_RATE=0.30
MEMORY_VETO_MIN_ANALOGS=10
```

With little or no history, Market Memory remains neutral. It never fabricates a track record.

## Important behavior

The base quantitative gate still controls execution quality, expected value, spread, slippage, and adverse selection. Market Memory is a second evidence layer. It cannot turn a trade that fails the base quant gate into an approved trade.
