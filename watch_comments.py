import requests
import threading
import time
import os
from google_sheet import get_active_pages

ACCESS_TOKEN = os.getenv("META_SYSTEM_TOKEN")
WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_COMMENT")

def check_comments(page_id):
    url = f"https://graph.facebook.com/v19.0/{page_id}/feed?fields=comments{{id,message,from}}&access_token={ACCESS_TOKEN}"
    try:
        response = requests.get(url)
        data = response.json()
        # 🧠 ici tu dois filtrer les nouveaux commentaires si tu veux éviter les doublons
        print(f"[{page_id}] ✅ Commentaires reçus :", data)
        requests.post(WEBHOOK_URL, json=data)  # envoyer à Make
    except Exception as e:
        print(f"[{page_id}] ❌ Erreur récupération commentaires :", e)

def start():
    print("📄 Lecture Google Sheet...")
    while True:
        try:
            pages = get_active_pages()
            for page_id in pages:
                threading.Thread(target=check_comments, args=(page_id,)).start()
            time.sleep(60)  # boucle toutes les 60 secondes
        except Exception as e:
            print("❌ Erreur dans la boucle comments:", e)
            time.sleep(60)
