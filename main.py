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

        connected_insta_id = page_data.get("connected_instagram_account", {}).get("id")
        selected_insta_id = insta_data.get("id")

        if connected_insta_id and selected_insta_id and connected_insta_id != selected_insta_id:
            msg = (
                f"❌ Erreur : Le compte Instagram sélectionné via OAuth ne correspond pas à celui lié à la page Facebook.<br><br>"
                f"➡️ Page Facebook : <b>{page_data.get('name', 'inconnue')}</b><br>"
                f"📎 Compte Instagram lié à la page : <b>{connected_insta_id}</b><br>"
                f"🔗 Compte Instagram sélectionné : <b>{selected_insta_id}</b><br><br>"
                "Merci de sélectionner dans la fenêtre d’autorisation le compte Instagram qui est bien relié à la page choisie.<br>"
                "Vérifiez dans votre page Facebook > Paramètres > Instagram que c’est bien le bon compte lié."
            )
            print(msg)
            send_email(ADMIN_EMAIL, "❌ Échec post-OAuth", msg)
            return f"<h2 style='color:red'>{msg}</h2>"

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
        🟢 Le token a été stocké <br>
        <br>
        <a href=\"https://instagram-webhook-listener.onrender.com/oauth\">Retour</a>
        """

    except Exception as e:
        error_text = str(e)

        try:
            user_resp = requests.get("https://graph.facebook.com/v19.0/me?fields=name", params={"access_token": token}).json()
            user_name = user_resp.get("name", "utilisateur inconnu")
        except:
            user_name = "utilisateur inconnu"

        try:
            page_resp = requests.get("https://graph.facebook.com/v19.0/me/accounts", params={"access_token": token}).json()
            pages = page_resp.get("data", [])
        except:
            pages = []

        if not pages:
            msg = (
                "❌ <span style='font-size: 20px; font-weight: bold;'>Erreur post-OAuth :</span> "
                "<span style='font-size: 18px;'>soit vous n’avez pas associé la bonne page Facebook au bon compte Instagram, "
                "soit vous n’êtes pas administrateur de la page Facebook sélectionnée.</span><br><br>"
                "<span style='font-size: 16px;'>Merci de vérifier :</span><br>"
                "<span style='font-size: 16px;'>1. Que votre compte Facebook est bien administrateur de la page (<b>Page > Paramètres > Accès à la Page</b>)</span><br>"
                "<span style='font-size: 16px;'>2. Que la page est bien liée à un compte Instagram professionnel via <b>Paramètres > Instagram</b>.</span><br>"
                "<span style='font-size: 16px;'>3. Que vous avez bien sélectionné la bonne combinaison dans la fenêtre d’autorisation.</span>"
            )
            print(msg)
            send_email(ADMIN_EMAIL, "❌ Échec post-OAuth", msg)
            return f"<h2 style='color:red; font-family:Arial, sans-serif'>{msg}</h2>"

        if "OAuthException" in error_text and ("does not have access" in error_text or "not authorized" in error_text):
            page_name = pages[0].get("name", "inconnue")
            msg = (
                "❌ <span style='font-size: 20px; font-weight: bold;'>Erreur post-OAuth :</span> "
                "<span style='font-size: 18px;'>soit vous n’avez pas associé la bonne page Facebook au bon compte Instagram, "
                "soit vous n’êtes pas administrateur de la page Facebook sélectionnée.</span><br><br>"
                "<span style='font-size: 16px;'>Merci de vérifier :</span><br>"
                "<span style='font-size: 16px;'>1. Que votre compte Facebook est bien administrateur de la page (<b>Page > Paramètres > Accès à la Page</b>)</span><br>"
                "<span style='font-size: 16px;'>2. Que la page est bien liée à un compte Instagram professionnel via <b>Paramètres > Instagram</b>.</span><br>"
                "<span style='font-size: 16px;'>3. Que vous avez bien sélectionné la bonne combinaison dans la fenêtre d’autorisation.</span>"
            )
            print(msg)
            send_email(ADMIN_EMAIL, "❌ Échec post-OAuth", msg)
            return f"<h2 style='color:red; font-family:Arial, sans-serif'>{msg}</h2>"

        if "connected_instagram_account" in error_text:
            page_name = pages[0].get("name", "inconnue")
            msg = f"❌ Erreur : La page <b>{page_name}</b> n'est pas liée à un compte Instagram professionnel."
            print(msg)
            send_email(ADMIN_EMAIL, "❌ Échec post-OAuth", msg)
            return f"<h2 style='color:red'>{msg}</h2>"

        fallback_msg = f"❌ Erreur post-OAuth inconnue : {error_text}"
        print(fallback_msg)
        send_email(ADMIN_EMAIL, "❌ Échec post-OAuth", fallback_msg)
        return f"<h2 style='color:red'>{fallback_msg}</h2>"

if __name__ == "__main__":
    app.run()
