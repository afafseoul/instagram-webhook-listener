import requests
import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MAKE_NEW_POST_WEBHOOK = os.getenv("MAKE_NEW_POST_WEBHOOK")  # lien Make

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_media_timestamp(media_id, token):
    """Récupère le timestamp d’un media"""
    url = f"https://graph.facebook.com/v19.0/{media_id}"
    params = {"fields": "timestamp", "access_token": token}
    try:
        res = requests.get(url, params=params, timeout=10)
        return res.json().get("timestamp")
    except Exception as e:
        print("❌ Erreur récupération timestamp media :", e)
        return None

def get_user_info(instagram_id):
    """Récupère les infos Supabase du client (abonnement, timestamp, etc.)"""
    result = supabase.table("instagram_tokens").select("*").eq("instagram_id", instagram_id).execute()
    if not result.data:
        return None
    return result.data[0]

def handle_comment_event(data):
    """Analyse un événement webhook reçu, regarde si le commentaire est sur un post valide"""
    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if value.get("item") == "comment":
                    media_id = value.get("parent_id")
                    instagram_id = entry.get("id")

                    if not media_id or not instagram_id:
                        continue

                    # 🔍 Récupération données Supabase client
                    user = get_user_info(instagram_id)
                    if not user:
                        print("❌ Utilisateur non trouvé dans Supabase")
                        continue

                    # 📛 Vérifie si abonnement actif
                    if not (user.get("abonnement_1") or user.get("abonnement_2") or user.get("abonnement_3")):
                        print("❌ Aucun abonnement actif, on ignore")
                        continue

                    # ⏱️ Vérifie le timestamp du post vs service_start_timestamp
                    token = user.get("access_token") or os.getenv("META_SYSTEM_TOKEN")
                    media_ts = get_media_timestamp(media_id, token)
                    service_ts = user.get("service_start_timestamp")

                    if not media_ts or not service_ts:
                        print("⚠️ Timestamps manquants")
                        continue

                    if media_ts > service_ts:
                        print(f"🆕 Nouveau post détecté (media_id={media_id}) après début service")
                        supabase.table("new_posts").insert({
                            "instagram_id": instagram_id,
                            "media_id": media_id
                        }).execute()
                        send_new_post_webhook(instagram_id, media_id, value)
                    else:
                        print("⏳ Ancien post, on ignore")

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
