import os
import logging
import aiohttp
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
from bs4 import BeautifulSoup
import urllib.parse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Source configurations
SOURCES = [
    {
        "name": "Source 1",
        "base_url": "https://new3.scloud.ninja",
        "search_url": "{base_url}?search={query}",
    },
]

GROUP_LINK = "https://t.me/BASEMENT_GC"

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

async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if not query:
        return

    user = update.effective_user
    user_mention = f"[{user.first_name}](tg://user?id={user.id})"
    reply_to_message_id = update.message.message_id

    status_message = await update.message.reply_text(
        f"🔍 *Searching...* {user_mention}",
        parse_mode=ParseMode.MARKDOWN
    )

    async with aiohttp.ClientSession() as session:
        try:
            search_url = SOURCES[0]["search_url"].format(
                base_url=SOURCES[0]["base_url"],
                query=urllib.parse.quote(query)
            )
            
            async with session.get(search_url, timeout=10) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                results = []
                
                for result in soup.find_all('a', class_='block')[:5]:
                    title = result.text.strip()
                    href = result.get('href')
                    if href:
                        movie_url = f"{SOURCES[0]['base_url'].rstrip('/')}/{href.lstrip('/')}"
                        results.append((title, movie_url))

                if not results:
                    google_search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}+movie+download"
                    keyboard = [
                        [InlineKeyboardButton("🔍 Search on Google", url=google_search_url)],
                        [InlineKeyboardButton("🏠 Join Our Group", url=GROUP_LINK)]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=(
                            f"❌ *No results found!* {user_mention}\n\n"
                            "Try searching on Google or join our group for help."
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=reply_markup,
                        reply_to_message_id=reply_to_message_id
                    )
                    return

                keyboard = []
                for idx, (title, url) in enumerate(results):
                    keyboard.append([InlineKeyboardButton(f"🎬 {title}", callback_data=f"dl:{idx}")])
                
                keyboard.append([InlineKeyboardButton("🏠 Join Our Group", url=GROUP_LINK)])
                reply_markup = InlineKeyboardMarkup(keyboard)

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=(
                        f"*🎯 Search Results:* {user_mention}\n\n"
                        "Select a title to get the download link:"
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup,
                    reply_to_message_id=reply_to_message_id
                )

                context.user_data['search_results'] = results

        except Exception as e:
            logger.error(f"Search error: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    f"❌ *An error occurred* {user_mention}\n\n"
                    "Please try again later."
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply_to_message_id
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
                f"*🎯 Fetching download link...* {user_mention}",
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
                                download_url = f"{SOURCES[0]['base_url'].rstrip('/')}/{download_url.lstrip('/')}"

                            keyboard = [
                                [InlineKeyboardButton("⬇️ Download Now", url=download_url)],
                                [InlineKeyboardButton("🏠 Join Our Group", url=GROUP_LINK)]
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)

                            await context.bot.send_message(
                                chat_id=query.message.chat_id,
                                text=(
                                    f"*🎉 Download Ready!* {user_mention}\n\n"
                                    f"*Title:* `{title}`\n\n"
                                    f"*Click the button below to download:*"
                                ),
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=reply_markup,
                                reply_to_message_id=query.message.message_id
                            )
                        else:
                            google_search_url = f"https://www.google.com/search?q={urllib.parse.quote(title)}+movie+download"
                            keyboard = [
                                [InlineKeyboardButton("🔍 Search on Google", url=google_search_url)],
                                [InlineKeyboardButton("🏠 Join Our Group", url=GROUP_LINK)]
                            ]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            
                            await context.bot.send_message(
                                chat_id=query.message.chat_id,
                                text=(
                                    f"❌ *Download link not found* {user_mention}\n\n"
                                    "Try searching on Google or join our group for help."
                                ),
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=reply_markup,
                                reply_to_message_id=query.message.message_id
                            )

                except Exception as e:
                    logger.error(f"Download error: {e}")
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=(
                            f"❌ *Failed to fetch download link* {user_mention}\n\n"
                            "Please try again later."
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                        reply_to_message_id=query.message.message_id
                    )

    except Exception as e:
        logger.error(f"Selection error: {e}")

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    application.add_handler(CallbackQueryHandler(handle_result_selection, pattern="^dl:"))

    logger.info("@TheKnightFlix Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
