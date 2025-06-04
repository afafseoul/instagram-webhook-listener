from webhook import app
from threading import Thread
from watch_comments import watch_new_comments
from watch_posts import watch_new_posts

def launch():
    print("🚀 Lancement Commanda")
    
    # Lancer la détection des nouveaux posts
    thread_posts = Thread(target=watch_new_posts)
    thread_posts.daemon = True
    thread_posts.start()
    print("🟢 Thread watch_posts lancé")

    # Lancer la détection des nouveaux commentaires
    thread_comments = Thread(target=watch_new_comments)
    thread_comments.daemon = True
    thread_comments.start()
    print("🟢 Thread watch_comments lancé")

if __name__ == "__main__":
    launch()
    app.run(host="0.0.0.0", port=10000)
