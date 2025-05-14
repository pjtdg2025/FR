import os
import asyncio
import aiohttp
from datetime import datetime, timedelta, timezone

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload) as resp:
            return await resp.text()

async def fetch_binance_funding():
    url = "https://fapi.binance.com/fapi/v1/premiumIndex"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            result = []
            now = datetime.now(timezone.utc)
            for item in data:
                next_funding_time = datetime.fromtimestamp(item['nextFundingTime'] / 1000, tz=timezone.utc)
                minutes_left = (next_funding_time - now).total_seconds() / 60
                if 14 <= minutes_left <= 16:
                    result.append({
                        "symbol": item['symbol'],
                        "rate": float(item['lastFundingRate']),
                        "next_time": next_funding_time.strftime("%H:%M UTC")
                    })
            top_5 = sorted(result, key=lambda x: abs(x['rate']), reverse=True)[:5]
            return top_5

async def fetch_bybit_funding():
    url = "https://api.bybit.com/v2/public/tickers"
    funding_url = "https://api.bybit.com/v2/public/funding/prev-funding-rate"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            tickers = await resp.json()
        async with session.get(funding_url) as resp:
            funding_data = await resp.json()
            result = []
            now = datetime.now(timezone.utc)
            next_time = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
            minutes_left = (next_time - now).total_seconds() / 60
            if 14 <= minutes_left <= 16:
                for item in funding_data['result']:
                    result.append({
                        "symbol": item['symbol'],
                        "rate": float(item['funding_rate']),
                        "next_time": next_time.strftime("%H:%M UTC")
                    })
            top_5 = sorted(result, key=lambda x: abs(x['rate']), reverse=True)[:5]
            return top_5

async def fetch_okx_funding():
    url = "https://www.okx.com/api/v5/public/funding-rate"
    async with aiohttp.ClientSession() as session:
        async with session.get("https://www.okx.com/api/v5/public/instruments?instType=SWAP") as resp:
            instruments = await resp.json()
            result = []
            now = datetime.now(timezone.utc)
            for inst in instruments['data']:
                symbol = inst['instId']
                async with session.get(f"{url}?instId={symbol}") as f_resp:
                    data = await f_resp.json()
                    if data['data']:
                        item = data['data'][0]
                        time_str = item['nextFundingTime']
                        next_funding_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                        minutes_left = (next_funding_time - now).total_seconds() / 60
                        if 14 <= minutes_left <= 16:
                            result.append({
                                "symbol": symbol,
                                "rate": float(item['fundingRate']),
                                "next_time": next_funding_time.strftime("%H:%M UTC")
                            })
            top_5 = sorted(result, key=lambda x: abs(x['rate']), reverse=True)[:5]
            return top_5

async def fetch_mexc_funding():
    url = "https://api.mexc.com/api/v1/private/funding_rate"  # MEXC public funding rate endpoint may vary
    async with aiohttp.ClientSession() as session:
        async with session.get("https://contract.mexc.com/api/v1/contract/detail") as resp:
            symbols = await resp.json()
            result = []
            now = datetime.now(timezone.utc)
            for item in symbols['data']:
                symbol = item['symbol']
                try:
                    async with session.get(f"https://contract.mexc.com/api/v1/contract/funding_rate/{symbol}") as f_resp:
                        data = await f_resp.json()
                        if data['data']:
                            next_funding_time = datetime.fromtimestamp(data['data']['nextFundingTime'] / 1000, tz=timezone.utc)
                            minutes_left = (next_funding_time - now).total_seconds() / 60
                            if 14 <= minutes_left <= 16:
                                result.append({
                                    "symbol": symbol,
                                    "rate": float(data['data']['fundingRate']),
                                    "next_time": next_funding_time.strftime("%H:%M UTC")
                                })
                except:
                    continue
            top_5 = sorted(result, key=lambda x: abs(x['rate']), reverse=True)[:5]
            return top_5

async def check_and_alert():
    messages = []

    binance_top5 = await fetch_binance_funding()
    if binance_top5:
        msg = "<b>📢 Binance Top 5 Funding Rates (15 min before):</b>\n"
        for item in binance_top5:
            msg += f"\n<b>{item['symbol']}</b>: {item['rate']*100:.4f}% at {item['next_time']}"
        messages.append(msg)

    bybit_top5 = await fetch_bybit_funding()
    if bybit_top5:
        msg = "<b>📢 Bybit Top 5 Funding Rates (15 min before):</b>\n"
        for item in bybit_top5:
            msg += f"\n<b>{item['symbol']}</b>: {item['rate']*100:.4f}% at {item['next_time']}"
        messages.append(msg)

    okx_top5 = await fetch_okx_funding()
    if okx_top5:
        msg = "<b>📢 OKX Top 5 Funding Rates (15 min before):</b>\n"
        for item in okx_top5:
            msg += f"\n<b>{item['symbol']}</b>: {item['rate']*100:.4f}% at {item['next_time']}"
        messages.append(msg)

    mexc_top5 = await fetch_mexc_funding()
    if mexc_top5:
        msg = "<b>📢 MEXC Top 5 Funding Rates (15 min before):</b>\n"
        for item in mexc_top5:
            msg += f"\n<b>{item['symbol']}</b>: {item['rate']*100:.4f}% at {item['next_time']}"
        messages.append(msg)

    for msg in messages:
        await send_telegram_message(msg)

async def main_loop():
    while True:
        try:
            await check_and_alert()
        except Exception as e:
            print(f"Error: {e}")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main_loop())
