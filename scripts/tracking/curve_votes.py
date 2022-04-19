import asyncio, json, time
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
voter = "0xF147b8125d2ef93FB6965Db97D6746952a133934" # Yearn
voter = "0x989AEb4d175e16225E39E87d0D97A3360524AD80" # Convex
voter = "0x88017d9449681d2db852B0311670182929151080"
reth = "0x8aD7e0e6EDc61bC48ca0DD07f9021c249044eD30"
tetranode = "0x9c5083dd4838E120Dbeac44C052179692Aa5dAC5"
dola_gauge = "0x8Fa728F393588E8D8dD1ca397E9a710E53fA553a"
spell_gauge = "0xd8b712d29381748dB89c36BCa0138d7c75866ddF"
dola_gauge_creation_block = 14297137
gauge_controller_addr = "0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB"
deploy_block = 10647875
gauge_controller = contract(gauge_controller_addr)
vecrv = contract("0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2")
gauge_controller = web3.eth.contract(str(gauge_controller_addr), abi=gauge_controller.abi)
last_time = 0

def votes_by_user():    
    user_to_track = tetranode
    topics = construct_event_topic_set(
        gauge_controller.events.VoteForGauge().abi, 
        web3.codec, 
        {
            'user': [user_to_track]
        }
    )
    logs = web3.eth.get_logs(
            { 'topics': topics, 'fromBlock': deploy_block, 'toBlock': chain.height }
    )

    events = gauge_controller.events.VoteForGauge().processReceipt({'logs': logs})

    event_filter = web3.eth.filter({'topics': topics})
    last_time = 0
    print(f"Voter history: {user_to_track}\n")
    for event in events:
        time, user, gauge_address, weight = event.args.values()
        if event.address != gauge_controller and user != user_to_track:
            continue
        if time != last_time:
            dt = datetime.utcfromtimestamp(time).strftime("%m/%d/%Y, %H:%M:%S")
            print()
            print(f"--- {dt} ---")
        name = ""
        try:
            name = contract(gauge_address).name()
        except:
            name = "could not find gauge name"
        print(weight, name, gauge_address)
        last_time = time

def votes_by_gauge():
    topics = construct_event_topic_set(
        gauge_controller.events.VoteForGauge().abi, 
        web3.codec, 
        {
        }
    )
    logs = web3.eth.get_logs(
            {'topics': topics, 'fromBlock': dola_gauge_creation_block, 'toBlock': chain.height }
    )

    events = gauge_controller.events.VoteForGauge().processReceipt({'logs': logs})

    event_filter = web3.eth.filter({'topics': topics})
    last_time = 0
    
    for event in events:
        ts, user, gauge_address, weight = event.args.values()
        if gauge_address != reth: #dola_gauge:
            continue
        if ts != last_time:
            dt = datetime.utcfromtimestamp(ts).strftime("%m/%d/%Y, %H:%M:%S")
            print()
            print(f"--- {dt} ---")
        name = ""
        try:
            name = contract(gauge_address).name()
        except:
            name = "could not find gauge name"
        # print(weight, name)
        lock_end = vecrv.locked__end(user)
        current_time = web3.eth.getBlock(event.blockNumber).timestamp
        remaining_lock = (lock_end - int( time.time() )) / SECONDS_IN_A_YEAR
        print(f'Vote from {user} with {int(vecrv.balanceOf(user)/10**vecrv.decimals())} veCRV, {"{:.1%}".format(weight/10_000)} weight, and lock of {"{:.2f}".format(remaining_lock)} years at time of vote')
        last_time = time