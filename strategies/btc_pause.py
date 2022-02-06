"""
BTC Pause
"""

import os
import time as t
import redis
import requests

from datetime import datetime 

SIGNAL_NAME = 'btc_pause'
SIGNAL_TYPE = 'pause'

def analyse_btc():
	
	global MarketData
	paused = False
	now = datetime.now()

	Bitcoin_TA_1m = MarketData.hgetall('TA:BTCUSDT1T')
	if len(Bitcoin_TA_1m) > 0:
		histbtc = float(Bitcoin_TA_1m['macd']) 
	else: 
		print("ERROR - BTC is missing from Ticker list, please add")
		sys.exit(0)

	if histbtc > 0:
		paused = False
		#print(f'{SIGNAL_NAME}: Market looks OK')
	else:
		print(f'{SIGNAL_NAME}: Market not looking good - BitCoin 1m MACD is -ve =' + str(histbtc))
		paused = True

	#if 0 <= now.weekday() <= 4:
	return paused

def do_work():
	
	MarketData = redis.Redis(host='localhost', port=6379, db=DATABASE,decode_responses=True)

	while True:
		paused = analyse_btc()
		if paused:
			with open(f'signals/{SIGNAL_NAME}.{SIGNAL_TYPE}', 'a+') as f:
				f.write('yes')
			print(f"Bot paused by BTC")

		else:
			if os.path.isfile(f'signals/{SIGNAL_NAME}.{SIGNAL_TYPE}'):
				os.remove(f'signals/{SIGNAL_NAME}.{SIGNAL_TYPE}')
				print(f"Bot resumed by btc_pause")
		t.sleep(60)
