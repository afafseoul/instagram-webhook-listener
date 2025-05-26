from flask import Flask, request, redirect, render_template_string, session
import requests
import json
import os
from datetime import datetime, timedelta
from threading import Thread
import time

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "supersecret")

@app.route('/')
def index():
    return '🏠 API Commanda opérationnelle.'

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN")
    MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")

    print("📥 Requête Webhook reçue")
    if request.method == 'GET':
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        print(f"🔍 GET mode={mode}, token={token}, challenge={challenge}")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("✅ Vérification du webhook réussie")
            return challenge, 200
        print("❌ Échec vérification webhook")
        return "Erreur de vérification", 403

    if request.method == 'POST':
        data = request.json
        print(f"📩 Données POST reçues: {json.dumps(data, indent=2)}")
        if MAKE_WEBHOOK_URL:
            print(f"📤 Redirection vers MAKE_WEBHOOK_URL: {MAKE_WEBHOOK_URL}")
            requests.post(MAKE_WEBHOOK_URL, json=data)
        return "OK", 200

def check_instagram_posts():
    SYSTEM_TOKEN = os.getenv("META_SYSTEM_TOKEN")
    MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")
    last_seen = {}
    business_id = "9878394526928338"  # Business ID fixe

    while True:
        try:
            print("🔁 Début boucle de vérification des posts IG")
            pages_res = requests.get(f"https://graph.facebook.com/v19.0/{business_id}/client_pages", params={
                "access_token": SYSTEM_TOKEN
            })
            print(f"📦 Réponse /client_pages: {pages_res.text}")
            pages = pages_res.json().get("data", [])

            for page in pages:
                page_id = page.get("id")
                print(f"➡️ Page détectée: {page_id}")

                ig_resp = requests.get(f"https://graph.facebook.com/v19.0/{page_id}", params={
                    "fields": "instagram_business_account",
                    "access_token": SYSTEM_TOKEN
                })
                print(f"📦 Réponse /{page_id}?fields=instagram_business_account: {ig_resp.text}")

                ig_account = ig_resp.json().get("instagram_business_account")
                if ig_account:
                    ig_id = ig_account.get("id")
                    print(f"✅ Compte IG trouvé: {ig_id}")
                    url = f"https://graph.facebook.com/v19.0/{ig_id}/media"
                    params = {
                        "fields": "id,caption,media_type,media_url,permalink,timestamp,username",
                        "access_token": SYSTEM_TOKEN
                    }
                    res = requests.get(url, params=params)
                    print(f"📦 Réponse /{ig_id}/media: {res.text}")

                    media = res.json().get("data", [])
                    if not media:
                        print(f"⚠️ Aucun média trouvé pour IG: {ig_id}")
                        continue

                    latest_post = media[0]
                    print(f"🆕 Dernier post ID: {latest_post['id']} pour IG: {ig_id}")
                    if ig_id not in last_seen or last_seen[ig_id] != latest_post["id"]:
                        last_seen[ig_id] = latest_post["id"]
                        if MAKE_WEBHOOK_URL:
                            print(f"🚀 Nouveau post détecté. Envoi vers {MAKE_WEBHOOK_URL}")
                            requests.post(MAKE_WEBHOOK_URL, json=latest_post)
                else:
                    print(f"❌ Aucun compte IG associé à la page {page_id}")

        except Exception as e:
            print(f"💥 Erreur dans check_instagram_posts: {str(e)}")

        print("⏳ Pause 60s avant prochain check")
        time.sleep(60)

# 🔁 Démarre le scanner en arrière-plan
Thread(target=check_instagram_posts).start()

if __name__ == '__main__':
    app.run(debug=True)
