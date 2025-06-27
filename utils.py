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


def verify_token_permissions(token: str) -> None:
    # Vérifie qu’on a les accès de base
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
