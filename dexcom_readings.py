"""Dexcom CGM data polling and forwarding service.

This module provides continuous glucose monitoring data replication from the
Dexcom Share API to Nightscout with local CSV logging for backup.

Usage:
    Set environment variables: DEXCOM_USERNAME, DEXCOM_PASSWORD
    Optional: DEXCOM_REGION, NIGHTSCOUT_URL, NIGHTSCOUT_API_SECRET
    Run: python dexcom_readings.py

License:
    Copyright 2026. All rights reserved.
"""

import csv
import datetime
import logging
from logging.handlers import SysLogHandler, WatchedFileHandler
import os
import signal
import sys
import time
import fcntl
from pathlib import Path
from typing import Any, Optional

from pydexcom import Dexcom  # Dexcom Share API client

import requests

# IMPORTANT: Store your credentials securely as environment variables
DEXCOM_USERNAME = os.environ.get("DEXCOM_USERNAME")
DEXCOM_PASSWORD = os.environ.get("DEXCOM_PASSWORD")
# Optional: Specify if outside the US, e.g., "ous" for "outside US" or "jp" for
# Japan. Default is "us".
DEXCOM_REGION = os.environ.get("DEXCOM_REGION", "us")

NIGHTSCOUT_URL = os.environ.get("NIGHTSCOUT_URL")
# Use a hashed secret if possible, but plain is common for API uploads
NIGHTSCOUT_API_SECRET = os.environ.get("NIGHTSCOUT_API_SECRET")

# Polling interval in seconds (configurable via environment variable)
try:
    POLLING_INTERVAL_SECONDS = int(
        os.environ.get("POLLING_INTERVAL_SECONDS", "60")
    )
    if POLLING_INTERVAL_SECONDS < 1:
        logging.warning(
            "POLLING_INTERVAL_SECONDS must be at least 1, using default 60"
        )
        POLLING_INTERVAL_SECONDS = 60
except ValueError:
    logging.warning(
        "Invalid POLLING_INTERVAL_SECONDS value, using default 60"
    )
    POLLING_INTERVAL_SECONDS = 60

# Retry configuration for transient failures
RETRY_MAX_ATTEMPTS = 3
RETRY_INITIAL_DELAY_SECONDS = 1
RETRY_MAX_DELAY_SECONDS = 30

# XDG Base Directory Specification defaults
DEFAULT_DATA_DIR = os.environ.get(
    "XDG_DATA_HOME", str(Path.home() / ".local" / "share")
)
DEFAULT_STATE_DIR = os.environ.get(
    "XDG_STATE_HOME", str(Path.home() / ".local" / "state")
)

# Configurable file paths (all absolute)
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

# Logging configuration
LOG_DESTINATION = os.environ.get("DEXCOM_LOG_DESTINATION", "console").lower()
LOG_LEVEL = os.environ.get("DEXCOM_LOG_LEVEL", "INFO").upper()

CSV_HEADERS = [
    "check_timestamp_utc", "new_reading_received", "glucose_value_mgdl",
    "glucose_timestamp_utc", "trend_description", "trend_arrow"
]


class PIDFile:
    """Context manager for PID-based single-instance locking.

    Uses fcntl file locking to guarantee the lock is released even if
    the process crashes. Prevents stale PID files from blocking startup.

    Attributes:
        pidfile_path: Path to the PID file.
        pidfile: File handle for the PID file.

    Example:
        with PIDFile("/var/run/dexcom-readings.pid") as pid:
            # Only one instance can reach here
            main_loop()
    """

    def __init__(self, pidfile_path: str) -> None:
        """Initialize the PID file context manager.

        Args:
            pidfile_path: Path to the PID file.
        """
        self.pidfile_path = pidfile_path
        self.pidfile: Optional[Any] = None

    def __enter__(self) -> "PIDFile":
        """Acquire the PID file lock.

        Creates parent directory if needed, opens the PID file, and
        acquires an exclusive non-blocking lock. Writes the current
        process ID to the file.

        Returns:
            PIDFile: self, allowing use as a context manager.

        Raises:
            RuntimeError: If another instance is already running.
        """
        # Create parent directory if needed
        pid_dir = os.path.dirname(self.pidfile_path)
        if pid_dir and not os.path.exists(pid_dir):
            os.makedirs(pid_dir, exist_ok=True)

        self.pidfile = open(self.pidfile_path, "w")
        try:
            # LOCK_EX = exclusive lock, LOCK_NB = non-blocking
            fcntl.flock(self.pidfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.pidfile.write(f"{os.getpid()}\n")
            self.pidfile.flush()
            logging.info(f"Acquired PID file lock: {self.pidfile_path}")
            return self
        except BlockingIOError:
            self.pidfile.close()
            raise RuntimeError(
                f"Another instance is already running (PID file: {self.pidfile_path})"
            )

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any]
    ) -> None:
        """Release the PID file lock and clean up.

        Releases the file lock, closes the file handle, and removes
        the PID file from the filesystem.

        Args:
            exc_type: Exception type if an exception was raised.
            exc_val: Exception value if an exception was raised.
            exc_tb: Exception traceback if an exception was raised.

        Returns:
            None
        """
        if self.pidfile:
            fcntl.flock(self.pidfile.fileno(), fcntl.LOCK_UN)
            self.pidfile.close()
            try:
                os.unlink(self.pidfile_path)
            except OSError:
                pass  # File may already be deleted


