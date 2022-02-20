# No future support offered, use this script at own risk - test before using real funds
# If you lose money using this MOD (and you will at some point) you've only got yourself to blame!

from tradingview_ta import TA_Handler, Interval

# used for dates
import time

from datetime import datetime

# use for environment variables
import os
# use if needed to pass args to external modules
import sys

# for colourful logging to the console
class txcolors:
    BUY = '\033[92m'
    WARNING = '\033[93m'
    SELL_LOSS = '\033[91m'
    SELL_PROFIT = '\033[32m'
    DIM = '\033[2m\033[35m'
    DEFAULT = '\033[39m'


INTERVAL1MIN = Interval.INTERVAL_1_MINUTE # Main Timeframe for analysis on Oscillators and Moving Averages (1 mins)
EXCHANGE = 'BINANCE'
SCREENER = 'CRYPTO'
TICKERS = 'tickers.txt'
PAIR_WITH = "USDT"
TIME_TO_WAIT = 1 # Minutes to wait between analysis
signal_file_type = '.buy'
SIGNAL_NAME = 'Ak_Scalp'
SIGNAL_FILE_BUY = 'signals/' + SIGNAL_NAME + '.buy'


def analyze(pairs):

    analysis1MIN = {}
    handler1MIN = {}
    CoinsBuyCounter = 0

    if os.path.exists(SIGNAL_FILE_BUY):
        os.remove(SIGNAL_FILE_BUY)
        
    for symbol in pairs:
        handler1MIN[symbol] = TA_Handler(
            symbol=symbol,
            exchange=EXCHANGE,
            screener=SCREENER,
            interval=INTERVAL1MIN,
            timeout= 10)
                          
        try:
            analysis1MIN = handler1MIN[symbol].get_analysis()
        except Exception as e:
            #print(f'{SIGNAL_NAME} Exception:')
            #print(e)
            #print (f'Coin: {symbol}')
            continue

        #SMA10_1MIN = round(analysis1MIN.indicators['SMA10'],4)            
        #SMA20_1MIN = round(analysis1MIN.indicators['SMA20'],4)
        #SMA200_1MIN = round(analysis1MIN.indicators['SMA200'],4)

        RecommOSC = analysis1MIN.oscillators["RECOMMENDATION"]
        RecommMACD = analysis1MIN.moving_averages["RECOMMENDATION"]
        #RecommSummary = analysis1MIN.summary["RECOMMENDATION"]

        BuyCoin = False

        # Buy condition on the 1 minute indicator
        if (RecommMACD == "BUY" or RecommMACD == "STRONG_BUY") and (RecommOSC == "BUY" or RecommOSC == "STRONG_BUY"):
            #print(symbol)
            #print(analysis1MIN.summary)
            #print(analysis1MIN.indicators)
            BuyCoin = True

        #-----------------------------------------------------------------
        #Buy coin check
        if BuyCoin:
            CoinsBuyCounter += 1
            # add to signal
            with open(f'signals/{SIGNAL_NAME}{signal_file_type}', 'a+') as f:
                f.write(str(symbol) + '\n')
                #print(f'{str(datetime.now())}:{SIGNAL_NAME} - BUY - {symbol} \n')
                

#if __name__ == '__main__':	
def do_work():
    
    while True:
        try:
        
            if not os.path.exists(TICKERS):
                time.sleep((TIME_TO_WAIT*60))
                continue

            signal_coins = {}
            pairs = {}

            pairs=[line.strip() for line in open(TICKERS)]
            for line in open(TICKERS):
                pairs=[line.strip() + PAIR_WITH for line in open(TICKERS)] 

            #print(f'{SIGNAL_NAME}: Analyzing {len(pairs)} coins')
            signal_coins = analyze(pairs)
            time.sleep((TIME_TO_WAIT*60))
        
        except Exception as e:
            print(f'{SIGNAL_NAME}: Exception do_work() Scalp: {e}')
            print("Error on line {}".format(sys.exc_info()[-1].tb_lineno))
            continue
        except KeyboardInterrupt as ki:
            continue