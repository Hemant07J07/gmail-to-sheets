# src/gmail_service.py
import os, pickle, json, base64
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

def get_credentials(creds_path, token_path, scopes):
    creds = None
    if os.path.exists(token_path):
        with open(token_path, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, scopes)
            creds = flow.run_local_server(port=0)
        with open(token_path, "wb") as f:
            pickle.dump(creds, f)
    return creds

def get_gmail_service(creds):
    return build("gmail", "v1", credentials=creds)

def list_unread_messages(service, max_results=100):
    res = service.users().messages().list(userId='me', q='in:inbox is:unread', maxResults=max_results).execute()
    return res.get("messages", [])

def get_message(service, msg_id):
    return service.users().messages().get(userId='me', id=msg_id, format='full').execute()

def mark_as_read(service, msg_id):
    body = {'removeLabelIds': ['UNREAD']}
    return service.users().messages().modify(userId='me', id=msg_id, body=body).execute()
