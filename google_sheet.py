SHEET_URL = "https://docs.google.com/spreadsheets/d/11H74lWqyPPc0SPVOcX0x1iN97x8qJw6c7y8-WFeWijY/edit"

import gspread
from oauth2client.service_account import ServiceAccountCredentials

def fetch_page_ids():
    print("📄 Lecture Google Sheet...")
    try:
        gc = gspread.service_account(filename='/etc/secrets/credentials.json')
        sh = gc.open_by_url(SHEET_URL)
        worksheet = sh.sheet1
        rows = worksheet.get_all_values()
        print(f"📄 Sheet récupérée : {len(rows)} lignes")
        page_ids = []
        for row in rows[1:]:  # skip header
            if len(row) >= 4 and row[3].strip().lower() == "active":
                print(f"✅ Page active trouvée : {row[0]} / {row[1]}")
                page_ids.append({
                    "page_id": row[0],
                    "instagram_id": row[1],
                    "client_name": row[2]
                })
        print(f"✅ Total pages actives : {len(page_ids)}")
        return page_ids
    except Exception as e:
        print(f"❌ Erreur lecture Google Sheet: {e}")
        return []
