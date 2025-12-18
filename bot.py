import os
import requests
from pymongo import MongoClient
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ================= CONFIG =================

BOT_TOKEN = "8504701481:AAEI5vYill3F-JlcKWT4YnB9hrxA1_Bu0Yk"
CHANNEL_ID = -1003593747739        # PRIVATE CHANNEL ID
MONGO_URI = "mongodb+srv://prathmeshcoder69_db_user:M0XsgeHY4bnf90ta@cluster0.ngbpudu.mongodb.net/?appName=Cluster0"

MAX_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ================= DATABASE =================

client = MongoClient(MONGO_URI)
db = client["telegram_video_bot"]
videos = db["videos"]

# ================= BOT =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📥 Send a direct video link (max 2GB).\n"
        "I will save it to the private channel."
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not url.startswith("http"):
        await update.message.reply_text("❌ Invalid link.")
        return

    # Check MongoDB (avoid duplicate)
    existing = videos.find_one({"original_url": url})
    if existing:
        await update.message.reply_text("♻️ Already saved. Sending video...")
        await context.bot.send_video(
            chat_id=update.effective_chat.id,
            video=existing["telegram_file_id"]
        )
        return

    await update.message.reply_text("🔍 Checking file size...")

    try:
        head = requests.head(url, allow_redirects=True, timeout=20)
        size = int(head.headers.get("Content-Length", 0))

        if size == 0:
            await update.message.reply_text("⚠️ Cannot detect file size.")
        elif size > MAX_SIZE:
            await update.message.reply_text("❌ File is larger than 2GB.")
            return

        await update.message.reply_text("⬇️ Downloading video...")

        file_path = os.path.join(DOWNLOAD_DIR, "video.mp4")

        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            downloaded = 0
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        downloaded += len(chunk)
                        if downloaded > MAX_SIZE:
                            f.close()
                            os.remove(file_path)
                            await update.message.reply_text("❌ File exceeded 2GB while downloading.")
                            return
                        f.write(chunk)

        await update.message.reply_text("⬆️ Uploading to private channel...")

        with open(file_path, "rb") as video:
            msg = await context.bot.send_video(
                chat_id=CHANNEL_ID,
                video=video
            )

        # Save to MongoDB
        videos.insert_one({
            "original_url": url,
            "telegram_file_id": msg.video.file_id,
            "message_id": msg.message_id,
            "channel_id": CHANNEL_ID
        })

        # Send to user
        await context.bot.send_video(
            chat_id=update.effective_chat.id,
            video=msg.video.file_id
        )

        await update.message.reply_text("✅ Video saved successfully!")

        os.remove(file_path)

    except Exception as e:
        await update.message.reply_text(f_
