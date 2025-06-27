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
    return redirect(
        f"https://www.facebook.com/v19.0/dialog/oauth?client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&response_type=code"
    )


@app.route("/callback")
def oauth_callback():
    print("✅ Requête reçue sur /callback")
    print("🔎 URL complète:", request.url)
    print("🔎 Paramètres GET:", dict(request.args))

    code = request.args.get("code")
    page = request.args.get("page")
    ig = request.args.get("ig")

    if not code:
        return "❌ Erreur : Code OAuth manquant"

    return f"""
        ✅ Code reçu : {code}<br>
        📄 Page : {page}<br>
        📸 IG : {ig}<br>
        🔁 Redirige manuellement vers : {BASE_REDIRECT_URL}?success=1&page={page}&ig={ig}
    """


if __name__ == "__main__":
    app.run()
