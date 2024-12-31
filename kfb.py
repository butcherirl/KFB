import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from bs4 import BeautifulSoup
import urllib.parse
import asyncio
import nest_asyncio
from dotenv import load_dotenv
import random

# Load environment variables
load_dotenv()

# Apply nest_asyncio to fix event loop issues
nest_asyncio.apply()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Sources
SOURCES = [
    {
        "base_url": "https://new3.scloud.ninja",
        "search_url": "{base_url}?search={query}",
        "process_results": "process_source1_results",
    },
    {
        "base_url": "https://www.oomoye.life",
        "search_url": "{base_url}/search.php?q={query}",
        "process_results": "process_source2_results",
    },
    {
        "base_url": "https://katmoviehd.nexus",
        "search_url": "{base_url}/?s={query}",
        "process_results": "process_source3_results",
    },
]

ANIMATIONS = ["⏳", "🔄", "🔍", "✨", "🎥"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Search Movies", callback_data='search')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome to the Ultimate Movie Bot! 🎬\nUse the button below to search for movies.",
        reply_markup=reply_markup
    )

async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    animation = random.choice(ANIMATIONS)
    await update.message.reply_text(f"{animation} Searching for: {message} \n Please wait...")

    query = urllib.parse.quote(message)
    for source in SOURCES:
        try:
            search_url = source["search_url"].format(base_url=source["base_url"], query=query)
            response = requests.get(search_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Call the appropriate processing function for the source
            process_func = globals()[source["process_results"]]
            results = await process_func(soup, context)

            if results:
                keyboard = [
                    [InlineKeyboardButton(title, url=url)] for title, url in results[:7]
                ]
                keyboard.append([InlineKeyboardButton("Search Another Source 🔄", callback_data=f"search_next:{query}")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    "📽️ Search Results:",
                    reply_markup=reply_markup
                )
                return
        except Exception as e:
            print(f"Error fetching from {source['base_url']}: {e}")

    await update.message.reply_text("❌ No movies found across all sources.")

async def process_source1_results(soup, context):
    results = []
    for result in soup.find_all('a', class_='block'):
        result_card = result.find('div', class_='result-card rounded-lg p-4')
        if not result_card:
            continue
        title_div = result_card.find('div', class_='mb-3')
        if not title_div:
            continue
        movie_title = title_div.text.strip()
        movie_href = result['href']
        movie_url = f"https://new3.scloud.ninja{movie_href}"
        results.append((movie_title, movie_url))
    return results

async def process_source2_results(soup, context):
    results = []
    for result in soup.find_all('a', title=True):
        title = result.text.strip()
        href = result['href']
        results.append((title, href))
    return results

async def process_source3_results(soup, context):
    results = []
    for result in soup.find_all('a', title=True)[:3]:
        title = result['title']
        href = result['href']
        results.append((title, href))
    return results

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data.startswith("search_next:"):
        search_term = data.split(":")[1]

        # Delete the previous two messages
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id - 1)
        except Exception as e:
            print(f"Error deleting messages: {e}")

        # Send a new wait message with updated animation
        new_animation = random.choice(ANIMATIONS)
        wait_message = await context.bot.send_message(
            chat_id=chat_id,
            text=f"{new_animation} Searching in the next source for: {search_term} \n Please wait..."
        )

        # Simulate searching in the next source
        await asyncio.sleep(2)

        # Proceed with the next source search
        await search_movie(update, context)

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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    application.add_handler(CommandHandler("search", search_movie))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
