"""
jthhk/Binance-volatility-trading-bot (forked from Olorin Sledge Fork)
Version: 0.5

Disclaimer

All investment strategies and investments involve risk of loss.
Nothing contained in this program, scripts, code or repositoy should be
construed as investment advice.Any reference to an investment's past or
potential performance is not, and should not be construed as, a recommendation
or as a guarantee of any specific outcome or profit.

By using this program you accept all liabilities,
and that no claims can be made against the developers,
or others connected with the program.

Binance_Detect_Mooningsv2 logic
==============================

Checks for existing bot files backs them up, asks to use them or remove
 ../logs/YYYYMMDD_HH_MM_SS
Uses 2 dataframes coins_bought and coins_sold while bot is runing 

Starts the market data feed (redis database + snapshot 5m + websockets) in sub process 
  MarketData_WebSoc.py
Starts the external signals (also re-wrote to use market data from redis database)
  jimbot-signal_framework 

for each coin in the ticker list 
	Skip if coin does not have marketdata (not -1)
	Calc Take Profit and Stop Loss 
	Trailing stop loss/take profit re-adjustment (lock in profits)
	Check if bot should sell SINGLE coin and sell if coin Profit/loss met 
    Check if bot should sell ALL coins if session Profit/loss met 

Update the Bot portfolio json files (coins_bought / coins_sold )
Display the balance report to screen 
Update the Bot overall stats 
Check Sub processes are runing, is problem Alert (May auto restart the market data) 

CTRL+C
==============================
[1] Exit (default option)
[2] Sell All Coins
[3] Sell A Specific Coin
[4] Resume Bot
[5] Stop Purchases (or start)
[6] OCO All Coins
[7] Stop Market Data Socket (or start)
==============================
"""

# use for environment variables
import os 

# Clear the screen
from os import system, name

# use if needed to pass args to external modules
import sys

# used for math functions
import math

# used to create threads & dynamic loading of modules
import multiprocessing
import importlib

# used for directory handling
import glob

#discord needs import request
import requests

#Display child processes 
import psutil

#timezones
import pytz

#read json files
import json

#dataframes
import pandas as pd

from tabulate import tabulate

# Needed for colorful console output Install with: python3 -m pip install colorama (Mac/Linux) or pip install colorama (PC)
from colorama import init
init()

# needed for the binance API / websockets / Exception handling
from binance.client import Client
from binance.exceptions import BinanceAPIException
from requests.exceptions import ReadTimeout, ConnectionError

# used for dates
from datetime import datetime,timedelta
import time

# used to store trades and sell assets
import json

# copy files to log folder
import shutil

# Used to call OCO Script in utilities
import subprocess

#redis
import redis

#global Settings 
import settings

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

txcolors = txcolors()

# print with timestamps
old_out = sys.stdout
class St_ampe_dOut:
    """Stamped stdout."""
    nl = True
    def write(self, x):
        """Write function overloaded."""
        if x == '\n':
            old_out.write(x)
            self.nl = True
        elif self.nl:
            old_out.write(f'{txcolors.DIM}[{str(datetime.now().replace(microsecond=0))}]{txcolors.DEFAULT} {x}')
            self.nl = False
        else:
            old_out.write(x)

    def flush(self):
        pass

sys.stdout = St_ampe_dOut()

def decimals():
    # set number of decimals for reporting fractions
    if settings.is_fiat():
        return 4
    else:
        return 8

def truncate(number, decimals=0):
    """
    Returns a value truncated to a specific number of decimal places.
    Better than rounding
    """
    if not isinstance(decimals, int):
        raise TypeError("decimal places must be an integer.")
    elif decimals < 0:
        raise ValueError("decimal places has to be 0 or more.")
    elif decimals == 0:
        return math.trunc(number)

    factor = 10.0 ** decimals
    return math.trunc(number * factor) / factor

def print_table(table):
    global old_out

    print('')
    sys.stdout = old_out
    print(table)
    sys.stdout = St_ampe_dOut()

def print_notimestamp(msg):
    global old_out

    sys.stdout = old_out
    print(msg, end = ' ')
    sys.stdout = St_ampe_dOut()

# define our clear function
def clear():
  
    # for windows
    if name == 'nt':
        _ = system('cls')
    # for mac and linux(here, os.name is 'posix')
    else:
        _ = system('clear')


##########################################################
#Thread mgt
#########################################################

def restart_signal_threads():
    try:
        for signalthread in signalthreads:
            if any(signalthread.name in word for word in settings.EXTSIGNAL_MODULES):
                name = signalthread.name
                print(f'Terminating thread {str(name)}')
                signalthread.terminate()

                time.sleep(2)
                start_signal_thread(name)
    except:
        pass

def check_signal_threads():

    try:
        for signalthread in signalthreads:
            if signalthread.is_alive():
                return False
        return True

    except:
        pass

def stop_signal_threads():

    try:
        for signalthread in signalthreads:
            print(f'Terminating thread {str(signalthread.name)}')
            signalthread.terminate()
    except:
        pass

def start_signal_threads():
    signal_threads = []

    try:
        if len(settings.SIGNALLING_MODULES) > 0:
            for module in settings.SIGNALLING_MODULES:
                signal_threads.append(start_signal_thread(module))
        else:
            print(f'No modules to load {settings.SIGNALLING_MODULES}')
    except Exception as e:
        if str(e) == "object of type 'NoneType' has no len()":
            print(f'No external signal modules running')
        else:
            print(f'start_signal_threads(): Loading external signals exception: {e}')

    return signal_threads

def start_signal_thread(module):
    try:
        print(f'Starting {module}')
        mymodule[module] = importlib.import_module(module)
        t = multiprocessing.Process(target=mymodule[module].do_work, args=())
        t.name = module
        t.daemon = True
        t.start()
        
        time.sleep(2)

        return t
    except Exception as e:
        if str(e) == "object of type 'NoneType' has no len()":
            print(f'No external signal modules running')
        else:
            print(f'start_signal_thread(): Loading external signals exception: {e}')

def stop_signal_thread(module):

    try:
        print(f'Terminating thread {str(module)}')
        module.terminate()
    except:
        pass

##########################################################
#Signal mgt
#########################################################
def remove_external_signals(fileext):
    signals = glob.glob(f'signals/*.{fileext}')
    for filename in signals:
        try:
            os.remove(filename)
        except:
            if settings.DEBUG: print(f'{txcolors.WARNING}Could not remove external signalling file {filename}{txcolors.DEFAULT}')

