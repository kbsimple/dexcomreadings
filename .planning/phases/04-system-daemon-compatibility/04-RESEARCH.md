# Phase 4: System Daemon Compatibility - Research

**Researched:** 2026-04-24
**Domain:** Python daemonization, system service management, logging infrastructure
**Confidence:** HIGH

## Summary

This phase transforms the dexcom_readings.py script into a production-ready system daemon compatible with both systemd (Linux) and launchd (macOS). The script already implements graceful shutdown handling (SIGTERM/SIGINT) from Phase 2, but needs enhancement for: absolute configurable paths, PID-based single-instance enforcement, flexible logging destinations (syslog/file/console), SIGHUP log rotation support, and system service templates.

**Primary recommendation:** Do NOT self-daemonize. Let systemd/launchd manage the process lifecycle. Implement PID file for single-instance protection, use Python's `WatchedFileHandler` for external log rotation support, and add SIGHUP handler for log file reopening. Provide service templates that work with the foreground execution model.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `logging.handlers.WatchedFileHandler` | stdlib | Log file rotation detection | Built-in, works with logrotate/newsyslog |
| `logging.handlers.SysLogHandler` | stdlib | Syslog integration | Standard for Unix daemon logging |
| `signal` | stdlib | Signal handling (SIGHUP, SIGTERM, SIGINT) | Required for daemon behavior |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `python-daemon` | 3.1.2 | Full daemonization context | When NOT using systemd/launchd (standalone daemon) |
| `systemd-python` | 235+ | Journal logging, notify socket | When deploying on systemd systems |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Self-daemonization with `python-daemon` | Let systemd/launchd manage | systemd/launchd is preferred: better process supervision, automatic restart, dependency management |
| `RotatingFileHandler` | `WatchedFileHandler` + logrotate | `WatchedFileHandler` allows external tools to manage rotation (compress, archive) |
| Simple PID file existence check | File-locking PID with `fcntl` | File locking is OS-guaranteed to release on process exit, avoiding stale PID files |

**Installation:**
```bash
# Optional - only needed if self-daemonization is required
pip install python-daemon==3.1.2

# Optional - for systemd journal integration
pip install systemd-python
```

**Version verification:**
- `logging.handlers` is part of Python stdlib (no installation needed)
- `signal` is part of Python stdlib (no installation needed)
- `python-daemon` 3.1.2 confirmed via pip index (2026-04-24)

## Architecture Patterns

### Recommended Project Structure
```
dexcom_readings.py           # Main script (enhanced with daemon features)
dexcom_readings_test.py      # Unit tests
requirements.txt             # Dependencies
README.md                    # Documentation
service/
├── dexcom-readings.service  # systemd unit file template
└── com.dexcom.readings.plist # launchd plist template
```

### Pattern 1: PID File with File Locking (Single Instance Enforcement)

**What:** Prevents multiple daemon instances from running simultaneously using OS-guaranteed file locking.

**When to use:** Always. Critical for data integrity (prevents duplicate CSV entries, duplicate Nightscout uploads).

**Example:**
```python
# Source: [VERIFIED: Python stdlib fcntl, PEP 3143 pattern]
import fcntl
import os

class PIDFile:
    """Context manager for PID-based single-instance locking."""

    def __init__(self, pidfile_path: str) -> None:
        self.pidfile_path = pidfile_path
        self.pidfile = None

    def __enter__(self) -> "PIDFile":
        self.pidfile = open(self.pidfile_path, "w")
        try:
            fcntl.flock(self.pidfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.pidfile.write(f"{os.getpid()}\n")
            self.pidfile.flush()
            return self
        except BlockingIOError:
            raise RuntimeError(
                f"Another instance is already running (PID file: {self.pidfile_path})"
            )

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.pidfile:
            fcntl.flock(self.pidfile.fileno(), fcntl.LOCK_UN)
            self.pidfile.close()
            os.unlink(self.pidfile_path)
```

