---
phase: 6
slug: failure-handling-api-resilience
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-04
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | unittest (Python standard library) |
| **Config file** | none — tests in dexcom_readings_test.py |
| **Quick run command** | `python -m unittest dexcom_readings_test -v` |
| **Full suite command** | `python -m unittest dexcom_readings_test -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m unittest dexcom_readings_test -v`
- **After every plan wave:** Run `python -m unittest dexcom_readings_test -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | FAIL-01 | — | Circuit opens after threshold failures | unit | `python -m unittest dexcom_readings_test.TestCircuitBreaker.test_circuit_opens_after_failures -v` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | FAIL-02 | — | Circuit auto-recovers after cooldown | unit | `python -m unittest dexcom_readings_test.TestCircuitBreaker.test_circuit_recovers_after_timeout -v` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | FAIL-03 | — | Configurable thresholds via env vars | unit | `python -m unittest dexcom_readings_test.TestCircuitBreaker.test_configurable_thresholds -v` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 1 | API-01 | — | Handle HTTP 429 with backoff | unit | `python -m unittest dexcom_readings_test.TestRateLimitHandling.test_429_triggers_backoff -v` | ❌ W0 | ⬜ pending |
| 06-03-01 | 03 | 1 | API-02 | — | Connection timeout configurable | unit | `python -m unittest dexcom_readings_test.TestTimeoutSession.test_connection_timeout -v` | ❌ W0 | ⬜ pending |
| 06-03-02 | 03 | 1 | API-03 | — | Read timeout configurable | unit | `python -m unittest dexcom_readings_test.TestTimeoutSession.test_read_timeout -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `TestCircuitBreaker` class in `dexcom_readings_test.py` — unit tests for circuit breaker state machine
- [ ] `TestRateLimitHandling` class in `dexcom_readings_test.py` — unit tests for HTTP 429 handling
- [ ] `TestTimeoutSession` class in `dexcom_readings_test.py` — unit tests for TimeoutSession class
- [ ] Integration with existing `TestSessionResilience` class pattern

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | — | All phase behaviors have automated verification |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending