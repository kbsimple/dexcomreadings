# Dexcom Readings

## What This Is

A Dexcom CGM (Continuous Glucose Monitor) data polling and forwarding service. It fetches real-time glucose readings from the Dexcom Share API and forwards them to Nightscout (a diabetes management platform) with local CSV logging. Users are people with diabetes who want to replicate their CGM data for monitoring and analysis.

## Core Value

Reliable, continuous glucose data replication from Dexcom to Nightscout without data loss.

## Requirements

### Validated

- ✓ Dexcom Share API authentication with region support (US/OUS) — existing
- ✓ Polling loop with configurable interval — existing
- ✓ Local CSV logging of all readings — existing
- ✓ Nightscout API upload — existing
- ✓ Graceful error handling (continue on failures) — existing

### Active

- [ ] Add `requirements.txt` with pinned dependencies (`pydexcom`, `requests`)
- [ ] Add `README.md` with installation, configuration, and usage documentation
- [ ] Make polling interval configurable via environment variable
- [ ] Implement graceful shutdown with signal handlers (SIGTERM/SIGINT)
- [ ] Fix test suite — update mocks to match production logging (tests mock `print` but code uses `logging`)
- [ ] Add retry logic with exponential backoff for transient network failures
- [ ] Apply Google Python Style Guide compliance (docstrings, type hints, naming conventions, main function)

### Out of Scope

- Multi-user support — single-user polling service
- Database storage — CSV is sufficient for current use case
- Web UI — runs as daemon/background service
- Real-time notifications — polling-based architecture

## Context

**Current Architecture:**
- Single-file monolithic script (`dexcom_readings.py`)
- Procedural design with global state (`last_known_glucose_timestamp`)
- Environment variable configuration
- Python 3 with dependencies: `pydexcom`, `requests`

**Known Issues from Codebase Analysis:**
- Test suite mocks `builtins.print` but production uses `logging` module
- Module-level global mutable state complicates testing
- No type hints on function signatures
- Inconsistent exit mechanism (`exit()` vs `sys.exit()`)
- No graceful shutdown handling
- No retry logic for API calls
- Username logged in plaintext at INFO level

## Constraints

- **Tech Stack:** Python 3, pydexcom library, requests library
- **Compatibility:** Must work with existing Dexcom Share API and Nightscout API
- **Dependencies:** Third-party `pydexcom` library (no version currently pinned)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use pydexcom library | Avoid implementing Dexcom API authentication flow | — Pending |
| Environment variable configuration | Follow 12-factor app principles, avoid secrets in code | — Pending |
| CSV logging | Simple persistent storage without database dependency | — Pending |

---
*Last updated: 2026-04-19 after initialization*

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state