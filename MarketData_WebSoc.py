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
import websocket, pprint
import ccxt
import logging

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

# logging needed otherwise slient fails
logger = logging.getLogger('websocket')
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def InitializeDataFeed():
    #######################################
    # (a) Create redis database
    # (b) Define watch list and create a row for every coin 
    # (c) Open Web socket to start collecting market data into the redis database  
    # TO DO: Review: Looking at 3 things - SOCKET_LIST - bookTicker and aggTrade are pretty busy 
    # ######################################    
 
    SOCKET_URL= "wss://stream.binance.com:9443/ws/"
    #SOCKET_LIST = ["coin@bookTicker","coin@kline_1m","coin@aggTrade"]
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

            sleep_time = 2
            num_retries = 4
            
            for x in range(0, num_retries): 
                try:
                    info = client.get_symbol_info(coin)
                    step_size = info['filters'][2]['stepSize']

                    MarketDataRec = {'symbol': coin , 'open': -1, 'high': -1, 'low': -1, 'close': -1, 'potential' : -1, 'interval' : -1,'price' : -1,'LastQty': -1,'BBPx': -1,'BBQty': -1,'BAPx': -1,'BAQty': -1,'updated' : 0, 'step_size' : step_size, 'TrendingDown' : 0, 'spread': 0, 'WeightedAvgPrice': 0, 'mid': 0, 'orderBookDemand': '-',   'TrendingUp': 0 ,  'TakerCount': 0 , 'MakerCount': 0 , 'MarketPressure': '-' }

                    MarketData.hmset("L1:"+coin, MarketDataRec)
                    MarketData.lpush("L1", "L1:"+coin)

                    get_data_frame(coin)  #Needs to move out
                    coinlist= [sub.replace('coin', coin.lower()) for sub in SOCKET_LIST]
                    current_ticker_list.extend(coinlist)
                    CoinsCounter += 1
                except Exception as str_error:
                    print(f'Warning - {str_error} - sleeping for {sleep_time}' )
                    time.sleep(sleep_time)  # wait before trying to fetch the data again
                    sleep_time *= 2  # Implement your backoff algorithm here i.e. exponential backoff
                else:
                    break

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
        print (current_ticker_list) 

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
        SOCKET = SOCKET_URL + '/'.join(current_ticker_list)
        print( str(datetime.now()) + " :Connecting to WebSocket ...")
        if DEBUG: print( str(datetime.now()) + " :Connecting to WebSocket " + SOCKET + " ...")
        web_socket_app = websocket.WebSocketApp(SOCKET, header=['User-Agent: Python'],
                                            on_message=on_message,
                                            on_error=on_error,
                                            on_close=on_close,
                                            on_open=on_open)
        
        web_socket_app.run_forever()
        web_socket_app.close()
    #-------------------------------------------------------------------------------

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
    

#############################START OF WEB SOCKET###########################################
def on_open(ws):
    print("Opened connection.")
    with open('WebSocket.txt','a+') as f:
        f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")} - OPEN\n')


def on_close(ws, close_status_code, close_msg):
    if DEBUG:
        print("Closed connection.")
    with open('WebSocket.txt','a+') as f:
        f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")} - CLOSE \n')


def on_error(ws, error):
    #Handle disconnects/timeouts and try to reconnect 
    if DEBUG:
        print ('On_Error')
        print (os.sys.exc_info()[0:2])
        print ('Error info: %s' %(error))
        with open('WebSocket.txt','a+') as f:
            f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")} |{os.sys.exc_info()[0:2]}|{error}\n')
    
    TriggerRestart = True

    if ( "timed" in str(error) ):
        print ( "WebSocket Connenction is getting timed out: Please check the netwrork connection")
    elif( "getaddrinfo" in str(error) ):
        print ( "Network connection is lost: Cannot connect to the host. Please check the network connection ")
    elif( "unreachable host" in str(error) ):
        print ( "Cannot establish connetion with B6-Web: Network connection is lost or host is not running")
    elif( "remote host was lost" in str(error) ):
        print ( "Connection to remote host was lost: Network connection is lost or host is not running")
    else:
        TriggerRestart = False

    with open('WebSocket.txt','a+') as f:
        f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")} - on_error - restarted: {TriggerRestart} - {error}\n')

    if TriggerRestart:
        #for recreatng the WebSocket connection 
        if ws is not None:
            #ws.close()
            ws.on_message = None
            ws.on_open = None
            ws.close = None    
            print ('deleting ws - ' + str(error))
            del ws
            #Forcebly set ws to None            
            ws = None

        count = 0
        print ( "Websocket Client trying  to re-connect" ) 
        InitializeDataFeed()

