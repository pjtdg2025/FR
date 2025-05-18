import os
import asyncio
import aiohttp
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

async def check_and_alert():
    loop = asyncio.get_event_loop()

    def callback_sync(msg):
        # Schedule async send_telegram_message from sync callback
        asyncio.run_coroutine_threadsafe(send_telegram_message(msg), loop)

    # Use the funding module's check_all_exchanges, passing callback_sync
    funding.check_all_exchanges(callback_sync)

async def main_loop():
    while True:
        try:
            await check_and_alert()
        except Exception as e:
            print(f"Error: {e}")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main_loop())
