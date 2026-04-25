# Requirements

## v1 Requirements

### Project Infrastructure

- [x] **INFRA-01**: Add `requirements.txt` with pinned versions for `pydexcom` and `requests`
- [x] **INFRA-02**: Add `README.md` with installation, configuration, and usage documentation

### Configuration

- [x] **CONF-01**: Make polling interval configurable via `POLLING_INTERVAL_SECONDS` environment variable

### Robustness

- [x] **ROBUST-01**: Implement graceful shutdown with signal handlers (SIGTERM/SIGINT)
- [x] **ROBUST-02**: Add retry logic with exponential backoff for transient network failures

### Testing

- [x] **TEST-01**: Fix test mocks to use `logging` instead of `builtins.print`
- [x] **TEST-02**: Add tests for `upload_to_nightscout()` function
- [x] **TEST-03**: Use `sys.exit()` consistently (replace `exit()` calls)

### Style Guide Compliance

- [x] **STYLE-01**: Add module-level docstring with usage description and license
- [x] **STYLE-02**: Add docstrings to all public functions with Args/Returns/Raises
- [x] **STYLE-03**: Add type hints to all function signatures
- [x] **STYLE-04**: Rename constants to `CAPS_WITH_UNDERSCORE` format
- [x] **STYLE-05**: Organize imports per Google Style Guide (stdlib, third-party, local; alphabetical)
- [x] **STYLE-06**: Ensure all lines ≤80 characters
- [x] **STYLE-07**: Add `pylint` configuration and suppress warnings appropriately
- [x] **STYLE-08**: Encapsulate global state in a class or pass as parameter

### Daemon Compatibility

- [x] **DAEMON-01**: Implement absolute configurable file paths via environment variables
- [x] **DAEMON-02**: Add PID file single-instance enforcement with fcntl locking
- [ ] **DAEMON-03**: Implement configurable logging (syslog, file, console)
- [ ] **DAEMON-04**: Add SIGHUP handler for log file reopening
- [ ] **DAEMON-05**: Provide systemd and launchd service templates

---

## v2 Requirements (Deferred)

- Health check/status endpoint for monitoring
- Log rotation for CSV file growth
- Database storage option instead of CSV

---

## Out of Scope

- **Multi-user support** — Single-user polling service by design
- **Web UI** — Runs as daemon/background service
- **Real-time notifications** — Polling-based architecture, not event-driven
- **Database storage** — CSV is sufficient for current use case
- **Migration away from pydexcom** — Will continue using third-party library

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| STYLE-01 | Phase 1 | Complete |
| STYLE-02 | Phase 1 | Complete |
| STYLE-03 | Phase 1 | Complete |
| STYLE-04 | Phase 1 | Complete |
| STYLE-05 | Phase 1 | Complete |
| STYLE-06 | Phase 1 | Complete |
| STYLE-07 | Phase 1 | Complete |
| STYLE-08 | Phase 1 | Complete |
| INFRA-01 | Phase 1 | Complete |
| CONF-01 | Phase 2 | Complete |
| ROBUST-01 | Phase 2 | Complete |
| ROBUST-02 | Phase 2 | Complete |
| TEST-01 | Phase 3 | Complete |
| TEST-02 | Phase 3 | Complete |
| TEST-03 | Phase 3 | Complete |
| INFRA-02 | Phase 3 | Complete |
| DAEMON-01 | Phase 4 | Complete |
| DAEMON-02 | Phase 4 | Complete |
| DAEMON-03 | Phase 4 | Pending |
| DAEMON-04 | Phase 4 | Pending |
| DAEMON-05 | Phase 4 | Pending |

---
*Last updated: 2026-04-25*