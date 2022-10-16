# use for environment variables
import os

# used for dates
import time

# use if needed to pass args to external modules
import sys

#redis
import redis

#TA-lib 
import pandas_ta as ta

#global Settings 
import settings

# Added for WebSocket Support
import pandas as pd
import pprint
import ccxt
import logging

# Clear the screen
from os import system, name

from unicorn_binance_websocket_api.manager import BinanceWebSocketApiManager
from unicorn_fy.unicorn_fy import UnicornFy

#timezones
import pytz

#RegEx
from re import search

# Needed for colorful console output
from colorama import init

init()

# needed for the binance API / websockets / Exception handling
from binance.client import Client
from binance.exceptions import BinanceAPIException

# used for dates
from datetime import datetime

# used to store trades and sell assets
import json

# used to display holding coins in an ascii table
from prettytable import PrettyTable

# Load creds modules
from helpers.handle_creds import (
    test_api_key
)

# for colourful logging to the console
class txcolors:
    BUY = '\033[92m'
    WARNING = '\033[93m'
    SELL_LOSS = '\033[91m'
    SELL_PROFIT = '\033[32m'
    DIM = '\033[2m\033[35m'
    DEFAULT = '\033[39m'
    YELLOW = '\033[33m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ENDC = '\033[0m'

# logging needed otherwise slient fails - INFO/DEBUG/ERROR
logging.getLogger("unicorn_binance_websocket_api")
logging.basicConfig(level=logging.INFO,
                    filename=os.path.basename(__file__) + '.log',
                    format="{asctime} [{levelname:8}] {process} {thread} {module}: {message}",
                    style="{")

# define our clear function
def clear():
  
    # for windows
    if name == 'nt':
        _ = system('cls')
    # for mac and linux(here, os.name is 'posix')
    else:
        _ = system('clear')
        
def InitializeDataFeed():
    #######################################
    # (a) Create redis database
    # (b) Define watch list and create a row for every coin 
    # (c) Open Web socket to start collecting market data into the redis database  
    # TO DO: Review: Looking at 3 things - SOCKET_LIST - bookTicker and aggTrade are pretty busy 
    # ######################################    
    global web_socket_app

    SOCKET_LIST = settings.TICKER_ITEMS
    current_ticker_list = []
    #-------------------------------------------------------------------------------
    # (a) Create redis database (MarketData) with a hash and list collection
    #  Hash Keys: L1:{Coin} -> which has Level 1 market data fields, see MarketDataRec 
    #  list Keys: L1 -> L1:{Coin}
    #  Why: I added the list sorting of the hash, otherwise I could not sort
    # (b) Define watch list of coins we want to monitor, see SOCKET_LIST + current_ticker_list 
    CoinsCounter = 0
    tickers = [line.strip() for line in open(settings.TICKERS_LIST)]
    print( str(datetime.now()) + " :Preparing watch list defined in tickers file...")
    for item in tickers:

        if not (item in settings.EX_PAIRS):
            #Create Dataframes with coins
            coin = item + settings.PAIR_WITH
            data =  {'symbol': coin}

            sleep_time = 30
            num_retries = 4
            
            for x in range(0, num_retries): 
                try:
                    info = client.get_symbol_info(coin)
                    step_size = info['filters'][2]['stepSize']

                    MarketDataRec = {'symbol': coin , 'open': -1, 'high': -1, 'low': -1, 'close': -1, 'potential' : -1, 'interval' : -1,'price' : -1,'LastQty': -1,'BBPx': -1,'BBQty': -1,'BAPx': -1,'BAQty': -1,'updated' : 0, 'step_size' : step_size, 'TrendingDown' : 0, 'spread': 0, 'WeightedAvgPrice': 0, 'mid': 0, 'orderBookDemand': '-',   'TrendingUp': 0 ,  'TakerCount': 0 , 'MakerCount': 0 , 'MarketPressure': '-' }

                    MarketData.hmset("L1:"+coin, MarketDataRec)
                    MarketData.lpush("L1", "L1:"+coin)
                    get_data_frame(coin)  #Needs to move out
                    current_ticker_list.append(coin)
                    CoinsCounter += 1
                except Exception as str_error:
                    print(f'Warning - {coin} - get_symbol_info failed sleeping for {sleep_time}' )
                    time.sleep(sleep_time)  # wait before trying to fetch the data again
                    sleep_time *= 2  # Implement your backoff algorithm here i.e. exponential backoff
                else:
                    break
    clear()
    print(f'{str(datetime.now())}: Total Coins: {CoinsCounter}')

    if DEBUG:
        start = datetime.now()
        #Example sort and iterate thru the hash collection  
        GetCoinsInOrder = MarketData.sort('L1',alpha=True,desc=False,by='*->open')
        for key in GetCoinsInOrder:
            data = MarketData.hgetall(key)
            print(data)
            print('---scan--')
        end = datetime.now()
        print(str('queried in ' + str(end - start) + ' with sort.'))

    #------------------------------------
    # (c) Create a Web Socket to get the market data 
    if settings.BACKTEST_PLAY:
        num_lines = sum(1 for line in open(settings.BACKTEST_FILE))
        SleepValue = settings.MARKET_DATA_INTERVAL
        EstTime = (num_lines * SleepValue)/60
        print( str(datetime.now()) + " :Back tester enabled, Expected time will be " + str(EstTime) + " mins")
        with open(settings.BACKTEST_FILE) as topo_file:
            for line in topo_file:
                on_message('backtester',line)
                time.sleep(SleepValue)
        print( str(datetime.now()) + " :Back tester Replay Complete - Exiting")
        MarketData.flushall()
        sys.exit(0)   
        
    else:    
        print( str(datetime.now()) + " :Connecting to WebSocket ...")
        if DEBUG: print( str(datetime.now()) + " :Connecting to WebSocket " + str(SOCKET_LIST) + " ...")

        # create instance of BinanceWebSocketApiManager and provide the function for stream processing
        binance_websocket_api_manager = BinanceWebSocketApiManager(exchange="binance.com",stream_buffer_maxlen=250)
        # define markets
        #markets = {'bnbbtc', 'ethbtc'}


        # define stream channels
        channels = SOCKET_LIST

        # create and start the stream
        for channel in channels:
            markets = current_ticker_list.copy()
            bufferSize = CoinsCounter
            if channel == "aggTrade" or channel =="bookTicker":
                #Remove BTCUSDT and ETHUSDT from markets as they flood the busy streams
                markets.remove("BTCUSDT")
                markets.remove("ETHUSDT")
                bufferSize = 250
                                
            binance_websocket_api_manager.create_stream(channel, markets,output="UnicornFy",stream_buffer_name=channel,stream_label=channel,ping_interval=300, ping_timeout=None,stream_buffer_maxlen=bufferSize)
        
        #binance_websocket_api_manager.start_monitoring_api()

        while True:
            for channel in channels:
                i = 0
                while i < CoinsCounter:
                    latest_stream_data_from_stream_buffer = binance_websocket_api_manager.pop_stream_data_from_stream_buffer(stream_buffer_name=channel, mode='LIFO') 
                    if latest_stream_data_from_stream_buffer:
                        process_stream(latest_stream_data_from_stream_buffer)    
                        i += 1
                    else:
                        i = CoinsCounter
            
            closeminutes = int(datetime.utcfromtimestamp(round(time.time())/1000).strftime('%M'))
            if closeminutes % 3 == 0: 
                binance_websocket_api_manager.print_summary()
            
    #-------------------------------------------------------------------------------
def process_stream(event):

    try:
        eventtype = event['event_type'] 
        if eventtype == "bookTicker":
            eventtime = int('{:<013d}'.format(round(time.time())))
        else:
            eventtime = event['event_time'] 
                
        if DEBUG: print(f"Market data Update: {eventtype} @ {eventtime}")
        
        eventdiff = int('{:<013d}'.format(round(time.time()))) - eventtime
        #print(f"Event Diff:{eventtype} @ {eventdiff}")

        if LATENCY_TEST:
            file_path = 'backtester/' +  datetime.now().strftime('%Y%m%d_%H') + '.txt'
            with open(file_path, "a") as output_file:
                output_file.write(str(eventtype) + ';' + str(eventdiff) + '\n')

        EventRec = {'updated': eventtime }
        MarketData.hmset("UPDATE:"+eventtype, EventRec)

        if eventtype == "kline":
            candle=event['kline']
            #Need to check Candle is closed 
            is_candle_closed = candle['is_closed']
            symbol = candle["symbol"]
            interval = candle["interval"]
            closePx = candle["close_price"]
            potential = -1

            if DEBUG: print("KLINE:" + str(interval))
            if interval == "1s":
                #1sec/can be used to get prices
                MarketDataRec = {'symbol': symbol ,'price' : closePx, 'update': 1}
                MarketData.hmset("L1:"+symbol, MarketDataRec)
                if eventdiff > 1000:
                    print(f"Event Diff:{eventtype} - {interval} - {symbol} - { datetime.now().strftime('%HH:%MM:%SS')} @ {eventdiff}")
                if DEBUG: data = MarketData.hgetall("L1:" + symbol)

            elif interval == "1m":

                if is_candle_closed:
                    #1min/called standard 
                    OneMinDataSet = list_of_coins[symbol + '_1T'] 
                    FiveMinDataSet = list_of_coins[symbol + '_' + '5T']

                    #Get Last closed Candle data and prep in dataframe
                    closeminutes = int(datetime.utcfromtimestamp(candle["kline_close_time"]/1000).strftime('%M'))
                    closedate = datetime.fromtimestamp(candle["kline_close_time"]/1000, tz=pytz.utc)
                    closedate = closedate.replace(tzinfo=None)
                    LastCandle = {closedate : {'open': float(candle["open_price"]), 'high':  float(candle["high_price"]), 'low':  float(candle["low_price"]),'close':  float(candle["close_price"]), 'volume' :  float(candle["base_volume"])}}
                    LastCandle = pd.DataFrame(LastCandle).T.reset_index().rename(columns={"index":"time"})
                    LastCandle.set_index('time', inplace=True)

                    #Sliding Window: append latest candle onto my history, cap using Len()-1,  save it for the next recalc 
                    OneMinDataSet = OneMinDataSet.tail(len(OneMinDataSet)-1)
                    OneMinDataSet = pd.concat([OneMinDataSet,LastCandle])
                    list_of_coins[symbol + '_1T'] = OneMinDataSet

                    #Update the 5min data set
                    calc_timeframes = ['1T']

                    if closeminutes % 5 == 0: 
                        #Sliding Window: Calc the 5min candle from the 1min dataset, then save
                        calc_timeframes.append('5T')
                        
                        #Get last 5 1min rows, calc, save 1 5min row
                        LastFiveCandle = OneMinDataSet.tail(5) 
                        LastFiveCandle = LastFiveCandle.resample('5T').agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
                        LastFiveCandle - LastFiveCandle.tail(1)
                        
                        FiveMinDataSet = FiveMinDataSet.tail(len(FiveMinDataSet)-1)
                        FiveMinDataSet = pd.concat([FiveMinDataSet,LastFiveCandle])
                        list_of_coins[symbol + '_' + '5T'] = FiveMinDataSet
                    if closeminutes % 15 == 0: calc_timeframes.append('15T')
                    if closeminutes % 30 == 0: calc_timeframes.append('30T')

                    for calc_item in calc_timeframes:	
                        if calc_item == '1T':
                            dataset = OneMinDataSet
                        else:
                            dataset = FiveMinDataSet.resample(calc_item).agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
                        dataset = dataset.dropna()
                        rsi = dataset.ta.rsi()
                        adx = dataset.ta.adx()
                        macd = dataset.ta.macd(fast=12, slow=26)
                        trima = dataset.ta.trima(length=10)
                        sma = dataset.ta.sma(length=10)
        

                        get_rsi = rsi[-1:][0]
                        get_adx = adx['ADX_14'][len(adx)-1] #measure here is the direction/trend of the asset. It is represented using,
                        get_macd = macd['MACDh_12_26_9'][len(macd)-1]  #The histogram is positive when MACD is higher than its nine-day EMA, and negative when it is lower.
                        get_trima = trima[len(trima)-1]
                        get_sma = sma[len(sma)-1]

                        MarketDataRec = {'symbol': symbol , 'macd': get_macd,'rsi': get_rsi,'adx': get_adx ,'trima':get_trima,'sma':get_sma}
                        MarketData.hmset("TA:"+symbol+calc_item, MarketDataRec)
                        MarketData.lpush("TA", "TA:"+symbol+calc_item)
                        highpx =  candle["high_price"]
                        lowpx = candle["low_price"]

                    #session High/low using 1m and 5m combined                 
                    SixMinDataSet = pd.concat([OneMinDataSet,FiveMinDataSet])
                    column = SixMinDataSet["high"]
                    highpx = column.max()
                    column = SixMinDataSet["low"]
                    lowpx = column.min()
                    potential = (float(lowpx) / float(highpx)) * 100
                
                    MarketDataRec = {'symbol': symbol ,'price': closePx, 'open': candle["open_price"], 'high': highpx, 'low': lowpx, 'close': closePx, 'potential' : potential, 'interval' : interval,'update': 1}
                    MarketData.hmset("L1:"+symbol, MarketDataRec)
                    if eventdiff > 2000:
                        print(f"Event Diff:{eventtype} - {interval} - {symbol} - { datetime.now().strftime('%HH:%MM:%SS')} @ {eventdiff}")
                    if DEBUG: data = MarketData.hgetall("L1:" + symbol)


        elif eventtype == "aggTrade":
            symbol = event["symbol"]
            LastPx = MarketData.hget("L1:" + symbol,'price')
            TrendingDown = float(MarketData.hget("L1:" + symbol,'TrendingDown'))
            TrendingUp = float(MarketData.hget("L1:" + symbol,'TrendingUp'))
            MakerCount = float(MarketData.hget("L1:" + symbol,'MakerCount'))
            TakerCount = float(MarketData.hget("L1:" + symbol,'TakerCount'))

            if event["price"] < LastPx:
                TrendingDown+= 1
                TrendingUp= 0
            else:
                TrendingUp+= 1                
                TrendingDown = 0

            LastPx = event["price"]

            #markers and takers 
            is_market_maker = event["is_market_maker"]
            if is_market_maker:
                MakerCount=+ float(event["quantity"])
            else: 
                TakerCount=+ float(event["quantity"])

            if TakerCount>MakerCount:
                MarketPressure = "Bull"
            else:
                MarketPressure = "Bear"

            MarketDataRec = {'price' : LastPx, 'LastQty': event["quantity"], 'TrendingDown': TrendingDown, 'TrendingUp': TrendingUp, 'TakerCount': TakerCount, 'MakerCount': MakerCount,'MarketPressure': MarketPressure,'update': 1 }
            MarketData.hmset("L1:"+symbol, MarketDataRec)
            if eventdiff > 1000:
                print(f"Event Diff:{eventtype} - {LastPx} - {symbol} - { datetime.now().strftime('%HH:%MM:%SS')} @ {eventdiff}")
            if DEBUG: data = MarketData.hgetall("L1:" + symbol)


        elif eventtype == "bookTicker":
            symbol = event["symbol"]
            LastPx = event["best_ask_price"]

            #Experiment 
            askpx = float(event["best_ask_price"])
            bidpx = float(event["best_bid_price"])
            askqty =float(event["best_ask_quantity"])
            bidqty =float(event["best_bid_quantity"])
            spread =  askpx- bidpx 
            WeightedAvgPrice = (askpx * bidqty + bidpx  * askqty) / (askqty + bidqty)
            mid = (bidpx - askpx) / 2
            if bidqty > askqty:
                orderBookdemand = "Bull"
            else:
                orderBookdemand = "Bear"

            MarketDataRec = {'BBPx' : event["best_bid_price"], 'BBQty': event["best_bid_quantity"],'BAPx' : event["best_ask_price"], 'BAQty': event["best_ask_quantity"],'price': LastPx, 'spread': spread, 'WeightedAvgPrice':WeightedAvgPrice,'mid': mid,'orderBookdemand': orderBookdemand, 'update': 1 }
            MarketData.hmset("L1:"+symbol, MarketDataRec)
            if eventdiff > 1000:
                print(f"Event Diff:{eventtype} - {LastPx} - {symbol} - { datetime.now().strftime('%HH:%MM:%SS')} @ {eventdiff}")
            if DEBUG: data = MarketData.hgetall("L1:" + symbol)
        elif eventtype == "error":
            pprint.pprint("ERR:")
            pprint.pprint(event)
            
        if DEBUG: print(data)
        

    except:
        print(event)


    #Write events to log file to allow backtesting 
    if settings.BACKTEST_RECORD:
        file_path = 'backtester/' +  datetime.now().strftime('%Y%m%d_%H_%M') + '.txt'
        with open(file_path, "a") as output_file:
            output_file.write(event + '\n')
        


def is_nan(x):
    return (x == -1 )

def get_data_frame(symbol):
    # On start up get the history from fetch_ohlcv cia cctx 
    # - 5m used to calc the 5min (5T) and 15min (15T)
    # - 15m used to calc the 1min (1T)
    # UPDATED ARE THEN PROCESSED VIA THE WEBSOCKET

    exchange = ccxt.binance()

    #Get 5m data to calc the 5m and 15m
    timeframes = '5m'
    data  = exchange.fetch_ohlcv(symbol, timeframe=timeframes, limit=240)
    df  = pd.DataFrame(data , columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    df['time'] = pd.to_datetime(df['time'],unit='ms')
    df.set_index('time', inplace=True)
    list_of_coins[symbol + '_' + '5T'] = df
        
    calc_timeframes = ['5T', '15T','30T']
    for calc_item in calc_timeframes:	
        dataset = df.resample(calc_item).agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'})
        
        rsi = dataset.ta.rsi()
        adx = dataset.ta.adx()
        macd = dataset.ta.macd(fast=12, slow=26)
        trima = dataset.ta.trima(length=10)
        sma = dataset.ta.sma(length=10)

        get_rsi = rsi[-1:][0]
        get_adx = adx['ADX_14'][len(adx)-1]
        get_macd = macd['MACD_12_26_9'][len(macd)-1]
        get_trima = trima[len(trima)-1]
        get_sma = sma[len(sma)-1]

        MarketDataRec = {'symbol': symbol , 'macd': get_macd,'rsi': get_rsi,'adx': get_adx,'trima':get_trima,'sma':get_sma  }
        MarketData.hmset("TA:"+symbol+calc_item, MarketDataRec)
        MarketData.lpush("TA", "TA:"+symbol+calc_item)

    #get the 1m
    timeframes = '1m'
    data  = exchange.fetch_ohlcv(symbol, timeframe=timeframes, limit=36)
    df  = pd.DataFrame(data , columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    df['time'] = pd.to_datetime(df['time'],unit='ms')
    df.set_index('time', inplace=True)
    list_of_coins[symbol + '_' + '1T'] = df

    rsi = df.ta.rsi()
    adx = df.ta.adx()
    macd = df.ta.macd(fast=12, slow=26)
    trima = df.ta.trima(length=10)
    sma = df.ta.sma(length=10)

    get_rsi = rsi[-1:][0]
    get_adx = adx['ADX_14'][len(adx)-1]
    get_macd = macd['MACD_12_26_9'][len(macd)-1]
    get_trima = trima[len(trima)-1]
    get_sma = sma[len(sma)-1]

    timeframes = '1T'
    MarketDataRec = {'symbol': symbol , 'macd': get_macd,'rsi': get_rsi,'adx': get_adx,'trima':get_trima,'sma':get_sma  }
    MarketData.hmset("TA:"+symbol+timeframes,MarketDataRec)
    MarketData.lpush("TA", "TA:"+symbol+timeframes)
    


#loads config.cfg into settings.XXXXX
settings.init()

# Default no debugging
DEBUG = False
LATENCY_TEST = True

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
MarketData.flushall()

#Collection of dataframes to hold histroic raw data
list_of_coins = {}

def do_work():
    
    try:
        #Start Websocket
        InitializeDataFeed()
    except Exception as e:
        print(f'MarketData_WebSoc: Exception do_work() 1: {e}')
        print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        with open('WebSocket.txt','a+') as f:
            f.write(f'{time.strftime("%Y-%m-%d %H:%M")} |Exception do_work|{e}\n')
    except KeyboardInterrupt:
        print(f'{txcolors.WARNING}Market data feedhandler exiting - do_work.')


# Remove "*3 above 
if __name__ == '__main__':
#Uncomment for Testing Standalone only
    #loads config.cfg into settings.XXXXX
    settings.init()

    client = Client(settings.access_key, settings.secret_key)

    # If the users has a bad / incorrect API key.
    # this will stop the script from starting, and display a helpful error.
    api_ready, msg = test_api_key(client, BinanceAPIException)
    if api_ready is not True:
        exit(f'{txcolors.SELL_LOSS}{msg}{txcolors.DEFAULT}')

    #Start MarketData Thread
    do_work()
# Remove "*3 below 
