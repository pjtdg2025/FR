import requests
import datetime

def get_binance_funding():
    url = "https://fapi.binance.com/fapi/v1/fundingRate"
    params = {"limit": 100}
    response = requests.get(url, params=params).json()
    latest = response[0]
    time_next = datetime.datetime.fromtimestamp((latest['fundingTime'] + 28800000) / 1000)
    return [{
        'symbol': latest['symbol'],
        'rate': float(latest['fundingRate']),
        'next_funding_time': time_next,
        'exchange': 'Binance'
    }]

def get_okx_funding():
    url = "https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USD-SWAP"
    response = requests.get(url).json()
    data = response['data'][0]
    time_next = datetime.datetime.fromisoformat(data['nextFundingTime'].replace('Z', '+00:00'))
    return [{
        'symbol': data['instId'],
        'rate': float(data['fundingRate']),
        'next_funding_time': time_next,
        'exchange': 'OKX'
    }]

def get_bybit_funding():
    url = "https://api.bybit.com/v2/public/tickers"
    response = requests.get(url).json()
    result = []
    now = datetime.datetime.utcnow()
    for item in response['result']:
        if "USDT" in item['symbol']:
            try:
                rate = float(item.get("funding_rate", 0.0))
                funding_time = now + datetime.timedelta(hours=8 - now.hour % 8, minutes=-now.minute)
                result.append({
                    'symbol': item['symbol'],
                    'rate': rate,
                    'next_funding_time': funding_time,
                    'exchange': 'Bybit'
                })
            except:
                continue
    return result

def get_mexc_funding():
    url = "https://contract.mexc.com/api/v1/private/funding/prev_funding_rate"
    response = requests.get(url).json()
    result = []
    now = datetime.datetime.utcnow()
    for item in response['data']:
        try:
            rate = float(item['fundingRate'])
            funding_time = now + datetime.timedelta(hours=8 - now.hour % 8, minutes=-now.minute)
            result.append({
                'symbol': item['symbol'],
                'rate': rate,
                'next_funding_time': funding_time,
                'exchange': 'MEXC'
            })
        except:
            continue
    return result

def check_all_exchanges(alert_callback):
    all_data = (
        get_binance_funding() +
        get_okx_funding() +
        get_bybit_funding() +
        get_mexc_funding()
    )

    # Filter: alert 45 minutes before next funding
    now = datetime.datetime.utcnow()
    alert_window = now + datetime.timedelta(minutes=45)
    upcoming = [item for item in all_data if item['next_funding_time'] <= alert_window]

    # Group by exchange and get top 3 positive and top 3 negative
    from collections import defaultdict
    grouped = defaultdict(list)
    for item in upcoming:
        grouped[item['exchange']].append(item)

    for exchange, items in grouped.items():
        items = sorted(items, key=lambda x: x['rate'])
        negative = items[:3]
        positive = items[-3:][::-1]

        if negative or positive:
            message = f"<b>{exchange} - Upcoming Funding</b>\\n"
            for i in negative:
                message += f"🔻 <code>{i['symbol']}</code>: {i['rate']:.4%}\\n"
            for i in positive:
                message += f"🟢 <code>{i['symbol']}</code>: {i['rate']:.4%}\\n"
            alert_callback(message)
