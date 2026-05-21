# Phase 5: Session Resilience - Research

**Researched:** 2026-05-21
**Domain:** Python, pydexcom library, session management, error handling
**Confidence:** HIGH

## Summary

The pydexcom library (v0.5.1) already implements automatic session re-authentication internally. The `get_glucose_readings()` method catches `SessionError` and retries with a new session ID. However, the application still needs to handle persistent authentication failures (`AccountError`), track consecutive failures for pattern detection, and add visibility/logging when re-authentication occurs.

**Primary recommendation:** Extend `retry_with_backoff()` to catch pydexcom exceptions (`DexcomError`), add consecutive failure tracking with configurable thresholds, and implement logging for session recovery events. The library handles single-session expiration transparently; the application must handle persistent failures.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Detect session expiration via API response patterns — when `get_current_glucose_reading()` returns None or raises an authentication-related exception after previously working, treat as potential session expiration
- **D-02:** Use consecutive failure count threshold — after N consecutive authentication failures, trigger re-authentication (distinguishes transient errors from session expiration)
- **D-03:** Log session expiration detection clearly — use WARNING level for first detection, ERROR for sustained issues
- **D-04:** Re-use existing `initialize_dexcom_client()` function for re-authentication — it already handles credential retrieval and client creation
- **D-05:** Store credentials in memory at startup (already done via environment variables) — no new credential storage needed
- **D-06:** On re-authentication failure, retry with exponential backoff — same pattern as existing `retry_with_backoff()` for network failures
- **D-07:** After successful re-authentication, continue polling from where we left off — no data loss, timestamp tracking already in place
- **D-08:** Log re-authentication attempts clearly — "Session expired, re-authenticating..." and "Re-authentication successful" messages
- **D-09:** No readings are lost during recovery — the `last_known_glucose_timestamp` tracking prevents duplicate uploads, and the retry logic handles gaps
- **D-10:** Continue polling during recovery — don't exit the main loop, just retry authentication within the loop

### Claude's Discretion

- Exact threshold values for consecutive failures should be configurable via environment variables (FAIL-03 in Phase 6)
- Logging level and format follow existing conventions (logging module, structured messages)
- The pydexcom library behavior should be tested to understand what exceptions indicate session expiration

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SESS-01 | Service automatically reconnects when Dexcom session expires | pydexcom's `get_glucose_readings()` already handles single-session recovery internally; extend to track consecutive failures and add visibility |
| SESS-02 | Service re-authenticates without manual intervention | Re-use `initialize_dexcom_client()` for client recreation; track AccountError vs SessionError distinction |

</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydexcom | 0.5.1 | Dexcom Share API client | Only library for Dexcom integration; already in use |
| requests | 2.31.0 | HTTP client | Transitive dependency via pydexcom; already in use |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| logging | stdlib | Application logging | Already used throughout; follow existing patterns |
| time | stdlib | Sleep/retry delays | Already used in `retry_with_backoff()` |

### Version Discrepancy

**IMPORTANT:** `requirements.txt` pins `pydexcom==0.46.0` but installed version is `0.5.1`. This discrepancy should be resolved — either update requirements.txt to match installed version (recommended, as 0.5.1 has better error handling), or downgrade to match pinned version.

**Recommendation:** Update `requirements.txt` to `pydexcom==0.5.1` before implementation. [VERIFIED: pip show]

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pydexcom | Direct API calls | Higher maintenance, must implement session management from scratch; pydexcom already handles session recovery |
| Custom session wrapper | Extend pydexcom | Unnecessary — library already exposes the hooks needed |

**Installation:**
```bash
pip install pydexcom==0.5.1 requests==2.31.0
```

## Architecture Patterns

### pydexcom Exception Hierarchy [VERIFIED: source code analysis]

```
DexcomError (base)
├── AccountError — Authentication failures (unrecoverable without user action)
│   ├── FAILED_AUTHENTICATION — Invalid credentials
│   └── MAX_ATTEMPTS — Account locked due to too many attempts
├── SessionError — Session issues (recoverable via re-auth)
│   ├── NOT_FOUND — Session ID not found
│   └── INVALID — Session expired or timed out
├── ArgumentError — Invalid parameters (programming error)
│   └── Various validation errors
└── ServerError — API issues (potentially transient)
    ├── INVALID_JSON — Malformed response
    ├── UNKNOWN_CODE — Unrecognized error code
    └── UNEXPECTED — Other server issues
```

### pydexcom Built-in Session Recovery [VERIFIED: pydexcom/dexcom.py lines 281-306]

