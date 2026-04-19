# Coding Conventions

**Analysis Date:** 2026-04-19

## Naming Patterns

**Files:**
- Snake_case: `dexcom_readings.py`, `dexcom_readings_test.py`
- Test files: `<module>_test.py` suffix

**Functions:**
- Snake_case: `initialize_dexcom_client()`, `get_latest_glucose_reading()`, `write_to_csv()`, `upload_to_nightscout()`
- Descriptive verbs: `initialize_`, `get_`, `write_`, `upload_`

**Variables:**
- Snake_case for locals: `glucose_value_to_log`, `current_glucose_datetime`
- Descriptive names preferred over short ones

**Constants:**
- UPPER_SNAKE_CASE at module level: `DEXCOM_USERNAME`, `POLLING_INTERVAL_SECONDS`, `OUTPUT_CSV_FILE`, `CSV_HEADERS`

**Classes (in tests):**
- PascalCase: `MockGlucoseReading`, `TestDexcomReadings`

## Code Style

**Formatting:**
- No formal formatter config detected (no `.prettierrc`, `pyproject.toml`, etc.)
- Line length appears to follow PEP 8 style with some flexibility
- Comment `# noqa: E501` indicates awareness of line length linting

**Linting:**
- No explicit linting config files present
- Implicit adherence to PEP 8 conventions

**Indentation:**
- 4 spaces (Python standard)

**String Formatting:**
- f-strings used consistently for interpolation:
```python
logging.info(f"Connecting to Dexcom Share for user {DEXCOM_USERNAME} "
      f"in region {DEXCOM_REGION}...")
```

## Import Organization

**Order:**
1. Standard library: `csv`, `datetime`, `os`, `time`, `logging`
2. Third-party: `requests`, `pydexcom`
3. Local modules: No explicit local imports in this codebase

**Style:**
```python
import csv
import datetime
import os
import time
import logging
import requests
from pydexcom import Dexcom
```

## Error Handling

**Patterns:**
- Try-except blocks with specific exception types
- Return `None` on failure rather than raising custom exceptions
- Log errors before returning:

```python
try:
    bg = dexcom_client.get_current_glucose_reading()
    return bg
except Exception as e:
    logging.error(f"Error fetching glucose reading: {e}")
    return None
```

**Exit handling:**
- Use `exit(1)` for fatal errors in `main()`
- Functions return `None` for caller to handle

## Logging

**Framework:** Python `logging` module

**Configuration:**
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')
```

**Patterns:**
- Use `logging.info()` for normal operations
- Use `logging.error()` for failures
- Use `logging.warning()` for non-critical issues
- Include context in log messages with f-strings

## Comments

**When to Comment:**
- Inline comments for important clarifications (e.g., `# IMPORTANT: Store your credentials securely`)
- Commented-out code with explanatory notes for optional behavior

**Docstrings:**
- Single-line docstrings for functions:
```python
def initialize_dexcom_client():
    """Initializes and returns the Dexcom client."""
```

## Function Design

**Size:** Functions are moderately sized (10-30 lines typically)

**Parameters:** Minimal parameters; functions rely on module-level globals for configuration

**Return Values:**
- Return objects on success, `None` on failure
- No explicit type hints used

**Example pattern:**
```python
def get_latest_glucose_reading(dexcom_client):
    """Fetches the latest glucose reading from Dexcom."""
    if not dexcom_client:
        return None
    try:
        bg = dexcom_client.get_current_glucose_reading()
        return bg
    except Exception as e:
        logging.error(f"Error fetching glucose reading: {e}")
        return None
```

## Module Design

**Exports:** No explicit `__all__` declaration; all functions are module-level

**Global State:**
- Configuration loaded from environment variables at module load time
- Mutable global state: `last_known_glucose_timestamp` used to track readings

**Entry Point:**
```python
if __name__ == "__main__":
    # Setup logic
    main()
```

## Configuration

**Environment Variables:**
- All configuration via `os.environ.get()`
- Default values provided for optional settings:
```python
DEXCOM_REGION = os.environ.get("DEXCOM_REGION", "us")
```

**No config files:** Configuration is purely environment-based

---

*Convention analysis: 2026-04-19*