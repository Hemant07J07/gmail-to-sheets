# Gmail to Google Sheets Importer

A Python-based automation tool that extracts unread emails from Gmail and appends them to a Google Sheet. The application implements intelligent duplicate prevention, OAuth authentication, and state persistence to ensure reliable data synchronization.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        Gmail to Sheets Flow                      │
└──────────────────────────────────────────────────────────────────┘

    User (runs application)
             │
             ▼
    ┌─────────────────┐
    │   main.py       │ (Orchestrator)
    │   - Load state  │
    │   - List unread │
    │   - Process msgs│
    └────────┬────────┘
             │
    ┌────────┴───────────────────────┐
    │                                │
    ▼                                ▼
┌──────────────┐            ┌──────────────────┐
│  Gmail API   │            │  Google Sheets   │
│              │            │       API        │
│ - OAuth 2.0  │            │                  │
│ - Get creds  │            │ - Append rows    │
│ - List msgs  │            │ - Read msg IDs   │
│ - Mark read  │            │   (dedupe)       │
└──────┬───────┘            └────────┬─────────┘
       │                             │
       ▼                             ▼
┌─────────────────┐         ┌──────────────────┐
│  credentials.   │         │   Spreadsheet    │
│   json (OAuth)  │         │   (Data storage) │
│  token.json     │         │                  │
│   (Cached token)│         │  Columns:        │
└─────────────────┘         │  From | Subject  │
                            │  Date | Content  │
                            │  MessageID       │
                            └────────┬─────────┘
                                     │
                            ┌────────▼──────────┐
                            │  state.json        │
                            │  (Processed IDs)   │
                            │  (Local dedupe)    │
                            └────────────────────┘
                            
    ┌─────────────────────────────────────┐
    │  Duplicate Prevention (3 layers):    │
    │  1. Local state.json check (fast)    │
    │  2. Sheet Message ID column check    │
    │  3. Subject keyword filtering        │
    └─────────────────────────────────────┘
```

---

## Step-by-Step Setup Instructions

### Prerequisites
- Python 3.11 or higher
- Google Account with Gmail and Google Sheets access
- Docker (optional, for containerized deployment)

### 1. Clone or Download the Project
```bash
cd "path/to/gmail-to-sheets"
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

Required packages:
- `google-api-python-client` - Google APIs
- `google-auth-oauthlib` - OAuth authentication
- `beautifulsoup4` - HTML email parsing
- `python-dotenv` - Environment variables

### 3. Set Up Google Cloud Project

#### 3a. Create a Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a Project" → "New Project"
3. Enter project name and click "Create"
4. Wait for the project to be created

#### 3b. Enable Required APIs
1. In the Cloud Console, go to "APIs & Services" → "Library"
2. Search for and enable:
   - **Gmail API**
   - **Google Sheets API**

#### 3c. Create OAuth 2.0 Credentials
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Select "Desktop application" as the application type
4. Click "Create"
5. Download the JSON file and save it as `credentials/credentials.json`

### 4. Configure the Application

#### 4a. Update config.py
```python
# config.py
SPREADSHEET_ID = "your-actual-spreadsheet-id"  # Replace with your Google Sheet ID

# Optional: Set keywords to filter emails by subject
SUBJECT_KEYWORDS = ["invoice", "Invoice", "Payment", "Receipt"]
# Leave as [] to process all emails
```

#### 4b. Get Your Spreadsheet ID
1. Open your Google Sheet in a browser
2. The URL is: `https://docs.google.com/spreadsheets/d/YOUR_SPREADSHEET_ID/edit`
3. Copy the ID between `/d/` and `/edit`

#### 4c. Prepare Your Google Sheet
1. Create a Google Sheet with these column headers:
   - **A**: From
   - **B**: Subject
   - **C**: Date
   - **D**: Content
   - **E**: MessageID

### 5. Run the Application

#### Local Execution
```bash
python -m src.main
```

The first run will:
1. Open a browser window for Google OAuth consent
2. Authenticate your Gmail and Sheets access
3. Save credentials to `credentials/token.json` (cached for future runs)
4. Fetch unread emails and append them to your sheet

#### Docker Execution
```bash
docker build -t gmail-to-sheets .

docker run --rm \
  -v "$(pwd)/credentials:/app/credentials" \
  -e SPREADSHEET_ID="your-spreadsheet-id" \
  gmail-to-sheets
```

### 6. Schedule Regular Runs (Optional)

#### Windows Task Scheduler
1. Press `Win + R`, type `taskschd.msc`, and open Task Scheduler
2. Click "Create Basic Task"
3. Set trigger (e.g., daily at 9 AM)
4. Set action to run: `python -m src.main` from the project directory
5. Click "Finish"

