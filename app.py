import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters, ContextTypes
from bs4 import BeautifulSoup
import aiohttp
import urllib.parse

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BASE_URL = "https://new3.scloud.ninja"

class MovieBot:
    def __init__(self):
        self.search_cache = {}  # To store search results temporarily
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Welcome! Send me a movie/series name to search.")

    async def scrape_links(self, search_query):
        async with aiohttp.ClientSession() as session:
            search_url = f"{BASE_URL}/?search={urllib.parse.quote(search_query)}"
            async with session.get(search_url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                results = []

                for result in soup.find_all('a', class_='block'):
                    title = result.find('div', class_='mb-3').text.strip()
                    size = result.find('span', class_='px-3').text.strip()
                    file_path = result['href']
                    results.append({
                        'title': title,
                        'size': size,
                        'url': f"{BASE_URL}{file_path}"
                    })
                return results

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.message.text
        await update.message.reply_text("🔍 Searching... Please wait.")
        results = await self.scrape_links(query)
        
        if not results:
            await update.message.reply_text("❌ No results found.")
            return
        
        self.search_cache[query] = results
        await self.send_paginated_results(update, query, page=1)

    async def send_paginated_results(self, update: Update, query, page=1):
        results = self.search_cache.get(query, [])
        items_per_page = 5
        start = (page - 1) * items_per_page
        end = start + items_per_page
        paginated_results = results[start:end]

        keyboard = [
            [InlineKeyboardButton(f"{result['title']} ({result['size']})", callback_data=f"result:{query}:{idx}")]
            for idx, result in enumerate(results[start:end], start)
        ]

        if page > 1:
            keyboard.append([InlineKeyboardButton("⬅️ Previous", callback_data=f"page:{query}:{page-1}")])
        if end < len(results):
            keyboard.append([InlineKeyboardButton("➡️ Next", callback_data=f"page:{query}:{page+1}")])

        await update.message.reply_text("📋 Results:", reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data
        await query.answer()

        if data.startswith("page:"):
            _, search_query, page = data.split(":")
            await self.send_paginated_results(update, search_query, int(page))
        elif data.startswith("result:"):
            _, search_query, idx = data.split(":")
            results = self.search_cache.get(search_query, [])
            result = results[int(idx)]
            download_link = await self.get_download_link(result['url'])

            keyboard = [[InlineKeyboardButton("⬇️ Download", url=download_link)]]
            await query.edit_message_text(f"🎬 {result['title']}\n📦 Size: {result['size']}", reply_markup=InlineKeyboardMarkup(keyboard))

    async def get_download_link(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                return soup.find('a', {'target': '_blank'})['href']

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    bot = MovieBot()

    app.add_handler(CommandHandler("start", bot.start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    app.add_handler(CallbackQueryHandler(bot.handle_callback))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
