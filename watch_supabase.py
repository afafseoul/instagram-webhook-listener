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
