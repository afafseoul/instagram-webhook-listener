import time
import requests
import os
from google_sheet import fetch_page_ids

SYSTEM_TOKEN = os.getenv("META_SYSTEM_TOKEN")
last_seen_posts = {}

def watch_new_posts():
    while True:
        print("🔁 Vérification nouveaux posts...")
        page_ids = fetch_page_ids()

        for page_id in page_ids:
            try:
                ig_data = requests.get(f"https://graph.facebook.com/v19.0/{page_id}", params={
                    "fields": "instagram_business_account",
                    "access_token": SYSTEM_TOKEN
                }).json()

                ig = ig_data.get("instagram_business_account")
                if not ig:
                    continue

                ig_id = ig["id"]
                media = requests.get(f"https://graph.facebook.com/v19.0/{ig_id}/media", params={
                    "fields": "id,caption,media_type,media_url,permalink,timestamp,username",
                    "access_token": SYSTEM_TOKEN
                }).json().get("data", [])

                if not media:
                    continue

                latest = media[0]
                if last_seen_posts.get(ig_id) != latest["id"]:
                    print(f"🆕 Nouveau post détecté pour {ig_id} : {latest['id']}")
                    last_seen_posts[ig_id] = latest["id"]

            except Exception as e:
                print(f"💥 Erreur boucle post: {e}")

        time.sleep(45)
