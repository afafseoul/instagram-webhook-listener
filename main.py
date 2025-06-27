from flask import Flask, request
import requests
import os
import psycopg2
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
META_APP_ID = os.environ.get("META_APP_ID")
META_APP_SECRET = os.environ.get("META_APP_SECRET")
FROM_EMAIL = os.environ.get("GMAIL_FROM")
TO_EMAIL = os.environ.get("GMAIL_TO")
EMAIL_PASSWORD = os.environ.get("GMAIL_PASS")
DATABASE_URL = os.environ.get("DATABASE_URL")

def send_email(subject, body):
    try:
        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["From"] = formataddr(("Commanda", FROM_EMAIL))
        msg["To"] = TO_EMAIL

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(FROM_EMAIL, EMAIL_PASSWORD)
            server.sendmail(FROM_EMAIL, TO_EMAIL, msg.as_string())
    except Exception as e:
        print("Erreur lors de l'envoi de l'email :", e)

def store_in_supabase(page_id, page_name, instagram_id):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO instagram_tokens (page_id, page_name, instagram_id, created_at)
            VALUES (%s, %s, %s, %s)
        """, (page_id, page_name, instagram_id, datetime.utcnow()))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        send_email("❌ Échec DB Supabase", f"Erreur lors de l'enregistrement du token IG : {e}")

@app.route("/callback")
def callback():
    code = request.args.get("code")

    if not code:
        return "<h2 style='color:red'>❌ Erreur : Code OAuth manquant</h2>", 400

    try:
        # Obtenir token d'accès
        token_resp = requests.get("https://graph.facebook.com/v19.0/oauth/access_token", params={
            "client_id": META_APP_ID,
            "redirect_uri": "https://instagram-webhook-listener.onrender.com/callback",
            "client_secret": META_APP_SECRET,
            "code": code
        }).json()

        access_token = token_resp.get("access_token")
        if not access_token:
            send_email("❌ Échec post-OAuth", f"Réponse token invalide : {token_resp}")
            return "<h2 style='color:red'>❌ Erreur : Token d'accès non reçu</h2>", 400

        # Obtenir pages
        pages_resp = requests.get("https://graph.facebook.com/v19.0/me/accounts", params={
            "access_token": access_token
        }).json()
        pages = pages_resp.get("data", [])

        if not pages:
            send_email("❌ Échec post-OAuth", "Aucune page récupérée. L'utilisateur n'est peut-être pas admin.")
            return "<h2 style='color:red'>❌ Aucune page Facebook trouvée</h2>", 400

        page = pages[0]
        page_id = page["id"]
        page_name = page.get("name", "Page inconnue")

        # Obtenir IG ID
        ig_resp = requests.get(f"https://graph.facebook.com/v19.0/{page_id}", params={
            "fields": "connected_instagram_account",
            "access_token": access_token
        }).json()
        ig_account = ig_resp.get("connected_instagram_account", {})
        ig_id = ig_account.get("id")

        if not ig_id:
            send_email("❌ Échec IG", f"La page <b>{page_name}</b> n'a pas de compte Instagram relié.")
            return f"<h2 style='color:red'>❌ Aucun compte Instagram lié à <b>{page_name}</b></h2>", 400

        # Stocker
        store_in_supabase(page_id, page_name, ig_id)

        # Email succès
        send_email("✅ Nouveau token enregistré", f"""
        <h2>✅ Succès OAuth</h2>
        <ul>
          <li><b>Page</b> : {page_name}</li>
          <li><b>Instagram</b> : {ig_id}</li>
          <li><b>Page ID</b> : {page_id}</li>
        </ul>
        """)

        # Message client
        return f"""
        <h2 style='color:green'>✅ Connexion réussie</h2>
        <p><b>Page :</b> {page_name}</p>
        <p><b>Instagram :</b> {ig_id}</p>
        <p style='color:blue'>🟢 Enregistré + email envoyé</p>
        <a href='/'>Retour</a>
        """

    except Exception as e:
        send_email("❌ Erreur interne OAuth", f"<pre>{str(e)}</pre>")
        return "<h2 style='color:red'>❌ Erreur interne serveur</h2>", 500

if __name__ == "__main__":
    app.run(debug=True)
