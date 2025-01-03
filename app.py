import os
import logging
from flask import Flask, request
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WORKER_URL = os.getenv("WORKER_URL")  # Cloudflare Worker URL for search
BASE_URL = os.getenv("BASE_URL")  # Direct base URL for final download link

# Set up logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app and Telegram bot
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)

@app.route("/")
def index():
    return "Bot is running!"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

def start(update, context):
    """Send a welcome message."""
    update.message.reply_text("Welcome to the Movie Bot! 🎬\nType a movie name to search.")

def search_movie(update, context):
    """Search for movies based on user input."""
    query = update.message.text.strip()
    chat_id = update.message.chat.id

    if not query:
        update.message.reply_text("❌ Please enter a valid movie name.")
        return

    # Send initial response
    bot.send_message(chat_id=chat_id, text=f"🔍 Searching for: {query}... Please wait.")

    # Query Cloudflare Worker for movie results
    try:
        response = requests.get(f"{WORKER_URL}?search={requests.utils.quote(query)}", timeout=10)
        if response.status_code != 200:
            raise Exception(f"Cloudflare Worker error: {response.status_code}")

        results = response.json()  # Expecting Worker to return JSON
        if not results:
            bot.send_message(chat_id=chat_id, text="❌ No results found. Try a different query.")
            return

        # Generate inline buttons for results
        keyboard = [
            [InlineKeyboardButton(movie["title"], callback_data=f"get_final:{movie['url']}")]
            for movie in results
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        bot.send_message(chat_id=chat_id, text="📽️ Search Results:", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error searching movies: {e}")
        bot.send_message(chat_id=chat_id, text="❌ An error occurred while fetching results. Please try again later.")

def get_final_url(update, context):
    """Fetch the final download URL from the base URL."""
    query = update.callback_query
    query.answer()

    # Extract the selected movie URL from callback data
    movie_url = query.data.split(":")[1]
    chat_id = query.message.chat.id

    # Notify the user
    bot.send_message(chat_id=chat_id, text="🔗 Fetching the final download link... Please wait.")

    # Fetch the final download URL
    try:
        response = requests.get(movie_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if response.status_code != 200:
            raise Exception(f"Base URL error: {response.status_code}")

        # Parse the final download URL (example parsing logic)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        download_button = soup.find("a", {"class": "fastdl"})
        if not download_button:
            bot.send_message(chat_id=chat_id, text="❌ Could not find the download link on the page.")
            return

        final_url = download_button["href"]
        bot.send_message(chat_id=chat_id, text=f"🎥 Your download link:\n{final_url}")
    except Exception as e:
        logger.error(f"Error fetching final URL: {e}")
        bot.send_message(chat_id=chat_id, text="❌ An error occurred while fetching the download link. Please try again later.")

def help_command(update, context):
    """Display help message."""
    update.message.reply_text(
        "Help Menu:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "Type any movie name to search."
    )

# Set up Telegram dispatcher
dispatcher = Dispatcher(bot, None, workers=4)
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, search_movie))
dispatcher.add_handler(CallbackQueryHandler(get_final_url, pattern="^get_final:"))

if __name__ == "__main__":
    # Set webhook for Render deployment
    WEBHOOK_URL = os.getenv("RENDER_WEBHOOK_URL")
    bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

    # Start Flask app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
