from flask import Flask, request
import requests
import json
import os
from threading import Thread
import time

app = Flask(__name__)

@app.route('/')
def index():
    return '🏠 API Commanda opérationnelle.'

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN")
    MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")

    if request.method == 'GET':
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("✅ Vérification webhook réussie")
            return challenge, 200
        return "❌ Erreur vérification", 403

    if request.method == 'POST':
        data = request.json
        print(f"📩 Webhook POST reçu: {json.dumps(data, indent=2)}")
        if MAKE_WEBHOOK_URL:
            requests.post(MAKE_WEBHOOK_URL, json=data)
        return "OK", 200

def check_instagram_posts():
    SYSTEM_TOKEN = os.getenv("META_SYSTEM_TOKEN")
    MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")
    last_seen = {}

    # 🔒 Ici on met les ID des pages Facebook manuellement
    page_ids = [
        "500108869863121",  # Page Gestion J-C
        "585442894651616"   # Page Gestion J-E (pour aeesha_slh)
    ]

    while True:
        try:
            print("🔁 Boucle détection post IG")
            for page_id in page_ids:
                print(f"➡️ Page forcée: {page_id}")
                ig_data = requests.get(f"https://graph.facebook.com/v19.0/{page_id}", params={
                    "fields": "instagram_business_account",
                    "access_token": SYSTEM_TOKEN
                }).json()

                ig_account = ig_data.get("instagram_business_account")
                if not ig_account:
                    print(f"❌ Pas de compte IG pour la page {page_id}")
                    continue

                ig_id = ig_account["id"]
                print(f"✅ IG lié détecté: {ig_id}")

                media = requests.get(f"https://graph.facebook.com/v19.0/{ig_id}/media", params={
                    "fields": "id,caption,media_type,media_url,permalink,timestamp,username",
                    "access_token": SYSTEM_TOKEN
                }).json().get("data", [])

                if not media:
                    print(f"⚠️ Aucun média pour {ig_id}")
                    continue

                latest = media[0]
                if last_seen.get(ig_id) != latest["id"]:
                    last_seen[ig_id] = latest["id"]
                    print(f"🆕 Nouveau post: {latest['id']} pour {ig_id}")
                    if MAKE_WEBHOOK_URL:
                        requests.post(MAKE_WEBHOOK_URL, json=latest)

        except Exception as e:
            print(f"💥 Erreur dans boucle IG: {str(e)}")

        print("⏳ Attente 45s")
        time.sleep(45)

def keep_alive():
    url = "https://instagram-webhook-listener.onrender.com"
    while True:
        try:
            print("🔄 Keep alive ping")
            requests.get(url)
        except:
            pass
        time.sleep(30)

Thread(target=check_instagram_posts).start()
Thread(target=keep_alive).start()

if __name__ == '__main__':
    app.run(debug=True)
