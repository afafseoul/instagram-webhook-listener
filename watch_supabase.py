import os
import time
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

last_updated = None

def check_for_updates():
    """Vérifie si une ligne a été modifiée récemment"""
    global last_updated
    result = supabase.table("instagram_tokens").select("updated_at").order("updated_at", desc=True).limit(1).execute()
    if result.data:
        latest_update = result.data[0]["updated_at"]
        if last_updated is None or latest_update > last_updated:
            print(f"🔔 Changement détecté ! Nouvelle date : {latest_update}")
            last_updated = latest_update
            return True
    return False

def watch_updates():
    """Surveille en boucle les changements"""
    while True:
        try:
            if check_for_updates():
                from watch_comments import start_comment_watcher
                start_comment_watcher()
        except Exception as e:
            print("❌ Erreur dans le watcher :", str(e))
        time.sleep(10)

def handle_comment_event(data):
    """Analyse un événement webhook reçu, regarde si le commentaire est sur un post valide"""
    try:
        print("🚨 Début du traitement d'un nouveau commentaire reçu.")
        print("📩 Données reçues :", data)
        
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if value.get("item") == "comment":
                    media_id = value.get("parent_id")
                    instagram_id = entry.get("id")
                    print(f"📌 Commentaire détecté sur Instagram ID : {instagram_id} avec media_id : {media_id}")

                    if not media_id or not instagram_id:
                        print("⚠️ Données incomplètes : media_id ou instagram_id manquant.")
                        continue

                    # 🔍 Recherche de l'utilisateur dans Supabase
                    user = get_user_info(instagram_id)
                    if not user:
                        print("❌ Utilisateur introuvable dans Supabase.")
                        continue

                    print("✅ Utilisateur trouvé dans Supabase :", user)

                    # ✅ Vérifie si abonnement actif
                    if not (user.get("abonnement_1") or user.get("abonnement_2") or user.get("abonnement_3")):
                        print("⏹️ Aucun abonnement actif pour ce client, commentaire ignoré.")
                        continue

                    print("🔑 Abonnement actif détecté.")

                    # ⏱️ Vérifie le timestamp du post
                    token = user.get("access_token") or os.getenv("META_SYSTEM_TOKEN")
                    media_ts = get_media_timestamp(media_id, token)
                    service_ts = user.get("service_start_timestamp")

                    print(f"📆 Timestamp du post : {media_ts}")
                    print(f"📆 Timestamp service démarré : {service_ts}")

                    if not media_ts or not service_ts:
                        print("⚠️ Timestamps manquants, impossible de comparer.")
                        continue

                    if media_ts > service_ts:
                        print("🆕 Nouveau post détecté : media posté après le début du service.")
                        supabase.table("new_posts").insert({
                            "instagram_id": instagram_id,
                            "media_id": media_id
                        }).execute()
                        send_new_post_webhook(instagram_id, media_id, value)
                    else:
                        print("⏳ Ancien post, commentaire ignoré.")

    except Exception as e:
        print("❌ Erreur traitement commentaire :", str(e))
