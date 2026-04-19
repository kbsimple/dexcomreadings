# Technology Stack

**Analysis Date:** 2026-04-19

## Languages

**Primary:**
- Python 3.x - Core application logic in `dexcom_readings.py` and test file `dexcom_readings_test.py`

**Secondary:**
- None detected

## Runtime

**Environment:**
- Python 3.x (exact version not specified in project files)

**Package Manager:**
- No package manager configuration detected
- No `requirements.txt`, `pyproject.toml`, or `setup.py` present
- Dependencies must be installed manually via `pip install pydexcom requests`

## Frameworks

**Core:**
- None (standard library only for main application)

**Testing:**
- `unittest` - Python standard library testing framework
- `unittest.mock` - Built-in mocking utilities for test isolation

**Build/Dev:**
- No build tools detected
- Scripts run directly via `python dexcom_readings.py`

## Key Dependencies

**Critical:**
- `pydexcom` - Third-party library for Dexcom Share API integration. Provides `Dexcom` client class for authentication and glucose data retrieval
- `requests` - HTTP client library used for Nightscout API uploads

**Standard Library:**
- `csv` - CSV file I/O for local data logging
- `datetime` - Timestamp handling and UTC time operations
- `os` - Environment variable access for configuration
- `time` - Sleep functionality for polling interval
- `logging` - Application logging

## Configuration

**Environment:**
- All configuration via environment variables
- Required: `DEXCOM_USERNAME`, `DEXCOM_PASSWORD`
- Optional: `DEXCOM_REGION` (defaults to "us")
- Nightscout: `NIGHTSCOUT_URL`, `NIGHTSCOUT_API_SECRET`

**Build:**
- No build configuration files
- No `.python-version` file detected

## Platform Requirements

**Development:**
- Python 3.x runtime
- `pydexcom` and `requests` packages installed
- Dexcom Share account credentials

**Production:**
- Same as development
- Designed for continuous polling (60-second intervals)
- Can be deployed on any system with Python runtime

---

*Stack analysis: 2026-04-19*