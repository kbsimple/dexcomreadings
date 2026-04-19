# Testing Patterns

**Analysis Date:** 2026-04-19

## Test Framework

**Runner:**
- `unittest` (Python standard library)
- No config file (no `pytest.ini`, `tox.ini`, `setup.cfg`)

**Assertion Library:**
- `unittest.TestCase` assertion methods

**Run Commands:**
```bash
python dexcom_readings_test.py              # Run all tests
python -m unittest dexcom_readings_test     # Alternative
python -m unittest discover                 # Discover tests
```

## Test File Organization

**Location:**
- Co-located: `dexcom_readings_test.py` in same directory as `dexcom_readings.py`

**Naming:**
- Pattern: `<module>_test.py`

**Structure:**
```
[project-root]/
├── dexcom_readings.py          # Main module
└── dexcom_readings_test.py     # Test file
```

## Test Structure

**Suite Organization:**
```python
class TestDexcomReadings(unittest.TestCase):

    def setUp(self):
        # Reset global state from the module if necessary
        dexcom_readings.last_known_glucose_timestamp = None
        self._original_sys_exit = sys.exit

    def tearDown(self):
        sys.exit = self._original_sys_exit

    def test_initialize_dexcom_client_success_us(self, ...):
        # Test implementation
```

**Patterns:**
- **Setup**: Reset module-level global state in `setUp()`
- **Teardown**: Restore patched system functions
- **Test naming**: `test_<function_name>_<scenario>` pattern

## Mocking

**Framework:** `unittest.mock` with `patch`, `MagicMock`, `mock_open`

**Patterns:**
```python
# Decorator-based patching (most common)
@patch('dexcom_readings.Dexcom')
@patch('builtins.print')
@patch('builtins.exit')
def test_initialize_dexcom_client_success_us(self, mock_exit, mock_print, mock_pydexcom_dexcom):
    mock_client_instance = MagicMock()
    mock_pydexcom_dexcom.return_value = mock_client_instance
    # ...

# Context manager patching for environment variables
with patch.dict(os.environ, {"DEXCOM_USERNAME": "testuser", "DEXCOM_PASSWORD": "testpassword"}):
    client = dexcom_readings.initialize_dexcom_client()

# Patching module globals
with patch('dexcom_readings.DEXCOM_USERNAME', None), \
     patch('dexcom_readings.DEXCOM_PASSWORD', "testpassword"):
    client = dexcom_readings.initialize_dexcom_client()

# Mocking file operations
@patch('dexcom_readings.csv.writer')
@patch('builtins.open', new_callable=mock_open)
@patch('os.path.isfile')
def test_write_to_csv_new_file(self, mock_isfile, mock_open_func, mock_csv_writer_constructor):
    # ...
```

**What to Mock:**
- External API clients: `Dexcom` from pydexcom
- File I/O: `builtins.open`, `csv.writer`, `os.path.isfile`
- System functions: `builtins.exit`, `time.sleep`
- Environment variables: `os.environ` via `patch.dict`

**What NOT to Mock:**
- Module under test functions (call actual logic where possible)
- Simple data structures

## Test Data

**Helper Classes:**
```python
class MockGlucoseReading:
    def __init__(self, value, trend_description, trend_arrow, dt_obj):
        self.value = value
        self.trend_description = trend_description
        self.trend_arrow = trend_arrow
        self.datetime = dt_obj

    def __gt__(self, other_datetime):
        if isinstance(other_datetime, datetime.datetime):
            return self.datetime > other_datetime
        return NotImplemented
```

**Location:**
- Defined at top of test file
- Mimics external library's data structures

**Fixture pattern:**
```python
# Create test data inline
glucose_time = datetime.datetime(2023, 1, 1, 11, 55, 0)
mock_glucose_reading = MockGlucoseReading(120, "Rising Fast", "↑↑", glucose_time)
```

## Coverage

**Requirements:** No coverage enforcement detected

**View Coverage:**
```bash
coverage run -m unittest dexcom_readings_test
coverage report -m
```

## Test Types

**Unit Tests:**
- Primary test type in codebase
- Test individual functions in isolation
- Mock all external dependencies

**Integration Tests:**
- Not explicitly present
- Test `main()` function simulates integration-like scenarios

**E2E Tests:**
- Not used

## Common Patterns

**Testing Infinite Loops:**
```python
# Use KeyboardInterrupt to break loop after one iteration
@patch('dexcom_readings.time.sleep', side_effect=KeyboardInterrupt)
def test_main_loop_new_reading(self, ..., mock_sleep):
    with self.assertRaises(KeyboardInterrupt):
        dexcom_readings.main()
```

**Testing Error Conditions:**
```python
# Set side_effect on mock to simulate exceptions
mock_pydexcom_dexcom.side_effect = Exception("API Connection Failed")
```

**Testing File Writing:**
```python
@patch('dexcom_readings.csv.writer')
@patch('builtins.open', new_callable=mock_open)
@patch('os.path.isfile')
def test_write_to_csv_new_file(self, mock_isfile, mock_open_func, mock_csv_writer_constructor):
    mock_isfile.return_value = False
    mock_csv_writer_instance = MagicMock()
    mock_csv_writer_constructor.return_value = mock_csv_writer_instance

    dexcom_readings.write_to_csv(data_row)

    mock_csv_writer_instance.writerow.assert_any_call(headers)
    mock_csv_writer_instance.writerow.assert_any_call(data_row)
```

**Verifying Call Arguments:**
```python
mock_pydexcom_dexcom.assert_called_once_with(username="testuser", password="testpassword")
mock_print.assert_any_call("Expected message")
mock_exit.assert_not_called()
```

## Test Coverage Gaps

**Observed Issues:**
- Tests mock `builtins.print` but production code uses `logging` module - tests may not verify actual log output correctly
- `upload_to_nightscout()` function has no dedicated tests
- Nightscout upload integration is untested

**Recommendations:**
- Add tests for `upload_to_nightscout()` function
- Update tests to mock `logging` instead of `builtins.print`
- Add integration tests with mock HTTP servers

---

*Testing analysis: 2026-04-19*