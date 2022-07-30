import asyncio, json
from collections import defaultdict
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
from pytz import ZERO
import sentry_sdk
from datetime import datetime, timezone
from brownie import ZERO_ADDRESS, chain, web3, Contract
from rich import print
from rich.progress import track
from rich.table import Table
from web3._utils.events import construct_event_topic_set
# from yearn.prices import magic
from yearn.utils import contract, closest_block_after_timestamp
from brownie.exceptions import ContractNotFound
import warnings
warnings.filterwarnings("ignore", ".*cannot be installed or is not supported by Brownie.*")

def main():
    pool = Contract("0xAA5A67c256e27A5d80712c51971408db3370927D")
    vault = Contract("0x67B9F46BCbA2DF84ECd41cC6511ca33507c9f4E9")
    block_delimiter = 500
    deploy_block = 14_583_952
    current_block = chain.height
    dominances = []
    blocks = []
    for i in range(0, current_block - deploy_block, block_delimiter):
        block = deploy_block + i
        dominance = vault.totalAssets(block_identifier=block) / pool.totalSupply(block_identifier=block)
        dominances.append(dominance)
        blocks.append(block)


    d = {'blocks': blocks, 'dominance': dominances}
    df = pd.DataFrame.from_dict(d)
    df.plot(kind='line',x='blocks',y='dominance')
    plt.show()
    assert False
    df.plot(kind='line',x='blocks',y='backscratcher', label='Backscratcher')
    df.plot(kind='line',x='blocks',y='donations', label='Donations')
    df.plot(kind='line',x='blocks',y='keep_crv', label='KeepCRV')
    df.plot(kind='line',x=blocks)
    # plt.ylim(0,max_supply/1e18)
    plt.show()

def print_status(backscratcher_locked,donations,keep_crv):
    print(f'Backscratcher Locked: {"{0:,.2f}".format(backscratcher_locked)}')
    print(f'Donated: {"{0:,.2f}".format(donations)}')
    print(f'KeepCRV: {"{0:,.2f}".format(keep_crv)}\n')

def is_contract(address):
    try:
        if web3.eth.getCode(address) != '0x':
            return True
        return False
    except:
        return False

def is_strategy(address):
    try:
        Contract(address).keepCRV()
        return True
    except:
        try:
            Contract(address).performanceFee()
            return True
        except:
            try:
                Contract(address).keeper()
                return True
            except:
                try:
                    Contract(address).work()
                    return True
                except:
                    return False

def is_gnosis_safe(address):
    try:
        x = Contract.from_abi('gnosis', address, gnosis_implementation.abi)
        x.getOwners()
        return True
    except:
        return False