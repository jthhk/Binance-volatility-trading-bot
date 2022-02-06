
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

# used to display holding coins in an ascii table
from prettytable import PrettyTable

# Load helper modules
from helpers.parameters import (
    parse_args, load_config
)



DEFAULT_CONFIG_FILE = 'config.yml'

# Load arguments then parse settings
args = parse_args()
mymodule = {}

config_file = args.config if args.config else DEFAULT_CONFIG_FILE
parsed_config = load_config(config_file)
SIGNALLING_MODULES = parsed_config['trading_options']['SIGNALLING_MODULES']

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

def start_signal_threads():
    signal_threads = []

    try:
        if len(SIGNALLING_MODULES) > 0:
            for module in SIGNALLING_MODULES:
                #print(f"Starting external signal: {module}")
                # add process to a list. This is so the thread can be terminated at a later time
                signal_threads.append(start_signal_thread(module))
        else:
            print(f'No modules to load {SIGNALLING_MODULES}')
    except Exception as e:
        if str(e) == "object of type 'NoneType' has no len()":
            print(f'No external signal modules running')
        else:
            print(f'start_signal_threads(): Loading external signals exception: {e}')

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
            if DEBUG: print(f'{txcolors.WARNING}Could not remove external signalling file{txcolors.DEFAULT}')

    return external_list

def balance_report(last_price):

    global trade_wins, trade_losses, session_profit_incfees_perc, session_profit_incfees_total,unrealised_session_profit_incfees_perc,unrealised_session_profit_incfees_total 
    unrealised_session_profit_incfees_perc = 0
    unrealised_session_profit_incfees_total = 0

    BUDGET = TRADE_SLOTS * TRADE_TOTAL
    exposure_calcuated = 0

    for coin in list(coins_bought):
        LastPrice = float(last_price[coin]['price'])
        sellFee = (LastPrice * (TRADING_FEE/100))
        
        BuyPrice = float(coins_bought[coin]['bought_at'])
        buyFee = (BuyPrice * (TRADING_FEE/100))

        exposure_calcuated = exposure_calcuated + round(float(coins_bought[coin]['bought_at']) * float(coins_bought[coin]['volume']),0)

        #PriceChangeIncFees_Total = float(((LastPrice+sellFee) - (BuyPrice+buyFee)) * coins_bought[coin]['volume'])
        PriceChangeIncFees_Total = float(((LastPrice-sellFee) - (BuyPrice+buyFee)) * coins_bought[coin]['volume'])

        # unrealised_session_profit_incfees_perc = float(unrealised_session_profit_incfees_perc + PriceChangeIncFees_Perc)
        unrealised_session_profit_incfees_total = float(unrealised_session_profit_incfees_total + PriceChangeIncFees_Total)

    unrealised_session_profit_incfees_perc = (unrealised_session_profit_incfees_total / BUDGET) * 100

    DECIMALS = int(decimals())
    # CURRENT_EXPOSURE = round((TRADE_TOTAL * len(coins_bought)), DECIMALS)
    CURRENT_EXPOSURE = round(exposure_calcuated, 0)
    INVESTMENT_TOTAL = round((TRADE_TOTAL * TRADE_SLOTS), DECIMALS)
    
    # truncating some of the above values to the correct decimal places before printing
    WIN_LOSS_PERCENT = 0
    if (trade_wins > 0) and (trade_losses > 0):
        WIN_LOSS_PERCENT = round((trade_wins / (trade_wins+trade_losses)) * 100, 2)
    if (trade_wins > 0) and (trade_losses == 0):
        WIN_LOSS_PERCENT = 100
    
    market_profit = ((market_currprice - market_startprice)/ market_startprice) * 100

    mode = "Live (REAL MONEY)"
    discord_mode = "Live"
    if TEST_MODE:
        mode = "Test (no real money used)"
        discord_mode = "Test"

    font = f'{txcolors.ENDC}{txcolors.YELLOW}{txcolors.BOLD}{txcolors.UNDERLINE}'
    extsigs = ""
    try:
        for module in SIGNALLING_MODULES:
            if extsigs == "":
                extsigs = module
            else:
                extsigs = extsigs + ', ' + module
    except Exception as e:
        pass
    if extsigs == "":
        extsigs = "No external signals running"

    print(f'')
    print(f'--------')
    print(f"STARTED         : {str(bot_started_datetime).split('.')[0]} | Running for: {str(datetime.now() - bot_started_datetime).split('.')[0]}")
    print(f'CURRENT HOLDS   : {len(coins_bought)}/{TRADE_SLOTS} ({float(CURRENT_EXPOSURE):g}/{float(INVESTMENT_TOTAL):g} {PAIR_WITH})')
    if REINVEST_PROFITS:
        print(f'ADJ TRADE TOTAL : {TRADE_TOTAL:.2f} (Current TRADE TOTAL adjusted to reinvest profits)')
    print(f'BUYING MODE     : {font if mode == "Live (REAL MONEY)" else txcolors.DEFAULT}{mode}{txcolors.DEFAULT}{txcolors.ENDC}')
    print(f'Buying Paused   : {bot_paused}')
    print(f'')
    print(f'SESSION PROFIT (Inc Fees)')
    print(f'Realised        : {txcolors.SELL_PROFIT if session_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{session_profit_incfees_perc:.4f}% Est:${session_profit_incfees_total:.4f} {PAIR_WITH}{txcolors.DEFAULT}')
    print(f'Unrealised      : {txcolors.SELL_PROFIT if unrealised_session_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{unrealised_session_profit_incfees_perc:.4f}% Est:${unrealised_session_profit_incfees_total:.4f} {PAIR_WITH}{txcolors.DEFAULT}')
    print(f'        Total   : {txcolors.SELL_PROFIT if (session_profit_incfees_perc + unrealised_session_profit_incfees_perc) > 0. else txcolors.SELL_LOSS}{session_profit_incfees_perc + unrealised_session_profit_incfees_perc:.4f}% Est:${session_profit_incfees_total+unrealised_session_profit_incfees_total:.4f} {PAIR_WITH}{txcolors.DEFAULT}')
    print(f'')
    print(f'ALL TIME DATA   :')
    print(f"Market Profit   : {txcolors.SELL_PROFIT if market_profit > 0. else txcolors.SELL_LOSS}{market_profit:.4f}% (BTCUSDT Since STARTED){txcolors.DEFAULT}")
    print(f'Bot Profit      : {txcolors.SELL_PROFIT if historic_profit_incfees_perc > 0. else txcolors.SELL_LOSS}{historic_profit_incfees_perc:.4f}% Est:${historic_profit_incfees_total:.4f} {PAIR_WITH}{txcolors.DEFAULT}')
    print(f'Completed Trades: {trade_wins+trade_losses} (Wins:{trade_wins} Losses:{trade_losses})')
    print(f'Win Ratio       : {float(WIN_LOSS_PERCENT):g}%')
    print(f'')
    print(f'External Signals: {extsigs}')
    print(f'--------')
    print(f'')
    #msg1 = str(bot_started_datetime) + " | " + str(datetime.now() - bot_started_datetime)
    msg1 = str(datetime.now()).split('.')[0]
    msg2 = " | " + str(len(coins_bought)) + "/" + str(TRADE_SLOTS) + " | PBOT: " + str(bot_paused) + " | MODE: " + str(discord_mode)
    msg2 = msg2 + ' SPR%: ' + str(round(session_profit_incfees_perc,2)) + ' SPR$: ' + str(round(session_profit_incfees_total,4))
    msg2 = msg2 + ' SPU%: ' + str(round(unrealised_session_profit_incfees_perc,2)) + ' SPU$: ' + str(round(unrealised_session_profit_incfees_total,4))
    msg2 = msg2 + ' SPT%: ' + str(round(session_profit_incfees_perc + unrealised_session_profit_incfees_perc,2)) + ' SPT$: ' + str(round(session_profit_incfees_total+unrealised_session_profit_incfees_total,4))
    msg2 = msg2 + ' ATP%: ' + str(round(historic_profit_incfees_perc,2)) + ' ATP$: ' + str(round(historic_profit_incfees_total,4))
    msg2 = msg2 + ' CTT: ' + str(trade_wins+trade_losses) + ' CTW: ' + str(trade_wins) + ' CTL: ' + str(trade_losses) + ' CTWR%: ' + str(round(WIN_LOSS_PERCENT,2))

    msg_discord_balance(msg1, msg2)
    history_log(session_profit_incfees_perc, session_profit_incfees_total, unrealised_session_profit_incfees_perc, unrealised_session_profit_incfees_total, session_profit_incfees_perc + unrealised_session_profit_incfees_perc, session_profit_incfees_total+unrealised_session_profit_incfees_total, historic_profit_incfees_perc, historic_profit_incfees_total, trade_wins+trade_losses, trade_wins, trade_losses, WIN_LOSS_PERCENT)

    return msg1 + msg2

