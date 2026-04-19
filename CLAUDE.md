  ## Conventions                                                                                                          
                                                                                                                          
  ### Git Commit Author                                                                                                   
                                                                                                                          
  All commits must use:                                                                                                   
  - **Author name:** Faiser                                                                                               
  - **Email:** keepbreakfastsimple@gmail.com

<!-- GSD:project-start source:PROJECT.md -->
## Project

**Dexcom Readings**

A Dexcom CGM (Continuous Glucose Monitor) data polling and forwarding service. It fetches real-time glucose readings from the Dexcom Share API and forwards them to Nightscout (a diabetes management platform) with local CSV logging. Users are people with diabetes who want to replicate their CGM data for monitoring and analysis.

**Core Value:** Reliable, continuous glucose data replication from Dexcom to Nightscout without data loss.

### Constraints

- **Tech Stack:** Python 3, pydexcom library, requests library
- **Compatibility:** Must work with existing Dexcom Share API and Nightscout API
- **Dependencies:** Third-party `pydexcom` library (no version currently pinned)
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.x - Core application logic in `dexcom_readings.py` and test file `dexcom_readings_test.py`
- None detected
## Runtime
- Python 3.x (exact version not specified in project files)
- No package manager configuration detected
- No `requirements.txt`, `pyproject.toml`, or `setup.py` present
- Dependencies must be installed manually via `pip install pydexcom requests`
## Frameworks
- None (standard library only for main application)
- `unittest` - Python standard library testing framework
- `unittest.mock` - Built-in mocking utilities for test isolation
- No build tools detected
- Scripts run directly via `python dexcom_readings.py`
## Key Dependencies
- `pydexcom` - Third-party library for Dexcom Share API integration. Provides `Dexcom` client class for authentication and glucose data retrieval
- `requests` - HTTP client library used for Nightscout API uploads
- `csv` - CSV file I/O for local data logging
- `datetime` - Timestamp handling and UTC time operations
- `os` - Environment variable access for configuration
- `time` - Sleep functionality for polling interval
- `logging` - Application logging
## Configuration
- All configuration via environment variables
- Required: `DEXCOM_USERNAME`, `DEXCOM_PASSWORD`
- Optional: `DEXCOM_REGION` (defaults to "us")
- Nightscout: `NIGHTSCOUT_URL`, `NIGHTSCOUT_API_SECRET`
- No build configuration files
- No `.python-version` file detected
## Platform Requirements
- Python 3.x runtime
- `pydexcom` and `requests` packages installed
- Dexcom Share account credentials
- Same as development
- Designed for continuous polling (60-second intervals)
- Can be deployed on any system with Python runtime
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Snake_case: `dexcom_readings.py`, `dexcom_readings_test.py`
- Test files: `<module>_test.py` suffix
- Snake_case: `initialize_dexcom_client()`, `get_latest_glucose_reading()`, `write_to_csv()`, `upload_to_nightscout()`
- Descriptive verbs: `initialize_`, `get_`, `write_`, `upload_`
- Snake_case for locals: `glucose_value_to_log`, `current_glucose_datetime`
- Descriptive names preferred over short ones
- UPPER_SNAKE_CASE at module level: `DEXCOM_USERNAME`, `POLLING_INTERVAL_SECONDS`, `OUTPUT_CSV_FILE`, `CSV_HEADERS`
- PascalCase: `MockGlucoseReading`, `TestDexcomReadings`
## Code Style
- No formal formatter config detected (no `.prettierrc`, `pyproject.toml`, etc.)
- Line length appears to follow PEP 8 style with some flexibility
- Comment `# noqa: E501` indicates awareness of line length linting
- No explicit linting config files present
- Implicit adherence to PEP 8 conventions
- 4 spaces (Python standard)
- f-strings used consistently for interpolation:
## Import Organization
## Error Handling
- Try-except blocks with specific exception types
- Return `None` on failure rather than raising custom exceptions
- Log errors before returning:
- Use `exit(1)` for fatal errors in `main()`
- Functions return `None` for caller to handle
## Logging
- Use `logging.info()` for normal operations
- Use `logging.error()` for failures
- Use `logging.warning()` for non-critical issues
- Include context in log messages with f-strings
## Comments
- Inline comments for important clarifications (e.g., `# IMPORTANT: Store your credentials securely`)
- Commented-out code with explanatory notes for optional behavior
- Single-line docstrings for functions:
## Function Design
- Return objects on success, `None` on failure
- No explicit type hints used
## Module Design
- Configuration loaded from environment variables at module load time
- Mutable global state: `last_known_glucose_timestamp` used to track readings
## Configuration
- All configuration via `os.environ.get()`
- Default values provided for optional settings:
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Single-file monolithic script with no modular separation
- Event-driven polling loop with state tracking
- Dual output sinks: local CSV file and remote Nightscout API
- Configuration entirely through environment variables
- No class-based design - procedural with global state
## Layers
- Purpose: Core application logic - polling, processing, and output
- Location: `/Users/ffaber/claude-projects/dexcomreadings/dexcom_readings.py`
- Contains: All business logic, API clients, CSV handling, configuration
- Depends on: pydexcom (Dexcom API), requests (HTTP), standard library
- Used by: Direct execution via `python dexcom_readings.py`
- Purpose: Unit tests for main script functionality
- Location: `/Users/ffaber/claude-projects/dexcomreadings/dexcom_readings_test.py`
- Contains: unittest test cases with mocked dependencies
- Depends on: unittest, unittest.mock, main module
- Used by: Test runner (`python -m unittest`)
## Data Flow
- Single global variable: `last_known_glucose_timestamp` tracks most recent reading
- State persists only in-memory (lost on restart)
- CSV file serves as persistent log/audit trail
## Key Abstractions
- Purpose: Represents a single CGM reading from pydexcom
- Source: `pydexcom.GlucoseReading` (external library type)
- Properties used: `value` (mg/dL), `datetime` (UTC), `trend_description`, `trend_arrow`
- Mocked in tests via `MockGlucoseReading` class in test file
- Purpose: Authentication and data retrieval from Dexcom Share servers
- Implementation: `pydexcom.Dexcom` class instance
- Created by: `initialize_dexcom_client()` function
- Region support: US (default) and OUS (outside US) via `ous=True` parameter
- Purpose: API payload for Nightscout upload
- Format: JSON object with `dateString`, `sgv`, `direction`, `type` fields
- Endpoint: `{NIGHTSCOUT_URL}/api/v1/entries`
## Entry Points
- Location: Bottom of `dexcom_readings.py` (lines 193-198)
- Triggers: Direct Python execution
- Responsibilities:
- Location: `dexcom_readings.py`, lines 118-191
- Triggers: Called from script entry point
- Responsibilities:
## Error Handling
- Client initialization failure: Log error, return None, exit from main with code 1
- Glucose fetch failure: Log warning, write row with all None values, continue polling
- Nightscout upload failure: Log error, continue polling (upload is optional)
- Missing config: Log warning, skip optional features (Nightscout), continue
## Cross-Cutting Concerns
- Framework: Python `logging` module
- Level: INFO (default)
- Format: `%(asctime)s - %(levelname)s - %(message)s`
- Output: Console (stdout)
- Suppression: External library logging can be suppressed if needed (commented code)
- All config via environment variables
- Required: `DEXCOM_USERNAME`, `DEXCOM_PASSWORD`
- Optional: `DEXCOM_REGION` (default: "us"), `NIGHTSCOUT_URL`, `NIGHTSCOUT_API_SECRET`
- Constants: `POLLING_INTERVAL_SECONDS` (60), `OUTPUT_CSV_FILE` ("dexcom_readings_log.csv")
- Dexcom: Username/password via pydexcom library
- Nightscout: API secret passed in `api-secret` header
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
