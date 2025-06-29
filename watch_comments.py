import requests
import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MAKE_NEW_POST_WEBHOOK = os.getenv("MAKE_NEW_POST_WEBHOOK")  # ton lien Make

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_existing_media_ids(instagram_id, token):
    """Récupère les media_ids actuels du compte IG"""
    url = f"https://graph.facebook.com/v19.0/{instagram_id}/media"
    params = {"access_token": token, "limit": 100}
    try:
        res = requests.get(url, params=params, timeout=10)
        items = res.json().get("data", [])
        return [item["id"] for item in items if "id" in item]
    except Exception as e:
        print("❌ Erreur récupération médias :", e)
        return []

def store_initial_media_list(instagram_id, media_ids):
    """Stocke les media_ids dans Supabase (1 ligne par media)"""
    for media_id in media_ids:
        supabase.table("media_known").insert({
            "instagram_id": instagram_id,
            "media_id": media_id
        }).execute()

def media_id_already_known(instagram_id, media_id):
    """Vérifie si le media_id est déjà connu"""
    result = supabase.table("media_known").select("id").eq("instagram_id", instagram_id).eq("media_id", media_id).execute()
    return bool(result.data)

def save_new_media_id(instagram_id, media_id):
    """Ajoute le media_id à la base Supabase"""
    supabase.table("media_known").insert({
        "instagram_id": instagram_id,
        "media_id": media_id
    }).execute()

def handle_comment_event(data):
    """Analyse un événement webhook reçu, regarde si le commentaire est sur un nouveau post"""
    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if value.get("item") == "comment":
                    media_id = value.get("parent_id")  # ou 'post_id' selon la structure exacte
                    instagram_id = entry.get("id")

                    if not media_id or not instagram_id:
                        continue

                    if not media_id_already_known(instagram_id, media_id):
                        print(f"🆕 Nouveau post détecté avec media_id : {media_id}")
                        send_new_post_webhook(instagram_id, media_id, value)
                        save_new_media_id(instagram_id, media_id)
    except Exception as e:
        print("❌ Erreur traitement commentaire :", str(e))

def send_new_post_webhook(instagram_id, media_id, comment_data):
    """Envoie les données à Make.com"""
    payload = {
        "event": "new_post_detected",
        "instagram_id": instagram_id,
        "media_id": media_id,
        "comment": comment_data
    }
    try:
        res = requests.post(MAKE_NEW_POST_WEBHOOK, json=payload, timeout=10)
        print("📤 Envoi webhook Make réussi :", res.status_code)
    except Exception as e:
        print("❌ Erreur envoi webhook Make :", str(e))
