import asyncio, json
from collections import defaultdict
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import sentry_sdk
from datetime import datetime, timezone
from brownie import ZERO_ADDRESS, chain, web3, Contract
from rich import print
from rich.progress import track
from rich.table import Table
from web3._utils.events import construct_event_topic_set
from yearn.prices import magic
from yearn.utils import contract, closest_block_after_timestamp
from brownie.exceptions import ContractNotFound
import warnings
warnings.filterwarnings("ignore", ".*cannot be installed or is not supported by Brownie.*")


SECONDS_IN_A_YEAR = 31536000



def check():
    spell_address = "0x090185f2135308BaD17527004364eBcC2D37e5F6"
    spell = Contract(spell_address)
    total_supply = spell.totalSupply() / 1e18
    timestamp_jan1 = 1640995200
    deploy_block = 12454534
    start_block = closest_block_after_timestamp(timestamp_jan1)
    print("Block on jan 1.",start_block)
    start_supply = spell.totalSupply(block_identifier=start_block) / 1e18
    max_supply = spell.MAX_SUPPLY() / 1e18
    remaining_supply = max_supply - start_supply
    to_block = chain.height
    spell = web3.eth.contract(spell_address, abi=spell.abi)  
    topics = construct_event_topic_set(
        spell.events.Transfer().abi, 
        web3.codec, 
        {'_from': ZERO_ADDRESS},
    )
    logs = web3.eth.get_logs(
        { 'address': spell_address, 'topics': topics, 'fromBlock': deploy_block, 'toBlock': to_block }
    )
    
    events = spell.events.Transfer().processReceipt({'logs': logs})
    count = 0
    remaining_supplies = [remaining_supply]
    total_supplies = [total_supply]
    blocks = [start_block]
    total_supply_sum = 0
    for event in events:
        count += 1
        txn_hash = event.transactionHash.hex()
        print(f'Found event at txn hash {txn_hash}')
        src, dst, amount = event.args.values()
        amount = amount / 1e18
        remaining_supply -= amount
        total_supply_sum += amount
        total_supplies.append(int(total_supply_sum))
        remaining_supplies.append(int(remaining_supply))
        percent_total_supply = amount / total_supply_sum
        print(txn_hash, "{:.2%}".format(percent_total_supply))
        blocks.append(int(event.blockNumber))
    d = {'blocks': blocks, 'remaining_supply':remaining_supplies}
    df = pd.DataFrame.from_dict(d)
    df.plot(kind='line',x='blocks',y='remaining_supply')
    plt.ylim(0,max_supply/1e18)
    plt.show()
    
