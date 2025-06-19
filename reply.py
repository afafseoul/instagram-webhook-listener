import os
from typing import Dict

import requests


def reply_to_comment(comment_id: str, message: str) -> Dict:
    """Reply to a given Instagram comment via the Meta Graph API.

    Parameters
    ----------
    comment_id: str
        The ID of the comment to reply to.
    message: str
        The reply message.

    Returns
    -------
    dict
        Parsed JSON response from the Meta API.
    """

    access_token = os.getenv("META_SYSTEM_TOKEN")
    if not access_token:
        raise RuntimeError("META_SYSTEM_TOKEN environment variable is not set")

    url = f"https://graph.facebook.com/v19.0/{comment_id}/replies"
    payload = {"message": message, "access_token": access_token}

    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Request to Meta API failed: {exc}") from exc


def send_to_make_webhook(post_data: Dict, webhook_url: str) -> None:
    """Send post data to the provided Make.com webhook."""
    if not webhook_url:
        raise RuntimeError("Webhook URL is missing")

    try:
        response = requests.post(webhook_url, json=post_data)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to send data to Make webhook: {exc}") from exc

