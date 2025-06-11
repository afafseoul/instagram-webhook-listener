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

