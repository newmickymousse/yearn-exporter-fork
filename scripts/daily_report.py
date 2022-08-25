import asyncio, json, time, urllib, os, telebot
from brownie import Contract, chain, ZERO_ADDRESS
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
telegram_bot_key = os.environ.get('WAVEY_ALERTS_BOT_KEY')
environment = os.environ.get('ENVIRONMENT')
chat_id = "-789090497"
if environment == "PROD":
    chat_id = -1001466522938 # YFI_DAILY_REPORTS
alerts_enabled = True
bot = telebot.TeleBot(telegram_bot_key)

def main():
    oracle = Contract('0x83d95e0D5f402511dB06817Aff3f9eA88224B030')
    helper = Contract('0x52CbF68959e082565e7fd4bBb23D9Ccfb8C8C057')
    explorer = "https://etherscan.io/"
    vaults = list(helper.getVaults())
    DAY = 60 * 60 * 24
    threshold = DAY * 20
    current_time = chain.time()

    message = ''
    message = f'Showing vaults without harvest in the last {threshold/60/60/24} days\n\n'
    for v in vaults:
        v = Contract(v)
        price = oracle.getPriceUsdcRecommended(v.token()) / 10**6
        vault_tvl = price * v.totalAssets() / 10**v.decimals()
        if (
            vault_tvl > 1_000_000 
            and v.lastReport() + threshold < current_time
            and v.depositLimit() != 0
        ):
            msg = f"[{v.name()} {v.apiVersion()}]({explorer}address/{v.address})\n"
            message = message + msg
            strats = get_strats(v)
            try:
                for s in strats:
                    lr = v.strategies(s)['lastReport']
                    time_since = current_time - lr
                    msg = f'    ˃[{Contract(s).name()}]({explorer}address/{s}) days since: {int(time_since/DAY)}\n'
                    message = message + msg
            except:
                msg = f'    Could not load strategy data for {v.address}'
                message = message + msg
            message = message + '\n'
    send_alert(message, chat_id)

def get_strats(v):
    strats = []
    for i in range(0,20):
        s = v.withdrawalQueue(i)
        if s == ZERO_ADDRESS:
            break
        strats.append(s)
    return strats

def send_alert(msg, chat_id):
    # encoded_message = urllib.parse.quote(msg)
    # url = f"https://api.telegram.org/bot{telegram_bot_key}/sendMessage?chat_id={chat_id}&text={encoded_message}&disable_web_page_preview=true"
    # print(url)
    if alerts_enabled:
        bot.send_message(chat_id, msg, parse_mode="markdown", disable_web_page_preview = True)
        # urllib.request.urlopen(url)
    print(msg)
    