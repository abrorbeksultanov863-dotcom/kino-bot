import os
import sqlite3
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DB = "movies.db"

conn = sqlite3.connect(DB, check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS movies (
    code TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    file_type TEXT NOT NULL
)
""")
conn.commit()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Kino botga xush kelibsiz!\n\n"
        "Kino kodini yuboring va bot sizga kinoni chiqarib beradi."
    )


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Sizning Telegram ID'ingiz:\n{update.effective_user.id}"
    )


async def receive_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if update.message.video:
        file_id = update.message.video.file_id
        file_type = "video"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"
    else:
        return

    context.user_data["file_id"] = file_id
    context.user_data["file_type"] = file_type

    await update.message.reply_text(
        "✅ Kino qabul qilindi.\n\n"
        "🔢 Endi kino kodini yuboring.\n"
        "Masalan: 1234"
    )


async def receive_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # Admin kino kodini saqlayapti
    if update.effective_user.id == ADMIN_ID:
        if "file_id" in context.user_data:
            file_id = context.user_data.pop("file_id")
            file_type = context.user_data.pop("file_type")

            cur.execute(
                "INSERT OR REPLACE INTO movies VALUES (?, ?, ?)",
                (text, file_id, file_type)
            )
            conn.commit()

            await update.message.reply_text(
                f"✅ Kino saqlandi!\n\n"
                f"🔢 Kodi: {text}"
            )
            return

    # Oddiy foydalanuvchi kino qidirmoqda
    cur.execute(
        "SELECT file_id, file_type FROM movies WHERE code = ?",
        (text,)
    )
    movie = cur.fetchone()

    if not movie:
        await update.message.reply_text(
            "❌ Bunday koddagi kino topilmadi."
        )
        return

    file_id, file_type = movie

    if file_type == "video":
        await update.message.reply_video(video=file_id)
    else:
        await update.message.reply_document(document=file_id)


def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN topilmadi!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))

    app.add_handler(
        MessageHandler(
            filters.VIDEO | filters.Document.ALL,
            receive_movie
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receive_code
        )
    )

    print("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
