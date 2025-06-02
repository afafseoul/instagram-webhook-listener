import requests
import threading
import time
import os
from google_sheet import get_active_pages

ACCESS_TOKEN = os.getenv("META_SYSTEM_TOKEN")
WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_POST")

def check_posts(page_id):
    url = f"https://graph.facebook.com/v19.0/{page_id}/feed?fields=id,message,created_time&access_token={ACCESS_TOKEN}"
    try:
        response = requests.get(url)
        data = response.json()

        # 🧠 Ici tu peux ajouter une logique pour filtrer les nouveaux posts uniquement
        print(f"[{page_id}] ✅ Posts récupérés :", data)

        # Envoi à Make si des données existent
        if "data" in data and data["data"]:
            requests.post(WEBHOOK_URL, json={"page_id": page_id, "posts": data["data"]})
    except Exception as e:
        print(f"[{page_id}] ❌ Erreur récupération posts :", e)

def start():
    print("📄 Lecture Google Sheet des pages actives (posts)...")
    while True:
        try:
            pages = get_active_pages()
            for page_id in pages:
                threading.Thread(target=check_posts, args=(page_id,)).start()
            time.sleep(60)  # relance toutes les 60 secondes
        except Exception as e:
            print("❌ Erreur dans la boucle posts :", e)
            time.sleep(60)