```python
def get_glucose_readings(self, minutes: int = MAX_MINUTES, max_count: int = MAX_MAX_COUNT) -> list[GlucoseReading]:
    """Get glucose readings with automatic session recovery."""
    json_glucose_readings: list[dict[str, Any]] = []

    try:
        self._validate_session_id()
        json_glucose_readings = self._get_glucose_readings(minutes, max_count)
    except SessionError:
        # Attempt to update expired session ID — SINGLE RETRY ONLY
        self._get_session()
        json_glucose_readings = self._get_glucose_readings(minutes, max_count)

    return [GlucoseReading(json_reading) for json_reading in json_glucose_readings]
```

**Key insight:** The library handles single-session expiration automatically. The application must handle:
1. Persistent failures (when re-auth also fails)
2. `AccountError` exceptions (credentials invalid)
3. Network-level failures (already handled by `retry_with_backoff()`)
4. Consecutive failure patterns (to detect systemic issues)

### Current Error Handling Flow [VERIFIED: dexcom_readings.py analysis]

```
get_latest_glucose_reading(dexcom_client)
├── Calls: retry_with_backoff(fetch_reading)
│   ├── Catches: requests.exceptions.RequestException
│   ├── Catches: ConnectionError
│   ├── Catches: TimeoutError
│   └── Returns: None on failure (logs error)
├── Does NOT catch: DexcomError subclasses (SessionError, AccountError)
└── Returns: GlucoseReading | None
```

**Gap identified:** `retry_with_backoff()` catches network exceptions but NOT pydexcom exceptions. A `SessionError` or `AccountError` from pydexcom will propagate up uncaught.

### Recommended Recovery Pattern

```python
# Extend retry_with_backoff to handle pydexcom exceptions
def retry_with_backoff(func, max_attempts=3, initial_delay=1, max_delay=30):
    """Execute function with exponential backoff for transient failures."""
    delay = initial_delay
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return func()
        except (
            requests.exceptions.RequestException,
            ConnectionError,
            TimeoutError,
            SessionError,      # Session expired — pydexcom handles, but propagate for logging
            ServerError,        # Transient API issues
        ) as e:
            last_exception = e
            if attempt < max_attempts - 1:
                logging.warning(f"Attempt {attempt + 1}/{max_attempts} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
                delay = min(delay * 2, max_delay)
            else:
                logging.error(f"All {max_attempts} attempts failed. Last error: {e}")
        except AccountError as e:
            # Unrecoverable — credentials invalid
            logging.error(f"Authentication failed: {e}")
            raise  # Propagate for caller to handle (exit or alert)

    return None
```

### Pattern 1: Consecutive Failure Tracking

**What:** Track consecutive failures across polling cycles to detect persistent issues vs transient ones.

**When to use:** When distinguishing between temporary network issues and systemic problems (expired credentials, service outage).

**Example:**
```python
# Configuration (make configurable per D-02)
MAX_CONSECUTIVE_FAILURES = int(os.environ.get("DEXCOM_MAX_FAILURES", "3"))
FAILURE_RESET_AFTER_SECONDS = int(os.environ.get("DEXCOM_FAILURE_RESET", "300"))  # 5 minutes

# State tracking
consecutive_failures = 0
last_failure_time = None

def handle_reading_failure(error: Exception) -> bool:
    """Returns True if should attempt re-auth, False if should exit."""
    global consecutive_failures, last_failure_time

    now = time.time()

    # Reset counter if enough time has passed
    if last_failure_time and (now - last_failure_time) > FAILURE_RESET_AFTER_SECONDS:
        consecutive_failures = 0

    consecutive_failures += 1
    last_failure_time = now

    if isinstance(error, AccountError):
        logging.error("Authentication failed — credentials may be invalid")
        return False  # Exit

    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
        logging.warning(f"Consecutive failures ({consecutive_failures}) exceed threshold")
        return True  # Attempt re-auth

    return True  # Continue trying
```

### Pattern 2: Client Recreation for Recovery

**What:** Create a new Dexcom client instance when persistent failures indicate session issues.

**When to use:** When `initialize_dexcom_client()` needs to be called again for re-authentication.

**Example:**
```python
def reinitialize_client() -> Optional[Dexcom]:
    """Attempt to create a new Dexcom client for re-authentication."""
    logging.warning("Session expired, re-authenticating...")
    new_client = initialize_dexcom_client()
    if new_client:
        logging.info("Re-authentication successful")
    else:
        logging.error("Re-authentication failed")
    return new_client
```

### Anti-Patterns to Avoid

