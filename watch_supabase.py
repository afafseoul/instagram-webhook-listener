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
    print(f"📡 Requête Facebook pour {instagram_id}")
    try:
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        items = res.json().get("data", [])
        print(f"📝 Résultat brut : {items}")
        if items:
            return items[0]["timestamp"]
    except Exception as e:
        print("❌ Erreur get latest post timestamp :", e)
    return None

def process_pending_clients():
    """Détecte les clients avec un abonnement activé mais sans timestamp"""
    print("🔍 Recherche des clients à traiter...")
    result = supabase.table("instagram_tokens") \
        .select("*") \
        .or_("service_start_timestamp.is.null,service_start_timestamp.eq.''") \
        .or_("abonnement_1.eq.true") \
        .execute()
    
    print(f"📋 Clients récupérés : {len(result.data)}")

    for user in result.data:
        instagram_id = user["instagram_id"]
        abonnement_1 = user.get("abonnement_1")

        timestamp = user.get("service_start_timestamp")

        print(f"\n➡️ Traitement : {instagram_id}")
        print(f"   - abonnement_1 : {abonnement_1}")
        print(f"   - timestamp actuel : {timestamp}")

        # Vérifie si au moins un abonnement actif et timestamp vide
        if (abonnement_1 or abonnement_2 or abonnement_3) and (not timestamp or str(timestamp).strip() == ''):
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
            print("⏭️ Conditions non remplies (pas d'abonnement actif ou timestamp déjà défini)")

if __name__ == "__main__":
    while True:
        process_pending_clients()
        time.sleep(10)