### Pattern 2: WatchedFileHandler for Log Rotation

**What:** Python handler that detects when log file has been rotated (moved/deleted) and reopens it.

**When to use:** When using external log rotation tools (logrotate, newsyslog). Works with SIGHUP pattern.

**Example:**
```python
# Source: [CITED: docs.python.org/3/library/logging.handlers.html]
import logging
from logging.handlers import WatchedFileHandler

def setup_logging(log_file: str, log_level: str) -> logging.Logger:
    """Configure logging with file handler that supports rotation."""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # WatchedFileHandler auto-reopens when file is moved/deleted
    file_handler = WatchedFileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)

    return logger
```

### Pattern 3: SIGHUP Handler for Log Reopen

**What:** Signal handler that triggers log file reopening, typically called by logrotate's postrotate script.

**When to use:** When log rotation tools send SIGHUP to notify the daemon.

**Example:**
```python
# Source: [VERIFIED: Python signal module, Stack Overflow best practices]
import signal
import logging
from logging.handlers import WatchedFileHandler

# Use a flag-based approach to avoid race conditions
log_reopen_requested = False

def sighup_handler(signum: int, frame) -> None:
    """Request log file reopen on SIGHUP."""
    global log_reopen_requested
    log_reopen_requested = True
    logging.info("Received SIGHUP, will reopen log file on next cycle")

def check_and_reopen_logs(logger: logging.Logger) -> None:
    """Reopen log handlers if SIGHUP was received."""
    global log_reopen_requested
    if log_reopen_requested:
        for handler in logger.handlers:
            if isinstance(handler, WatchedFileHandler):
                handler.reopenIfNeeded()
        log_reopen_requested = False
        logging.info("Log file reopened")
```

### Pattern 4: Environment Variable Path Configuration

**What:** All file paths configurable via environment variables with sensible defaults.

**When to use:** Always for daemons. Enables different configurations for dev/staging/prod.

**Example:**
```python
# Source: [ASSUMED: Standard Python daemon pattern]
import os
from pathlib import Path

# Default to XDG Base Directory Specification paths
DEFAULT_DATA_DIR = os.environ.get(
    "XDG_DATA_HOME", str(Path.home() / ".local" / "share")
)
DEFAULT_STATE_DIR = os.environ.get(
    "XDG_STATE_HOME", str(Path.home() / ".local" / "state")
)

# Configurable paths with absolute path resolution
OUTPUT_CSV_FILE = os.path.abspath(
    os.environ.get(
        "DEXCOM_CSV_PATH",
        os.path.join(DEFAULT_DATA_DIR, "dexcom-readings", "readings.csv")
    )
)
PID_FILE = os.path.abspath(
    os.environ.get(
        "DEXCOM_PID_FILE",
        os.path.join(DEFAULT_STATE_DIR, "dexcom-readings", "dexcom-readings.pid")
    )
)
LOG_FILE = os.path.abspath(
    os.environ.get(
        "DEXCOM_LOG_FILE",
        os.path.join(DEFAULT_STATE_DIR, "dexcom-readings", "dexcom-readings.log")
    )
)
```

### Pattern 5: systemd Service Unit Template

**What:** systemd unit file that runs the script as a foreground process under systemd supervision.

**When to use:** For Linux deployments. The preferred modern approach.

**Example:**
```ini
# Source: [CITED: freedesktop.org systemd documentation]
[Unit]
Description=Dexcom CGM Readings Collector
Documentation=https://github.com/user/dexcom-readings
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=dexcom
Group=dexcom
WorkingDirectory=/opt/dexcom-readings
ExecStart=/opt/dexcom-readings/venv/bin/python /opt/dexcom-readings/dexcom_readings.py
Restart=on-failure
RestartSec=5s

# Environment variables
EnvironmentFile=/etc/default/dexcom-readings

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=dexcom-readings

# Security sandboxing
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/dexcom-readings

[Install]
WantedBy=multi-user.target
```