- **Catching all exceptions:** Don't use bare `except:` or `except Exception:` — let unexpected errors surface
- **Infinite retry loops:** Always have a maximum retry count to prevent hangs
- **Ignoring AccountError:** This exception indicates credentials are invalid; re-trying won't help
- **Re-initializing on every failure:** The library already handles single-session recovery; only re-initialize after consecutive failures

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session re-authentication | Custom session management | pydexcom's built-in retry | Library already catches SessionError and retries |
| Exponential backoff | New retry logic | Extend existing `retry_with_backoff()` | Pattern already exists and works well |
| Credential storage | Custom credential cache | Environment variables | Already implemented; D-05 confirms this |
| Timestamp tracking | New deduplication | Existing `last_known_glucose_timestamp` | Already tracks last reading to prevent duplicates |

**Key insight:** The implementation is primarily about *extending* existing patterns and adding visibility/logging, not building new session management from scratch.

## Runtime State Inventory

> This phase does NOT involve rename/refactor/migration. Step 2.5 SKIPPED.

## Common Pitfalls

### Pitfall 1: Over-Engineering Session Recovery

**What goes wrong:** Implementing complex session management when pydexcom already handles it.

**Why it happens:** Developers assume they need to manage sessions themselves without checking library capabilities.

**How to avoid:** Leverage pydexcom's built-in `SessionError` handling. Only add:
- Logging for visibility
- Consecutive failure tracking for pattern detection
- Client recreation for persistent failures

**Warning signs:** Writing code that catches every exception and retries; creating session state tracking when library does it internally.

### Pitfall 2: Catching AccountError and Retrying

**What goes wrong:** Retrying after `AccountError` when credentials are invalid, leading to infinite failure loops.

**Why it happens:** Treating all exceptions as transient.

**How to avoid:** `AccountError` is unrecoverable without user action. Log and exit or alert.

**Warning signs:** Code that retries on all pydexcom exceptions without distinguishing types.

### Pitfall 3: Missing pydexcom Exceptions in retry_with_backoff

**What goes wrong:** `SessionError` or `AccountError` propagates up and crashes the service.

**Why it happens:** `retry_with_backoff()` only catches network exceptions (`requests.exceptions.RequestException`, `ConnectionError`, `TimeoutError`).

**How to avoid:** Extend the exception tuple to include pydexcom exceptions (`SessionError`, `ServerError`).

**Warning signs:** Service crashes with `SessionError: Session ID not found` in logs.

### Pitfall 4: Version Mismatch Between requirements.txt and Installed

**What goes wrong:** Production installs older version with different error handling.

**Why it happens:** requirements.txt pins 0.46.0 but development uses 0.5.1.

**How to avoid:** Update requirements.txt to match installed version before deployment.

**Warning signs:** Different exception types or behaviors in production vs development.

## Code Examples

### Extended retry_with_backoff with pydexcom Exceptions

```python
# Source: Existing retry_with_backoff() pattern + pydexcom error hierarchy
from pydexcom.errors import AccountError, DexcomError, SessionError, ServerError

def retry_with_backoff(
        func: Any,
        max_attempts: int = RETRY_MAX_ATTEMPTS,
        initial_delay: float = RETRY_INITIAL_DELAY_SECONDS,
        max_delay: float = RETRY_MAX_DELAY_SECONDS) -> Optional[Any]:
    """Executes a function with exponential backoff retry for transient failures.

    Retries on network errors and recoverable pydexcom errors (SessionError,
    ServerError). Propagates AccountError (invalid credentials) to caller.

    Args:
        func: A callable to execute.
        max_attempts: Maximum retry attempts.
        initial_delay: Initial delay before first retry (seconds).
        max_delay: Maximum delay between retries (seconds).

    Returns:
        Function result on success, None if all attempts fail.

    Raises:
        AccountError: If authentication credentials are invalid.
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return func()
        except AccountError as e:
            # Unrecoverable — credentials invalid
            logging.error(f"Authentication failed: {e}")
            raise  # Propagate to caller
        except (requests.exceptions.RequestException,
                ConnectionError,
                TimeoutError,
                SessionError,
                ServerError) as e:
            last_exception = e
            if attempt < max_attempts - 1:
                logging.warning(
                    f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)
                delay = min(delay * 2, max_delay)
            else:
                logging.error(
                    f"All {max_attempts} attempts failed. Last error: {e}"
                )

    return None
```

### Consecutive Failure Detection Pattern