def setup_logging() -> logging.Logger:
    """Configure logging based on DEXCOM_LOG_DESTINATION environment variable.

    Supports three destinations:
    - console: StreamHandler to stderr (default)
    - file: WatchedFileHandler for log rotation support
    - syslog: SysLogHandler for Unix syslog integration

    Returns:
        logging.Logger: The configured root logger.
    """
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )

    if LOG_DESTINATION == "file":
        # Ensure log directory exists
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        handler = WatchedFileHandler(LOG_FILE, encoding="utf-8")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logging.info(f"Logging to file: {LOG_FILE}")

    elif LOG_DESTINATION == "syslog":
        # Try common syslog addresses
        syslog_addresses = [
            "/dev/log",       # Linux
            "/var/run/syslog",  # macOS (may not work on macOS 12+)
        ]
        handler = None
        for address in syslog_addresses:
            if os.path.exists(address):
                handler = SysLogHandler(address=address)
                break

        if handler is None:
            # Fallback to console if syslog not available
            logging.warning(
                "Syslog not available, falling back to console logging"
            )
            handler = logging.StreamHandler()

        # Syslog format typically includes the program name
        syslog_formatter = logging.Formatter(
            'dexcom-readings[%(process)d]: %(levelname)s - %(message)s'
        )
        handler.setFormatter(syslog_formatter)
        logger.addHandler(handler)
        logging.info("Logging to syslog")

    else:  # console (default)
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


# Shutdown flag for graceful termination
shutdown_requested = False


