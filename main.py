from flask import Flask
from webhook import webhook_bp

app = Flask(__name__)
app.register_blueprint(webhook_bp)

if __name__ == "__main__":
    print("✅ Flask Webhook Test lancé")
    app.run(host='0.0.0.0', port=10000)
