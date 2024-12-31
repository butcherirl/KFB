import os
import time
import asyncio
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import BadRequest
from dotenv import load_dotenv
from threading import Timer

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))  # Your Telegram user ID
ALLOWED_GROUPS = json.loads(os.getenv("ALLOWED_GROUPS", "[]"))  # List of allowed group IDs
BASE_URL = "https://new3.scloud.ninja/"
FILES_DB = "files.json"  # File metadata storage

# Create files DB if it doesn't exist
if not os.path.exists(FILES_DB):
    with open(FILES_DB, "w") as f:
        json.dump({}, f)

# Store files with expiry
async def auto_delete_file(context: ContextTypes.DEFAULT_TYPE, file_key):
    await asyncio.sleep(300)  # Wait 5 minutes
    with open(FILES_DB, "r+") as f:
        files = json.load(f)
        if file_key in files:
            del files[file_key]
            f.seek(0)
            json.dump(files, f)
            f.truncate()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if chat_id < 0 and chat_id not in ALLOWED_GROUPS and user_id != OWNER_ID:
        return

    if user_id == OWNER_ID:
        await update.message.reply_text(
            "Welcome, Owner! Use /upload to store files or /search to fetch links."
        )
    else:
        await update.message.reply_text(
            "Welcome! Use /search in allowed groups to fetch links."
        )

async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        return

    if not update.message.document:
        await update.message.reply_text("Please send a file to upload.")
        return

    file = await update.message.document.get_file()
    file_key = os.urandom(16).hex()

    with open(FILES_DB, "r+") as f:
        files = json.load(f)
        files[file_key] = {
            "file_id": file.file_id,
            "file_name": update.message.document.file_name,
            "expiry": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        }
        f.seek(0)
        json.dump(files, f)
        f.truncate()

    link = f"https://t.me/{context.bot.username}?start={file_key}"
    await update.message.reply_text(
        f"File uploaded successfully! Share this link: {link}\n\n"
        "The file will expire in 5 minutes. Forward it before it gets deleted."
    )

    context.application.create_task(auto_delete_file(context, file_key))

async def start_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = context.args[0] if context.args else None

    if not query:
        await update.message.reply_text("Invalid link.")
        return

    with open(FILES_DB, "r") as f:
        files = json.load(f)

    if query not in files:
        await update.message.reply_text("This file has expired or does not exist.")
        return

    file_data = files[query]
    await update.message.reply_document(
        InputFile(file_data["file_id"], filename=file_data["file_name"]),
        caption="Forward this file before it gets deleted!"
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id < 0 and chat_id not in ALLOWED_GROUPS and update.effective_user.id != OWNER_ID:
        return

    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Please provide a search query.")
        return

    await update.message.reply_text(f"Searching for: {query}")
    # Use the existing search logic here.

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Help Menu:\n" 
        "/start - Start the bot\n"
        "/upload - (Owner only) Upload a file\n"
        "/search <query> - Search for movie links\n"
        "Use the provided link to download uploaded files."
    )

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("upload", upload))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("start", start_link, filters=filters.COMMAND))

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
