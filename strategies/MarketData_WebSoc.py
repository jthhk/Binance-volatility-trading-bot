# use for environment variables
import os

# use if needed to pass args to external modules
import sys

# used for math functions
import math

# used to create threads & dynamic loading of modules
import threading
import multiprocessing
import importlib

# used for directory handling
import glob

#discord needs import request
import requests

#redis
import redis

# Added for WebSocket Support
import pandas as pd
import pandas_ta as ta
import websocket, pprint
import ccxt
import logging

# Needed for colorful console output Install with: python3 -m pip install colorama (Mac/Linux) or pip install colorama (PC)
from colorama import init
init()

# needed for the binance API / websockets / Exception handling
from binance.client import Client
from binance.exceptions import BinanceAPIException
from binance.helpers import round_step_size
from requests.exceptions import ReadTimeout, ConnectionError

# used for dates
from datetime import date, datetime, timedelta
import time

# used to repeatedly execute the code
from itertools import count

# used to store trades and sell assets
import json

# used to display holding coins in an ascii table
from prettytable import PrettyTable

# Load helper modules
from helpers.parameters import (
    parse_args, load_config
)

# Load creds modules
from helpers.handle_creds import (
    load_correct_creds, test_api_key,
    load_discord_creds
)

# my helper utils
from helpers.os_utils import(rchop)

