import os
import requests

GRAPH_BASE = "https://graph.facebook.com/v19.0"
APP_ID = os.getenv("META_CLIENT_ID")
APP_SECRET = os.getenv("META_CLIENT_SECRET")

def graph_get(endpoint: str, params: dict) -> dict:
    url = f"{GRAPH_BASE}/{endpoint}"
    res = requests.get(url, params=params, timeout=10)
    data = res.json()
    if res.status_code != 200:
        msg = data.get("error", {}).get("message", "Unknown error")
        raise Exception(msg)
    return data

def get_long_token(code: str):
    try:
        redirect_uri = "https://instagram-webhook-listener.onrender.com/callback"

        # 🔁 1. Échange code → token court terme
        print("🔁 Exchange code → short token...")
        short_data = graph_get("oauth/access_token", {
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "redirect_uri": redirect_uri,
            "code": code,
        })
        short_token = short_data.get("access_token")
        if not short_token:
            raise Exception("Token court introuvable")
        print("✅ short_token:", short_token)

        # ✅ 2. Vérifie que ce token a bien les permissions nécessaires
        print("🔍 Vérification des permissions...")
        graph_get("me", {"fields": "id", "access_token": short_token})
        accounts = graph_get("me/accounts", {"access_token": short_token}).get("data", [])
        if not accounts:
            raise Exception("Aucune page Facebook liée au compte")

        page = accounts[0]
        ig_acc = page.get("instagram_business_account")
        if not ig_acc:
            raise Exception("La page Facebook n'est pas liée à un compte Instagram Business")

        ig_id = ig_acc.get("id")
        ig_info = graph_get(ig_id, {"fields": "username", "access_token": short_token})
        ig_username = ig_info.get("username", "")

        print(f"✅ Permissions vérifiées. IG username: {ig_username}")

        # 🔁 3. Génère le token long terme
        print("🔁 Exchange short → long token...")
        long_data = graph_get("oauth/access_token", {
            "grant_type": "fb_exchange_token",
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "fb_exchange_token": short_token,
        })
        long_token = long_data.get("access_token")
        expires_in = long_data.get("expires_in", 0)
        if not long_token:
            raise Exception("Échec conversion en token long terme")
        print(f"✅ long_token: {long_token} (expires_in={expires_in}s)")

        return long_token, page, {"id": ig_id, "username": ig_username}, None

    except Exception as e:
        print("❌ get_long_token ERROR:", str(e))
        return None, None, None, str(e)

def send_email(to: str, subject: str, body: str):
    key = os.getenv("MAILGUN_API_KEY")
    return requests.post(
        "https://api.mailgun.net/v3/sandbox.mailgun.org/messages",
        auth=("api", key),
        data={
            "from": "Commanda <mailgun@sandbox.mailgun.org>",
            "to": to,
            "subject": subject,
            "text": body,
        },
        timeout=10,
    )
