# Phase 6: Failure Handling & API Resilience - Research

**Researched:** 2026-06-04
**Domain:** Circuit breaker pattern, API timeout configuration, rate limit handling
**Confidence:** HIGH

## Summary

This phase implements a circuit breaker pattern for repeated API failures and adds configurable timeouts for Dexcom API calls. The existing codebase already has a foundation for failure tracking (`_consecutive_failures`, `should_attempt_reauth()`), which provides a clear integration pattern for circuit breaker state.

**Primary recommendation:** Implement a lightweight circuit breaker using module-level state (matching existing session resilience pattern) rather than introducing the `pybreaker` dependency. Add timeouts by creating a custom requests Session subclass and injecting it into the pydexcom client.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### Circuit Breaker Pattern
- **D-01:** Implement circuit breaker with three states: CLOSED (normal), OPEN (failing), HALF_OPEN (testing)
- **D-02:** Open circuit after N consecutive failures (configurable via env var)
- **D-03:** Auto-recover after cooldown period (configurable via env var)
- **D-04:** In HALF_OPEN state, allow one test request; success -> CLOSED, failure -> OPEN

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

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FAIL-01 | Circuit breaker opens after repeated consecutive failures | Module-level `_circuit_state`, `_circuit_failure_count` tracking failures |
| FAIL-02 | Circuit breaker auto-recovers after cooldown period | `CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS` env var, state transition to HALF_OPEN |
| FAIL-03 | Configurable failure thresholds and recovery timeouts | `CIRCUIT_BREAKER_FAILURE_THRESHOLD` and `CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS` env vars |
| API-01 | Handle Dexcom API rate limits with exponential backoff | HTTP 429 detection in `retry_with_backoff`, `Retry-After` header parsing |
| API-02 | Configurable connection timeout for API calls | Custom `TimeoutSession` subclass with `DEXCOM_CONNECTION_TIMEOUT_SECONDS` |
| API-03 | Configurable read timeout for API responses | Custom `TimeoutSession` subclass with `DEXCOM_READ_TIMEOUT_SECONDS` |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydexcom | 0.5.1 | Dexcom API client | Already in use, locked in requirements.txt |
| requests | 2.31.0 | HTTP client | Already in use, pydexcom dependency |

### Supporting (To Add)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| None | - | Custom implementation preferred | Circuit breaker is simple enough to implement without pybreaker dependency |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom circuit breaker | pybreaker library | Adding dependency for 50 lines of logic is overkill; custom implementation matches existing code patterns |
| Injecting timeout session | Monkey-patch requests globally | Less invasive to use composition; easier to test |

**Installation:**
No new dependencies required. Implementation uses existing standard library and requests.

## Architecture Patterns

### Recommended Project Structure
```
dexcom_readings.py
├── Configuration (lines 33-98)
│   ├── CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.environ.get(..., "5"))
│   ├── CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS = int(os.environ.get(..., "60"))
│   ├── DEXCOM_CONNECTION_TIMEOUT_SECONDS = int(os.environ.get(..., "30"))
│   └── DEXCOM_READ_TIMEOUT_SECONDS = int(os.environ.get(..., "30"))
├── Circuit Breaker State (module-level, lines 261-265)
│   ├── _circuit_state: str = "closed"
│   ├── _circuit_failure_count: int = 0
│   └── _circuit_opened_at: Optional[float] = None
├── Session Resilience State (existing, lines 262-264)
├── TimeoutSession class (new, lines 267-290)
│   └── Subclass requests.Session with default timeout
├── Circuit Breaker Functions (new, lines 292-350)
│   ├── circuit_is_open() -> bool
│   ├── record_circuit_failure() -> None
│   ├── record_circuit_success() -> None
│   └── check_circuit_recovery() -> bool
├── retry_with_backoff (modified, lines 352-420)
│   └── Add circuit breaker check and 429 handling
└── initialize_dexcom_client (modified, lines 468-507)
    └── Inject TimeoutSession into pydexcom's internal session
```

### Pattern 1: Circuit Breaker State Machine

**What:** Three-state circuit breaker tracking API health
**When to use:** For any external API call that can fail repeatedly

