# src/main.py
import os
import sys
from config import CREDENTIALS_PATH, TOKEN_PATH, SCOPES, SPREADSHEET_ID, STATE_PATH

# Optional subject keywords (config may or may not define this)
try:
    from config import SUBJECT_KEYWORDS
except Exception:
    SUBJECT_KEYWORDS = []

# Gmail & Sheets helpers
from src.gmail_service import get_credentials, get_gmail_service, list_unread_messages, get_message, mark_as_read
from src.sheets_service import get_sheets_service, append_row

# Try to import read_message_ids (centralized dedupe). If missing, provide a safe stub.
try:
    from src.sheets_service import read_message_ids
except Exception:
    def read_message_ids(service, spreadsheet_id, range_name="Sheet1!E:E"):
        # If not implemented, return empty set (we'll fall back to local state.json dedupe)
        return set()

from src.email_parser import parse_message
from src.state import load_state, save_state

# Structured logger (expects src/logger.py). If missing, fallback to simple logger.
try:
    from src.logger import get_logger
    logger = get_logger(__name__)
except Exception:
    import datetime
    class SimpleLogger:
        def _log(self, level, *args):
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{ts} {level}:", *args)
        def info(self, *a): self._log("INFO", *a)
        def warning(self, *a): self._log("WARN", *a)
        def error(self, *a): self._log("ERROR", *a)
    logger = SimpleLogger()

def should_process_subject(subject: str) -> bool:
    """
    Return True if the subject passes the SUBJECT_KEYWORDS filter.
    If SUBJECT_KEYWORDS is empty, allow all subjects.
    """
    if not SUBJECT_KEYWORDS:
        return True
    s = (subject or "").lower()
    return any(k.lower() in s for k in SUBJECT_KEYWORDS)

def main():
    if not os.path.exists(CREDENTIALS_PATH):
        logger.error("Missing credentials.json at: %s", CREDENTIALS_PATH)
        sys.exit(1)

    logger.info("Loading credentials and creating API clients...")
    creds = get_credentials(CREDENTIALS_PATH, TOKEN_PATH, SCOPES)
    gmail = get_gmail_service(creds)
    sheets = get_sheets_service(creds)

    # Load local state (processed IDs)
    state = load_state(STATE_PATH) or {"processed_ids": []}
    processed = set(state.get("processed_ids", []))

    # Try to get message IDs already in the sheet for centralized dedupe
    try:
        existing_ids = read_message_ids(sheets, SPREADSHEET_ID, "Sheet1!E:E") or set()
        logger.info("Loaded %d message IDs from sheet for centralized dedupe", len(existing_ids))
    except Exception as e:
        logger.warning("Could not read existing message IDs from sheet (will use local state only): %s", e)
        existing_ids = set()

    logger.info("Listing unread messages from Gmail...")
    msgs = list_unread_messages(gmail, max_results=200)
    if not msgs:
        logger.info("No unread messages found.")
        return

    logger.info("Found %d unread messages", len(msgs))

    # Process messages one-by-one
    for m in msgs:
        mid = m.get("id")
        if not mid:
            logger.warning("Skipping message with no id: %s", m)
            continue

        # Skip based on local state (fast)
        if mid in processed:
            logger.info("Skipping already processed (local state): %s", mid)
            continue

        # Fetch full message
        try:
            full_msg = get_message(gmail, mid)
        except Exception as e:
            logger.error("Failed to fetch message %s: %s", mid, e)
            continue

        record = parse_message(full_msg)
        message_id = record.get("message_id") or mid  # fallback
        subject = record.get("subject", "")

        # Subject-based filtering
        if not should_process_subject(subject):
            logger.info("Skipping (subject filter): %s | message_id=%s", subject, message_id)
            # If you want filtered messages marked read too, uncomment the following:
            # try: mark_as_read(gmail, mid)
            # except Exception as e: logger.warning("Failed to mark filtered email as read: %s", e)
            continue

        # --- centralized dedupe check (exact snippet you requested) ---
        if message_id in existing_ids:
            logger.info("Skipping - already in sheet: %s", message_id)
            # mark as read or skip marking depending on design
            try:
                mark_as_read(gmail, mid)
            except Exception as e:
                logger.warning("Failed to mark-as-read for %s: %s", mid, e)
            # ensure local state also knows this message was observed
            processed.add(mid)
            continue
        # -----------------------------------------------------------------

        # Prepare row: From, Subject, Date, Body (trimmed), MessageID
        row = [
            record.get("from", ""),
            record.get("subject", ""),
            record.get("date", ""),
            (record.get("content") or "")[:1000],
            message_id
        ]

        # Append row to sheet, mark read, update state
        try:
            append_row(sheets, SPREADSHEET_ID, "Sheet1!A:E", row)
            try:
                mark_as_read(gmail, mid)
            except Exception as e:
                logger.warning("Appended but failed to mark message read %s: %s", mid, e)
            processed.add(mid)
            existing_ids.add(message_id)  # avoid re-appending within this run
            logger.info("Processed: %s  |  subject=%s", mid, subject)
            # Persist state after each successful append to avoid data loss mid-run
            state["processed_ids"] = list(processed)
            try:
                save_state(STATE_PATH, state)
            except Exception as e:
                logger.warning("Failed to save state after processing %s: %s", mid, e)
        except Exception as e:
            logger.error("Failed to append message %s to sheet: %s", mid, e)
            # don't mark as read or add to processed if append failed

    # final save (redundant but safe)
    state["processed_ids"] = list(processed)
    try:
        save_state(STATE_PATH, state)
    except Exception as e:
        logger.warning("Final save_state failed: %s", e)

    logger.info("Run complete. Processed %d messages (total local processed ids: %d).", len(processed), len(state.get("processed_ids", [])))

if __name__ == "__main__":
    main()
