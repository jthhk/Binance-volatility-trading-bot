# JTHHK / JimBot fork

THIS FORK HAS BEEN BEEN MODIFIED RUN AT YOUR OWN RISK

* Binance Detect Moonings.py = Orginal fork  <- Live
* Binance_Detect_Moonings.py = Fork version from Ak_Scalp - can't find reference   <- Live
* Binance_Detect_Mooningsv1.py = My first attempt of intro to web sockets  + redis <- Live
* Binance_Detect_Mooningsv2.py = Complete rewrite for web sockets + redis + dataframes for buy and sell coins <- Not tested

i have removed all the files under root into folders - just trying to reduce noise 

## Jim Bot 
```
jthhk/Binance-volatility-trading-bot (forked from Olorin Sledge Fork)
Version: 0.5

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

```
# Binance Volitility Trading Bot

## Description
This Binance trading bot analyses the changes in price across all coins on Binance and place trades on the most volatile ones. 
In addition to that, this Binance trading algorithm will also keep track of all the coins bought and sell them according to your specified Stop Loss and Take Profit.

The bot will listen to changes in price accross all coins on Binance. By default, we're only picking USDT pairs. We're excluding Margin (like BTCDOWNUSDT) and Fiat pairs

> Information below is an example and is all configurable

- The bot checks if the any coin has gone up by more than 3% in the last 5 minutes
- The bot will buy 100 USDT of the most volatile coins on Binance
- The bot will sell at 6% profit or 3% stop loss


You can follow the [Binance volatility bot guide](https://www.cryptomaton.org/2021/05/08/how-to-code-a-binance-trading-bot-that-detects-the-most-volatile-coins-on-binance/) for a step-by-step walkthrough of the bot development.

## READ BEFORE USE
1. If you use the `TEST_MODE: False` in your config, you will be using REAL money.
2. To ensure you do not do this, ALWAYS check the `TEST_MODE` configuration item in the config.yml file..
3. This is a framework for users to modify and adapt to their overall strategy and needs, and in no way a turn-key solution.
4. Depending on the current market, the default config might not do much, so you will have to adapt it to your own strategy.

## Usage
Please checkout our wiki pages:

- [Setup Guide](https://github.com/CyberPunkMetalHead/Binance-volatility-trading-bot/wiki/Setup-Guide)
- [Bot Strategy Guide](https://github.com/CyberPunkMetalHead/Binance-volatility-trading-bot/wiki/Bot-Strategy-Guide)
- [Configuration Guide](https://github.com/CyberPunkMetalHead/Binance-volatility-trading-bot/wiki/Configuration)

## Troubleshooting

1. Read the [FAQ](FAQ.md)
2. Open an issue / check us out on `#troubleshooting` at [Discord](https://discord.gg/buD27Dmvu3) 🚀 
    - Do not spam, do not berate, we are all humans like you, this is an open source project, not a full time job. 

## 💥 Disclaimer

All investment strategies and investments involve risk of loss. 
**Nothing contained in this program, scripts, code or repository should be construed as investment advice.**
Any reference to an investment's past or potential performance is not, 
and should not be construed as, a recommendation or as a guarantee of 
any specific outcome or profit.
By using this program you accept all liabilities, and that no claims can be made against the developers or others connected with the program.
