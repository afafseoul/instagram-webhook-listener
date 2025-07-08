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
    """Envoie un message DM Instagram via l'API Graph"""
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

@app.route("/", methods=["GET", "POST"])
def home():
    return "Webhook Listener OK", 200

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
        "pages_messaging"
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

        # Souscription aux événements de la page (feed et messages d'un coup)
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

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == os.getenv("WEBHOOK_VERIFY_TOKEN"):
            return challenge, 200
        return "Unauthorized", 403

    # 🎯 Traitement du webhook POST
    data = request.json
    print("📩 Webhook reçu :", data)

    try:
        for entry in data.get("entry", []):
            # Gestion des commentaires et posts Instagram (via 'changes')
            for change in entry.get("changes", []):
                value = change.get("value", {})
                field = change.get("field")
                item = value.get("item")

                # Commentaire Instagram
                if item == "comment":
                    instagram_id = entry.get("id")
                    media_id = value.get("parent_id")
                    print(f"📣 Nouveau commentaire détecté sur le compte Instagram {instagram_id} - Post : {media_id}")

                # Nouveau post Instagram
                elif item == "post" and value.get("verb") == "add":
                    instagram_id = entry.get("id")
                    media_id = value.get("post_id") or value.get("id")
                    print(f"🆕 Nouveau post détecté sur le compte Instagram {instagram_id} - Post : {media_id}")

            # Gestion des DMs Messenger / Instagram (via 'messaging')
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event.get("sender", {}).get("id")
                message_text = messaging_event.get("message", {}).get("text")
                print(f"📥 Nouveau DM Messenger / Instagram de {sender_id} : {message_text}")

                if sender_id and message_text:
                    send_instagram_dm(sender_id, "Merci pour votre message !")

    except Exception as e:
        print("❌ Erreur dans le traitement du webhook :", str(e))

    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