def buy_external_signals():
    external_list = {}
    signals = {}

    # check directory and load pairs from files into external_list
    signals = glob.glob("signals/*.buy")
    for filename in signals:
        for line in open(filename):
            symbol = line.strip()
            external_list[symbol] = symbol
        try:
            os.remove(filename)
        except:
            if settings.DEBUG: print(f'{txcolors.WARNING}Could not remove external signalling file{txcolors.DEFAULT}')

    return external_list

def sell_external_signals():
    external_list = {}
    signals = {}

    # check directory and load pairs from files into external_list
    signals = glob.glob("signals/*.sell")
    for filename in signals:
        for line in open(filename):
            symbol = line.strip()
            external_list[symbol] = symbol
            if settings.DEBUG: print(f'{symbol} added to sell_external_signals() list')
        try:
            os.remove(filename)
        except:
            if settings.DEBUG: print(f'{txcolors.WARNING}Could not remove external SELL signalling file{txcolors.DEFAULT}')

    return external_list

def pause_external_signals():
    signals = {}
    paused = False 

    # check directory and load pairs from files into external_list
    signals = glob.glob("signals/*.pause")
    for filename in signals:
        paused = True 

    return paused

##########################################################
#discord
#########################################################
def msg_discord(msg):
    message = msg + '\n\n'
    if settings.MSG_DISCORD:
        #Webhook of my channel. Click on edit channel --> Webhooks --> Creates webhook
        mUrl = "https://discordapp.com/api/webhooks/"+settings.DISCORD_WEBHOOK
        data = {"content": message}
        response = requests.post(mUrl, json=data)

##########################################################
#Writing to log files
#########################################################
def update_bot_stats():
    
    global bot_started_datetime,historic_profit_incfees_perc,historic_profit_incfees_total
    global trade_wins,trade_losses,trade_miss,market_startprice,unrealised_session_profit_incfees_total,unrealised_session_profit_incfees_perc
    global  session_profit_incfees_perc,session_profit_incfees_total

    bot_stats = {
        'total_capital' : str(settings.TRADE_SLOTS * settings.TRADE_TOTAL),
        'botstart_datetime' : str(bot_started_datetime),
        'historicProfitIncFees_Percent': historic_profit_incfees_perc,
        'historicProfitIncFees_Total': historic_profit_incfees_total,
        'tradeWins': trade_wins,
        'tradeLosses': trade_losses,
        'tradeMiss':trade_miss,
        'market_startprice': market_startprice,
        'unrealised_session_profit_incfees_total' : unrealised_session_profit_incfees_total,
        'unrealised_session_profit_incfees_perc' : unrealised_session_profit_incfees_perc,
        'session_profit_incfees_perc' : session_profit_incfees_perc,
        'session_profit_incfees_total' :session_profit_incfees_total
    }

    #save session info for through session portability
    with open(settings.bot_stats_file_path, 'w') as file:
        json.dump(bot_stats, file, indent=4)

def update_portfolio():
    
    # save the coins in a json file in the same directory
    if len(coins_bought.index) > 0:
        coins_bought.to_json(settings.coins_bought_file_path, orient = 'split', compression = 'infer', index = 'true')    
        #print(coins_bought.to_markdown())     
    else:
        with open(settings.coins_bought_file_path, 'w') as f:
            f.write('')

    if len(coins_sold.index) > 0:
        coins_sold.to_json(settings.coins_sold_file_path, orient = 'split', compression = 'infer', index = 'true')    
    else:
        with open(settings.coins_sold_file_path, 'w') as f:
            f.write('')

def write_log(logline):
    timestamp = datetime.now().strftime("%y-%m-%d %H:%M:%S")

    if not os.path.exists(settings.LOG_FILE):
        with open(settings.LOG_FILE,'a+') as f:
            f.write('Datetime\tType\tCoin\tVolume\tBuy Price\tCurrency\tSell Price\tProfit $\tProfit %\tSell Reason\n')    

    with open(settings.LOG_FILE,'a+') as f:
        f.write(timestamp + ' ' + logline + '\n')

