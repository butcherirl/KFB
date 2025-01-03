import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from bs4 import BeautifulSoup
import urllib.parse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = "https://new3.scloud.ninja/"

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to the Movie Bot! 🎬\nType the name of the movie you want to search."
    )

# Search movie function
async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if not query:
        await update.message.reply_text("Please enter a valid movie name!")
        return

    await update.message.reply_text(f"🔍 Searching for: {query}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # Search for the movie
        search_url = f"{BASE_URL}?search={urllib.parse.quote(query)}"
        response = requests.get(search_url, headers=headers)
        if response.status_code != 200:
            raise ConnectionError(f"Failed to connect to {BASE_URL} (HTTP {response.status_code})")

        soup = BeautifulSoup(response.text, 'html.parser')
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
            if movie_response.status_code != 200:
                raise ConnectionError(f"Failed to connect to movie page: {movie_page_url}")

            movie_soup = BeautifulSoup(movie_response.text, 'html.parser')
            download_button = movie_soup.find('a', href=True, class_='block w-full')
            if not download_button:
                continue

            download_url = download_button['href']
            keyboard.append([InlineKeyboardButton(movie_title, url=download_url)])

        if not keyboard:
            await update.message.reply_text("❌ No valid download links found!")
            return

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📽️ Search Results (Top 7):",
            reply_markup=reply_markup
        )

    except ConnectionError as e:
        logger.error(f"Connection error: {e}")
        await update.message.reply_text(f"❌ Could not connect to the server. Error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await update.message.reply_text(f"❌ An unexpected error occurred: {str(e)}")

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Help Menu:\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "Type any movie name to search."
    )

# Main function
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))

    logger.info("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
