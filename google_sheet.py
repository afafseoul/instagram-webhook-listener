"""Utility functions to retrieve active Facebook page IDs from Google Sheets."""

from typing import List

import gspread
from oauth2client.service_account import ServiceAccountCredentials


GOOGLE_CREDENTIALS_PATH = "/etc/secrets/credentials.json"
SHEET_NAME = "Client_pages_IDRender"
WORKSHEET_NAME = "Feuille 2"


def _get_worksheet():
    """Authenticate and return the configured worksheet."""
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
    return client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)


def get_active_pages() -> List[str]:
    """Return the list of active Facebook page IDs from the sheet."""
    sheet = _get_worksheet()
    page_ids = sheet.col_values(1)
    statuses = sheet.col_values(4)

    active_pages: List[str] = []
    for page_id, status in zip(page_ids[1:], statuses[1:]):
        page_id = str(page_id).strip()
        status = str(status).strip()
        if page_id and status == "✅":
            active_pages.append(page_id)

    return active_pages

