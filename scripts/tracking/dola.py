import asyncio, json
from configparser import MAX_INTERPOLATION_DEPTH
from collections import defaultdict
from datetime import datetime
from brownie import chain, web3, Contract
from rich import print
from rich.progress import track
from rich.table import Table
from web3._utils.events import construct_event_topic_set
from yearn.prices import magic
from yearn.utils import contract
from brownie.exceptions import ContractNotFound
import warnings
warnings.filterwarnings("ignore", ".*cannot be installed or is not supported by Brownie.*")


SECONDS_IN_A_YEAR = 31536000



def dola_minters():  
    deploy_block = 11915875
    dola_address = "0x865377367054516e17014CcdED1e7d814EDC9ce4"
    dola = contract(dola_address)
    dola = web3.eth.contract(str(dola.address), abi=dola.abi)  
    topics = construct_event_topic_set(
        dola.events.AddMinter().abi, 
        web3.codec, 
        {
        }
    )
    logs = web3.eth.get_logs(
            { 'address': dola.address, 'topics': topics, 'fromBlock': deploy_block, 'toBlock': chain.height }
    )

    events = dola.events.AddMinter().processReceipt({'logs': logs})
    dola = Contract(dola_address)
    for event in events:
        minter = event.args.values()
        if event.address != dola.address:
            continue
        print(minter)
    

    dola = contract(dola_address)
    dola = web3.eth.contract(str(dola.address), abi=dola.abi)  
    topics = construct_event_topic_set(
        dola.events.RemoveMinter().abi, 
        web3.codec, 
        {
        }
    )
    logs = web3.eth.get_logs(
            { 'address': dola.address, 'topics': topics, 'fromBlock': deploy_block, 'toBlock': chain.height }
    )
    events = dola.events.RemoveMinter().processReceipt({'logs': logs})
    
    for event in events:
        minter = event.args.values()
        if event.address != dola_address:
            continue
        print(minter)
