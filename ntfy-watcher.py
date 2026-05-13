import requests
import json
import time
import threading
import signal
import sys
from datetime import datetime
from winotify import Notification

# Change these as necessary
NTFY_URL = "http://100.109.107.116:5454"
TOPICS = ["test", "personal"]
RECONNECT_DELAY = 30


def handle_exit(sig, frame):
    print("\nExiting...")
    sys.exit(0)


def show_notification(title, body):
    try:
        toast = Notification(app_id="ntfy", title=title, msg=body, duration="short")
        toast.show()
    except Exception as e:
        print(e)


def format_notification(msg, topic):
    timestamp = datetime.fromtimestamp(msg.get("time", time.time())).strftime("%H:%M")
    title = msg.get("title") or f"ntfy / {topic}"
    if not msg.get("title"):
        # No title set, so include timestamp in title
        title = f"ntfy / {topic} @ {timestamp}"
    else:
        title = f"{msg['title']} — {topic} @ {timestamp}"
    body = msg.get("message", "")
    return title, body


def listen(topic):
    url = f"{NTFY_URL}/{topic}/json"
    print(f"Connecting to {url}...")
    disconnected = False
    while True:
        try:
            with requests.get(url, stream=True, timeout=None) as r:
                if disconnected:
                    threading.Thread(
                        target=show_notification,
                        args=(
                            "ntfy — Reconnected",
                            f"Connection to topic '{topic}' restored.",
                        ),
                        daemon=True,
                    ).start()
                    disconnected = False
                print(f"Connected to topic: {topic}")
                for line in r.iter_lines():
                    if line:
                        try:
                            msg = json.loads(line.decode("utf-8"))
                            if msg.get("event") == "message":
                                title, body = format_notification(msg, topic)
                                threading.Thread(
                                    target=show_notification,
                                    args=(title, body),
                                    daemon=True,
                                ).start()
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            print(f"Connection lost ({e}), reconnecting in {RECONNECT_DELAY}s...")
            if not disconnected:
                threading.Thread(
                    target=show_notification,
                    args=(
                        "ntfy — Connection Lost",
                        f"Lost connection to topic '{topic}'!",
                    ),
                    daemon=True,
                ).start()
                disconnected = True
            time.sleep(RECONNECT_DELAY)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    if len(TOPICS) == 1:
        listen(TOPICS[0])
    else:
        threads = [
            threading.Thread(target=listen, args=(t,), daemon=True) for t in TOPICS
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
