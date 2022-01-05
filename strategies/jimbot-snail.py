import time
from datetime import datetime

import requests
from helpers.parameters import parse_args, load_config
import pandas as pd
import pandas_ta as ta
import sys
import os
import websocket, json,pprint
import threading
from threading import Thread, Event
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
import ccxt

# Load creds modules
from helpers.handle_creds import (
	load_correct_creds, load_discord_creds
)

# Settings
args = parse_args()
DEFAULT_CONFIG_FILE = 'config.yml'
DEFAULT_CREDS_FILE = 'creds.yml'

config_file = args.config if args.config else DEFAULT_CONFIG_FILE
creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
parsed_creds = load_config(creds_file)
parsed_config = load_config(config_file)

# Load trading vars
PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']
EX_PAIRS = parsed_config['trading_options']['FIATS']
TEST_MODE = parsed_config['script_options']['TEST_MODE']
TAKE_PROFIT = parsed_config['trading_options']['TAKE_PROFIT']
DEBUG = parsed_config['script_options']['DEBUG']
DISCORD_WEBHOOK = load_discord_creds(parsed_creds)

# Load creds for correct environment
print("Loading access_key....")
access_key, secret_key = load_correct_creds(parsed_creds)
client = Client(access_key, secret_key)


# If True, an updated list of coins will be generated from the site - http://edgesforledges.com/watchlists/binance.
# If False, then the list you create in TICKERS_LIST = 'tickers.txt' will be used.
CREATE_TICKER_LIST = False

# When creating a ticker list from the source site:
# http://edgesforledges.com you can use the parameter (all or innovation-zone).
# ticker_type = 'innovation-zone'
ticker_type = 'all'
if CREATE_TICKER_LIST:
	TICKERS_LIST = 'tickers_all_USDT.txt'
else:
	TICKERS_LIST = 'tickers.txt'

# System Settings
BVT = False
OLORIN = True  # if not using Olorin Sledge Fork set to False
if OLORIN:
	signal_file_type = '.buy'
else:
	signal_file_type = '.exs'

# send message to discord
DISCORD = False

# Display Setttings
all_info = False
block_info = True

# buy coin file 
if TEST_MODE:
    coin_path = 'test_coins_bought.json'
else:
    if BVT:
        coin_path = 'coins_bought.json'
    else:
        coin_path = 'live_coins_bought.json'

class TextColors:
	BUY = '\033[92m'
	WARNING = '\033[93m'
	SELL_LOSS = '\033[91m'
	SELL_PROFIT = '\033[32m'
	DIM = '\033[2m\033[35m'
	DEFAULT = '\033[39m'
	YELLOW = '\033[33m'
	TURQUOISE = '\033[36m'
	UNDERLINE = '\033[4m'
	END = '\033[0m'
	ITALICS = '\033[3m'
	TCR = '\033[91m'
	TCG = '\033[32m'
	TCD = '\033[39m'

def msg_discord(msg):

	message = msg + '\n\n'

	mUrl = "https://discordapp.com/api/webhooks/"+DISCORD_WEBHOOK
	data = {"content": message}
	response = requests.post(mUrl, json=data)