### Pattern 6: launchd plist Template

**What:** macOS launchd property list that runs the script as a foreground process.

**When to use:** For macOS deployments.

**Example:**
```xml
<!-- Source: [CITED: developer.apple.com launchd documentation] -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dexcom.readings</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/dexcom-readings/venv/bin/python</string>
        <string>/opt/dexcom-readings/dexcom_readings.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/opt/dexcom-readings</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>DEXCOM_USERNAME</key>
        <string>YOUR_USERNAME_HERE</string>
        <key>DEXCOM_PASSWORD</key>
        <string>YOUR_PASSWORD_HERE</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/dexcom-readings.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/dexcom-readings.log</string>
</dict>
</plist>
```

### Anti-Patterns to Avoid

- **Self-daemonization when using systemd/launchd:** Let the service manager handle forking, process supervision, and restart. Running in foreground (`Type=simple`) is preferred.
- **Simple PID file existence check without locking:** Stale PID files persist after crashes, causing false "already running" errors. Always use file locking (`fcntl`).
- **Bare `exit()` calls:** Use `sys.exit()` consistently for testability.
- **Hardcoded paths:** Make all paths configurable for different deployment environments.
- **Ignoring SIGHUP:** Without handling, log rotation tools cannot notify the daemon to reopen log files.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PID file management | Custom PID file with existence check | `fcntl.flock()` locking pattern | OS guarantees lock release on exit, no stale PID files |
| Log rotation | Custom size-based file rotation | `WatchedFileHandler` + logrotate | External tools handle compression, archival, retention |
| Daemon context (if needed) | Manual fork/setsid/detach | `python-daemon` library | PEP 3143 standard, handles all edge cases |
| Syslog integration | Custom socket writes | `SysLogHandler` | Stdlib, handles protocol details, facility mapping |

**Key insight:** Modern service managers (systemd, launchd) make traditional daemonization unnecessary. The best approach is to run as a simple foreground process and let the service manager handle supervision, logging, and restart.

## Runtime State Inventory

> This is NOT a rename/refactor phase. Skipping Runtime State Inventory.

## Common Pitfalls

### Pitfall 1: Stale PID Files After Crash
**What goes wrong:** Daemon crashes, PID file remains, next startup fails with "already running" error.
**Why it happens:** Simple existence check doesn't detect the original process is dead.
**How to avoid:** Use `fcntl.flock()` with `LOCK_EX | LOCK_NB`. The OS releases the lock automatically when the process exits (even on crash).
**Warning signs:** "Already running" errors after unclean shutdown.

### Pitfall 2: Log File Not Reopened After Rotation
**What goes wrong:** logrotate moves the log file, but daemon continues writing to the old (deleted) file descriptor.
**Why it happens:** Process doesn't know the file was rotated; keeps writing to the old inode.
**How to avoid:** Use `WatchedFileHandler` (checks inode on each emit) or handle SIGHUP to reopen.
**Warning signs:** Log files are empty after rotation, disk space unexplained.

### Pitfall 3: macOS launchd Path Issues
**What goes wrong:** Plist works in testing but fails at boot because paths are relative or use `$HOME`.
**Why it happens:** launchd doesn't expand shell variables; runs with different environment at boot.
**How to avoid:** Use absolute paths everywhere. Expand variables in the plist file itself, not at runtime.
**Warning signs:** Service shows "loaded" but exit status is non-zero in `launchctl list`.

### Pitfall 4: systemd ExecStart Variable Expansion
**What goes wrong:** `ExecStart=$VENV/bin/python script.py` fails because systemd doesn't expand variables in the first argument.
**Why it happens:** systemd requires literal absolute path for the executable.
**How to avoid:** Use `/bin/sh -c '...'` wrapper for variable expansion, or hardcode the Python path.
**Warning signs:** Service fails with "No such file or directory" for the executable.

