from pathlib import Path

p = Path("/mnt/data/main.py")
text = """import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters,
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

FORCE_CHANNEL = os.getenv("FORCE_CHANNEL", "")
FORCE_CHANNEL_URL = os.getenv("FORCE_CHANNEL_URL", "")

DB = "movies.db"

conn = sqlite3.connect(DB, check_same_thread=False)
cur = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS movies (
    code TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    file_type TEXT NOT NULL
)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
''')
conn.commit()


# =========================
# RENDER PORT SERVER
# =========================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running!")

    def log_message(self, format, *args):
        return


def start_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"Render port: {port}")
    server.serve_forever()


# =========================
# USERLARNI SAQLASH
# =========================

def save_user(user_id):
    cur.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,)
    )
    conn.commit()


# =========================
# MAJBURIY A'ZOLIK
# =========================

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id == ADMIN_ID:
        return True

    if not FORCE_CHANNEL:
        return True

    try:
        member = await context.bot.get_chat_member(
            chat_id=FORCE_CHANNEL,
            user_id=user.id
        )
        if member.status in ["member", "administrator", "creator"]:
            return True
    except Exception as e:
        print("Subscription tekshirish xatosi:", e)

    keyboard = []

    if FORCE_CHANNEL_URL:
        keyboard.append([
            InlineKeyboardButton(
                "📢 Kanalga a'zo bo'lish",
                url=FORCE_CHANNEL_URL
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "✅ Tekshirish",
            callback_data="check_sub"
        )
    ])

    await update.effective_message.reply_text(
        "❗ Kino olish uchun avval kanalimizga a'zo bo'ling.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return False


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)

    await update.message.reply_text(
        "🎬 Kino botga xush kelibsiz!\\n\\n"
        "🔢 Kino kodini yuboring.\\n"
        "Bot sizga kinoni chiqarib beradi."
    )


# =========================
# MY ID
# =========================

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🆔 Sizning Telegram ID'ingiz:\\n\\n"
        f"{update.effective_user.id}"
    )


# =========================
# ADMIN PANEL
# =========================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz.")
        return

    keyboard = [
        [InlineKeyboardButton("🎬 Kino qo'shish", callback_data="add_movie")],
        [InlineKeyboardButton("🗑 Kino o'chirish", callback_data="delete_movie")],
        [InlineKeyboardButton("📋 Kinolar", callback_data="movie_list")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
    ]

    await update.message.reply_text(
        "👑 ADMIN PANEL\\n\\nKerakli bo'limni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# ADMIN BUTTONLARI
# =========================

async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("❌ Siz admin emassiz.")
        return

    action = query.data

    if action == "add_movie":
        context.user_data["admin_action"] = "waiting_movie"
        await query.edit_message_text(
            "🎬 KINO QO'SHISH\\n\\nMenga video yoki kino faylini yuboring."
        )

    elif action == "delete_movie":
        context.user_data["admin_action"] = "delete_movie"
        await query.edit_message_text(
            "🗑 Kino o'chirish\\n\\nO'chirmoqchi bo'lgan kino kodini yuboring."
        )

    elif action == "movie_list":
        cur.execute("SELECT code FROM movies ORDER BY code")
        movies = cur.fetchall()

        if not movies:
            text = "📋 Hozircha kinolar yo'q."
        else:
            text = "📋 KINOLAR:\\n\\n"
            for movie in movies:
                text += f"🎬 {movie[0]}\\n"

        keyboard = [[InlineKeyboardButton(
            "🔙 Admin panel", callback_data="back_admin"
        )]]

        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif action == "stats":
        cur.execute("SELECT COUNT(*) FROM movies")
        movie_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM users")
        user_count = cur.fetchone()[0]

        keyboard = [[InlineKeyboardButton(
            "🔙 Admin panel", callback_data="back_admin"
        )]]

        await query.edit_message_text(
            f"📊 STATISTIKA\\n\\n"
            f"👥 Foydalanuvchilar: {user_count}\\n"
            f"🎬 Kinolar: {movie_count}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif action == "back_admin":
        keyboard = [
            [InlineKeyboardButton("🎬 Kino qo'shish", callback_data="add_movie")],
            [InlineKeyboardButton("🗑 Kino o'chirish", callback_data="delete_movie")],
            [InlineKeyboardButton("📋 Kinolar", callback_data="movie_list")],
            [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
        ]

        await query.edit_message_text(
            "👑 ADMIN PANEL\\n\\nBo'limni tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif action == "check_sub":
        ok = await check_subscription(update, context)
        if ok:
            await query.edit_message_text(
                "✅ A'zolik tasdiqlandi!\\n\\nEndi kino kodini yuboring."
            )


# =========================
# ADMIN VIDEO QABUL QILISH
# =========================

async def receive_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    action = context.user_data.get("admin_action")
    if action != "waiting_movie":
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
    context.user_data["admin_action"] = "waiting_code"

    await update.message.reply_text(
        "✅ Kino qabul qilindi!\\n\\n"
        "🔢 Endi kino kodini yuboring.\\n\\n"
        "Masalan:\\n1234"
    )


# =========================
# TEXT
# =========================

async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if update.effective_user.id == ADMIN_ID:
        action = context.user_data.get("admin_action")

        if action == "waiting_code":
            if "file_id" not in context.user_data:
                return

            file_id = context.user_data.pop("file_id")
            file_type = context.user_data.pop("file_type")

            cur.execute(
                "INSERT OR REPLACE INTO movies VALUES (?, ?, ?)",
                (text, file_id, file_type)
            )
            conn.commit()

            context.user_data["admin_action"] = None

            await update.message.reply_text(
                f"✅ KINO SAQLANDI!\\n\\n"
                f"🎬 Kod: {text}\\n"
                f"📦 Turi: {file_type}"
            )
            return

        if action == "delete_movie":
            cur.execute(
                "SELECT code FROM movies WHERE code = ?", (text,)
            )
            movie = cur.fetchone()

            if not movie:
                await update.message.reply_text(
                    "❌ Bunday koddagi kino topilmadi."
                )
                return

            cur.execute("DELETE FROM movies WHERE code = ?", (text,))
            conn.commit()
            context.user_data["admin_action"] = None

            await update.message.reply_text(
                f"🗑 Kino o'chirildi!\\n\\n🔢 Kod: {text}"
            )
            return

    save_user(update.effective_user.id)

    if not await check_subscription(update, context):
        return

    cur.execute(
        "SELECT file_id, file_type FROM movies WHERE code = ?", (text,)
    )
    movie = cur.fetchone()

    if not movie:
        await update.message.reply_text(
            "❌ Bunday koddagi kino topilmadi."
        )
        return

    file_id, file_type = movie

    if file_type == "video":
        await update.message.reply_video(
            video=file_id, caption="🎬 FilmCreativ"
        )
    else:
        await update.message.reply_document(
            document=file_id, caption="🎬 FilmCreativ"
        )


# =========================
# MAIN
# =========================

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN topilmadi!")

    if not ADMIN_ID:
        raise ValueError("ADMIN_ID topilmadi!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(admin_buttons))

    app.add_handler(MessageHandler(
        filters.VIDEO | filters.Document.ALL,
        receive_movie
    ))

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        receive_text
    ))

    print("🤖 Bot ishga tushdi...")

    # Render Web Service portini ochish
    threading.Thread(
        target=start_web_server,
        daemon=True
    ).start()

    # Telegram botni polling orqali ishga tushirish
    app.run_polling()


if __name__ == "__main__":
    main()
"""

p.write_text(text, encoding="utf-8")
print(f"Тayyor: {p}")