def balance_report(EndOfAlgo=False):

    global bot_started_datetime,historic_profit_incfees_perc,historic_profit_incfees_total,exposure_calcuated
    global trade_wins,trade_losses,trade_miss,market_startprice,unrealised_session_profit_incfees_total,unrealised_session_profit_incfees_perc
    global  session_profit_incfees_perc,session_profit_incfees_total,coins_bought,bot_paused,feedhandler,ExternalPaused

    #Bot Summary 
    #truncating some of the above values to the correct decimal places before printing
    WIN_LOSS_PERCENT = 0
    if (trade_wins > 0) and (trade_losses+trade_miss > 0):
        WIN_LOSS_PERCENT = round((trade_wins / (trade_wins+trade_losses+trade_miss)) * 100, 2)
    if (trade_wins > 0) and (trade_losses+trade_miss == 0):
        WIN_LOSS_PERCENT = 100

    try:
        data = MarketData.hgetall("L1:"+settings.REF_COIN)   
        market_currprice = float(data['price'])  
        market_profit = ((market_currprice - market_startprice)/ market_startprice) * 100
        TrendingDown = float(data['TrendingDown'])
        TrendingUp = float(data['TrendingUp'])

        Ref_TA_5m = MarketData.hgetall('TA:'+settings.REF_COIN+'5T')
        market_macd_5min = float(Ref_TA_5m['macd'])  

        Ref_TA_1m = MarketData.hgetall('TA:'+settings.REF_COIN+'1T')
        market_macd_1min = float(Ref_TA_1m['macd'])  
        
        Ref_TA_30m = MarketData.hgetall('TA:'+settings.REF_COIN+'30T')
        market_macd_30min = float(Ref_TA_30m['macd'])  

    except Exception as e:
        #Bot not ready, loading data
        market_macd_1min = -999
        market_macd_5min = -999
        market_macd_30min = -999
        market_currprice = -999
        market_profit = -999
        TrendingDown = -999

    kline = -999
    BookTicker = -999
    aggTrade = -999
    api = -999
    APIWeight = -999

    Eventdata = MarketData.hgetall("UPDATE:kline")   
    if len(Eventdata) >0: kline = datetime.fromtimestamp(int(Eventdata['updated'])/1000, tz=pytz.utc)

    Eventdata = MarketData.hgetall("UPDATE:aggTrade")   
    if len(Eventdata) >0: aggTrade = datetime.fromtimestamp(int(Eventdata['updated'])/1000, tz=pytz.utc)

    Eventdata = MarketData.hgetall("UPDATE:BookTicker")   
    if len(Eventdata) >0: BookTicker = datetime.fromtimestamp(int(Eventdata['updated'])/1000, tz=pytz.utc)

    Eventdata = MarketData.hgetall("UPDATE:bookTicker")   
    if len(Eventdata) >0: BookTicker = datetime.fromtimestamp(int(Eventdata['updated'])/1000, tz=pytz.utc)

    Eventdata = MarketData.hgetall("UPDATE:API")   
    if len(Eventdata) >0: 
        api = datetime.fromtimestamp(int(Eventdata['updated'])/1000, tz=pytz.utc)
        APIWeight = str(Eventdata['APIWeight'])
 
    mode = "Live (REAL MONEY)"
    discord_mode = "Live"
    if settings.TEST_MODE:
        mode = "Test (no real money used)"
        discord_mode = "Test"

    font = f'{txcolors.ENDC}{txcolors.YELLOW}{txcolors.BOLD}{txcolors.UNDERLINE}'
    clear()
    print(f'--------')
    print(f"STARTED         : {str(bot_started_datetime).split('.')[0]} | Running for: {str(datetime.now() - bot_started_datetime).split('.')[0]}")
    print(f'CURRENT HOLDS   : {len(coins_bought)}/{settings.TRADE_SLOTS} ({float(exposure_calcuated):g}/{float(settings.total_capital_config):g} {settings.PAIR_WITH})')
    if settings.REINVEST_PROFITS:
        print(f'ADJ TRADE TOTAL : {settings.TRADE_TOTAL:.2f} (Current TRADE TOTAL adjusted to reinvest profits)')
    print(f'BUYING MODE     : {font if mode == "Live (REAL MONEY)" else txcolors.DEFAULT}{mode}{txcolors.DEFAULT}{txcolors.ENDC}')
    print(f'BACKTESTER      : {settings.BACKTEST_PLAY}')
    print(f'Buying Paused   : {bot_paused}')
    if bot_paused:
        if ExternalPaused:
            if market_currprice == -999:
                print(f'{txcolors.WARNING}Bot is paused until market data is ready, please wait....')
            else:
                print(f'{txcolors.WARNING}Bot is paused by external signals, stop loss and take profit will continue to work...')                            
        else:
            print(f'{txcolors.WARNING}Bot is paused manually, stop loss and take profit will continue to work...')
    print(f'')
    print(f'SESSION PROFIT (Inc Fees)')
    print(f'Realised        : {txcolors.SELL_PROFIT if session_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{session_profit_incfees_perc:.4f}% Est:${session_profit_incfees_total:.4f} {settings.PAIR_WITH}{txcolors.DEFAULT}')
    print(f'Unrealised      : {txcolors.SELL_PROFIT if unrealised_session_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{unrealised_session_profit_incfees_perc:.4f}% Est:${unrealised_session_profit_incfees_total:.4f} {settings.PAIR_WITH}{txcolors.DEFAULT}')
    print(f'        Total   : {txcolors.SELL_PROFIT if (session_profit_incfees_perc + unrealised_session_profit_incfees_perc) > 0. else txcolors.SELL_LOSS}{session_profit_incfees_perc + unrealised_session_profit_incfees_perc:.4f}% Est:${session_profit_incfees_total+unrealised_session_profit_incfees_total:.4f} {settings.PAIR_WITH}{txcolors.DEFAULT}')
    print(f'')
    print(f'REFERENCE PRICE :')
    print(f"Market Profit   : {txcolors.SELL_PROFIT if market_profit > 0. else txcolors.SELL_LOSS}{market_profit:.4f}% ( {settings.REF_COIN} Since STARTED){txcolors.DEFAULT} {market_currprice} | {market_startprice}")
    print(f"Trending        : 1m={market_macd_1min:.4f} | 5m={market_macd_5min:.4f} | 30m={market_macd_30min:.4f} | TrendDown={TrendingDown}| TrendUp={TrendingUp}")
    print(f'')
    print(f'ALL TIME DATA   :')
    print(f'Bot Profit      : {txcolors.SELL_PROFIT if historic_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{historic_profit_incfees_perc:.4f}% Est:${historic_profit_incfees_total:.4f} {settings.PAIR_WITH}{txcolors.DEFAULT}')
    print(f'Completed Trades: {trade_wins+trade_losses+trade_miss} (Wins:{trade_wins} Losses:{trade_losses} Misses:{trade_miss})')
    print(f'Win Ratio       : {float(WIN_LOSS_PERCENT):g}%')
    print(f'')
    print(f'Data WebSoc: kline|{kline}|aggTrade|{aggTrade}|BookTicker|{BookTicker}')
    print(f'Data RestAPI: api|{api}|API Weight|{APIWeight}')
    print(f'')
    print(f'External Signals: {settings.SIGNALLING_MODULES} + {settings.MARKET_DATA_MODULE}')
    current_process = psutil.Process()
    children = current_process.children(recursive=True)
    AuctualSubProcess = 0 
    ExpectedSubProcess =len(settings.SIGNALLING_MODULES) +1 
    for child in children:
        AuctualSubProcess += 1

    if (AuctualSubProcess < ExpectedSubProcess) and not EndOfAlgo: 
        print(f'{txcolors.WARNING}Subprocess possibility missing missing..auto restarting....')
        External = check_signal_threads()
        print(f'External Signals Status: {External}')
        if External and feedhandler != -1:
            print(f'Market Data Feedhandler restarting, please do manually via CTRL+C....')
            stop_signal_thread(feedhandler)
            feedhandler = start_signal_thread(settings.MARKET_DATA_MODULE)            
            time.sleep(5)
        else:
            stop_signal_threads()
            start_signal_threads()
    else:
        print(f'Subprocess running as expected - {AuctualSubProcess} of {ExpectedSubProcess}')
    print(f'--------')

    #Bought Coins Table 
    if len(coins_bought.index) > 0:
        print(f'---Holding----')
        print_notimestamp(coins_bought.to_markdown())
        print_notimestamp('\n')
    if EndOfAlgo:
        if len(coins_sold.index) > 0:
            print(f'---Sold----')
            print_notimestamp(coins_sold.to_markdown())
            print_notimestamp('\n')
    else:
        #write out every time
        if not os.path.exists(settings.HISTORY_LOG_FILE):
            with open(settings.HISTORY_LOG_FILE,'a+') as f:
                f.write(f'{datetime.now().strftime("%H:%M")}\t{len(coins_bought)}\t{settings.TRADE_SLOTS}\t{str(bot_paused)}\t{session_profit_incfees_total+unrealised_session_profit_incfees_total:.4f}\t{unrealised_session_profit_incfees_perc:.4f}%\t{market_profit:.4f}%\t{trade_wins}\t{trade_losses}\t{trade_miss}\n')                

    CurrentMinutes = int(datetime.now().strftime('%M'))
    CurrentSecond = int(datetime.now().strftime('%S'))
    if (CurrentMinutes % 5 == 0) & (CurrentSecond < 2): 
        msg_discord('Pause\tPROFIT\tWins\tHeld\n')
        msg_discord(f'{str(bot_paused)}\t{(session_profit_incfees_perc + unrealised_session_profit_incfees_perc):.4f}%\t{trade_wins}v{trade_losses}v{trade_miss}\t{len(coins_bought)}v{settings.TRADE_SLOTS}\n')
        msg_discord('---')

