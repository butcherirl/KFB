import os
import logging
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
from bs4 import BeautifulSoup
import urllib.parse
import asyncio
import nest_asyncio
from flask import Flask, request
from dotenv import load_dotenv
import random

# Apply nest_asyncio
nest_asyncio.apply()

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # This is your render app URL

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Source configuration
SOURCE = {
    "base_url": "https://new3.scloud.ninja",
    "search_url": "{base_url}?search={query}",
}

LOADING_ANIMATIONS = ["⏳", "🔄", "🔍", "✨", "🎥"]

# Initialize Flask
app = Flask(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏠 Our Group", url="https://t.me/BASEMENT_GC")],
        [InlineKeyboardButton("🔍 Search Movie", switch_inline_query_current_chat="")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        "🎬 *Welcome to @TheKnightFlix Bot* 🎥\n\n"
        "Your Ultimate Movie & Series Companion!\n\n"
        "🔍 Just type any movie/series name to begin!\n\n"
        "🌟 *Powered by @TheKnightFlix*"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if not query:
        return
    user = update.effective_user
    user_mention = f"[{user.first_name}](tg://user?id={user.id})"
    reply_to_message_id = update.message.message_id
    animation = random.choice(LOADING_ANIMATIONS)
    status_message = await update.message.reply_text(
        f"{animation} *Searching for:* `{query}`\n{user_mention}",
        parse_mode=ParseMode.MARKDOWN,
        reply_to_message_id=reply_to_message_id
    )
    try:
        search_url = SOURCE["search_url"].format(
            base_url=SOURCE["base_url"],
            query=urllib.parse.quote(query)
        )

        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, timeout=10) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                results = []

                for result in soup.find_all('a', class_='block')[:5]:
                    result_card = result.find('div', class_='result-card rounded-lg p-4')
                    if not result_card:
                        continue
                    title_div = result_card.find('div', class_='mb-3')
                    if not title_div:
                        continue
                    movie_title = title_div.text.strip()
                    movie_href = result['href']
                    movie_url = f"{SOURCE['base_url']}{movie_href}"
                    results.append((movie_title, movie_url))
                if not results:
                    google_search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}+movie+download"
                    keyboard = [
                        [InlineKeyboardButton("🔍 Search on Google", url=google_search_url)],
                        [InlineKeyboardButton("🏠 Join Our Group", url="https://t.me/BASEMENT_GC")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    await status_message.edit_text(
                        f"❌ *No results found!* {user_mention}\n\n"
                        "Try searching on Google or join our group for help.",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup
                    )
                    return
                keyboard = []
                for idx, (title, url) in enumerate(results):
                    keyboard.append([InlineKeyboardButton(f"🎬 {title}", callback_data=f"dl:{idx}")])
                keyboard.append([InlineKeyboardButton("🏠 Join Our Group", url="https://t.me/BASEMENT_GC")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await status_message.edit_text(
                    f"🎯 *Found {len(results)} results* {user_mention}\n\n"
                    "Select a movie to get the download link:",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                context.user_data['search_results'] = results
    except Exception as e:
        logger.error(f"Search error: {e}")
        await status_message.edit_text(
            f"❌ *An error occurred* {user_mention}\n\n"
            "Please try again later.",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_result_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        _, selected_idx = query.data.split(":")
        selected_num = int(selected_idx)
        results = context.user_data.get('search_results', [])

        if 0 <= selected_num < len(results):
            title, url = results[selected_num]
            user = query.from_user
            user_mention = f"[{user.first_name}](tg://user?id={user.id})"
            status_message = await query.edit_message_text(
                f"🎯 *Fetching download link...* {user_mention}",
                parse_mode=ParseMode.MARKDOWN
            )
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url, timeout=10) as response:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        download_button = soup.find('a', href=True, class_='block w-full')
                        if download_button:
                            download_url = download_button['href']
                            if not download_url.startswith("http"):
                                download_url = f"{SOURCE['base_url'].rstrip('/')}/{download_url.lstrip('/')}"
                            keyboard = [
                                [InlineKeyboardButton("⬇️ Download Now", url=download_url)],
                                [InlineKeyboardButton("🏠 Join Our Group", url="https://t.me/BASEMENT_GC")]
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            await status_message.edit_text(
                                f"*🎉 Download Ready!* {user_mention}\n\n"
                                f"*Title:* `{title}`\n\n"
                                f"*Click the button below to download:*",
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=reply_markup
                            )
                        else:
                            google_search_url = f"https://www.google.com/search?q={urllib.parse.quote(title)}+movie+download"
                            keyboard = [
                                [InlineKeyboardButton("🔍 Search on Google", url=google_search_url)],
                                [InlineKeyboardButton("🏠 Join Our Group", url="https://t.me/BASEMENT_GC")]
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)

                            await status_message.edit_text(
                                f"❌ *Download link not found* {user_mention}\n\n"
                                "Try searching on Google or join our group for help.",
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=reply_markup
                            )
                except Exception as e:
                    logger.error(f"Download error: {e}")
                    await status_message.edit_text(
                        f"❌ *Failed to fetch download link* {user_mention}\n\n"
                        "Please try again later.",
                        parse_mode=ParseMode.MARKDOWN
                    )
    except Exception as e:
        logger.error(f"Selection error: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Help Menu:*\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "Type any movie name to search.",
        parse_mode=ParseMode.MARKDOWN
    )

async def setup_bot():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    application.add_handler(CallbackQueryHandler(handle_result_selection, pattern="^dl:"))

    try:
        await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
        logger.info(f"Webhook set to {WEBHOOK_URL}/webhook")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")

    return application

@app.route('/webhook', methods=['POST'])
async def telegram_webhook():
    application = await setup_bot()
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "OK", 200

@app.route('/', methods=['GET'])
def index():
    return "Bot is running!", 200

if __name__ == '__main__':
    asyncio.run(setup_bot())
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
