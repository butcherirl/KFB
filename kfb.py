import os
import logging
import aiohttp
import asyncio
from flask import Flask, request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
from bs4 import BeautifulSoup
import urllib.parse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Your Render URL

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Source configurations
SOURCES = [
    {
        "name": "Source 1",
        "base_url": "https://new3.scloud.ninja",
        "search_url": "{base_url}?search={query}",
    },
]

GROUP_LINK = "https://t.me/BASEMENT_GC"

# Initialize bot application
application = Application.builder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏠 Our Group", url=GROUP_LINK)],
        [InlineKeyboardButton("🔍 Search Movie", switch_inline_query_current_chat="")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "🎬 *Welcome to @TheKnightFlix Bot* 🎥\n\n"
        "Your Ultimate Movie & Series Companion!\n\n"
        "🔍 Just type any movie/series name to begin!\n\n"
        "🌟 *Powered by @TheKnightFlix*"
    )
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

# [Previous handlers remain exactly the same]
# Copy all your existing handlers (search_movie, handle_result_selection) here
# They remain unchanged

def setup_handlers():
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    application.add_handler(CallbackQueryHandler(handle_result_selection, pattern="^dl:"))

# Webhook route
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook_handler():
    """Handle incoming updates from Telegram."""
    if request.method == "POST":
        await application.update_queue.put(Update.de_json(request.get_json(), application.bot))
        return Response("OK", status=200)
    return Response("Method not allowed", status=405)

# Health check route
@app.route("/")
def health_check():
    return "Bot is running!"

async def setup_webhook():
    """Set up webhook for the bot."""
    webhook_url = f"{WEBHOOK_URL}/{BOT_TOKEN}"
    await application.bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook set to {webhook_url}")

if __name__ == "__main__":
    setup_handlers()
    
    # Set up webhook
    asyncio.run(setup_webhook())
    
    # Start Flask server
    port = int(os.environ.get("PORT", 8443))
    app.run(host="0.0.0.0", port=port)
