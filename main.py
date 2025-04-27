from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = "afafsecret123"

@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        else:
            return "Verification token mismatch", 403
    if request.method == "POST":
        data = request.json
        print("Received webhook:", data)
        return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
