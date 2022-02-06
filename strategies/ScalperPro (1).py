# Available indicators here: https://python-tradingview-ta.readthedocs.io/en/latest/usage.html#retrieving-the-analysis
# Based on https://es.tradingview.com/script/YuWaSZ1Z/

from tradingview_ta import TA_Handler, Interval, Exchange
# use for environment variables
import os
# use if needed to pass args to external modules
import sys
# used for directory handling
import glob
# used for dates
from datetime import date, datetime, timedelta

import time
import threading
import array
import statistics
import numpy as np
from math import exp, cos

from analysis_buffer import AnalysisBuffer

# my helper utils
from helpers.os_utils import(rchop)

from helpers.parameters import parse_args, load_config

args = parse_args()
DEFAULT_CONFIG_FILE = 'config.yml'

config_file = args.config if args.config else DEFAULT_CONFIG_FILE
parsed_config = load_config(config_file)

USE_MOST_VOLUME_COINS = parsed_config['trading_options']['USE_MOST_VOLUME_COINS']
PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']

INTERVAL = Interval.INTERVAL_1_MINUTE
#Interval.INTERVAL_5_MINUTES
#Interval.INTERVAL_15_MINUTES
#Interval.INTERVAL_30_MINUTES
#Interval.INTERVAL_1_HOUR
#Interval.INTERVAL_2_HOURS
#Interval.INTERVAL_4_HOURS
#Interval.INTERVAL_1_DAY
#Interval.INTERVAL_1_WEEK
#Interval.INTERVAL_1_MONTH


class txcolors:
    BUY = '\033[92m'
    WARNING = '\033[93m'
    SELL_LOSS = '\033[91m'
    SELL_PROFIT = '\033[32m'
    DIM = '\033[2m\033[35m'
    DEFAULT = '\033[39m'    
    
EXCHANGE = 'BINANCE'
SCREENER = 'CRYPTO'

if USE_MOST_VOLUME_COINS == True:
        #if ABOVE_COINS_VOLUME == True:
    TICKERS = "volatile_volume_" + str(date.today()) + ".txt"
else:
    TICKERS = 'tickers.txt' #'signalsample.txt'

TIME_TO_WAIT = 1 # Minutes to wait between analysis
FULL_LOG = False # List analysis result to console
DEBUG = True

SIGNAL_NAME = 'ScalperPro'
SIGNAL_FILE_BUY = 'signals/' + SIGNAL_NAME + '.buy'

def crossover(arr1, arr2): #buysignal
    #print (f'{txcolors.BUY}{SIGNAL_NAME}: crossover {arr1} {arr2})')
    if arr1 != arr2: #...it is found where the numbers are no longer equil
        if arr1 < arr2: #check if it was below before
            CrossOver = True
        else:				
            CrossOver = False
    return CrossOver

def crossunder(arr1, arr2): #sellsignal
    #print (f'{txcolors.BUY}{SIGNAL_NAME}: crossunder {arr1} {arr2})')
    if arr1 != arr2: #...it is found where the numbers are no longer equil
        if arr1 > arr2: #check if it was below before
            CrossUnder = True
        else:				
            CrossUnder = False
    return CrossUnder
    
