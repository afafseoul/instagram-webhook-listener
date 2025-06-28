from flask import Flask, request, redirect
import os
from supabase import create_client
import requests
from utils import (
    verify_token_permissions,
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

def get_default_error_message():
    return (
        "❌ <span style='font-size: 22px; font-weight: bold;'>Erreur post-OAuth :</span><br>"
        "<span style='font-size: 18px;'>Soit vous n’avez pas associé la bonne page Facebook au bon compte Instagram,<br>"
        "soit vous n’êtes pas administrateur de la page Facebook sélectionnée.</span><br><br>"
        "<span style='font-size: 17px; font-weight: bold;'>Merci de vérifier point par point :</span><br><br>"
        "<span style='font-size: 16px;'>1️⃣ Connectez-vous à votre compte Facebook personnel (celui qui a accès à la page)</span><br>"
        "<span style='font-size: 16px;'>2️⃣ Rendez-vous sur <b>Facebook > Page concernée > Paramètres</b></span><br>"
        "<span style='font-size: 16px;'>3️⃣ Cliquez sur <b>Accès à la Page</b> (ou 'New Pages Experience')</span><br>"
        "<span style='font-size: 16px;'>4️⃣ Vérifiez que votre profil Facebook est bien <b>Administrateur</b></span><br><br>"
        "<span style='font-size: 16px;'>5️⃣ Allez dans <b>Paramètres > Instagram</b> pour vérifier que la page est bien liée à un compte Instagram professionnel</span><br><br>"
        "<span style='font-size: 16px;'>6️⃣ Dans la fenêtre d’autorisation, sélectionnez uniquement cette page Facebook et le bon compte Instagram</span><br>"
    )

def fetch_instagram_data(token):
    accounts_resp = requests.get(
        "https://graph.facebook.com/v19.0/me/accounts",
        headers={"Authorization": f"Bearer {token}"}
    ).json()
    if not accounts_resp.get("data"):
        raise Exception("Aucune page Facebook accessible trouvée.")

    page_data = accounts_resp["data"][0]  # à améliorer si besoin
    page_id = page_data.get("id")

    connected_resp = requests.get(
        f"https://graph.facebook.com/v19.0/{page_id}?fields=connected_instagram_account",
        headers={"Authorization": f"Bearer {token}"}
    ).json()
    connected_insta = connected_resp.get("connected_instagram_account")

    insta_data = {}
    if connected_insta:
        insta_id = connected_insta.get("id")
        if insta_id:
            insta_data = requests.get(
                f"https://graph.facebook.com/v19.0/{insta_id}?fields=id,username",
                headers={"Authorization": f"Bearer {token}"}
            ).json()

    return page_data, insta_data

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

    page_name = ""
    username = ""

    try:
        verify_token_permissions(token)
        page_data, insta_data = fetch_instagram_data(token)

        connected_insta = page_data.get("connected_instagram_account")
        connected_insta_id = connected_insta.get("id") if connected_insta else None
        selected_insta_id = insta_data.get("id")

        print(f"🔍 IG connecté à la page : {connected_insta_id}")
        print(f"🔍 IG sélectionné via API : {selected_insta_id}")

        page_id = page_data.get("id", "")
        page_name = page_data.get("name", "")
        insta_id = insta_data.get("id", "")
        username = insta_data.get("username", "")

        print("✅ Code reçu :", code)
        print("📄 Page :", page_name)
        print("📸 IG :", username)

        if not page_id or not page_name:
            print("⚠️ page_id ou page_name manquant")
            raise ValueError("Missing page_id")
        if not insta_id or not username:
            print("⚠️ insta_id ou username manquant")
            raise ValueError("Missing insta_id")
        if not connected_insta_id:
            print("⚠️ Aucun compte Instagram connecté à la page")
            raise ValueError("Missing connected Instagram")

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
            f"✅ Nouveau token client - {username or page_name or 'inconnu'}",
            f"📄 <b>Token long terme</b> : {token[:50]}...<br><br>"
            f"⏳ <b>Expiration</b> : {expires_at}<br>"
            f"📄 <b>Page</b> : {page_name}<br>"
            f"📸 <b>Instagram</b> : {username}"
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
        print("❌ Exception dans oauth_callback:", str(e))
        msg = get_default_error_message()
        send_email(ADMIN_EMAIL, f"❌ OAuth échoué - {page_name or username or 'inconnu'}", msg)
        return f"<h2 style='color:red; font-family:Arial, sans-serif'>{msg}</h2>"

if __name__ == "__main__":
    app.run()
