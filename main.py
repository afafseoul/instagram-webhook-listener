from flask import Flask, request, redirect
import os
from supabase import create_client
from utils import (
    verify_token_permissions,
    fetch_instagram_data,
    get_long_token,
    send_email,
)

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
BASE_REDIRECT_URL = os.getenv("BASE_REDIRECT_URL")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


@app.route("/oauth")
def oauth_start():
    client_id = os.getenv("META_CLIENT_ID")
    redirect_uri = os.getenv("BASE_REDIRECT_URL")
    scope = ",".join([
        "pages_show_list",
        "instagram_basic",
        "instagram_manage_comments",
        "pages_manage_metadata",
        "pages_read_engagement"
    ])
    print("🔁 Redirection vers Meta OAuth")
    return redirect(
        f"https://www.facebook.com/v19.0/dialog/oauth?client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&response_type=code"
    )


@app.route("/callback")
def oauth_callback():
    code = request.args.get("code")
    if not code:
        print("❌ Aucun code reçu")
        return "❌ Erreur : Code OAuth manquant"

    print(f"✅ Code reçu : {code}")

    redirect_uri = os.getenv("BASE_REDIRECT_URL")
    token, expires_at, error = get_long_token(code, redirect_uri)

    if error:
        print("❌ Erreur lors de la récupération du token :", error)
        send_email(ADMIN_EMAIL, "❌ Échec OAuth", error)
        return error

    print(f"✅ Token récupéré : {token[:60]}... (expire à {expires_at})")

    try:
        print("🔐 Vérification des permissions du token...")
        verify_token_permissions(token)

        print("📦 Récupération des données page et Instagram...")
        page_data, insta_data = fetch_instagram_data(token)

        page_id = page_data.get("id", "None")
        page_name = page_data.get("name", "None")
        insta_id = insta_data.get("id", "None")
        username = insta_data.get("username", "None")

        print(f"📄 Page : {page_name} ({page_id})")
        print(f"📸 IG : {username} ({insta_id})")

        print("💾 Insertion dans Supabase...")
        supabase.table("instagram_tokens").insert({
            "access_token": token,
            "token_expires_at": expires_at.isoformat() if expires_at else None,
            "page_id": page_id,
            "page_name": page_name,
            "instagram_id": insta_id,
            "instagram_username": username,
            "status_verified": True,
        }).execute()

        send_email(
            ADMIN_EMAIL,
            "✅ Nouveau token client",
            f"📄 Token long terme :\n{token}\n\nExpire le : {expires_at}\n\nPage : {page_name}\nIG : {username}"
        )

        print("✅ Redirection finale réussie")
        return redirect(f"{BASE_REDIRECT_URL}?success=1&page={page_name}&ig={username}")

    except Exception as e:
        msg = f"❌ Erreur post-OAuth : {str(e)}"
        print(msg)
        send_email(ADMIN_EMAIL, "❌ Échec post-OAuth", msg)
        return msg


if __name__ == "__main__":
    app.run()
