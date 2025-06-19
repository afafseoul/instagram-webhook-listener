from typing import List
import gspread
from oauth2client.service_account import ServiceAccountCredentials

GOOGLE_CREDENTIALS_PATH = "/etc/secrets/credentials.json"
SHEET_NAME = "Commanda - Clients actifs"
COLUMN_INDEX = 3  # Column C


def _get_sheet():
    """Authenticate and return the first worksheet of the spreadsheet."""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        GOOGLE_CREDENTIALS_PATH, scope
    )
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1


def get_instagram_ids() -> List[str]:
    """Return Instagram Business IDs from column C of the Google Sheet."""
    sheet = _get_sheet()
    raw_values = sheet.col_values(COLUMN_INDEX)
    ids: List[str] = []
    for value in raw_values:
        value = value.strip()
        if not value or value.lower().startswith("instagram"):
            continue
        ids.append(value)
    return ids
