---
phase: 04-system-daemon-compatibility
plan: 02
subsystem: logging
tags: [daemon, logging, sighup, log-rotation, syslog]
requires: [04-01]
provides: [flexible-logging, log-rotation-support]
affects: [dexcom_readings.py]
tech-stack:
  added: [logging.handlers.SysLogHandler, logging.handlers.WatchedFileHandler]
  patterns: [signal-handler, context-manager]
key-files:
  created: []
  modified: [dexcom_readings.py]
decisions:
  - Use WatchedFileHandler for log rotation (external tools manage rotation)
  - Use flag-based SIGHUP handler to avoid race conditions
  - Fallback to console logging if syslog unavailable
metrics:
  duration: ~5 minutes
  completed: "2026-04-25"
  tasks: 2
  commits: 2
---

# Phase 4 Plan 2: Flexible Logging and Log Rotation Summary

## One-liner

Implemented flexible logging destinations (console/file/syslog) with SIGHUP handler for external log rotation support.

## Changes Made

### Task 1: Flexible Logging Destinations

Replaced `logging.basicConfig()` with a `setup_logging()` function that supports three destinations:

- **console**: StreamHandler to stderr (default)
- **file**: WatchedFileHandler for log rotation support
- **syslog**: SysLogHandler for Unix syslog integration

Added environment variables:
- `DEXCOM_LOG_DESTINATION`: Controls logging destination (console/file/syslog)
- `DEXCOM_LOG_LEVEL`: Controls log level (default: INFO)

### Task 2: SIGHUP Handler for Log Rotation

Added signal handling for log rotation tools (logrotate, newsyslog):
- `log_reopen_requested` module flag
- `handle_sighup()` signal handler
- `check_and_reopen_logs()` function called each polling cycle
- Windows compatibility via try/except for SIGHUP registration

## Deviations from Plan

None - plan executed exactly as written.

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| WatchedFileHandler over RotatingFileHandler | External tools (logrotate) handle compression, archival, retention |
| Flag-based SIGHUP handler | Avoids race conditions; handler sets flag, main loop processes |
| Console fallback for syslog | Ensures logging works even if syslog unavailable |

## Files Modified

| File | Changes |
|------|---------|
| dexcom_readings.py | Added setup_logging(), handle_sighup(), check_and_reopen_logs(); added LOG_DESTINATION and LOG_LEVEL constants |

## Commits

| Commit | Description |
|--------|-------------|
| 4a22e9b | feat(04-02): implement flexible logging destinations |
| 38e7400 | feat(04-02): add SIGHUP handler for log rotation |

## Verification

- All 20 unit tests pass
- `setup_logging()` function works with console destination
- SIGHUP handler registered (Unix only)

## Requirements Delivered

- **DAEMON-03**: Logging supports syslog and file output with configurable destinations
- **DAEMON-04**: SIGHUP triggers log file reopen for log rotation