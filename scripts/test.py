import asyncio, json, time, urllib, os
from dotenv import load_dotenv, find_dotenv
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from brownie import chain, web3, Contract, ZERO_ADDRESS
from rich import print
from rich.progress import track
from rich.table import Table
from web3._utils.events import construct_event_topic_set
from yearn.db.models import FedActivity, Reports, GaugeVotes, Session, engine, select
from sqlalchemy import desc, asc
# from yearn.prices import magic
from yearn.utils import contract
from brownie.exceptions import ContractNotFound
import warnings
warnings.filterwarnings("ignore", ".*cannot be installed or is not supported by Brownie.*")

def main():
    ts = int(time.time())
    vaults = [
        "0xD4108Bb1185A5c30eA3f4264Fd7783473018Ce17", # dola vault
        "0x67B9F46BCbA2DF84ECd41cC6511ca33507c9f4E9", # crv dola vault
    ]
    data = {}
    data["last_update_str"] = datetime.utcfromtimestamp(ts).strftime("%m/%d/%Y, %H:%M:%S")
    data["last_update"] = ts

    # Curve Data
    data["curve"] = {}
    data["curve"]["pool"] = {}
    data["curve"]["pool"]["coins"] = []
    d = data["curve"]["pool"]["coins"]
    pool = Contract("0xAA5A67c256e27A5d80712c51971408db3370927D")
    tvl = 0
    for c in range(0,5):
        try:
            token_address = pool.coins(c)
        except:
            break
        if token_address == ZERO_ADDRESS:
            break
        token = Contract(token_address)
        decimals = token.decimals()
        coin = {}
        tvl = tvl + pool.balances(c) / 10**decimals
        coin["token_address"] = token_address
        coin["name"] = token.name()
        coin["symbol"] = token.symbol()
        
        coin["decimals"] = decimals
        coin["balance"] = pool.balances(c) / 10**decimals
        array = [0,0]
        amount = 1_000_000
        use_base_pool = False
        if c == 1:
            use_base_pool = True
            virtual_price_3crv = Contract("0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7").get_virtual_price() / 1e18
            amount = amount / virtual_price_3crv
        else:
            use_base_pool = False
        array[c] = amount * 1e18
        virtual_price = pool.get_virtual_price() / 1e18
        if use_base_pool:
            amount = 1_000_000
        # IN
        amount_out = pool.calc_token_amount(array, True) / 1e18 * virtual_price
        diff = amount_out - amount
        slippage = diff / amount
        coin["slippage_deposit_1M"] = slippage
        # OUT
        need_to_burn = pool.calc_token_amount(array, False) / 1e18 * virtual_price
        diff = amount - need_to_burn
        slippage = diff / amount
        coin["slippage_withdraw_1M"] = slippage
        array = [0,0]
        d.append(coin)
    data["curve"]["pool"]["tvl"] = tvl
    d = json.dumps(data, default=str)
