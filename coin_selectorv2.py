# use for environment variables
import os 

import pandas as pd
import pandas_ta as ta

#global Settings 
import settings

# used for dates
from datetime import datetime,timedelta
import time

from binance.client import BinanceAPIException, Client

#loads config.cfg into settings.XXXXX
settings.init()

# Binance API
client = Client(settings.access_key, settings.secret_key, tld='us')


pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', 1200)

def coins_update_API():

	global symbol_list
	symbol_list = []

	PairLen = -len(settings.PAIR_WITH)
	exchange_info = client.get_exchange_info()
	for s in exchange_info['symbols']:
		if s['symbol'][PairLen:] == settings.PAIR_WITH:
			print(s['symbol'])
			symbol_list.append(s['symbol'])
	return symbol_list


# works - relies on coins_update
def coin_hist_1h():
	global hist_df, symbol_list, symbol

	coins_update_API()
	coin_hist_list = []
	count = 0
	
	for symbol in symbol_list:
		interval = '1h'
		limit = 210

		# print(f"Downloading Historical data for {symbol}")
		try:

			coin = client.get_klines(symbol=symbol, interval=interval, limit=limit)
			coin_hist_list.append(coin)
			hist_df = pd.DataFrame(coin, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'close time', 'USDT Volume', 'Trades', 'sell USDT', 'buy USDT', 'ignore'])
			# add columns
			hist_df['date'] = pd.to_datetime((hist_df['time'] / 1000), unit='s')
			hist_df['date'] = hist_df['date'] + timedelta(hours=+8)
			hist_df.set_index('date', inplace=True)
			hist_df['close'] = hist_df['close'].astype(float)
			hist_df['max'] = hist_df['close'].max()
			hist_df['min'] = hist_df['close'].min()
			hist_df['MA5'] = hist_df.ta.sma(5)
			hist_df['MA5_check'] = hist_df['MA5'][-1] - hist_df['MA5'][-2]
			if len(hist_df['close']) > 20:
				hist_df['MA20'] = hist_df.ta.sma(20)
				hist_df['MA20_check'] = hist_df['MA20'][-1] - hist_df['MA20'][-2]
			else:
				continue
			price_change_24h = ((hist_df['close'][0] -hist_df['close'][24])/hist_df['close'][0])*100
			price_change_12h = ((hist_df['close'][0] -hist_df['close'][12])/hist_df['close'][0])*100
			price_change_6h = ((hist_df['close'][0] -hist_df['close'][6])/hist_df['close'][0])*100
			price_change_3h = ((hist_df['close'][0] -hist_df['close'][3])/hist_df['close'][0])*100
			hist_df['US%'] = ((hist_df['max'] - hist_df['close'][-1]) / hist_df['close'][-1]) * 100
			hist_df['DS%'] = ((hist_df['close'][-1] - hist_df['min']) / hist_df['min'][-1]) * 100

			if len(hist_df['close']) > 200:
				trend_5 = hist_df['MA5_check'][-1].astype(float)
				trend_20 = hist_df['MA20_check'][-1].astype(float)
				upside = hist_df['US%'][-1].astype(float)
				downside = hist_df['DS%'][-1].astype(float)
			else:
				continue

			if trend_5 > 0 and trend_20 > 0:
				Status = "Include"
			else:
				Status = "Skipping"
			count +=1
			timestamp = datetime.now().strftime("%y-%m-%d %H:%M:%S")
			if not os.path.exists(settings.COIN_FILE):
				with open(settings.COIN_FILE,'a+') as f:
					f.write('Datetime;count;Status;symbol;trend_5;trend_20;upside;downside;price_change_24h;price_change_12h;price_change_6h;price_change_3h\n')    

			with open(settings.COIN_FILE,'a+') as f:
				f.write(str(timestamp) + ';' + str(count) + ';' + str(Status) + ';' + str(symbol) + ';' + str(trend_5) + ';' + str(trend_20) + ';' + str(upside) + ';' + str(downside) + ';' + str(price_change_24h) +  ';' + str(price_change_12h) + ';' + str(price_change_6h) + ';' + str(price_change_3h) +'\n')
				

		except BinanceAPIException as be:
			print(f"Get Coin Hist Error: {symbol} - {be}")


	return symbol, coin_hist_list, hist_df, symbol_list, interval

if __name__ == '__main__':

	coin_hist_1h()