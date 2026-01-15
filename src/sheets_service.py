# src/sheets_service.py
from googleapiclient.discovery import build
from src.retry_helper import retry

def get_sheets_service(creds):
    return build("sheets", "v4", credentials=creds)

@retry(max_attempts=5, initial_delay=1, backoff=2, allowed_exceptions=(Exception,))
def append_row(service, spreadsheet_id, range_name, row_values):
    body = {"values": [row_values]}
    return service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()

def read_column(service, spreadsheet_id, range_name):
    res = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    return res.get("values", [])

def read_message_ids(service, spreadsheet_id, range_name="Sheet1!E:E"):
    res = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    vals = res.get("values", [])

    # Flatten and return set
    return set(v[0] for v in vals if v and v[0])