###############################################################
# Bot Session Mgt
###############################################################
def CheckForExistingSession():

    global bot_started_datetime,historic_profit_incfees_perc,historic_profit_incfees_total
    global trade_wins,trade_losses,trade_miss,market_startprice,unrealised_session_profit_incfees_total,unrealised_session_profit_incfees_perc
    global  session_profit_incfees_perc,session_profit_incfees_total

    # Check if files exist and if they do ask what to do 
    if os.path.isfile(settings.bot_stats_file_path) and os.stat(settings.bot_stats_file_path).st_size!= 0:

        #BACKUP TO LOGS
        NewFolder = "logs/" + datetime.now().strftime('%Y%m%d_%H_%M_%SS') + "/"
        print(settings.bot_stats_file_path)
        print(NewFolder + settings.bot_stats_file_path)
        os.umask(0)
        os.makedirs(NewFolder, mode=0o777)
        if os.path.exists(settings.bot_stats_file_path):shutil.copyfile(settings.bot_stats_file_path, NewFolder + settings.bot_stats_file_path)
        if os.path.exists(settings.coins_bought_file_path):shutil.copyfile(settings.coins_bought_file_path, NewFolder + settings.coins_bought_file_path)
        if os.path.exists(settings.LOG_FILE):shutil.copyfile(settings.LOG_FILE, NewFolder  + settings.LOG_FILE)
        if os.path.exists(settings.HISTORY_LOG_FILE):shutil.copyfile(settings.HISTORY_LOG_FILE, NewFolder  + settings.HISTORY_LOG_FILE)      
        if os.path.exists('config.yml'):shutil.copyfile('config.yml', NewFolder  + 'config.yml')     
        if os.path.exists('WebSocket.txt'):shutil.copyfile('WebSocket.txt', NewFolder  + 'WebSocket.txt')
        print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Session backed up to logs ...')

        #Create folder under logs , copy past session files
        print(f'\n{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Use previous session exists, do you want to continue it (y)? Otherwise a new session will be created.')
        x = input('y/n: ')
        if x == "n":
            #remove past session 
        #remove past session 
            #remove past session 
            print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Deleting previous sessions ...')
            if os.path.exists(settings.bot_stats_file_path): os.remove(settings.bot_stats_file_path)
            if os.path.exists(settings.coins_bought_file_path): os.remove(settings.coins_bought_file_path)
            if os.path.exists(settings.coins_sold_file_path): os.remove(settings.coins_sold_file_path)
            if os.path.exists(settings.LOG_FILE): os.remove(settings.LOG_FILE)
            if os.path.exists(settings.HISTORY_LOG_FILE): os.remove(settings.HISTORY_LOG_FILE)
            if os.path.exists('WebSocket.txt'):os.remove('WebSocket.txt')     
            print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Session deleted, continuing ...')
        else:
            print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Continuing with the session started ...')
       
    if os.path.isfile(settings.bot_stats_file_path) and os.stat(settings.bot_stats_file_path).st_size!= 0:
        with open(settings.bot_stats_file_path) as file:
            # load bot stats:
            bot_stats = json.load(file)
            bot_started_datetime = datetime.strptime(bot_stats['botstart_datetime'], '%Y-%m-%d %H:%M:%S.%f')
            total_capital = bot_stats['total_capital']
            historic_profit_incfees_perc =  bot_stats['historicProfitIncFees_Percent']
            historic_profit_incfees_total = bot_stats['historicProfitIncFees_Total']
            trade_wins = bot_stats['tradeWins']
            trade_losses = bot_stats['tradeLosses']
            trade_miss = bot_stats['tradeMiss']
            market_startprice = bot_stats['market_startprice']

            if total_capital != settings.total_capital_config:
                historic_profit_incfees_perc = (historic_profit_incfees_total / settings.total_capital_config) * 100