**State Transitions:**
```
CLOSED (normal) --[failures >= threshold]--> OPEN (failing)
OPEN --[recovery_timeout elapsed]--> HALF_OPEN (testing)
HALF_OPEN --[success]--> CLOSED
HALF_OPEN --[failure]--> OPEN
```

**Example:**
```python
# Source: [Verified against existing session resilience pattern in dexcom_readings.py]
# Circuit breaker state (module-level, following existing pattern)
_circuit_state: str = "closed"  # "closed", "open", "half_open"
_circuit_failure_count: int = 0
_circuit_opened_at: Optional[float] = None

def circuit_is_open() -> bool:
    """Check if circuit breaker is open (blocking requests)."""
    global _circuit_state, _circuit_opened_at

    if _circuit_state == "closed":
        return False

    if _circuit_state == "open":
        now = time.time()
        if _circuit_opened_at and (now - _circuit_opened_at) >= CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS:
            # Transition to half-open for testing
            _circuit_state = "half_open"
            logging.warning("Circuit breaker transitioning to HALF_OPEN")
            return False
        return True

    # half_open state - allow one test request
    return False

def record_circuit_failure() -> None:
    """Record a failure and potentially open the circuit."""
    global _circuit_state, _circuit_failure_count, _circuit_opened_at

    _circuit_failure_count += 1

    if _circuit_state == "half_open":
        # Test request failed, back to open
        _circuit_state = "open"
        _circuit_opened_at = time.time()
        logging.warning(
            f"Circuit breaker HALF_OPEN -> OPEN (test request failed)"
        )
    elif _circuit_failure_count >= CIRCUIT_BREAKER_FAILURE_THRESHOLD:
        _circuit_state = "open"
        _circuit_opened_at = time.time()
        logging.warning(
            f"Circuit breaker CLOSED -> OPEN "
            f"(failures: {_circuit_failure_count}, threshold: {CIRCUIT_BREAKER_FAILURE_THRESHOLD})"
        )

def record_circuit_success() -> None:
    """Record a success and close the circuit if in half_open."""
    global _circuit_state, _circuit_failure_count, _circuit_opened_at

    _circuit_failure_count = 0

    if _circuit_state == "half_open":
        _circuit_state = "closed"
        _circuit_opened_at = None
        logging.warning("Circuit breaker HALF_OPEN -> CLOSED (recovered)")
```

### Pattern 2: Timeout Session Injection

**What:** Custom requests.Session subclass with default timeouts
**When to use:** When library doesn't expose timeout parameters (pydexcom case)

**Example:**
```python
# Source: [CITED: https://github.com/psf/requests/issues/2011]
class TimeoutSession(requests.Session):
    """requests.Session subclass that enforces default timeout on all requests."""

    def __init__(self, timeout: tuple[float, float]):
        super().__init__()
        self._timeout = timeout

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        kwargs.setdefault('timeout', self._timeout)
        return super().request(method, url, **kwargs)

def initialize_dexcom_client() -> Optional[Dexcom]:
    # ... credential checks ...
    timeout = (
        DEXCOM_CONNECTION_TIMEOUT_SECONDS,
        DEXCOM_READ_TIMEOUT_SECONDS
    )
    session = TimeoutSession(timeout)

    dexcom_client = Dexcom(username=DEXCOM_USERNAME, password=DEXCOM_PASSWORD)
    # Inject timeout session into pydexcom's internal session
    dexcom_client._session = session
    return dexcom_client
```

### Pattern 3: Rate Limit Handling

**What:** HTTP 429 detection with Retry-After header support
**When to use:** In retry_with_backoff to handle rate limits gracefully

