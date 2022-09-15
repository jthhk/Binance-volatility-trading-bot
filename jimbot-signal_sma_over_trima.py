import time
from datetime import datetime

import sys
import os

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

    try:
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
                        # change risk level:  0.5 = 50% below high_price-Lowpx (spread)
                        percent_below = 0.5  
                        
                        # movement can be either:
                        #  "MOVEMENT" for original movement calc
                        MOVEMENT = 'MOVEMENT'

                        #-----------------------------------------------------------------
                        #Get the latest market data from the dataframes
                        last_price = float(data['price'])
                        high_price = float(data['high'])
                        low_price = float(data['low' ])
                        bid_price = float(data['BBPx'])
                        ask_price = float(data['BAPx'])
                        close_price = float(data['close'])
                        #current_bid = float(data['BBPx'])
                        #current_ask = float(data['BAPx'])
                        potential = float(data['potential'])  # (session Low/High)*100

                        #spread = float(data['spread'])  #ask-Bid
                        #WeightedAvgPrice = float(data['WeightedAvgPrice'])  # ((Askpx * BuyQty) (Bidpx * AskQty)) / (BuyQty+BuyQty)
                        #mid = float(data['mid'])  #Bid-Ask/2
                        #orderBookDemand = data['orderBookDemand']  #BidQty > AskQty = Bull else Bear

                        #TrendingDown = float(data['TrendingDown'])  #count inc if trade px is < last one, resets to 0 once direction changes
                        TrendingUp = float(data['TrendingUp'])  #count inc if trade px is > last one, resets to 0 once direction changes
                        #TakerCount = float(data['TakerCount'])  #cum vol of Taker trades
                        #MakerCount = float(data['MakerCount'])  #cum vol of marker trades
                        MarketPressure = data['MarketPressure']  #TakerCount > MakerCount = Bull else Bear
                        
                        #Candle data 
                        TA_1m = MarketData.hgetall('TA:'+symbol+'1T')
                        TA_5m = MarketData.hgetall('TA:'+symbol+'5T')
                        TA_15m = MarketData.hgetall('TA:'+symbol+'15T')

                        #MACD hist crossing above zero is considered bullish, while crossing below zero is bearish.
                        macd1m = float(TA_1m['macd'])
                        macd5m = float(TA_5m['macd'])
                        macd15m = float(TA_15m['macd'])

                        # If SMA IS LESS THAN TRIMA not Good
                        curve = float(TA_5m['trima'])
                        sma = float(TA_5m['sma'])

                        #If the RSI is over 70, this is generally seen as over-bought and price might move down. 
                        #A reading of 30 indicates a market that is over-sold and price might move up
                        #------------------------------
                        #rsi1m = float(TA_1m['rsi'])
                        #rsi5m = float(TA_5m['rsi'])
                        #rsi15m = float(TA_15m['rsi'])

                        #ADX Value	Trend Strength (up or down)
                        #0-25	Absent or Weak Trend
                        #25-50	Strong Trend
                        #50-75	Very Strong Trend / 
                        #75-100	Extremely Strong Trend
                        #------------------------------
                        #adx1m = float(TA_1m['adx'])
                        adx5m = float(TA_5m['adx'])
                        #adx15m = float(TA_15m['adx'])

                        #Standard Strategy Calcs 
                        #using last Candle lowpx and highpx 
                        range = float(high_price - low_price)
                        buy_below = float(high_price - (range * percent_below))
                                            
                        #using last Candle highpx and last trade price, if last trade nan then fall back to lowpx or AskPx
                        current_range = float(high_price - last_price)
                        #buy_current_below = float(high_price - (current_range * percent_below))

                        #it is possible to have the samw High/low/last trade resulting in "Cannot divide by zero"
                        movement = (current_range/high_price) * 100 if current_range > 0 else 0

                        BuyCoin = False
                        #-----------------------------------------------------------------
                        #Do your custom strategy calcs

                        #it is possible to have the same current_range=0 resulting in "Cannot divide by zero"
                        current_drop = (100 * current_range) / high_price if current_range > 0 else 0

                        #-----------------------------------------------------------------
                        #Do your strategy check here
                        #-----------------------------------------------------------------
                        TimeFrameCheck = False 

                        #Main Strategy checker
                        TimeFrameCheck = (sma > curve) 
                        if TimeFrameCheck:
                            BuyCoin = True
                        #-----------------------------------------------------------------
                        #Buy coin check
                        if BuyCoin:
                            CoinsBuyCounter += 1
                            # add to signal
                            try:
                                with open(f'signals/{SIGNAL_NAME}{signal_file_type_buy}', 'a+') as f:
                                    f.write(str(symbol) + '\n')
                                    if settings.DEBUG: print(f'{str(datetime.now())}:{SIGNAL_NAME} - BUY - {symbol} \n')
                            except Exception as e:
                                time.sleep(1)
                                continue
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
                                f'Buy Below:{buy_below:.3f} |'
                                f'Potential profit:{potential:.0f} |'
                                f'Buy Below:{buy_below:.3f} \n'
                                f'\n-----------Strategy Calcs based off closed last candle---------\n'
                                f'Day Max Range (lstpx):{current_range:.3f} |'
                                f'Movement:{movement:.2f}\n'
                                f'\n------------Custom calcs-----------------------\n'
                                f'{Custom_Fields}'
                                f'----------------------------------------------\n'
                                f'Last Update:{datetime.now()} \n'
                                )
                            print('\n\n-------MACD--------\n'
                                f'macd1m:{macd1m} |'
                                f'macd5m:{macd5m} |'
                                f'macd15m:{macd15m}\n'
                                )
        
                if block_info:
                    timetaken = time.time() - StartTime
                    print(f'{str(datetime.now())}:Time(sec): {timetaken} |Total Coins Scanned: {CoinsCounter} |Skipped:{CoinsSkippedCounter} |Reviewed:{CoinsCounter - (CoinsSkippedCounter + CoinsBuyCounter)} |Bought:{CoinsBuyCounter}')
        
        if CoinsCounter == 0 and settings.BACKTEST_PLAY:
            print('Signal file exiting as no coins in the MarketData redis database.')
            sys.exit(0)
    except KeyboardInterrupt:
        print('Signal file exiting from DoCycle.')
           

def do_work():
    
    global MarketData
    
    settings.init()
    MarketData = redis.Redis(host='host', port=6379, db=settings.DATABASE,decode_responses=True)
    try:
        while True:
            DoCycle()
            time.sleep(settings.RECHECK_INTERVAL * 2 ) 
    except KeyboardInterrupt:
        print('Signal file exiting from do_work.')
        sys.exit(0)
