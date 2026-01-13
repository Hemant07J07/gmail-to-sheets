# config.py
import os

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1QDSiAGBYqk1TonJ01qT-cfaF_ROJPz40jQVHg3dj5SA") # Replace with your actual Spreadsheet ID
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "credentials", "credentials.json") # Path to your credentials file
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "credentials", "token.json") # Path to your token file
STATE_PATH = os.path.join(os.path.dirname(__file__), "state.json") # Path to your state file
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify", # Gmail API scope
    "https://www.googleapis.com/auth/spreadsheets" # Google Sheets API scope
]
