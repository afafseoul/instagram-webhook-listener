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

    if request.method == 'GET':
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        return "Erreur de vérification", 403

    if request.method == 'POST':
        data = request.json
        if MAKE_WEBHOOK_URL:
            requests.post(MAKE_WEBHOOK_URL, json=data)
        return "OK", 200

def check_instagram_posts():
    SYSTEM_TOKEN = os.getenv("META_SYSTEM_TOKEN")
    MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")
    last_seen = {}

    while True:
        try:
            businesses = requests.get("https://graph.facebook.com/v19.0/me/businesses", params={
                "access_token": SYSTEM_TOKEN
            }).json().get("data", [])

            for biz in businesses:
                business_id = biz["id"]
                pages = requests.get(f"https://graph.facebook.com/v19.0/{business_id}/client_pages", params={
                    "access_token": SYSTEM_TOKEN
                }).json().get("data", [])

                for page in pages:
                    page_id = page["id"]
                    ig_resp = requests.get(f"https://graph.facebook.com/v19.0/{page_id}", params={
                        "fields": "instagram_business_account",
                        "access_token": SYSTEM_TOKEN
                    }).json()

                    ig_account = ig_resp.get("instagram_business_account")
                    if ig_account:
                        ig_id = ig_account["id"]
                        url = f"https://graph.facebook.com/v19.0/{ig_id}/media"
                        params = {
                            "fields": "id,caption,media_type,media_url,permalink,timestamp,username",
                            "access_token": SYSTEM_TOKEN
                        }
                        res = requests.get(url, params=params)
                        media = res.json().get("data", [])
                        if not media:
                            continue
                        latest_post = media[0]
                        if ig_id not in last_seen or last_seen[ig_id] != latest_post["id"]:
                            last_seen[ig_id] = latest_post["id"]
                            if MAKE_WEBHOOK_URL:
                                requests.post(MAKE_WEBHOOK_URL, json=latest_post)
        except Exception as e:
            print(f"Erreur Instagram check: {e}")

        time.sleep(60)

# 🔁 Démarre le scanner en arrière-plan
Thread(target=check_instagram_posts).start()

if __name__ == '__main__':
    app.run(debug=True)