### Pitfall 5: Dual Logging Destinations
**What goes wrong:** Logs go to both file and journal/syslog, creating duplication and confusion.
**Why it happens:** Both `StandardOutput=journal` and file handler are configured.
**How to avoid:** Choose one primary destination. If using journal/syslog, remove file handlers. If using files, set `StandardOutput=null`.
**Warning signs:** Every log message appears twice in the central logging system.

## Code Examples

Verified patterns from official sources:

### SysLogHandler Configuration
```python
# Source: [CITED: docs.python.org/3/library/logging.handlers.html]
import logging
import logging.handlers

# Local syslog via Unix domain socket (Linux)
handler = logging.handlers.SysLogHandler(
    address="/dev/log",
    facility=logging.handlers.SysLogHandler.LOG_LOCAL0
)

# For macOS, use /var/run/syslog (may not work on macOS 12+)
# Alternative: use file logging or journald on Linux
```

### Environment Variable with Absolute Path Resolution
```python
# Source: [VERIFIED: Python pathlib documentation]
import os
from pathlib import Path

def get_absolute_path(env_var: str, default: str) -> str:
    """Resolve a path from environment variable or default to absolute path."""
    path = os.environ.get(env_var, default)
    return str(Path(path).resolve())  # Always returns absolute path

# Usage
CSV_PATH = get_absolute_path(
    "DEXCOM_CSV_PATH",
    "/var/lib/dexcom-readings/readings.csv"
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Self-daemonization (fork/setsid) | Foreground + service manager | ~2015 with systemd adoption | Simpler code, better supervision |
| Simple PID file | File-locked PID | Longstanding best practice | No stale PID files |
| Internal log rotation | External logrotate + SIGHUP | Standard Unix practice | Centralized log management |
| Hardcoded paths | Environment variable configuration | Modern DevOps practice | Portable across environments |

**Deprecated/outdated:**
- `Type=forking` in systemd: Use `Type=simple` with foreground processes whenever possible
- `syslog` module (direct): Prefer `logging.handlers.SysLogHandler` for structured logging integration
- Manual `fork()`/`setsid()`: Use service managers or `python-daemon` library

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | XDG Base Directory paths are appropriate defaults | Pattern 4 | May need different defaults for different platforms |
| A2 | `/var/run/syslog` is the syslog socket on macOS | Code Examples | macOS 12+ changed syslog behavior; may need fallback to file logging only |

## Open Questions

1. **Should `python-daemon` be a dependency?**
   - What we know: Modern service managers (systemd, launchd) make self-daemonization unnecessary.
   - What's unclear: Whether users might run the script standalone without a service manager.
   - Recommendation: Make it an optional dependency. Primary use case is service-managed deployment.

2. **macOS syslog availability?**
   - What we know: macOS 12+ Monterey changed syslog daemon behavior.
   - What's unclear: Whether local syslog is reliable on modern macOS.
   - Recommendation: Default to file logging on macOS. Document syslog as Linux-focused.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | Runtime | Yes | 3.9.6 | - |
| pydexcom | Dexcom API | Yes | 0.5.1 | - |
| requests | Nightscout API | Yes | 2.32.5 | - |
| systemd | Linux service | No | - | Use launchd or standalone |
| launchd | macOS service | Yes | 7.0.0 | - |
| python-daemon | Self-daemonization | No | - | Not required for service-managed deployment |
| systemd-python | Journal logging | No | - | Use file or syslog logging |

**Missing dependencies with no fallback:**
- None blocking. All core functionality achievable with stdlib.

**Missing dependencies with fallback:**
- `python-daemon`: Not required when using systemd/launchd
- `systemd-python`: Can use `SysLogHandler` or file logging instead

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | unittest (Python stdlib) |
| Config file | None - tests in `dexcom_readings_test.py` |
| Quick run command | `python -m unittest dexcom_readings_test -v` |
| Full suite command | `python -m unittest dexcom_readings_test -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DAEMON-01 | Absolute configurable file paths | unit | `python -m unittest dexcom_readings_test.TestDaemonPaths -v` | Wave 0 needed |
| DAEMON-02 | PID file prevents multiple instances | unit | `python -m unittest dexcom_readings_test.TestPIDFile -v` | Wave 0 needed |
| DAEMON-03 | Configurable logging (syslog, file, console) | unit | `python -m unittest dexcom_readings_test.TestLoggingConfig -v` | Wave 0 needed |
| DAEMON-04 | SIGHUP triggers log file reopen | unit | `python -m unittest dexcom_readings_test.TestSIGHUP -v` | Wave 0 needed |
| DAEMON-05 | Service templates provided and documented | manual | - | Wave 0 needed |

