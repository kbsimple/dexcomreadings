# Requirements

## v1 Requirements

### Project Infrastructure

- [ ] **INFRA-01**: Add `requirements.txt` with pinned versions for `pydexcom` and `requests`
- [ ] **INFRA-02**: Add `README.md` with installation, configuration, and usage documentation

### Configuration

- [ ] **CONF-01**: Make polling interval configurable via `POLLING_INTERVAL_SECONDS` environment variable

### Robustness

- [ ] **ROBUST-01**: Implement graceful shutdown with signal handlers (SIGTERM/SIGINT)
- [ ] **ROBUST-02**: Add retry logic with exponential backoff for transient network failures

### Testing

- [ ] **TEST-01**: Fix test mocks to use `logging` instead of `builtins.print`
- [ ] **TEST-02**: Add tests for `upload_to_nightscout()` function
- [ ] **TEST-03**: Use `sys.exit()` consistently (replace `exit()` calls)

### Style Guide Compliance

- [ ] **STYLE-01**: Add module-level docstring with usage description and license
- [ ] **STYLE-02**: Add docstrings to all public functions with Args/Returns/Raises
- [ ] **STYLE-03**: Add type hints to all function signatures
- [ ] **STYLE-04**: Rename constants to `CAPS_WITH_UNDERSCORE` format
- [ ] **STYLE-05**: Organize imports per Google Style Guide (stdlib, third-party, local; alphabetical)
- [ ] **STYLE-06**: Ensure all lines ≤80 characters
- [ ] **STYLE-07**: Add `pylint` configuration and suppress warnings appropriately
- [ ] **STYLE-08**: Encapsulate global state in a class or pass as parameter

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

| Phase | Requirements | Status |
|-------|--------------|--------|
| _ | _ | _ |

---
*Last updated: 2026-04-19*