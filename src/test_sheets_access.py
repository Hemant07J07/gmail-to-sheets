# src/test_sheets_access.py
import os, sys
from config import CREDENTIALS_PATH, TOKEN_PATH, SCOPES, SPREADSHEET_ID
from src.gmail_service import get_credentials  # re-uses credentials flow
from src.sheets_service import get_sheets_service
from googleapiclient.errors import HttpError

def run_test():
    if not os.path.exists(CREDENTIALS_PATH):
        print("Missing credentials.json at:", CREDENTIALS_PATH); return
    if not SPREADSHEET_ID or "yourSheetId" in SPREADSHEET_ID:
        print("SPREADSHEET_ID looks wrong. Check config.py or env var."); return

    creds = get_credentials(CREDENTIALS_PATH, TOKEN_PATH, SCOPES)
    sheets = get_sheets_service(creds)
    try:
        meta = sheets.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        title = meta.get("properties", {}).get("title", "<no title>")
        sheets_list = [s.get("properties", {}).get("title") for s in meta.get("sheets", [])]
        print("Spreadsheet found. Title:", title)
        print("Tabs:", sheets_list)
    except HttpError as e:
        status = e.resp.status
        print(f"HTTP Error {status}: {e}")
        if status == 404:
            print(" -> 404: wrong spreadsheet ID or spreadsheet does not exist.")
        elif status == 403:
            print(" -> 403: authenticated account doesn't have permission to access this sheet.")
        else:
            print(" -> See full error above.")

if __name__ == "__main__":
    run_test()
