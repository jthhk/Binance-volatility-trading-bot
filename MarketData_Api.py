# used for dates
import time

# use if needed to pass args to external modules
import sys

#redis
import redis



#global Settings 
import settings


# Clear the screen
from os import system, name


#RegEx
from re import search

# Needed for colorful console output
from colorama import init

# needed for the binance API / websockets / Exception handling
from binance.client import Client
from binance.exceptions import BinanceAPIException

# used for dates
from datetime import datetime

# Load creds modules
from helpers.handle_creds import (
    test_api_key
)

        
def InitializeDataFeed():

    lastime = time.time()

    while True:
        if (time.time() - lastime > 10):
            prices = client.get_all_tickers()
            for coin in prices:
                symbol = coin['symbol']
                lastpx = coin['price']
                data = MarketData.hgetall("L1:"+symbol)
                if data:
                    MarketDataRec = {'symbol': symbol ,'price' : lastpx, 'update': 1}
                    MarketData.hmset("L1:"+symbol, MarketDataRec)
                lastime = time.time()

#-------------------------------------------------------------------------------
        
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
    
    try:
        #Start Websocket
        print("Market data api feedhandler starting - do_work.")
        InitializeDataFeed()
    except KeyboardInterrupt:
        print('Market data api file exiting from do_work.')
        sys.exit(0)

"""
if __name__ == '__main__':

    #Start MarketData Thread
    do_work()
"""