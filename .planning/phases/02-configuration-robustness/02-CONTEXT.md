# Phase 2: Configuration & Robustness - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Add configurable polling interval, graceful shutdown handling, and retry logic with exponential backoff. This is a refactoring-only phase — no functionality changes to the core polling behavior.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key constraints from requirements:
- POLLING_INTERVAL_SECONDS should be configurable via environment variable
- Graceful shutdown must complete current polling cycle before exiting
- Retry logic should use exponential backoff for transient failures
- All changes preserve existing behavior

### Graceful Shutdown Pattern
Use Python's `signal` module to register handlers for SIGTERM and SIGINT. Set a flag that the main loop checks to exit cleanly after completing the current cycle.

### Retry Pattern
Implement retry logic with exponential backoff (start at 1s, double each retry, max 30s) for network API calls. Distinguish between transient failures (retry) and permanent failures (log and continue).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `dexcom_readings.py` — main script with polling loop
- `initialize_dexcom_client()` — Dexcom authentication
- `get_latest_glucose_reading()` — fetch glucose data
- `upload_to_nightscout()` — Nightscout API upload
- `write_to_csv()` — local logging

### Established Patterns
- Environment variable configuration via `os.environ.get()`
- Try-except with logging, return None on failure
- Polling loop with `time.sleep()`
- Single-threaded execution

### Integration Points
- Dexcom Share API via pydexcom library
- Nightscout REST API via requests library
- Local CSV file for logging

</code_context>

<specifics>
## Specific Ideas

1. **POLLING_INTERVAL_SECONDS**: Add environment variable with default of 60 seconds
2. **Signal handlers**: Register SIGTERM/SIGINT handlers that set a shutdown flag
3. **Exponential backoff**: Create a retry decorator or helper function for API calls
4. **Clean shutdown**: Check shutdown flag in main loop, exit after current cycle completes

</specifics>

<deferred>
## Deferred Ideas

None — infrastructure phase.

</deferred>