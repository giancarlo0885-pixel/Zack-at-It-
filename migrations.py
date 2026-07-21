from __future__ import annotations

import os
from pathlib import Path

from database import connect, utc_now

TARGET_BALANCE = float(os.getenv("STARTING_BALANCE", "2000"))
MIGRATION_LOCK_ID = 734_202_603

REPAIR_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS schema_migrations (
        version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS opportunity_rankings (
        id BIGSERIAL PRIMARY KEY, market TEXT NOT NULL, symbol TEXT NOT NULL,
        rank INTEGER NOT NULL, opportunity_score DOUBLE PRECISION NOT NULL,
        payload JSONB, created_at TEXT NOT NULL)""",
    """CREATE INDEX IF NOT EXISTS idx_opportunity_market_created
        ON opportunity_rankings(market, created_at DESC)""",
    """CREATE INDEX IF NOT EXISTS idx_opportunity_market_score
        ON opportunity_rankings(market, opportunity_score DESC)""",
    """CREATE TABLE IF NOT EXISTS portfolio_rotations (
        id BIGSERIAL PRIMARY KEY, market TEXT NOT NULL, sold_symbol TEXT,
        bought_symbol TEXT, score_gap DOUBLE PRECISION, reason TEXT,
        status TEXT NOT NULL DEFAULT 'proposed', created_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS provider_health (
        provider TEXT PRIMARY KEY, configured BOOLEAN NOT NULL,
        status TEXT NOT NULL, latency_ms DOUBLE PRECISION, message TEXT,
        checked_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS backtest_runs (
        id BIGSERIAL PRIMARY KEY, market TEXT, symbol TEXT NOT NULL,
        strategy TEXT NOT NULL, parameters JSONB, metrics JSONB NOT NULL,
        created_at TEXT NOT NULL)""",
    "ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS peak_equity DOUBLE PRECISION",
    "ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS risk_state TEXT DEFAULT 'normal'",
    """CREATE TABLE IF NOT EXISTS trade_dna (
        id BIGSERIAL PRIMARY KEY, market TEXT NOT NULL, symbol TEXT NOT NULL,
        trade_id BIGINT, entry_time TEXT, exit_time TEXT, market_regime TEXT,
        sector TEXT, alpha_score DOUBLE PRECISION, execution_score DOUBLE PRECISION,
        institutional_score DOUBLE PRECISION, risk_score DOUBLE PRECISION,
        relative_value_score DOUBLE PRECISION, trade_quality DOUBLE PRECISION,
        expected_value_pct DOUBLE PRECISION, estimated_cost_pct DOUBLE PRECISION,
        adverse_selection_score DOUBLE PRECISION, probability_of_profit DOUBLE PRECISION,
        risk_reward_ratio DOUBLE PRECISION, entry_reason TEXT, exit_reason TEXT,
        pnl DOUBLE PRECISION, max_favorable_excursion DOUBLE PRECISION,
        max_adverse_excursion DOUBLE PRECISION, holding_minutes INTEGER,
        payload JSONB, created_at TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_trade_dna_market_symbol ON trade_dna(market, symbol, created_at DESC)",
    """CREATE TABLE IF NOT EXISTS market_memory_observations (
        id BIGSERIAL PRIMARY KEY, market TEXT NOT NULL, symbol TEXT NOT NULL,
        regime TEXT, feature_vector JSONB NOT NULL, decision_payload JSONB,
        outcome_linked BOOLEAN NOT NULL DEFAULT FALSE, created_at TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_memory_observations_symbol ON market_memory_observations(market, symbol, created_at DESC)",
    """CREATE TABLE IF NOT EXISTS scenario_assessments (
        id BIGSERIAL PRIMARY KEY, market TEXT NOT NULL, symbol TEXT NOT NULL,
        horizon_days INTEGER NOT NULL, probability_of_profit DOUBLE PRECISION,
        expected_return_pct DOUBLE PRECISION, value_at_risk_95_pct DOUBLE PRECISION,
        expected_shortfall_95_pct DOUBLE PRECISION, position_multiplier DOUBLE PRECISION,
        approved BOOLEAN NOT NULL DEFAULT FALSE, payload JSONB, created_at TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_scenario_market_symbol ON scenario_assessments(market, symbol, created_at DESC)",
    """CREATE TABLE IF NOT EXISTS opportunity_radar_assessments (
        id BIGSERIAL PRIMARY KEY, market TEXT NOT NULL, symbol TEXT NOT NULL,
        primary_setup TEXT NOT NULL, setup_score DOUBLE PRECISION,
        urgency_score DOUBLE PRECISION, durability_score DOUBLE PRECISION,
        catalyst_score DOUBLE PRECISION, crowding_risk DOUBLE PRECISION,
        approved BOOLEAN NOT NULL DEFAULT FALSE, veto BOOLEAN NOT NULL DEFAULT FALSE,
        payload JSONB, created_at TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_radar_market_symbol ON opportunity_radar_assessments(market, symbol, created_at DESC)",
    """CREATE TABLE IF NOT EXISTS explainability_assessments (
        id BIGSERIAL PRIMARY KEY, market TEXT NOT NULL, symbol TEXT NOT NULL,
        recommendation TEXT NOT NULL, consensus_label TEXT,
        consensus_score DOUBLE PRECISION, agreement_pct DOUBLE PRECISION,
        confidence_quality TEXT, payload JSONB, created_at TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_explainability_market_symbol ON explainability_assessments(market, symbol, created_at DESC)",
    """CREATE TABLE IF NOT EXISTS market_memory_model_state (
        market TEXT PRIMARY KEY, completed_trades INTEGER NOT NULL DEFAULT 0,
        win_rate DOUBLE PRECISION, average_return_pct DOUBLE PRECISION,
        model_version TEXT NOT NULL DEFAULT 'v11', payload JSONB,
        updated_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS oracle_decision_audit (
        id BIGSERIAL PRIMARY KEY, market TEXT NOT NULL, symbol TEXT NOT NULL,
        recommendation TEXT NOT NULL, grade TEXT, opportunity_score DOUBLE PRECISION,
        approved BOOLEAN NOT NULL, reason TEXT, payload JSONB, created_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS research_reports (
        id BIGSERIAL PRIMARY KEY, market TEXT NOT NULL, symbol TEXT NOT NULL,
        research_rating TEXT, research_score DOUBLE PRECISION, evidence_quality TEXT,
        payload JSONB, created_at TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_research_reports_symbol ON research_reports(market, symbol, created_at DESC)",
    """CREATE TABLE IF NOT EXISTS portfolio_supercomputer_assessments (
        id BIGSERIAL PRIMARY KEY, market TEXT NOT NULL, symbol TEXT NOT NULL,
        portfolio_health_score DOUBLE PRECISION, candidate_fit_score DOUBLE PRECISION,
        recommended_trade_value DOUBLE PRECISION, recommended_trade_pct DOUBLE PRECISION,
        approved BOOLEAN NOT NULL DEFAULT FALSE, veto BOOLEAN NOT NULL DEFAULT FALSE,
        verdict TEXT, payload JSONB, created_at TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_portfolio_supercomputer_symbol ON portfolio_supercomputer_assessments(market, symbol, created_at DESC)",
]


def _repair_database(conn) -> None:
    for statement in REPAIR_STATEMENTS:
        conn.execute(statement)

    # Preserve existing P/L while upgrading legacy portfolios to V3 funding.
    conn.execute(
        """
        UPDATE portfolios
        SET cash = cash + (%s - starting_balance),
            starting_balance = %s,
            peak_equity = GREATEST(COALESCE(peak_equity, 0), %s),
            updated_at = %s
        WHERE starting_balance < %s
        """,
        (TARGET_BALANCE, TARGET_BALANCE, TARGET_BALANCE, utc_now(), TARGET_BALANCE),
    )

    # Keep the canonical market keys used by workers, portfolios, and dashboard.
    # Older builds wrote the stock heartbeat under ``stock``. Copy the newest
    # legacy state into ``cash`` when needed, then remove the duplicate row.
    conn.execute(
        """
        INSERT INTO market_worker_status(market,status,message,last_run,heartbeat)
        SELECT 'cash', status, message, last_run, heartbeat
        FROM market_worker_status
        WHERE market='stock'
        ON CONFLICT (market) DO UPDATE SET
            status = CASE
                WHEN COALESCE(EXCLUDED.heartbeat, '') > COALESCE(market_worker_status.heartbeat, '')
                THEN EXCLUDED.status ELSE market_worker_status.status END,
            message = CASE
                WHEN COALESCE(EXCLUDED.heartbeat, '') > COALESCE(market_worker_status.heartbeat, '')
                THEN EXCLUDED.message ELSE market_worker_status.message END,
            last_run = GREATEST(EXCLUDED.last_run, market_worker_status.last_run),
            heartbeat = GREATEST(EXCLUDED.heartbeat, market_worker_status.heartbeat)
        """
    )
    conn.execute("DELETE FROM market_worker_status WHERE market='stock'")



def run_migrations() -> list[str]:
    """Repair the live schema and apply unapplied SQL files exactly once."""
    folder = Path(__file__).with_name("migrations")
    applied: list[str] = []

    with connect() as conn:
        # All three Railway services may boot together. The transaction-level
        # advisory lock prevents migration races and releases on commit/rollback.
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK_ID,))
        _repair_database(conn)

        existing = {
            record["version"]
            for record in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }
        if not folder.exists():
            return applied

        for path in sorted(folder.glob("*.sql")):
            if path.name in existing:
                continue
            sql = path.read_text(encoding="utf-8").strip()
            if sql:
                conn.execute(sql)
            conn.execute(
                """INSERT INTO schema_migrations(version,applied_at)
                   VALUES (%s,%s) ON CONFLICT(version) DO NOTHING""",
                (path.name, utc_now()),
            )
            applied.append(path.name)

    return applied
