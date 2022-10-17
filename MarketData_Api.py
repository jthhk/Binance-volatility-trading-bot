# used for dates
import time

# use if needed to pass args to external modules
import sys

#redis
import redis

#global Settings 
import settings

#RegEx
from re import search

# needed for the binance API / websockets / Exception handling
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Load creds modules
from helpers.handle_creds import (
    test_api_key
)
        
#loads config.cfg into settings.XXXXX
settings.init()

# Binance - Authenticate with the client, Ensure API key is good before continuing
if settings.AMERICAN_USER:
    client = Client(settings.access_key, settings.secret_key, tld='us')
else:
    client = Client(settings.access_key, settings.secret_key)

# If the users has a bad / incorrect API key.
# this will stop the script from starting, and display a helpful error.
api_ready, msg = test_api_key(client, BinanceAPIException)
if api_ready is not True:
    exit(f'{msg}')
        
    
#define redis DataBase connection and flush it
MarketData = redis.Redis(host='localhost', port=6379, db=settings.DATABASE,decode_responses=True)

def do_work():
    
    #Start Websocket
    print("Market data api feedhandler starting - do_work.")
    lastime = time.time()

    while True:
        if (time.time() - lastime > 1):
            prices = client.get_all_tickers()
            for coin in prices:
                symbol = coin['symbol']
                lastpx = coin['price']
                data = MarketData.hgetall("L1:"+symbol)
                if data:
                    MarketDataRec = {'symbol': symbol ,'price' : lastpx, 'update': 1}
                    MarketData.hmset("L1:"+symbol, MarketDataRec)
                lastime = time.time()
                eventtime = int('{:<013d}'.format(round(time.time())))
                EventRec = {'updated': eventtime }
                MarketData.hmset("UPDATE:API", EventRec)
                #time.sleep(10)
