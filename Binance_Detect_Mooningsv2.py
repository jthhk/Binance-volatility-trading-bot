# use for environment variables
import os 

# Clear the screen
from os import system, name

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
from binance.helpers import round_step_size
from requests.exceptions import ReadTimeout, ConnectionError

# used for dates
from datetime import date, datetime, timedelta
import time

# used to repeatedly execute the code
from itertools import count

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

# used to display holding coins in an ascii table
from prettytable import PrettyTable

# my helper utils
from helpers.os_utils import(rchop)

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
        # t = threading.Thread(target=mymodule[module].do_work, args=())
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

##########################################################
#discord
#########################################################
def msg_discord_balance(msg1, msg2):
    global last_msg_discord_balance_date, discord_msg_balance_data
    time_between_insertion = datetime.now() - last_msg_discord_balance_date
    
    # only put the balance message to discord once every 60 seconds and if the balance information has changed since last times
    if time_between_insertion.seconds > 60:
        if msg2 != discord_msg_balance_data:
            msg_discord(msg1 + msg2)
            discord_msg_balance_data = msg2
        else:
            # ping msg to know the bot is still running
            msg_discord(".")
        last_msg_discord_balance_date = datetime.now()

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
    
    global bot_started_datetime,total_capital,historic_profit_incfees_perc,historic_profit_incfees_total
    global trade_wins,trade_losses,market_startprice,unrealised_session_profit_incfees_total,unrealised_session_profit_incfees_perc
    global  session_profit_incfees_perc,session_profit_incfees_total,coins_bought,bot_manual_pause


    bot_stats = {
        'total_capital' : str(settings.TRADE_SLOTS * settings.TRADE_TOTAL),
        'botstart_datetime' : str(bot_started_datetime),
        'historicProfitIncFees_Percent': historic_profit_incfees_perc,
        'historicProfitIncFees_Total': historic_profit_incfees_total,
        'tradeWins': trade_wins,
        'tradeLosses': trade_losses,
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

    if len(coins_sold.index) > 0:
        coins_sold.to_json(settings.coins_sold_file_path, orient = 'split', compression = 'infer', index = 'true')    
        #print(coins_sold.to_markdown())     

def write_log(logline):
    timestamp = datetime.now().strftime("%y-%m-%d %H:%M:%S")

    if not os.path.exists(settings.LOG_FILE):
        with open(settings.LOG_FILE,'a+') as f:
            f.write('Datetime\tType\tCoin\tVolume\tBuy Price\tCurrency\tSell Price\tProfit $\tProfit %\tSell Reason\n')    

    with open(settings.LOG_FILE,'a+') as f:
        f.write(timestamp + ' ' + logline + '\n')

def balance_report(EndOfAlgo=False):

    global bot_started_datetime,total_capital,historic_profit_incfees_perc,historic_profit_incfees_total,exposure_calcuated
    global trade_wins,trade_losses,market_startprice,unrealised_session_profit_incfees_total,unrealised_session_profit_incfees_perc
    global  session_profit_incfees_perc,session_profit_incfees_total,coins_bought,bot_manual_pause,bot_paused

    #Bot Summary 
    # truncating some of the above values to the correct decimal places before printing
    WIN_LOSS_PERCENT = 0
    if (trade_wins > 0) and (trade_losses > 0):
        WIN_LOSS_PERCENT = round((trade_wins / (trade_wins+trade_losses)) * 100, 2)
    if (trade_wins > 0) and (trade_losses == 0):
        WIN_LOSS_PERCENT = 100
    
    market_currprice = 1
    market_startprice = 2
    market_profit = ((market_currprice - market_startprice)/ market_startprice) * 100

    mode = "Live (REAL MONEY)"
    discord_mode = "Live"
    if settings.TEST_MODE:
        mode = "Test (no real money used)"
        discord_mode = "Test"


    font = f'{txcolors.ENDC}{txcolors.YELLOW}{txcolors.BOLD}{txcolors.UNDERLINE}'
    extsigs = ""
    try:
        for module in settings.SIGNALLING_MODULES:
            if extsigs == "":
                extsigs = module
            else:
                extsigs = extsigs + ', ' + module
    except Exception as e:
        pass
    if extsigs == "":
        extsigs = "No external signals running"
    clear()
    print(f'')
    print(f'--------')
    print(f"STARTED         : {str(bot_started_datetime).split('.')[0]} | Running for: {str(datetime.now() - bot_started_datetime).split('.')[0]}")
    print(f'CURRENT HOLDS   : {len(coins_bought)}/{settings.TRADE_SLOTS} ({float(exposure_calcuated):g}/{float(settings.total_capital_config):g} {settings.PAIR_WITH})')
    if settings.REINVEST_PROFITS:
        print(f'ADJ TRADE TOTAL : {TRADE_TOTAL:.2f} (Current TRADE TOTAL adjusted to reinvest profits)')
    print(f'BUYING MODE     : {font if mode == "Live (REAL MONEY)" else txcolors.DEFAULT}{mode}{txcolors.DEFAULT}{txcolors.ENDC}')
    print(f'BACKTESTER      : {settings.BACKTEST_PLAY}')
    print(f'Buying Paused   : {bot_paused}')
    print(f'')
    print(f'SESSION PROFIT (Inc Fees)')
    print(f'Realised        : {txcolors.SELL_PROFIT if session_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{session_profit_incfees_perc:.4f}% Est:${session_profit_incfees_total:.4f} {settings.PAIR_WITH}{txcolors.DEFAULT}')
    print(f'Unrealised      : {txcolors.SELL_PROFIT if unrealised_session_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{unrealised_session_profit_incfees_perc:.4f}% Est:${unrealised_session_profit_incfees_total:.4f} {settings.PAIR_WITH}{txcolors.DEFAULT}')
    print(f'        Total   : {txcolors.SELL_PROFIT if (session_profit_incfees_perc + unrealised_session_profit_incfees_perc) > 0. else txcolors.SELL_LOSS}{session_profit_incfees_perc + unrealised_session_profit_incfees_perc:.4f}% Est:${session_profit_incfees_total+unrealised_session_profit_incfees_total:.4f} {settings.PAIR_WITH}{txcolors.DEFAULT}')
    print(f'')
    print(f'ALL TIME DATA   :')
    print(f"Market Profit   : {txcolors.SELL_PROFIT if market_profit > 0. else txcolors.SELL_LOSS}{market_profit:.4f}% (BTCUSDT Since STARTED){txcolors.DEFAULT}")
    print(f'Bot Profit      : {txcolors.SELL_PROFIT if historic_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{historic_profit_incfees_perc:.4f}% Est:${historic_profit_incfees_total:.4f} {settings.PAIR_WITH}{txcolors.DEFAULT}')
    print(f'Completed Trades: {trade_wins+trade_losses} (Wins:{trade_wins} Losses:{trade_losses})')
    print(f'Win Ratio       : {float(WIN_LOSS_PERCENT):g}%')
    print(f'')
    print(f'External Signals: {extsigs}')
    print(f'--------')
  
    #Bought Coins Table 
    if len(coins_bought.index) > 0:
        print_notimestamp(f'\n')
        print_notimestamp(f'\n---Holding----\n')
        print_notimestamp(coins_bought.to_markdown())
        print_notimestamp(f'\n')

    if EndOfAlgo:
        if len(coins_sold.index) > 0:
            print_notimestamp(f'\n---Sold----\n')
            print_notimestamp(coins_sold.to_markdown())
            print_notimestamp(f'\n')

    else:
        #write out every time
        if not os.path.exists(settings.HISTORY_LOG_FILE):
            with open(settings.HISTORY_LOG_FILE,'a+') as f:
                f.write('Datetime\tCoins Holding\tTrade Slots\tPausebot Active\tSession Profit %\tSession Profit $\tSession Profit Unrealised %\tSession Profit Unrealised $\tSession Profit Total %\tSession Profit Total $\tAll Time Profit %\tAll Time Profit $\tTotal Trades\tWon Trades\tLost Trades\tWin Loss Ratio\n')    

        #with open(settings.HISTORY_LOG_FILE,'a+') as f:
            #f.write(f'{timestamp}\t{len(coins_bought)}\t{TRADE_SLOTS}\t{str(bot_paused)}\t{str(round(sess_profit_perc,2))}\t{str(round(sess_profit,4))}\t{str(round(sess_profit_perc_unreal,2))}\t{str(round(sess_profit_unreal,4))}\t{str(round(sess_profit_perc_total,2))}\t{str(round(sess_profit_total,4))}\t{str(round(alltime_profit_perc,2))}\t{str(round(alltime_profit,4))}\t{str(total_trades)}\t{str(won_trades)}\t{str(lost_trades)}\t{str(winloss_ratio)}\n')



###############################################################
# Bot Session Mgt
###############################################################
def CheckForExistingSession():

    # Check if files exist and if they do ask what to do 
    if os.path.isfile(settings.bot_stats_file_path) and os.stat(settings.bot_stats_file_path).st_size!= 0:

        #BACKUP TO LOGS
        NewFolder = "logs/" + datetime.now().strftime('%Y%m%d_%H_%M_%SS')
        os.makedirs(NewFolder)
        if os.path.exists(settings.bot_stats_file_path):shutil.copy(settings.bot_stats_file_path, NewFolder)
        if os.path.exists(settings.coins_bought_file_path):shutil.copy(settings.coins_bought_file_path, NewFolder)
        if os.path.exists(settings.LOG_FILE):shutil.copy(settings.LOG_FILE, NewFolder)
        if os.path.exists(settings.HISTORY_LOG_FILE):shutil.copy(settings.HISTORY_LOG_FILE, NewFolder)      
        if os.path.exists('config.yml'):shutil.copy('config.yml', NewFolder)     
        print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Session backed up to logs ...')

        print(f'\n{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Use previous session exists, do you want to continue it (y)? Otherwise a new session will be created.')
        x = input('y/n: ')
        #Create folder under logs , copy past session files
        #remove past session 
        if x == "n":
            print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Deleting previous sessions ...')
            if os.path.exists(settings.bot_stats_file_path): os.remove(settings.bot_stats_file_path)
            if os.path.exists(settings.coins_bought_file_path): os.remove(settings.coins_bought_file_path)
            if os.path.exists(settings.coins_sold_file_path): os.remove(settings.coins_sold_file_path)
            if os.path.exists(settings.LOG_FILE): os.remove(settings.LOG_FILE)
            if os.path.exists(settings.HISTORY_LOG_FILE): os.remove(settings.HISTORY_LOG_FILE)
            print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Session deleted, continuing ...')
        else:
            print(f'{txcolors.WARNING}BINANCE DETECT MOONINGS: {txcolors.DEFAULT}Continuing with the session started ...')
       
    if os.path.isfile(settings.bot_stats_file_path) and os.stat(settings.bot_stats_file_path).st_size!= 0:
        with open(settings.bot_stats_file_path) as file:
            bot_stats = json.load(file)
            # load bot stats:
            bot_started_datetime = datetime.strptime(bot_stats['botstart_datetime'], '%Y-%m-%d %H:%M:%S.%f')
            total_capital = bot_stats['total_capital']
            historic_profit_incfees_perc =  bot_stats['session_profit_incfees_perc']
            historic_profit_incfees_total = bot_stats['session_profit_incfees_total']
            trade_wins = bot_stats['tradeWins']
            trade_losses = bot_stats['tradeLosses']
            market_startprice = bot_stats['market_startprice']

            if total_capital != settings.total_capital_config:
                historic_profit_incfees_perc = (historic_profit_incfees_total / settings.total_capital_config) * 100


def sell(symbol,reason):

    global coins_sold,coins_bought,bot_manual_pause,trade_wins,trade_losses,historic_profit_incfees_perc
    global session_profit_incfees_total,session_profit_incfees_perc,historic_profit_incfees_total

    if (symbol == "ALL"):
        bot_manual_pause = True
        Sell_Coins_Details = coins_bought
    else:
        Sell_Coins_Details = coins_bought[coins_bought['symbol'] == symbol]
    
    for index, row in Sell_Coins_Details.iterrows():
        FILLS_TOTAL = FILLS_QTY = FILLS_FEE = BNB_WARNING = 0
        coin = row['symbol']
        if settings.TEST_MODE:
            data = MarketData.hgetall("L1:"+coin)
            FILLS_QTY = float(row['volume'])
            FILL_PRICE = float(data['price'])
            FILLS_TOTAL = FILLS_QTY * FILL_PRICE
            orderID = 0
            TxnTime =  datetime.now().timestamp()
        else:
            try:
                order_details = client.create_order(
                    symbol = coin,
                    side = 'SELL',
                    type = 'MARKET',
                    quantity = row['volume']
                )

            # error handling here in case position cannot be placed
            except Exception as e:
                print(f"sell_coins() Exception occured on selling the coin! Coin: {coin}\nSell Volume coins_bought: {row['volume']}\nPrice:{row['avgPrice']}\nException: {e}")

            orderID = order_details['orderId']
            TxnTime = order_details['transactTime']

            # loop through each 'fill':
            for fills in order_details['fills']:
                FILL_PRICE = float(fills['price'])
                FILL_QTY = float(fills['qty'])
                FILLS_FEE += float(fills['commission'])
                
                # check if the fee was in BNB. If not, log a nice warning:
                if (fills['commissionAsset'] != 'BNB') and (settings.TRADING_FEE == 0.075):
                    print(f"WARNING: BNB not used for trading fee, please enable it in Binance!")
                FILLS_TOTAL += (FILL_PRICE * FILL_QTY)
                FILLS_QTY += FILL_QTY

        # calculate average fill price:
        SellPrice = float(FILLS_TOTAL / FILLS_QTY)
        sellFee = (SellPrice * (settings.TRADING_FEE/100))
        sellFeeTotal = (row['volume'] * SellPrice) * (settings.TRADING_FEE/100)
        SellPriceWithFees = SellPrice + sellFee

        BuyPrice = float(row['avgPrice'])
        buyFee = (BuyPrice * (settings.TRADING_FEE/100))
        buyFeeTotal = (row['volume'] * BuyPrice) * (settings.TRADING_FEE/100)
        BuyPricePlusFees = BuyPrice + buyFee

        ProfitAfterFees = SellPriceWithFees - BuyPricePlusFees
        ProfitAfterFees_Perc = float(((BuyPricePlusFees - SellPriceWithFees) / BuyPricePlusFees) * 100)

        if (SellPriceWithFees) >= (BuyPricePlusFees):
            trade_wins += 1
        else:
            trade_losses += 1
        
        #Session Profit
        session_profit_incfees_total = session_profit_incfees_total + ProfitAfterFees
        session_profit_incfees_perc = session_profit_incfees_perc + ((session_profit_incfees_total/settings.total_capital_config) * 100)
        
        #Session Profit + History 
        historic_profit_incfees_total = historic_profit_incfees_total + ProfitAfterFees
        historic_profit_incfees_perc = historic_profit_incfees_perc + ((historic_profit_incfees_total/settings.total_capital_config) * 100)

        # create object with received data from Binance
        transactionInfo = pd.DataFrame({
            'symbol': coin,
            'orderId': orderID,
            'timestamp': TxnTime,
            'avgPrice': float(SellPrice),
            'volume': float(FILLS_QTY),
            'tradeFeeBNB': float(FILLS_FEE),
            'tradeFeeUnit': sellFee,
            'profit' : ProfitAfterFees,
            'perc_profit' : ProfitAfterFees_Perc,
            'reason': reason
        },index=[0])

        # Log trade
        write_log(f"\tSell\t{coin}\t{FILLS_QTY}\t{str(SellPrice)}\t{settings.PAIR_WITH}\t{SellPrice}\t{ProfitAfterFees:.{decimals()}f}\t{ProfitAfterFees_Perc:.2f}\t{reason}")
        coins_sold = coins_sold.append(transactionInfo,ignore_index=True)
        coins_bought = coins_bought.drop(index=index)
        msg_discord(f"{str(datetime.now())}|Sell|{coin}|{FILLS_QTY}|{str(SellPrice)}|{settings.PAIR_WITH}|{SellPrice}|{ProfitAfterFees:.{decimals()}f}|{ProfitAfterFees_Perc:.2f}|{reason}")

def buy(symbol):
    '''Place Buy market orders for each volatile coin found'''
    
    global coins_bought
    coin = MarketData.hgetall("L1:"+symbol)
    if len(coin) > 1 and bool(coin['updated']):
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

        if settings.TEST_MODE:
            #In Test mode so just writing to a file
            transactionInfo = pd.DataFrame({
                'symbol': symbol,
                'timestamp': datetime.now().timestamp(),
                'orderId': 0,
                'avgPrice': float(coin['price']),
                'volume': volume,
                'take_profit' : settings.TAKE_PROFIT,
                'stop_loss' :settings.STOP_LOSS
            },index=[0])
        else:    
            # try to create a real order if the test orders did not raise an exception
            try:
                order_details = client.create_order(
                    symbol = symbol,
                    side = 'BUY11',
                    type = 'MARKET',
                    quantity = volume
                )

            # error handling here in case position cannot be placed
            except Exception as e:
                print(f'buy() exception: {e}')

            FILLS_TOTAL = FILLS_QTY = FILLS_FEE = BNB_WARNING = 0
            # loop through each 'fill':
            for fills in order_details['fills']:
                FILL_PRICE = float(fills['price'])
                FILL_QTY = float(fills['qty'])
                FILLS_FEE += float(fills['commission'])
                
                # check if the fee was in BNB. If not, log a nice warning:
                if (fills['commissionAsset'] != 'BNB') and (settings.TRADING_FEE == 0.075):
                    print(f"WARNING: BNB not used for trading fee, please enable it in Binance!")
                # quantity of fills * price
                FILLS_TOTAL += (FILL_PRICE * FILL_QTY)
                # add to running total of fills quantity
                FILLS_QTY += FILL_QTY
                # increase fills array index by 1

            # calculate average fill price:
            FILL_AVG = (FILLS_TOTAL / FILLS_QTY)
            tradeFeeApprox = float(FILL_AVG) * (settings.TRADING_FEE/100)

            # create object with received data from Binance
            transactionInfo = pd.DataFrame({
                'symbol': order_details['symbol'],
                'orderId': order_details['orderId'],
                'timestamp': order_details['transactTime'],
                'avgPrice': float(FILL_AVG),
                'volume': float(FILLS_QTY),
                'tradeFeeBNB': float(FILLS_FEE),
                'tradeFeeUnit': tradeFeeApprox,
                'take_profit' : settings.TAKE_PROFIT,
                'stop_loss' :settings.STOP_LOSS
            },index=[0])
        # Log trade
        write_log(f"\tBuy\t{symbol}\t{volume}\t{coin['price']}\t{settings.PAIR_WITH}")
        coins_bought = coins_bought.append(transactionInfo,ignore_index=True)
    


def menu():

    global bot_manual_pause
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
        print_notimestamp(f'\n{txcolors.WARNING}Please choose one of the above menu options ([1]. Exit):{txcolors.DEFAULT}')
        menuoption = input()

        if menuoption == "1" or menuoption == "":
            print_notimestamp('\n')
            sys.exit(0)
            END = True
            LOOP = False
        elif menuoption == "2":
            print_notimestamp('\n')
            sell('ALL','Sell All Coins menu option chosen!')
            print_notimestamp('\n')
            END = True
            LOOP = False            
        elif menuoption == "3":
            while not menuoption.upper() == "N":
                # setup table
                my_table = PrettyTable()
                my_table.field_names = ["Symbol", "Volume", "Bought At", "Now At", "TP %", "SL %", "Change % (ex fees)", "Profit $", "Time Held"]
                my_table.align["Symbol"] = "l"
                my_table.align["Volume"] = "r"
                my_table.align["Bought At"] = "r"
                my_table.align["Now At"] = "r"
                my_table.align["TP %"] = "r"
                my_table.align["SL %"] = "r"
                my_table.align["Change % (ex fees)"] = "r"
                my_table.align["Profit $"] = "r"
                my_table.align["Time Held"] = "l"

                # display coins to sell
                for index, coin in coins_bought.iterrows():
                    symbol = coin['symbol']
                    data = MarketData.hgetall("L1:"+symbol)
                    last_price = float(data['price'])
                    time_held = timedelta(seconds=datetime.now().timestamp()-int(str(1642264983072)[:10]))
                    #timedelta(seconds=datetime.now().timestamp()-int(str(coin['timestamp'][:10])))
                    change_perc = (float(last_price) - float(coin['avgPrice']))/float(coin['avgPrice']) * 100
                    ProfitExFees = float(last_price) - float(coin['avgPrice'])
                    my_table.add_row([f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{symbol}{txcolors.DEFAULT}",
                                    f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{float(coin['volume']):.6f}{txcolors.DEFAULT}",
                                    f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{float(coin['avgPrice']):.6f}{txcolors.DEFAULT}",
                                    f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{float(last_price):.6f}{txcolors.DEFAULT}",
                                    f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{float(coin['take_profit']):.4f}{txcolors.DEFAULT}",
                                    f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{float(coin['stop_loss']):.4f}{txcolors.DEFAULT}",
                                    f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{change_perc:.4f}{txcolors.DEFAULT}",
                                    f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{(float(coin['volume'])*float(coin['avgPrice'])*change_perc)/100:.6f}{txcolors.DEFAULT}",
                                    f"{txcolors.SELL_PROFIT if ProfitExFees >= 0. else txcolors.SELL_LOSS}{str(time_held).split('.')[0]}{txcolors.DEFAULT}"])
                    
                my_table.sortby = 'Change % (ex fees)'
                if len(my_table._rows) > 0:
                    print_notimestamp(my_table)
                else:
                    break

                # ask for coin to sell
                print_notimestamp(f'{txcolors.WARNING}\nType in the Symbol you wish to sell, including pair (i.e. BTCUSDT) or type N to return to Menu (N)?{txcolors.DEFAULT}')
                menuoption = input()
                if menuoption == "":
                    break
                sell(menuoption.upper(),'Sell single Coin menu option chosen!')
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
    return END

if __name__ == '__main__':

    req_version = (3,9)
    if sys.version_info[:2] < req_version: 
        print(f'This bot requires Python version 3.9 or higher/newer. You are running version {sys.version_info[:2]} - please upgrade your Python version!!')
        sys.exit()

    global bot_started_datetime,total_capital,historic_profit_incfees_perc,historic_profit_incfees_total,bot_paused
    global trade_wins,trade_losses,market_startprice,unrealised_session_profit_incfees_total,unrealised_session_profit_incfees_perc
    global  session_profit_incfees_perc,session_profit_incfees_total,coins_bought,bot_manual_pause,exposure_calcuated

    historic_profit_incfees_perc = historic_profit_incfees_total = 0
    trade_wins=trade_losses=market_startprice=unrealised_session_profit_incfees_total=unrealised_session_profit_incfees_perc = 0
    session_profit_incfees_perc=session_profit_incfees_total = exposure_calcuated = 0

    settings.init()
    
   # Binance - Authenticate with the client, Ensure API key is good before continuing
    if not settings.TEST_MODE:
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
        coins_bought = pd.DataFrame(columns=['symbol', 'orderId', 'timestamp', 'avgPrice', 'volume', 'tradeFeeBNB','tradeFeeUnit','take_profit','stop_loss', 'Lastpx','Profit'])
    
    #Get Sold File
    if os.path.isfile(settings.coins_sold_file_path) and os.stat(settings.coins_sold_file_path).st_size!= 0:
        coins_sold = pd.read_json(settings.coins_sold_file_path, orient ='split', compression = 'infer')
        coins_sold.head()
    else:
        coins_sold = pd.DataFrame(columns=['symbol', 'orderId', 'timestamp', 'avgPrice', 'volume', 'tradeFeeBNB','tradeFeeUnit','profit','perc_profit','reason'])

    print(f'{txcolors.WARNING}Press Ctrl-C for more options / to stop the bot{txcolors.DEFAULT}')
    
    #Clear alerting
    remove_external_signals('buy')
    remove_external_signals('sell')
    remove_external_signals('pause')

    # load signalling modules
    mymodule = {}
    signalthreads = start_signal_threads()   
    is_bot_running = True 
    
    if not settings.TEST_MODE:
        print('WARNING: Test mode is disabled in the configuration, you are using _LIVE_ funds.')
        print('WARNING: Waiting 10 seconds before live trading as a security measure!')
        time.sleep(10)
    bot_started_datetime = datetime.now()
    bot_manual_pause = False
    MarketData = redis.Redis(host='localhost', port=6379, db=settings.DATABASE,decode_responses=True)

    while is_bot_running:
        try:
            if  not (os.path.exists("signals/pausebot.pause") or bot_manual_pause):
            #only if Bot is NOT paused 		

                #if settings.REINVEST_PROFITS:
                #    settings.TRADE_TOTAL = total_capital / settings.TRADE_SLOTS

                bot_paused = False
                externals = buy_external_signals()
                for excoin in externals:
                    CoinAlreadyBought = coins_bought[coins_bought['symbol'].str.contains(excoin)]
                    if len(CoinAlreadyBought.index) == 0 and (len(coins_bought.index) + 1) <= settings.TRADE_SLOTS:
                        buy(excoin) 

                externals = sell_external_signals()
                for excoin in externals:
                    sell(excoin, 'Sell Signal') 
            else:
            #Bot is paused 
                remove_external_signals('buy')
                if bot_manual_pause:
                    print(f'{txcolors.WARNING}Purchase paused manually, stop loss and take profit will continue to work...')
                    msg = str(datetime.now()) + ' | PAUSEBOT.Purchase paused manually, stop loss and take profit will continue to work...'
                else:
                    print(f'{txcolors.WARNING}Buying paused due to negative market conditions, stop loss and take profit will continue to work...{txcolors.DEFAULT}')
                    msg = str(datetime.now()) + ' | PAUSEBOT. Buying paused due to negative market conditions, stop loss and take profit will continue to work.'
                bot_paused = True
                msg_discord(msg)

            #Check every cycle/reset values 
            exposure_calcuated = 0  
            unrealised_session_profit_incfees_total = 0 
            unrealised_session_profit_incfees_perc = 0
            for index, row in coins_bought.iterrows():
                symbol = row['symbol']
                data = MarketData.hgetall("L1:"+symbol)
                if len(data) > 1 and bool(data['updated']) and float(data['price']) > 0:
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
                    TP = float(BuyPrice) + ((float(BuyPrice) * (row['take_profit'])/100))
                    SL = float(BuyPrice) + ((float(BuyPrice) * (row['stop_loss'])/100))
  
                    #TP and SL Adjustment to lock in profits
                    if SellPriceWithFees >= TP and settings.USE_TRAILING_STOP_LOSS: 
                            row['stop_loss'] =  row['take_profit'] + settings.TRAILING_STOP_LOSS 
                            row['take_profit'] =   row['take_profit'] + settings.TRAILING_TAKE_PROFIT 
                            coins_bought.loc[index, ['take_profit']] = row['take_profit']
                            coins_bought.loc[index, ['stop_loss']] = row['stop_loss'] 

                    #Check exposure_calcuated 
                    exposure_calcuated += round((SellPriceWithFees *row['volume']) ,0)

                    #update px
                    coins_bought.loc[index, ['Lastpx']] = data['price'] 
                    coins_bought.loc[index, ['Profit']] = ProfitAfterFees_Perc

                    # check that the price is below the stop loss or above take profit (if trailing stop loss not used) and sell if this is the case
                    if SellPriceWithFees < SL: 
                        if settings.USE_TRAILING_STOP_LOSS:
                            if ProfitAfterFees_Perc >= 0:
                                sell_reason = "TTP " + str(SL) + " reached"
                            else:
                                sell_reason = "TSL " + str(SL) + " reached"
                        else:
                            sell_reason = "SL " + str(SL) + " reached"
                        sell(symbol,sell_reason)
                    if SellPriceWithFees > TP:
                        sell_reason = "TP " + str(TP) + " reached"
                        sell(symbol,sell_reason)
 
                    #Check Session stats
                    unrealised_session_profit_incfees_total = float(unrealised_session_profit_incfees_total + ProfitAfterFees)
                    unrealised_session_profit_incfees_perc = (unrealised_session_profit_incfees_total / settings.total_capital_config) * 100

                    #Check History + Session stats
                    allsession_profits_perc = session_profit_incfees_perc +  ((unrealised_session_profit_incfees_total / settings.total_capital_config) * 100)

                    if settings.SESSION_TPSL_OVERRIDE:
                        if allsession_profits_perc >= float(settings.SESSION_TAKE_PROFIT): 
                            sell_reason = "STP Override:" + str(settings.SESSION_TAKE_PROFIT) + f"% |profit:{allsession_profits_perc}%"
                            is_bot_running = False
                        if allsession_profits_perc <= float(settings.SESSION_STOP_LOSS):
                            sell_reason = "SSL Override:" + str(settings.SESSION_STOP_LOSS) + f"% |loss:{allsession_profits_perc}%"
                            is_bot_running = False
 
                        if not is_bot_running:
                            unrealised_session_profit_incfees_total = 0
                            unrealised_session_profit_incfees_perc = 0
                            exposure_calcuated = 0
                            sell('ALL',sell_reason)
                            print(f'{sell_reason}')
                            break

            #Publish updates to files and screen
            update_portfolio()
            balance_report()
            update_bot_stats()
            time.sleep(settings.RECHECK_INTERVAL) 

        except ReadTimeout as rt:
            TIMEOUT_COUNT += 1
            print(f'We got a timeout error from Binance. Re-loop. Connection Timeouts so far: {TIMEOUT_COUNT}')
        except ConnectionError as ce:
            READ_CONNECTERR_COUNT += 1
            print(f'We got a connection error from Binance. Re-loop. Connection Errors so far: {READ_CONNECTERR_COUNT}')
        except BinanceAPIException as bapie:
            BINANCE_API_EXCEPTION += 1
            print(f'We got an API error from Binance. Re-loop. API Errors so far: {BINANCE_API_EXCEPTION}.\nException:\n{bapie}')
        except KeyboardInterrupt as ki:
            stop_signal_threads()
            if menu() == True: sys.exit(0)

    if not is_bot_running:
            print(f'')
            print(f'Bot terminated, end of bot report...')
            balance_report(True)