import os
import time
from datetime import datetime, timezone
from config import REPLIES_DIR


def get_uptime(start_time: float) -> str:
    seconds = int(time.time() - start_time)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"


def load_replies():
    replies = {}

    if not os.path.exists(REPLIES_DIR):
        return replies

    for filename in os.listdir(REPLIES_DIR):
        if filename.endswith(".md"):
            filepath = os.path.join(REPLIES_DIR, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().split("---")
                if len(content) >= 2:
                    summary_line = content[0].strip().splitlines()[0]
                    reply_text = content[1].strip()
                    command_name = filename[:-3]
                    replies[command_name] = (summary_line, reply_text)
    return replies


def log_to_file(entry: str, log_file: str):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} - {entry}\n")


def clean_message_content(content: str) -> str:
    invisible_chars = ["\u200b", "\u200c", "\u200d", "\u200e", "\u200f"]
    cleaned_content = content
    for ch in invisible_chars:
        cleaned_content = cleaned_content.replace(ch, "")
    return cleaned_content.strip()