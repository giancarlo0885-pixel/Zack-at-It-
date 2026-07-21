from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from ai_oracle import answer_market_question, market_briefing, openai_available, oracle_council
from autonomous_intelligence import build_autonomous_brief
from backtesting import run_backtest
from cache import stats as cache_stats
from config import APP_NAME, STARTING_BALANCE
from dashboard_helpers import as_float, normalized_confidence, parse_json, short_reason, worker_is_online
from database import initialize_database, row, rows
from market_data import get_history
from market_memory import memory_dashboard_summary
from migrations import run_migrations
from platform_intelligence import build_snapshot, deterministic_brief
from provider_diagnostics import provider_diagnostics

st.set_page_config(page_title=f"{APP_NAME} — Intelligence Platform", page_icon="🔮", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
:root{--bg:#071018;--panel:#0d1823;--panel2:#111f2d;--line:#24384a;--text:#eef5fb;--muted:#94a8ba;--accent:#53e0b3;--purple:#9b87ff;--warn:#ffcc66;--bad:#ff6f7d}
.stApp{background:radial-gradient(circle at 10% 0%,rgba(83,224,179,.12),transparent 30%),radial-gradient(circle at 95% 0%,rgba(155,135,255,.14),transparent 28%),var(--bg)}
.block-container{max-width:1500px;padding-top:1rem;padding-bottom:3rem}.hero{border:1px solid var(--line);background:linear-gradient(135deg,rgba(17,31,45,.98),rgba(9,19,29,.98));border-radius:26px;padding:25px;margin-bottom:14px;box-shadow:0 18px 50px rgba(0,0,0,.24)}
.eyebrow{font-size:.72rem;font-weight:900;letter-spacing:.16em;color:var(--accent);text-transform:uppercase}.hero h1{font-size:clamp(2rem,5vw,3.5rem);line-height:1;margin:.35rem 0}.hero p{color:var(--muted);font-size:1.02rem;max-width:950px}.badge{display:inline-block;padding:.35rem .7rem;border:1px solid var(--line);border-radius:999px;background:#0b1620;margin:.25rem .3rem .1rem 0;color:#cbd8e3;font-size:.82rem}
.kpi{border:1px solid var(--line);border-radius:18px;background:linear-gradient(145deg,var(--panel2),var(--panel));padding:17px;min-height:128px}.kpi small{color:var(--muted);display:block}.kpi b{font-size:2rem;display:block;margin:.25rem 0}.good{color:var(--accent)}.warn{color:var(--warn)}.bad{color:var(--bad)}
.panel{border:1px solid var(--line);border-radius:20px;background:var(--panel);padding:18px;margin-bottom:12px}.panel h3{margin-top:0}.muted{color:var(--muted)}.opportunity{border:1px solid var(--line);border-radius:16px;background:#0a151f;padding:15px;margin-bottom:9px}.opportunity .symbol{font-size:1.35rem;font-weight:900}.score{font-size:1.5rem;font-weight:900;color:var(--accent)}
.alert-card{border-left:4px solid var(--warn);background:#101b26;border-radius:12px;padding:12px 14px;margin-bottom:8px}.brief{font-size:1.03rem;line-height:1.65;color:#d7e3ec}.status{display:inline-flex;align-items:center;gap:7px}.dot{width:9px;height:9px;border-radius:50%;display:inline-block}.dot.on{background:var(--accent);box-shadow:0 0 12px rgba(83,224,179,.7)}.dot.off{background:var(--bad)}
div[data-testid="stMetric"]{border:1px solid var(--line);border-radius:16px;padding:12px;background:var(--panel)}
@media(max-width:700px){.block-container{padding-left:.7rem;padding-right:.7rem}.hero{padding:18px}.hero h1{font-size:2rem}.kpi b{font-size:1.6rem}}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def bootstrap() -> list[str]:
    initialize_database()
    return run_migrations()


def safe_rows(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    try:
        return rows(query, params)
    except Exception:
        return []


def safe_row(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    try:
        return row(query, params) or {}
    except Exception:
        return {}


def money(x: Any) -> str:
    return f"${as_float(x):,.2f}"


def get_portfolio(market: str) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, float]]:
    p = safe_row("SELECT * FROM portfolios WHERE market=%s", (market,))
    pos = safe_rows("SELECT * FROM positions WHERE market=%s ORDER BY symbol", (market,))
    cash = as_float(p.get("cash"), STARTING_BALANCE)
    invested = sum(as_float(x.get("quantity"))*as_float(x.get("current_price")) for x in pos)
    start = as_float(p.get("starting_balance"), STARTING_BALANCE)
    equity = cash + invested
    return p, pos, {"market":market,"cash":cash,"positions_value":invested,"equity":equity,"return_pct":((equity/start)-1)*100 if start else 0}


def latest_opportunities(limit: int = 20) -> list[dict[str, Any]]:
    recs = safe_rows("""SELECT DISTINCT ON (market,symbol) market,symbol,rank,opportunity_score,payload,created_at FROM opportunity_rankings ORDER BY market,symbol,created_at DESC""")
    return sorted(recs,key=lambda x:as_float(x.get("opportunity_score")),reverse=True)[:limit]


def snapshot_context() -> dict[str, Any]:
    stock_p, stock_pos, stock_m = get_portfolio("cash")
    crypto_p, crypto_pos, crypto_m = get_portfolio("crypto")
    signals = safe_rows("SELECT * FROM signals ORDER BY id DESC LIMIT 100")
    opportunities = latest_opportunities(30)
    alerts = safe_rows("SELECT * FROM alerts WHERE acknowledged=0 ORDER BY id DESC LIMIT 30")
    events = safe_rows("SELECT * FROM intelligence_events ORDER BY id DESC LIMIT 40")
    workers = safe_rows("SELECT * FROM market_worker_status ORDER BY market")
    diagnostics = provider_diagnostics()
    snap, risk_reasons = build_snapshot(signals=signals,opportunities=opportunities,positions=stock_pos+crypto_pos,portfolio_metrics=[stock_m,crypto_m],alerts=alerts,diagnostics=diagnostics,workers=workers,worker_online_fn=worker_is_online)
    return {"stock_portfolio":stock_p,"crypto_portfolio":crypto_p,"stock_positions":stock_pos,"crypto_positions":crypto_pos,"portfolios":[stock_m,crypto_m],"signals":signals,"opportunities":opportunities,"alerts":alerts,"events":events,"workers":workers,"diagnostics":diagnostics,"snapshot":snap,"risk_reasons":risk_reasons}


migration_results = bootstrap()
ctx = snapshot_context()
snap = ctx["snapshot"]
autonomous_brief = build_autonomous_brief(ctx)

with st.sidebar:
    st.markdown("## 🔮 Oracle Navigation")
    page = st.radio("Workspace", ["Mission Control","Oracle One","Autonomous Intelligence","Portfolio Supercomputer","Explainable AI","Opportunity Radar","Opportunity Center","Capital Allocator","Scenario Lab","Market Memory","Global Intelligence","Market Intelligence","Portfolio Lab","Research Lab","Research Desk","Risk & Alerts","System Health"], label_visibility="collapsed")
    st.divider()
    st.caption("Platform mode")
    st.write("**Financial intelligence + simulated execution**")
    st.caption("Workers")
    for market in ("cash","crypto"):
        r = next((x for x in ctx["workers"] if x.get("market")==market),{})
        online = worker_is_online(r.get("status"))
        st.markdown(f'<span class="status"><span class="dot {"on" if online else "off"}"></span>{market.title()} worker: {html.escape(str(r.get("status","waiting")))}</span>',unsafe_allow_html=True)
    if st.button("Refresh intelligence", use_container_width=True):
        st.cache_data.clear(); st.rerun()

st.markdown(f"""<div class="hero"><div class="eyebrow">Global Financial Intelligence Platform</div><h1>{html.escape(APP_NAME)}</h1><p>One command center for market regime, opportunity ranking, portfolio intelligence, institutional signals, economic events, AI research, simulated execution, and system health.</p><span class="badge">Regime: {snap.regime}</span><span class="badge">Risk: {snap.risk_level}</span><span class="badge">Coverage: {snap.provider_coverage:.0f}%</span><span class="badge">Updated {datetime.now(timezone.utc).strftime('%H:%M UTC')}</span></div>""",unsafe_allow_html=True)

if page == "Mission Control":
    c1,c2,c3,c4,c5 = st.columns(5)
    cards=[("Market Regime",snap.regime,f"{snap.regime_score:.0f}/100","good" if snap.regime_score>=56 else "warn"),("Risk Radar",snap.risk_level,f"{snap.risk_score:.0f}/100","bad" if snap.risk_score>=55 else "warn"),("Top Opportunity",snap.top_opportunity or "Waiting",f"{snap.top_opportunity_score:.0f}/100","good"),("Signal Breadth",f"{snap.breadth:+.0f}",f"{snap.bullish_signals} buy / {snap.bearish_signals} sell","good" if snap.breadth>=0 else "bad"),("Workers Online",f"{snap.workers_online}/{snap.workers_expected}",f"{snap.active_alerts} active alerts","good" if snap.workers_online>=snap.workers_expected else "bad")]
    for col,(label,value,sub,klass) in zip((c1,c2,c3,c4,c5),cards):
        col.markdown(f'<div class="kpi"><small>{label}</small><b class="{klass}">{value}</b><span class="muted">{sub}</span></div>',unsafe_allow_html=True)
    left,right=st.columns([1.35,1])
    with left:
        st.markdown("### Executive Intelligence Brief")
        brief = deterministic_brief(snap,ctx["risk_reasons"])
        st.markdown(f'<div class="panel brief">{html.escape(brief)}</div>',unsafe_allow_html=True)
        st.markdown(f'<div class="panel"><b>V20 Operating Posture: {html.escape(autonomous_brief.posture)}</b><br><span class="muted">Deployment {autonomous_brief.deployment_score:.1f}/100 · Readiness {autonomous_brief.system_readiness_score:.1f}/100</span></div>',unsafe_allow_html=True)
        if openai_available() and st.button("Generate AI market briefing"):
            with st.spinner("Analyzing current platform data…"):
                st.markdown(market_briefing({"snapshot":snap.to_dict(),"opportunities":ctx["opportunities"][:10],"alerts":ctx["alerts"][:10],"events":ctx["events"][:15],"portfolios":ctx["portfolios"]}))
        st.markdown("### Portfolio Command")
        pcols=st.columns(2)
        for col,data,title in zip(pcols,ctx["portfolios"],["Stock Portfolio","Crypto Portfolio"]):
            klass="good" if data["return_pct"]>=0 else "bad"
            col.markdown(f'<div class="panel"><h3>{title}</h3><div class="score">{money(data["equity"])}</div><div class="{klass}">{data["return_pct"]:+.2f}% return</div><div class="muted">Cash {money(data["cash"])} · Invested {money(data["positions_value"])}</div></div>',unsafe_allow_html=True)
    with right:
        st.markdown("### Priority Opportunities")
        if not ctx["opportunities"]: st.info("No rankings yet. The workers create rankings after completing scans.")
        for i,x in enumerate(ctx["opportunities"][:6],1):
            payload=parse_json(x.get("payload"))
            quant=payload.get("quant",{}) if isinstance(payload,dict) else {}
            grade=str(payload.get("grade","WATCH")) if isinstance(payload,dict) else "WATCH"
            recommendation=str(payload.get("recommendation","WATCH")) if isinstance(payload,dict) else "WATCH"
            probability=as_float(payload.get("probability_of_profit")) if isinstance(payload,dict) else 0.0
            rr=as_float(payload.get("risk_reward_ratio")) if isinstance(payload,dict) else 0.0
            net_ev=as_float(quant.get("net_expected_value_pct"))*100 if isinstance(quant,dict) else 0.0
            scenario=payload.get("scenario",{}) if isinstance(payload,dict) else {}
            capital=payload.get("capital",{}) if isinstance(payload,dict) else {}
            radar=payload.get("radar",{}) if isinstance(payload,dict) else {}
            explain=payload.get("explainability",{}) if isinstance(payload,dict) else {}
            portfolio_ai=payload.get("portfolio_supercomputer",{}) if isinstance(payload,dict) else {}
            scenario_ev=as_float(scenario.get("expected_return_pct"))
            verdict=str(scenario.get("verdict","BUILDING"))
            capital_verdict=str(capital.get("verdict","BUILDING"))
            target_pct=as_float(capital.get("recommended_position_pct"))
            setup=str(radar.get("primary_setup","SCANNING")).title()
            setup_score=as_float(radar.get("setup_score"))
            st.markdown(f'<div class="opportunity"><div class="muted">#{i} · {html.escape(str(x.get("market",""))).upper()} · {html.escape(grade)} · {html.escape(verdict)}</div><div class="symbol">{html.escape(str(x.get("symbol","—")))}</div><div class="score">{html.escape(recommendation)} · {as_float(x.get("opportunity_score")):.1f}/100</div><div class="muted">Radar: {html.escape(setup)} {setup_score:.0f}/100</div><div class="muted">Probability {probability:.0f}% · R/R {rr:.2f}:1 · Net EV {net_ev:+.2f}% · Scenario {scenario_ev:+.2f}%</div><div class="muted">Capital: {html.escape(capital_verdict)} · Target {target_pct:.1f}%</div><div class="muted">Portfolio AI: {html.escape(str(portfolio_ai.get("verdict","BUILDING")))} · {money(as_float(portfolio_ai.get("recommended_trade_value")))}</div><div class="muted">AI consensus: {html.escape(str(explain.get("consensus_label","BUILDING")))} · {as_float(explain.get("agreement_pct")):.0f}% agreement</div><div class="muted">{html.escape(short_reason(x,130))}</div></div>',unsafe_allow_html=True)
        st.markdown("### Risk Watch")
        for reason in ctx["risk_reasons"]:
            st.markdown(f'<div class="alert-card">{html.escape(reason)}</div>',unsafe_allow_html=True)

elif page == "Oracle One":
    st.markdown("## V20 Oracle One")
    st.caption("The final execution-integrity layer. It verifies freshness, engine agreement, positive expected value, portfolio approval, and an exact dollar ceiling before any BUY can reach execution.")
    if not ctx["opportunities"]:
        st.info("Oracle One verdicts appear after the workers publish opportunity rankings.")
    else:
        guardian_rows=[]
        for x in ctx["opportunities"]:
            payload=parse_json(x.get("payload"))
            guard=payload.get("oracle_one",{}) if isinstance(payload,dict) else {}
            guardian_rows.append({
                "Market":str(x.get("market","")).upper(),
                "Symbol":x.get("symbol"),
                "Recommendation":payload.get("recommendation","WATCH") if isinstance(payload,dict) else "WATCH",
                "Oracle One":guard.get("verdict","BUILDING"),
                "Integrity":as_float(guard.get("integrity_score")),
                "Execution ceiling":as_float(guard.get("execution_ceiling")),
                "Stale":bool(guard.get("stale_data",False)),
                "Kill switch":bool(guard.get("kill_switch_active",False)),
            })
        st.dataframe(pd.DataFrame(guardian_rows),use_container_width=True,hide_index=True)
        symbol=st.selectbox("Inspect final execution verdict",[x.get("symbol") for x in ctx["opportunities"]],key="oracle_one_symbol")
        selected=next(x for x in ctx["opportunities"] if x.get("symbol")==symbol)
        payload=parse_json(selected.get("payload")); guard=payload.get("oracle_one",{}) if isinstance(payload,dict) else {}
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Final verdict",guard.get("verdict","BUILDING"))
        c2.metric("Integrity",f"{as_float(guard.get('integrity_score')):.1f}/100")
        c3.metric("Execution ceiling",money(as_float(guard.get("execution_ceiling"))))
        c4.metric("Approved", "YES" if guard.get("approved") else "NO")
        st.markdown(f'<div class="panel brief">{html.escape(str(guard.get("summary","Final validation is building.")))}</div>',unsafe_allow_html=True)
        left,right=st.columns(2)
        with left:
            st.markdown("### Blocking failures")
            failures=guard.get("invariant_failures",[]) or []
            if failures:
                for item in failures: st.markdown(f'<div class="alert-card">{html.escape(str(item))}</div>',unsafe_allow_html=True)
            else:
                st.success("No execution invariant failed.")
        with right:
            st.markdown("### Cautions")
            warnings=guard.get("warnings",[]) or []
            if warnings:
                for item in warnings: st.write(f"• {item}")
            else:
                st.success("No final-stage caution is active.")

elif page == "Autonomous Intelligence":
    st.markdown("## V19 Autonomous Intelligence")
    st.caption("A deterministic command brief that combines opportunity quality, portfolio capacity, active risk, worker health, and provider readiness into one operating posture.")
    c1,c2,c3=st.columns(3)
    c1.metric("Operating posture", autonomous_brief.posture)
    c2.metric("Deployment score", f"{autonomous_brief.deployment_score:.1f}/100")
    c3.metric("System readiness", f"{autonomous_brief.system_readiness_score:.1f}/100")
    st.markdown(f'<div class="panel brief">{html.escape(autonomous_brief.executive_brief)}</div>',unsafe_allow_html=True)
    left,right=st.columns(2)
    with left:
        st.markdown("### Command priorities")
        for action in autonomous_brief.top_actions:
            st.markdown(f'<div class="alert-card">{html.escape(action)}</div>',unsafe_allow_html=True)
    with right:
        st.markdown("### Evidence ledger")
        st.write(autonomous_brief.opportunity_summary)
        st.write(autonomous_brief.portfolio_summary)
        st.write(autonomous_brief.risk_summary)
        st.write(autonomous_brief.operations_summary)

elif page == "Portfolio Supercomputer":
    st.markdown("## V18 Portfolio Supercomputer")
    st.caption("Portfolio-level optimization that checks cash, concentration, diversification, drawdown resilience, candidate fit, rotation opportunities, and the exact dollar amount the worker is allowed to deploy.")
    if not ctx["opportunities"]:
        st.info("Portfolio assessments appear after the workers publish opportunity rankings.")
    else:
        portfolio_rows=[]
        for x in ctx["opportunities"]:
            payload=parse_json(x.get("payload"))
            ps=payload.get("portfolio_supercomputer",{}) if isinstance(payload,dict) else {}
            portfolio_rows.append({
                "Market":str(x.get("market","")).upper(), "Symbol":x.get("symbol"),
                "Decision":payload.get("recommendation","WATCH") if isinstance(payload,dict) else "WATCH",
                "Verdict":ps.get("verdict","BUILDING"),
                "Portfolio health":as_float(ps.get("portfolio_health_score")),
                "Candidate fit":as_float(ps.get("candidate_fit_score")),
                "Target $":as_float(ps.get("recommended_trade_value")),
                "Target %":as_float(ps.get("recommended_trade_pct")),
                "Cash after %":as_float(ps.get("projected_cash_pct")),
                "Rotation":ps.get("rotation_candidate") or "—",
            })
        st.dataframe(pd.DataFrame(portfolio_rows),use_container_width=True,hide_index=True)
        symbol=st.selectbox("Inspect portfolio decision",[x.get("symbol") for x in ctx["opportunities"]],key="portfolio_supercomputer_symbol")
        selected=next(x for x in ctx["opportunities"] if x.get("symbol")==symbol)
        payload=parse_json(selected.get("payload")); ps=payload.get("portfolio_supercomputer",{}) if isinstance(payload,dict) else {}
        p1,p2,p3,p4=st.columns(4)
        p1.metric("Portfolio health",f"{as_float(ps.get('portfolio_health_score')):.1f}/100")
        p2.metric("Candidate fit",f"{as_float(ps.get('candidate_fit_score')):.1f}/100")
        p3.metric("Approved target",money(as_float(ps.get('recommended_trade_value'))))
        p4.metric("Projected cash",f"{as_float(ps.get('projected_cash_pct')):.1f}%")
        q1,q2,q3,q4=st.columns(4)
        q1.metric("Diversification",f"{as_float(ps.get('diversification_score')):.1f}/100")
        q2.metric("Liquidity",f"{as_float(ps.get('liquidity_score')):.1f}/100")
        q3.metric("Concentration",f"{as_float(ps.get('concentration_score')):.1f}/100")
        q4.metric("Drawdown resilience",f"{as_float(ps.get('drawdown_resilience_score')):.1f}/100")
        st.markdown(f"### {html.escape(str(ps.get('verdict','BUILDING')))}")
        st.write(ps.get("summary","Portfolio analysis is building."))
        left,right=st.columns(2)
        with left:
            st.markdown("#### Exposure projection")
            st.write(f"Largest position: {as_float(ps.get('current_largest_position_pct')):.1f}% → {as_float(ps.get('projected_largest_position_pct')):.1f}%")
            st.write(f"Largest sector: {as_float(ps.get('current_sector_concentration_pct')):.1f}% → {as_float(ps.get('projected_sector_concentration_pct')):.1f}%")
            st.write(f"Position multiplier: {as_float(ps.get('position_multiplier')):.3f}×")
        with right:
            st.markdown("#### Rebalance actions")
            for action in ps.get("rebalance_actions",[]) or ["No rebalance guidance available yet."]:
                st.write(f"• {action}")
            if ps.get("weakest_position"):
                st.write(f"Weakest position: **{ps.get('weakest_position')}** ({as_float(ps.get('weakest_position_score')):.1f})")

elif page == "Explainable AI":
    st.markdown("## V16 Explainable AI")
    st.caption("A deterministic evidence ledger showing how every Oracle engine voted, what supports the trade, what conflicts with it, what invalidates the thesis, and how the final position size was formed.")
    if not ctx["opportunities"]:
        st.info("Explainability reports appear after the workers publish opportunity rankings.")
    else:
        explain_rows=[]
        for x in ctx["opportunities"]:
            payload=parse_json(x.get("payload"))
            ex=payload.get("explainability",{}) if isinstance(payload,dict) else {}
            explain_rows.append({
                "Market":str(x.get("market","")).upper(), "Symbol":x.get("symbol"),
                "Decision":payload.get("recommendation","WATCH") if isinstance(payload,dict) else "WATCH",
                "Consensus":ex.get("consensus_label","BUILDING"),
                "Agreement %":as_float(ex.get("agreement_pct")),
                "Consensus quality":as_float(ex.get("consensus_score")),
                "Confidence quality":ex.get("confidence_quality","BUILDING"),
                "Conflicts":len(ex.get("conflicts",[]) or []),
            })
        st.dataframe(pd.DataFrame(explain_rows),use_container_width=True,hide_index=True)
        symbol=st.selectbox("Inspect Oracle reasoning",[x.get("symbol") for x in ctx["opportunities"]],key="explain_symbol")
        selected=next(x for x in ctx["opportunities"] if x.get("symbol")==symbol)
        payload=parse_json(selected.get("payload")); ex=payload.get("explainability",{}) if isinstance(payload,dict) else {}
        e1,e2,e3,e4=st.columns(4)
        e1.metric("Final decision",str(payload.get("recommendation","WATCH")))
        e2.metric("Consensus",str(ex.get("consensus_label","BUILDING")))
        e3.metric("Engine agreement",f"{as_float(ex.get('agreement_pct')):.1f}%")
        e4.metric("Confidence quality",str(ex.get("confidence_quality","BUILDING")))
        votes=ex.get("engine_votes",[]) or []
        if votes:
            st.markdown("### Engine vote ledger")
            st.dataframe(pd.DataFrame(votes),use_container_width=True,hide_index=True)
        left,right=st.columns(2)
        with left:
            st.markdown("### Strongest supporting evidence")
            for item in ex.get("strongest_drivers",[]) or []: st.success(str(item))
            if not ex.get("strongest_drivers"): st.info("No engine has produced strong supporting evidence yet.")
            st.markdown("### Decision path")
            for i,item in enumerate(ex.get("decision_path",[]) or [],1): st.write(f"{i}. {item}")
        with right:
            st.markdown("### Material conflicts")
            for item in ex.get("conflicts",[]) or []: st.warning(str(item))
            if not ex.get("conflicts"): st.success("No material engine conflict detected.")
            st.markdown("### Thesis invalidation")
            for item in ex.get("invalidation_conditions",[]) or []: st.error(str(item))
        st.markdown("### Position-size attribution")
        for item in ex.get("sizing_explanation",[]) or []: st.write(f"• {item}")
        st.markdown(f'<div class="panel brief">{html.escape(str(ex.get("summary","Explainability is building.")))}</div>',unsafe_allow_html=True)

elif page == "Opportunity Radar":
    st.markdown("## V15 Opportunity Radar")
    st.caption("Strategy-aware scanner that classifies each setup, measures urgency and durability, and rejects crowded or stale entries before capital is committed.")
    if not ctx["opportunities"]:
        st.info("Radar results appear after the workers complete a scan.")
    else:
        radar_rows=[]
        for x in ctx["opportunities"]:
            payload=parse_json(x.get("payload"))
            radar=payload.get("radar",{}) if isinstance(payload,dict) else {}
            radar_rows.append({
                "Market":str(x.get("market","")).upper(),
                "Symbol":x.get("symbol"),
                "Decision":payload.get("recommendation","WATCH") if isinstance(payload,dict) else "WATCH",
                "Primary setup":str(radar.get("primary_setup","SCANNING")).title(),
                "Setup score":as_float(radar.get("setup_score")),
                "Urgency":as_float(radar.get("urgency_score")),
                "Durability":as_float(radar.get("durability_score")),
                "Catalyst":as_float(radar.get("catalyst_score")),
                "Crowding risk":as_float(radar.get("crowding_risk")),
                "Radar adjustment":as_float(radar.get("radar_adjustment")),
                "Size multiplier":as_float(radar.get("position_multiplier")),
                "Veto":bool(radar.get("veto",False)),
            })
        rdf=pd.DataFrame(radar_rows)
        st.dataframe(rdf,use_container_width=True,hide_index=True)
        radar_symbol=st.selectbox("Inspect radar setup",[x.get("symbol") for x in ctx["opportunities"]],key="radar_symbol")
        selected=next(x for x in ctx["opportunities"] if x.get("symbol")==radar_symbol)
        payload=parse_json(selected.get("payload"))
        radar=payload.get("radar",{}) if isinstance(payload,dict) else {}
        r1,r2,r3,r4,r5=st.columns(5)
        r1.metric("Primary setup",str(radar.get("primary_setup","SCANNING")).title())
        r2.metric("Setup strength",f"{as_float(radar.get('setup_score')):.1f}/100")
        r3.metric("Urgency",f"{as_float(radar.get('urgency_score')):.1f}/100")
        r4.metric("Durability",f"{as_float(radar.get('durability_score')):.1f}/100")
        r5.metric("Crowding risk",f"{as_float(radar.get('crowding_risk')):.1f}/100")
        st.markdown(f'<div class="panel"><h3>{html.escape(str(radar.get("primary_setup","Scanning")).title())}</h3><div class="muted">Secondary lens: {html.escape(str(radar.get("secondary_setup","—")).title())}</div><p>{html.escape(str(radar.get("summary","Radar analysis is building.")))}</p></div>',unsafe_allow_html=True)
        reasons=radar.get("reasons",[]) or []
        warnings=radar.get("warnings",[]) or []
        a,b=st.columns(2)
        with a:
            st.markdown("### Supporting evidence")
            if reasons:
                for reason in reasons: st.success(str(reason))
            else: st.info("No strong setup confirmations yet.")
        with b:
            st.markdown("### Entry warnings")
            if warnings:
                for warning in warnings: st.warning(str(warning))
            else: st.success("No material radar warnings.")

elif page == "Opportunity Center":
    st.markdown("## Opportunity Center")
    st.caption("Ranked decision support—not a profit guarantee. Filter the full stock and crypto opportunity universe.")
    market_filter=st.selectbox("Market",["All","cash","crypto"])
    opps=[x for x in ctx["opportunities"] if market_filter=="All" or x.get("market")==market_filter]
    if opps:
        table_rows=[]
        for i,x in enumerate(opps):
            payload=parse_json(x.get("payload"))
            quant=payload.get("quant",{}) if isinstance(payload,dict) else {}
            table_rows.append({"Rank":i+1,"Market":x.get("market"),"Symbol":x.get("symbol"),"Grade":payload.get("grade","—") if isinstance(payload,dict) else "—","Action":payload.get("recommendation","WATCH") if isinstance(payload,dict) else "WATCH","Quality":round(as_float(x.get("opportunity_score")),1),"Probability %":as_float(payload.get("probability_of_profit")) if isinstance(payload,dict) else 0,"Risk/Reward":as_float(payload.get("risk_reward_ratio")) if isinstance(payload,dict) else 0,"Net EV %":round(as_float(quant.get("net_expected_value_pct"))*100,2) if isinstance(quant,dict) else 0,"Scenario":(payload.get("scenario",{}) or {}).get("verdict","—") if isinstance(payload,dict) else "—","Scenario EV %":as_float((payload.get("scenario",{}) or {}).get("expected_return_pct")) if isinstance(payload,dict) else 0,"Setup":str((payload.get("radar",{}) or {}).get("primary_setup","—")).title() if isinstance(payload,dict) else "—","Radar":as_float((payload.get("radar",{}) or {}).get("setup_score")) if isinstance(payload,dict) else 0,"Crowding":as_float((payload.get("radar",{}) or {}).get("crowding_risk")) if isinstance(payload,dict) else 0,"AI Consensus":(payload.get("explainability",{}) or {}).get("consensus_label","—") if isinstance(payload,dict) else "—","Agreement %":as_float((payload.get("explainability",{}) or {}).get("agreement_pct")) if isinstance(payload,dict) else 0,"Updated":x.get("created_at")})
        df=pd.DataFrame(table_rows)
        st.dataframe(df,use_container_width=True,hide_index=True)
        sym=st.selectbox("Open opportunity",[x.get("symbol") for x in opps])
        selected=next(x for x in opps if x.get("symbol")==sym)
        payload=parse_json(selected.get("payload"))
        a,b=st.columns([1,1])
        quant=payload.get("quant",{}) if isinstance(payload,dict) else {}
        a.metric("Recommendation",str(payload.get("recommendation","WATCH")) if isinstance(payload,dict) else "WATCH")
        a.metric("Trade quality",f"{as_float(selected.get('opportunity_score')):.1f}/100")
        a.metric("Probability of profit",f"{as_float(payload.get('probability_of_profit')):.1f}%" if isinstance(payload,dict) else "—")
        a.metric("Risk / reward",f"{as_float(payload.get('risk_reward_ratio')):.2f}:1" if isinstance(payload,dict) else "—")
        a.write(short_reason(selected,500))
        b.metric("Net expected value",f"{as_float(quant.get('net_expected_value_pct'))*100:+.2f}%" if isinstance(quant,dict) else "—")
        b.metric("Execution quality",f"{as_float(quant.get('execution_score')):.1f}/100" if isinstance(quant,dict) else "—")
        b.metric("Risk quality",f"{as_float(quant.get('risk_score')):.1f}/100" if isinstance(quant,dict) else "—")
        scenario=payload.get("scenario",{}) if isinstance(payload,dict) else {}
        st.markdown("### V12 Scenario Engine")
        s1,s2,s3,s4=st.columns(4)
        s1.metric("Scenario verdict",str(scenario.get("verdict","BUILDING")))
        s2.metric("Profitable paths",f"{as_float(scenario.get('probability_of_profit')):.1f}%")
        s3.metric("Expected return",f"{as_float(scenario.get('expected_return_pct')):+.2f}%")
        s4.metric("95% tail loss",f"{as_float(scenario.get('expected_shortfall_95_pct')):+.2f}%")
        if scenario.get("summary"): st.caption(str(scenario.get("summary")))
        radar=payload.get("radar",{}) if isinstance(payload,dict) else {}
        st.markdown("### V15 Opportunity Radar")
        q1,q2,q3,q4=st.columns(4)
        q1.metric("Setup",str(radar.get("primary_setup","SCANNING")).title())
        q2.metric("Setup strength",f"{as_float(radar.get('setup_score')):.1f}/100")
        q3.metric("Durability",f"{as_float(radar.get('durability_score')):.1f}/100")
        q4.metric("Crowding risk",f"{as_float(radar.get('crowding_risk')):.1f}/100")
        if radar.get("summary"): st.caption(str(radar.get("summary")))
        memory=payload.get("memory",{}) if isinstance(payload,dict) else {}
        st.markdown("### Market Memory")
        m1,m2,m3,m4=st.columns(4)
        m1.metric("Historical pattern",str(memory.get("pattern_label","NO HISTORY")))
        m2.metric("Similar setups",str(int(as_float(memory.get("analog_count")))))
        win_rate=memory.get("win_rate")
        m3.metric("Analog win rate",f"{as_float(win_rate)*100:.1f}%" if win_rate is not None else "—")
        m4.metric("Score adjustment",f"{as_float(memory.get('score_adjustment')):+.1f}")
        if memory.get("summary"): st.caption(str(memory.get("summary")))
        explain=payload.get("explainability",{}) if isinstance(payload,dict) else {}
        st.markdown("### V16 Explainable AI")
        x1,x2,x3=st.columns(3)
        x1.metric("Consensus",str(explain.get("consensus_label","BUILDING")))
        x2.metric("Engine agreement",f"{as_float(explain.get('agreement_pct')):.1f}%")
        x3.metric("Confidence quality",str(explain.get("confidence_quality","BUILDING")))
        if explain.get("summary"): st.caption(str(explain.get("summary")))
        with b.expander("Full Oracle decision data"):
            st.json(payload or {"message":"No extended ranking payload saved."})
    else: st.info("No ranked opportunities are stored yet.")

elif page == "Capital Allocator":
    st.markdown("## V13 Capital Allocation AI")
    st.caption("Compares opportunity quality with cash, concentration, correlation, regime, liquidity, and existing positions before capital is committed.")
    if not ctx["opportunities"]:
        st.info("Capital plans appear after the workers publish opportunity rankings.")
    else:
        allocation_rows=[]
        for x in ctx["opportunities"]:
            payload=parse_json(x.get("payload"))
            capital=payload.get("capital",{}) if isinstance(payload,dict) else {}
            allocation_rows.append({
                "Market":x.get("market"),"Symbol":x.get("symbol"),
                "Decision":payload.get("recommendation","WATCH") if isinstance(payload,dict) else "WATCH",
                "Capital verdict":capital.get("verdict","BUILDING"),
                "Priority":as_float(capital.get("capital_priority_score")),
                "Portfolio fit":as_float(capital.get("portfolio_fit_score")),
                "Target equity %":as_float(capital.get("recommended_position_pct")),
                "Target value":as_float(capital.get("recommended_position_value")),
                "Cash after %":as_float(capital.get("cash_after_trade_pct")),
                "Rotation":capital.get("rotation_candidate") or "—",
            })
        st.dataframe(pd.DataFrame(allocation_rows),use_container_width=True,hide_index=True)
        symbol=st.selectbox("Inspect allocation",[x.get("symbol") for x in ctx["opportunities"]],key="capital_symbol")
        selected=next(x for x in ctx["opportunities"] if x.get("symbol")==symbol)
        payload=parse_json(selected.get("payload")); capital=payload.get("capital",{}) if isinstance(payload,dict) else {}
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Capital verdict",str(capital.get("verdict","BUILDING")))
        c2.metric("Priority",f"{as_float(capital.get('capital_priority_score')):.1f}/100")
        c3.metric("Target allocation",f"{as_float(capital.get('recommended_position_pct')):.1f}%")
        c4.metric("Target value",money(capital.get("recommended_position_value")))
        c5,c6,c7,c8=st.columns(4)
        c5.metric("Portfolio fit",f"{as_float(capital.get('portfolio_fit_score')):.1f}/100")
        c6.metric("Cash after trade",f"{as_float(capital.get('cash_after_trade_pct')):.1f}%")
        c7.metric("Concentration penalty",f"{as_float(capital.get('concentration_penalty')):.1f}")
        c8.metric("Correlation penalty",f"{as_float(capital.get('correlation_penalty')):.1f}")
        if capital.get("rotation_candidate"):
            st.warning(f"Rotate from {capital.get('rotation_candidate')} first. Estimated edge: {as_float(capital.get('rotation_edge')):.1f} points.")
        st.markdown(f'<div class="panel brief">{html.escape(str(capital.get("summary","Capital analysis is building.")))}</div>',unsafe_allow_html=True)

elif page == "Scenario Lab":
    st.markdown("## V12 Scenario Lab")
    st.caption("Probability-weighted bull, base and bear cases with a simulated path distribution. Scenarios measure uncertainty; they do not guarantee outcomes.")
    scenario_rows=[]
    for x in ctx["opportunities"]:
        payload=parse_json(x.get("payload"))
        sc=payload.get("scenario",{}) if isinstance(payload,dict) else {}
        scenario_rows.append({
            "Market":x.get("market"),"Symbol":x.get("symbol"),"Verdict":sc.get("verdict","BUILDING"),
            "Profit Paths %":as_float(sc.get("probability_of_profit")),"Expected %":as_float(sc.get("expected_return_pct")),
            "Median %":as_float(sc.get("median_return_pct")),"95% VaR %":as_float(sc.get("value_at_risk_95_pct")),
            "Tail Loss %":as_float(sc.get("expected_shortfall_95_pct")),"Uncertainty %":as_float(sc.get("uncertainty_pct")),
            "Size Multiplier":as_float(sc.get("position_multiplier")),"Approved":bool(sc.get("approved",False)),
        })
    if scenario_rows:
        st.dataframe(pd.DataFrame(scenario_rows),use_container_width=True,hide_index=True)
        selected_symbol=st.selectbox("Inspect scenario",[x.get("symbol") for x in ctx["opportunities"]],key="scenario_symbol")
        selected=next(x for x in ctx["opportunities"] if x.get("symbol")==selected_symbol)
        payload=parse_json(selected.get("payload")); sc=payload.get("scenario",{}) if isinstance(payload,dict) else {}
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Verdict",str(sc.get("verdict","BUILDING")))
        c2.metric("Profitable paths",f"{as_float(sc.get('probability_of_profit')):.1f}%")
        c3.metric("Expected return",f"{as_float(sc.get('expected_return_pct')):+.2f}%")
        c4.metric("Position multiplier",f"{as_float(sc.get('position_multiplier')):.2f}×")
        cases=[]
        for label in ("bull","base","bear"):
            case=sc.get(label,{}) or {}
            cases.append({"Case":str(case.get("name",label.upper())),"Probability %":as_float(case.get("probability"))*100,"Return %":as_float(case.get("return_pct"))*100,"Price Target":case.get("price_target"),"Explanation":case.get("explanation")})
        st.dataframe(pd.DataFrame(cases),use_container_width=True,hide_index=True)
        st.markdown("### Risk envelope")
        r1,r2,r3,r4=st.columns(4)
        r1.metric("Median",f"{as_float(sc.get('median_return_pct')):+.2f}%")
        r2.metric("95% VaR",f"{as_float(sc.get('value_at_risk_95_pct')):+.2f}%")
        r3.metric("Expected shortfall",f"{as_float(sc.get('expected_shortfall_95_pct')):+.2f}%")
        r4.metric("Uncertainty band",f"{as_float(sc.get('uncertainty_pct')):.2f}%")
        st.info(str(sc.get("summary","Scenario data will populate after the next worker scan.")))
    else:
        st.info("No opportunities have been ranked yet. Scenario results appear after the workers complete a scan.")

elif page == "Market Memory":
    st.markdown("## V11 Market Memory")
    st.caption("The Oracle compares current setups with completed historical trades. Memory can support, reduce, or veto a trade, but it never invents history when the sample is too small.")
    memory_summary=memory_dashboard_summary()
    a,b,c=st.columns(3)
    a.metric("Completed Trade DNA",str(memory_summary.get("completed_trades",0)))
    wr=memory_summary.get("win_rate")
    b.metric("Historical win rate",f"{as_float(wr)*100:.1f}%" if wr is not None else "Building history")
    ar=memory_summary.get("average_return_pct")
    c.metric("Average completed return",f"{as_float(ar)*100:+.2f}%" if ar is not None else "Building history")

    st.markdown("### Current Opportunity Memory")
    memory_rows=[]
    for x in ctx["opportunities"]:
        payload=parse_json(x.get("payload"))
        memory=payload.get("memory",{}) if isinstance(payload,dict) else {}
        memory_rows.append({
            "Market":x.get("market"), "Symbol":x.get("symbol"),
            "Pattern":memory.get("pattern_label","NO HISTORY"),
            "Analogs":int(as_float(memory.get("analog_count"))),
            "Win Rate %":round(as_float(memory.get("win_rate"))*100,1) if memory.get("win_rate") is not None else None,
            "Avg Return %":round(as_float(memory.get("average_return_pct"))*100,2) if memory.get("average_return_pct") is not None else None,
            "Similarity %":round(as_float(memory.get("average_similarity"))*100,1),
            "Memory Adjustment":as_float(memory.get("score_adjustment")),
            "Final Quality":as_float(x.get("opportunity_score")),
            "Recommendation":payload.get("recommendation","WATCH") if isinstance(payload,dict) else "WATCH",
        })
    if memory_rows:
        st.dataframe(pd.DataFrame(memory_rows),use_container_width=True,hide_index=True)
    else:
        st.info("No ranked opportunities are available yet. Both workers must complete a scan.")

    left,right=st.columns(2)
    with left:
        st.markdown("### Strongest historical regimes")
        best=memory_summary.get("best_patterns",[])
        if best:
            st.dataframe(pd.DataFrame(best),use_container_width=True,hide_index=True)
        else: st.info("Trade DNA will populate this after positions close.")
    with right:
        st.markdown("### Weakest historical regimes")
        weak=memory_summary.get("weak_patterns",[])
        if weak:
            st.dataframe(pd.DataFrame(weak),use_container_width=True,hide_index=True)
        else: st.info("Trade DNA will populate this after positions close.")

    st.markdown("### How V11 uses memory")
    st.markdown("""- Builds a normalized fingerprint from trend, momentum, volatility, volume, sentiment, relative strength, event risk, score, and confidence.  
- Finds completed trades with the closest setup fingerprints.  
- Weights the nearest analogs more heavily than loose matches.  
- Adjusts quality by up to the configured limit; a strong negative history can veto an entry only when the sample and confidence are sufficient.  
- Stores every completed trade as Trade DNA so the evidence base grows automatically.""")

elif page == "Global Intelligence":
    st.markdown("## V14 Global Intelligence")
    st.caption("Cross-market confirmation connects each trade to volatility, rates, dollar strength, market breadth, liquidity, sector leadership, commodities, credit and crypto conditions. Missing inputs remain neutral rather than fabricated.")
    global_rows=[]
    for x in ctx["opportunities"]:
        payload=parse_json(x.get("payload"))
        gi=payload.get("global_intelligence",{}) if isinstance(payload,dict) else {}
        global_rows.append({
            "Market":x.get("market"),"Symbol":x.get("symbol"),"Regime":gi.get("regime","MIXED"),
            "Verdict":gi.get("verdict","BUILDING"),"Global Score":as_float(gi.get("global_score")),
            "Macro":as_float(gi.get("macro_alignment_score")),"Cross Asset":as_float(gi.get("cross_asset_confirmation_score")),
            "Sector":as_float(gi.get("sector_alignment_score")),"Liquidity":as_float(gi.get("liquidity_regime_score")),
            "Risk-On":as_float(gi.get("risk_on_score")),"Score Adjustment":as_float(gi.get("score_adjustment")),
            "Size Multiplier":as_float(gi.get("position_multiplier")),"Veto":bool(gi.get("veto",False)),
        })
    if global_rows:
        st.dataframe(pd.DataFrame(global_rows),use_container_width=True,hide_index=True)
        symbol=st.selectbox("Inspect global backdrop",[x.get("symbol") for x in ctx["opportunities"]],key="global_symbol")
        selected=next(x for x in ctx["opportunities"] if x.get("symbol")==symbol)
        payload=parse_json(selected.get("payload")); gi=payload.get("global_intelligence",{}) if isinstance(payload,dict) else {}
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Global score",f"{as_float(gi.get('global_score')):.1f}/100")
        c2.metric("Regime",str(gi.get("regime","MIXED")))
        c3.metric("Quality adjustment",f"{as_float(gi.get('score_adjustment')):+.1f}")
        c4.metric("Position multiplier",f"{as_float(gi.get('position_multiplier')):.2f}×")
        left,right=st.columns(2)
        with left:
            st.markdown("### Supporting drivers")
            drivers=gi.get("drivers",[]) or []
            if drivers:
                for item in drivers: st.success(str(item))
            else: st.info("No strong global confirmation is available yet.")
        with right:
            st.markdown("### Conflicts")
            conflicts=gi.get("conflicts",[]) or []
            if conflicts:
                for item in conflicts: st.warning(str(item))
            else: st.success("No major cross-market conflict detected.")
        st.markdown(f'<div class="panel brief">{html.escape(str(gi.get("summary","Global intelligence is building.")))}</div>',unsafe_allow_html=True)
    else:
        st.info("Global intelligence appears after the workers rank opportunities.")

elif page == "Market Intelligence":
    st.markdown("## Market Intelligence")
    tabs=st.tabs(["Signal Map","Event Stream","Economic Lens","Sector Pulse"])
    with tabs[0]:
        sig=ctx["signals"]
        if sig:
            df=pd.DataFrame([{"Market":x.get("market"),"Symbol":x.get("symbol"),"Action":x.get("action"),"Score":as_float(x.get("score")),"Confidence":normalized_confidence(x.get("confidence")),"Price":as_float(x.get("price")),"Time":x.get("created_at")} for x in sig])
            st.dataframe(df,use_container_width=True,hide_index=True)
        else: st.info("No signals yet.")
    with tabs[1]:
        for x in ctx["events"]:
            st.markdown(f'<div class="panel"><b>{html.escape(str(x.get("title","Event")))}</b><div class="muted">{html.escape(str(x.get("category","")))} · {html.escape(str(x.get("provider","")))} · {html.escape(str(x.get("symbol") or "Global"))}</div><p>{html.escape(short_reason(x.get("details"),350))}</p></div>',unsafe_allow_html=True)
        if not ctx["events"]: st.info("No intelligence events stored yet.")
    with tabs[2]:
        cats={}
        for x in ctx["events"]: cats[str(x.get("category","other"))]=cats.get(str(x.get("category","other")),0)+1
        if cats:
            fig=px.bar(pd.DataFrame({"Category":list(cats),"Events":list(cats.values())}),x="Category",y="Events",title="Intelligence coverage by category")
            st.plotly_chart(fig,use_container_width=True)
        else: st.info("Economic and macro modules will populate this view as providers return data.")
    with tabs[3]:
        st.write("Current breadth combines the latest worker decisions across stocks and crypto.")
        st.metric("Breadth",f"{snap.breadth:+.1f}")
        st.progress(max(0,min(100,int((snap.breadth+100)/2))))

elif page == "Portfolio Lab":
    st.markdown("## Portfolio Lab")
    market=st.segmented_control("Portfolio",options=["cash","crypto"],default="cash")
    p,positions,m= get_portfolio(market)
    a,b,c,d=st.columns(4); a.metric("Equity",money(m["equity"])); b.metric("Cash",money(m["cash"])); c.metric("Invested",money(m["positions_value"])); d.metric("Return",f"{m['return_pct']:+.2f}%")
    if positions:
        df=pd.DataFrame([{"Symbol":x.get("symbol"),"Quantity":as_float(x.get("quantity")),"Average Price":as_float(x.get("average_price") or x.get("entry_price")),"Current Price":as_float(x.get("current_price")),"Market Value":as_float(x.get("quantity"))*as_float(x.get("current_price")),"Unrealized P&L":as_float(x.get("quantity"))*(as_float(x.get("current_price"))-as_float(x.get("average_price") or x.get("entry_price")))} for x in positions])
        st.dataframe(df,use_container_width=True,hide_index=True)
        fig=px.pie(df,values="Market Value",names="Symbol",title="Position concentration")
        st.plotly_chart(fig,use_container_width=True)
    else: st.info("This portfolio currently has no open positions.")
    st.markdown("### Backtest Workbench")
    symbol=st.text_input("Symbol",value="SPY" if market=="cash" else "BTC-USD").upper().strip()
    if st.button("Run backtest"):
        try:
            result=run_backtest(symbol=symbol,market=market)
            st.json(result)
        except TypeError:
            try: st.json(run_backtest(symbol))
            except Exception as exc: st.error(f"Backtest could not run: {exc}")
        except Exception as exc: st.error(f"Backtest could not run: {exc}")

elif page == "Research Lab":
    st.markdown("## V17 Institutional Research Lab")
    st.caption("Deterministic research reports built from the same evidence that controls ranking, risk, and execution. Missing data is identified instead of fabricated.")
    if not ctx["opportunities"]:
        st.info("Research reports appear after the workers publish opportunity rankings.")
    else:
        research_rows=[]
        for x in ctx["opportunities"]:
            payload=parse_json(x.get("payload")); r=payload.get("research",{}) if isinstance(payload,dict) else {}
            research_rows.append({"Market":str(x.get("market","")).upper(),"Symbol":x.get("symbol"),"Rating":r.get("research_rating","BUILDING"),"Research score":as_float(r.get("research_score")),"Technical":as_float(r.get("technical_score")),"Fundamentals":as_float(r.get("fundamental_score")),"Catalysts":as_float(r.get("catalyst_score")),"Valuation":as_float(r.get("valuation_score")),"Risk quality":as_float(r.get("risk_score")),"Evidence":r.get("evidence_quality","LIMITED")})
        st.dataframe(pd.DataFrame(research_rows),use_container_width=True,hide_index=True)
        symbol=st.selectbox("Open institutional research report",[x.get("symbol") for x in ctx["opportunities"]],key="research_lab_symbol")
        selected=next(x for x in ctx["opportunities"] if x.get("symbol")==symbol)
        payload=parse_json(selected.get("payload")); r=payload.get("research",{}) if isinstance(payload,dict) else {}
        a,b,c,d=st.columns(4); a.metric("Research rating",str(r.get("research_rating","BUILDING"))); b.metric("Research score",f"{as_float(r.get('research_score')):.1f}/100"); c.metric("Evidence quality",str(r.get("evidence_quality","LIMITED"))); d.metric("Trade decision",str(payload.get("recommendation","WATCH")))
        st.markdown(f'<div class="panel brief"><b>Investment thesis</b><br>{html.escape(str(r.get("thesis","Research is building.")))}<br><br>{html.escape(str(r.get("executive_summary","")))}</div>',unsafe_allow_html=True)
        lft,rgt=st.columns(2)
        with lft:
            st.markdown("### Bull case")
            for item in r.get("bull_case",[]) or []: st.success(str(item))
            st.markdown("### Catalysts")
            for item in r.get("catalysts",[]) or []: st.write(f"• {item}")
            st.markdown("### Confirmation conditions")
            for item in r.get("confirmation_conditions",[]) or []: st.write(f"• {item}")
        with rgt:
            st.markdown("### Bear case")
            for item in r.get("bear_case",[]) or []: st.warning(str(item))
            st.markdown("### Principal risks")
            for item in r.get("risks",[]) or []: st.write(f"• {item}")
            st.markdown("### Thesis invalidation")
            for item in r.get("invalidation_conditions",[]) or []: st.error(str(item))
        if r.get("data_gaps"):
            st.markdown("### Data gaps")
            for item in r.get("data_gaps",[]): st.info(str(item))

elif page == "Research Desk":
    st.markdown("## AI Research Desk")
    st.caption("Ask questions using the data already collected by your platform. The assistant is instructed not to invent missing live information.")
    symbols=sorted({str(x.get("symbol")) for x in ctx["signals"]+ctx["opportunities"] if x.get("symbol")})
    selected=st.selectbox("Research symbol",symbols or ["SPY"])
    question=st.text_area("Question",value=f"Give me the bull case, bear case, biggest risk, and what would confirm the setup for {selected}.")
    c1,c2=st.columns(2)
    if c1.button("Ask Oracle",use_container_width=True):
        if not openai_available(): st.warning("Add OPENAI_API_KEY to Railway to activate AI research.")
        else:
            relevant_signals=[x for x in ctx["signals"] if x.get("symbol")==selected][:10]
            relevant_opps=[x for x in ctx["opportunities"] if x.get("symbol")==selected][:5]
            with st.spinner("Building research answer…"):
                st.markdown(answer_market_question(question,{"platform_snapshot":snap.to_dict(),"symbol":selected,"signals":relevant_signals,"opportunities":relevant_opps,"events":ctx["events"][:20]}))
    if c2.button("Run Oracle Council",use_container_width=True):
        if not openai_available(): st.warning("Add OPENAI_API_KEY to Railway to activate the Oracle Council.")
        else:
            with st.spinner("Council specialists are reviewing the evidence…"):
                st.markdown(oracle_council(selected,{"signals":[x for x in ctx["signals"] if x.get("symbol")==selected][:10],"opportunities":[x for x in ctx["opportunities"] if x.get("symbol")==selected],"events":ctx["events"][:20]}))

elif page == "Risk & Alerts":
    st.markdown("## Risk Center")
    a,b,c=st.columns(3); a.metric("Platform risk",snap.risk_level); b.metric("Risk score",f"{snap.risk_score:.1f}/100"); c.metric("Active alerts",snap.active_alerts)
    for reason in ctx["risk_reasons"]: st.markdown(f'<div class="alert-card">{html.escape(reason)}</div>',unsafe_allow_html=True)
    st.markdown("### Alert Feed")
    if ctx["alerts"]:
        st.dataframe(pd.DataFrame(ctx["alerts"]),use_container_width=True,hide_index=True)
    else: st.success("No unacknowledged alerts are stored.")

elif page == "System Health":
    st.markdown("## System Health")
    tabs=st.tabs(["Providers","Workers","Database & Cache","Deployment Checklist"])
    with tabs[0]:
        d=pd.DataFrame(ctx["diagnostics"])
        st.dataframe(d,use_container_width=True,hide_index=True)
        st.metric("Configured provider coverage",f"{snap.provider_coverage:.0f}%")
    with tabs[1]:
        st.dataframe(pd.DataFrame(ctx["workers"]) if ctx["workers"] else pd.DataFrame([{"status":"No worker heartbeat stored"}]),use_container_width=True,hide_index=True)
    with tabs[2]:
        st.write("Migrations applied this launch:",migration_results or "Database already current")
        try: st.json(cache_stats())
        except Exception as exc: st.caption(f"Cache stats unavailable: {exc}")
    with tabs[3]:
        st.markdown("""1. Keep PostgreSQL plus the web, stock-worker, and crypto-worker services.  
2. Web start command: `python start_web.py`.  
3. Stock worker: `python stock_worker.py`.  
4. Crypto worker: `python crypto_worker.py`.  
5. Link the same `DATABASE_URL` to all three services.  
6. Add provider keys only in Railway Variables—never commit them to GitHub.  
7. Confirm both worker heartbeats turn online here before enabling real users.""")

st.divider()
st.caption("GARIBALDI MARKET ORACLE™ provides research and simulated decision support. It does not guarantee performance or replace licensed financial advice.")
