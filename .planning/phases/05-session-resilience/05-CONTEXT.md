# Phase 5: Session Resilience - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous execution)

<domain>
## Phase Boundary

Service automatically recovers from Dexcom session expiration without manual intervention. The service continues polling and forwarding glucose data even when the Dexcom API session expires, detecting expiration and re-authenticating transparently.

</domain>

<decisions>
## Implementation Decisions

### Session Expiration Detection
- **D-01:** Detect session expiration via API response patterns — when `get_current_glucose_reading()` returns None or raises an authentication-related exception after previously working, treat as potential session expiration
- **D-02:** Use consecutive failure count threshold — after N consecutive authentication failures, trigger re-authentication (distinguishes transient errors from session expiration)
- **D-03:** Log session expiration detection clearly — use WARNING level for first detection, ERROR for sustained issues

### Re-authentication Strategy
- **D-04:** Re-use existing `initialize_dexcom_client()` function for re-authentication — it already handles credential retrieval and client creation
- **D-05:** Store credentials in memory at startup (already done via environment variables) — no new credential storage needed
- **D-06:** On re-authentication failure, retry with exponential backoff — same pattern as existing `retry_with_backoff()` for network failures
- **D-07:** After successful re-authentication, continue polling from where we left off — no data loss, timestamp tracking already in place

### Recovery Behavior
- **D-08:** Log re-authentication attempts clearly — "Session expired, re-authenticating..." and "Re-authentication successful" messages
- **D-09:** No readings are lost during recovery — the `last_known_glucose_timestamp` tracking prevents duplicate uploads, and the retry logic handles gaps
- **D-10:** Continue polling during recovery — don't exit the main loop, just retry authentication within the loop

### Claude's Discretion
- Exact threshold values for consecutive failures should be configurable via environment variables (FAIL-03 in Phase 6)
- Logging level and format follow existing conventions (logging module, structured messages)
- The pydexcom library behavior should be tested to understand what exceptions indicate session expiration

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Codebase
- `dexcom_readings.py` — Main application file containing all current implementation
- `dexcom_readings_test.py` — Existing test patterns to follow

### External Documentation
- pydexcom library documentation (for understanding session behavior and exceptions)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `initialize_dexcom_client()` — Already handles authentication; can be called again for re-authentication
- `retry_with_backoff()` — Existing retry logic with exponential backoff; can be adapted for re-authentication
- `last_known_glucose_timestamp` — Tracks last reading to prevent duplicates; already handles gaps

### Established Patterns
- Global `shutdown_requested` flag for clean termination — pattern exists for signal handling
- Logging via `logging` module with structured format — follow this pattern
- Environment variable configuration — all thresholds should be configurable
- Functions return `None` on failure — consistent error handling pattern

### Integration Points
- Main loop at `_run_main_loop()` — where session expiration detection should be added
- `get_latest_glucose_reading()` — where we detect auth failures
- `initialize_dexcom_client()` — called for re-authentication

</code_context>

<specifics>
## Specific Ideas

- Session expiration typically manifests as authentication errors from the Dexcom API
- The pydexcom library may raise specific exceptions for session expiration — need to research
- Should distinguish between "session expired" and "network error" — different recovery paths
- Re-authentication should be transparent to the user — no manual intervention needed

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-session-resilience*
*Context gathered: 2026-05-21*