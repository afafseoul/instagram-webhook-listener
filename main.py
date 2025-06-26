from flask import Flask, request, redirect
import os
import requests
from supabase import create_client
from utils import get_long_token, verify_token_permissions, fetch_instagram_data

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
BASE_REDIRECT_URL = os.getenv("BASE_REDIRECT_URL")  # ex: https://www.commanda.site/after-auth.html
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

MAKE_WEBHOOK_EMAIL = "https://hook.eu2.make.com/lgkj7kr5nec5ijv1mo08jq03ikjv3t1y"  # ton webhook Make

def send_email(to, subject, body):
    try:
        requests.post(MAKE_WEBHOOK_EMAIL, json={
            "to": to,
            "subject": subject,
            "body": body
        }, timeout=10)
    except Exception as e:
        print("Erreur lors de l'envoi de l'email via Make:", str(e))


@app.route("/oauth")
def oauth_start():
    client_id = os.getenv("META_CLIENT_ID")
    redirect_uri = f"{request.url_root}callback"
    scope = ",".join([
        "pages_show_list",
        "instagram_basic",
        "instagram_manage_comments",
        "pages_manage_metadata",
        "pages_read_engagement"
    ])
    return redirect(
        f"https://www.facebook.com/v19.0/dialog/oauth?client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&response_type=code"
    )


@app.route("/callback")
def oauth_callback():
    code = request.args.get("code")
    if not code:
        return "Erreur : Code OAuth manquant"

    # 🔄 Étape 1 : échange de code contre access_token long terme
    token, email, error = get_long_token(code)
    if error:
        send_email(ADMIN_EMAIL, "Échec OAuth", error)
        return error

    try:
        # ✅ Étape 2 : vérification des droits et extraction données
        verify_token_permissions(token)
        page_data, insta_data = fetch_instagram_data(token)

        page_id = page_data["id"]
        insta_id = insta_data["id"]

        # ✅ Étape 3 : stockage dans Supabase
        supabase.table("clients").insert({
            "access_token": token,
            "page_id": page_id,
            "page_name": page_data.get("name", ""),
            "instagram_id": insta_id,
            "instagram_username": insta_data.get("username", ""),
            "client_email": email
        }).execute()

        # ✅ Étape 4 : notifications
        confirmation = f"Page : {page_data.get('name', '')}\nIG : {insta_data.get('username', '')}\nEmail : {email}"
        send_email(ADMIN_EMAIL, "✅ Nouveau client lié", confirmation)

        # ✅ Étape 5 : redirection finale vers la page du site
        return redirect(
            f"{BASE_REDIRECT_URL}?success=1&page={page_data.get('name','')}&ig={insta_data.get('username','')}"
        )

    except Exception as e:
        msg = f"Erreur post-OAuth : {str(e)}"
        send_email(ADMIN_EMAIL, "❌ Échec post-OAuth", msg)
        return msg


if __name__ == "__main__":
    app.run()
