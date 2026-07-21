# GARIBALDI MARKET ORACLE V20.1 — Production Audit

This maintenance release hardens V20 without adding another decision engine.

## Corrections

- Removed the obsolete generic Procfile worker process.
- Standardized worker heartbeat keys to `cash` and `crypto`.
- Added safe migration repair for legacy `stock` heartbeat rows.
- Rebuilt the health check around both canonical workers.
- Prevented `stopped` and unknown worker states from being reported online.
- Aligned Autonomous Intelligence with the same strict worker-state rules.
- Corrected the in-app Railway deployment checklist.
- Added production regression tests for all fixes.

This application remains a simulated research and decision-support platform.
