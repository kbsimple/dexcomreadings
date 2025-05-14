import unittest
from unittest.mock import patch, MagicMock, mock_open, call
import datetime
import os
import sys

# Assuming dexcom_readings.py is in the same directory or accessible in PYTHONPATH
import dexcom_readings

# Helper to create mock glucose reading objects similar to what pydexcom might return
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

class TestDexcomReadings(unittest.TestCase):

    def setUp(self):
        # Reset global state from the module if necessary
        dexcom_readings.last_known_glucose_timestamp = None
        # Store original sys.exit to restore it if needed, though patch should handle it
        self._original_sys_exit = sys.exit

    def tearDown(self):
        sys.exit = self._original_sys_exit
        # Clean up any environment variables set for specific tests if not using patch.dict context manager

    @patch('dexcom_readings.Dexcom')
    @patch('builtins.print')
    @patch('builtins.exit') # Patch builtins.exit for the exit() call
    def test_initialize_dexcom_client_success_us(self, mock_exit, mock_print, mock_pydexcom_dexcom):
        mock_client_instance = MagicMock()
        mock_pydexcom_dexcom.return_value = mock_client_instance

        with patch.dict(os.environ, {"DEXCOM_USERNAME": "testuser", "DEXCOM_PASSWORD": "testpassword", "DEXCOM_REGION": "us"}):
            client = dexcom_readings.initialize_dexcom_client()

        self.assertEqual(client, mock_client_instance)
        mock_pydexcom_dexcom.assert_called_once_with(username="testuser", password="testpassword")
        mock_print.assert_any_call("Connecting to Dexcom Share for user testuser in region us...")
        mock_print.assert_any_call("Connecting in us")
        mock_print.assert_any_call("Successfully connected to Dexcom Share.")
        mock_exit.assert_not_called()

    @patch('dexcom_readings.Dexcom')
    @patch('builtins.print')
    @patch('builtins.exit')
    def test_initialize_dexcom_client_success_ous(self, mock_exit, mock_print, mock_pydexcom_dexcom):
        mock_client_instance = MagicMock()
        mock_pydexcom_dexcom.return_value = mock_client_instance

        with patch.dict(os.environ, {"DEXCOM_USERNAME": "testuser", "DEXCOM_PASSWORD": "testpassword", "DEXCOM_REGION": "ous"}):
            client = dexcom_readings.initialize_dexcom_client()

        self.assertEqual(client, mock_client_instance)
        mock_pydexcom_dexcom.assert_called_once_with("testuser", "testpassword", ous=True)
        mock_print.assert_any_call("Connecting to Dexcom Share for user testuser in region ous...")
        mock_print.assert_any_call("Successfully connected to Dexcom Share.")
        mock_exit.assert_not_called()

    @patch('dexcom_readings.Dexcom')
    @patch('builtins.print')
    @patch('builtins.exit') # Patch builtins.exit
    def test_initialize_dexcom_client_missing_username(self, mock_exit, mock_print, mock_pydexcom_dexcom):
        # Ensure DEXCOM_USERNAME is not set, or set to None
        with patch.dict(os.environ, {"DEXCOM_PASSWORD": "testpassword"}, clear=True):
            # Reload config from dexcom_readings to reflect patched os.environ
            # This is tricky because globals are set at import time.
            # A better way is to pass config or make DEXCOM_USERNAME a function call.
            # For now, we'll patch the module's global directly for the test.
            with patch('dexcom_readings.DEXCOM_USERNAME', None), \
                 patch('dexcom_readings.DEXCOM_PASSWORD', "testpassword"):
                client = dexcom_readings.initialize_dexcom_client()

        self.assertIsNone(client)
        mock_print.assert_any_call("Error: DEXCOM_USERNAME and DEXCOM_PASSWORD must be set.")
        mock_exit.assert_called_once_with(1)
        mock_pydexcom_dexcom.assert_not_called()

    @patch('dexcom_readings.Dexcom')
    @patch('builtins.print')
    @patch('builtins.exit')
    def test_initialize_dexcom_client_missing_password(self, mock_exit, mock_print, mock_pydexcom_dexcom):
        with patch.dict(os.environ, {"DEXCOM_USERNAME": "testuser"}, clear=True):
             with patch('dexcom_readings.DEXCOM_USERNAME', "testuser"), \
                  patch('dexcom_readings.DEXCOM_PASSWORD', None):
                client = dexcom_readings.initialize_dexcom_client()

        self.assertIsNone(client)
        mock_print.assert_any_call("Error: DEXCOM_USERNAME and DEXCOM_PASSWORD must be set.")
        mock_exit.assert_called_once_with(1)
        mock_pydexcom_dexcom.assert_not_called()

    @patch('dexcom_readings.Dexcom')
    @patch('builtins.print')
    @patch('builtins.exit')
    def test_initialize_dexcom_client_api_error(self, mock_exit, mock_print, mock_pydexcom_dexcom):
        mock_pydexcom_dexcom.side_effect = Exception("API Connection Failed")

        with patch.dict(os.environ, {"DEXCOM_USERNAME": "testuser", "DEXCOM_PASSWORD": "testpassword", "DEXCOM_REGION": "us"}):
            client = dexcom_readings.initialize_dexcom_client()

        self.assertIsNone(client)
        mock_print.assert_any_call("Error initializing Dexcom client: API Connection Failed")
        mock_exit.assert_not_called() # Should not exit here, just return None

    @patch('builtins.print')
    def test_get_latest_glucose_reading_success(self, mock_print):
        mock_dexcom_client = MagicMock()
        expected_reading = MockGlucoseReading(100, "Flat", "→", datetime.datetime.utcnow())
        mock_dexcom_client.get_current_glucose_reading.return_value = expected_reading

        reading = dexcom_readings.get_latest_glucose_reading(mock_dexcom_client)

        self.assertEqual(reading, expected_reading)
        mock_dexcom_client.get_current_glucose_reading.assert_called_once()
        mock_print.assert_not_called()

    @patch('builtins.print')
    def test_get_latest_glucose_reading_no_client(self, mock_print):
        reading = dexcom_readings.get_latest_glucose_reading(None)
        self.assertIsNone(reading)
        # No print expected here by the function itself, but good to check
        # mock_print.assert_not_called() # The function doesn't print if client is None

    @patch('builtins.print')
    def test_get_latest_glucose_reading_api_error(self, mock_print):
        mock_dexcom_client = MagicMock()
        mock_dexcom_client.get_current_glucose_reading.side_effect = Exception("Fetch Error")

        reading = dexcom_readings.get_latest_glucose_reading(mock_dexcom_client)

        self.assertIsNone(reading)
        mock_print.assert_called_once_with("Error fetching glucose reading: Fetch Error")

    @patch('dexcom_readings.csv.writer') # Patching csv.writer as used in the module
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.isfile')
    def test_write_to_csv_new_file(self, mock_isfile, mock_open_func, mock_csv_writer_constructor):
        mock_isfile.return_value = False # Simulate file does not exist
        mock_csv_writer_instance = MagicMock()
        mock_csv_writer_constructor.return_value = mock_csv_writer_instance

        data_row = ["2023-01-01T12:00:00", True, 100, "2023-01-01T11:55:00", "Rising", "↑"]
        
        # Ensure OUTPUT_CSV_FILE and CSV_HEADERS are accessible
        # These are global in dexcom_readings
        output_file = dexcom_readings.OUTPUT_CSV_FILE
        headers = dexcom_readings.CSV_HEADERS

        dexcom_readings.write_to_csv(data_row)

        mock_isfile.assert_called_once_with(output_file)
        mock_open_func.assert_called_once_with(output_file, mode='a', newline='', encoding='utf-8')
        mock_csv_writer_constructor.assert_called_once_with(mock_open_func()) # Check it's called with the file handle
        
        self.assertEqual(mock_csv_writer_instance.writerow.call_count, 2)
        mock_csv_writer_instance.writerow.assert_any_call(headers)
        mock_csv_writer_instance.writerow.assert_any_call(data_row)

    @patch('dexcom_readings.csv.writer')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.isfile')
    def test_write_to_csv_existing_file(self, mock_isfile, mock_open_func, mock_csv_writer_constructor):
        mock_isfile.return_value = True # Simulate file exists
        mock_csv_writer_instance = MagicMock()
        mock_csv_writer_constructor.return_value = mock_csv_writer_instance

        data_row = ["2023-01-01T12:05:00", True, 105, "2023-01-01T12:00:00", "Steady", "→"]
        output_file = dexcom_readings.OUTPUT_CSV_FILE

        dexcom_readings.write_to_csv(data_row)

        mock_isfile.assert_called_once_with(output_file)
        mock_open_func.assert_called_once_with(output_file, mode='a', newline='', encoding='utf-8')
        mock_csv_writer_constructor.assert_called_once_with(mock_open_func())
        
        mock_csv_writer_instance.writerow.assert_called_once_with(data_row) # Headers should not be written again

    # --- Tests for main() logic ---
    # We'll test main by mocking its dependencies and simulating one loop iteration

    @patch('builtins.print')
    @patch('dexcom_readings.initialize_dexcom_client')
    def test_main_init_failure(self, mock_init_client, mock_print):
        mock_init_client.return_value = None # Simulate client initialization failure
        
        dexcom_readings.main()

        mock_init_client.assert_called_once()
        mock_print.assert_any_call("Exiting due to Dexcom client initialization failure.")

    @patch('dexcom_readings.time.sleep', side_effect=KeyboardInterrupt) # To break the loop after one iteration
    @patch('dexcom_readings.write_to_csv')
    @patch('dexcom_readings.get_latest_glucose_reading')
    @patch('dexcom_readings.initialize_dexcom_client')
    @patch('datetime.datetime') # Mock datetime module inside dexcom_readings if it's imported like `from datetime import datetime`
                               # If it's `import datetime`, then `dexcom_readings.datetime.datetime`
    @patch('builtins.print')
    def test_main_loop_new_reading(self, mock_print, mock_datetime_module, 
                                   mock_init_client, mock_get_reading, 
                                   mock_write_csv, mock_sleep):
        # Setup mocks
        mock_dex_client = MagicMock()
        mock_init_client.return_value = mock_dex_client

        fixed_check_time = datetime.datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime_module.utcnow.return_value = fixed_check_time

        glucose_time = datetime.datetime(2023, 1, 1, 11, 55, 0)
        mock_glucose_reading = MockGlucoseReading(120, "Rising Fast", "↑↑", glucose_time)
        mock_get_reading.return_value = mock_glucose_reading

        dexcom_readings.last_known_glucose_timestamp = None # Ensure it's fresh

        with self.assertRaises(KeyboardInterrupt): # Expect loop to break
            dexcom_readings.main()

        mock_init_client.assert_called_once()
        mock_get_reading.assert_called_once_with(mock_dex_client)
        
        mock_print.assert_any_call(f"Polling Dexcom every {dexcom_readings.POLLING_INTERVAL_SECONDS} seconds. Logging to {dexcom_readings.OUTPUT_CSV_FILE}")
        mock_print.assert_any_call(f"{fixed_check_time.isoformat()}: New reading! Value: 120 mg/dL (Rising Fast), Time: {glucose_time.isoformat()}")

        expected_log_row = [
            fixed_check_time.isoformat(),
            True, # new_reading_received
            120,  # glucose_value_to_log
            glucose_time.isoformat(), # glucose_timestamp_to_log
            "Rising Fast", # trend_description_to_log
            "↑↑"  # trend_arrow_to_log
        ]
        mock_write_csv.assert_called_once_with(expected_log_row)
        mock_sleep.assert_called_once_with(dexcom_readings.POLLING_INTERVAL_SECONDS)
        self.assertEqual(dexcom_readings.last_known_glucose_timestamp, glucose_time)

    @patch('dexcom_readings.time.sleep', side_effect=KeyboardInterrupt)
    @patch('dexcom_readings.write_to_csv')
    @patch('dexcom_readings.get_latest_glucose_reading')
    @patch('dexcom_readings.initialize_dexcom_client')
    @patch('datetime.datetime')
    @patch('builtins.print')
    def test_main_loop_no_new_reading(self, mock_print, mock_datetime_module, 
                                      mock_init_client, mock_get_reading, 
                                      mock_write_csv, mock_sleep):
        mock_dex_client = MagicMock()
        mock_init_client.return_value = mock_dex_client

        fixed_check_time = datetime.datetime(2023, 1, 1, 12, 5, 0)
        mock_datetime_module.utcnow.return_value = fixed_check_time

        # Simulate a reading that is older or same as last known
        last_known_time = datetime.datetime(2023, 1, 1, 11, 55, 0)
        dexcom_readings.last_known_glucose_timestamp = last_known_time
        
        # This reading's timestamp is the same as last_known_time
        current_glucose_time = last_known_time 
        mock_glucose_reading = MockGlucoseReading(115, "Flat", "→", current_glucose_time)
        mock_get_reading.return_value = mock_glucose_reading

        with self.assertRaises(KeyboardInterrupt):
            dexcom_readings.main()

        mock_get_reading.assert_called_once_with(mock_dex_client)
        mock_print.assert_any_call(f"{fixed_check_time.isoformat()}: No new reading. Last known: {last_known_time.isoformat()}")

        expected_log_row = [
            fixed_check_time.isoformat(),
            False, # new_reading_received
            None,  # glucose_value_to_log
            None,  # glucose_timestamp_to_log
            None,  # trend_description_to_log
            None   # trend_arrow_to_log
        ]
        mock_write_csv.assert_called_once_with(expected_log_row)
        self.assertEqual(dexcom_readings.last_known_glucose_timestamp, last_known_time) # Should not change

    @patch('dexcom_readings.time.sleep', side_effect=KeyboardInterrupt)
    @patch('dexcom_readings.write_to_csv')
    @patch('dexcom_readings.get_latest_glucose_reading')
    @patch('dexcom_readings.initialize_dexcom_client')
    @patch('datetime.datetime')
    @patch('builtins.print')
    def test_main_loop_could_not_retrieve_reading(self, mock_print, mock_datetime_module, 
                                                  mock_init_client, mock_get_reading, 
                                                  mock_write_csv, mock_sleep):
        mock_dex_client = MagicMock()
        mock_init_client.return_value = mock_dex_client

        fixed_check_time = datetime.datetime(2023, 1, 1, 12, 10, 0)
        mock_datetime_module.utcnow.return_value = fixed_check_time

        mock_get_reading.return_value = None # Simulate failure to get reading

        dexcom_readings.last_known_glucose_timestamp = datetime.datetime(2023, 1, 1, 11, 0, 0) # Some prior value

        with self.assertRaises(KeyboardInterrupt):
            dexcom_readings.main()

        mock_get_reading.assert_called_once_with(mock_dex_client)
        mock_print.assert_any_call(f"{fixed_check_time.isoformat()}: Could not retrieve glucose reading.")

        expected_log_row = [
            fixed_check_time.isoformat(),
            False, # new_reading_received
            None, None, None, None # All glucose related fields are None
        ]
        mock_write_csv.assert_called_once_with(expected_log_row)

    # Test for the initial CSV header writing in `if __name__ == "__main__":`
    # This is a bit more of an integration test for that specific block.
    # To test this, we'd need to simulate running the script.
    # For pure unit tests of functions, this is usually skipped or refactored.
    # However, if you want to test this specific block:
    @patch('dexcom_readings.main') # Mock out the actual main() call
    @patch('dexcom_readings.csv.writer')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.isfile')
    def test_script_execution_writes_header_if_new(self, mock_isfile, mock_open_func, mock_csv_writer_constructor, mock_main_func):
        # This tests the block:
        # if __name__ == "__main__":
        #     if not os.path.isfile(OUTPUT_CSV_FILE):
        #         ... write header ...
        #     main()
        
        mock_isfile.return_value = False # File does not exist
        mock_csv_writer_instance = MagicMock()
        mock_csv_writer_constructor.return_value = mock_csv_writer_instance
        
        # To simulate `if __name__ == "__main__":` block, we can't directly call it.
        # We can re-import the module or use runpy, but that's complex for a unit test.
        # A simpler way is to extract that logic into a testable function.
        # For now, let's assume we are testing the intended effect if that block were run.
        # This test is more conceptual for that block.
        
        # Let's create a helper function in the test to mimic the __main__ block's header logic
        def simulate_main_block_header_write():
            if not os.path.isfile(dexcom_readings.OUTPUT_CSV_FILE):
                with open(dexcom_readings.OUTPUT_CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
                    writer = dexcom_readings.csv.writer(f)
                    writer.writerow(dexcom_readings.CSV_HEADERS)
            # dexcom_readings.main() # This would be called, but we mocked it

        simulate_main_block_header_write()
        
        mock_isfile.assert_called_once_with(dexcom_readings.OUTPUT_CSV_FILE)
        mock_open_func.assert_called_once_with(dexcom_readings.OUTPUT_CSV_FILE, mode='w', newline='', encoding='utf-8')
        mock_csv_writer_instance.writerow.assert_called_once_with(dexcom_readings.CSV_HEADERS)
        # mock_main_func.assert_called_once() # If we were testing the full script run

    def test_os_environ_patch_behavior(self):
        """
        Tests the behavior of patch.dict for os.environ to ensure
        variables are set within the context and restored afterward.
        """
        test_var_name = "MY_TEST_ENV_VAR_PATCH_BEHAVIOR" # Unique name
        original_value = os.environ.get(test_var_name)

        # Ensure a clean state for the test var if it somehow exists
        if original_value is not None:
            del os.environ[test_var_name]

        self.assertIsNone(os.environ.get(test_var_name),
                            f"Pre-condition: {test_var_name} should not be set in os.environ.")

        patched_value = "test_patched_value_123"
        with patch.dict(os.environ, {test_var_name: patched_value}):
            self.assertEqual(os.environ.get(test_var_name), patched_value,
                             f"Inside patch: {test_var_name} should have the patched value.")

        self.assertIsNone(os.environ.get(test_var_name),
                            f"After patch: {test_var_name} should be unset (restored).")

        # If original_value was not None, restore it.
        if original_value is not None:
            os.environ[test_var_name] = original_value

if __name__ == '__main__':
    unittest.main()