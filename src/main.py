# src/main.py
import os, sys
from config import CREDENTIALS_PATH, TOKEN_PATH, SCOPES, SPREADSHEET_ID, STATE_PATH
from src.gmail_service import get_credentials, get_gmail_service, list_unread_messages, get_message, mark_as_read
from src.sheets_service import get_sheets_service, append_row
from src.email_parser import parse_message
from src.state import load_state, save_state

def main():
    if not os.path.exists(CREDENTIALS_PATH):
        print("Missing credentials.json at:", CREDENTIALS_PATH)
        sys.exit(1)
    creds = get_credentials(CREDENTIALS_PATH, TOKEN_PATH, SCOPES)
    gmail = get_gmail_service(creds)
    sheets = get_sheets_service(creds)

    state = load_state(STATE_PATH)
    processed = set(state.get("processed_ids", []))

    msgs = list_unread_messages(gmail, max_results=200)
    if not msgs:
        print("No unread messages found.")
        return

    for m in msgs:
        mid = m["id"]
        if mid in processed:
            print("Skipping already processed:", mid)
            continue
        full_msg = get_message(gmail, mid)
        record = parse_message(full_msg)
        # Row structure: From, Subject, Date, Content, MessageID
        row = [record["from"], record["subject"], record["date"], record["content"][:1000], record["message_id"]]
        # Append to sheet (Sheet1!A:E) - adjust if needed
        append_row(sheets, SPREADSHEET_ID, "Sheet1!A:E", row)
        mark_as_read(gmail, mid)
        processed.add(mid)
        print("Processed:", mid, record["subject"])

    state["processed_ids"] = list(processed)
    save_state(STATE_PATH, state)
    print("Done.")

if __name__ == "__main__":
    main()
