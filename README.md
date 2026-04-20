# Dexcom Readings

A continuous glucose monitoring (CGM) data polling and forwarding service that
replicates glucose readings from the Dexcom Share API to Nightscout with local
CSV logging for backup.

## Installation

### Prerequisites

- Python 3.9 or higher
- A Dexcom Share account with data sharing enabled
- (Optional) A Nightscout instance for data upload

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd dexcomreadings
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

The application is configured via environment variables:

### Required Variables

| Variable | Description |
|----------|-------------|
| `DEXCOM_USERNAME` | Your Dexcom Share username |
| `DEXCOM_PASSWORD` | Your Dexcom Share password |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEXCOM_REGION` | Dexcom region: `us` (United States), `ous` (outside US), or `jp` (Japan) | `us` |
| `NIGHTSCOUT_URL` | Your Nightscout URL (e.g., `https://your-site.azurewebsites.net`) | None |
| `NIGHTSCOUT_API_SECRET` | Your Nightscout API secret | None |
| `POLLING_INTERVAL_SECONDS` | Polling interval in seconds (minimum 1) | `60` |

### Setting Environment Variables

**On macOS/Linux:**
```bash
export DEXCOM_USERNAME="your_username"
export DEXCOM_PASSWORD="your_password"
export DEXCOM_REGION="us"
export NIGHTSCOUT_URL="https://your-nightscout-site.com"
export NIGHTSCOUT_API_SECRET="your_api_secret"
export POLLING_INTERVAL_SECONDS="300"
```

**On Windows (PowerShell):**
```powershell
$env:DEXCOM_USERNAME="your_username"
$env:DEXCOM_PASSWORD="your_password"
$env:DEXCOM_REGION="us"
$env:NIGHTSCOUT_URL="https://your-nightscout-site.com"
$env:NIGHTSCOUT_API_SECRET="your_api_secret"
$env:POLLING_INTERVAL_SECONDS="300"
```

## Usage

### Running the Service

```bash
python dexcom_readings.py
```

The service will:
1. Connect to the Dexcom Share API using your credentials
2. Poll for new glucose readings at the configured interval
3. Log readings to `dexcom_readings_log.csv`
4. Upload readings to Nightscout (if configured)

### Graceful Shutdown

The service handles graceful shutdown on `SIGTERM` and `SIGINT` signals
(Ctrl+C). It will complete the current polling cycle before exiting.

### Output

Glucose readings are logged to `dexcom_readings_log.csv` with the following
columns:

| Column | Description |
|--------|-------------|
| `check_timestamp_utc` | Timestamp when the reading was checked |
| `new_reading_received` | Boolean indicating if a new reading was received |
| `glucose_value_mgdl` | Glucose value in mg/dL |
| `glucose_timestamp_utc` | Timestamp of the glucose reading |
| `trend_description` | Trend description (e.g., "Rising", "Flat") |
| `trend_arrow` | Trend arrow symbol (e.g., "↑", "→", "↓↓") |

## Example

```bash
# Set required credentials
export DEXCOM_USERNAME="myuser@example.com"
export DEXCOM_PASSWORD="mypassword"

# Optionally configure Nightscout
export NIGHTSCOUT_URL="https://mynightscout.azurewebsites.net"
export NIGHTSCOUT_API_SECRET="mysecret"

# Poll every 5 minutes
export POLLING_INTERVAL_SECONDS="300"

# Run the service
python dexcom_readings.py
```

## Troubleshooting

### Authentication Errors

- Verify your Dexcom credentials are correct
- Ensure your Dexcom Share account has data sharing enabled
- Check that `DEXCOM_REGION` matches your account region

### Nightscout Upload Issues

- Verify `NIGHTSCOUT_URL` is accessible and correctly formatted
- Check that your API secret is valid
- Both `NIGHTSCOUT_URL` and `NIGHTSCOUT_API_SECRET` must be set for uploads

### No Readings Received

- Check your internet connection
- Verify the polling interval is appropriate (default 60 seconds)
- Review the CSV log for error patterns

## License

Copyright 2026. All rights reserved.

## Dependencies

- [pydexcom](https://github.com/gagebenne/pydexcom) - Dexcom Share API client
- [requests](https://docs.python-requests.org/) - HTTP library