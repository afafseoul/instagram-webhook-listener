from flask import Flask, request, redirect
import os
from supabase import create_client
import requests
from utils import (
    verify_token_permissions,
    fetch_instagram_data,
    get_long_token,
)
from datetime import datetime

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
BASE_REDIRECT_URL = os.getenv("BASE_REDIRECT_URL")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
MAKE_WEBHOOK_EMAIL = os.getenv("MAKE_WEBHOOK_EMAIL")
MAKE_WEBHOOK_POSTS = os.getenv("MAKE_WEBHOOK_POSTS")  # Ajouté pour les nouveaux posts

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def send_email(to, subject, message):
    payload = {
        "to": to,
        "subject": subject,
        "message": message
    }
    print("📬 ENVOI À MAKE :", payload)
    try:
        requests.post(MAKE_WEBHOOK_EMAIL, json=payload)
    except Exception as e:
        print("❌ Erreur envoi Make.com :", str(e))

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
        "pages_read_user_content"
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
        send_email(ADMIN_EMAIL, "❌ Échec OAuth - Erreur récupération token", error)
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
            msg = f"❌ Erreur : la page <b>{page_name}</b> est déjà connectée. Vous ne pouvez pas la réassocier."
            print(msg)
            send_email(ADMIN_EMAIL, f"❌ Page déjà connectée - {page_name}", msg)
            return f"<h2 style='color:red'>{msg}</h2>"

        # Souscrire aux événements de la page
        requests.post(f"https://graph.facebook.com/v19.0/{page_id}/subscribed_apps", params={"access_token": token})

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

        success_msg = f"✅ <b>Connexion réussie !</b><br><br>\n🔑 <b>Token reçu</b> : {token[:50]}...<br>\n📄 <b>Page</b> : {page_name}<br>\n📸 <b>Instagram</b> : {username}<br><br>\n🟢 Le token a été stocké dans Supabase et un email a été envoyé.<br><br>\n<a href=\"https://instagram-webhook-listener.onrender.com/oauth\">Retour</a>"

        send_email(
            ADMIN_EMAIL,
            f"✅ Nouveau token client - {page_name}",
            success_msg
        )

        return success_msg

    except Exception as e:
        error_text = str(e)
        # même gestion d'erreurs qu'avant (inchangée)
        # [...]
        msg = "❌ Erreur post-OAuth inconnue : " + error_text
        print(msg)
        send_email(ADMIN_EMAIL, f"❌ Échec post-OAuth - {page_name}", msg)
        return f"<h2 style='color:red'>{msg}</h2>"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == os.getenv("WEBHOOK_VERIFY_TOKEN"):
            return challenge, 200
        return "Unauthorized", 403

    data = request.json
    print("📩 Webhook reçu :", data)
    if MAKE_WEBHOOK_POSTS:
        try:
            requests.post(MAKE_WEBHOOK_POSTS, json=data)
        except Exception as e:
            print("❌ Erreur envoi webhook à Make:", str(e))
    return "ok", 200

if __name__ == "__main__":
    app.run()
