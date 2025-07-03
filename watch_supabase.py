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
        .is_("service_start_timestamp", "null") \
        .eq("abonnement_1", True) \
        .execute()

    for user in result.data:
        instagram_id = user["instagram_id"]
        token = user.get("access_token") or os.getenv("META_SYSTEM_TOKEN")

        # 👉 Option 1 : timestamp du dernier post
        latest_ts = get_instagram_latest_post_timestamp(instagram_id, token)

        # 👉 Option 2 : ou juste le timestamp actuel
        # latest_ts = datetime.now(timezone.utc).isoformat()

        if latest_ts:
            supabase.table("instagram_tokens") \
                .update({"service_start_timestamp": latest_ts}) \
                .eq("instagram_id", instagram_id) \
                .execute()
            print(f"✅ Timestamp de démarrage défini pour {instagram_id} : {latest_ts}")
        else:
            print(f"⚠️ Impossible de récupérer le timestamp pour {instagram_id}")

if __name__ == "__main__":
    while True:
        process_pending_clients()
        time.sleep(10)
