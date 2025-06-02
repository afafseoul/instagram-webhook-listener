from flask import Flask, request
import requests
import json
import os
import time
from threading import Thread
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# === CONFIG ===
WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")
SYSTEM_TOKEN = os.getenv("META_SYSTEM_TOKEN")
RENDER_URL = "https://instagram-webhook-listener.onrender.com"
SHEET_URL = "https://docs.google.com/spreadsheets/d/11H74lWqyPPc0SPVOcX0x1iN97x8qJw6c7y8-WFeWijY"

# === GOOGLE SHEETS AUTH ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("/etc/secrets/credentials.json", scope)
client = gspread.authorize(creds)

# === GLOBAL ===
last_seen_posts = {}

@app.route('/')
def index():
    return '✅ API opérationnelle'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print(f"📩 Commentaire reçu : {json.dumps(data, indent=2)}")
    if WEBHOOK_URL:
        requests.post(WEBHOOK_URL, json=data)
    return 'OK', 200

@app.route('/reply', methods=['POST'])
def reply():
    data = request.json
    ig_user_id = data.get("ig_user_id")
    comment_id = data.get("comment_id")
    message = data.get("message")

    if not all([ig_user_id, comment_id, message]):
        return "Missing data", 400

    url = f"https://graph.facebook.com/v19.0/{comment_id}/replies"
    r = requests.post(url, params={
        "access_token": SYSTEM_TOKEN,
        "message": message
    })
    print(f"💬 Réponse envoyée : {r.text}")
    return r.text, r.status_code

def fetch_page_ids():
    try:
        sheet = client.open_by_url(SHEET_URL)
        worksheet = sheet.worksheet("Feuille 2")
        records = worksheet.get_all_records()
        return [str(row["Client page id"]).strip() for row in records if row.get("Client page id")]
    except Exception as e:
        print(f"❌ Erreur lecture Google Sheet: {e}")
        return []

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
                print(f"💥 Erreur boucle post pour {page_id} : {e}")

        time.sleep(45)

def keep_alive():
    while True:
        try:
            requests.get(RENDER_URL)
        except:
            pass
        time.sleep(30)

# === THREADS ===
Thread(target=watch_new_posts).start()
Thread(target=keep_alive).start()

if __name__ == '__main__':
    app.run(debug=True)
