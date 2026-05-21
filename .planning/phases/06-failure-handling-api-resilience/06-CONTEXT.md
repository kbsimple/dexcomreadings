# Phase 6: Failure Handling & API Resilience - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous execution)

<domain>
## Phase Boundary

Implement circuit breaker pattern for repeated API failures and add configurable timeouts. The service handles failures gracefully with automatic recovery.

</domain>

<decisions>
## Implementation Decisions

### Circuit Breaker Pattern
- **D-01:** Implement circuit breaker with three states: CLOSED (normal), OPEN (failing), HALF_OPEN (testing)
- **D-02:** Open circuit after N consecutive failures (configurable via env var)
- **D-03:** Auto-recover after cooldown period (configurable via env var)
- **D-04:** In HALF_OPEN state, allow one test request; success → CLOSED, failure → OPEN

### Failure Thresholds
- **D-05:** Use environment variables: CIRCUIT_BREAKER_FAILURE_THRESHOLD (default: 5)
- **D-06:** Use CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS (default: 60)
- **D-07:** Log circuit state transitions at WARNING level

### API Timeouts
- **D-08:** Add DEXCOM_CONNECTION_TIMEOUT_SECONDS env var (default: 30)
- **D-09:** Add DEXCOM_READ_TIMEOUT_SECONDS env var (default: 30)
- **D-10:** Pass timeouts to pydexcom client or requests library

### Rate Limit Handling
- **D-11:** Detect rate limit responses (HTTP 429) and back off
- **D-12:** Use existing retry_with_backoff with extended delay for rate limits
- **D-13:** Log rate limit encounters at WARNING level

### Claude's Discretion
- Circuit breaker tracks failures globally (module-level state like session resilience)
- Integration point: retry_with_backoff already catches exceptions; add circuit state check
- Tests should verify circuit opens/closes correctly

</decisions>

<canonical_refs>
## Canonical References
- `dexcom_readings.py` — Main implementation (modified in Phase 5)
- `dexcom_readings_test.py` — Test patterns to follow

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (from Phase 5)
- `retry_with_backoff()` — Extended to catch pydexcom exceptions
- `should_attempt_reauth()`, `reset_failure_counter()` — Failure tracking pattern
- Module-level state pattern established in Phase 5

### Integration Points
- `retry_with_backoff()` — Add circuit breaker check before retrying
- `initialize_dexcom_client()` — Add timeout configuration
- Main loop — Check circuit state before making API calls

</code_context>

<deferred>
## Deferred Ideas
None — discussion stayed within phase scope.
</deferred>

---
*Phase: 06-failure-handling-api-resilience*
*Context gathered: 2026-05-21*