def do_work(MarketData,MarketPriceFrames):
    
    if DEBUG : print ("DEBUG is enabled - get ready for lots of data, may want to use block_info instead")
    
    #exchange = ccxt.binance()

    #(a) Setup the ticker dataframe and Websockets
    #InitializeDataFeed()

    try:
        while True:

            held_coins_list = {}            
            CoinsCounter = 0
            CoinsSkippedCounter = 0 
            CoinsBuyCounter = 0
            Custom_Fields = ""
            start_time = time.time()

            #Get Held coins so we don't but 2 of the same
            if os.path.isfile(coin_path) and os.stat(coin_path).st_size != 0:
                with open(coin_path) as file:
                    held_coins_list = json.load(file)	

            #Get bitcoinpx for ref 
            exchange = ccxt.binance()
            macdbtc = exchange.fetch_ohlcv('BTCUSDT', timeframe='1m', limit=36)
            dfbtc = pd.DataFrame(macdbtc, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            macdbtc = dfbtc.ta.macd(fast=12, slow=26)
            get_histbtc = float(macdbtc.iloc[35, 1])
            
            #Do the coins with the  most potential
            MarketData.sort_values('potential', ascending=False)
            for index, row in enumerate(MarketData.itertuples(), 1):                         
                symbol = row.symbol
                print(f'{TextColors.DEFAULT}{symbol} updated1 - {row.updated} \n')

                CoinsCounter += 1
                if (symbol in held_coins_list):
                    CoinsSkippedCounter += 1
                    if block_info:   
                        print(f'{TextColors.DEFAULT}{symbol} Skipping as we already holding \n')
                else:
                    #-----------------------------------------------------------------
                    # Set your custom Strategy Settings
                    profit_min = 15
                    profit_max = 100  # only required if you want to limit max profit
                    
                    # change risk level:  0.7 = 70% below high_price, 0.5 = 50% below high_price
                    percent_below = 0.6  
                    
                    # movement can be either:
                    #  "MOVEMENT" for original movement calc
                    #  "ATR_MOVEMENT" for Average True Range Percentage calc
                    MOVEMENT = 'MOVEMENT'

                    #No idea
                    DROP_CALCULATION = False
                    #-----------------------------------------------------------------
                    #Get the latest market data from the dataframes
                    last_price = float(row.LastPx)
                    high_price = float(row.high)
                    low_price = float(row.low)
                    bid_price = float(row.BBPx)
                    ask_price = float(row.BAPx)
                    close_price = float(row.close)
                    current_bid = float(row.BBPx)
                    current_ask = float(row.BAPx)
                    potential = float(row.potential)
                    #Candle data 
                    TimeFrames = MarketPriceFrames.loc[MarketPriceFrames['symbol'] == symbol]
                    macd5m = float(TimeFrames['5m'].values[0])
                    macd15m = float(TimeFrames['15m'].values[0])
                    macd4h = float(TimeFrames['4h'].values[0])
                    macd1d = float(TimeFrames['1d'].values[0])
                    
                    #Standard Strategy Calcs 
                    #using last Candle lowpx and highpx 
                    range = float(high_price - low_price)
                    buy_above = float(low_price * 1.00)
                    buy_below = float(high_price - (range * percent_below))
                    max_potential = float(potential * profit_max)
                    min_potential = float(potential * profit_min)
                                        
                    #using last Candle highpx and last trade price, if last trade nan then fall back to lowpx or AskPx
                    current_range = float(high_price - last_price)
                    current_potential = float((last_price / high_price) * 100)
                    current_buy_above = float(last_price * 1.00)
                    current_buy_below = float(high_price - (current_range * percent_below))
                    current_max_potential = float(current_potential * profit_max) 
                    current_min_potential = float(current_potential * profit_min)

                    if current_range == 0: 
                        #it is possible to have the samw High/low/last trade resulting in "Cannot divide by zero"
                        movement = 0
                    else:
                        movement = (low_price / current_range)   

                    macd1m = float(row.open)  
                    BuyCoin = False
                    #-----------------------------------------------------------------
                    #Do your custom strategy calcs
                    if current_range == 0: 
                        #it is possible to have the samw current_range=0 resulting in "Cannot divide by zero"
                        current_drop = (100 * (current_range)) / high_price
                    else:
                        current_drop = 0

                    atr = []               # average true range
                    atr.append(high_price-low_price)
                    atr_percentage = ((sum(atr)/len(atr)) / close_price) * 100
                    #-----------------------------------------------------------------
                    #Do your strategy check here
                    #-----------------------------------------------------------------
                    RealTimeCheck = False
                    TimeFrameCheck = False 
                    TimeFrameOption = False

                    if DROP_CALCULATION:
                        current_potential = current_drop
                    
                    #Different MOVEMENT models 
                    if MOVEMENT == "MOVEMENT":
                        TimeFrameOption = (movement >= (TAKE_PROFIT + 0.2))
                    elif MOVEMENT ==  "ATR_MOVEMENT":
                        TimeFrameOption = (atr_percentage >= TAKE_PROFIT)
                    else:
                        TimeFrameOption = True

                    #Main Strategy checker
                    if TimeFrameOption:
                        RealTimeCheck = (profit_min < current_potential < profit_max and last_price < buy_below)
                        if RealTimeCheck:
                            TimeFrameCheck = (macd1m >= 0 and macd5m  >= 0 and macd15m >= 0 and macd1d >= 0 and get_histbtc >= 0)
                            if TimeFrameCheck:
                                BuyCoin = True

                    #Custom logging output for the algo
                    if all_info:
                        print(f'{TextColors.DEFAULT}{symbol} RealTimecheck:{RealTimeCheck} Timeframecheck:{TimeFrameCheck} TimeFrameOption: {TimeFrameOption} \n')
                        print ("-------DEBUG--------")
                        print(f'\nCoin:            {symbol}\n'
                              f'CHECK1 True:       {(profit_min < current_potential < profit_max)} \n'
                              f'CHECK2 True:       {(last_price < buy_below)} \n'
                              f'Data 1 :           {profit_min} | {current_potential} | {profit_max} | {last_price} | {buy_below}  \n'
                              f'Data 2 :           {macd1m} | {macd5m} | {macd15m} | {macd1d} |  {get_histbtc} \n'
                              )

                    #Custom logging output for generic debug mode below
                    Custom_Fields = (
                                    "current_drop:" + str(current_drop) + "|" 
                                    "atr_percentage:" + str(atr_percentage)  + "\n" 
                                    )

                    #-----------------------------------------------------------------
                    #Buy coin check
                    if BuyCoin:
                        CoinsBuyCounter += 1
                        # add to signal
                        with open(f'signals/snail_scan{signal_file_type}', 'a+') as f:
                            f.write(str(symbol) + '\n')
                            print(f'{TextColors.BUY}{str(datetime.now())}:{symbol} \n')


                    #-----------------------------------------------------------------
                    #Debug Output
                    #may change this to output to a file
                    if DEBUG:
                        print (f'{TextColors.DEFAULT}-------DEBUG--------\n')
                        print(f'\nCoin:            {symbol}\n'
                            f'\n------------------Market Data---------------\n'
                            f'Price:{last_price:.3f} |'
                            f'Bid:{bid_price:.3f} |'
                            f'Ask:{ask_price:.3f} |'
                            f'High:{high_price:.3f} |'
                            f'Low:{low_price:.3f} |'
                            f'Close:{close_price:.3f}\n'
                            f'\n-----------------Standard Strategy Calcs---------------\n'
                            f'Day Max Range:{range:.3f} |'
                            f'Buy above:{buy_above:.3f} |'
                            f'Buy Below:{buy_below:.3f} |'
                            f'Potential profit:{potential:.0f} |'
                            f'Potential max profit:{max_potential:.0f} |'
                            f'Potential min profit:{min_potential:.0f}  |n'
                            f'Buy above:{buy_above:.3f} |'
                            f'Buy Below:{buy_below:.3f} \n'
                            f'\n-----------Strategy Calcs based off closed last candle---------\n'
                            f'Day Max Range (lstpx):{current_range:.3f} |'
                            f'Potential profit(lstpx):{current_potential:.0f} |'
                            f'Potential max profit:{current_max_potential:.0f} |'
                            f'Potential min profit:{current_min_potential:.0f} |'
                            f'Buy above (lstpx):{current_buy_above:.3f} |'
                            f'Buy Below(lstpx):{current_buy_below:.3f} |'
                            f'Movement:{movement:.2f}\n'
                            f'\n------------Custom calcs-----------------------\n'
                            f'{Custom_Fields}'
                            f'----------------------------------------------\n'
                            f'Last Update:{datetime.now()} \n'
                            )
                        print('\n\n-------MACD--------\n'
                            f'macd1m:{macd1m} |'
                            f'macd5m:{macd5m} |'
                            f'macd15m:{macd15m} |'
                            f'macd4h:{macd4h} |'
                            f'macd1d:{macd1d}\n'
                            )
                        print ("\n-------Bitcoin--------")
                        print (f"get_histbtc:   {get_histbtc}")

            
            if block_info:
                print(f'{str(datetime.now())}:Time(sec): {time.time() - start_time} |Total Coins Scanned: {CoinsCounter} |Skipped:{CoinsSkippedCounter} |Reviewed:{CoinsCounter - (CoinsSkippedCounter + CoinsBuyCounter)} |Bought:{CoinsBuyCounter}')

            time.sleep(3)
            
    except Exception as e:
        print(str(e))
        print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
        
        #only pushing data from dataframe to help debug 
        print(f'\nCoin:            {symbol}\n'
            f'Price:               ${last_price:.3f}\n'
            f'Bid:                 ${bid_price:.3f}\n'
            f'Ask:                 ${ask_price:.3f}\n'
            f'High:                ${high_price:.3f}\n'
            f'Low:                 ${low_price:.3f}\n'
            f'Close:               ${close_price:.3f}\n'
            )
    except KeyboardInterrupt:
        print("KeyboardInterrupt")