def sell(symbol,reason):

    global coins_sold,coins_bought,bot_manual_pause,trade_wins,trade_losses,trade_miss,historic_profit_incfees_perc
    global session_profit_incfees_total,session_profit_incfees_perc,historic_profit_incfees_total

    if (symbol == "ALL"):
        bot_manual_pause = True
        Sell_Coins_Details = coins_bought
    else:
        Sell_Coins_Details = coins_bought[coins_bought['symbol'] == symbol]
    
    for index, row in Sell_Coins_Details.iterrows():
        orderID = FillQty = FillPx = TotalFillQty = TotalFillCost = FillFee  = 0
        coin = row['symbol']
        BuyPrice = float(row['avgPrice'])
        data = MarketData.hgetall("L1:"+coin)
        TotalFillQty = float(row['volume'])
        FillPx = float(data['price']) if float(data['price']) > 0 else BuyPrice
        TotalFillCost = TotalFillQty * FillPx
        TxnTime =  datetime.now().strftime("%H:%M:%S.%f")
        EntryTime =  datetime.now().strftime("%H:%M:%S.%f")

        if not settings.TEST_MODE:
            try:
                order_details = client.create_order(
                    symbol = coin,
                    side = 'SELL',
                    type = 'MARKET',
                    quantity = row['volume']
                )
                TotalFillCost = TotalFillQty = 0
                orderID = order_details['orderId']
                TxnTime = datetime.fromtimestamp(order_details['transactTime']/1000, tz=pytz.utc)
                TxnTime = TxnTime.strftime("%H:%M:%S.%f")
                FillFee = float(0.0)
                # loop through each 'fill':
                for fills in order_details['fills']:
                    FillPx = float(fills['price'])
                    FillQty = float(fills['qty'])
                    FillFee = FillFee + float(fills['commission'])

                    # check if the fee was in BNB. If not, log a nice warning:
                    if (fills['commissionAsset'] != 'BNB') and (settings.TRADING_FEE == 0.075):
                        print(f"WARNING: BNB not used for trading fee, please enable it in Binance!")
                    TotalFillCost  += (FillPx * FillQty)
                    TotalFillQty += FillQty


            # error handling here in case position cannot be placed
            except Exception as e:
                print(f"sell_coins() Exception occured on selling the coin! Coin: {coin}\nSell Volume coins_bought: {row['volume']}\nPrice:{row['avgPrice']}\nException: {e}")
                reason = str(e)  + ' - ' + str(reason)

        # calculate average fill price:
        SellPrice = float( TotalFillCost / TotalFillQty)
        sellFee = (SellPrice * (settings.TRADING_FEE/100))
        SellPriceWithFees = SellPrice + sellFee
       
        buyFee = (BuyPrice * (settings.TRADING_FEE/100))
        BuyPriceWithFees = BuyPrice + buyFee

        ProfitAfterFees = (SellPriceWithFees - BuyPriceWithFees) * row['volume']
        ProfitAfterFees_Perc = float(((SellPriceWithFees - BuyPriceWithFees) / BuyPriceWithFees) * 100)

        if (SellPriceWithFees) >= (BuyPriceWithFees):
            trade_wins += 1
        elif (reason[0] == "1"):
            #Should of been profit but missed the price, main reason slow price feed/internet
            trade_miss += 1
        else:
            trade_losses += 1
        
        #Session Profit
        session_profit_incfees_total = session_profit_incfees_total + ProfitAfterFees
        session_profit_incfees_perc = (session_profit_incfees_total/settings.total_capital_config) * 100
        
        #Session Profit + History 
        historic_profit_incfees_total = historic_profit_incfees_total + ProfitAfterFees
        historic_profit_incfees_perc = (historic_profit_incfees_total/settings.total_capital_config) * 100

        # create object with received data from Binance
        transactionInfo = pd.DataFrame({
            'symbol': coin,
            'orderId': orderID,
            'timestamp': TxnTime,
            'entrytimestamp': EntryTime,
            'buyPrice': float(BuyPriceWithFees),
            'avgPrice': float(SellPriceWithFees),
            'volume': float(TotalFillQty),
            'tradeFeeBNB': float(FillFee),
            'tradeFeeUnit': sellFee,
            'profit' : ProfitAfterFees,
            'perc_profit' : ProfitAfterFees_Perc,
            'reason': reason
        },index=[0])

        # Log trade
        write_log(f"\t{str(TxnTime)}\t{str(EntryTime)}\tSell\t{coin}\t{TotalFillQty}\t{str(BuyPrice)}\t{settings.PAIR_WITH}\t{SellPrice}\t{ProfitAfterFees:.{decimals()}f}\t{ProfitAfterFees_Perc:.2f}\t{reason}")
        coins_sold = coins_sold.append(transactionInfo,ignore_index=True)
        coins_bought = coins_bought.drop(index=index)
        msg_discord(f"{str(datetime.now())}|Sell|{coin}|{TotalFillQty}|{str(BuyPrice)}|{settings.PAIR_WITH}|{SellPrice}|{ProfitAfterFees:.{decimals()}f}|{ProfitAfterFees_Perc:.2f}|{reason}")

def buy(symbol):
    '''Place Buy market orders for each volatile coin found'''
    
    global coins_bought
    coin = MarketData.hgetall("L1:"+symbol)
    if len(coin) > 1 and bool(coin['updated'] and float(coin['price']) > 0):
        #Calc Trading Vol
        lot_size = float(coin['step_size'])
        volume = float(settings.TRADE_TOTAL / float(coin['price']))
        # define the volume with the correct step size
        precision = int(round(-math.log(lot_size, 10), 0))
        volume = float(round(volume, precision))

        #Send order
        print(f"{txcolors.BUY}Preparing to buy {volume} of {symbol} @ ${coin['price']}{txcolors.DEFAULT}")
        msg1 = str(datetime.now()) + ' | BUY: ' + symbol + '. V:' +  str(volume) + ' P$:' + str(coin['price'])
        msg_discord(msg1)
     
        orderID = FillFee = FillQty = FillPx = TotalFillQty = TotalFillCost  = 0
        data = MarketData.hgetall("L1:"+symbol)
        TotalFillQty = volume
        FillPx = float(data['price'])
        TotalFillCost = TotalFillQty * FillPx
        txntime =  datetime.now().strftime("%H:%M:%S.%f")
        EntryTime =  datetime.now().strftime("%H:%M:%S.%f")

        if not settings.TEST_MODE:
            # try to create a real order if the test orders did not raise an exception
            try:
                order_details = client.create_order(
                    symbol = symbol,
                    side = 'BUY',
                    type = 'MARKET',
                    quantity = volume
                )
                TotalFillQty = TotalFillCost = 0
                orderID = order_details['orderId']
                txntime = datetime.fromtimestamp(order_details['transactTime']/1000, tz=pytz.utc)
                txntime = txntime.strftime("%H:%M:%S.%f")
                FillFee = float(0.0)
                # loop through each 'fill':
                for fills in order_details['fills']:
                    FillPx = float(fills['price'])
                    FillQty = float(fills['qty'])
                    FillFee = FillFee + float(fills['commission'])

                    # check if the fee was in BNB. If not, log a nice warning:
                    if (fills['commissionAsset'] != 'BNB') and (settings.TRADING_FEE == 0.075):
                        print(f"WARNING: BNB not used for trading fee, please enable it in Binance!")
                    TotalFillCost  += (FillPx * FillQty)
                    TotalFillQty += FillQty
            
            except Exception as e:
                print(f'buy() exception: {e}')    
                sys.exit()


        # calculate average fill price:
        BuyPrice = float( TotalFillCost / TotalFillQty)
        # calc the tradeFee Approx @ unit level (from Olorin Sledge), display only
        buyFee = (BuyPrice * (settings.TRADING_FEE/100))

        # create object with received data from Binance
        transactionInfo = pd.DataFrame({
            'symbol': symbol,
            'orderId': orderID,
            'timestamp': txntime,
            'entrytimestamp': str(EntryTime),
            'avgPrice': float(BuyPrice),
            'volume': volume,
            'tradeFeeBNB': float(FillFee),
            'tradeFeeUnit': buyFee,
            'take_profit' : settings.TAKE_PROFIT,
            'stop_loss' :settings.STOP_LOSS
        },index=[0])

        # Log trade coin['price']}\t{settings.PAIR_WITH}")
        write_log(f"\t{str(txntime)}\t{str(EntryTime)}\tBuy\t{symbol}\t{volume}\t{coin['price']}\t{settings.PAIR_WITH}")
        coins_bought = coins_bought.append(transactionInfo,ignore_index=True)
        # error handling here in case position cannot be placed