from threading import Thread, Event

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
    SOCKET_LIST = ["coin@bookTicker","coin@kline_1m","coin@aggTrade"]
    current_ticker_list = []
    #-------------------------------------------------------------------------------
    # (a) Create redis database (MarketData) with a hash and list collection
    #  Hash Keys: L1:{Coin} -> which has Level 1 market data fields, see MarketDataRec 
    #  list Keys: L1 -> L1:{Coin}
    #  Why: I added the list sorting of the hash, otherwise I could not sort
    # (b) Define watch list of coins we want to monitor, see SOCKET_LIST + current_ticker_list 
    CoinsCounter = 0
    tickers = [line.strip() for line in open(TICKERS_LIST)]
    print( str(datetime.now()) + " :Preparing watch list defined in tickers file...")
    for item in tickers:
        #Create Dataframes with coins
        coin = item + PAIR_WITH
        data =  {'symbol': coin}
        MarketDataRec = {'symbol': coin , 'open': CoinsCounter, 'high': -1, 'low': -1, 'close': -1, 'potential' : -1, 'interval' : -1,'LastPx' : -1,'LastQty': -1,'BBPx': -1,'BBQty': -1,'BAPx': -1,'BAQty': -1,'updated' : -1}
        MarketData.hmset("L1:"+coin, MarketDataRec)
        MarketData.lpush("L1", "L1:"+coin)
        #get_data_frame(coin)  #Needs to move out
        coinlist= [sub.replace('coin', coin.lower()) for sub in SOCKET_LIST]
        current_ticker_list.extend(coinlist)
        CoinsCounter += 1

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

    #-------------------------------------------------------------------------------
    # (c) Create a Web Socket to get the market data 
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

    global MarketPriceFrames

    exchange = ccxt.binance()
    timeframes = ['5m','15m','4h', '1d']
    for item in timeframes:	
        macd = exchange.fetch_ohlcv(symbol, timeframe=item, limit=36)
        df1  = pd.DataFrame(macd, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        macd = df1.ta.macd(fast=12, slow=26)
        Index = MarketPriceFrames.loc[MarketPriceFrames['symbol'] == symbol].index.item()
        MarketPriceFrames.loc[Index, item] =  macd.iloc[35][1]
        MarketPriceFrames.loc[Index, ['updated']] = datetime.now()

#############################START OF WEB SOCKET###########################################
def on_open(ws):
    print("Opened connection.")

def on_close(ws, close_status_code, close_msg):
    if DEBUG:
        print("Closed connection.")

def on_error(ws, error):
    #Handle disconnects/timeouts and try to reconnect 
    if DEBUG:
        print ('On_Error')
        print (os.sys.exc_info()[0:2])
        print ('Error info: %s' %(error))
    
    TriggerRestart = False

    if ( "timed" in str(error) ):
        print ( "WebSocket Connenction is getting timed out: Please check the netwrork connection")
    elif( "getaddrinfo" in str(error) ):
        print ( "Network connection is lost: Cannot connect to the host. Please check the network connection ")
    elif( "unreachable host" in str(error) ):
        print ( "Cannot establish connetion with B6-Web: Network connection is lost or host is not running")
    else:
        TriggerRestart = False    

    if TriggerRestart:
        #for recreatng the WebSocket connection 
        if ws is not None:
            #ws.close()
            ws.on_message = None
            ws.on_open = None
            ws.close = None    
            print ('deleting ws')
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
    event = json.loads(message)
    
    try:
        eventtype = event['e'] 
    except:
        eventtype = "BookTicker"
    
    if DEBUG : print(f"{eventtype} event")

    try:
        if eventtype == "kline":
            candle=event['k']
            #Need to check Candle is closed 
            is_candle_closed = candle['x']
            symbol = candle["s"]
            interval = candle["i"]
            closePx = candle["c"]
            potential = -1


            if interval == "1m":
                #1min/called standard

                LastPx = MarketData.hget("L1:" + symbol,'LastPx' )
                if is_candle_closed:
                    potential = (float(candle["l"]) / float(candle["h"])) * 100
                else:
                    closePx = candle["o"]

                if float(LastPx) == -1:
                    LastPx = closePx
                
                MarketDataRec = {'symbol': symbol , 'open': candle["o"], 'high': candle["h"], 'low': candle["l"], 'close': closePx, 'potential' : potential, 'interval' : interval,'LastPx' : LastPx}
            else:
                interval = candle["i"]
                LastPx = candle["o"]
                MarketDataRec = {'LastPx' : LastPx}
            
            MarketData.hmset("L1:"+symbol, MarketDataRec)
            data = MarketData.hgetall("L1:" + symbol)

        elif eventtype == "aggTrade":
            symbol = event["s"]
            MarketDataRec = {'LastPx' : event["p"], 'LastQty': event["q"] }
            MarketData.hmset("L1:"+symbol, MarketDataRec)
            data = MarketData.hgetall("L1:" + symbol)
            #is_market_maker = event['x']
            #side = "B" 
            #if is_market_maker:
            #    side = "S" 
        elif eventtype == "BookTicker":
            symbol = event["s"]
            ClosePx = MarketData.hget("L1:" + symbol,'close' )
            LastPx = MarketData.hget("L1:" + symbol,'LastPx' )

            #fall back as aggTrade or close may not be in yet
            if float(ClosePx) == -1:
                LastPx = event["a"]

            if float(LastPx) == -1:
                LastPx = event["a"]

            MarketDataRec = {'BBPx' : event["b"], 'BBQty': event["B"],'BAPx' : event["a"], 'BAQty': event["A"],'LastPx': LastPx,'close': ClosePx }
            MarketData.hmset("L1:"+symbol, MarketDataRec)
            data = MarketData.hgetall("L1:" + symbol)
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
    except KeyboardInterrupt as ki:
        sys.exit(0)    

#############################END OF WEB SOCKET###########################################

args = parse_args()
DEFAULT_CONFIG_FILE = 'config.yml'
DEFAULT_CREDS_FILE = 'creds.yml'

config_file = args.config if args.config else DEFAULT_CONFIG_FILE
creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
parsed_config = load_config(config_file)
parsed_creds = load_config(creds_file)

# Default no debugging
DEBUG = False

# Load system vars
TEST_MODE = parsed_config['script_options']['TEST_MODE']
DEBUG_SETTING = parsed_config['script_options'].get('DEBUG')
AMERICAN_USER = parsed_config['script_options'].get('AMERICAN_USER')
DATABASE = parsed_config['script_options']['DATABASE']

# Load trading vars
PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']
FIATS = parsed_config['trading_options']['FIATS']

CUSTOM_LIST = parsed_config['trading_options']['CUSTOM_LIST']
CUSTOM_LIST_AUTORELOAD = parsed_config['trading_options']['CUSTOM_LIST_AUTORELOAD']
TICKERS_LIST = parsed_config['trading_options']['TICKERS_LIST']

#define redis DataBase connection and flush it
MarketData = redis.Redis(host='app', port=6379, db=DATABASE,decode_responses=True)
MarketData.flushall()

def do_work():
    
    try:
        #Start Websocket
        InitializeDataFeed()
    except Exception as e:
        print(f'MarketData_WebSoc: Exception do_work() 1: {e}')
        print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
    except KeyboardInterrupt:
        sys.exit(0)   