import threading
from watch_posts import watch_new_posts
from watch_comments import watch_new_comments
from keep_alive import keep_alive
from webhook import app

def start_webhook():
    app.run(host='0.0.0.0', port=10000)

if __name__ == '__main__':
    print("🚀 Lancement Commanda")
    threading.Thread(target=watch_new_posts).start()
    threading.Thread(target=watch_new_comments).start()
    threading.Thread(target=keep_alive).start()
    threading.Thread(target=start_webhook).start()
