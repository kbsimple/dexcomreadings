import csv
import datetime
import os
import time
from pydexcom import Dexcom  # Or the specific import from the library you choose

# --- Configuration ---
# IMPORTANT: Store your credentials securely as environment variables
DEXCOM_USERNAME = os.environ.get("DEXCOM_USERNAME")
DEXCOM_PASSWORD = os.environ.get("DEXCOM_PASSWORD")
# Optional: Specify if outside the US, e.g., "ous" for "outside US" or "jp" for
# Japan. Default is "us".
DEXCOM_REGION = os.environ.get("DEXCOM_REGION", "us")

# Polling interval in seconds
POLLING_INTERVAL_SECONDS = 60

# CSV file for logging
OUTPUT_CSV_FILE = "dexcom_readings_log.csv"
CSV_HEADERS = [
    "check_timestamp_utc", "new_reading_received", "glucose_value_mgdl",
    "glucose_timestamp_utc", "trend_description", "trend_arrow"
]

# --- Global State ---
last_known_glucose_timestamp = None

def initialize_dexcom_client():
    """Initializes and returns the Dexcom client."""
    if not DEXCOM_USERNAME or not DEXCOM_PASSWORD:
        print("Error: DEXCOM_USERNAME and DEXCOM_PASSWORD must be set.")
        exit(1)
    
    print(f"Connecting to Dexcom Share for user {DEXCOM_USERNAME} in region "
          f"{DEXCOM_REGION}...")
    try:
        if DEXCOM_REGION.lower() == "us":
            print("Connecting in us")
            dexcom_client = Dexcom(username=DEXCOM_USERNAME,
                                   password=DEXCOM_PASSWORD)
        else:
            dexcom_client = Dexcom(DEXCOM_USERNAME, DEXCOM_PASSWORD,
                                   ous=(DEXCOM_REGION.lower() == "ous"))
        print("Successfully connected to Dexcom Share.")
        return dexcom_client
    except Exception as e:
        print(f"Error initializing Dexcom client: {e}")
        return None

def get_latest_glucose_reading(dexcom_client):
    """Fetches the latest glucose reading from Dexcom."""
    if not dexcom_client:
        return None
    try:
        bg = dexcom_client.get_current_glucose_reading()
        return bg
    except Exception as e:
        print(f"Error fetching glucose reading: {e}")
        return None

def write_to_csv(data_row):
    """Appends a row of data to the CSV file."""
    file_exists = os.path.isfile(OUTPUT_CSV_FILE)
    with open(OUTPUT_CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(CSV_HEADERS)
        writer.writerow(data_row)

def main():
    global last_known_glucose_timestamp

    dexcom_client = initialize_dexcom_client()
    if not dexcom_client:
        print("Exiting due to Dexcom client initialization failure.")
        return

    print(f"Polling Dexcom every {POLLING_INTERVAL_SECONDS} seconds. Logging "
          f"to {OUTPUT_CSV_FILE}")

    while True:
        check_timestamp_utc = datetime.datetime.utcnow()
        new_reading_received = False
        
        current_bg = get_latest_glucose_reading(dexcom_client)

        glucose_value_to_log = None
        glucose_timestamp_to_log = None
        trend_description_to_log = None
        trend_arrow_to_log = None

        if current_bg:
            current_glucose_timestamp = current_bg.datetime

            if (last_known_glucose_timestamp is None or
                    current_glucose_timestamp > last_known_glucose_timestamp):
                new_reading_received = True
                last_known_glucose_timestamp = current_glucose_timestamp
                
                glucose_value_to_log = current_bg.value
                glucose_timestamp_to_log = current_glucose_timestamp.isoformat()
                trend_description_to_log = current_bg.trend_description
                trend_arrow_to_log = current_bg.trend_arrow
                
                print(f"{check_timestamp_utc.isoformat()}: New reading! Value: "
                      f"{current_bg.value} mg/dL ({current_bg.trend_description}), "
                      f"Time: {current_glucose_timestamp.isoformat()}")
            else:
                print(f"{check_timestamp_utc.isoformat()}: No new reading. Last "
                      f"known: {last_known_glucose_timestamp.isoformat() if "
                      f"last_known_glucose_timestamp else 'N/A'}")
        else:
            print(f"{check_timestamp_utc.isoformat()}: Could not retrieve "
                  f"glucose reading.")

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
