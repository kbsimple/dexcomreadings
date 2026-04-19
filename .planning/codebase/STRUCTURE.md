# Codebase Structure

**Analysis Date:** 2026-04-19

## Directory Layout

```
/Users/ffaber/claude-projects/dexcomreadings/
├── .git/                     # Git repository
├── .planning/                # Planning documents (generated)
│   └── codebase/             # Codebase analysis documents
├── CLAUDE.md                 # Project instructions for Claude
├── LICENSE                   # MIT License
├── dexcom_readings.py        # Main application script
└── dexcom_readings_test.py   # Unit tests
```

## Directory Purposes

**Root Directory:**
- Purpose: Contains entire application (flat structure)
- Contains: Main script, tests, license, documentation
- Key files: `dexcom_readings.py` (main), `dexcom_readings_test.py` (tests)

**`.planning/codebase/`:**
- Purpose: GSD planning system documents
- Contains: Architecture, stack, and convention analysis files
- Generated: Yes (by `/gsd-map-codebase` command)

## Key File Locations

**Entry Points:**
- `dexcom_readings.py`: Main script - run with `python dexcom_readings.py`
- `dexcom_readings_test.py`: Test suite - run with `python -m unittest dexcom_readings_test.py`

**Configuration:**
- No config files in repository
- Environment variables loaded at runtime from shell environment
- Required: `DEXCOM_USERNAME`, `DEXCOM_PASSWORD`
- Optional: `DEXCOM_REGION`, `NIGHTSCOUT_URL`, `NIGHTSCOUT_API_SECRET`

**Output Files (Generated at Runtime):**
- `dexcom_readings_log.csv`: Glucose reading log (created in working directory)

**Documentation:**
- `CLAUDE.md`: Project instructions for Claude AI assistant
- `LICENSE`: MIT License

## Naming Conventions

**Files:**
- Python files: `snake_case.py` (e.g., `dexcom_readings.py`, `dexcom_readings_test.py`)
- Test files: `{module}_test.py` suffix pattern
- Documentation: `UPPERCASE.md` for markdown docs

**Functions:**
- snake_case: `initialize_dexcom_client`, `get_latest_glucose_reading`, `write_to_csv`, `upload_to_nightscout`
- Private/internal indicated by context, not naming (no underscore prefix convention)

**Variables:**
- Module-level constants: `UPPER_SNAKE_CASE` (e.g., `DEXCOM_USERNAME`, `OUTPUT_CSV_FILE`, `POLLING_INTERVAL_SECONDS`)
- Local variables: `snake_case` (e.g., `glucose_value_to_log`, `current_bg`)
- Global state: `last_known_glucose_timestamp`

**Classes (in tests only):**
- PascalCase for test mocks: `MockGlucoseReading`

## Where to Add New Code

**New Feature (in existing script):**
- Add function to `dexcom_readings.py`
- Call from `main()` loop or as helper function
- Add corresponding test to `dexcom_readings_test.py`

**New Output Target (e.g., another API):**
- Add function similar to `upload_to_nightscout()` in `dexcom_readings.py`
- Add configuration constants at module top
- Call from main loop after getting new reading

**New Configuration Option:**
- Add environment variable retrieval near top of `dexcom_readings.py` (lines 10-18)
- Add validation in `main()` function

**New Test:**
- Add test method to `TestDexcomReadings` class in `dexcom_readings_test.py`
- Use `unittest.mock` for patching dependencies

## Special Directories

**`.git/`:**
- Purpose: Git version control
- Generated: No (managed by git)
- Committed: No (excluded)

**`.planning/`:**
- Purpose: GSD workflow planning documents
- Generated: Yes (by GSD commands)
- Committed: Yes (part of project documentation)

## Runtime File Locations

**Generated Files:**
- `dexcom_readings_log.csv`: Created in current working directory where script runs
- Location determined by `OUTPUT_CSV_FILE` constant

**Dependencies:**
- External: `pydexcom` (Dexcom API client), `requests` (HTTP library)
- Standard library: `csv`, `datetime`, `os`, `time`, `logging`
- Install: `pip install pydexcom requests` (no requirements.txt in repo)

---

*Structure analysis: 2026-04-19*