**Example:**
```python
# Source: [CITED: https://dev.to/137foundry/how-to-implement-exponential-backoff-for-rate-limited-apis-in-python-28b5]
def retry_with_backoff(
        func: Callable[[], Any],
        max_attempts: int = RETRY_MAX_ATTEMPTS,
        initial_delay: float = RETRY_INITIAL_DELAY_SECONDS,
        max_delay: float = RETRY_MAX_DELAY_SECONDS) -> Optional[Any]:
    delay = initial_delay
    last_exception = None

    for attempt in range(max_attempts):
        # Check circuit breaker before attempting
        if circuit_is_open():
            logging.warning("Circuit breaker OPEN - skipping request")
            return None

        try:
            result = func()
            record_circuit_success()
            return result
        except AccountError as e:
            # Unrecoverable
            logging.error(f"Authentication failed: {e}")
            raise
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                # Rate limited - use Retry-After if available
                retry_after = e.response.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = float(retry_after)
                        logging.warning(f"Rate limited, waiting {delay}s (Retry-After)")
                    except ValueError:
                        delay = min(delay * 2, max_delay)
                else:
                    delay = min(delay * 2, max_delay)
            record_circuit_failure()
            last_exception = e
            # ... rest of retry logic
```

### Anti-Patterns to Avoid

- **Adding pybreaker dependency:** Overkill for simple three-state tracking; 50 lines of custom code matches existing patterns
- **Monkey-patching requests globally:** Too invasive; use composition with TimeoutSession
- **Separate circuit breaker per API:** Single circuit breaker for Dexcom API is sufficient; Nightscout has its own error handling
- **Ignoring Retry-After header:** Server knows best - respect the header value
- **Infinite HALF_OPEN attempts:** Must have max_attempts in retry to prevent loops

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Circuit state tracking | Complex state machine | Module-level variables | Existing pattern established in Phase 5 |
| HTTP retries | Custom retry loop | Existing `retry_with_backoff()` | Already implemented, tested, and handles exponential backoff |
| Rate limit parsing | Custom header parsing | `float(response.headers.get("Retry-After", default))` | Simple one-liner, handle ValueError for non-numeric values |

**Key insight:** The existing session resilience pattern (`_consecutive_failures`, `should_attempt_reauth()`) provides a blueprint. Circuit breaker is similar state tracking with different transitions.

## Runtime State Inventory

This is a refactor/enhancement phase. No stored data migration required.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None - all state is in-memory module variables | None |
| Live service config | None - config via environment variables only | None |
| OS-registered state | None | None |
| Secrets/env vars | New vars: `CIRCUIT_BREAKER_FAILURE_THRESHOLD`, `CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS`, `DEXCOM_CONNECTION_TIMEOUT_SECONDS`, `DEXCOM_READ_TIMEOUT_SECONDS` | Add to README.md documentation |
| Build artifacts | None | None |

## Common Pitfalls

### Pitfall 1: Timeout Not Applied to Internal Session
**What goes wrong:** Creating TimeoutSession but not replacing pydexcom's internal session means timeouts are never applied.
**Why it happens:** pydexcom creates its own `requests.Session()` internally; simply creating a timeout session doesn't affect it.
**How to avoid:** Must explicitly replace `dexcom_client._session` after client instantiation.
**Warning signs:** Requests hang indefinitely; no timeout errors in logs.

### Pitfall 2: Circuit Breaker Never Recovers
**What goes wrong:** Circuit opens but never transitions to HALF_OPEN because recovery check is missing.
**Why it happens:** Forgetting to check elapsed time in `circuit_is_open()` or missing the HALF_OPEN state entirely.
**How to avoid:** Always check `time.time() - _circuit_opened_at >= RECOVERY_TIMEOUT` in `circuit_is_open()`.
**Warning signs:** Service permanently blocked after temporary outage; manual restart required.

### Pitfall 3: HALF_OPEN Creates Retry Loop
**What goes wrong:** HALF_OPEN allows requests but failures immediately re-open circuit, creating rapid state thrashing.
**Why it happens:** Not limiting retry attempts in HALF_OPEN state.
**How to avoid:** HALF_OPEN should allow one test request; failure goes straight to OPEN, success closes circuit.
**Warning signs:** Logs show rapid CLOSED -> OPEN -> HALF_OPEN -> OPEN cycling.

### Pitfall 4: Retry-After Header Not Parsed
**What goes wrong:** Ignoring Retry-After header and using fixed backoff delay, causing unnecessary repeated 429s.
**Why it happens:** Not checking `response.headers.get("Retry-After")` before calculating delay.
**How to avoid:** Always parse Retry-After first, fall back to exponential backoff only if header absent.
**Warning signs:** Multiple 429 responses in quick succession despite backing off.

