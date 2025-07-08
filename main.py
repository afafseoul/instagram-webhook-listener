from flask import Flask, request, redirect
import os
import requests
from datetime import datetime
from supabase import create_client
from utils import (
    verify_token_permissions,
    fetch_instagram_data,
    get_long_token,
)

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
BASE_REDIRECT_URL = os.getenv("BASE_REDIRECT_URL")
INSTAGRAM_DM_PAGE_TOKEN = os.getenv("INSTAGRAM_DM_PAGE_TOKEN")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def send_instagram_dm(recipient_id, message_text):
    url = "https://graph.facebook.com/v19.0/me/messages"
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text},
        "messaging_type": "RESPONSE"
    }
    params = {"access_token": INSTAGRAM_DM_PAGE_TOKEN}
    try:
        response = requests.post(url, params=params, json=payload, headers=headers)
        print("✅ DM envoyé :", response.status_code, response.text)
    except Exception as e:
        print("❌ Erreur envoi DM :", e)

@app.route("/oauth")
def oauth_start():
    client_id = os.getenv("META_CLIENT_ID")
    redirect_uri = BASE_REDIRECT_URL
    scope = ",".join([
        "pages_show_list",
        "instagram_basic",
        "instagram_manage_comments",
        "pages_manage_metadata",
        "pages_read_engagement",
        "pages_read_user_content",
        "pages_messaging",
        "instagram_manage_messages"
    ])
    return redirect(
        f"https://www.facebook.com/v19.0/dialog/oauth?client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&response_type=code&state=123"
    )

@app.route("/callback")
def oauth_callback():
    code = request.args.get("code")
    if not code:
        return "❌ <b>Erreur :</b> Code OAuth manquant"

    print("🔁 URL reçue :", request.url)
    print("📦 Params GET:", dict(request.args))

    redirect_uri = BASE_REDIRECT_URL
    token, expires_at, error = get_long_token(code, redirect_uri)

    if error:
        return f"❌ Erreur récupération token : {error}"

    try:
        verify_token_permissions(token)
        page_data, insta_data = fetch_instagram_data(token)

        page_id = page_data["id"]
        page_name = page_data.get("name", "")
        insta_id = insta_data["id"]
        username = insta_data.get("username", "")

        print("✅ Code reçu :", code)
        print("📄 Page :", page_name)
        print("📸 IG :", username)

        existing = supabase.table("instagram_tokens").select("id").eq("page_id", page_id).execute()
        if existing.data:
            msg = f"❌ Erreur : la page <b>{page_name}</b> est déjà connectée."
            print(msg)
            return f"<h2 style='color:red'>{msg}</h2>"

        requests.post(
            f"https://graph.facebook.com/v19.0/{page_id}/subscribed_apps",
            params={"access_token": token, "subscribed_fields": "feed,messages"}
        )

        supabase.table("instagram_tokens").insert({
            "access_token": token,
            "token_expires_at": expires_at.isoformat() if expires_at else None,
            "page_id": page_id,
            "page_name": page_name,
            "instagram_id": insta_id,
            "instagram_username": username,
            "status_verified": True,
            "created_at": datetime.utcnow().isoformat()
        }).execute()

        return f"✅ Connexion réussie pour {username} ({page_name}) !"

    except Exception as e:
        error_text = str(e)
        print("❌ Erreur post-OAuth :", error_text)
        return f"<h2 style='color:red'>❌ Erreur post-OAuth : {error_text}</h2>"

@app.route("/", methods=["POST"])
def root_fallback():
    data = request.get_json(force=True)
    print("📍 `/`")

    for entry in data.get("entry", []):
        if "messaging" in entry:
            for msg in entry["messaging"]:
                sender_id = msg.get("sender", {}).get("id")
                recipient_id = msg.get("recipient", {}).get("id")
                message = msg.get("message", {})
                text = message.get("text", "")
                mid = message.get("mid", "")
                timestamp = msg.get("timestamp")

                print("📥 [DM reçu sur `/`]")
                print(f"👤 De     : {sender_id}")
                print(f"🎯 Vers   : {recipient_id}")
                print(f"🕒 Time   : {timestamp}")
                print(f"💬 Texte  : {text}")
                print(f"🆔 MID    : {mid}")

    return "ok", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    print("📍 Requête `/webhook`")
   


    for entry in data.get("entry", []):
        # DM Instagram détecté ici aussi
        if "messaging" in entry:
            for msg in entry["messaging"]:
                sender_id = msg.get("sender", {}).get("id")
                recipient_id = msg.get("recipient", {}).get("id")
                message = msg.get("message", {})
                text = message.get("text", "")
                mid = message.get("mid", "")
                timestamp = msg.get("timestamp")

                print("📥 [DM reçu sur `/webhook`]")
                print(f"👤 De     : {sender_id}")
                print(f"🎯 Vers   : {recipient_id}")
                print(f"🕒 Time   : {timestamp}")
                print(f"💬 Texte  : {text}")
                print(f"🆔 MID    : {mid}")

        # Commentaires
        if "changes" in entry:
            for change in entry["changes"]:
                value = change.get("value", {})
                field = change.get("field")
                if field == "comments":
                    instagram_id = entry.get("id")
                    media_id = value.get("media", {}).get("id")
                    user_id = value.get("from", {}).get("id")
                    username = value.get("from", {}).get("username")
                    text = value.get("text")
                    print("🔍 Payload brut du commentaire :", value)
                    print("💬 [Commentaire détecté]")
                    print(f"👤 Compte IG  : {instagram_id}")
                    print(f"🖼️  Media ID   : {media_id}")
                    print(f"👤 Auteur      : {username} (ID {user_id})")
                    print(f"💬 Texte       : {text}")

    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
