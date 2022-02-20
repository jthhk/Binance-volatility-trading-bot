from math import sqrt
from numpy import around
from numpy.random import uniform
from pandas import DataFrame
from statistics import stdev
from binance.client import BinanceAPIException, Client

access_key = "vjRP6EWGMjk76CTgtFZGw7VDACSKrQ6yuJUBUFGx8lkFYiJERc1huiOItwHpoM1A"
secret_key = "DZ6YKVL2ulHZB2fjHsKFPorj9qkdiA4FE5Wi0vntae00EUu4qhY3xEdBzlNuFPVk"
client = Client(access_key, secret_key)

data = around(a=uniform(low=1.0, high=50.0, size=(500, 1)), decimals=3)
df = DataFrame(data=data, columns=['close'], dtype='float64')
df['delta'] = df['close'].pct_change().fillna(0).round(3)

volatility = []

for index in range(df.shape[0]):
    if index < 89: #change to 89
        volatility.append(0)
    else:
        start = index - 89 #change to 89
        stop = index
        volatility.append(stdev(df['delta']) * sqrt(252))

df['volatility1'] = volatility
df['volatility2'] = df.loc[:, 'delta'].rolling(window=90).std(ddof=1) * sqrt(252) #change to ddof=1

print(df)