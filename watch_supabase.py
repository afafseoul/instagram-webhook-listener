import os
import time
import requests
from datetime import datetime, timezone
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_instagram_latest_post_timestamp(instagram_id, token):
    """Récupère la date de publication du dernier post"""
    url = f"https://graph.facebook.com/v19.0/{instagram_id}/media"
    params = {"fields": "timestamp", "limit": 1, "access_token": token}
    try:
        res = requests.get(url, params=params, timeout=10)
        items = res.json().get("data", [])
        if items:
            return items[0]["timestamp"]
    except Exception as e:
        print("❌ Erreur get latest post timestamp :", e)
    return None

def process_pending_clients():
    """Détecte les clients avec un abonnement activé mais sans timestamp"""
    result = supabase.table("instagram_tokens") \
        .select("*") \
        .eq("abonnement_1", True) \
        .execute()

    for user in result.data:
        timestamp = user.get("service_start_timestamp")
        if not timestamp or str(timestamp).strip() == "":
            instagram_id = user["instagram_id"]
            token = user.get("access_token") or os.getenv("META_SYSTEM_TOKEN")

            latest_ts = get_instagram_latest_post_timestamp(instagram_id, token)

            if latest_ts:
                supabase.table("instagram_tokens") \
                    .update({"service_start_timestamp": latest_ts}) \
                    .eq("instagram_id", instagram_id) \
                    .execute()
                print(f"✅ Timestamp défini pour {instagram_id} : {latest_ts}")
            else:
                print(f"⚠️ Impossible de récupérer le timestamp pour {instagram_id}")
        else:
            print(f"⏭️ Déjà traité : {user.get('instagram_username')}")

if __name__ == "__main__":
    while True:
        process_pending_clients()
        time.sleep(10)