def retry_with_backoff(
        func: Any,
        max_attempts: int = RETRY_MAX_ATTEMPTS,
        initial_delay: float = RETRY_INITIAL_DELAY_SECONDS,
        max_delay: float = RETRY_MAX_DELAY_SECONDS) -> Optional[Any]:
    """Executes a function with exponential backoff retry for transient failures.

    Retries the function on network-related exceptions, doubling the delay
    between attempts up to max_delay.

    Args:
        func: A callable to execute. Should be a lambda or partial that
            captures any arguments needed.
        max_attempts: Maximum number of retry attempts before giving up.
        initial_delay: Initial delay in seconds before first retry.
        max_delay: Maximum delay in seconds between retries.

    Returns:
        Any | None: The function result on success, or None if all
            attempts fail.

    Raises:
        No exceptions raised; errors are logged and None is returned.
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(max_attempts):
        try:
            return func()
        except (requests.exceptions.RequestException,
                ConnectionError,
                TimeoutError) as e:
            last_exception = e
            if attempt < max_attempts - 1:
                logging.warning(
                    f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)
                delay = min(delay * 2, max_delay)
            else:
                logging.error(
                    f"All {max_attempts} attempts failed. Last error: {e}"
                )

    return None


def handle_shutdown_signal(signum: int, frame: Any) -> None:
    """Handles SIGTERM and SIGINT for graceful shutdown.

    Sets the shutdown_requested flag to allow the main loop to
    complete the current polling cycle before exiting.

    Args:
        signum: The signal number received (SIGTERM or SIGINT).
        frame: The current stack frame (unused).

    Returns:
        None
    """
    global shutdown_requested
    signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
    logging.info(f"Received {signal_name}, completing current cycle...")
    shutdown_requested = True


def initialize_dexcom_client() -> Optional[Any]:
    """Initializes and authenticates a Dexcom Share API client.

    Reads credentials from environment variables (DEXCOM_USERNAME,
    DEXCOM_PASSWORD, DEXCOM_REGION) and creates an authenticated
    Dexcom client for fetching glucose readings.

    Args:
        None

    Returns:
        Dexcom | None: An authenticated Dexcom client instance, or None
            if credentials are missing or authentication fails.

    Raises:
        No exceptions raised; errors are logged and None is returned.
    """
    if not DEXCOM_USERNAME or not DEXCOM_PASSWORD:
        logging.error("DEXCOM_USERNAME and DEXCOM_PASSWORD must be set.")
        return None  # Return None instead of exiting, let main handle exit

    logging.info(f"Connecting to Dexcom Share for user {DEXCOM_USERNAME} "
          f"in region {DEXCOM_REGION}...")
    try:
        if DEXCOM_REGION.lower() == "us":
            logging.info("Connecting in us")
            dexcom_client = Dexcom(username=DEXCOM_USERNAME,
                                   password=DEXCOM_PASSWORD)
        else:
            dexcom_client = Dexcom(
                DEXCOM_USERNAME,
                DEXCOM_PASSWORD,
                ous=DEXCOM_REGION.lower() == "ous"
            )
        logging.info("Successfully connected to Dexcom Share.")
        return dexcom_client
    except Exception as e:
        logging.error(f"Error initializing Dexcom client: {e}")
        return None

def get_latest_glucose_reading(dexcom_client: Any) -> Optional[Any]:
    """Fetches the most recent glucose reading from the Dexcom API.

    Uses retry logic with exponential backoff for transient failures.

    Args:
        dexcom_client: An authenticated Dexcom client instance from
            pydexcom library.

    Returns:
        GlucoseReading | None: The latest glucose reading object containing
            value, datetime, and trend information, or None if all
            retry attempts fail or client is invalid.

    Raises:
        No exceptions raised; errors are logged and None is returned.
    """
    if not dexcom_client:
        return None

    def fetch_reading() -> Any:
        return dexcom_client.get_current_glucose_reading()

    result = retry_with_backoff(fetch_reading)
    if result is None:
        logging.error("Failed to fetch glucose reading after all retries")
    return result

def write_to_csv(data_row: list) -> None:
    """Appends a glucose reading data row to the CSV log file.

    Creates the file with headers if it doesn't exist, otherwise appends
    the data row to the existing file.

    Args:
        data_row: A list of values to write as a CSV row. Expected format:
            [check_timestamp_utc, new_reading_received, glucose_value_mgdl,
             glucose_timestamp_utc, trend_description, trend_arrow]

    Returns:
        None

    Raises:
        No exceptions raised; file I/O errors are not caught here.
    """
    file_exists = os.path.isfile(OUTPUT_CSV_FILE)
    with open(OUTPUT_CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(CSV_HEADERS)
        writer.writerow(data_row)

def upload_to_nightscout(
        value: int,
        timestamp_utc: datetime.datetime,
        trend_arrow: str) -> None:
    """Uploads a glucose reading to Nightscout via REST API.

    Uses retry logic with exponential backoff for transient failures.
    Requires NIGHTSCOUT_URL and NIGHTSCOUT_API_SECRET environment
    variables to be set. If either is missing, the function returns
    early without uploading.

    Args:
        value: The glucose value in mg/dL as an integer.
        timestamp_utc: A datetime object representing the reading timestamp
            in UTC.
        trend_arrow: A string representing the trend direction arrow
            (e.g., "→", "↑", "↓↓").

    Returns:
        None

    Raises:
        No exceptions raised; HTTP and network errors are logged and the
            function returns silently.
    """
    if not NIGHTSCOUT_URL or not NIGHTSCOUT_API_SECRET:
        return

    date_string = timestamp_utc.isoformat()
    entry = {
        "dateString": date_string,
        "sgv": value,
        "direction": trend_arrow,
        "type": "sgv"
    }

    url = f"{NIGHTSCOUT_URL.rstrip('/')}/api/v1/entries"
    headers = {
        "api-secret": NIGHTSCOUT_API_SECRET,
        "Content-Type": "application/json"
    }

    def post_to_nightscout() -> None:
        logging.info(f"Uploading reading to Nightscout: {value} "
                    f"at {date_string}")
        response = requests.post(
            url, json=[entry], headers=headers, timeout=30
        )
        response.raise_for_status()
        logging.info("Successfully uploaded to Nightscout.")

    result = retry_with_backoff(post_to_nightscout)
    if result is None:
        logging.error(
            f"Failed to upload to Nightscout after all retries: "
            f"{value} at {date_string}"
        )

def main() -> None:
    """Main entry point with PID file single-instance enforcement.

    Acquires a PID file lock before starting the polling loop. If another
    instance is already running, exits with an error message.

    Continuously polls the Dexcom Share API for new glucose readings,
    logs data to CSV, and uploads to Nightscout when configured.

    Args:
        None

    Returns:
        None

    Raises:
        SystemExit: If Dexcom client initialization fails (exit code 1).
        SystemExit: If another instance is already running (exit code 1).
    """
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGINT, handle_shutdown_signal)

    # Acquire PID file lock for single-instance enforcement
    try:
        with PIDFile(PID_FILE) as pid:
            _run_main_loop()
    except RuntimeError as e:
        logging.error(str(e))
        sys.exit(1)


def _run_main_loop() -> None:
    """Internal main loop, called after PID file is acquired.

    Separated from main() to allow clean PID file handling.

    Continuously polls the Dexcom Share API for new glucose readings,
    logs data to CSV, and uploads to Nightscout when configured.

    Args:
        None

    Returns:
        None

    Raises:
        SystemExit: If Dexcom client initialization fails (exit code 1).
    """
    setup_logging()  # Initialize logging based on LOG_DESTINATION

    last_known_glucose_timestamp = None  # Local state, not global

    dexcom_client = initialize_dexcom_client()
    if not dexcom_client:
        logging.error("Exiting due to Dexcom client initialization failure.")
        sys.exit(1)  # Now exit here after logging

    if not NIGHTSCOUT_URL or not NIGHTSCOUT_API_SECRET:
        logging.warning("NIGHTSCOUT_URL or NIGHTSCOUT_API_SECRET not set. "
              "Nightscout upload will be skipped.")
    else:
        logging.info(f"Nightscout upload enabled for URL: {NIGHTSCOUT_URL}")

    logging.info(f"Polling Dexcom every {POLLING_INTERVAL_SECONDS} seconds. "
          f"Logging to {OUTPUT_CSV_FILE}")

    while not shutdown_requested:
        check_timestamp_utc = datetime.datetime.utcnow()
        new_reading_received = False

        current_bg = get_latest_glucose_reading(dexcom_client)

        glucose_value_to_log = None
        glucose_timestamp_to_log = None
        trend_description_to_log = None
        trend_arrow_to_log = None

        current_glucose_datetime = None

        if current_bg:
            current_glucose_datetime = current_bg.datetime

            if (last_known_glucose_timestamp is None or
                    current_glucose_datetime > last_known_glucose_timestamp):
                new_reading_received = True  # noqa: E501

                last_known_glucose_timestamp = current_glucose_datetime

                glucose_value_to_log = current_bg.value
                glucose_timestamp_to_log = current_glucose_datetime.isoformat()
                trend_description_to_log = current_bg.trend_description
                trend_arrow_to_log = current_bg.trend_arrow

                # Changed to logging for new reading notification
                logging.info(
                    f"{check_timestamp_utc.isoformat()}: New reading! "
                    f"Value: {current_bg.value} mg/dL "
                    f"({current_bg.trend_description}), "
                    f"Time: {current_glucose_datetime.isoformat()}"
                )

                upload_to_nightscout(
                    glucose_value_to_log,
                    current_glucose_datetime,
                    trend_arrow_to_log
                )
            else:
                last_known = (last_known_glucose_timestamp.isoformat() if
                              last_known_glucose_timestamp else 'N/A')
                logging.info(
                    f"{check_timestamp_utc.isoformat()}: No new reading. "
                    f"Last known: {last_known}"
                )
        else:
            logging.warning(f"{check_timestamp_utc.isoformat()}: Could not "
                            f"retrieve glucose reading.")

        log_row = [
            check_timestamp_utc.isoformat(),
            new_reading_received,
            glucose_value_to_log,
            glucose_timestamp_to_log,
            trend_description_to_log,
            trend_arrow_to_log
        ]
        write_to_csv(log_row)

        time.sleep(POLLING_INTERVAL_SECONDS)

    logging.info("Shutdown complete.")


if __name__ == "__main__":
    if not os.path.isfile(OUTPUT_CSV_FILE):
        with open(OUTPUT_CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)
    main()