```python
# Source: Pattern based on D-02 and D-06 from CONTEXT.md

# Configuration constants (can be made configurable via env vars)
MAX_CONSECUTIVE_FAILURES = int(os.environ.get("DEXCOM_MAX_FAILURES", "3"))
REAUTH_COOLDOWN_SECONDS = int(os.environ.get("DEXCOM_REAUTH_COOLDOWN", "60"))

# Module-level state
_consecutive_failures = 0
_last_failure_time: Optional[float] = None
_last_reauth_time: Optional[float] = None

def should_attempt_reauth(error: Exception) -> bool:
    """Determine if re-authentication should be attempted.

    Args:
        error: The exception that caused the failure.

    Returns:
        True if re-authentication should be attempted.
        False if the error is unrecoverable (AccountError).

    Raises:
        No exceptions raised.
    """
    global _consecutive_failures, _last_failure_time, _last_reauth_time

    now = time.time()

    # AccountError is unrecoverable
    if isinstance(error, AccountError):
        logging.error("Authentication credentials invalid — manual intervention required")
        return False

    # Update failure tracking
    _consecutive_failures += 1
    _last_failure_time = now

    # Check if we've exceeded threshold
    if _consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
        # Rate-limit re-auth attempts
        if _last_reauth_time and (now - _last_reauth_time) < REAUTH_COOLDOWN_SECONDS:
            logging.warning(
                f"Consecutive failures: {_consecutive_failures}, "
                f"but re-auth cooldown not elapsed"
            )
            return False

        logging.warning(
            f"Consecutive failures ({_consecutive_failures}) exceed threshold "
            f"({MAX_CONSECUTIVE_FAILURES}) — attempting re-authentication"
        )
        return True

    return False

def reset_failure_counter() -> None:
    """Reset consecutive failure counter after successful operation."""
    global _consecutive_failures, _last_failure_time
    _consecutive_failures = 0
    _last_failure_time = None

def record_reauth_attempt() -> None:
    """Record that a re-authentication attempt was made."""
    global _last_reauth_time
    _last_reauth_time = time.time()
```

### Main Loop Integration

