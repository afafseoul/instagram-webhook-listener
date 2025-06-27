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
        "pages_read_engagement"
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
        send_email(ADMIN_EMAIL, "❌ Échec OAuth", error)
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

        send_email(
            ADMIN_EMAIL,
            "✅ Nouveau token client",
            f"📄 Token long terme : {token[:50]}...\n\nExpire le : {expires_at}\nPage : {page_name}\nIG : {username}"
        )

        return f"""
        ✅ <b>Connexion réussie !</b><br><br>
        🔑 <b>Token reçu</b> : {token[:50]}...<br>
        📄 <b>Page</b> : {page_name}<br>
        📸 <b>Instagram</b> : {username}<br><br>
        🟢 Le token a été stocké dans Supabase et un email a été envoyé.<br>
        <br>
        <a href=\"https://instagram-webhook-listener.onrender.com/oauth\">Retour</a>
        """

    except Exception as e:
        error_text = str(e)

        if "OAuthException" in error_text and ("does not have access" in error_text or "not authorized" in error_text):
            try:
                page_resp = requests.get("https://graph.facebook.com/v19.0/me/accounts", params={"access_token": token}).json()
                page = page_resp.get("data", [{}])[0]
                page_name = page.get("name", "inconnue")
            except:
                page_name = "inconnue"

            try:
                user_resp = requests.get("https://graph.facebook.com/v19.0/me?fields=name", params={"access_token": token}).json()
                user_name = user_resp.get("name", "utilisateur inconnu")
            except:
                user_name = "utilisateur inconnu"

            msg = f"❌ Erreur : Le compte Facebook <b>{user_name}</b> n'est pas administrateur de la page <b>{page_name}</b>."
            print(msg)
            send_email(ADMIN_EMAIL, "❌ Échec post-OAuth", msg)
            return f"<h2 style='color:red'>{msg}</h2>"

        if "connected_instagram_account" in error_text:
            try:
                page_name = page_data.get("name", "inconnue")
            except:
                page_name = "inconnue"
            msg = f"❌ Erreur : La page <b>{page_name}</b> n'est pas liée à un compte Instagram professionnel."
            print(msg)
            send_email(ADMIN_EMAIL, "❌ Échec post-OAuth", msg)
            return f"<h2 style='color:red'>{msg}</h2>"

        msg = f"❌ Erreur post-OAuth : {error_text}"
        print(msg)
        send_email(ADMIN_EMAIL, "❌ Échec post-OAuth", msg)
        return f"<h2 style='color:red'>{msg}</h2>"

if __name__ == "__main__":
    app.run()
