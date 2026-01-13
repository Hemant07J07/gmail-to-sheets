# src/sheets_service.py
from googleapiclient.discovery import build

def get_sheets_service(creds):
    return build("sheets", "v4", credentials=creds)

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