```python
# Source: Pattern for integrating session resilience into _run_main_loop()

def _run_main_loop() -> None:
    """Internal main loop with session resilience."""
    setup_logging()
    last_known_glucose_timestamp = None
    dexcom_client = initialize_dexcom_client()

    if not dexcom_client:
        logging.error("Exiting due to Dexcom client initialization failure.")
        sys.exit(1)

    while not shutdown_requested:
        check_and_reopen_logs()
        check_timestamp_utc = datetime.datetime.utcnow()

        try:
            current_bg = get_latest_glucose_reading(dexcom_client)

            if current_bg:
                # Success — reset failure counter
                reset_failure_counter()
                # ... process reading ...

        except AccountError:
            logging.error("Authentication failed — exiting")
            sys.exit(1)

        except (SessionError, ServerError) as e:
            if should_attempt_reauth(e):
                logging.info("Attempting to re-authenticate...")
                new_client = initialize_dexcom_client()
                if new_client:
                    dexcom_client = new_client
                    record_reauth_attempt()
                    logging.info("Re-authentication successful")
                else:
                    logging.error("Re-authentication failed")
            # Continue polling — failure already logged

        time.sleep(POLLING_INTERVAL_SECONDS)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Catch all exceptions | Distinguish by exception type | pydexcom 0.5.x | AccountError is unrecoverable; SessionError is recoverable |
| Manual session management | Library handles session recovery | pydexcom 0.5.x | Built-in `SessionError` catch-and-retry in `get_glucose_readings()` |
| No failure tracking | Consecutive failure counter | Phase 5 | Pattern detection to distinguish transient vs systemic issues |

**Deprecated/outdated:**
- **pydexcom 0.4.x:** Had different error handling; upgrade to 0.5.1 for better session recovery

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | pydexcom 0.5.1's built-in session recovery works correctly | Standard Stack | If library has bugs, application recovery may not work |
| A2 | AccountError always means credentials are invalid | Architecture Patterns | Could miss cases where server temporarily returns auth errors |
| A3 | Network errors and pydexcom exceptions are mutually exclusive | Code Examples | Both could occur simultaneously in rare cases |
| A4 | Environment variables are already set for DEXCOM_MAX_FAILURES defaults | Code Examples | May need to add defaults in code if not configurable |

## Open Questions

1. **Should requirements.txt be updated to pydexcom 0.5.1?**
   - What we know: Installed version is 0.5.1, requirements.txt pins 0.46.0
   - What's unclear: Whether 0.46.0 was intentional for compatibility
   - Recommendation: Update to 0.5.1 — better error handling, type hints, session recovery

2. **Should consecutive failure threshold be configurable via environment variable?**
   - What we know: D-02 suggests configurable thresholds; FAIL-03 in Phase 6 addresses this
   - What's unclear: Whether Phase 5 should implement the configuration or leave for Phase 6
   - Recommendation: Implement with sensible defaults (3 failures), leave config for Phase 6

3. **Should re-authentication logging include the reason (SessionError type)?**
   - What we know: SessionError has NOT_FOUND and INVALID variants
   - What's unclear: Whether this detail is useful for operators
   - Recommendation: Log the enum value for debugging visibility

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | Yes | 3.9.6 | — |
| pydexcom | Dexcom API | Yes | 0.5.1 | — |
| requests | HTTP client | Yes | 2.31.0 | — |

**Missing dependencies with no fallback:**
- None detected

**Version discrepancy:**
- requirements.txt: pydexcom==0.46.0
- Installed: pydexcom==0.5.1
- Action: Update requirements.txt before deployment

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | unittest (Python stdlib) |
| Config file | None — tests in `dexcom_readings_test.py` |
| Quick run command | `python -m unittest dexcom_readings_test -v` |
| Full suite command | `python -m unittest discover -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SESS-01 | Service reconnects when session expires | unit | `python -m unittest dexcom_readings_test.TestSessionResilience.test_session_error_recovery -v` | Wave 0 |
| SESS-01 | Library handles single session expiration | integration | `python -m unittest dexcom_readings_test.TestSessionResilience.test_pydexcom_builtin_recovery -v` | Wave 0 |
| SESS-02 | Service re-authenticates without manual intervention | unit | `python -m unittest dexcom_readings_test.TestSessionResilience.test_reauth_on_consecutive_failures -v` | Wave 0 |
| SESS-02 | AccountError causes graceful exit | unit | `python -m unittest dexcom_readings_test.TestSessionResilience.test_account_error_exits -v` | Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m unittest dexcom_readings_test -v`
- **Per wave merge:** `python -m unittest discover -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `TestSessionResilience` class — new test class for session resilience
- [ ] `test_session_error_recovery` — verify SessionError is caught and logged
- [ ] `test_pydexcom_builtin_recovery` — verify library's built-in retry works
- [ ] `test_reauth_on_consecutive_failures` — verify re-auth after threshold
- [ ] `test_account_error_exits` — verify AccountError causes exit
- [ ] Mock setup for pydexcom exceptions (`SessionError`, `AccountError`)

## Security Domain

> Security enforcement enabled. ASVS categories evaluated.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | Credentials from environment variables (already implemented) |
| V3 Session Management | Yes | pydexcom handles session lifecycle; application tracks failures |
| V4 Access Control | No | No user roles or access control |
| V5 Input Validation | No | No user input; all data from API |
| V6 Cryptography | No | No cryptographic operations in this phase |

### Known Threat Patterns for Python + pydexcom

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Credential exposure in logs | Information Disclosure | Never log `DEXCOM_PASSWORD` or `DEXCOM_USERNAME` values |
| Session ID in logs | Information Disclosure | pydexcom logs session ID at DEBUG level only |
| Account lockout | Denial of Service | Rate-limit re-authentication attempts (cooldown period) |
| Exception message leakage | Information Disclosure | Log exception type, not full traceback with credentials |

## Sources

### Primary (HIGH confidence)

- pydexcom source code (`/Users/ffaber/Library/Python/3.9/lib/python/site-packages/pydexcom/dexcom.py`) — Exception hierarchy, session recovery logic
- pydexcom source code (`/Users/ffaber/Library/Python/3.9/lib/python/site-packages/pydexcom/errors.py`) — Error enum definitions
- dexcom_readings.py — Existing error handling patterns, `retry_with_backoff()` implementation
- CONTEXT.md — User decisions for implementation approach

### Secondary (MEDIUM confidence)

- [pydexcom GitHub repository](https://github.com/gagebenne/pydexcom) — Version history, error handling patterns
- [pydexcom documentation](https://gagebenne.github.io/pydexcom/pydexcom.html) — API reference

### Tertiary (LOW confidence)

- None — All findings verified from source code or documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pydexcom is the only option; version discrepancy documented
- Architecture: HIGH — Exception hierarchy verified from source; session recovery confirmed in library
- Pitfalls: HIGH — Based on code analysis and common patterns

**Research date:** 2026-05-21
**Valid until:** 90 days — stable library, but pydexcom may release updates