# External Integrations

**Analysis Date:** 2026-04-19

## APIs & External Services

**Dexcom Share API:**
- Purpose: Fetch real-time glucose readings from Dexcom CGM
- SDK/Client: `pydexcom` library (`from pydexcom import Dexcom`)
- Auth: Username/password authentication
- Environment vars: `DEXCOM_USERNAME`, `DEXCOM_PASSWORD`, `DEXCOM_REGION`
- Regions supported: "us" (default), "ous" (outside US), "jp" (Japan)
- Implementation: `dexcom_readings.py` lines 40-60

**Nightscout API:**
- Purpose: Upload glucose readings to Nightscout diabetes management platform
- SDK/Client: `requests` library (HTTP client)
- Auth: API secret via HTTP header
- Environment vars: `NIGHTSCOUT_URL`, `NIGHTSCOUT_API_SECRET`
- Endpoint: `{NIGHTSCOUT_URL}/api/v1/entries` (POST)
- Payload: JSON array with `dateString`, `sgv`, `direction`, `type` fields
- Implementation: `dexcom_readings.py` lines 82-116

## Data Storage

**Databases:**
- None (no database integration)

**File Storage:**
- Local filesystem only
- CSV file: `dexcom_readings_log.csv`
- Headers: `check_timestamp_utc`, `new_reading_received`, `glucose_value_mgdl`, `glucose_timestamp_utc`, `trend_description`, `trend_arrow`
- Implementation: `dexcom_readings.py` lines 73-80

**Caching:**
- In-memory only: `last_known_glucose_timestamp` global variable for deduplication
- No persistent cache

## Authentication & Identity

**Dexcom Auth:**
- Provider: Dexcom Share service
- Implementation: `pydexcom.Dexcom(username, password)` client initialization
- Credentials sourced from environment variables at runtime
- Region-aware authentication (US vs OUS vs JP)

**Nightscout Auth:**
- Provider: Self-hosted Nightscout instance
- Implementation: API secret passed in `api-secret` HTTP header
- Plain secret (not hashed) in requests
- Credentials sourced from environment variables

## Monitoring & Observability

**Error Tracking:**
- None (no external error tracking service)

**Logs:**
- Python `logging` module with INFO level
- Format: `%(asctime)s - %(levelname)s - %(message)s`
- Console output only (no log file or external service)
- Implementation: `dexcom_readings.py` lines 31-33

## CI/CD & Deployment

**Hosting:**
- Not specified (local script designed for continuous execution)

**CI Pipeline:**
- None detected (no `.github` directory)

**Deployment:**
- Manual execution: `python dexcom_readings.py`
- Continuous polling loop with 60-second intervals

## Environment Configuration

**Required env vars:**
- `DEXCOM_USERNAME` - Dexcom Share account username
- `DEXCOM_PASSWORD` - Dexcom Share account password

**Optional env vars:**
- `DEXCOM_REGION` - Region code ("us", "ous", "jp"), defaults to "us"
- `NIGHTSCOUT_URL` - Nightscout instance URL (skipped if not set)
- `NIGHTSCOUT_API_SECRET` - Nightscout API secret (skipped if not set)

**Secrets location:**
- Environment variables only
- No `.env` file detected in repository
- No secrets management integration

## Webhooks & Callbacks

**Incoming:**
- None (polling-based architecture)

**Outgoing:**
- Nightscout POST requests to `/api/v1/entries` endpoint

## Data Flow Summary

```
Dexcom Share API --(pydexcom)--> dexcom_readings.py --(requests)--> Nightscout API
                                        |
                                        v
                                dexcom_readings_log.csv (local file)
```

**Polling Cycle:**
1. Script starts, initializes Dexcom client
2. Every 60 seconds: fetch latest glucose reading from Dexcom
3. If new reading: log to CSV, upload to Nightscout
4. If no new reading: log check timestamp only

---

*Integration audit: 2026-04-19*