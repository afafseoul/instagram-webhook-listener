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

        # Souscription aux événements de la page (feed et messages)
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

@app.route("/webhook", methods=["POST"])

@app.before_request
def log_every_request():
    if request.method == "POST":
        print("🚨 Requête POST détectée")
        print("➡️  Chemin :", request.path)
        try:
            data = request.get_json(force=True)
            print("📩 Payload brut reçu :")
            print(data)
        except Exception as e:
            print("⚠️ Aucune payload JSON ou erreur :", e)

def webhook():
    # ✅ Affiche la route exacte reçue par Flask
    print("Requête reçue sur :", request.path)
    
    # ✅ Affiche le JSON brut reçu (quel que soit le type d’événement)
    data = request.get_json(force=True)
    print("📩 Payload brut reçu :")
    print(data)
    return "ok", 200

    # ✅ CODE DE TRAITEMENT NORMAL (EN COMMENTAIRE TEMPORAIRE)
    """
    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                field = change.get("field")
                item = value.get("item")

                # Commentaire
                if item == "comment":
                    instagram_id = entry.get("id")
                    media_id = value.get("parent_id")
                    print(f"📣 Nouveau commentaire détecté sur le compte Instagram {instagram_id} - Post : {media_id}")

                # Nouveau post
                elif item == "post" and value.get("verb") == "add":
                    instagram_id = entry.get("id")
                    media_id = value.get("post_id") or value.get("id")
                    print(f"🆕 Nouveau post détecté sur le compte Instagram {instagram_id} - Post : {media_id}")

                # DM Instagram (messages)
                elif field == "messages":
                    sender_id = value.get("sender", {}).get("id")
                    message_text = value.get("message", {}).get("text")
                    print(f"📥 Nouveau DM Instagram de {sender_id} : {message_text}")
                    if sender_id and message_text:
                        send_instagram_dm(sender_id, "Merci pour votre message !")

    except Exception as e:
        print("❌ Erreur dans le traitement du webhook :", str(e))
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
