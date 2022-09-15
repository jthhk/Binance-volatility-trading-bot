"""
BTC Pause
"""

import os
import sys
import time as t
import redis
import settings

from datetime import datetime 

SIGNAL_NAME = 'jimbot_pause'
SIGNAL_TYPE = 'pause'

def analyse_btc():
	
    global MarketData

    paused = False
    now = datetime.now()

    Bitcoin_TA_1m = MarketData.hgetall('TA:BTCUSDT1T')
    Bitcoin_TA_5m = MarketData.hgetall('TA:BTCUSDT5T')
    if len(Bitcoin_TA_1m) > 0:
        histbtc = float(Bitcoin_TA_1m['macd']) 
        curve = float(Bitcoin_TA_5m['trima'])
        sma = float(Bitcoin_TA_5m['sma'])
    else: 
        histbtc = -999
        curve = -999
        sma = -999

    if histbtc < 0:
        print(f'{SIGNAL_NAME}: Market not looking good - BitCoin 1m MACD is -ve =' + str(histbtc))
        paused = True

    data = MarketData.hgetall('L1:BTCUSDT')
    if len(data) > 0:
        TrendingDown = float(data['TrendingDown'])  #count inc if trade px is < last one, resets to 0 once direction changes
    else:
        TrendingDown = 0

    if TrendingDown > 10:
        print(f'{SIGNAL_NAME}: Market not looking good - BitCoin is trending down :' + str(TrendingDown))
        paused = True

    if sma < curve:
        print(f'{SIGNAL_NAME}: Market not looking good - SMA IS LESS THAN TRIMA :' + str(sma) + '<' + str(curve) )
        #paused = True

    #Trade only monday to Friday
    #if 0 <= now.weekday() <= 4:
    return paused

def do_work():
	
    global MarketData

    settings.init()
    MarketData = redis.Redis(host='localhost', port=6379, db=settings.DATABASE,decode_responses=True)

    while True:
        paused = analyse_btc()
        if paused:
            with open(f'signals/{SIGNAL_NAME}.{SIGNAL_TYPE}', 'a+') as f:
                f.write('yes')
            print("Bot paused by BTC")
        else:
            if os.path.isfile(f'signals/{SIGNAL_NAME}.{SIGNAL_TYPE}'):
                os.remove(f'signals/{SIGNAL_NAME}.{SIGNAL_TYPE}')
                print("Bot resumed by btc_pause")
        t.sleep(settings.RECHECK_INTERVAL * 2 ) 
