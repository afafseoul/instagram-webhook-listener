from flask import Flask, request, render_template_string
import requests
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
META_CLIENT_ID = os.getenv('META_CLIENT_ID')
META_CLIENT_SECRET = os.getenv('META_CLIENT_SECRET')
META_REDIRECT_URI = os.getenv('META_REDIRECT_URI')
SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


EMAIL_TO = 'ad@wwwjeneveuxpastravailler.com'


def send_email(subject: str, body: str) -> None:
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = EMAIL_TO
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [EMAIL_TO], msg.as_string())
    except Exception as exc:
        print(f"Cannot send email: {exc}")


def graph_get(endpoint: str, params: dict) -> dict:
    url = f"https://graph.facebook.com/v19.0/{endpoint}"
    resp = requests.get(url, params=params, timeout=10)
    data = resp.json()
    if resp.status_code != 200:
        message = data.get('error', {}).get('message', 'Unknown error')
        raise Exception(message)
    return data


@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return 'Missing code', 400

    try:
        # Exchange code for short-lived token
        token_params = {
            'client_id': META_CLIENT_ID,
            'redirect_uri': META_REDIRECT_URI,
            'client_secret': META_CLIENT_SECRET,
            'code': code,
        }
        data = graph_get('oauth/access_token', token_params)
        short_token = data.get('access_token')

        if not short_token:
            raise Exception('No access token returned')

        # Exchange for long-lived token
        long_params = {
            'grant_type': 'fb_exchange_token',
            'client_id': META_CLIENT_ID,
            'client_secret': META_CLIENT_SECRET,
            'fb_exchange_token': short_token,
        }
        long_token_data = graph_get('oauth/access_token', long_params)
        access_token = long_token_data.get('access_token')
        expires_in = int(long_token_data.get('expires_in', 0))

        if not access_token or expires_in < 3600:
            raise Exception('Long-lived token not obtained')

        # Get page and instagram info
        accounts = graph_get('me/accounts', {
            'fields': 'id,name,instagram_business_account',
            'access_token': access_token,
        }).get('data', [])

        if not accounts:
            raise Exception('No Facebook page available')

        page = accounts[0]
        page_id = page['id']
        page_name = page.get('name', '')
        ig_account = page.get('instagram_business_account')
        if not ig_account:
            raise Exception('Page not linked to Instagram')
        ig_id = ig_account['id']

        ig_info = graph_get(ig_id, {
            'fields': 'username',
            'access_token': access_token,
        })
        ig_username = ig_info.get('username', '')

        # Permission checks
        graph_get('me', {'fields': 'id,name', 'access_token': access_token})
        graph_get(f'{ig_id}/media', {'limit': 1, 'access_token': access_token})
        graph_get(f'{page_id}', {'fields': 'access_token', 'access_token': access_token})

        # Store in Supabase
        supabase.table('connected_pages').insert({
            'page_id': page_id,
            'page_name': page_name,
            'ig_id': ig_id,
            'ig_username': ig_username,
            'token': access_token,
        }).execute()

        subject = '🚀 Nouvelle connexion réussie'
        body = (f"🚀 Nouvelle connexion réussie\n"
                f"- Page Facebook : {page_name}\n"
                f"- ID : {page_id}\n"
                f"- Compte Instagram : @{ig_username} (ID: {ig_id})")
        send_email(subject, body)

        html = f"""<h2>Connexion réussie</h2>
<p>Page Facebook : {page_name}<br>Instagram : @{ig_username}</p>"""
        return render_template_string(html)

    except Exception as exc:
        message = str(exc)
        try:
            user = graph_get('me', {'fields': 'name', 'access_token': access_token})
            user_name = user.get('name', '')
        except Exception:
            user_name = ''
        send_email(
            '❌ Erreur de connexion OAuth',
            f"❌ Erreur de connexion OAuth\n- message : {message}\n- Page Facebook détectée : {page_name if 'page_name' in locals() else ''}\n- Utilisateur Facebook : {user_name}"
        )
        return render_template_string(f"<h2>Erreur : {message}</h2>"), 400


if __name__ == '__main__':
    app.run()
