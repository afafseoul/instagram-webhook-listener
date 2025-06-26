import os
import requests

GRAPH_BASE = "https://graph.facebook.com/v19.0"
APP_ID = os.getenv("META_CLIENT_ID")
APP_SECRET = os.getenv("META_CLIENT_SECRET")


def graph_get(endpoint: str, params: dict) -> dict:
    url = f"{GRAPH_BASE}/{endpoint}"
    res = requests.get(url, params=params, timeout=10)
    data = res.json()
    if res.status_code != 200:
        msg = data.get("error", {}).get("message", "Unknown error")
        raise Exception(msg)
    return data


def get_long_token(code: str):
    try:
        redirect_uri = "https://instagram-webhook-listener.onrender.com/callback"
        params = {
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "redirect_uri": redirect_uri,
            "code": code,
        }

        print("🔁 Exchange code → short token...")
        data = graph_get("oauth/access_token", params)
        short_token = data.get("access_token")
        print("✅ short_token:", short_token)

        long_params = {
            "grant_type": "fb_exchange_token",
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "fb_exchange_token": short_token,
        }

        print("🔁 Exchange short → long token...")
        long_data = graph_get("oauth/access_token", long_params)
        token = long_data.get("access_token")
        expires_in = long_data.get("expires_in", 0)
        print(f"✅ long_token: {token} (expires_in={expires_in}s)")

        if int(expires_in) < 3600:
            raise Exception("Token trop court")

        me = graph_get("me", {"fields": "email", "access_token": token})
        email = me.get("email", "")
        return token, email, None

    except Exception as e:
        print("❌ get_long_token ERROR:", str(e))
        return None, None, str(e)


def verify_token_permissions(token: str) -> None:
    graph_get("me", {"fields": "id", "access_token": token})
    graph_get("me/accounts", {"access_token": token})


def fetch_instagram_data(token: str):
    pages = graph_get(
        "me/accounts",
        {"fields": "id,name,instagram_business_account", "access_token": token},
    ).get("data", [])
    if not pages:
        raise Exception("Aucune page accessible")

    page = pages[0]
    ig_acc = page.get("instagram_business_account")
    if not ig_acc:
        raise Exception("Page non liée à Instagram")
    ig_id = ig_acc["id"]
    ig_info = graph_get(ig_id, {"fields": "username", "access_token": token})
    return page, {"id": ig_id, "username": ig_info.get("username", "")}


def send_email(to: str, subject: str, body: str):
    key = os.getenv("MAILGUN_API_KEY")
    return requests.post(
        "https://api.mailgun.net/v3/sandbox.mailgun.org/messages",
        auth=("api", key),
        data={
            "from": "Commanda <mailgun@sandbox.mailgun.org>",
            "to": to,
            "subject": subject,
            "text": body,
        },
        timeout=10,
    )
