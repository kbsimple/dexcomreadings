# Architecture

**Analysis Date:** 2026-04-19

## Pattern Overview

**Overall:** Polling Daemon (Long-running service script)

**Key Characteristics:**
- Single-file monolithic script with no modular separation
- Event-driven polling loop with state tracking
- Dual output sinks: local CSV file and remote Nightscout API
- Configuration entirely through environment variables
- No class-based design - procedural with global state

## Layers

**Main Script (`dexcom_readings.py`):**
- Purpose: Core application logic - polling, processing, and output
- Location: `/Users/ffaber/claude-projects/dexcomreadings/dexcom_readings.py`
- Contains: All business logic, API clients, CSV handling, configuration
- Depends on: pydexcom (Dexcom API), requests (HTTP), standard library
- Used by: Direct execution via `python dexcom_readings.py`

**Test Layer (`dexcom_readings_test.py`):**
- Purpose: Unit tests for main script functionality
- Location: `/Users/ffaber/claude-projects/dexcomreadings/dexcom_readings_test.py`
- Contains: unittest test cases with mocked dependencies
- Depends on: unittest, unittest.mock, main module
- Used by: Test runner (`python -m unittest`)

## Data Flow

**Glucose Reading Pipeline:**

1. Polling loop wakes at configured interval (default: 60 seconds)
2. Fetch current glucose reading from Dexcom Share API via pydexcom
3. Compare reading timestamp against `last_known_glucose_timestamp`
4. If new reading:
   - Log to console with timestamp and value
   - Write full reading data to CSV file
   - Upload to Nightscout API (if configured)
5. If duplicate/old reading:
   - Log "No new reading" with last known timestamp
   - Write row with `new_reading_received=False`
6. Sleep until next poll cycle

**State Management:**
- Single global variable: `last_known_glucose_timestamp` tracks most recent reading
- State persists only in-memory (lost on restart)
- CSV file serves as persistent log/audit trail

## Key Abstractions

**Glucose Reading Object:**
- Purpose: Represents a single CGM reading from pydexcom
- Source: `pydexcom.GlucoseReading` (external library type)
- Properties used: `value` (mg/dL), `datetime` (UTC), `trend_description`, `trend_arrow`
- Mocked in tests via `MockGlucoseReading` class in test file

**Dexcom Client:**
- Purpose: Authentication and data retrieval from Dexcom Share servers
- Implementation: `pydexcom.Dexcom` class instance
- Created by: `initialize_dexcom_client()` function
- Region support: US (default) and OUS (outside US) via `ous=True` parameter

**Nightscout Entry:**
- Purpose: API payload for Nightscout upload
- Format: JSON object with `dateString`, `sgv`, `direction`, `type` fields
- Endpoint: `{NIGHTSCOUT_URL}/api/v1/entries`

## Entry Points

**Script Entry (`if __name__ == "__main__"`):**
- Location: Bottom of `dexcom_readings.py` (lines 193-198)
- Triggers: Direct Python execution
- Responsibilities:
  - Check/create CSV file with headers if not exists
  - Call `main()` to start polling loop

**Main Function:**
- Location: `dexcom_readings.py`, lines 118-191
- Triggers: Called from script entry point
- Responsibilities:
  - Initialize Dexcom client
  - Validate Nightscout configuration
  - Run infinite polling loop
  - Handle errors gracefully (continue on failure)

## Error Handling

**Strategy:** Graceful degradation with logging

**Patterns:**
- Client initialization failure: Log error, return None, exit from main with code 1
- Glucose fetch failure: Log warning, write row with all None values, continue polling
- Nightscout upload failure: Log error, continue polling (upload is optional)
- Missing config: Log warning, skip optional features (Nightscout), continue

**No exceptions propagate:** All exceptions caught and logged within functions

## Cross-Cutting Concerns

**Logging:**
- Framework: Python `logging` module
- Level: INFO (default)
- Format: `%(asctime)s - %(levelname)s - %(message)s`
- Output: Console (stdout)
- Suppression: External library logging can be suppressed if needed (commented code)

**Configuration:**
- All config via environment variables
- Required: `DEXCOM_USERNAME`, `DEXCOM_PASSWORD`
- Optional: `DEXCOM_REGION` (default: "us"), `NIGHTSCOUT_URL`, `NIGHTSCOUT_API_SECRET`
- Constants: `POLLING_INTERVAL_SECONDS` (60), `OUTPUT_CSV_FILE` ("dexcom_readings_log.csv")

**Authentication:**
- Dexcom: Username/password via pydexcom library
- Nightscout: API secret passed in `api-secret` header

---

*Architecture analysis: 2026-04-19*