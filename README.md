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

## Daemon Deployment

The service can be deployed as a system daemon for continuous, unattended operation.

### Environment Variables for Daemon Mode

| Variable | Description | Default |
|----------|-------------|---------|
| `DEXCOM_LOG_DESTINATION` | Logging destination: `console`, `file`, or `syslog` | `console` |
| `DEXCOM_LOG_LEVEL` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |
| `DEXCOM_LOG_FILE` | Path to log file (when `DEXCOM_LOG_DESTINATION=file`) | `~/.local/state/dexcom-readings/dexcom-readings.log` |
| `DEXCOM_CSV_PATH` | Path to CSV data file | `~/.local/share/dexcom-readings/readings.csv` |
| `DEXCOM_PID_FILE` | Path to PID file for single-instance locking | `~/.local/state/dexcom-readings/dexcom-readings.pid` |

### Linux (systemd)

1. Copy the service template:
   ```bash
   sudo cp service/dexcom-readings.service /etc/systemd/system/
   ```

2. Create the environment file `/etc/default/dexcom-readings`:
   ```bash
   DEXCOM_USERNAME="your_username"
   DEXCOM_PASSWORD="your_password"
   DEXCOM_REGION="us"
   NIGHTSCOUT_URL="https://your-nightscout.example.com"
   NIGHTSCOUT_API_SECRET="your_secret"
   DEXCOM_LOG_DESTINATION="file"
   DEXCOM_LOG_FILE="/var/log/dexcom-readings/dexcom-readings.log"
   ```

3. Create user and directories:
   ```bash
   sudo useradd -r -s /bin/false dexcom
   sudo mkdir -p /opt/dexcom-readings /var/lib/dexcom-readings /var/log/dexcom-readings
   sudo chown dexcom:dexcom /var/lib/dexcom-readings /var/log/dexcom-readings
   ```

4. Install the application:
   ```bash
   # Copy files to /opt/dexcom-readings/
   cd /opt/dexcom-readings
   python3 -m venv venv
   ./venv/bin/pip install -r requirements.txt
   ```

5. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable dexcom-readings
   sudo systemctl start dexcom-readings
   ```

6. View logs:
   ```bash
   journalctl -u dexcom-readings -f
   ```

### macOS (launchd)

1. Copy the plist template:
   ```bash
   cp service/com.dexcom.readings.plist ~/Library/LaunchAgents/
   ```

2. Edit the plist to set your credentials and paths (see comments in the file).

3. Create the installation directory:
   ```bash
   mkdir -p /opt/dexcom-readings
   cd /opt/dexcom-readings
   python3 -m venv venv
   ./venv/bin/pip install -r requirements.txt
   # Copy dexcom_readings.py to this directory
   ```

4. Load the service:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.dexcom.readings.plist
   ```

5. Check status:
   ```bash
   launchctl list | grep dexcom
   ```

### Log Rotation

For file-based logging, use external log rotation tools:

**Linux (logrotate):**
Create `/etc/logrotate.d/dexcom-readings`:
```
/var/log/dexcom-readings/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    postrotate
        systemctl kill -s HUP dexcom-readings.service
    endscript
}
```

The `SIGHUP` signal triggers the daemon to reopen the log file after rotation.

## License

Copyright 2026. All rights reserved.

## Dependencies

- [pydexcom](https://github.com/gagebenne/pydexcom) - Dexcom Share API client
- [requests](https://docs.python-requests.org/) - HTTP library