### Sampling Rate
- **Per task commit:** `python -m unittest dexcom_readings_test -v`
- **Per wave merge:** `python -m unittest dexcom_readings_test -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_daemon.py` or additions to `dexcom_readings_test.py` — covers DAEMON-01 through DAEMON-04
- [ ] Service template files — `service/dexcom-readings.service` and `service/com.dexcom.readings.plist`
- [ ] Documentation update — README.md daemon deployment section

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A - no authentication in this service |
| V3 Session Management | no | N/A - no sessions |
| V4 Access Control | no | N/A - no access control |
| V5 Input Validation | yes | Environment variables validated before use |
| V6 Cryptography | no | N/A - no crypto operations |

### Known Threat Patterns for Python Daemon

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| PID file race condition | Tampering | Use `fcntl.flock()` for atomic locking |
| Log injection | Tampering | Sanitize user inputs before logging |
| Credential exposure in logs | Information Disclosure | Never log credentials; use environment variables |
| Path traversal in config | Tampering | Validate paths are within expected directories |
| Privilege escalation | Elevation | Run as non-root user; use `NoNewPrivileges=true` in systemd |

## Sources

### Primary (HIGH confidence)
- [Python logging.handlers documentation](https://docs.python.org/3/library/logging.handlers.html) - WatchedFileHandler, SysLogHandler, RotatingFileHandler details
- [PEP 3143 - Standard daemon process library](https://peps.python.org/pep-3143) - DaemonContext specification
- [Apple Developer Documentation - Creating Launch Daemons and Agents](https://developer.apple.com/library/mac/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html) - launchd plist format

### Secondary (MEDIUM confidence)
- [Stack Overflow: Single instance of python daemon](https://stackoverflow.com/questions/21990439/single-instance-of-a-python-daemon-with-python-daemon) - PID locking patterns
- [Stack Overflow: Rotate/reopen file in Python3 when signal received](https://stackoverflow.com/questions/62036007/rotate-reopen-file-in-python3-when-signal-is-received) - SIGHUP log rotation
- [Stack Overflow: Configure logging to syslog in Python](https://stackoverflow.com/questions/3968669/how-to-configure-logging-to-syslog-in-python) - SysLogHandler configuration
- [Python in Plain English: Daemons and systemd](https://python.plainenglish.io/linux-for-pythonistas-daemons-and-background-services-with-systemd-df70e62c482e) - systemd best practices

### Tertiary (LOW confidence)
- [AndyPi: Python script as launchd service](https://andypi.co.uk/2023/02/14/how-to-run-a-python-script-as-a-service-on-mac-os/) - Practical launchd examples
- [DEV Community: Crash-tolerant agent with launchd](https://dev.to/whoffagents/how-to-build-a-crash-tolerant-ai-agent-with-launchd-on-macos-454) - Advanced launchd patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All components are Python stdlib or well-established libraries
- Architecture: HIGH - Patterns verified against official documentation and PEP 3143
- Pitfalls: HIGH - Common issues documented from multiple Stack Overflow sources and official docs

**Research date:** 2026-04-24
**Valid until:** 30 days - daemon patterns are stable; Python stdlib APIs are long-term stable