def history_log(sess_profit_perc, sess_profit, sess_profit_perc_unreal, sess_profit_unreal, sess_profit_perc_total, sess_profit_total, alltime_profit_perc, alltime_profit, total_trades, won_trades, lost_trades, winloss_ratio):
    global last_history_log_date
    time_between_insertion = datetime.now() - last_history_log_date

    # only log balance to log file once every 60 seconds
    if time_between_insertion.seconds > 60:
        last_history_log_date = datetime.now()
        timestamp = datetime.now().strftime("%y-%m-%d %H:%M:%S")

        if not os.path.exists(HISTORY_LOG_FILE):
            with open(HISTORY_LOG_FILE,'a+') as f:
                f.write('Datetime\tCoins Holding\tTrade Slots\tPausebot Active\tSession Profit %\tSession Profit $\tSession Profit Unrealised %\tSession Profit Unrealised $\tSession Profit Total %\tSession Profit Total $\tAll Time Profit %\tAll Time Profit $\tTotal Trades\tWon Trades\tLost Trades\tWin Loss Ratio\n')    

        with open(HISTORY_LOG_FILE,'a+') as f:
            f.write(f'{timestamp}\t{len(coins_bought)}\t{TRADE_SLOTS}\t{str(bot_paused)}\t{str(round(sess_profit_perc,2))}\t{str(round(sess_profit,4))}\t{str(round(sess_profit_perc_unreal,2))}\t{str(round(sess_profit_unreal,4))}\t{str(round(sess_profit_perc_total,2))}\t{str(round(sess_profit_total,4))}\t{str(round(alltime_profit_perc,2))}\t{str(round(alltime_profit,4))}\t{str(total_trades)}\t{str(won_trades)}\t{str(lost_trades)}\t{str(winloss_ratio)}\n')

    
if __name__ == '__main__':
    
    print('Starting signals.....')
    signalthreads = start_signal_threads()

    try:
        while True:

            volatile_coins = {}
            externals = {}

            # Check signals and log 
            externals = buy_external_signals()

            for excoin in externals:
                if excoin not in volatile_coins and excoin not in coins_bought and \
                        (len(coins_bought) + len(volatile_coins)) < TRADE_SLOTS:
                    volatile_coins[excoin] = 1
                    exnumber +=1
                    print(f"External signal received on {excoin}, purchasing ${TRADE_TOTAL} {PAIR_WITH} value of {excoin}!")

            balance_report(last_price)

            time.sleep(1) 
    except KeyboardInterrupt:
        sys.exit(0)
