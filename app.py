import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import aiohttp
from bs4 import BeautifulSoup
import urllib.parse
from cachetools import TTLCache

# Configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = "https://new3.scloud.ninja"
RESULTS_PER_PAGE = 5
PORT = int(os.environ.get("PORT", "8080"))

# Cache setup
search_cache = TTLCache(maxsize=100, ttl=3600)  # 1-hour cache

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

async def fetch_with_timeout(session, url, timeout=10):
    try:
        async with session.get(url, timeout=timeout) as response:
            if response.status == 200:
                return await response.text()
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
    return None

async def get_download_link(session, file_path):
    file_url = f"{BASE_URL}{file_path}"
    html = await fetch_with_timeout(session, file_url)
    if html:
        try:
            soup = BeautifulSoup(html, 'html.parser')
            download_link = soup.find('a', {'target': '_blank'})
            return download_link['href'] if download_link else None
        except Exception as e:
            logger.error(f"Error parsing download page: {e}")
    return None

async def search_content(query: str):
    cache_key = query.lower().strip()
    if cache_key in search_cache:
        return search_cache[cache_key]

    search_url = f"{BASE_URL}/?search={urllib.parse.quote(query)}"
    
    try:
        async with aiohttp.ClientSession() as session:
            html = await fetch_with_timeout(session, search_url)
            if not html:
                return []

            soup = BeautifulSoup(html, 'html.parser')
            results = []
            
            for result in soup.find_all('a', class_='block'):
                try:
                    title = result.find('div', class_='mb-3').text.strip()
                    size = result.find('span', class_='px-3').text.strip()
                    file_path = result['href']
                    
                    results.append({
                        'title': title,
                        'size': size,
                        'file_path': file_path
                    })
                except Exception as e:
                    logger.error(f"Error parsing result: {e}")
                    continue

            search_cache[cache_key] = results
            return results
    except Exception as e:
        logger.error(f"Error in search: {e}")
        return []

def get_results_keyboard(results, page=0):
    keyboard = []
    start_idx = page * RESULTS_PER_PAGE
    end_idx = start_idx + RESULTS_PER_PAGE
    current_results = results[start_idx:end_idx]
    
    for idx, result in enumerate(current_results, start=1):
        title = result['title']
        if len(title) > 50:
            title = title[:47] + "..."
        keyboard.append([
            InlineKeyboardButton(
                f"{idx}. {title} ({result['size']})",
                callback_data=f"result_{start_idx + idx - 1}"
            )
        ])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"page_{page-1}"))
    if end_idx < len(results):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Welcome! Send me a movie or series name to search.\n\n"
        "Example: `Inception`",
        parse_mode='Markdown'
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    status_message = await update.message.reply_text("🔍 Searching... Please wait.")
    
    try:
        results = await search_content(query)
        if not results:
            await status_message.edit_text("❌ No results found! Try another search term.")
            return

        context.user_data['results'] = results
        context.user_data['current_query'] = query
        
        await status_message.edit_text(
            f"🎯 Found {len(results)} results for: *{query}*",
            parse_mode='Markdown',
            reply_markup=get_results_keyboard(results)
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        await status_message.edit_text("❌ An error occurred while searching. Please try again later!")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data.startswith("page_"):
            page = int(query.data.split("_")[1])
            results = context.user_data.get('results', [])
            current_query = context.user_data.get('current_query', "Search")
            
            await query.message.edit_text(
                f"🎯 Results for: *{current_query}*",
                parse_mode='Markdown',
                reply_markup=get_results_keyboard(results, page)
            )
        
        elif query.data.startswith("result_"):
            idx = int(query.data.split("_")[1])
            results = context.user_data.get('results', [])
            result = results[idx]
            
            loading_message = await query.message.edit_text("⏳ Fetching download link...")
            
            async with aiohttp.ClientSession() as session:
                download_link = await get_download_link(session, result['file_path'])
                
                if download_link:
                    keyboard = [[
                        InlineKeyboardButton("⬇️ Download", url=download_link),
                        InlineKeyboardButton("🔙 Back", callback_data="back_to_search")
                    ]]
                    
                    await loading_message.edit_text(
                        f"📥 *{result['title']}*\n"
                        f"💾 Size: {result['size']}",
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await loading_message.edit_text(
                        "❌ Failed to get download link! Try selecting another result.",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🔙 Back to Results", callback_data="back_to_search")
                        ]])
                    )
        
        elif query.data == "back_to_search":
            results = context.user_data.get('results', [])
            current_query = context.user_data.get('current_query', "Search")
            
            await query.message.edit_text(
                f"🎯 Results for: *{current_query}*",
                parse_mode='Markdown',
                reply_markup=get_results_keyboard(results)
            )
            
    except Exception as e:
        logger.error(f"Callback error: {e}")
        await query.message.edit_text(
            "❌ An error occurred. Please try searching again.",
            reply_markup=None
        )

async def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Start the bot
    if os.environ.get("ENVIRONMENT") == "production":
        # Production mode (Render.com)
        await application.bot.set_webhook(os.environ.get("WEBHOOK_URL"))
        await application.start()
        await application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=os.environ.get("WEBHOOK_URL"),
            secret_token=os.environ.get("SECRET_TOKEN", "")
        )
    else:
        # Development mode
        await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
