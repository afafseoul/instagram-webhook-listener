from flask import Flask, request, Response
import requests

app = Flask(__name__)

VERIFY_TOKEN = "afasecret123"  # Remplace par ton token de vérification choisi
MAKE_WEBHOOK_URL = "https://hook.make.com/xxxxxxxxxxxxxx"  # Remplace par ton lien Make

@app.route("/", methods=["GET", "POST", "HEAD"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return Response(request.args.get("hub.challenge"), status=200)
        else:
            return Response("Verification token mismatch", status=403)

    elif request.method == "POST":
        data = request.json
        print("Received webhook:", data)
        requests.post(MAKE_WEBHOOK_URL, json=data)
        return Response("OK", status=200)

    elif request.method == "HEAD":
        return Response(status=200)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
