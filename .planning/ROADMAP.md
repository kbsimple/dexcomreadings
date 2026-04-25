# Roadmap

## Project Summary

Dexcom Readings - A Dexcom CGM data polling and forwarding service. Fetches real-time glucose readings from the Dexcom Share API and forwards them to Nightscout with local CSV logging.

**Core Value:** Reliable, continuous glucose data replication from Dexcom to Nightscout without data loss.

---

## Phases

- [x] **Phase 1: Style Guide & Infrastructure** - Establish Google Python Style Guide compliance and project documentation foundation (completed 2026-04-19)
- [x] **Phase 2: Configuration & Robustness** - Add operational flexibility with configurable polling and resilient error handling (completed 2026-04-19)
- [x] **Phase 3: Testing & Documentation** - Verify all changes work correctly and complete user-facing documentation (completed 2026-04-20)
- [ ] **Phase 4: System Daemon Compatibility** - Upgrade the script to be production-ready as a system daemon

---

## Phase Details

### Phase 1: Style Guide & Infrastructure

**Goal:** Codebase complies with Google Python Style Guide with proper documentation and dependency specification.

**Depends on:** Nothing (first phase)

**Requirements:** STYLE-01, STYLE-02, STYLE-03, STYLE-04, STYLE-05, STYLE-06, STYLE-07, STYLE-08, INFRA-01

**Success Criteria** (what must be TRUE):
  1. `pylint` runs on the codebase with no unresolved warnings
  2. All public functions have docstrings with Args/Returns/Raises sections
  3. All function signatures display type hints when inspected
  4. Constants follow `CAPS_WITH_UNDERSCORE` naming convention
  5. `requirements.txt` exists with pinned versions for `pydexcom` and `requests`

**Plans:** 4/4 plans complete

Plans:
- [x] 01-01-PLAN.md — Create requirements.txt, add module docstring, organize imports, verify constants
- [x] 01-02-PLAN.md — Encapsulate global state (pass last_known_glucose_timestamp as parameter)
- [x] 01-03-PLAN.md — Add comprehensive docstrings and type hints to all functions
- [x] 01-04-PLAN.md — Fix line length violations, configure pylint

---

### Phase 2: Configuration & Robustness

**Goal:** Service operates reliably with configurable behavior and graceful degradation under adverse conditions.

**Depends on:** Phase 1

**Requirements:** CONF-01, ROBUST-01, ROBUST-02

**Success Criteria** (what must be TRUE):
  1. User can set polling interval via `POLLING_INTERVAL_SECONDS` environment variable
  2. Service shuts down cleanly when receiving SIGTERM or SIGINT, completing current cycle first
  3. Service retries failed API calls with exponential backoff before logging error
  4. Service continues running after transient network failures (does not crash)

**Plans:** 2/2 plans complete

Plans:
- [x] 02-01-PLAN.md — Configure polling interval from environment and implement graceful shutdown
- [x] 02-02-PLAN.md — Add retry logic with exponential backoff for network failures

---

### Phase 3: Testing & Documentation

**Goal:** Test suite validates production behavior and users have complete setup documentation.

**Depends on:** Phase 2

**Requirements:** TEST-01, TEST-02, TEST-03, INFRA-02

**Success Criteria** (what must be TRUE):
  1. All existing tests pass with corrected mocks using `logging` module
  2. `upload_to_nightscout()` function has test coverage for success and failure cases
  3. Codebase uses `sys.exit()` consistently (no bare `exit()` calls)
  4. `README.md` documents installation, configuration, and usage with all environment variables

**Plans:** 1/1 plans complete

---

### Phase 4: System Daemon Compatibility

**Goal:** Script is production-ready for deployment as a system daemon with proper file paths, logging, and service templates.

**Depends on:** Phase 3

**Requirements:** DAEMON-01, DAEMON-02, DAEMON-03, DAEMON-04, DAEMON-05

**Success Criteria** (what must be TRUE):
  1. All file paths are absolute and configurable via environment variables
  2. PID file prevents multiple instances from running
  3. Logging supports syslog and file output with configurable destinations
  4. SIGHUP triggers log file reopen (for log rotation)
  5. Service file templates for systemd and launchd are provided and documented

**Plans:** Not planned yet

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Style Guide & Infrastructure | 4/4 | Complete    | 2026-04-19 |
| 2. Configuration & Robustness | 2/2 | Complete    | 2026-04-19 |
| 3. Testing & Documentation | 1/1 | Complete    | 2026-04-20 |
| 4. System Daemon Compatibility | 0/? | Not Started | — |

---

*Last updated: 2026-04-24*