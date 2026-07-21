# GARIBALDI MARKET ORACLE™ — Oracle Council V3

## V11 Market Memory

The Oracle now learns from completed simulated trades through transparent historical analog matching. Current setups are compared with Trade DNA using trend, momentum, volatility, volume, sentiment, relative strength, and event risk. Historical evidence can support, reduce, or veto a setup only when the sample is large and similar enough. See `V11_MARKET_MEMORY.md`.



## Railway service commands

Use the existing Railway project and PostgreSQL service. Do not delete your variables.

- Web: `python start_web.py`
- Stock worker: `python stock_worker.py`
- Crypto worker: `python crypto_worker.py`

Link `DATABASE_URL` to all three services. The web process starts even when PostgreSQL is unavailable and displays the database error in the dashboard instead of producing a silent 502.

Railway-ready market intelligence and simulated trading platform with one PostgreSQL database and three services: **web**, **stock-worker**, and **crypto-worker**.

## V3 upgrade

- $2,000 stock portfolio and $2,000 crypto portfolio
- Oracle Council V3 with 12 weighted specialists
- Cross-watchlist opportunity ranking
- Portfolio-rotation proposals and persistence tables
- Friction-aware backtesting with fees, slippage, stops, drawdown, Sharpe ratio, trade log, and equity curve
- In-process API/market-data caching
- Provider credential diagnostics
- Mission Control Streamlit dashboard
- Versioned PostgreSQL migrations
- Automated unit tests and Python compilation checks
- Railway service-specific deployment files

## Architecture

All three services deploy from this repository and share the same `DATABASE_URL`:

```text
web            -> streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
stock-worker   -> python stock_worker.py
crypto-worker  -> python crypto_worker.py
```

Do not create separate databases. Link the same Railway PostgreSQL `DATABASE_URL` variable into all three services.

## Required Railway variables

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
STARTING_BALANCE=2000
STOCK_STARTING_BALANCE=2000
CRYPTO_STARTING_BALANCE=2000
WORKER_INTERVAL_SECONDS=300
ENABLE_AUTOTRADE=true
ENABLE_NEWS=true
API_CACHE_TTL_SECONDS=300
ROTATION_ENABLED=true
ROTATION_MIN_SCORE_GAP=8
OPPORTUNITY_LIMIT=12
```

Optional provider keys remain server-side Railway variables. Never commit credentials.

## Database migrations

`initialize_database()` creates the legacy-compatible core schema. `migrations.py` then applies every unapplied SQL file in `migrations/` and records it in `schema_migrations`. Migration `001_oracle_v3.sql` adds opportunity rankings, rotation history, provider health, backtest runs, and portfolio risk fields.

Existing positions and trades are preserved. New empty portfolios initialize at $2,000. Existing funded portfolios are not silently reset.

## Local test

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m compileall -q .
pytest -q
```

A live application boot also requires a PostgreSQL `DATABASE_URL`.

## Railway deployment

Create exactly three services from the same GitHub repository and use:

- `railway.web.json` as the web reference
- `railway.stock-worker.json` as the stock worker reference
- `railway.crypto-worker.json` as the crypto worker reference

The root `railway.json`, `Dockerfile`, and `Procfile` remain included for compatibility.

## Safety

This is paper trading and market research software. It does not connect to a brokerage, execute real orders, or guarantee returns. Premium intelligence modules report missing providers rather than fabricating data.

## Simplified Oracle Home dashboard

The default Streamlit page now prioritizes immediate answers:

- Current Oracle decision, confidence, rating, and plain-language reason
- Stock, crypto, and combined portfolio scorecards
- Top five ranked opportunities
- Stock and crypto worker health
- Recent activity in readable one-line entries

Detailed positions, Council V3 signals, market radar, trade journal, backtesting,
provider diagnostics, cache statistics, and database migrations remain available
in dedicated tabs.

## Version 7 — Financial Intelligence Platform Overhaul

This package upgrades the project from a trading-centered dashboard to a seven-workspace financial intelligence platform:

- Mission Control with regime, breadth, portfolio, risk, worker and opportunity intelligence
- Opportunity Center with unified stock/crypto rankings
- Market Intelligence with signal maps and event streams
- Portfolio Lab with concentration analysis and backtesting access
- AI Research Desk using the existing OpenAI Responses API integration
- Risk Center with operational and portfolio warnings
- System Health with provider coverage, worker heartbeat, migration and deployment checks

The existing stock worker, crypto worker, execution engine, PostgreSQL schema, migrations and Railway service layout remain compatible. `app_v6_backup.py` is included as a rollback copy of the prior dashboard.

## Institutional-style quantitative trade gate

Version 8 adds `quant_trade_standard.py`. Every automatic entry is now evaluated for alpha, execution quality, portfolio risk, relative value, net expected value after costs, and adverse-selection risk. See `ORACLE_QUANT_STANDARD.md` for formulas and Railway controls.

## V10 Oracle Core alignment

V10 uses one shared decision standard for ranking and execution. `oracle_intelligence.py` converts the quantitative assessment into an actionable Oracle decision with a grade, recommendation, probability estimate, expected upside/downside, risk/reward and net expected value. The dashboard and automatic worker now evaluate opportunities from the same formula.

The database repair migration also creates `trade_dna` and `oracle_decision_audit` tables as the foundation for transparent post-trade learning and decision review.

## V12 Scenario Engine
Every ranked opportunity now includes bull/base/bear cases, probability of profit, expected return, 95% VaR, expected shortfall, uncertainty, and scenario-aware position sizing. See `V12_SCENARIO_ENGINE.md`.

## V13 — Capital Allocation AI

V13 adds portfolio-aware allocation, concentration and correlation controls, cash-reserve protection, opportunity competition, and rotation suggestions. See `V13_CAPITAL_ALLOCATION_AI.md`.

## V14 Global Intelligence
V14 adds cross-market confirmation and regime-aware sizing. The Oracle can use volatility, rates, dollar strength, breadth, liquidity, sector leadership, credit, commodities and crypto context when providers expose those values. It stays neutral when data is unavailable.

## V15 Opportunity Radar

V15 adds strategy-aware setup classification, urgency, durability, catalyst intensity, crowding protection, and a radar position-size multiplier. See `V15_OPPORTUNITY_RADAR.md` for details.


## V16 Explainable AI
Every ranked opportunity now contains a deterministic evidence ledger with weighted engine votes, consensus, conflicts, invalidation conditions, decision path and position-size attribution. See `V16_EXPLAINABLE_AI.md`.

## V17 Institutional Research Lab
Every ranked setup now carries a structured, evidence-based research report. Open **Research Lab** to inspect the thesis, technical/fundamental/catalyst/valuation/risk scores, bull and bear cases, confirmation conditions, invalidation rules, and known data gaps.

## V18 Portfolio Supercomputer

The execution pipeline now includes a portfolio-level optimization gate. See `V18_PORTFOLIO_SUPERCOMPUTER.md` for allocation limits, rotation logic, and audit fixes.


## V19 Autonomous Intelligence

V19 adds a deterministic command layer that combines opportunity quality, portfolio capacity, risk warnings, worker health, and provider readiness into one operating posture and prioritized action list. See `V19_AUTONOMOUS_INTELLIGENCE.md`.

## V20 Oracle One

V20 consolidates the platform behind a final execution-integrity guardian. See
`V20_ORACLE_ONE.md`. A trade cannot execute unless upstream engines agree, data
freshness is acceptable, expected value remains positive, portfolio approval is
present, and an exact dollar ceiling has been assigned.
