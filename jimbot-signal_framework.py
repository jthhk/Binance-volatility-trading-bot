import time
from datetime import date, datetime

import sys
import os

import json

#redis
import redis

#dataframes
import pandas as pd

#global Settings 
import settings

# System Settings
signal_file_type_buy = '.buy'


#TODO move to config file
SIGNAL_NAME = 'jimbot_signal'
block_info = False


def DoCycle():

    CoinsSkippedCounter = 0 
    CoinsCounter = 0
    CoinsBuyCounter = 0
    Custom_Fields = ""
    StartTime = time.time()

    #Get Held coins so we don't but 2 of the same
    held_coins_list = pd.DataFrame(columns=['symbol', 'orderId', 'timestamp', 'avgPrice', 'volume', 'tradeFeeBNB','tradeFeeUnit','take_profit','stop_loss'])
    if os.path.isfile(settings.coins_bought_file_path) and os.stat(settings.coins_bought_file_path).st_size!= 0:
        held_coins_list = pd.read_json(settings.coins_bought_file_path, orient ='split', compression = 'infer')
        held_coins_list.head()
    else:
        held_coins_list = pd.DataFrame(columns=['symbol', 'orderId', 'timestamp', 'avgPrice', 'volume', 'tradeFeeBNB','tradeFeeUnit','take_profit','stop_loss'])

    #Get bitcoinpx for ref 
    get_histbtc = float(49000)  # TODO Source
    
    #Do the coins with the  most potential
    GetCoinsInOrder = MarketData.sort('L1',alpha=True,desc=False,by='*->potential')

    #Get latest prices from database
    for key in GetCoinsInOrder:
        data = MarketData.hgetall(key)
        
        if len(data) > 1 and bool(data['updated']) and float(data['price']) > 0:
            symbol = data['symbol']
            CoinAlreadyBought = held_coins_list[held_coins_list['symbol'].str.contains(symbol)]    
            if len(CoinAlreadyBought.index) == 0:
                CoinsCounter += 1
                if symbol in held_coins_list.index:
                    CoinsSkippedCounter += 1
                    if block_info:   
                        print(f'{symbol} Skipping as we already holding \n')
                else:
                    # Set your custom Strategy Settings
                    profit_max = 100  # only required if you want to limit max profit
                    profit_min = 15

                    # change risk level:  0.7 = 70% below high_price, 0.5 = 50% below high_price
                    percent_below = 0.6  
                    
                    # movement can be either:
                    #  "MOVEMENT" for original movement calc
                    #  "ATR_MOVEMENT" for Average True Range Percentage calc
                    MOVEMENT = 'MOVEMENT'

                    #-----------------------------------------------------------------
                    #Get the latest market data from the dataframes
                    last_price = float(data['price'])
                    high_price = float(data['high'])
                    low_price = float(data['low' ])
                    bid_price = float(data['BBPx'])
                    ask_price = float(data['BAPx'])
                    close_price = float(data['close'])
                    current_bid = float(data['BBPx'])
                    current_ask = float(data['BAPx'])
                    potential = float(data['potential'])  # (Low/High)*100

                    spread = float(data['spread'])  #ask-Bid
                    WeightedAvgPrice = float(data['WeightedAvgPrice'])  # ((Askpx * BuyQty) (Bidpx * AskQty)) / (BuyQty+BuyQty)
                    mid = float(data['mid'])  #Bid-Ask/2
                    orderBookDemand = data['orderBookDemand']  #BidQty > AskQty = Bull else Bear

                    TendingDown = float(data['TendingDown'])  #count inc if trade px is < last one, resets to 0 once direction changes
                    TendingUp = float(data['TendingUp'])  #count inc if trade px is > last one, resets to 0 once direction changes
                    TakerCount = float(data['TakerCount'])  #cum vol of Taker trades
                    MakerCount = float(data['MakerCount'])  #cum vol of marker trades
                    MarketPressure = data['MarketPressure']  #TakerCount > MakerCount = Bull else Bear
                    
                    #Candle data 
                    macd1m = float(data['open'])  
                    macd5m = float(100)
                    macd15m = float(100)
                    macd4h = float(100)
                    macd1d = float(100)

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

                    #Different MOVEMENT models 
                    if MOVEMENT == "MOVEMENT":
                        TimeFrameOption = (movement >= (settings.TRAILING_TAKE_PROFIT + 0.2))
                    elif MOVEMENT ==  "ATR_MOVEMENT":
                        TimeFrameOption = (atr_percentage >= settings.TRAILING_TAKE_PROFIT)
                    else:
                        TimeFrameOption = True

                    #Main Strategy checker
                    if TimeFrameOption:
                        RealTimeCheck = (profit_min < current_potential < profit_max and last_price < buy_below)
                        if RealTimeCheck:
                            TimeFrameCheck = (macd1m >= 0 and macd5m  >= 0 and macd15m >= 0 and macd1d >= 0 and get_histbtc >= 0)
                            if TimeFrameCheck:
                                BuyCoin = True

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
                        with open(f'signals/{SIGNAL_NAME}{signal_file_type_buy}', 'a+') as f:
                            f.write(str(symbol) + '\n')
                            print(f'{str(datetime.now())}:{SIGNAL_NAME} - BUY - {symbol} \n')

                    #-----------------------------------------------------------------
                    #Debug Output
                    #may change this to output to a file
                    if settings.DEBUG:
                        print (f'-------DEBUG--------\n')
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
                timetaken = time.time() - StartTime
                print(f'{str(datetime.now())}:Time(sec): {timetaken} |Total Coins Scanned: {CoinsCounter} |Skipped:{CoinsSkippedCounter} |Reviewed:{CoinsCounter - (CoinsSkippedCounter + CoinsBuyCounter)} |Bought:{CoinsBuyCounter}')
    
    if CoinsCounter == 0 and settings.BACKTEST_PLAY:
        print('Signal file exiting as no coins in the MarketData redis database.')
        sys.exit(0)

def do_work():
    
    global MarketData
    
    settings.init()
    MarketData = redis.Redis(host='localhost', port=6379, db=settings.DATABASE,decode_responses=True)
    try:
        while True:
            DoCycle()
            time.sleep(settings.RECHECK_INTERVAL * 2 ) 
    except KeyboardInterrupt:
        sys.exit(0)
