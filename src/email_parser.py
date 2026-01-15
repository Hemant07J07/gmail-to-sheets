# src/email_parser.py
import base64
from bs4 import BeautifulSoup
from datetime import datetime
import re

def decode_base64(data_str):
    return base64.urlsafe_b64decode(data_str + '==').decode('utf-8', errors='replace')

def extract_headers(headers, name):
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""

def get_plain_text_from_payload(payload):
    # If body in payload
    if payload.get("body", {}).get("data"):
        return decode_base64(payload["body"]["data"])
    # If parts exist, search for text/plain
    parts = payload.get("parts", []) or []
    for part in parts:
        mime = part.get("mimeType", "")
        if mime == "text/plain" and part.get("body", {}).get("data"):
            return decode_base64(part["body"]["data"])
        if mime == "text/html" and part.get("body", {}).get("data"):
            html = decode_base64(part["body"]["data"])
            return BeautifulSoup(html, "html.parser").get_text("\n")
        # nested parts
        if part.get("parts"):
            text = get_plain_text_from_payload(part)
            if text:
                return text
    return ""

def parse_message(gmail_message):
    msg_id = gmail_message.get("id")
    headers = gmail_message.get("payload", {}).get("headers", [])
    sender = extract_headers(headers, "From")
    subject = extract_headers(headers, "Subject")
    date_raw = extract_headers(headers, "Date")
    # Try internalDate if header missing
    try:
        internal_ts = int(gmail_message.get("internalDate"))/1000.0
        date_iso = datetime.utcfromtimestamp(internal_ts).isoformat() + "Z"
    except:
        date_iso = date_raw

    content = get_plain_text_from_payload(gmail_message.get("payload", {})) or ""
    return {
        "message_id": msg_id,
        "from": sender,
        "subject": subject,
        "date": date_iso,
        "content": content.strip()
    }

def html_to_text(html):
    # BeautifulSoup to strip tags then collapse whitespace
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")

    # Collapse excessive newlines & whitespace
    text = re.sub(r'\n\s*\n+', '\n\n', text).strip()
    return text