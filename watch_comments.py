import os
import time
import requests
from google_sheet import fetch_page_ids

# Token système déjà fourni via les variables d'environnement
system_token = os.environ.get("META_SYSTEM_TOKEN")
MAKE_WEBHOOK = os.environ.get("MAKE_WEBHOOK_COMMENTS")

# Cache local pour suivre les commentaires déjà vus
last_seen_comments = {}

def subscribe_ig_account_to_webhooks(instagram_business_id):
    """Abonne le compte Instagram Business aux webhooks pour les commentaires."""
    url = f"https://graph.facebook.com/v19.0/{instagram_business_id}/subscribed_apps"
    payload = {
        # Pour les commentaires Instagram, le champ à souscrire est 'instagram_comments'
        "subscribed_fields": "instagram_comments",
        "access_token": system_token,
    }
    try:
        response = requests.post(url, data=payload)
        if response.ok:
            print(f"✅ IBA {instagram_business_id} abonné aux webhooks")
        else:
            print(
                f"⚠️ Échec abonnement IBA {instagram_business_id}: {response.status_code} {response.text}"
            )
    except Exception as e:
        print(f"❌ Exception abonnement IBA {instagram_business_id}: {e}")

def get_comments(instagram_id):
    url = f"https://graph.facebook.com/v19.0/{instagram_id}/media?fields=id,comments{{id,text,timestamp,username}}&access_token={system_token}"
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
