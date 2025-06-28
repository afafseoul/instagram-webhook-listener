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

        success_msg = f"✅ <b>Connexion réussie !</b><br><br>\n🔑 <b>Token reçu</b> : {token[:50]}...<br>\n📄 <b>Page</b> : {page_name}<br>\n📸 <b>Instagram</b> : {username}<br><br>\n🟢 Le token a été stocké dans Supabase et un email a été envoyé.<br><br>\n<a href=\"https://instagram-webhook-listener.onrender.com/oauth\">Retour</a>"

        send_email(
            ADMIN_EMAIL,
            f"✅ Nouveau token client - {page_name}",
            success_msg
        )

        return success_msg

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
            msg = """
            ❌ Échec : aucune page Facebook n’a été récupérée avec votre compte.

            Cela peut venir de plusieurs causes :

            1. 👉 Vous n’avez rien sélectionné dans le processus de connexion.
               • Recommencez le processus et sélectionnez une page Facebook liée à votre compte Instagram professionnel.

            2. 👉 Vous avez sélectionné une page Facebook sur laquelle votre compte n’a PAS les bons droits.
               • Il faut que votre compte Facebook ait les “accès complets” à cette page.

               🔧 Pour vérifier et corriger cela :
               - Connectez-vous à votre compte Facebook
               - Allez sur la page concernée
               - En haut à droite : cliquez sur “Passer à la Page”
               - Cliquez sur “Paramètres” > “Accès à la Page”
               - Vérifiez que votre nom est bien présent dans la section “Accès à la Page”
               - Assurez-vous que vous avez le rôle “Accès total”

            3. 👉 La page sélectionnée n’est liée à aucun compte Instagram professionnel
               • Pour lier un compte Instagram à votre page Facebook :
                 - Accédez à la page Facebook concernée
                 - Allez dans “Paramètres” > “Instagram”
                 - Cliquez sur “Lier un compte” ou “Associer un compte”
                 - Connectez-vous avec votre compte Instagram professionnel
            """
            print(msg)
            send_email(ADMIN_EMAIL, "❌ Échec post-OAuth - Aucune page", msg)
            return f"<h2 style='color:red; white-space:pre-wrap'>{msg}</h2>"

        page_name = pages[0].get("name", "inconnue")

        if "OAuthException" in error_text and ("does not have access" in error_text or "not authorized" in error_text):
            msg = f"❌ Erreur : Le compte Facebook <b>{user_name}</b> n'est pas administrateur de la page <b>{page_name}</b>."
            print(msg)
            send_email(ADMIN_EMAIL, f"❌ Échec post-OAuth - {page_name}", msg)
            return f"<h2 style='color:red'>{msg}</h2>"

        if "connected_instagram_account" in error_text:
            msg = f"❌ Erreur : La page <b>{page_name}</b> n'est pas liée à un compte Instagram professionnel."
            print(msg)
            send_email(ADMIN_EMAIL, f"❌ Échec post-OAuth - {page_name}", msg)
            return f"<h2 style='color:red'>{msg}</h2>"

        if "Missing permissions" in error_text or "permissions error" in error_text:
            msg = """
            ❌ Échec : autorisations insuffisantes accordées à l’application.

            ✅ Pour fonctionner correctement, nous avons besoin des autorisations suivantes :
            - pages_show_list
            - pages_read_engagement
            - pages_manage_metadata
            - instagram_basic
            - instagram_manage_comments

            🔍 Vous n’avez pas validé certains de ces accès lors de la connexion.

            🛠️ Que faire :
            1. Recommencez la connexion
            2. Lors de la pop-up Meta, accordez toutes les autorisations demandées (ne modifiez pas les cases cochées)
            3. Terminez le processus
            """
            print(msg)
            send_email(ADMIN_EMAIL, f"❌ Échec post-OAuth - {page_name}", msg)
            return f"<h2 style='color:red; white-space:pre-wrap'>{msg}</h2>"

        msg = "❌ Erreur post-OAuth inconnue : " + error_text
        print(msg)
        send_email(ADMIN_EMAIL, f"❌ Échec post-OAuth - {page_name}", msg)
        return f"<h2 style='color:red'>{msg}</h2>"

if __name__ == "__main__":
    app.run()
