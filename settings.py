
# Load helper modules
from helpers.parameters import (
    parse_args, load_config
)

# Load creds modules
from helpers.handle_creds import (
    load_correct_creds, test_api_key,
    load_discord_creds
)

def is_fiat():
    # check if we are using a fiat as a base currency
    #list below is in the order that Binance displays them, apologies for not using ASC order
    fiats = ['USDT', 'BUSD', 'AUD', 'BRL', 'EUR', 'GBP', 'RUB', 'TRY', 'TUSD', 'USDC', 'PAX', 'BIDR', 'DAI', 'IDRT', 'UAH', 'NGN', 'VAI', 'BVND']

    if PAIR_WITH in fiats:
        return True
    else:
        return False
        
def Reinvest_profits(total_capital):
    TRADE_TOTAL = total_capital
    total_capital_config = TRADE_SLOTS * TRADE_TOTAL
    

def init():

    global AMERICAN_USER,access_key, secret_key,DATABASE,WEBSOCKET,bot_stats_file_path,coins_bought_file_path,LOG_FILE,HISTORY_LOG_FILE
    global SIGNALLING_MODULES,TEST_MODE,REINVEST_PROFITS,TRADE_TOTAL,TRADE_SLOTS,SESSION_STOP_LOSS,TRADING_FEE,SELL_ON_SIGNAL_ONLY
    global USE_TRAILING_STOP_LOSS,SESSION_TPSL_OVERRIDE, DEBUG, MSG_DISCORD,DISCORD_WEBHOOK,PAIR_WITH,EXTSIGNAL_MODULES,coins_sold_file_path
    global TRAILING_TAKE_PROFIT,TRAILING_STOP_LOSS,total_capital_config,SESSION_TAKE_PROFIT,BACKTEST_PLAY,MOVEMENT,RECHECK_INTERVAL,TICKER_ITEMS
    global TAKE_PROFIT, STOP_LOSS,CHANGE_IN_PRICE,REF_COIN,BACKTEST_FILE,BACKTEST_RECORD,MARKET_DATA_INTERVAL,TICKERS_LIST,MARKET_DATA_MODULE

    DEFAULT_CONFIG_FILE = 'config.yml'
    DEFAULT_CREDS_FILE = 'creds.yml'

    # Load arguments then parse settings
    args = parse_args()
    mymodule = {}

    config_file = args.config if args.config else DEFAULT_CONFIG_FILE
    creds_file = args.creds if args.creds else DEFAULT_CREDS_FILE
    parsed_config = load_config(config_file)
    parsed_creds = load_config(creds_file)

    # Default no debugging
    DEBUG = False

    # Load system vars
    TEST_MODE = parsed_config['script_options']['TEST_MODE']
    LOG_FILE = parsed_config['script_options'].get('LOG_FILE')
    HISTORY_LOG_FILE = "history.txt"
    DEBUG_SETTING = parsed_config['script_options'].get('DEBUG')
    AMERICAN_USER = parsed_config['script_options'].get('AMERICAN_USER')

    #EnableWeb Sockets
    DATABASE = parsed_config['script_options']['DATABASE']
    WEBSOCKET = parsed_config['script_options']['WEBSOCKET']
    TICKER_ITEMS = parsed_config['script_options']['TICKER_ITEMS']

    #Back Testing Setting 
    BACKTEST_PLAY = parsed_config['script_options']['BACKTEST_PLAY']
    BACKTEST_FILE = parsed_config['script_options']['BACKTEST_FILE'] 
    BACKTEST_RECORD = parsed_config['script_options']['BACKTEST_RECORD'] 
    MARKET_DATA_INTERVAL = parsed_config['script_options']['MARKET_DATA_INTERVAL'] 

    # Load trading vars
    PAIR_WITH = parsed_config['trading_options']['PAIR_WITH']
    TRADE_TOTAL = parsed_config['trading_options']['TRADE_TOTAL']
    TRADE_SLOTS = parsed_config['trading_options']['TRADE_SLOTS']
    FIATS = parsed_config['trading_options']['FIATS']
    REF_COIN = parsed_config['trading_options']['REF_COIN']
    

    RECHECK_INTERVAL = parsed_config['trading_options']['RECHECK_INTERVAL']

    STOP_LOSS = parsed_config['trading_options']['STOP_LOSS']
    TAKE_PROFIT = parsed_config['trading_options']['TAKE_PROFIT']

    #COOLOFF_PERIOD = parsed_config['trading_options']['COOLOFF_PERIOD']

    CUSTOM_LIST = parsed_config['trading_options']['CUSTOM_LIST']
    CUSTOM_LIST_AUTORELOAD = parsed_config['trading_options']['CUSTOM_LIST_AUTORELOAD']
    TICKERS_LIST = parsed_config['trading_options']['TICKERS_LIST']

    USE_TRAILING_STOP_LOSS = parsed_config['trading_options']['USE_TRAILING_STOP_LOSS']
    TRAILING_STOP_LOSS = parsed_config['trading_options']['TRAILING_STOP_LOSS']
    TRAILING_TAKE_PROFIT = parsed_config['trading_options']['TRAILING_TAKE_PROFIT']
        
    # Code modified from DJCommie fork
    # Load Session OVERRIDE values - used to STOP the bot when current session meets a certain STP or SSL value
    SESSION_TPSL_OVERRIDE = parsed_config['trading_options']['SESSION_TPSL_OVERRIDE']
    SESSION_TAKE_PROFIT = parsed_config['trading_options']['SESSION_TAKE_PROFIT']
    SESSION_STOP_LOSS = parsed_config['trading_options']['SESSION_STOP_LOSS']


    # Discord integration
    # Used to push alerts, messages etc to a discord channel
    MSG_DISCORD = parsed_config['trading_options']['MSG_DISCORD']

    # Whether the bot should reinvest your profits or not.
    REINVEST_PROFITS = parsed_config['trading_options']['REINVEST_PROFITS']

    # Functionality to "reset / restart" external signal modules
    RESTART_EXTSIGNALS = parsed_config['trading_options']['RESTART_EXTSIGNALS']
    EXTSIGNAL_MODULES = parsed_config['trading_options']['EXTSIGNAL_MODULES']

    # Trashcan settings
    #HODLMODE_ENABLED = parsed_config['trading_options']['HODLMODE_ENABLED']
    #HODLMODE_TIME_THRESHOLD = parsed_config['trading_options']['HODLMODE_TIME_THRESHOLD']

    TRADING_FEE = parsed_config['trading_options']['TRADING_FEE']
    SIGNALLING_MODULES = parsed_config['trading_options']['SIGNALLING_MODULES']
    MARKET_DATA_MODULE = parsed_config['trading_options']['MARKET_DATA_MODULE']

    if DEBUG_SETTING or args.debug:
        DEBUG = True

    # Load creds for correct environment
    access_key, secret_key = load_correct_creds(parsed_creds)

    if MSG_DISCORD:
        DISCORD_WEBHOOK = load_discord_creds(parsed_creds)

    sell_all_coins = False
    sell_specific_coin = False

 

    # Use CUSTOM_LIST symbols if CUSTOM_LIST is set to True
    if CUSTOM_LIST: tickers=[line.strip() for line in open(TICKERS_LIST)]

    # try to load all the coins bought by the bot if the file exists and is not empty
    coins_bought = {}

    if TEST_MODE:
        file_prefix = 'test_'
    else:
        file_prefix = 'live_'

        # path to the saved coins_bought file
    coins_bought_file_path = file_prefix + 'coins_bought.json'

    # The below mod was stolen and altered from GoGo's fork, a nice addition for keeping a historical history of profit across multiple bot sessions.
    # path to the saved bot_stats file
    bot_stats_file_path = file_prefix + 'bot_stats.json'

    coins_sold_file_path  = file_prefix + 'coins_sold.json'

    # use separate files for testing and live trading
    LOG_FILE = file_prefix + LOG_FILE
    HISTORY_LOG_FILE = file_prefix + HISTORY_LOG_FILE

    total_capital_config = TRADE_SLOTS * TRADE_TOTAL
