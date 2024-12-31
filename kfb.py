import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from bs4 import BeautifulSoup
import urllib.parse
import asyncio
import nest_asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Apply nest_asyncio to fix event loop issues
nest_asyncio.apply()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = "https://new3.scloud.ninja/"

# List of common abbreviations to ignore
COMMON_ABBREVIATIONS = [
    "plz", "gimme", "haven't", "wanna", "gonna", "lemme", "y'all", "ain't",
    "idk", "tbh", "brb", "omg", "btw", "lmk", "ikr", "fyi", "thx", "b/c", "np", "asap"
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Search Movies", callback_data='search')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome to the Movie Bot! 🎬\nUse the button below to search for movies.",
        reply_markup=reply_markup
    )

async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text

    # Ignore messages with more than 7 words
    if len(message.split()) > 7:
        return

    # Ignore messages containing links
    if "http://" in message or "https://" in message:
        return

    # Ignore messages starting with symbols or numbers
    if message[0].isdigit() or message[0] in "!@#$%^&*()-_=+[{]}\\|;:'\",<.>/?":
        return

    # Ignore messages containing common abbreviations
    if any(abbreviation in message.lower() for abbreviation in COMMON_ABBREVIATIONS):
        return

    # Ignore messages containing @handles
    if "@" in message:
        return

    await update.message.reply_text(f"🔍 Searching for: {message}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # First, search for the movie
        search_url = f"{BASE_URL}?search={urllib.parse.quote(message)}"
        response = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all result cards
        results = soup.find_all('a', class_='block')
        if not results:
            await update.message.reply_text("❌ No movies found!")
            return

        keyboard = []
        for idx, result in enumerate(results[:7]):  # Limit to first 7 results
            result_card = result.find('div', class_='result-card rounded-lg p-4')
            if not result_card:
                continue

            title_div = result_card.find('div', class_='mb-3')
            if not title_div:
                continue

            movie_title = title_div.text.strip()
            movie_href = result['href']
            movie_page_url = f"{BASE_URL}{movie_href}"

            # Fetch the download link from the movie page
            movie_response = requests.get(movie_page_url, headers=headers)
            movie_soup = BeautifulSoup(movie_response.text, 'html.parser')
            download_button = movie_soup.find('a', href=True, class_='block w-full')
            if not download_button:
                continue

            download_url = download_button['href']
            keyboard.append([InlineKeyboardButton(movie_title, url=download_url)])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📽️ Search Results (Top 7):",
            reply_markup=reply_markup
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Error occurred: {str(e)}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Help Menu:\n" 
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "Type any movie name to search."
    )

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
