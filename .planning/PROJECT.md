# Dexcom Readings

## What This Is

A Dexcom CGM (Continuous Glucose Monitor) data polling and forwarding service. It fetches real-time glucose readings from the Dexcom Share API and forwards them to Nightscout (a diabetes management platform) with local CSV logging. Users are people with diabetes who want to replicate their CGM data for monitoring and analysis.

## Core Value

Reliable, continuous glucose data replication from Dexcom to Nightscout without data loss.

## Current State: v1.1 Reliability Improvements (Shipped)

**Shipped:** 2026-06-04

**Features:**
- Automatic Dexcom session reconnection when authentication expires
- Circuit breaker pattern for cascade failure protection
- HTTP 429 rate limit handling with Retry-After support
- Configurable connection and read timeouts
- Production-ready daemon support with PID file, syslog, SIGHUP rotation
- Google Python Style Guide compliant codebase

**Tech Stack:**
- Python 3.x with pydexcom 0.2.0 (pinned)
- ~2,555 lines of code
- 86 unit tests

## Requirements

### Validated

- ✓ Google Python Style Guide compliance — v1.0
- ✓ Configurable polling interval — v1.0
- ✓ Graceful shutdown (SIGTERM/SIGINT) — v1.0
- ✓ Exponential backoff retry logic — v1.0
- ✓ System daemon compatibility (PID, syslog, SIGHUP) — v1.0
- ✓ Systemd/launchd service templates — v1.0
- ✓ Automatic session reconnection — v1.1
- ✓ Circuit breaker failure protection — v1.1
- ✓ Rate limit handling (HTTP 429) — v1.1
- ✓ Configurable timeouts — v1.1

### Active

- [ ] Health check/status endpoint for monitoring (v2.0)
- [ ] Log rotation for CSV file growth (v2.0)
- [ ] Database storage option instead of CSV (v2.0)
- [ ] Structured logging (JSON format) (v2.0)
- [ ] Prometheus metrics export (v2.0)

### Out of Scope

- **Multi-user support** — Single-user polling service by design
- **Web UI** — Runs as daemon/background service
- **Real-time notifications** — Polling-based architecture, not event-driven
- **Database storage** — CSV is sufficient for current use case (may revisit in v2.0)
- **Migration away from pydexcom** — Will continue using third-party library

## Context

**Current Architecture:**
- Single-file monolithic script (`dexcom_readings.py`)
- Module-level state for session tracking and circuit breaker
- Environment variable configuration
- Python 3 with dependencies: pydexcom 0.2.0, requests

**Known Technical Debt:**
- Module-level mutable state complicates testing (acceptable for current scope)
- Single-file architecture (acceptable for ~2500 LOC)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use pydexcom library | Avoid implementing Dexcom API authentication flow | ✓ Stable |
| Pin pydexcom 0.2.0 | API stability, known behavior | ✓ Working |
| Environment variable config | 12-factor app principles | ✓ Working |
| CSV logging | Simple persistent storage without database dependency | ✓ Working |
| Three-state circuit breaker | Industry standard pattern for failure protection | ✓ Working |
| TimeoutSession injection | Enforce timeouts on pydexcom's internal requests | ✓ Working |

---

*Last updated: 2026-06-04 after v1.1 milestone*