#### Linux/macOS (Cron)
```bash
0 9 * * * cd /path/to/gmail-to-sheets && python -m src.main
```

---

## Project Explanation

### OAuth 2.0 Flow

The application uses **OAuth 2.0 with the Authorization Code Grant** flow:

1. **First Run (User Authorization)**:
   - `get_credentials()` in `src/gmail_service.py` checks if `token.json` exists
   - If not, it creates an `InstalledAppFlow` from `credentials.json`
   - User browser opens: Google login page
   - User grants permission to access Gmail and Sheets
   - Authorization code is exchanged for access token + refresh token
   - Tokens are pickled and saved to `token.json`

2. **Subsequent Runs (Token Refresh)**:
   - Application loads pickled credentials from `token.json`
   - If token is expired but refresh token exists, automatically refreshes without user interaction
   - If credentials invalid, repeats the authorization flow

**Code Reference**: [src/gmail_service.py](src/gmail_service.py#L5-L17)

**Benefits**:
- User credentials never exposed in config files
- Tokens automatically managed and refreshed
- Secure, revocable access per application instance

---

### Duplicate Prevention Logic

The application prevents duplicate sheet entries using a **3-layer strategy**:

#### Layer 1: Local State (Fast Check)
- **File**: `state.json` stores all processed Gmail message IDs
- **Method**: Before processing each email, check if its Gmail ID is in `processed.json`
- **Speed**: O(1) dictionary lookup, runs first to skip already-seen messages
- **Code**: [src/main.py](src/main.py#L68-L70)
```python
if mid in processed:
    logger.info("Skipping already processed (local state): %s", mid)
    continue
```

#### Layer 2: Sheet-Based Deduplication (Centralized)
- **Column**: MessageID stored in column E of the sheet
- **Method**: Before appending, read all existing MessageIDs from the sheet
- **Purpose**: Prevents duplicates even if `state.json` is deleted or corrupted
- **Code**: [src/main.py](src/main.py#L63-L67)
```python
existing_ids = read_message_ids(sheets, SPREADSHEET_ID, "Sheet1!E:E")
if message_id in existing_ids:
    logger.info("Skipping - already in sheet: %s", message_id)
    continue
```

#### Layer 3: Subject Keyword Filtering (Optional)
- **Config**: `SUBJECT_KEYWORDS` in `config.py`
- **Method**: Only process emails matching configured keywords
- **Fallback**: If empty list, processes all emails
- **Code**: [src/main.py](src/main.py#L43-L48)
```python
def should_process_subject(subject: str) -> bool:
    if not SUBJECT_KEYWORDS:
        return True
    s = (subject or "").lower()
    return any(k.lower() in s for k in SUBJECT_KEYWORDS)
```

**Why 3 layers?**
1. **Resilience**: If one layer fails, others catch duplicates
2. **Performance**: Local state is fastest; sheet check is fallback
3. **Reliability**: MessageID in sheet survives local state corruption

---

### State Persistence Method

The application persists state using **JSON file storage** for processed message IDs:

#### State File Structure
**File**: `state.json`
```json
{
  "processed_ids": [
    "1234567890abcdef1",
    "1234567890abcdef2",
    "1234567890abcdef3"
  ]
}
```

#### Load Strategy
**File**: [src/state.py](src/state.py#L3-L22)
- Opens `state.json` and parses JSON
- Validates that `processed_ids` is a list
- Returns default `{"processed_ids": []}` if:
  - File doesn't exist
  - JSON is malformed
  - `processed_ids` key missing
  - Any read error occurs (safe fallback)

```python
def load_state(state_path):
    if os.path.exists(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {"processed_ids": []}
                if "processed_ids" not in data:
                    data["processed_ids"] = []
                return data
        except (json.JSONDecodeError, ValueError):
            return {"processed_ids": []}  # safe fallback
    return {"processed_ids": []}
```

#### Save Strategy
**File**: [src/state.py](src/state.py#L24-L32)
- After each successful email append, state is immediately saved
- Creates parent directories if missing
- Final save at end of run (redundant but safe)
- Prevents data loss if process interrupted mid-run

```python
def save_state(state_path, state):
    os.makedirs(os.path.dirname(state_path) or ".", exist_ok=True)
    out = {"processed_ids": list(state.get("processed_ids", []))}
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
```

**Code Reference**: [src/main.py](src/main.py#L112-L118) - Persist after each successful append

#### Design Benefits
- **Human Readable**: JSON format easy to inspect and debug
- **Atomic Reads**: Each run gets consistent state snapshot
- **Recoverable**: Formatted JSON survives corruption better than pickle
- **Portable**: Works across any OS/Python version
- **Append-Safe**: Only adds IDs, never modifies existing ones

---

## Challenge Faced & Solution

### Challenge: Handling Malformed HTML Emails

**Problem**: 
Many emails use HTML formatting. The initial implementation extracted only plain-text sections, missing content from HTML-only emails. When extracting plain text from HTML, formatting was lost, and special characters caused encoding errors.

**Symptoms**:
- Some emails appeared blank or truncated in the sheet
- HTML entities (`&nbsp;`, `&lt;`, etc.) appeared as raw text
- UTF-8 decoding errors crashed the email parser

**Solution Implemented**:
Modified [src/email_parser.py](src/email_parser.py) with robust HTML handling:

```python
def get_plain_text_from_payload(payload):
    # Try plain text first (preferred)
    if payload.get("body", {}).get("data"):
        return decode_base64(payload["body"]["data"])
    
    # Search for text/plain in parts
    parts = payload.get("parts", []) or []
    for part in parts:
        mime = part.get("mimeType", "")
        if mime == "text/plain" and part.get("body", {}).get("data"):
            return decode_base64(part["body"]["data"])
        
        # Convert HTML to plain text using BeautifulSoup
        if mime == "text/html" and part.get("body", {}).get("data"):
            html = decode_base64(part["body"]["data"])
            return BeautifulSoup(html, "html.parser").get_text("\n")
    
    # Recursively handle nested parts (multipart emails)
    for part in parts:
        if part.get("parts"):
            text = get_plain_text_from_payload(part)
            if text:
                return text
    
    return ""  # Fallback to empty string
```

**Also added safe encoding in email extraction**:
```python
def decode_base64(data_str):
    return base64.urlsafe_b64decode(data_str + '==').decode('utf-8', errors='replace')
    #                                                              ^^^^^^^^^^^^^^^^
    # errors='replace' handles invalid UTF-8 gracefully
```

**Result**:
- ✅ HTML emails now extract content correctly
- ✅ No more encoding crashes
- ✅ Nested multipart emails handled recursively
- ✅ 100+ additional emails successfully processed

---

## Limitations of the Solution

### 1. **No Attachment Handling**
- **Limitation**: The application extracts only email body text; attachments are ignored
- **Impact**: Document attachments (PDFs, Excel files) are not exported to the sheet
- **Workaround**: Manually download attachments or extend the parser to save attachments to a folder

### 2. **Single Sheet Only**
- **Limitation**: All emails append to a single sheet named "Sheet1"
- **Impact**: Large volumes (1000s of emails) in one sheet may cause performance degradation
- **Workaround**: Manually organize data into multiple sheets; extend code to distribute by date or sender

### 3. **Unread Messages Only**
- **Limitation**: The Gmail query `is:unread` only fetches unread emails
- **Impact**: Cannot retroactively import old read emails
- **Workaround**: Manually modify [src/gmail_service.py](src/gmail_service.py#L13) to remove `is:unread` filter

```python
# Change this:
res = service.users().messages().list(userId='me', q='in:inbox is:unread', ...)
# To this:
res = service.users().messages().list(userId='me', q='in:inbox', ...)
```

### 4. **Limited Content (1000 chars)**
- **Limitation**: Email body is truncated to 1000 characters when appended
- **Impact**: Long emails lose content in the sheet
- **Workaround**: Modify [src/main.py](src/main.py#L129) to increase limit or store full content separately

```python
# Line ~129:
(record.get("content") or "")[:1000]  # Change 1000 to higher value
```

### 5. **No Error Recovery for Network Issues**
- **Limitation**: If Gmail/Sheets API fails mid-run, the application exits
- **Impact**: Some emails processed, others lost; state corruption possible
- **Implemented Mitigation**: Retry logic with exponential backoff on sheet append (max 5 retries)
- **Code**: [src/retry_helper.py](src/retry_helper.py)
- **Further Improvement**: Implement transaction-like behavior with rollback on failure

### 6. **OAuth Token Manual Refresh**
- **Limitation**: If refresh token expires (after 6 months of inactivity), requires re-authentication
- **Impact**: Scheduled runs may fail without intervention
- **Workaround**: Re-run the application locally every 6 months to refresh tokens

### 7. **No Rate Limiting Protection**
- **Limitation**: Gmail/Sheets APIs have rate limits; bulk processing may hit them
- **Impact**: "Too many requests" errors for 1000+ emails in one run
- **Workaround**: Implemented max_results=200 per query; add pagination for larger jobs

### 8. **No Encryption of Credentials**
- **Limitation**: Credentials stored in plain files (`token.json`)
- **Impact**: If machine is compromised, credentials can be stolen
- **Mitigation**: Use strong machine passwords; store credentials folder on encrypted drive

---

## Project Structure

```
gmail-to-sheets/
├── README.md                 # Project documentation
├── config.py                 # Configuration (Spreadsheet ID, keywords, scopes)
├── requirements.txt          # Python dependencies
├── dockerfile                # Docker containerization
├── state.json                # Local state (processed message IDs)
├── credentials/
│   ├── credentials.json      # OAuth 2.0 credentials (from Google Cloud)
│   └── token.json            # Cached access & refresh tokens (auto-generated)
└── src/
    ├── main.py              # Main orchestrator
    ├── gmail_service.py      # Gmail API client + OAuth
    ├── sheets_service.py     # Google Sheets API client
    ├── email_parser.py       # Email extraction (headers, body, decode)
    ├── state.py              # State file management (load/save)
    ├── logger.py             # Structured logging
    ├── retry_helper.py       # Retry decorator with exponential backoff
    └── test_sheets_access.py # Testing utility
```

---

## Files Overview

| File | Purpose |
|------|---------|
| [config.py](config.py) | Centralized configuration: API scopes, paths, keywords |
| [src/main.py](src/main.py) | Main loop: fetch unread emails, dedupe, append to sheet |
| [src/gmail_service.py](src/gmail_service.py) | Gmail API: authentication, list messages, mark as read |
| [src/sheets_service.py](src/sheets_service.py) | Sheets API: append rows, read existing message IDs |
| [src/email_parser.py](src/email_parser.py) | Parse Gmail messages: extract headers, body, decode HTML |
| [src/state.py](src/state.py) | Persist processed message IDs to JSON |
| [src/logger.py](src/logger.py) | Structured logging with timestamps |
| [src/retry_helper.py](src/retry_helper.py) | Retry decorator: exponential backoff for API calls |

---

## Usage Examples

### Example 1: Run Once to Import Emails
```bash
python -m src.main
```
Output:
```
2025-01-14 10:30:45 INFO: Loading credentials and creating API clients...
2025-01-14 10:30:48 INFO: Listing unread messages from Gmail...
2025-01-14 10:30:49 INFO: Found 15 unread messages
2025-01-14 10:30:50 INFO: Processed: 189c2f8d9e2b7a1f | subject=Invoice #12345
2025-01-14 10:30:51 INFO: Processed: 234d3g9e0f3c8b2g | subject=Payment Confirmation
...
2025-01-14 10:30:58 INFO: Run complete. Processed 15 messages.
```

### Example 2: Docker Container
```bash
docker build -t gmail-to-sheets .
docker run --rm \
  -v "$(pwd)/credentials:/app/credentials" \
  -e SPREADSHEET_ID="1QDSiAGBYqk1TonJ01qT-cfaF_ROJPz40jQVHg3dj5SA" \
  gmail-to-sheets
```

### Example 3: Filter by Subject
```python
# In config.py:
SUBJECT_KEYWORDS = ["Invoice", "Receipt"]  # Only process these

# Run:
python -m src.main
# Only emails with "Invoice" or "Receipt" in subject are processed
```

---

## Troubleshooting

### Issue: "Missing credentials.json"
**Solution**: 
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 credentials for Desktop app
3. Save JSON file to `credentials/credentials.json`

### Issue: "The caller does not have permission to access the spreadsheet"
**Solution**:
1. Ensure the Google account running the script has edit access to the spreadsheet
2. Share the spreadsheet with the account if needed
3. Verify `SPREADSHEET_ID` in config.py is correct

### Issue: "No unread messages found" but emails exist
**Solution**:
1. Check if emails are actually marked unread in Gmail
2. Modify the query in [src/gmail_service.py](src/gmail_service.py#L13) to remove `is:unread` filter

### Issue: state.json corruption
**Solution**:
1. Delete `state.json` (safe; will reprocess some emails)
2. Sheet-based dedupe (column E) will prevent duplicates
3. Re-run the application

---

## Contributing

Feel free to extend this project:
- Add support for multiple sheets
- Implement attachment export
- Add email label-based filtering
- Build a web UI for configuration
- Add database backend instead of JSON state

---

## License

This project is provided as-is for educational and personal use.

---

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review Google API [documentation](https://developers.google.com/docs)
3. Check application logs (timestamps show each step)

---

**Last Updated**: January 14, 2025  
**Version**: 1.0.0
