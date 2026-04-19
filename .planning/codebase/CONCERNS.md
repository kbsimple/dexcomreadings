# Codebase Concerns

**Analysis Date:** 2026-04-19

## Tech Debt

**Test Mock Mismatch:**
- Issue: Test file mocks `builtins.print` but production code uses `logging` module
- Files: `dexcom_readings_test.py` lines 36-141
- Impact: Tests verify incorrect behavior - they assert `print()` calls that never occur
- Fix approach: Update tests to mock `logging` instead of `builtins.print`

**Global Mutable State:**
- Issue: `last_known_glucose_timestamp` is module-level global mutable state
- Files: `dexcom_readings.py` line 38, 119
- Impact: Makes testing difficult, requires `setUp()` to reset state; can cause issues if module imported multiple times
- Fix approach: Encapsulate state in a class or pass as parameter

**Missing Type Hints:**
- Issue: No function signatures include type hints
- Files: `dexcom_readings.py` all functions
- Impact: Reduced IDE support, harder to catch type errors
- Fix approach: Add type hints to all function signatures

**Inconsistent Exit Mechanism:**
- Issue: Tests patch `sys.exit` but production uses `exit()` (line 124)
- Files: `dexcom_readings.py` line 124, `dexcom_readings_test.py` lines 37-84
- Impact: Tests may not properly validate exit behavior
- Fix approach: Use `sys.exit(1)` consistently in production code

## Known Bugs

**Test DateTime Mocking Issue:**
- Issue: Test patches `datetime.datetime` but code imports `datetime` module and calls `datetime.datetime.utcnow()`
- Files: `dexcom_readings_test.py` lines 204-215, 248-259
- Impact: Mock may not work correctly because the patch target doesn't match the import structure
- Trigger: Running tests with `python -m pytest` or `python dexcom_readings_test.py`
- Fix approach: Patch `dexcom_readings.datetime.datetime` or restructure the mock

**CSV Header Race Condition:**
- Issue: `if __name__ == "__main__"` block creates CSV file without atomic check
- Files: `dexcom_readings.py` lines 194-198
- Impact: If multiple processes start simultaneously, header row may be duplicated
- Workaround: Currently only single process runs
- Fix approach: Use file locking or atomic file creation

## Security Considerations

**Plaintext API Secret in Headers:**
- Risk: Nightscout API secret sent as plaintext in `api-secret` header
- Files: `dexcom_readings.py` lines 102-104
- Current mitigation: HTTPS assumed (enforced by Nightscout servers)
- Recommendations: Consider using hashed secret if Nightscout supports it; document security requirement for HTTPS

**Credential Handling:**
- Risk: Environment variables may be logged or visible in process listings
- Files: `dexcom_readings.py` lines 10-18
- Current mitigation: Using environment variables is industry standard
- Recommendations: Document that credentials should not be logged; ensure log statements don't include credentials (line 46 logs username - should mask)

**Logging Username:**
- Risk: Username logged in plaintext at INFO level
- Files: `dexcom_readings.py` line 46-47
- Current mitigation: None
- Recommendations: Mask or redact username in logs, or use placeholder

## Performance Bottlenecks

**Synchronous Blocking Sleep:**
- Problem: 60-second blocking sleep prevents graceful shutdown
- Files: `dexcom_readings.py` line 191
- Cause: `time.sleep(POLLING_INTERVAL_SECONDS)` blocks entire thread
- Improvement path: Use interruptible wait or signal handling

**No Retry Logic for API Calls:**
- Problem: Transient network failures cause immediate failure without retry
- Files: `dexcom_readings.py` lines 62-71, 82-116
- Cause: Single try-except with no retry mechanism
- Improvement path: Implement exponential backoff retry for transient failures

## Fragile Areas

**Infinite Loop with No Graceful Exit:**
- Files: `dexcom_readings.py` lines 135-191
- Why fragile: `while True` with only `time.sleep()` break; no signal handlers
- What breaks: No way to cleanly close connections or flush data on SIGTERM/SIGINT
- Safe modification: Add signal handlers for graceful shutdown
- Test coverage: Tests use `KeyboardInterrupt` side effect to break loop (lines 200-242)

**Module-Level Configuration:**
- Files: `dexcom_readings.py` lines 10-23
- Why fragile: Configuration loaded at import time; cannot be changed after import
- What breaks: Testing requires patching module globals
- Safe modification: Extract configuration into a function or class
- Test coverage: Tests patch globals (lines 42-43, 78-80)

**Missing Dependency Specification:**
- Files: No `requirements.txt` or `pyproject.toml`
- Why fragile: External dependencies (`pydexcom`, `requests`) not documented
- What breaks: New installations won't know what to install
- Safe modification: Create `requirements.txt` with pinned versions
- Test coverage: N/A

## Scaling Limits

**Single-Threaded Polling:**
- Current capacity: One reading per polling interval (default 60 seconds)
- Limit: Cannot handle multiple users or data sources
- Scaling path: Would require significant refactoring to class-based design

**CSV File Growth:**
- Current capacity: Unlimited file growth
- Limit: No rotation or archival strategy
- Scaling path: Implement log rotation or database storage

## Dependencies at Risk

**pydexcom Dependency:**
- Risk: Third-party library for Dexcom API; no version pinning
- Impact: Breaking changes in pydexcom could break the application
- Migration plan: Pin version in requirements.txt; monitor library changelog

**requests Dependency:**
- Risk: Used for Nightscout uploads; no version pinning
- Impact: Generally stable but API changes could cause issues
- Migration plan: Pin version; consider using urllib3 directly for fewer dependencies

## Missing Critical Features

**No Graceful Shutdown:**
- Problem: No signal handlers for SIGTERM/SIGINT
- Blocks: Clean application exit, proper resource cleanup
- Impact: May lose last reading or corrupt CSV on forced termination

**No Configuration Validation:**
- Problem: Missing required env vars only checked on use
- Files: `dexcom_readings.py` lines 42-44, 84-85
- Blocks: Early failure detection, better error messages
- Impact: Application fails after startup instead of immediately

**No Health Check/Status Endpoint:**
- Problem: No way to verify application is running correctly
- Blocks: Monitoring, alerting on failures
- Impact: Silent failures undetected until logs checked

## Test Coverage Gaps

**Print Mocking vs Logging:**
- What's not tested: Actual logging output (tests mock `print` not `logging`)
- Files: `dexcom_readings_test.py` all test methods
- Risk: Logging statements not verified; could be malformed
- Priority: High - tests are effectively broken

**Nightscout Upload Integration:**
- What's not tested: `upload_to_nightscout()` function
- Files: `dexcom_readings.py` lines 82-116
- Risk: HTTP requests, error handling, data formatting untested
- Priority: High

**CSV Writing on Existing File:**
- What's not tested: Race condition when file doesn't exist during check but created before write
- Files: `dexcom_readings.py` lines 75-80
- Risk: Header duplication possible
- Priority: Medium

**Error Paths:**
- What's not tested: Network timeout, invalid responses, rate limiting
- Files: `dexcom_readings.py` lines 107-116
- Risk: Errors not handled gracefully in production
- Priority: Medium

---

*Concerns audit: 2026-04-19*