def menu():

    global bot_manual_pause,feedhandler
    END = False
    LOOP = True

    while LOOP:
        print_notimestamp(f'\n[1] Exit (default option)')
        print_notimestamp(f'\n[2] Sell All Coins')
        print_notimestamp(f'\n[3] Sell A Specific Coin')
        print_notimestamp(f'\n[4] Resume Bot')
        if bot_manual_pause: 
            print_notimestamp(f'\n[5] Start Purchases')                
        else:
            print_notimestamp(f'\n[5] Stop Purchases')
        print_notimestamp(f'\n[6] OCO All Coins')
        if settings.WEBSOCKET: 
            if feedhandler.is_alive: 
                print_notimestamp(f'\n[7] Stop Market Data Socket')
            else:
                print_notimestamp(f'\n[7] Start Market Data Socket')   
        print_notimestamp(f'\n[8] Sold Coin Report')            
        print_notimestamp(f'\n{txcolors.WARNING}Please choose one of the above menu options ([1]. Exit):{txcolors.DEFAULT}')
        menuoption = input()

        if menuoption == "1" or menuoption == "":
            print_notimestamp('\n')
            END = True
            LOOP = False
            print(f'')
            print(f'Bot terminated, end of bot report...')
            balance_report(True)            
            sys.exit(0)
        elif menuoption == "2":
            print_notimestamp('\n')
            sell('ALL','Sell All Coins menu option chosen!')
            print_notimestamp('\n')
            print(f'Bot terminated, end of bot report...')
            balance_report(True)
            END = True
            LOOP = False            
        elif menuoption == "3":
            while not menuoption.upper() == "N":
                if len(coins_bought.index) > 0:
                    # ask for coin to sell
                    print_notimestamp(coins_bought.to_markdown())
                    print_notimestamp(f'{txcolors.WARNING}\nType in the Symbol you wish to sell, including pair (i.e. BTCUSDT) or type N to return to Menu (N)?{txcolors.DEFAULT}')
                    menuoption = input()
                    if menuoption == "":
                        break
                    sell(menuoption.upper(),'Sell single Coin menu option chosen!')
                else:
                    break
        elif menuoption == "4":
            print_notimestamp(f'{txcolors.WARNING}\nResuming the bot...\n\n{txcolors.DEFAULT}')
            start_signal_threads()
            LOOP = False
        elif menuoption == "5":
            if bot_manual_pause:
                bot_manual_pause = False
            else:
                bot_manual_pause = True
        elif menuoption == "6":
            print_notimestamp(f'Triggering OCO Script....')
            cmd = ['python', 'sell-oco-remaining-coins.py']
            subprocess.Popen(cmd).wait()
            LOOP = False
            END = True
        elif menuoption == "7":
            if feedhandler.is_alive: 
                stop_signal_thread(feedhandler)
                feedhandler.is_alive = False
            else:
                feedhandler = start_signal_thread(settings.MARKET_DATA_MODULE)
        elif menuoption == "8":
            if len(coins_sold.index) > 0:
                print(f'---Sold----')
                print_notimestamp(coins_sold.to_markdown())
                print_notimestamp('\n')
            

    return END

