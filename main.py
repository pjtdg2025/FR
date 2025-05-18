import os
import asyncio
import aiohttp
from aiohttp import web
from utils import funding

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload) as resp:
            return await resp.text()

async def alert_callback(message):
    await send_telegram_message(message)

async def run_checks():
    loop = asyncio.get_event_loop()

    def callback_sync(msg):
        asyncio.run_coroutine_threadsafe(send_telegram_message(msg), loop)

    funding.check_all_exchanges(callback_sync)

async def handle_check(request):
    try:
        await run_checks()
        return web.Response(text="Funding check done, alerts sent if applicable.")
    except Exception as e:
        return web.Response(text=f"Error: {e}", status=500)

app = web.Application()
app.add_routes([web.get('/check_funding', handle_check)])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    web.run_app(app, port=port)
