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

@app.route('/oauth-callback')
def oauth_callback():
    code = request.args.get('code')
    state = request.args.get('state')

    if not code:
        return "Erreur : aucun code reçu", 400

    token_url = "https://graph.facebook.com/v19.0/oauth/access_token"
    params = {
        "client_id": "2883439835182858",
        "redirect_uri": "https://instagram-webhook-listener.onrender.com/oauth-callback",
        "client_secret": os.environ.get("OAUTH_CLIENT_SECRET"),
        "code": code
    }
    res = requests.get(token_url, params=params)
    data = res.json()

    access_token = data.get("access_token")
    if not access_token:
        return f"Erreur d'obtention du token : {data}", 400

    page_name = "Non détectée"
    try:
        page_req = requests.get("https://graph.facebook.com/v19.0/me/accounts", params={
            "access_token": access_token
        })
        page_data = page_req.json()
        page_name = page_data.get("data", [{}])[0].get("name", "Inconnue")
    except:
        pass

    email = session.get("email", "test@ece-cook.com")
    plan = session.get("plan", "Free")
    preferences = session.get("preferences", "Style par défaut")
    date_start = datetime.now().isoformat()
    date_end = (datetime.now() + timedelta(days=30)).isoformat()

    payload = {
        "email": email,
        "plan": plan,
        "preferences": preferences,
        "date_start": date_start,
        "date_end": date_end,
        "page_name": page_name,
        "type": "oauth",
        "access_token": access_token
    }

    return render_template_string(f"""
    <html>
      <head><title>Connexion réussie</title></head>
      <body style="font-family: sans-serif; padding: 2em;">
        <h2>✅ Connexion Meta réussie</h2>
        <p>L’automatisation est maintenant activée pour :</p>
        <ul>
          <li><strong>Email :</strong> {email}</li>
          <li><strong>Plan :</strong> {plan}</li>
          <li><strong>Préférences :</strong> {preferences}</li>
          <li><strong>Page Facebook :</strong> {page_name}</li>
          <li><strong>Du :</strong> {date_start[:10]} au {date_end[:10]}</li>
        </ul>
        <a href="https://cozy-maamoul-92d86f.netlify.app/dashboard.html">↩️ Retour au dashboard</a>
      </body>
    </html>
    """)

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

Thread(target=check_instagram_posts).start()

if __name__ == '__main__':
    app.run(debug=True)
