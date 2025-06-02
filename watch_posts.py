import time
import threading
import requests
from google_sheet import get_active_pages

WEBHOOK_URL_POSTS = "https://hook.us1.make.com/ton_webhook_posts"  # remplace avec ton vrai lien Make.com

def check_new_posts():
    pages = get_active_pages()
    for page in pages:
        # ⚠️ Cette structure est un exemple : à toi de modifier selon ton vrai check
        print(f"🔍 Vérification des nouveaux posts pour {page['client_name']} ({page['page_id']})...")
        data = {
            "page_id": page["page_id"],
            "instagram_id": page["instagram_id"],
            "client_name": page["client_name"]
        }
        try:
            response = requests.post(WEBHOOK_URL_POSTS, json=data)
            if response.status_code == 200:
                print(f"📤 Webhook envoyé pour {page['client_name']}")
            else:
                print(f"⚠️ Erreur Webhook : {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Exception Webhook pour {page['client_name']}: {e}")

def watch_new_posts():
    print("🟢 Thread watch_posts lancé")
    while True:
        check_new_posts()
        time.sleep(60)  # toutes les 60 secondes