### Pitfall 5: Circuit Breaker Tracks Wrong Failures
**What goes wrong:** Circuit opens for AccountError (credential failures) when it should only track transient failures.
**Why it happens:** Catching all exceptions in circuit failure tracking without filtering.
**How to avoid:** Only call `record_circuit_failure()` for `SessionError`, `ServerError`, `ConnectionError`, `TimeoutError`, and `HTTPError(429)`. Never for `AccountError`.
**Warning signs:** Service exits immediately after credentials become invalid instead of graceful shutdown.

## Code Examples

### Verified patterns from existing codebase:

### Current retry_with_backoff (lines 267-320)
```python
# Source: [VERIFIED: dexcom_readings.py lines 267-320]
def retry_with_backoff(
        func: Any,
        max_attempts: int = RETRY_MAX_ATTEMPTS,
        initial_delay: float = RETRY_INITIAL_DELAY_SECONDS,
        max_delay: float = RETRY_MAX_DELAY_SECONDS) -> Optional[Any]:
    delay = initial_delay
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return func()
        except AccountError as e:
            # Unrecoverable - credentials invalid
            logging.error(f"Authentication failed: {e}")
            raise  # Propagate to caller for graceful exit
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

### Current session resilience state (lines 261-264)
```python
# Source: [VERIFIED: dexcom_readings.py lines 261-264]
# Session resilience state
_consecutive_failures: int = 0
_last_failure_time: Optional[float] = None
_last_reauth_time: Optional[float] = None
```

### Current should_attempt_reauth (lines 377-426)
```python
# Source: [VERIFIED: dexcom_readings.py lines 377-426]
def should_attempt_reauth(error: Exception) -> bool:
    global _consecutive_failures, _last_failure_time, _last_reauth_time

    now = time.time()

    # AccountError is unrecoverable
    if isinstance(error, AccountError):
        logging.error(
            "Authentication credentials invalid - manual intervention required"
        )
        return False

    _consecutive_failures += 1
    _last_failure_time = now

    if _consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
        if _last_reauth_time and (now - _last_reauth_time) < REAUTH_COOLDOWN_SECONDS:
            logging.warning(
                f"Consecutive failures: {_consecutive_failures}, "
                f"but re-auth cooldown not elapsed"
            )
            return False
        logging.warning(
            f"Consecutive failures ({_consecutive_failures}) exceed threshold "
            f"({MAX_CONSECUTIVE_FAILURES}) - attempting re-authentication"
        )
        return True
    return False
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No timeout configuration | Default timeouts in requests 2.34.0+ | 2024 | Native timeout support coming; backport needed for now |
| Single retry loop | Circuit breaker + retry | Industry standard | Prevents cascade failures during outages |
| Fixed backoff delay | Exponential + jitter + Retry-After | Industry standard | Prevents thundering herd, respects server guidance |

**Deprecated/outdated:**
- Global requests timeout monkey-patch: Use TimeoutSession subclass instead
- pybreaker dependency for simple cases: Overkill for three-state tracking

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | pydexcom's internal `_session` attribute can be replaced after instantiation | Architecture Patterns | If pydexcom doesn't expose `_session` or creates new sessions per request, timeout injection fails |
| A2 | Dexcom Share API returns HTTP 429 with Retry-After header when rate limited | Rate Limit Handling | If no Retry-After, fall back to exponential backoff |
| A3 | Circuit breaker state should be shared across all Dexcom API calls (single instance) | Architecture Patterns | If separate circuits needed per operation, refactor required |

**Verification needed:** Test that pydexcom's `_session` replacement works correctly before relying on it.

## Open Questions

1. **Should circuit breaker state persist across restarts?**
   - What we know: Current implementation uses in-memory module variables
   - What's unclear: Whether circuit state should survive process restart (e.g., written to file)
   - Recommendation: Start with in-memory (matches session resilience); file persistence is v2 feature if needed

