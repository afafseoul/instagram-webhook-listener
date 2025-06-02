
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def fetch_page_ids():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('/etc/secrets/credentials.json', scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/11H74lWqyPPc0SPVOcX0x1iN97x8qJw6c7y8-WFeWijY/edit").sheet1
    data = sheet.get_all_records()

    return [
        {
            "page_id": row["ID Page Facebook"],
            "instagram_id": row["ID Compte Instagram"],
            "client": row["Nom client"],
            "active": row["Statut"].strip().lower() == "active"
        }
        for row in data if row["Statut"].strip().lower() == "active"
    ]
