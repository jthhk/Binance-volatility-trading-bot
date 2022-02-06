from datetime import timedelta
import pandas as pd
import pandas_ta as ta
from binance.client import BinanceAPIException, Client

# comment me out
from account import keys
client = Client(keys.access_key, keys.secret_key)

# Uncomment and fill me in
# access_key = ""
# secret_key = ""
# client = Client(access_key, secret_key)


pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', 1200)


# works
def coins_update():
	global symbol_list
	symbol_list = []
	try:
		coin_list = open('coins_binance_usdt.txt', 'r').readlines()
		for coin in coin_list:
			coin = coin.split()
			for element in coin:
				symbol_list.append(element)
				# print(symbol)
		return symbol_list
	except Exception as e:
		print(e)

# works - relies on coins_update
def coin_hist_1h():
	global hist_df, symbol_list, symbol
	coins_update()
	coin_hist_list = []
	count = 0
	# temp short list for testing
	#symbol_list = ['BTCUSDT', 'ETHUSDT']

	for symbol in symbol_list:
		symbol = symbol

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
			hist_df['MA50'] = hist_df.ta.sma(50)
			hist_df['MA50_check'] = hist_df['MA50'][-1] - hist_df['MA50'][-2]
			if len(hist_df['close']) > 200:
				hist_df['MA200'] = hist_df.ta.sma(200)
				hist_df['MA200_check'] = hist_df['MA200'][-1] - hist_df['MA200'][-2]
			else:
				continue


			hist_df['US%'] = ((hist_df['max'] - hist_df['close'][-1]) / hist_df['close'][-1]) * 100
			hist_df['DS%'] = ((hist_df['close'][-1] - hist_df['min']) / hist_df['min'][-1]) * 100

			if len(hist_df['close']) > 200:
				trend_50 = hist_df['MA50_check'][-1].astype(float)
				trend_200 = hist_df['MA200_check'][-1].astype(float)
				upside = hist_df['US%'][-1].astype(float)
				downside = hist_df['DS%'][-1].astype(float)
			else:
				continue

			if trend_50 > 0 and trend_200 > 0:
				count +=1
				print(f"{count} Uptrend {symbol}         MA50 {trend_50:.3f}         MA200 {trend_200:.3f}         Upside {upside:.3f}%         Downside {downside:.3f}%")
				# print(f"HDF {symbol} {limit} hours \n{hist_df.tail()}\n\n")
		except BinanceAPIException as be:
			print(f"Get Coin Hist Error: {be}")

	return symbol, coin_hist_list, hist_df, symbol_list, interval






if __name__ == '__main__':
	coin_hist_1h()