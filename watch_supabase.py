import os
import time
import requests
from datetime import datetime, timezone
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_instagram_latest_post_timestamp(instagram_id, token):
    """Récupère la date de publication du dernier post Instagram"""
    url = f"https://graph.facebook.com/v19.0/{instagram_id}/media"
    params = {"fields": "timestamp", "limit": 1, "access_token": token}
    try:
        res = requests.get(url, params=params, timeout=10)
        items = res.json().get("data", [])
        if items:
            return items[0]["timestamp"]
    except Exception as e:
        print("❌ Erreur récupération dernier timestamp :", e)
    return None

def process_pending_clients():
    """Détecte les clients abonnés sans timestamp défini"""
    result = supabase.table("instagram_tokens") \
        .select("*") \
        .eq("abonnement_1", True) \
        .execute()

    for user in result.data:
        instagram_id = user.get("instagram_id")
        token = user.get("access_token") or os.getenv("META_SYSTEM_TOKEN")
        service_ts = user.get("service_start_timestamp")

        # Si timestamp manquant (NULL ou vide)
        if not service_ts or str(service_ts).strip() == "" or str(service_ts).lower() == "null":
            latest_ts = get_instagram_latest_post_timestamp(instagram_id, token)

            if latest_ts:
                supabase.table("instagram_tokens") \
                    .update({"service_start_timestamp": latest_ts}) \
                    .eq("instagram_id", instagram_id) \
                    .execute()
                print(f"✅ Timestamp ajouté pour {instagram_id} : {latest_ts}")
            else:
                print(f"⚠️ Impossible de récupérer le dernier post pour {instagram_id}")
        else:
            print(f"⏭️ Déjà configuré pour {instagram_id}, on passe")

if __name__ == "__main__":
    while True:
        process_pending_clients()
        time.sleep(10)
