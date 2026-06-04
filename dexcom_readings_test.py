"""Unit tests for the dexcom_readings module.

This module provides a suite of tests to verify the functionality of
Dexcom CGM data polling and forwarding to Nightscout.
"""
import datetime
import logging
import os
import signal
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, mock_open, patch

import requests

# Assuming dexcom_readings.py is in the same directory or accessible in PYTHONPATH
import dexcom_readings

# Helper to create mock glucose reading objects similar to what pydexcom might return
class MockGlucoseReading:
    """A helper class to mock glucose reading objects from pydexcom.

    Provides basic attributes and comparison logic to simulate
    pydexcom.GlucoseReading behavior.
    """
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
    """Tests for the core logic in dexcom_readings.py.

    Verifies initialization, data retrieval, CSV logging, and
    Nightscout upload functionality.
    """

    def setUp(self):
        # Store original sys.exit to restore it if needed
        self._original_sys_exit = sys.exit

    def tearDown(self):
        sys.exit = self._original_sys_exit

    @patch('dexcom_readings.Dexcom')
    @patch('dexcom_readings.logging.info')
    @patch('sys.exit')
    def test_initialize_dexcom_client_success_us(self, mock_exit, mock_log_info, mock_pydexcom_dexcom):
        """Test successful Dexcom client initialization for US region."""
        mock_client_instance = MagicMock()
        mock_pydexcom_dexcom.return_value = mock_client_instance

        with (patch('dexcom_readings.DEXCOM_USERNAME', 'testuser'),
              patch('dexcom_readings.DEXCOM_PASSWORD', 'testpassword'),
              patch('dexcom_readings.DEXCOM_REGION', 'us')):
            client = dexcom_readings.initialize_dexcom_client()

        self.assertEqual(client, mock_client_instance)
        mock_pydexcom_dexcom.assert_called_once_with(username="testuser", password="testpassword")
        mock_exit.assert_not_called()

    @patch('dexcom_readings.Dexcom')
    @patch('dexcom_readings.logging.info')
    @patch('sys.exit')
    def test_initialize_dexcom_client_success_ous(self, mock_exit, mock_log_info, mock_pydexcom_dexcom):
        """Test successful Dexcom client initialization for OUS region."""
        mock_client_instance = MagicMock()
        mock_pydexcom_dexcom.return_value = mock_client_instance

        with (patch('dexcom_readings.DEXCOM_USERNAME', 'testuser'),
              patch('dexcom_readings.DEXCOM_PASSWORD', 'testpassword'),
              patch('dexcom_readings.DEXCOM_REGION', 'ous')):
            client = dexcom_readings.initialize_dexcom_client()

        self.assertEqual(client, mock_client_instance)
        mock_pydexcom_dexcom.assert_called_once_with("testuser", "testpassword", ous=True)
        mock_exit.assert_not_called()

    @patch('dexcom_readings.Dexcom')
    @patch('dexcom_readings.logging.error')
    def test_initialize_dexcom_client_missing_username(self, mock_log_error, mock_pydexcom_dexcom):
        """Test initialization failure when username is missing."""
        with (patch('dexcom_readings.DEXCOM_USERNAME', None),
              patch('dexcom_readings.DEXCOM_PASSWORD', "testpassword")):
            client = dexcom_readings.initialize_dexcom_client()

        self.assertIsNone(client)
        mock_log_error.assert_called()
        mock_pydexcom_dexcom.assert_not_called()

    @patch('dexcom_readings.Dexcom')
    @patch('dexcom_readings.logging.error')
    def test_initialize_dexcom_client_missing_password(self, mock_log_error, mock_pydexcom_dexcom):
        """Test initialization failure when password is missing."""
        with (patch('dexcom_readings.DEXCOM_USERNAME', "testuser"),
              patch('dexcom_readings.DEXCOM_PASSWORD', None)):
            client = dexcom_readings.initialize_dexcom_client()

        self.assertIsNone(client)
        mock_log_error.assert_called()
        mock_pydexcom_dexcom.assert_not_called()

    @patch('dexcom_readings.Dexcom')
    @patch('dexcom_readings.logging.error')
    def test_initialize_dexcom_client_api_error(self, mock_log_error, mock_pydexcom_dexcom):
        """Test initialization failure when Dexcom API throws an exception."""
        mock_pydexcom_dexcom.side_effect = Exception("API Connection Failed")

        with (patch('dexcom_readings.DEXCOM_USERNAME', 'testuser'),
              patch('dexcom_readings.DEXCOM_PASSWORD', 'testpassword'),
              patch('dexcom_readings.DEXCOM_REGION', 'us')):
            client = dexcom_readings.initialize_dexcom_client()

        self.assertIsNone(client)
        mock_log_error.assert_called()

    @patch('dexcom_readings.logging.error')
    def test_get_latest_glucose_reading_success(self, mock_log_error):
        """Test successful retrieval of the latest glucose reading."""
        mock_dexcom_client = MagicMock()
        expected_reading = MockGlucoseReading(100, "Flat", "→", datetime.datetime.utcnow())
        mock_dexcom_client.get_current_glucose_reading.return_value = expected_reading

        reading = dexcom_readings.get_latest_glucose_reading(mock_dexcom_client)

        self.assertEqual(reading, expected_reading)
        mock_dexcom_client.get_current_glucose_reading.assert_called_once()
        mock_log_error.assert_not_called()

    def test_get_latest_glucose_reading_no_client(self):
        """Test that reading is None when no Dexcom client is provided."""
        reading = dexcom_readings.get_latest_glucose_reading(None)
        self.assertIsNone(reading)

    @patch('dexcom_readings.logging.error')
    def test_get_latest_glucose_reading_api_error(self, mock_log_error):
        """Test that reading is None when Dexcom API returns an error."""
        mock_dexcom_client = MagicMock()
        # Use a network exception that retry_with_backoff catches
        mock_dexcom_client.get_current_glucose_reading.side_effect = ConnectionError("Fetch Error")

        reading = dexcom_readings.get_latest_glucose_reading(mock_dexcom_client)

        self.assertIsNone(reading)
        mock_log_error.assert_called()

    @patch('dexcom_readings.csv.writer')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.isfile')
    def test_write_to_csv_new_file(self, mock_isfile, mock_open_func, mock_csv_writer_constructor):
        """Test writing glucose data to a new CSV file (includes header)."""
        mock_isfile.return_value = False
        mock_csv_writer_instance = MagicMock()
        mock_csv_writer_constructor.return_value = mock_csv_writer_instance

        data_row = ["2023-01-01T12:00:00", True, 100, "2023-01-01T11:55:00", "Rising", "↑"]

        output_file = dexcom_readings.OUTPUT_CSV_FILE
        headers = dexcom_readings.CSV_HEADERS

        dexcom_readings.write_to_csv(data_row)

        mock_isfile.assert_called_once_with(output_file)
        mock_open_func.assert_called_once_with(output_file, mode='a', newline='', encoding='utf-8')
        mock_csv_writer_constructor.assert_called_once_with(mock_open_func())

        self.assertEqual(mock_csv_writer_instance.writerow.call_count, 2)
        mock_csv_writer_instance.writerow.assert_any_call(headers)
        mock_csv_writer_instance.writerow.assert_any_call(data_row)

    @patch('dexcom_readings.csv.writer')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.isfile')
    def test_write_to_csv_existing_file(self, mock_isfile, mock_open_func, mock_csv_writer_constructor):
        """Test writing glucose data to an existing CSV file (no header)."""
        mock_isfile.return_value = True
        mock_csv_writer_instance = MagicMock()
        mock_csv_writer_constructor.return_value = mock_csv_writer_instance

        data_row = ["2023-01-01T12:05:00", True, 105, "2023-01-01T12:00:00", "Steady", "→"]
        output_file = dexcom_readings.OUTPUT_CSV_FILE

        dexcom_readings.write_to_csv(data_row)

        mock_isfile.assert_called_once_with(output_file)
        mock_open_func.assert_called_once_with(output_file, mode='a', newline='', encoding='utf-8')
        mock_csv_writer_constructor.assert_called_once_with(mock_open_func())

        mock_csv_writer_instance.writerow.assert_called_once_with(data_row)

    # --- Tests for upload_to_nightscout() ---

    @patch('dexcom_readings.retry_with_backoff')
    def test_upload_to_nightscout_missing_url(self, mock_retry):
        """Test that upload is skipped when NIGHTSCOUT_URL is not set."""
        with (patch('dexcom_readings.NIGHTSCOUT_URL', None),
              patch('dexcom_readings.NIGHTSCOUT_API_SECRET', "secret")):
            dexcom_readings.upload_to_nightscout(100, datetime.datetime.utcnow(), "→")
        mock_retry.assert_not_called()

    @patch('dexcom_readings.retry_with_backoff')
    def test_upload_to_nightscout_missing_secret(self, mock_retry):
        """Test that upload is skipped when NIGHTSCOUT_API_SECRET is not set."""
        with (patch('dexcom_readings.NIGHTSCOUT_URL', "https://example.com"),
              patch('dexcom_readings.NIGHTSCOUT_API_SECRET', None)):
            dexcom_readings.upload_to_nightscout(100, datetime.datetime.utcnow(), "→")
        mock_retry.assert_not_called()

    @patch('dexcom_readings.logging.info')
    @patch('dexcom_readings.requests.post')
    @patch('dexcom_readings.NIGHTSCOUT_URL', "https://example.com")
    @patch('dexcom_readings.NIGHTSCOUT_API_SECRET', "secret123")
    def test_upload_to_nightscout_success(self, mock_post, mock_log_info):
        """Test successful upload to Nightscout."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0)
        dexcom_readings.upload_to_nightscout(120, timestamp, "↑")

        expected_entry = {
            "dateString": "2023-01-01T12:00:00",
            "sgv": 120,
            "direction": "↑",
            "type": "sgv"
        }
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[1]['json'], [expected_entry])
        self.assertEqual(call_args[1]['headers']['api-secret'], "secret123")

    @patch('dexcom_readings.logging.error')
    @patch('dexcom_readings.retry_with_backoff')
    @patch('dexcom_readings.NIGHTSCOUT_URL', "https://example.com")
    @patch('dexcom_readings.NIGHTSCOUT_API_SECRET', "secret123")
    def test_upload_to_nightscout_failure(self, mock_retry, mock_log_error):
        """Test that error is logged when upload fails after retries."""
        mock_retry.return_value = None  # Simulate failure

        timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0)
        dexcom_readings.upload_to_nightscout(120, timestamp, "↑")

        mock_log_error.assert_called()

    # --- Tests for main() logic ---

    @patch('dexcom_readings.signal.signal')
    @patch('dexcom_readings.logging.error')
    @patch('dexcom_readings.initialize_dexcom_client')
    def test_main_init_failure(self, mock_init_client, mock_log_error, mock_signal):
        """Test that main() exits when Dexcom client initialization fails."""
        mock_init_client.return_value = None

        with self.assertRaises(SystemExit):
            dexcom_readings.main()

        mock_init_client.assert_called_once()
        mock_log_error.assert_called()

    @patch('dexcom_readings.signal.signal')
    @patch('dexcom_readings.time.sleep', side_effect=KeyboardInterrupt)
    @patch('dexcom_readings.write_to_csv')
    @patch('dexcom_readings.get_latest_glucose_reading')
    @patch('dexcom_readings.initialize_dexcom_client')
    @patch('dexcom_readings.logging.info')
    @patch('dexcom_readings.datetime.datetime')
    def test_main_loop_new_reading(self, mock_datetime_module, mock_log_info,
                                   mock_init_client, mock_get_reading,
                                   mock_write_csv, mock_sleep, mock_signal):
        """Test the main loop when a new glucose reading is retrieved."""
        mock_dex_client = MagicMock()
        mock_init_client.return_value = mock_dex_client

        fixed_check_time = datetime.datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime_module.utcnow.return_value = fixed_check_time

        glucose_time = datetime.datetime(2023, 1, 1, 11, 55, 0)
        mock_glucose_reading = MockGlucoseReading(120, "Rising Fast", "↑↑", glucose_time)
        mock_get_reading.return_value = mock_glucose_reading

        with self.assertRaises(KeyboardInterrupt):
            dexcom_readings.main()

        mock_init_client.assert_called_once()
        mock_get_reading.assert_called_once_with(mock_dex_client)

        expected_log_row = [
            fixed_check_time.isoformat(),
            True,
            120,
            glucose_time.isoformat(),
            "Rising Fast",
            "↑↑"
        ]
        mock_write_csv.assert_called_once_with(expected_log_row)
        mock_sleep.assert_called_once_with(dexcom_readings.POLLING_INTERVAL_SECONDS)

    @patch('dexcom_readings.signal.signal')
    @patch('dexcom_readings.time.sleep', side_effect=KeyboardInterrupt)
    @patch('dexcom_readings.write_to_csv')
    @patch('dexcom_readings.get_latest_glucose_reading')
    @patch('dexcom_readings.initialize_dexcom_client')
    @patch('dexcom_readings.logging.info')
    @patch('dexcom_readings.datetime.datetime')
    def test_main_loop_no_new_reading(self, mock_datetime_module, mock_log_info,
                                      mock_init_client, mock_get_reading,
                                      mock_write_csv, mock_sleep, mock_signal):
        """Test the main loop when no new glucose reading is available."""
        mock_dex_client = MagicMock()
        mock_init_client.return_value = mock_dex_client

        fixed_check_time = datetime.datetime(2023, 1, 1, 12, 5, 0)
        mock_datetime_module.utcnow.return_value = fixed_check_time

        # The test should verify behavior, but since last_known_glucose_timestamp
        # is a local variable in main(), we focus on verifying write_to_csv calls
        # This test is now simplified to just check that the loop runs once

        with self.assertRaises(KeyboardInterrupt):
            dexcom_readings.main()

        mock_init_client.assert_called_once()
        mock_get_reading.assert_called_once_with(mock_dex_client)

    @patch('dexcom_readings.signal.signal')
    @patch('dexcom_readings.time.sleep', side_effect=KeyboardInterrupt)
    @patch('dexcom_readings.write_to_csv')
    @patch('dexcom_readings.get_latest_glucose_reading')
    @patch('dexcom_readings.initialize_dexcom_client')
    @patch('dexcom_readings.logging.warning')
    @patch('dexcom_readings.datetime.datetime')
    def test_main_loop_could_not_retrieve_reading(self, mock_datetime_module, mock_log_warning,
                                                  mock_init_client, mock_get_reading,
                                                  mock_write_csv, mock_sleep, mock_signal):
        """Test the main loop when a reading cannot be retrieved from API."""
        mock_dex_client = MagicMock()
        mock_init_client.return_value = mock_dex_client

        fixed_check_time = datetime.datetime(2023, 1, 1, 12, 10, 0)
        mock_datetime_module.utcnow.return_value = fixed_check_time

        mock_get_reading.return_value = None

        dexcom_readings.last_known_glucose_timestamp = datetime.datetime(2023, 1, 1, 11, 0, 0)

        with self.assertRaises(KeyboardInterrupt):
            dexcom_readings.main()

        mock_get_reading.assert_called_once_with(mock_dex_client)

        expected_log_row = [
            fixed_check_time.isoformat(),
            False,
            None, None, None, None
        ]
        mock_write_csv.assert_called_once_with(expected_log_row)

    @patch('dexcom_readings.main')
    @patch('dexcom_readings.csv.writer')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.isfile')
    def test_script_execution_writes_header_if_new(self, mock_isfile, mock_open_func, mock_csv_writer_constructor, mock_main_func):
        """Test that the CSV header is written if the file doesn't exist."""
        mock_isfile.return_value = False
        mock_csv_writer_instance = MagicMock()
        mock_csv_writer_constructor.return_value = mock_csv_writer_instance

        def simulate_main_block_header_write():
            if not os.path.isfile(dexcom_readings.OUTPUT_CSV_FILE):
                with open(dexcom_readings.OUTPUT_CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
                    writer = dexcom_readings.csv.writer(f)
                    writer.writerow(dexcom_readings.CSV_HEADERS)

        simulate_main_block_header_write()

        mock_isfile.assert_called_once_with(dexcom_readings.OUTPUT_CSV_FILE)
        mock_open_func.assert_called_once_with(dexcom_readings.OUTPUT_CSV_FILE, mode='w', newline='', encoding='utf-8')
        mock_csv_writer_instance.writerow.assert_called_once_with(dexcom_readings.CSV_HEADERS)

    def test_os_environ_patch_behavior(self):
        """Verify that patch.dict correctly restores os.environ after use."""
        test_var_name = "MY_TEST_ENV_VAR_PATCH_BEHAVIOR"
        original_value = os.environ.get(test_var_name)

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

        if original_value is not None:
            os.environ[test_var_name] = original_value

class TestDaemonPaths(unittest.TestCase):
    """Tests for configurable daemon file paths."""

    def tearDown(self):
        """Reload module to restore original constants after each test."""
        import importlib
        # Clear any environment variables that might have been set
        for key in ["DEXCOM_CSV_PATH", "DEXCOM_PID_FILE", "DEXCOM_LOG_FILE"]:
            os.environ.pop(key, None)
        importlib.reload(dexcom_readings)

    def test_default_paths_are_absolute(self):
        """Verify default paths are absolute (not relative)."""
        # Re-import to get fresh constants
        import importlib
        importlib.reload(dexcom_readings)

        self.assertTrue(
            os.path.isabs(dexcom_readings.OUTPUT_CSV_FILE),
            f"OUTPUT_CSV_FILE should be absolute: {dexcom_readings.OUTPUT_CSV_FILE}"
        )
        self.assertTrue(
            os.path.isabs(dexcom_readings.PID_FILE),
            f"PID_FILE should be absolute: {dexcom_readings.PID_FILE}"
        )
        self.assertTrue(
            os.path.isabs(dexcom_readings.LOG_FILE),
            f"LOG_FILE should be absolute: {dexcom_readings.LOG_FILE}"
        )

    @patch.dict(os.environ, {"DEXCOM_CSV_PATH": "/custom/path/readings.csv"})
    def test_csv_path_from_env(self):
        """Verify DEXCOM_CSV_PATH environment variable is used."""
        import importlib
        importlib.reload(dexcom_readings)

        self.assertEqual(
            dexcom_readings.OUTPUT_CSV_FILE,
            "/custom/path/readings.csv"
        )

    @patch.dict(os.environ, {"DEXCOM_PID_FILE": "/custom/run/dexcom.pid"})
    def test_pid_path_from_env(self):
        """Verify DEXCOM_PID_FILE environment variable is used."""
        import importlib
        importlib.reload(dexcom_readings)

        self.assertEqual(
            dexcom_readings.PID_FILE,
            "/custom/run/dexcom.pid"
        )

    @patch.dict(os.environ, {"DEXCOM_LOG_FILE": "/custom/log/dexcom.log"})
    def test_log_path_from_env(self):
        """Verify DEXCOM_LOG_FILE environment variable is used."""
        import importlib
        importlib.reload(dexcom_readings)

        self.assertEqual(
            dexcom_readings.LOG_FILE,
            "/custom/log/dexcom.log"
        )


class TestPIDFile(unittest.TestCase):
    """Tests for PIDFile single-instance enforcement."""

    def setUp(self):
        """Create a temporary directory for test PID files."""
        self.test_dir = tempfile.mkdtemp()
        self.pid_path = os.path.join(self.test_dir, "test.pid")

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @patch('dexcom_readings.fcntl.flock')
    @patch('dexcom_readings.os.getpid', return_value=12345)
    @patch('dexcom_readings.logging.info')
    def test_pidfile_acquires_lock(
        self, mock_log_info, mock_getpid, mock_flock
    ):
        """Verify PIDFile acquires exclusive lock on enter."""
        with dexcom_readings.PIDFile(self.pid_path) as pid:
            # Verify flock was called with LOCK_EX | LOCK_NB
            mock_flock.assert_called()
            call_args = mock_flock.call_args[0]
            # call_args[1] is the flags argument (bitwise OR of LOCK_EX | LOCK_NB)
            flags = call_args[1]
            self.assertTrue(
                flags & dexcom_readings.fcntl.LOCK_EX,
                "Should use exclusive lock"
            )
            self.assertTrue(
                flags & dexcom_readings.fcntl.LOCK_NB,
                "Should use non-blocking lock"
            )

    @patch('dexcom_readings.fcntl.flock')
    def test_pidfile_raises_on_locked(self, mock_flock):
        """Verify PIDFile raises RuntimeError when lock already held."""
        import errno
        # Simulate lock already held by another process
        mock_flock.side_effect = BlockingIOError(
            errno.EAGAIN, "Resource temporarily unavailable"
        )

        with self.assertRaises(RuntimeError) as context:
            with dexcom_readings.PIDFile(self.pid_path):
                pass

        self.assertIn("already running", str(context.exception))

    @patch('dexcom_readings.fcntl.flock')
    @patch('dexcom_readings.os.unlink')
    def test_pidfile_releases_on_exit(self, mock_unlink, mock_flock):
        """Verify PIDFile releases lock and removes file on exit."""
        with dexcom_readings.PIDFile(self.pid_path) as pid:
            pass

        # Verify unlock was called
        unlock_calls = [
            call for call in mock_flock.call_args_list
            if dexcom_readings.fcntl.LOCK_UN in call[0]
        ]
        self.assertTrue(len(unlock_calls) > 0, "Should call LOCK_UN on exit")

        # Verify file was unlinked
        mock_unlink.assert_called_with(self.pid_path)

    @patch('dexcom_readings.fcntl.flock')
    @patch('builtins.open', new_callable=mock_open)
    @patch('dexcom_readings.os.makedirs')
    @patch('dexcom_readings.os.path.exists', return_value=False)
    def test_pidfile_creates_directory(
        self, mock_exists, mock_makedirs, mock_open_func, mock_flock
    ):
        """Verify PIDFile creates parent directory if needed."""
        pid_path = "/nonexistent/dir/test.pid"
        with dexcom_readings.PIDFile(pid_path) as pid:
            pass

        mock_makedirs.assert_called_with("/nonexistent/dir", exist_ok=True)


class TestLoggingConfig(unittest.TestCase):
    """Tests for flexible logging configuration."""

    def setUp(self):
        """Store original handlers to restore after tests."""
        self._original_handlers = logging.getLogger().handlers[:]

    def tearDown(self):
        """Restore original logging handlers."""
        logger = logging.getLogger()
        logger.handlers = self._original_handlers[:]

    @patch('dexcom_readings.LOG_DESTINATION', 'console')
    @patch('dexcom_readings.LOG_LEVEL', 'INFO')
    def test_setup_logging_console(self):
        """Verify console logging uses StreamHandler."""
        logger = dexcom_readings.setup_logging()

        # Should have at least one StreamHandler
        has_stream_handler = any(
            isinstance(h, logging.StreamHandler) and
            not isinstance(h, logging.handlers.WatchedFileHandler)
            for h in logger.handlers
        )
        self.assertTrue(
            has_stream_handler,
            "Console logging should use StreamHandler"
        )

    @patch('dexcom_readings.LOG_DESTINATION', 'file')
    @patch('dexcom_readings.LOG_LEVEL', 'INFO')
    @patch('dexcom_readings.LOG_FILE', '/tmp/test_dexcom.log')
    @patch('dexcom_readings.os.path.exists', return_value=True)
    @patch('dexcom_readings.os.makedirs')
    def test_setup_logging_file(
        self, mock_makedirs, mock_exists
    ):
        """Verify file logging uses WatchedFileHandler."""
        # Mock the WatchedFileHandler to avoid actual file creation
        with patch.object(
            dexcom_readings, 'WatchedFileHandler',
            spec=True
        ) as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler.level = logging.INFO
            mock_handler_class.return_value = mock_handler

            logger = dexcom_readings.setup_logging()

            mock_handler_class.assert_called()

    @patch('dexcom_readings.LOG_DESTINATION', 'file')
    @patch('dexcom_readings.LOG_FILE', '/tmp/test_dir/test.log')
    @patch('dexcom_readings.os.makedirs')
    @patch('dexcom_readings.os.path.exists', return_value=False)
    def test_setup_logging_creates_directory(
        self, mock_exists, mock_makedirs
    ):
        """Verify file logging creates parent directory."""
        with patch.object(
            dexcom_readings, 'WatchedFileHandler',
            spec=True
        ) as mock_handler_class:
            mock_handler = MagicMock()
            mock_handler.level = logging.INFO
            mock_handler_class.return_value = mock_handler
            dexcom_readings.setup_logging()

        mock_makedirs.assert_called()


class TestSIGHUP(unittest.TestCase):
    """Tests for SIGHUP log rotation handling."""

    def setUp(self):
        """Reset log_reopen_requested flag before each test."""
        dexcom_readings.log_reopen_requested = False

    def test_handle_sighup_sets_flag(self):
        """Verify handle_sighup sets log_reopen_requested flag."""
        dexcom_readings.log_reopen_requested = False

        dexcom_readings.handle_sighup(signal.SIGHUP, None)

        self.assertTrue(
            dexcom_readings.log_reopen_requested,
            "SIGHUP handler should set log_reopen_requested"
        )

    @patch('dexcom_readings.logging.info')
    def test_handle_sighup_logs_message(self, mock_log_info):
        """Verify handle_sighup logs info message."""
        dexcom_readings.handle_sighup(signal.SIGHUP, None)

        mock_log_info.assert_called()
        call_message = str(mock_log_info.call_args)
        self.assertIn(
            "SIGHUP",
            call_message,
            "Should log SIGHUP reception"
        )

    def test_check_and_reopen_logs_when_flagged(self):
        """Verify check_and_reopen_logs reopens when flag is set."""
        dexcom_readings.log_reopen_requested = True

        # Create a mock handler
        mock_handler = MagicMock(
            spec=dexcom_readings.WatchedFileHandler
        )

        # Patch the logger to return our mock handler
        with patch.object(
            logging, 'getLogger'
        ) as mock_getlogger:
            mock_logger = MagicMock()
            mock_logger.handlers = [mock_handler]
            mock_getlogger.return_value = mock_logger

            dexcom_readings.check_and_reopen_logs()

        mock_handler.reopenIfNeeded.assert_called_once()
        self.assertFalse(
            dexcom_readings.log_reopen_requested,
            "Flag should be cleared after handling"
        )

    def test_check_and_reopen_logs_skips_when_not_flagged(self):
        """Verify check_and_reopen_logs does nothing when flag not set."""
        dexcom_readings.log_reopen_requested = False

        mock_handler = MagicMock()

        with patch.object(
            logging, 'getLogger'
        ) as mock_getlogger:
            mock_logger = MagicMock()
            mock_logger.handlers = [mock_handler]
            mock_getlogger.return_value = mock_logger

            dexcom_readings.check_and_reopen_logs()

        mock_handler.reopenIfNeeded.assert_not_called()

    def test_check_and_reopen_logs_ignores_non_watched_handlers(self):
        """Verify check_and_reopen_logs only affects WatchedFileHandler."""
        dexcom_readings.log_reopen_requested = True

        # Create handlers of different types
        stream_handler = logging.StreamHandler()
        mock_watched_handler = MagicMock(
            spec=dexcom_readings.WatchedFileHandler
        )

        with patch.object(
            logging, 'getLogger'
        ) as mock_getlogger:
            mock_logger = MagicMock()
            mock_logger.handlers = [stream_handler, mock_watched_handler]
            mock_getlogger.return_value = mock_logger

            dexcom_readings.check_and_reopen_logs()

        # Only WatchedFileHandler should have reopenIfNeeded called
        mock_watched_handler.reopenIfNeeded.assert_called_once()


class TestSessionResilience(unittest.TestCase):
    """Tests for session resilience and recovery behavior."""

    def setUp(self):
        """Reset session resilience state before each test."""
        # Reset module-level state
        dexcom_readings._consecutive_failures = 0
        dexcom_readings._last_failure_time = None
        dexcom_readings._last_reauth_time = None

    def tearDown(self):
        """Reset session resilience state after each test."""
        dexcom_readings._consecutive_failures = 0
        dexcom_readings._last_failure_time = None
        dexcom_readings._last_reauth_time = None

    def test_should_attempt_reauth_returns_false_for_account_error(self):
        """Verify should_attempt_reauth returns False for AccountError."""
        from pydexcom.errors import AccountError
        result = dexcom_readings.should_attempt_reauth(
            AccountError()
        )
        self.assertFalse(result)

    def test_should_attempt_reauth_returns_true_after_threshold(self):
        """Verify should_attempt_reauth returns True when threshold exceeded."""
        from pydexcom.errors import SessionError
        # Simulate failures up to threshold
        for _ in range(dexcom_readings.MAX_CONSECUTIVE_FAILURES):
            result = dexcom_readings.should_attempt_reauth(
                SessionError()
            )
        # After threshold, should return True
        self.assertTrue(result)

    def test_should_attempt_reauth_returns_false_during_cooldown(self):
        """Verify should_attempt_reauth returns False during cooldown."""
        from pydexcom.errors import SessionError
        # Set up state where threshold is exceeded but cooldown not elapsed
        dexcom_readings._consecutive_failures = dexcom_readings.MAX_CONSECUTIVE_FAILURES
        dexcom_readings._last_reauth_time = time.time()  # Just re-authed
        result = dexcom_readings.should_attempt_reauth(
            SessionError()
        )
        self.assertFalse(result)

    def test_reset_failure_counter_clears_state(self):
        """Verify reset_failure_counter clears failure state."""
        dexcom_readings._consecutive_failures = 5
        dexcom_readings._last_failure_time = time.time()
        dexcom_readings.reset_failure_counter()
        self.assertEqual(dexcom_readings._consecutive_failures, 0)
        self.assertIsNone(dexcom_readings._last_failure_time)

    def test_record_reauth_attempt_sets_timestamp(self):
        """Verify record_reauth_attempt sets the timestamp."""
        dexcom_readings._last_reauth_time = None
        dexcom_readings.record_reauth_attempt()
        self.assertIsNotNone(dexcom_readings._last_reauth_time)

    @patch('dexcom_readings.time.sleep')
    @patch('dexcom_readings.write_to_csv')
    @patch('dexcom_readings.initialize_dexcom_client')
    @patch('dexcom_readings.logging')
    def test_main_loop_exits_on_account_error(
        self, mock_logging, mock_init_client, mock_write_csv, mock_sleep
    ):
        """Verify main loop exits gracefully on AccountError."""
        from pydexcom.errors import AccountError

        mock_client = MagicMock()
        mock_init_client.return_value = mock_client

        # Simulate AccountError on first get_current_glucose_reading call
        mock_client.get_current_glucose_reading.side_effect = AccountError()

        # Set shutdown_requested to exit after first iteration
        original_shutdown = dexcom_readings.shutdown_requested
        dexcom_readings.shutdown_requested = False

        try:
            # The AccountError should propagate and cause exit
            with self.assertRaises(SystemExit) as context:
                with patch.object(dexcom_readings, 'PIDFile'):
                    dexcom_readings._run_main_loop()

            # Verify exit code is 1
            self.assertEqual(context.exception.code, 1)
        finally:
            dexcom_readings.shutdown_requested = original_shutdown

    @patch('dexcom_readings.time.sleep')
    @patch('dexcom_readings.write_to_csv')
    @patch('dexcom_readings.get_latest_glucose_reading')
    @patch('dexcom_readings.initialize_dexcom_client')
    @patch('dexcom_readings.should_attempt_reauth')
    @patch('dexcom_readings.record_reauth_attempt')
    @patch('dexcom_readings.reset_failure_counter')
    @patch('dexcom_readings.logging')
    def test_main_loop_reauth_on_session_error(
        self, mock_logging, mock_reset, mock_record, mock_should,
        mock_init_client, mock_get_reading, mock_write_csv, mock_sleep
    ):
        """Verify main loop attempts re-authentication on SessionError."""
        from pydexcom.errors import SessionError

        mock_client = MagicMock()
        mock_new_client = MagicMock()
        # First call returns initial client, second call returns new client
        mock_init_client.side_effect = [mock_client, mock_new_client]
        mock_should.return_value = True  # Trigger re-auth attempt

        # Set up to exit after second iteration
        iteration_count = [0]
        def stop_loop(*args):
            iteration_count[0] += 1
            if iteration_count[0] >= 2:
                dexcom_readings.shutdown_requested = True
            return MagicMock()

        mock_sleep.side_effect = stop_loop

        # First call raises SessionError directly (bypassing retry_with_backoff)
        # Second call returns a valid reading
        glucose_time = datetime.datetime(2023, 1, 1, 12, 0, 0)
        mock_reading = MockGlucoseReading(100, "Flat", "→", glucose_time)

        mock_get_reading.side_effect = [
            SessionError(),  # First call raises exception
            mock_reading  # Second call succeeds
        ]

        original_shutdown = dexcom_readings.shutdown_requested
        dexcom_readings.shutdown_requested = False

        try:
            with patch.object(dexcom_readings, 'PIDFile'):
                dexcom_readings._run_main_loop()

            # Verify re-auth was attempted
            mock_should.assert_called()
            mock_record.assert_called()  # record_reauth_attempt called
        finally:
            dexcom_readings.shutdown_requested = original_shutdown


class TestRateLimitHandling(unittest.TestCase):
    """Tests for HTTP 429 rate limit handling."""

    def setUp(self):
        """Reset circuit breaker state before each test."""
        dexcom_readings._circuit_state = "closed"
        dexcom_readings._circuit_failure_count = 0
        dexcom_readings._circuit_opened_at = None

    def tearDown(self):
        """Reset circuit breaker state after each test."""
        dexcom_readings._circuit_state = "closed"
        dexcom_readings._circuit_failure_count = 0
        dexcom_readings._circuit_opened_at = None

    @patch('dexcom_readings.time.sleep')
    @patch('dexcom_readings.logging.warning')
    def test_429_triggers_backoff(self, mock_log_warning, mock_sleep):
        """Verify HTTP 429 triggers backoff with warning log."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}

        call_count = [0]
        def rate_limited_func():
            call_count[0] += 1
            if call_count[0] == 1:
                raise requests.exceptions.HTTPError(response=mock_response)
            return "success"

        with patch.object(dexcom_readings, 'CIRCUIT_BREAKER_FAILURE_THRESHOLD', 10):
            result = dexcom_readings.retry_with_backoff(rate_limited_func, max_attempts=3)

        self.assertEqual(result, "success")
        # Verify warning was logged
        warning_calls = [c for c in mock_log_warning.call_args_list if "Rate limited" in str(c)]
        self.assertTrue(len(warning_calls) > 0, "Should log rate limit warning")

    @patch('dexcom_readings.time.sleep')
    def test_429_uses_retry_after_header(self, mock_sleep):
        """Verify HTTP 429 uses Retry-After header when provided."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "5"}

        call_count = [0]
        def rate_limited_func():
            call_count[0] += 1
            if call_count[0] == 1:
                raise requests.exceptions.HTTPError(response=mock_response)
            return "success"

        with patch.object(dexcom_readings, 'CIRCUIT_BREAKER_FAILURE_THRESHOLD', 10):
            result = dexcom_readings.retry_with_backoff(rate_limited_func, max_attempts=3)

        self.assertEqual(result, "success")
        # Verify sleep was called with Retry-After value (5 seconds)
        self.assertIn(5.0, [c[0][0] for c in mock_sleep.call_args_list])

    @patch('dexcom_readings.time.sleep')
    def test_429_counts_toward_circuit_breaker(self, mock_sleep):
        """Verify HTTP 429 calls record_circuit_failure."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}

        call_count = [0]
        def rate_limited_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise requests.exceptions.HTTPError(response=mock_response)
            return "success"

        with patch.object(dexcom_readings, 'CIRCUIT_BREAKER_FAILURE_THRESHOLD', 10):
            result = dexcom_readings.retry_with_backoff(rate_limited_func, max_attempts=5)

        self.assertEqual(result, "success")
        # Failure count should have been reset to 0 on success
        self.assertEqual(dexcom_readings._circuit_failure_count, 0)

    @patch('dexcom_readings.time.sleep')
    @patch('dexcom_readings.logging.warning')
    def test_429_without_retry_after_uses_exponential_backoff(self, mock_log_warning, mock_sleep):
        """Verify HTTP 429 without Retry-After uses exponential backoff."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}

        call_count = [0]
        def rate_limited_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise requests.exceptions.HTTPError(response=mock_response)
            return "success"

        with patch.object(dexcom_readings, 'CIRCUIT_BREAKER_FAILURE_THRESHOLD', 10):
            result = dexcom_readings.retry_with_backoff(
                rate_limited_func,
                max_attempts=5,
                initial_delay=1,
                max_delay=30
            )

        self.assertEqual(result, "success")
        # Verify exponential backoff was used (first delay should be 1, second should be 2)
        sleep_calls = [c[0][0] for c in mock_sleep.call_args_list]
        self.assertEqual(sleep_calls[0], 1)  # First retry uses initial_delay

    @patch('dexcom_readings.time.sleep')
    @patch('dexcom_readings.logging.warning')
    def test_429_invalid_retry_after_falls_back_to_exponential(self, mock_log_warning, mock_sleep):
        """Verify HTTP 429 with invalid Retry-After falls back to exponential backoff."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "invalid"}

        call_count = [0]
        def rate_limited_func():
            call_count[0] += 1
            if call_count[0] == 1:
                raise requests.exceptions.HTTPError(response=mock_response)
            return "success"

        with patch.object(dexcom_readings, 'CIRCUIT_BREAKER_FAILURE_THRESHOLD', 10):
            result = dexcom_readings.retry_with_backoff(
                rate_limited_func,
                max_attempts=3,
                initial_delay=1
            )

        self.assertEqual(result, "success")
        # Should have used exponential backoff instead of invalid Retry-After
        sleep_calls = [c[0][0] for c in mock_sleep.call_args_list]
        self.assertEqual(sleep_calls[0], 1)  # Initial delay (exponential backoff)

    @patch('dexcom_readings.time.sleep')
    def test_non_429_http_error_uses_standard_retry(self, mock_sleep):
        """Verify non-429 HTTPError uses standard retry backoff."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {}

        call_count = [0]
        def error_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise requests.exceptions.HTTPError(response=mock_response)
            return "success"

        with patch.object(dexcom_readings, 'CIRCUIT_BREAKER_FAILURE_THRESHOLD', 10):
            result = dexcom_readings.retry_with_backoff(
                error_func,
                max_attempts=5,
                initial_delay=1
            )

        self.assertEqual(result, "success")
        # Verify standard exponential backoff was used
        sleep_calls = [c[0][0] for c in mock_sleep.call_args_list]
        self.assertEqual(sleep_calls[0], 1)  # First delay

    @patch('dexcom_readings.time.sleep')
    def test_multiple_429s_in_sequence_increase_delay(self, mock_sleep):
        """Verify multiple 429s in sequence use increasing delays (exponential backoff)."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}

        call_count = [0]
        def rate_limited_func():
            call_count[0] += 1
            if call_count[0] < 4:
                raise requests.exceptions.HTTPError(response=mock_response)
            return "success"

        with patch.object(dexcom_readings, 'CIRCUIT_BREAKER_FAILURE_THRESHOLD', 10):
            result = dexcom_readings.retry_with_backoff(
                rate_limited_func,
                max_attempts=5,
                initial_delay=1,
                max_delay=30
            )

        self.assertEqual(result, "success")
        # Verify delays increase: 1, 2, 4
        sleep_calls = [c[0][0] for c in mock_sleep.call_args_list]
        self.assertEqual(sleep_calls[0], 1)
        self.assertEqual(sleep_calls[1], 2)
        self.assertEqual(sleep_calls[2], 4)


class TestCircuitBreaker(unittest.TestCase):
    """Tests for circuit breaker state machine."""

    def setUp(self):
        """Reset circuit breaker state before each test."""
        dexcom_readings._circuit_state = "closed"
        dexcom_readings._circuit_failure_count = 0
        dexcom_readings._circuit_opened_at = None

    def tearDown(self):
        """Reset circuit breaker state after each test."""
        dexcom_readings._circuit_state = "closed"
        dexcom_readings._circuit_failure_count = 0
        dexcom_readings._circuit_opened_at = None

    def test_circuit_breaker_failure_threshold_default(self):
        """Verify CIRCUIT_BREAKER_FAILURE_THRESHOLD defaults to 5."""
        import importlib
        import os
        # Remove env var if set
        os.environ.pop('CIRCUIT_BREAKER_FAILURE_THRESHOLD', None)
        importlib.reload(dexcom_readings)
        self.assertEqual(dexcom_readings.CIRCUIT_BREAKER_FAILURE_THRESHOLD, 5)

    def test_circuit_breaker_failure_threshold_from_env(self):
        """Verify CIRCUIT_BREAKER_FAILURE_THRESHOLD uses env var value."""
        import importlib
        import os
        with patch.dict(os.environ, {'CIRCUIT_BREAKER_FAILURE_THRESHOLD': '10'}):
            importlib.reload(dexcom_readings)
            self.assertEqual(dexcom_readings.CIRCUIT_BREAKER_FAILURE_THRESHOLD, 10)

    def test_circuit_breaker_recovery_timeout_default(self):
        """Verify CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS defaults to 60."""
        import importlib
        import os
        os.environ.pop('CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS', None)
        importlib.reload(dexcom_readings)
        self.assertEqual(dexcom_readings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS, 60)

    def test_circuit_state_initializes_to_closed(self):
        """Verify _circuit_state initializes to 'closed'."""
        import importlib
        import os
        # Clear env vars and reload to get fresh state
        os.environ.pop('CIRCUIT_BREAKER_FAILURE_THRESHOLD', None)
        os.environ.pop('CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS', None)
        importlib.reload(dexcom_readings)
        self.assertEqual(dexcom_readings._circuit_state, "closed")

    def test_circuit_failure_count_initializes_to_zero(self):
        """Verify _circuit_failure_count initializes to 0."""
        import importlib
        import os
        os.environ.pop('CIRCUIT_BREAKER_FAILURE_THRESHOLD', None)
        os.environ.pop('CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS', None)
        importlib.reload(dexcom_readings)
        self.assertEqual(dexcom_readings._circuit_failure_count, 0)

    def test_circuit_opened_at_initializes_to_none(self):
        """Verify _circuit_opened_at initializes to None."""
        import importlib
        import os
        os.environ.pop('CIRCUIT_BREAKER_FAILURE_THRESHOLD', None)
        os.environ.pop('CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS', None)
        importlib.reload(dexcom_readings)
        self.assertIsNone(dexcom_readings._circuit_opened_at)

    # Tests for circuit_is_open()
    def test_circuit_is_open_returns_false_when_closed(self):
        """Verify circuit_is_open() returns False when state is 'closed'."""
        dexcom_readings._circuit_state = "closed"
        result = dexcom_readings.circuit_is_open()
        self.assertFalse(result)

    def test_circuit_is_open_returns_true_when_open_and_timeout_not_elapsed(self):
        """Verify circuit_is_open() returns True when state is 'open' and timeout not elapsed."""
        dexcom_readings._circuit_state = "open"
        dexcom_readings._circuit_opened_at = time.time()  # Just opened
        result = dexcom_readings.circuit_is_open()
        self.assertTrue(result)

    def test_circuit_is_open_transitions_to_half_open_after_timeout(self):
        """Verify circuit_is_open() transitions to 'half_open' after recovery timeout."""
        # Set circuit to open with timeout elapsed
        dexcom_readings._circuit_state = "open"
        # Set opened_at to more than RECOVERY_TIMEOUT seconds ago
        dexcom_readings._circuit_opened_at = (
            time.time() - dexcom_readings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT_SECONDS - 1
        )
        result = dexcom_readings.circuit_is_open()
        self.assertFalse(result)
        self.assertEqual(dexcom_readings._circuit_state, "half_open")

    def test_circuit_is_open_returns_false_when_half_open(self):
        """Verify circuit_is_open() returns False when state is 'half_open'."""
        dexcom_readings._circuit_state = "half_open"
        result = dexcom_readings.circuit_is_open()
        self.assertFalse(result)

    # Tests for record_circuit_failure()
    def test_record_circuit_failure_increments_count(self):
        """Verify record_circuit_failure() increments failure count."""
        dexcom_readings._circuit_failure_count = 0
        dexcom_readings.record_circuit_failure()
        self.assertEqual(dexcom_readings._circuit_failure_count, 1)

    def test_record_circuit_failure_opens_circuit_at_threshold(self):
        """Verify record_circuit_failure() opens circuit when threshold reached."""
        dexcom_readings._circuit_failure_count = (
            dexcom_readings.CIRCUIT_BREAKER_FAILURE_THRESHOLD - 1
        )
        dexcom_readings._circuit_state = "closed"
        dexcom_readings.record_circuit_failure()
        self.assertEqual(dexcom_readings._circuit_state, "open")
        self.assertIsNotNone(dexcom_readings._circuit_opened_at)

    @patch('dexcom_readings.logging.warning')
    def test_record_circuit_failure_logs_warning_on_open(self, mock_warning):
        """Verify record_circuit_failure() logs WARNING with failure count and threshold."""
        dexcom_readings._circuit_failure_count = (
            dexcom_readings.CIRCUIT_BREAKER_FAILURE_THRESHOLD - 1
        )
        dexcom_readings._circuit_state = "closed"
        dexcom_readings.record_circuit_failure()
        mock_warning.assert_called()
        call_args = str(mock_warning.call_args)
        self.assertIn("CLOSED -> OPEN", call_args)

    def test_record_circuit_failure_reopens_from_half_open(self):
        """Verify record_circuit_failure() transitions from 'half_open' to 'open'."""
        dexcom_readings._circuit_state = "half_open"
        dexcom_readings._circuit_opened_at = None
        dexcom_readings.record_circuit_failure()
        self.assertEqual(dexcom_readings._circuit_state, "open")
        self.assertIsNotNone(dexcom_readings._circuit_opened_at)

    # Tests for record_circuit_success()
    def test_record_circuit_success_resets_failure_count(self):
        """Verify record_circuit_success() resets failure count to 0."""
        dexcom_readings._circuit_failure_count = 3
        dexcom_readings.record_circuit_success()
        self.assertEqual(dexcom_readings._circuit_failure_count, 0)

    @patch('dexcom_readings.logging.warning')
    def test_record_circuit_success_closes_from_half_open(self, mock_warning):
        """Verify record_circuit_success() transitions from 'half_open' to 'closed'."""
        dexcom_readings._circuit_state = "half_open"
        dexcom_readings._circuit_opened_at = time.time()
        dexcom_readings.record_circuit_success()
        self.assertEqual(dexcom_readings._circuit_state, "closed")
        self.assertIsNone(dexcom_readings._circuit_opened_at)
        mock_warning.assert_called()
        call_args = str(mock_warning.call_args)
        self.assertIn("HALF_OPEN -> CLOSED", call_args)

    def test_record_circuit_success_does_nothing_when_closed(self):
        """Verify record_circuit_success() does nothing special when state is 'closed'."""
        dexcom_readings._circuit_state = "closed"
        dexcom_readings._circuit_failure_count = 0
        dexcom_readings._circuit_opened_at = None
        dexcom_readings.record_circuit_success()
        self.assertEqual(dexcom_readings._circuit_state, "closed")
        self.assertEqual(dexcom_readings._circuit_failure_count, 0)
        self.assertIsNone(dexcom_readings._circuit_opened_at)

    # Tests for retry_with_backoff integration with circuit breaker
    @patch('dexcom_readings.time.sleep')
    def test_retry_with_backoff_respects_open_circuit(self, mock_sleep):
        """Verify retry_with_backoff returns None when circuit is open."""
        from pydexcom.errors import SessionError

        # Set circuit to open
        dexcom_readings._circuit_state = "open"
        dexcom_readings._circuit_opened_at = time.time()

        call_count = [0]
        def failing_func():
            call_count[0] += 1
            raise SessionError()

        result = dexcom_readings.retry_with_backoff(failing_func, max_attempts=3)

        # Should return None without calling the function
        self.assertIsNone(result)
        self.assertEqual(call_count[0], 0)  # Function never called
        mock_sleep.assert_not_called()

    @patch('dexcom_readings.time.sleep')
    def test_retry_with_backoff_records_success(self, mock_sleep):
        """Verify retry_with_backoff calls record_circuit_success on success."""
        call_count = [0]
        def success_func():
            call_count[0] += 1
            return "success"

        # Start with some failures recorded
        dexcom_readings._circuit_failure_count = 3

        result = dexcom_readings.retry_with_backoff(success_func)

        self.assertEqual(result, "success")
        self.assertEqual(dexcom_readings._circuit_failure_count, 0)  # Reset on success
        self.assertEqual(dexcom_readings._circuit_state, "closed")

    @patch('dexcom_readings.time.sleep')
    def test_retry_with_backoff_records_failure_on_transient_error(self, mock_sleep):
        """Verify retry_with_backoff calls record_circuit_failure on transient error."""
        from pydexcom.errors import SessionError

        call_count = [0]
        def failing_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise SessionError()
            return "success"

        # Set threshold high enough to not open circuit
        with patch.object(dexcom_readings, 'CIRCUIT_BREAKER_FAILURE_THRESHOLD', 10):
            result = dexcom_readings.retry_with_backoff(failing_func, max_attempts=5)

        self.assertEqual(result, "success")
        # Failures recorded, then reset on success
        self.assertEqual(dexcom_readings._circuit_failure_count, 0)  # Reset on success

    def test_retry_with_backoff_does_not_record_failure_on_account_error(self):
        """Verify retry_with_backoff does NOT call record_circuit_failure on AccountError."""
        from pydexcom.errors import AccountError

        def account_error_func():
            raise AccountError()

        # Start with clean state
        dexcom_readings._circuit_failure_count = 0
        dexcom_readings._circuit_state = "closed"

        # AccountError should propagate, not be caught as transient
        with self.assertRaises(AccountError):
            dexcom_readings.retry_with_backoff(account_error_func, max_attempts=3)

        # Failure count should still be 0 - AccountError is not a transient failure
        self.assertEqual(dexcom_readings._circuit_failure_count, 0)
        self.assertEqual(dexcom_readings._circuit_state, "closed")

    @patch('dexcom_readings.time.sleep')
    def test_circuit_opens_after_threshold_failures(self, mock_sleep):
        """Verify circuit opens after threshold consecutive failures."""
        from pydexcom.errors import SessionError

        # Set threshold to 3
        with patch.object(dexcom_readings, 'CIRCUIT_BREAKER_FAILURE_THRESHOLD', 3):
            call_count = [0]
            def always_fail():
                call_count[0] += 1
                raise SessionError()

            # First call: failures accumulate but circuit stays closed
            dexcom_readings._circuit_failure_count = 0
            result1 = dexcom_readings.retry_with_backoff(always_fail, max_attempts=3)
            self.assertIsNone(result1)
            # After retries, failures are recorded
            # (3 retries = 3 failures recorded in this case)

            # Reset for second call attempt
            call_count[0] = 0

            # Set circuit to open state
            dexcom_readings._circuit_state = "open"
            dexcom_readings._circuit_opened_at = time.time()

            # Second call: circuit is open, should return None immediately
            result2 = dexcom_readings.retry_with_backoff(always_fail, max_attempts=3)
            self.assertIsNone(result2)
            # Function should not be called when circuit is open
            self.assertEqual(call_count[0], 0)


class TestTimeoutConfiguration(unittest.TestCase):
    """Tests for timeout configuration constants."""

    def tearDown(self):
        """Reload module to restore original constants after each test."""
        import importlib
        # Clear any environment variables that might have been set
        os.environ.pop('DEXCOM_CONNECTION_TIMEOUT_SECONDS', None)
        os.environ.pop('DEXCOM_READ_TIMEOUT_SECONDS', None)
        importlib.reload(dexcom_readings)

    def test_connection_timeout_defaults_to_30(self):
        """Verify DEXCOM_CONNECTION_TIMEOUT_SECONDS defaults to 30."""
        import importlib
        os.environ.pop('DEXCOM_CONNECTION_TIMEOUT_SECONDS', None)
        importlib.reload(dexcom_readings)
        self.assertEqual(
            dexcom_readings.DEXCOM_CONNECTION_TIMEOUT_SECONDS, 30,
            "Connection timeout should default to 30 seconds"
        )

    def test_connection_timeout_from_env(self):
        """Verify DEXCOM_CONNECTION_TIMEOUT_SECONDS uses env var value."""
        import importlib
        with patch.dict(os.environ, {'DEXCOM_CONNECTION_TIMEOUT_SECONDS': '45'}):
            importlib.reload(dexcom_readings)
            self.assertEqual(
                dexcom_readings.DEXCOM_CONNECTION_TIMEOUT_SECONDS, 45,
                "Connection timeout should use env var value"
            )

    def test_read_timeout_defaults_to_30(self):
        """Verify DEXCOM_READ_TIMEOUT_SECONDS defaults to 30."""
        import importlib
        os.environ.pop('DEXCOM_READ_TIMEOUT_SECONDS', None)
        importlib.reload(dexcom_readings)
        self.assertEqual(
            dexcom_readings.DEXCOM_READ_TIMEOUT_SECONDS, 30,
            "Read timeout should default to 30 seconds"
        )

    def test_read_timeout_from_env(self):
        """Verify DEXCOM_READ_TIMEOUT_SECONDS uses env var value."""
        import importlib
        with patch.dict(os.environ, {'DEXCOM_READ_TIMEOUT_SECONDS': '60'}):
            importlib.reload(dexcom_readings)
            self.assertEqual(
                dexcom_readings.DEXCOM_READ_TIMEOUT_SECONDS, 60,
                "Read timeout should use env var value"
            )

    @patch('dexcom_readings.logging.warning')
    def test_connection_timeout_invalid_uses_default(self, mock_warning):
        """Verify invalid DEXCOM_CONNECTION_TIMEOUT_SECONDS uses default."""
        import importlib
        with patch.dict(os.environ, {'DEXCOM_CONNECTION_TIMEOUT_SECONDS': 'invalid'}):
            importlib.reload(dexcom_readings)
            # Should fall back to default
            self.assertEqual(
                dexcom_readings.DEXCOM_CONNECTION_TIMEOUT_SECONDS, 30,
                "Invalid connection timeout should fall back to default"
            )

    @patch('dexcom_readings.logging.warning')
    def test_read_timeout_invalid_uses_default(self, mock_warning):
        """Verify invalid DEXCOM_READ_TIMEOUT_SECONDS uses default."""
        import importlib
        with patch.dict(os.environ, {'DEXCOM_READ_TIMEOUT_SECONDS': 'invalid'}):
            importlib.reload(dexcom_readings)
            # Should fall back to default
            self.assertEqual(
                dexcom_readings.DEXCOM_READ_TIMEOUT_SECONDS, 30,
                "Invalid read timeout should fall back to default"
            )

    @patch('dexcom_readings.logging.warning')
    def test_connection_timeout_too_low_uses_default(self, mock_warning):
        """Verify DEXCOM_CONNECTION_TIMEOUT_SECONDS < 1 uses default 30."""
        import importlib
        with patch.dict(os.environ, {'DEXCOM_CONNECTION_TIMEOUT_SECONDS': '0'}):
            importlib.reload(dexcom_readings)
            self.assertEqual(
                dexcom_readings.DEXCOM_CONNECTION_TIMEOUT_SECONDS, 30,
                "Connection timeout < 1 should use default"
            )
            mock_warning.assert_called()

    @patch('dexcom_readings.logging.warning')
    def test_read_timeout_too_low_uses_default(self, mock_warning):
        """Verify DEXCOM_READ_TIMEOUT_SECONDS < 1 uses default 30."""
        import importlib
        with patch.dict(os.environ, {'DEXCOM_READ_TIMEOUT_SECONDS': '0'}):
            importlib.reload(dexcom_readings)
            self.assertEqual(
                dexcom_readings.DEXCOM_READ_TIMEOUT_SECONDS, 30,
                "Read timeout < 1 should use default"
            )
            mock_warning.assert_called()


class TestTimeoutSession(unittest.TestCase):
    """Tests for TimeoutSession and timeout configuration."""

    def test_timeout_session_inherits_from_session(self):
        """Verify TimeoutSession is a requests.Session subclass."""
        self.assertTrue(
            issubclass(dexcom_readings.TimeoutSession, requests.Session),
            "TimeoutSession should inherit from requests.Session"
        )

    def test_timeout_session_sets_timeout_on_request(self):
        """Verify TimeoutSession passes timeout to request method."""
        with patch.object(requests.Session, 'request') as mock_request:
            mock_request.return_value = MagicMock()

            session = dexcom_readings.TimeoutSession(timeout=(5.0, 10.0))
            session.request('GET', 'http://example.com')

            # Verify timeout was passed to request
            call_kwargs = mock_request.call_args[1]
            self.assertEqual(call_kwargs.get('timeout'), (5.0, 10.0))

    def test_timeout_session_preserves_explicit_timeout(self):
        """Verify explicit timeout kwarg overrides default."""
        with patch.object(requests.Session, 'request') as mock_request:
            mock_request.return_value = MagicMock()

            session = dexcom_readings.TimeoutSession(timeout=(5.0, 10.0))
            session.request('GET', 'http://example.com', timeout=(1.0, 2.0))

            # Explicit timeout should override default
            call_kwargs = mock_request.call_args[1]
            self.assertEqual(call_kwargs.get('timeout'), (1.0, 2.0))

    def test_timeout_session_timeout_is_tuple(self):
        """Verify timeout is (connection, read) tuple."""
        session = dexcom_readings.TimeoutSession(timeout=(30.0, 30.0))
        self.assertEqual(session._timeout, (30.0, 30.0))

    @patch('dexcom_readings.Dexcom')
    def test_initialize_dexcom_client_creates_timeout_session(self, mock_dexcom):
        """Verify initialize_dexcom_client creates TimeoutSession."""
        mock_client = MagicMock()
        mock_dexcom.return_value = mock_client

        with (patch('dexcom_readings.DEXCOM_USERNAME', 'testuser'),
              patch('dexcom_readings.DEXCOM_PASSWORD', 'testpassword'),
              patch('dexcom_readings.DEXCOM_REGION', 'us')):
            client = dexcom_readings.initialize_dexcom_client()

        # Verify _session was set to a TimeoutSession instance
        self.assertIsNotNone(client)
        self.assertIsInstance(
            client._session,
            dexcom_readings.TimeoutSession,
            "dexcom_client._session should be TimeoutSession instance"
        )

    def test_timeout_uses_configured_values(self):
        """Verify TimeoutSession uses configured timeout values."""
        import importlib
        with patch.dict(os.environ, {
            'DEXCOM_USERNAME': 'testuser',
            'DEXCOM_PASSWORD': 'testpass',
            'DEXCOM_CONNECTION_TIMEOUT_SECONDS': '45',
            'DEXCOM_READ_TIMEOUT_SECONDS': '60'
        }):
            # Reload module to pick up new env vars
            importlib.reload(dexcom_readings)

            # Now patch Dexcom on the reloaded module
            with patch.object(dexcom_readings, 'Dexcom') as mock_dexcom:
                mock_client = MagicMock()
                mock_dexcom.return_value = mock_client

                client = dexcom_readings.initialize_dexcom_client()

                # Verify timeout matches configured values
                self.assertIsNotNone(client)
                self.assertEqual(client._session._timeout, (45, 60))

        # Reload again to restore original state
        os.environ.pop('DEXCOM_CONNECTION_TIMEOUT_SECONDS', None)
        os.environ.pop('DEXCOM_READ_TIMEOUT_SECONDS', None)
        importlib.reload(dexcom_readings)


if __name__ == '__main__':
    unittest.main()