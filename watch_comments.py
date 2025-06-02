# watch_comments.py

import requests
import time
from google_sheet import fetch_page_ids

WEBHOOK_COMMENTS_URL = "https://hook.eu1.make.com/..."  # ton vrai lien Make ici

def watch_new_comments():
    print("🌀 Lancement de la boucle de surveillance des commentaires...")
    while True:
        try:
            pages = fetch_page_ids()
            for page in pages:
                print(f"📩 Check commentaires pour {page['client_name']}")

                requests.post(WEBHOOK_COMMENTS_URL, json={
                    "instagram_id": page["instagram_id"],
                    "page_id": page["page_id"],
                    "client": page["client_name"],
                    "type": "new_comment"
                })

            time.sleep(120)
        except Exception as e:
            print(f"❌ Erreur dans watch_new_comments : {e}")
            time.sleep(60)
