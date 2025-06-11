import os
import time
import requests
from google_sheet import fetch_page_ids

META_TOKEN = os.environ.get("META_SYSTEM_TOKEN")
MAKE_WEBHOOK = os.environ.get("MAKE_WEBHOOK_COMMENTS")

# Cache local pour suivre les commentaires déjà vus
last_seen_comments = {}

def subscribe_page_to_webhooks(page_id):
    """Abonne la page Facebook aux webhooks pour recevoir les commentaires Instagram."""
    url = f"https://graph.facebook.com/v19.0/{page_id}/subscribed_apps"
    payload = {
        # Selon la documentation Meta Graph API, le champ correct est
        # "comments" afin de recevoir les commentaires Instagram relayés
        # via la Page Facebook associée.
        "subscribed_fields": "comments",
        "access_token": META_TOKEN,
    }
    try:
        response = requests.post(url, data=payload)
        if response.ok:
            print(f"✅ Page {page_id} abonnée aux webhooks")
        else:
            print(
                f"⚠️ Échec abonnement page {page_id}: {response.status_code} {response.text}"
            )
    except Exception as e:
        print(f"❌ Exception abonnement page {page_id}: {e}")

def get_comments(instagram_id):
    url = f"https://graph.facebook.com/v19.0/{instagram_id}/media?fields=id,comments{{id,text,timestamp,username}}&access_token={META_TOKEN}"
    try:
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        return data.get("data", [])
    except Exception as e:
        print(f"❌ Erreur récupération des commentaires : {e}")
        return []

def send_to_make(comment, media_id, client_name):
    payload = {
        "media_id": media_id,
        "comment_id": comment["id"],
        "text": comment.get("text"),
        "username": comment.get("username"),
        "timestamp": comment.get("timestamp"),
        "client": client_name,
    }
    try:
        res = requests.post(MAKE_WEBHOOK, json=payload)
        if res.status_code == 200:
            print(f"📨 Envoyé à Make : {comment['text'][:30]}...")
        else:
            print(f"⚠️ Erreur Make : {res.status_code} {res.text}")
    except Exception as e:
        print(f"❌ Exception envoi Make : {e}")

def watch_new_comments():
    print("🧠 Lancement détection rapide des commentaires...")
    pages = fetch_page_ids()
    while True:
        for page in pages:
            ig_id = page["instagram_id"]
            client = page["client_name"]
            medias = get_comments(ig_id)
            for media in medias:
                media_id = media.get("id")
                comments = media.get("comments", {}).get("data", [])
                for comment in comments:
                    if comment["id"] not in last_seen_comments.get(media_id, []):
                        send_to_make(comment, media_id, client)
                        last_seen_comments.setdefault(media_id, []).append(comment["id"])
                        # On garde max 50 commentaires récents par post
                        last_seen_comments[media_id] = last_seen_comments[media_id][-50:]
        time.sleep(10)  # 🔁 boucle toutes les 10 secondes
