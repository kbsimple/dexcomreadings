import csv
import datetime
import os
import time
import logging
import requests
from pydexcom import Dexcom  # Or the specific import from the library you choose

# IMPORTANT: Store your credentials securely as environment variables
DEXCOM_USERNAME = os.environ.get("DEXCOM_USERNAME")
DEXCOM_PASSWORD = os.environ.get("DEXCOM_PASSWORD")
# Optional: Specify if outside the US, e.g., "ous" for "outside US" or "jp" for
# Japan. Default is "us".
DEXCOM_REGION = os.environ.get("DEXCOM_REGION", "us")

NIGHTSCOUT_URL = os.environ.get("NIGHTSCOUT_URL")
# Use a hashed secret if possible, but plain is common for API uploads
NIGHTSCOUT_API_SECRET = os.environ.get("NIGHTSCOUT_API_SECRET")

# Polling interval in seconds
POLLING_INTERVAL_SECONDS = 60

# CSV file for logging
OUTPUT_CSV_FILE = "dexcom_readings_log.csv"
CSV_HEADERS = [
    "check_timestamp_utc", "new_reading_received", "glucose_value_mgdl",
    "glucose_timestamp_utc", "trend_description", "trend_arrow"
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')

# Suppress excessive logging from requests or other libraries if needed
# logging.getLogger("requests").setLevel(logging.WARNING)

last_known_glucose_timestamp = None

def initialize_dexcom_client():
    """Initializes and returns the Dexcom client."""
    if not DEXCOM_USERNAME or not DEXCOM_PASSWORD:
        logging.error("DEXCOM_USERNAME and DEXCOM_PASSWORD must be set.")
        return None # Return None instead of exiting, let main handle exit
    
    logging.info(f"Connecting to Dexcom Share for user {DEXCOM_USERNAME} "
          f"in region {DEXCOM_REGION}...")
    try:
        if DEXCOM_REGION.lower() == "us":
            logging.info("Connecting in us")
            dexcom_client = Dexcom(username=DEXCOM_USERNAME,
                                   password=DEXCOM_PASSWORD)
        else:
            dexcom_client = Dexcom(DEXCOM_USERNAME, DEXCOM_PASSWORD,
                                   ous=(DEXCOM_REGION.lower() == "ous"))
        logging.info("Successfully connected to Dexcom Share.")
        return dexcom_client
    except Exception as e:
        logging.error(f"Error initializing Dexcom client: {e}")
        return None

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

def write_to_csv(data_row):
    """Appends a row of data to the CSV file."""
    file_exists = os.path.isfile(OUTPUT_CSV_FILE)
    with open(OUTPUT_CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(CSV_HEADERS)
        writer.writerow(data_row)

def upload_to_nightscout(value, timestamp_utc, trend_arrow):
    """Uploads a single glucose reading to Nightscout."""
    if not NIGHTSCOUT_URL or not NIGHTSCOUT_API_SECRET:
        return

    # Nightscout expects ISO 8601 format, UTC
    # The pydexcom datetime object is already UTC
    date_string = timestamp_utc.isoformat()

    # Nightscout typically uses arrow names for direction
    direction = trend_arrow

    entry = {
        "dateString": date_string,
        "sgv": value,
        "direction": direction,
        "type": "sgv" # Specify type as sgv (sensor glucose value)
    }

    url = f"{NIGHTSCOUT_URL.rstrip('/')}/api/v1/entries"
    headers = {
        "api-secret": NIGHTSCOUT_API_SECRET,
        "Content-Type": "application/json"
    }

    try:
        logging.info(f"Uploading reading to Nightscout: {value} at "
              f"{date_string}")
        response = requests.post(url, json=[entry], headers=headers)
        response.raise_for_status()  # For bad status codes (4xx or 5xx)
        logging.info("Successfully uploaded to Nightscout.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error uploading to Nightscout: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during Nightscout upload: {e}")

def main():
    global last_known_glucose_timestamp

    dexcom_client = initialize_dexcom_client()
    if not dexcom_client:
        logging.error("Exiting due to Dexcom client initialization failure.")
        exit(1) # Now exit here after logging

    if not NIGHTSCOUT_URL or not NIGHTSCOUT_API_SECRET:
        logging.warning("NIGHTSCOUT_URL or NIGHTSCOUT_API_SECRET not set. "
              "Nightscout upload will be skipped.")
    else:
        logging.info(f"Nightscout upload enabled for URL: {NIGHTSCOUT_URL}")

    logging.info(f"Polling Dexcom every {POLLING_INTERVAL_SECONDS} seconds. "
          f"Logging to {OUTPUT_CSV_FILE}")

    while True:
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
                new_reading_received = True # noqa: E501

                last_known_glucose_timestamp = current_glucose_datetime
                
                glucose_value_to_log = current_bg.value
                glucose_timestamp_to_log = current_glucose_datetime.isoformat()
                trend_description_to_log = current_bg.trend_description
                trend_arrow_to_log = current_bg.trend_arrow
                
                # Corrected duplicated "New reading! Value: " and changed to logging
                logging.info(f"{check_timestamp_utc.isoformat()}: New reading! Value: {current_bg.value} mg/dL "
                      f"({current_bg.trend_description}), Time: "
                      f"{current_glucose_datetime.isoformat()}")

                upload_to_nightscout(
                    glucose_value_to_log,
                    current_glucose_datetime,
                    trend_arrow_to_log
                )
            else:
                last_known = (last_known_glucose_timestamp.isoformat() if
                              last_known_glucose_timestamp else 'N/A')
                logging.info(f"{check_timestamp_utc.isoformat()}: No new reading. "
                      f"Last known: {last_known}")
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

if __name__ == "__main__":
    if not os.path.isfile(OUTPUT_CSV_FILE):
        with open(OUTPUT_CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)
    main()
