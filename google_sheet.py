import gspread
from oauth2client.service_account import ServiceAccountCredentials

def fetch_page_ids():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('/etc/secrets/credentials.json', scope)
        client = gspread.authorize(creds)

        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/11H74lWqyPPc0SPVOcX0x1iN97x8qJw6c7y8-WFeWijY/edit").sheet1
        data = sheet.get_all_records()

        return [
            {
                "page_id": row.get("ID Page Facebook"),
                "instagram_id": row.get("ID Compte Instagram"),
                "client": row.get("Nom client"),
                "active": str(row.get("Statut", "")).strip().lower() == "active"
            }
            for row in data if str(row.get("Statut", "")).strip().lower() == "active"
        ]
    except Exception as e:
        print("❌ Erreur lecture Google Sheet:", e)
        return []
