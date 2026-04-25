---
phase: 04
slug: system-daemon-compatibility
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-24
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | unittest (Python stdlib) |
| **Config file** | none — existing test file |
| **Quick run command** | `python -m unittest dexcom_readings_test -v` |
| **Full suite command** | `python -m unittest dexcom_readings_test -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m unittest dexcom_readings_test -v`
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | DAEMON-01 | T-04-01 | Paths validated before use | unit | `python -m unittest dexcom_readings_test.TestDaemonPaths -v` | ✅ exists | ⬜ pending |
| 04-01-02 | 01 | 1 | DAEMON-02 | T-04-02 | PID file with fcntl locking | unit | `python -m unittest dexcom_readings_test.TestPIDFile -v` | ✅ exists | ⬜ pending |
| 04-02-01 | 02 | 2 | DAEMON-03 | T-04-04 | Logging destinations validated | unit | `python -m unittest dexcom_readings_test.TestLoggingConfig -v` | ✅ exists | ⬜ pending |
| 04-02-02 | 02 | 2 | DAEMON-04 | — | SIGHUP handler sets flag | unit | `python -m unittest dexcom_readings_test.TestSIGHUP -v` | ✅ exists | ⬜ pending |
| 04-03-01 | 03 | 1 | DAEMON-05 | T-04-07, T-04-08 | Service templates with secure paths | manual | `grep -E "^\[Unit\]|ExecStart=" service/dexcom-readings.service` | ❌ W0 | ⬜ pending |
| 04-03-02 | 03 | 1 | DAEMON-05 | T-04-07 | launchd plist with secure paths | manual | `plutil -lint service/com.dexcom.readings.plist` | ❌ W0 | ⬜ pending |
| 04-03-03 | 03 | 1 | DAEMON-05 | — | README documents daemon deployment | manual | `grep "## Daemon Deployment" README.md` | ❌ W0 | ⬜ pending |
| 04-04-01 | 04 | 3 | DAEMON-01, DAEMON-02 | — | Tests for path and PID | unit | `python -m unittest dexcom_readings_test.TestDaemonPaths dexcom_readings_test.TestPIDFile -v` | ✅ exists | ⬜ pending |
| 04-04-02 | 04 | 3 | DAEMON-03, DAEMON-04 | — | Tests for logging and SIGHUP | unit | `python -m unittest dexcom_readings_test.TestLoggingConfig dexcom_readings_test.TestSIGHUP -v` | ✅ exists | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `service/dexcom-readings.service` — systemd unit template
- [ ] `service/com.dexcom.readings.plist` — launchd plist template
- [ ] README.md update — Daemon Deployment section

*Test infrastructure exists in dexcom_readings_test.py.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| systemd service deployment | DAEMON-05 | Requires root/system access | Follow README instructions, verify `systemctl status dexcom-readings` shows active |
| launchd service deployment | DAEMON-05 | Requires macOS system access | Follow README instructions, verify `launchctl list \| grep dexcom` shows loaded |
| log rotation with SIGHUP | DAEMON-04 | Requires external logrotate | Trigger logrotate, verify daemon reopens log file |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter (after verification)

**Approval:** pending