2. **Should HALF_OPEN allow multiple concurrent test requests or just one?**
   - What we know: Industry standard is to allow limited requests in HALF_OPEN
   - What's unclear: Single-threaded polling means only one request at a time
   - Recommendation: Allow one test request (simpler implementation)

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.x | Runtime | ✓ | 3.9+ | - |
| requests | HTTP client | ✓ | 2.31.0 | - |
| pydexcom | Dexcom API | ✓ | 0.5.1 | - |
| unittest | Testing | ✓ | stdlib | - |

**Missing dependencies with no fallback:**
- None

**Missing dependencies with fallback:**
- None

## Validation Architecture

**Skip this section:** workflow.nyquist_validation is enabled, but test infrastructure analysis follows.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | unittest (Python standard library) |
| Config file | None - tests in dexcom_readings_test.py |
| Quick run command | `python -m unittest dexcom_readings_test -v` |
| Full suite command | `python -m unittest dexcom_readings_test -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FAIL-01 | Circuit opens after threshold failures | unit | `python -m unittest dexcom_readings_test.TestCircuitBreaker.test_circuit_opens_after_failures -v` | Wave 0 |
| FAIL-02 | Circuit auto-recovers after cooldown | unit | `python -m unittest dexcom_readings_test.TestCircuitBreaker.test_circuit_recovers_after_timeout -v` | Wave 0 |
| FAIL-03 | Configurable thresholds via env vars | unit | `python -m unittest dexcom_readings_test.TestCircuitBreaker.test_configurable_thresholds -v` | Wave 0 |
| API-01 | Handle HTTP 429 with backoff | unit | `python -m unittest dexcom_readings_test.TestRateLimitHandling.test_429_triggers_backoff -v` | Wave 0 |
| API-02 | Connection timeout configurable | unit | `python -m unittest dexcom_readings_test.TestTimeoutSession.test_connection_timeout -v` | Wave 0 |
| API-03 | Read timeout configurable | unit | `python -m unittest dexcom_readings_test.TestTimeoutSession.test_read_timeout -v` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m unittest dexcom_readings_test -v`
- **Per wave merge:** `python -m unittest dexcom_readings_test -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_circuit_breaker.py` - unit tests for circuit breaker state machine
- [ ] `tests/test_timeout_session.py` - unit tests for TimeoutSession class
- [ ] `tests/test_rate_limit.py` - unit tests for HTTP 429 handling
- [ ] Integration with existing `TestSessionResilience` class pattern

*(If no gaps: "None - existing test infrastructure covers all phase requirements")*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Handled by pydexcom library |
| V3 Session Management | no | No user sessions |
| V4 Access Control | no | Single-user service |
| V5 Input Validation | no | No user input beyond credentials |
| V6 Cryptography | no | HTTPS handled by requests library |

### Known Threat Patterns for Python HTTP Clients

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Connection timeout | Denial of Service | Configurable timeout prevents hanging |
| Rate limit evasion | Denial of Service | Exponential backoff respects server limits |
| Credential exposure | Information Disclosure | Environment variables, not hardcoded |

## Sources

### Primary (HIGH confidence)
- [VERIFIED: dexcom_readings.py] - Current implementation patterns, session resilience architecture
- [VERIFIED: dexcom_readings_test.py] - Test patterns, mock usage
- [CITED: https://github.com/gagebenne/pydexcom] - pydexcom 0.5.1, no timeout parameter support
- [CITED: https://github.com/gagebenne/pydexcom/blob/main/pydexcom/dexcom.py] - Dexcom class creates internal `_session`

### Secondary (MEDIUM confidence)
- [CITED: https://github.com/psf/requests/issues/2011] - TimeoutSession subclass pattern
- [CITED: https://oneuptime.com/blog/post/2026-01-23-python-circuit-breakers] - Circuit breaker three-state pattern
- [CITED: https://dev.to/137foundry/how-to-implement-exponential-backoff-for-rate-limited-apis-in-python-28b5] - Rate limit handling with Retry-After

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies, using existing patterns
- Architecture: HIGH - Matches existing session resilience pattern
- Pitfalls: HIGH - Based on verified pydexcom source code and industry best practices

**Research date:** 2026-06-04
**Valid until:** 2026-12-04 (6 months - stable patterns)