def on_message(ws, message):
    ########################################################
    #Handles each event sent and puts it into the correct dataframe (MarketData)
    #TO DO: PING
    ########################################################
    try:
        event = json.loads(message)
        
        #exchange = ccxt.binance()

        try:
            eventtype = event['e'] 
            eventtime = event['E'] 
        except:
            eventtype = "BookTicker"
            eventtime = round(time.time())
   
                
        if DEBUG : print(f"Market data Update: {eventtype} @ {eventtime}")

        if LATENCY_TEST:
            file_path = 'backtester/' +  datetime.now().strftime('%Y%m%d_%H') + '.txt'
            with open(file_path, "a") as output_file:
                utc_timestamp = datetime.utcnow()
                utc_eventtime = datetime.fromtimestamp(eventtime/1000, tz=pytz.utc)
                output_file.write(str(eventtype) + ';' + str(utc_eventtime) + ';' + str(utc_timestamp) + '\n')

        EventRec = {'updated': eventtime }
        MarketData.hmset("UPDATE:"+eventtype, EventRec)

        if eventtype == "kline":
            candle=event['k']
            #Need to check Candle is closed 
            is_candle_closed = candle['x']
            symbol = candle["s"]
            interval = candle["i"]
            closePx = candle["c"]

            #get price, if not set then set it, if BookTicker not enabled then update
            LastPx = MarketData.hget("L1:" + symbol,'price')
            if (search("BookTicker", str(settings.TICKER_ITEMS))== None):
                if is_candle_closed:
                    LastPx = candle["c"]
                else:
                    LastPx = candle["o"]
            potential = -1

            if interval == "1s":
                #1sec/can be used to get prices
                MarketDataRec = {'symbol': symbol ,'price' : LastPx, 'update': 1}
                MarketData.hmset("L1:"+symbol, MarketDataRec)
            elif interval == "1m":
                #1min/called standard 
                OneMinDataSet = list_of_coins[symbol + '_1T'] 
                FiveMinDataSet = list_of_coins[symbol + '_' + '5T']

                if is_candle_closed:

                    #Get Last closed Candle data and prep in dataframe
                    closeminutes = int(datetime.utcfromtimestamp(candle["T"]/1000).strftime('%M'))
                    closedate = datetime.fromtimestamp(candle["T"]/1000, tz=pytz.utc)
                    closedate = closedate.replace(tzinfo=None)
                    LastCandle = {closedate : {'open': float(candle["o"]), 'high':  float(candle["h"]), 'low':  float(candle["l"]),'close':  float(candle["c"]), 'volume' :  float(candle["v"])}}
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
                        highpx =  candle["h"]
                        lowpx = candle["l"]
                else:
                    closePx = candle["o"]
                    
                #session High/low using 1m and 5m combined                 
                SixMinDataSet = pd.concat([OneMinDataSet,FiveMinDataSet])
                column = SixMinDataSet["high"]
                highpx = column.max()
                column = SixMinDataSet["low"]
                lowpx = column.min()
                potential = (float(lowpx) / float(highpx)) * 100
                
                MarketDataRec = {'symbol': symbol , 'open': candle["o"], 'high': highpx, 'low': lowpx, 'close': closePx, 'potential' : potential, 'interval' : interval,'price' : LastPx, 'update': 1}
                MarketData.hmset("L1:"+symbol, MarketDataRec)
                if DEBUG: data = MarketData.hgetall("L1:" + symbol)

        elif eventtype == "aggTrade":
            symbol = event["s"]
            LastPx = MarketData.hget("L1:" + symbol,'price')
            TrendingDown = float(MarketData.hget("L1:" + symbol,'TrendingDown'))
            TrendingUp = float(MarketData.hget("L1:" + symbol,'TrendingUp'))
            MakerCount = float(MarketData.hget("L1:" + symbol,'MakerCount'))
            TakerCount = float(MarketData.hget("L1:" + symbol,'TakerCount'))

            if (search("BookTicker", str(settings.TICKER_ITEMS)) == None):
                LastPx = event["p"]

            if event["p"] < LastPx:
                TrendingDown+= 1
                TrendingUp= 0
            else:
                TrendingUp+= 1                
                TrendingDown = 0

            #markers and takers 
            is_market_maker = event["m"]
            if is_market_maker:
                TakerCount=+ float(event["q"])
            else: 
                MakerCount=+ float(event["q"])

            if TakerCount>MakerCount:
                MarketPressure = "Bull"
            else:
                MarketPressure = "Bear"

            MarketDataRec = {'price' : LastPx, 'LastQty': event["q"], 'TrendingDown': TrendingDown, 'TrendingUp': TrendingUp, 'TakerCount': TakerCount, 'MakerCount': MakerCount,'MarketPressure': MarketPressure,'update': 1 }
            MarketData.hmset("L1:"+symbol, MarketDataRec)
            if DEBUG: data = MarketData.hgetall("L1:" + symbol)


        elif eventtype == "BookTicker":
            symbol = event["s"]
            ClosePx = MarketData.hget("L1:" + symbol,'close' )

            #fall back as aggTrade or close may not be in yet
            if float(ClosePx) == -1:
                ClosePx = event["a"]

            LastPx = event["a"]

            #Experiment 
            askpx = float(event["a"])
            bidpx = float(event["b"])
            askqty =float(event["A"])
            bidqty =float(event["B"])
            spread =  askpx- bidpx 
            WeightedAvgPrice = (askpx * bidqty + bidpx  * askqty) / (askqty + bidqty)
            mid = (bidpx - askpx) / 2
            if bidqty > askqty:
                orderBookdemand = "Bull"
            else:
                orderBookdemand = "Bear"

            MarketDataRec = {'BBPx' : event["b"], 'BBQty': event["B"],'BAPx' : event["a"], 'BAQty': event["A"],'price': LastPx,'close': ClosePx, 'spread': spread, 'WeightedAvgPrice':WeightedAvgPrice,'mid': mid,'orderBookdemand': orderBookdemand, 'update': 1 }
            MarketData.hmset("L1:"+symbol, MarketDataRec)
            if DEBUG: data = MarketData.hgetall("L1:" + symbol)
        elif eventtype == "Ping":
            pong_json = { 'Type':'Pong' }
            ws.send(json.dumps(pong_json))
            print("SENT:")
            print(json.dumps(pong_json, sort_keys=True, indent=2, separators=(',', ':')))
        elif eventtype == "error":
            pprint.pprint("ERR:")
            pprint.pprint(event)

        if DEBUG:
            print(data)
            print("------" + eventtype + "------")


        #Write events to log file to allow backtesting 
        if settings.BACKTEST_RECORD:
            file_path = 'backtester/' +  datetime.now().strftime('%Y%m%d_%H_%M') + '.txt'
            with open(file_path, "a") as output_file:
                output_file.write(message + '\n')
        
    except KeyboardInterrupt as ki:
        pass
        #print(f'{txcolors.WARNING}Market data feedhandler exixting - on_message.')
        #sys.exit(0)    

#############################END OF WEB SOCKET###########################################

#loads config.cfg into settings.XXXXX
settings.init()

# Default no debugging
DEBUG = False
LATENCY_TEST = False

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
if settings.WEBSOCKET: MarketData.flushall()

#Collection of dataframes to hold histroic raw data
list_of_coins = {}

def do_work():
    
    try:
        #Start Websocket
        if settings.WEBSOCKET: InitializeDataFeed()
    except Exception as e:
        print(f'MarketData_WebSoc: Exception do_work() 1: {e}')
        print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        with open('WebSocket.txt','a+') as f:
            f.write(f'{time.strftime("%Y-%m-%d %H:%M")} |Exception do_work|{e}\n')
    except KeyboardInterrupt:
        print(f'{txcolors.WARNING}Market data feedhandler exiting - do_work.')

"""
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
"""