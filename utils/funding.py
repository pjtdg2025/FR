import aiohttp
import datetime
from collections import defaultdict

async def get_binance_funding():
    url = "https://fapi.binance.com/fapi/v1/fundingRate?limit=100"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            response = await resp.json()
    latest = response[0]
    time_next = datetime.datetime.fromtimestamp((latest['fundingTime'] + 28800000) / 1000, tz=datetime.timezone.utc)
    return [{
        'symbol': latest['symbol'],
        'rate': float(latest['fundingRate']),
        'next_funding_time': time_next,
        'exchange': 'Binance'
    }]

async def get_okx_funding():
    url = "https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USD-SWAP"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            response = await resp.json()
    data = response['data'][0]
    time_next = datetime.datetime.fromisoformat(data['nextFundingTime'].replace('Z', '+00:00'))
    return [{
        'symbol': data['instId'],
        'rate': float(data['fundingRate']),
        'next_funding_time': time_next,
        'exchange': 'OKX'
    }]

async def get_bybit_funding():
    url = "https://api.bybit.com/v2/public/tickers"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            response = await resp.json()
    result = []
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    for item in response['result']:
        if "USDT" in item['symbol']:
            try:
                rate = float(item.get("funding_rate", 0.0))
                # Calculate next funding time (every 8 hours)
                hour_mod = now.hour % 8
                next_funding_hour = now.replace(hour=now.hour - hour_mod) + datetime.timedelta(hours=8)
                funding_time = next_funding_hour.replace(minute=0, second=0, microsecond=0)
                result.append({
                    'symbol': item['symbol'],
                    'rate': rate,
                    'next_funding_time': funding_time,
                    'exchange': 'Bybit'
                })
            except:
                continue
    return result

async def get_mexc_funding():
    symbols_url = "https://contract.mexc.com/api/v1/contract/detail"
    funding_url_base = "https://contract.mexc.com/api/v1/contract/funding_rate/"
    async with aiohttp.ClientSession() as session:
        async with session.get(symbols_url) as resp:
            symbols_response = await resp.json()
        result = []
        now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        for item in symbols_response.get('data', []):
            symbol = item['symbol']
            try:
                async with session.get(f"{funding_url_base}{symbol}") as f_resp:
                    data = await f_resp.json()
                    if data.get('data'):
                        next_funding_time = datetime.datetime.fromtimestamp(data['data']['nextFundingTime'] / 1000, tz=datetime.timezone.utc)
                        rate = float(data['data']['fundingRate'])
                        # Only add if next funding is in the future
                        if next_funding_time > now:
                            result.append({
                                'symbol': symbol,
                                'rate': rate,
                                'next_funding_time': next_funding_time,
                                'exchange': 'MEXC'
                            })
            except:
                continue
    return result

async def check_all_exchanges():
    all_data = []
    all_data.extend(await get_binance_funding())
    all_data.extend(await get_okx_funding())
    all_data.extend(await get_bybit_funding())
    all_data.extend(await get_mexc_funding())

    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    alert_window_start = now
    alert_window_end = now + datetime.timedelta(minutes=45)

    upcoming = [item for item in all_data if alert_window_start <= item['next_funding_time'] <= alert_window_end]

    grouped = defaultdict(list)
    for item in upcoming:
        grouped[item['exchange']].append(item)

    messages = []
    for exchange, items in grouped.items():
        items = sorted(items, key=lambda x: x['rate'])
        negative = items[:3]
        positive = items[-3:][::-1]
        if negative or positive:
            message = f"<b>{exchange} - Upcoming Funding (within 45 min)</b>\n"
            for i in negative:
                message += f"🔻 <code>{i['symbol']}</code>: {i['rate']:.4%}\n"
            for i in positive:
                message += f"🟢 <code>{i['symbol']}</code>: {i['rate']:.4%}\n"
            messages.append(message)

    return messages
