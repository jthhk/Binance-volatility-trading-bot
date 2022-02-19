# use for environment variables
import os 

from datetime import timedelta
import pandas as pd
import pandas_ta as ta
from pandas import DataFrame
from statistics import stdev
from math import sqrt
from binance.client import BinanceAPIException, Client


access_key = "vjRP6EWGMjk76CTgtFZGw7VDACSKrQ6yuJUBUFGx8lkFYiJERc1huiOItwHpoM1A"
secret_key = "DZ6YKVL2ulHZB2fjHsKFPorj9qkdiA4FE5Wi0vntae00EUu4qhY3xEdBzlNuFPVk"
client = Client(access_key, secret_key)

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', 1200)

def coins_update(symbol):
	try:
		with open('auto_coins_binance_usdt.txt', 'a+') as f:
			f.write(str(symbol) + '\n')
	except Exception as e:
		print(f"ERROR: {e}")

def coin_hist_1h():
	coin_hist_list = []
	count = 0
	symbol_list = client.get_all_tickers()

	for coin in symbol_list:
		symbol = coin['symbol'] 
		PAIR_WITH = "USDT"
		if PAIR_WITH in symbol:
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
				hist_df['volume'] = hist_df['volume'].sum()
				if len(hist_df['close']) > 35:
					hist_df['MA50'] = hist_df.ta.sma(50)
					hist_df['MA50_check'] = hist_df['MA50'][-1] - hist_df['MA50'][-2]
				
				if len(hist_df['close']) > 200:
					hist_df['MA200'] = hist_df.ta.sma(200)
					hist_df['MA200_check'] = hist_df['MA200'][-1] - hist_df['MA200'][-2]
				
				hist_df['US%'] = ((hist_df['max'] - hist_df['close'][-1]) / hist_df['close'][-1]) * 100
				hist_df['DS%'] = ((hist_df['close'][-1] - hist_df['min']) / hist_df['min'][-1]) * 100

				if len(hist_df['close']) > 200:
					trend_50 = hist_df['MA50_check'][-1].astype(float)
					trend_200 = hist_df['MA200_check'][-1].astype(float)
					upside = hist_df['US%'][-1].astype(float)
					downside = hist_df['DS%'][-1].astype(float)

				df = hist_df
				#df = DataFrame(data=data, columns=['close'], dtype='float64')
				df['delta'] = df['close'].pct_change().fillna(0).round(3)

				volatility = []

				for index in range(df.shape[0]):
					if index < 89: #change to 89
						volatility.append(0)
					else:
						start = index - 89 #change to 89
						stop = index
						volatility.append(stdev(df[start:stop]['delta']) * sqrt(252))

				df['volatility1'] = volatility
				df['volatility2'] = df[:]['delta'].rolling(window=90).std(ddof=1) * sqrt(252) #change to ddof=1
				vol1 = str(df.iloc[-1]['volatility1'])
				vol2 = str(df.iloc[-1]['volatility2'])
				vol = str(df.iloc[-1]['volume'])

				if trend_50 > 0 and trend_200 > 0:
					count +=1
					print(f"{count} Uptrend {symbol}  VOL1 {vol1}  VOL2 {vol2}   MA50 {trend_50:.3f}  VOL: {vol}    MA200 {trend_200:.3f}         Upside {upside:.3f}%         Downside {downside:.3f}%")
					coins_update(symbol)
				elif len(hist_df['close']) < 35:
					print(f"{count} NEW COIN {symbol}")
				else:
					count +=1
					print(f"{count} skippping {symbol}  VOL1 {vol1}  VOL2 {vol2}   MA50 {trend_50:.3f}   VOL: {vol}   MA200 {trend_200:.3f}         Upside {upside:.3f}%         Downside {downside:.3f}%")
			except BinanceAPIException as be:
				print(f"Get Coin Hist Error: {be}")


if __name__ == '__main__':

	if os.path.exists('auto_coins_binance_usdt.txt'): os.remove('auto_coins_binance_usdt.txt')
	coin_hist_1h()
	