if __name__ == '__main__':

    req_version = (3,8)
    if sys.version_info[:2] < req_version: 
        print(f'This bot requires Python version 3.9 or higher/newer. You are running version {sys.version_info[:2]} - please upgrade your Python version!!')
        sys.exit()

    global bot_started_datetime,total_capital,historic_profit_incfees_perc,historic_profit_incfees_total,bot_paused
    global trade_wins,trade_losses,trade_miss,market_startprice,unrealised_session_profit_incfees_total,unrealised_session_profit_incfees_perc,coins_cooloff
    global  session_profit_incfees_perc,session_profit_incfees_total,coins_bought,bot_manual_pause,exposure_calcuated,feedhandler,ExternalPaused

    historic_profit_incfees_perc = historic_profit_incfees_total = 0
    trade_wins=trade_losses=trade_miss=market_startprice=unrealised_session_profit_incfees_total=unrealised_session_profit_incfees_perc = 0
    session_profit_incfees_perc=session_profit_incfees_total = exposure_calcuated = 0

    #loads config.cfg into settings.XXXXX
    settings.init()

    #set report time - every 1 minute
    lastime = time.time()

   # Binance - Authenticate with the client, Ensure API key is good before continuing
    if not settings.TEST_MODE:

        print('WARNING: Test mode is disabled in the configuration, you are using _LIVE_ funds.')
        print('WARNING: Waiting 10 seconds before live trading as a security measure!')
        time.sleep(10)

        if settings.AMERICAN_USER:
            client = Client(settings.access_key, settings.secret_key, tld='us')
        else:
            client = Client(settings.access_key, settings.secret_key)

        # If the users has a bad / incorrect API key.
        # this will stop the script from starting, and display a helpful error.
        api_ready, msg = test_api_key(client, BinanceAPIException)
        if api_ready is not True:
            exit(f'{txcolors.SELL_LOSS}{msg}{txcolors.DEFAULT}')

    #Reset or load last session
    CheckForExistingSession()

    #Get Bought File
    if os.path.isfile(settings.coins_bought_file_path) and os.stat(settings.coins_bought_file_path).st_size!= 0:
        coins_bought = pd.read_json(settings.coins_bought_file_path, orient ='split', compression = 'infer')
        coins_bought.head()
    else:
        coins_bought = pd.DataFrame(columns=['symbol', 'orderId', 'timestamp', 'entrytimestamp', 'avgPrice', 'volume', 'tradeFeeBNB','tradeFeeUnit','take_profit','stop_loss', 'Lastpx','Profit'])
    
    #Get Sold File
    if os.path.isfile(settings.coins_sold_file_path) and os.stat(settings.coins_sold_file_path).st_size!= 0:
        coins_sold = pd.read_json(settings.coins_sold_file_path, orient ='split', compression = 'infer')
        coins_sold.head()
    else:
        coins_sold = pd.DataFrame(columns=['symbol', 'orderId', 'timestamp', 'entrytimestamp', 'avgPrice', 'volume', 'tradeFeeBNB','tradeFeeUnit','profit','perc_profit','reason'])

    #cool down, temp not saved to file 
    coins_cooloff = pd.DataFrame(columns=['symbol',  'timestamp'])

    print(f'{txcolors.WARNING}Press Ctrl-C for more options / to stop the bot{txcolors.DEFAULT}')
    
    #Clear alerting
    remove_external_signals('buy')
    remove_external_signals('sell')
    remove_external_signals('pause')

    mymodule = {}

    #Start MarketData Thread
    if settings.WEBSOCKET:
        feedhandler = start_signal_thread(settings.MARKET_DATA_MODULE)
    else:
        feedhandler = -1
        print(f'{txcolors.WARNING}PLEASE Start MarketData WebSocket.{txcolors.DEFAULT}')
        time.sleep(10)

    # load signalling modules
    signalthreads = start_signal_threads()   
    
    #bot settings
    bot_started_datetime = datetime.now()
    MarketData = redis.Redis(host='localhost', port=6379, db=settings.DATABASE,decode_responses=True)
    bot_manual_pause = False
    is_bot_running = True
    market_startprice = 0
    ReviewCounter = 0

    while is_bot_running:
        try:
            CoinsUpdates = False
            ExternalPaused = pause_external_signals()
            if  not (ExternalPaused or bot_manual_pause):
            #only if Bot is NOT paused 		
                #if settings.REINVEST_PROFITS:
                #     settings.Reinvest_profits(total_capital)
                bot_paused = False
                
                externals = buy_external_signals()
                for excoin in externals:
                    CoinAlreadyBought = coins_bought[coins_bought['symbol'].str.contains(excoin)]
                    CoinCoolingDown = coins_cooloff[coins_cooloff['symbol'].str.contains(excoin)]
                    if len(CoinCoolingDown) > 0:
                        #Check Timestamp and over the cool off period, if so then remove so we can buy again  
                        CooloffEndTime = pd.to_datetime(CoinCoolingDown['timestamp']) +timedelta(minutes=settings.COOLOFF_PERIOD)
                        if datetime.now() >=  CooloffEndTime.iloc[0]:
                             coins_cooloff = coins_cooloff.drop(index=coins_cooloff['symbol'].str.contains(excoin).index.values)
                             CoinCoolingDown = CoinCoolingDown.drop(index=CoinCoolingDown['symbol'].str.contains(excoin).index.values)
                        else:
                            print(str(excoin) + " Stock still cooling down")

                    if len(CoinAlreadyBought.index) == 0 and len(CoinCoolingDown.index) == 0 and (len(coins_bought.index) + 1) <= settings.TRADE_SLOTS:
                        buy(excoin)
                        CoinsUpdates = True 

                externals = sell_external_signals()
                for excoin in externals:
                    sell(excoin, 'Sell Signal')
                    CoinsUpdates = True 
            else:
            #Bot is paused 
                remove_external_signals('buy')
                remove_external_signals('sell')
                if bot_manual_pause:
                    msg = str(datetime.now()) + ' | PAUSEBOT.Purchase paused manually, stop loss and take profit will continue to work...'
                else:
                    msg = str(datetime.now()) + ' | PAUSEBOT. Buying paused due to negative market conditions, stop loss and take profit will continue to work.'
                bot_paused = True
                #msg_discord(msg)   

            #Check every cycle/reset values 
            exposure_calcuated = 0  
            unrealised_session_profit_incfees_total = 0 
            unrealised_session_profit_incfees_perc = 0
            botIscheckingCoins = False
            ReviewCounter = ReviewCounter + 1 

            #Check i have a prices, it may take a few seconds at the start 
            refpx = MarketData.hgetall("L1:"+settings.REF_COIN)   
            if market_startprice <= 0:
                if refpx: 
                    market_startprice = float(refpx['price'])  
                    feedhandler = start_signal_thread(settings.MARKET_DATA_MODULE)

            for index, row in coins_bought.iterrows():
                symbol = row['symbol']
                data = MarketData.hgetall("L1:"+symbol)

                #Check i have a price, it may take a few seconds at the start 
                if len(data) > 1 and bool(data['updated']) and float(data['price']) > 0:
                    botIscheckingCoins = True 
                    SellPrice =  float(data['price'])
                    sellFee = (SellPrice * (settings.TRADING_FEE/100))
                    sellFeeTotal = (row['volume'] * SellPrice) * (settings.TRADING_FEE/100)
                    SellPriceWithFees = SellPrice + sellFee


                    BuyPrice = float(row['avgPrice'])
                    buyFee = (BuyPrice * (settings.TRADING_FEE/100))
                    buyFeeTotal = (row['volume'] * BuyPrice) * (settings.TRADING_FEE/100)
                    BuyPriceWithFees = BuyPrice + buyFee

                    ProfitAfterFees = (SellPriceWithFees - BuyPriceWithFees) * row['volume']
                    ProfitAfterFees_Perc = float(((SellPriceWithFees - BuyPriceWithFees) / BuyPriceWithFees) * 100)

                    # define stop loss and take profit
                    TP = float(BuyPriceWithFees) + ((float(BuyPriceWithFees) * (row['take_profit'])/100))
                    SL = float(BuyPriceWithFees) + ((float(BuyPriceWithFees) * (row['stop_loss'])/100))
  
                    #TP and SL Adjustment to lock in profits
                    #SellPriceWithFees (Current px) > TP (bought + take_profit target px)
                    if SellPriceWithFees >= TP and settings.USE_TRAILING_STOP_LOSS: 
                            row['stop_loss'] =  round(row['take_profit'] + settings.TRAILING_STOP_LOSS,2) 
                            row['take_profit'] =   row['take_profit'] + settings.TAKE_PROFIT 
                            coins_bought.loc[index, ['take_profit']] = row['take_profit']
                            coins_bought.loc[index, ['stop_loss']] = row['stop_loss'] 
                            TP = float(BuyPriceWithFees) + ((float(BuyPriceWithFees) * (row['take_profit'])/100))
                   
                    #exposure_calcuated for balance_report screen
                    exposure_calcuated += round((SellPriceWithFees *row['volume']) ,0)

                    #update px for balance_report screen
                    coins_bought.loc[index, ['Lastpx']] = data['price'] 
                    coins_bought.loc[index, ['Profit']] = round(ProfitAfterFees_Perc,3)

                    # check that the price is below the stop loss or above take profit (if trailing stop loss not used) and sell if this is the case
                    if SellPriceWithFees < SL: 
                        if settings.USE_TRAILING_STOP_LOSS:
                            if row['stop_loss'] > settings.STOP_LOSS:
                                sell_reason = "1-Adj-TSL: " + str(SL) + "|" + str(row['stop_loss']) + " reached"
                            else:
                                sell_reason = "0-TSL: " + str(SL) + "|" + str(row['stop_loss']) + " reached"
                        else:
                            sell_reason = "0-SL: " + str(SL) + " reached"

                        sell(symbol,sell_reason)
                        CoinsUpdates = True
                        #Add to the cooloff list so not to buy back at once
                        transactionInfo = pd.DataFrame({
                            'symbol': symbol,
                            'timestamp': datetime.now(),
                        },index=[0])
                        coins_cooloff = coins_cooloff.append(transactionInfo,ignore_index=True)         
                      
                    if SellPriceWithFees > TP:
                        if settings.USE_TRAILING_STOP_LOSS:
                            if row['take_profit'] > settings.TAKE_PROFIT:
                                sell_reason = "1-Adj-TTP: " + str(TP) + "|" + str(row['take_profit']) + " reached"
                            else:
                                sell_reason = "1-TTP: " + str(TP) + "|" + str(row['take_profit']) + " reached"
                        else:
                            sell_reason = "1-TP: " + str(TP) + "|" + str(row['take_profit']) + " reached"
                        sell(symbol,sell_reason)
                        CoinsUpdates = True
                        #Add to the cooloff list so not to buy back at once
                        transactionInfo = pd.DataFrame({
                            'symbol': symbol,
                            'timestamp': datetime.now(),
                        },index=[0])
                        coins_cooloff = coins_cooloff.append(transactionInfo,ignore_index=True)                                                
 
                    #Check Session stats
                    unrealised_session_profit_incfees_total = float(unrealised_session_profit_incfees_total + ProfitAfterFees)
                    unrealised_session_profit_incfees_perc = (unrealised_session_profit_incfees_total / settings.total_capital_config) * 100

                    #Check History + Session stats
                    allsession_profits_perc = session_profit_incfees_perc +  unrealised_session_profit_incfees_perc
                    market_currprice = float(refpx['price'])
                    market_profit = ((market_currprice - market_startprice)/ market_startprice) * 100

                    if settings.SESSION_TPSL_OVERRIDE:

                        #Session TP and SL Adjustment to lock in profits
                        #SellPriceWithFees (Current px) > TP (bought + take_profit target px)
                        if allsession_profits_perc >= float(settings.SESSION_TAKE_PROFIT) and settings.USE_TRAILING_STOP_LOSS: 
                            sl = float(settings.SESSION_TAKE_PROFIT) - settings.TRAILING_STOP_LOSS
                            tp = float(settings.SESSION_TAKE_PROFIT) + settings.TRAILING_TAKE_PROFIT
                            #TODO - Bug need to check out logic of the 
                            #settings.Trailing_StopLoss(sl,tp)

                        if allsession_profits_perc >= float(settings.SESSION_TAKE_PROFIT): 
                            sell_reason = "STP Override:" + str(settings.SESSION_TAKE_PROFIT) + f"% |profit:{allsession_profits_perc}%"
                            is_bot_running = False
                        elif allsession_profits_perc <= float(settings.SESSION_STOP_LOSS):
                            sell_reason = "SSL Override:" + str(settings.SESSION_STOP_LOSS) + f"% |loss:{allsession_profits_perc}%"
                            is_bot_running = False
                        #elif ((session_profit_incfees_perc + unrealised_session_profit_incfees_perc) <= (float(settings.SESSION_STOP_LOSS)/2) and (market_profit < -0.7)):
                        #    sell_reason = "Kill Switch:" + str(float(settings.SESSION_STOP_LOSS)/2) + f"% |loss:{(session_profit_incfees_perc + unrealised_session_profit_incfees_perc)}%|" + str(market_profit)
                        #    is_bot_running = False
                            
 
                        if not is_bot_running:
                            unrealised_session_profit_incfees_total = 0
                            unrealised_session_profit_incfees_perc = 0
                            exposure_calcuated = 0
                            sell('ALL',sell_reason)
                            print(f'{sell_reason}')

                            CoinsUpdates = True
                            break

            #Publish updates to files and screen
            if CoinsUpdates: update_portfolio()
            
            if (time.time() - lastime > settings.RECHECK_INTERVAL) or CoinsUpdates:
                balance_report()
                print("Coin list reviewed in last cycle:" + str(ReviewCounter))
                ReviewCounter = 0
                lastime = time.time()
                update_bot_stats()
            
            time.sleep(0.2)

        except ReadTimeout as rt:
            print(f'We got a timeout error from Binance. Re-loop.')
        except ConnectionError as ce:
            print(f'We got a connection error from Binance. Re-loop.')
        except BinanceAPIException as bapie:
            print(f'We got an API error from Binance. Re-loop. \nException:\n{bapie}')
        except KeyboardInterrupt as ki:
            stop_signal_threads()
            if menu() == True: 
                print(f'')
                print(f'Bot terminated, end of bot report...')
                balance_report(True)
                sys.exit(0)

    if not is_bot_running:
            print(f'')
            print(f'Bot terminated, end of bot report...')
            balance_report(True)