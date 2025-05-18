import os
import asyncio
import aiohttp
import funding  # your async funding.py module

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload) as resp:
            return await resp.text()

async def check_and_alert():
    messages = await funding.check_all_exchanges()
    for msg in messages:
        await send_telegram_message(msg)

async def main_loop():
    while True:
        try:
            await check_and_alert()
        except Exception as e:
            print(f"Error in main_loop: {e}")
        await asyncio.sleep(60)  # run every 60 seconds

if __name__ == "__main__":
    asyncio.run(main_loop())