def analyze(pairs):
    signal_coins = {}
    analysis = {}
    handler = {}
    
    if os.path.exists(SIGNAL_FILE_BUY ):
        os.remove(SIGNAL_FILE_BUY )

    for pair in pairs:
        handler[pair] = TA_Handler(
            symbol=pair,
            exchange=EXCHANGE,
            screener=SCREENER,
            interval=INTERVAL,
            timeout= 10)
       
    for pair in pairs:
        try:
            ssmooth = 0
            ssmooth2 = 0
            ssmooth3 = 0
            macd = 0
            p = 0
            macd1 = 0
            p1 = 0
            ssmooth1 = 0
            ssmooth21 = 0
            ssmooth22 = 0
            ssmooth31 = 0
            ssmooth32 = 0
            
            for i in range(4):
                print (f'{txcolors.BUY}{SIGNAL_NAME}: Analyzing pair {pair} in loop {i+1}')
                analysis = handler[pair].get_analysis()
                p = analysis.indicators["close"]
                
                print (f'{txcolors.BUY}{SIGNAL_NAME}: macd:{macd} macd1:{macd1} p:{p} p1:{p1} ssmooth:{ssmooth} ssmooth1:{ssmooth1} ssmooth2:{ssmooth2} ssmooth21:{ssmooth21} ssmooth3:{ssmooth2} ssmooth31:{ssmooth31}')
                
                length1 = 8
                f = (1.414*3.141592653589793238462643)/length1
                a = exp(-f)
                c2 = 2*a*cos(f)
                c3 = -a*a
                c1 = 1-c2-c3
                ssmooth = c1*(p+p1)*0.5+c2*ssmooth1+c3*ssmooth2

                length2 = 10
                f2 = (1.414*3.141592653589793238462643)/length2
                a2 = exp(-f2)
                c22 = 2*a2*cos(f2)
                c32 = -a2*a2
                c12 = 1-c22-c32
                ssmooth2 = c12*(p+p1)*0.5+c22*ssmooth21+c32*ssmooth22

                macd = (ssmooth - ssmooth2)*10000000

                length3 = 8
                f3 = (1.414*3.141592653589793238462643)/length3
                a3 = exp(-f3)
                c23 = 2*a3*cos(f3)
                c33 = -a3*a3
                c13 = 1-c23-c33
                ssmooth3 = c13*(macd+macd1)*0.5+c23*ssmooth31+c33*ssmooth32

                buySignal =  crossover (macd,ssmooth3)
                sellSignal = crossunder (macd,ssmooth3)
                
                if buySignal == True:
                    signal_coins[pair] = pair
                    print(f'{txcolors.BUY}{SIGNAL_NAME}: {pair} - Buy Signal Detected. [crossover macd:{macd} < ssmooth3:{ssmooth3}]{txcolors.DEFAULT}')
                    with open(SIGNAL_FILE_BUY,'a+') as f:
                        f.write(pair + '\n')
                #else:
                    #print(f'{txcolors.BUY}{SIGNAL_NAME}: {pair} - No Buy Signal Detected{txcolors.DEFAULT}')
                
                if sellSignal == True:
                    #signal_coins[pair] = pair
                    print(f'{txcolors.BUY}{SIGNAL_NAME}: {pair} - Sell Signal Detected. [crossunder macd:{macd} > ssmooth3:{ssmooth3}]{txcolors.DEFAULT}')
                    #with open(SIGNAL_FILE_BUY,'a+') as f:
                        #f.write(pair + '\n')
                #else:
                    #print(f'{txcolors.BUY}{SIGNAL_NAME}: {pair} - No Sell Signal Detected{txcolors.DEFAULT}')
                
                p1 = p

                ssmooth1 = ssmooth

                ssmooth21 = ssmooth2
                ssmooth22 = ssmooth21

                ssmooth31 = ssmooth3
                ssmooth32 = ssmooth31
                
                macd1 = macd
                
                time.sleep(5) #arbitrary value
                
        except Exception as e:
            print(SIGNAL_NAME + ":")
            print("Exception:")
            print(e)
            print (f'Coin: {pair}')
            print (f'handler: {handler[pair]}')            
            
    return signal_coins

def do_work():
    signal_coins = {}
    pairs = {}

    pairs=[line.strip() for line in open(TICKERS)]
    for line in open(TICKERS):
        pairs=[line.strip() + PAIR_WITH for line in open(TICKERS)] 
    
    while True:
        try:
            if not threading.main_thread().is_alive(): exit()
            print(f'Signals {SIGNAL_NAME}: Analyzing {len(pairs)} coins')
            signal_coins = analyze(pairs)
            print(f'Signals {SIGNAL_NAME}: {len(signal_coins)} coins with Buy Signals. Waiting {TIME_TO_WAIT} minutes for next analysis.')
            time.sleep((TIME_TO_WAIT*60))
        except Exception as e:
            print(f'{SIGNAL_NAME}: Exception do_work(): {e}')
            pass
        except KeyboardInterrupt as ki:
            pass