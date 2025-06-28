import os
from datetime import datetime, timedelta
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


def get_long_token(code: str, redirect_uri: str):
    try:
        short_token = graph_get(
            "oauth/access_token",
            {
                "client_id": APP_ID,
                "client_secret": APP_SECRET,
                "redirect_uri": redirect_uri,
                "code": code,
            },
        ).get("access_token")

        long_data = graph_get(
            "oauth/access_token",
            {
                "grant_type": "fb_exchange_token",
                "client_id": APP_ID,
                "client_secret": APP_SECRET,
                "fb_exchange_token": short_token,
            },
        )
        token = long_data.get("access_token")
        exp = long_data.get("expires_in")
        expires_at = datetime.utcnow() + timedelta(seconds=exp) if exp else None
        return token, expires_at, None
    except Exception as e:
        return None, None, str(e)


def verify_token_permissions(token: str) -> None:
    system_token = os.getenv("META_SYSTEM_TOKEN") or f"{APP_ID}|{APP_SECRET}"
    debug = graph_get(
        "debug_token",
        {"input_token": token, "access_token": system_token},
    ).get("data", {})

    if not debug.get("is_valid"):
        raise Exception("Token invalide")

    scopes = debug.get("scopes", [])
    if "instagram_manage_comments" not in scopes:
        raise Exception("Permission instagram_manage_comments manquante")

    graph_get("me/accounts", {"access_token": token})


def fetch_instagram_data(token: str):
    accounts = graph_get(
        "me/accounts",
        {"access_token": token}
    ).get("data", [])

    if not accounts:
        raise Exception("Aucune page accessible")

    page = accounts[0]
    page_id = page.get("id")

    connected = graph_get(
        f"{page_id}",
        {"fields": "connected_instagram_account", "access_token": token}
    ).get("connected_instagram_account", {})

    insta_id = connected.get("id")
    insta_data = {}

    if insta_id:
        insta_data = graph_get(
            f"{insta_id}",
            {"fields": "id,username", "access_token": token}
        )

    return page, insta_data


def send_email(to: str, subject: str, body: str):
    key = os.getenv("MAILGUN_API_KEY")
    domain = os.getenv("MAILGUN_DOMAIN")
    return requests.post(
        f"https://api.mailgun.net/v3/{domain}/messages",
        auth=("api", key),
        data={
            "from": f"Commanda <bot@{domain}>",
            "to": to,
            "subject": subject,
            "text": body,
        },
        timeout=10,
    )
