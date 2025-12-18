import os
import requests
from pymongo import MongoClient
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ================= CONFIG =================

BOT_TOKEN = "8504701481:AAEI5vYill3F-JlcKWT4YnB9hrxA1_Bu0Yk"
CHANNEL_ID = -1003593747739   # PRIVATE CHANNEL ID (number, no quotes)
MONGO_URI = "mongodb+srv://prathmeshcoder69_db_user:M0XsgeHY4bnf90ta@cluster0.ngbpudu.mongodb.net/?appName=Cluster0"

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ================ DATABASE =================

client = MongoClient(MONGO_URI)
db = client["telegram_video_bot"]
videos = db["videos"]

# ================ BOT HANDLERS ================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📥 Send me a DIRECT video download link.\n"
        "I will save it to the private channel."
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not url.startswith("http"):
        await update.message.reply_text("❌ Please send a valid video link.")
        return

    # Check if already exists
    existing = videos.find_one({"original_url": url})
    if existing:
        await update.message.reply_text("♻️ Video already saved. Sending again...")
        await context.bot.send_video(
            chat_id=update.effective_chat.id,
            video=existing["telegram_file_id"]
        )
        return

    await update.message.reply_text("⬇️ Downloading video...")

    file_path = os.path.join(DOWNLOAD_DIR, "video.mp4")

    try:
        # Download video
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

        await update.message.reply_text("⬆️ Uploading to private channel...")

        # Upload to private channel
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
        await update.message.reply_text(f"❌ Error: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)

# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
