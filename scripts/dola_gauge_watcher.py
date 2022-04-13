import asyncio, json, time, urllib, os
from dotenv import load_dotenv, find_dotenv
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
dola_gauge = "0x8Fa728F393588E8D8dD1ca397E9a710E53fA553a"
spell_gauge = "0xd8b712d29381748dB89c36BCa0138d7c75866ddF"
dola_gauge_creation_block = 13608864
gauge_controller_addr = "0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB"
deploy_block = 10647875
gauge_controller = contract(gauge_controller_addr)
vecrv = contract("0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2")
gauge_controller = web3.eth.contract(str(gauge_controller_addr), abi=gauge_controller.abi)
last_time = 0

load_dotenv(find_dotenv())
telegram_bot_key = os.environ.get('WAVEY_ALERTS_BOT_KEY')
chat_id = "-618227757"
def main():
    
    votes_by_gauge()

def votes_by_user():    
    topics = construct_event_topic_set(
        gauge_controller.events.VoteForGauge().abi, 
        web3.codec, 
        {
            'user': [voter]
        }
    )
    logs = web3.eth.get_logs(
            { 'topics': topics, 'address': gauge_controller_addr, 'fromBlock': deploy_block, 'toBlock': chain.height }
    )

    events = gauge_controller.events.VoteForGauge().processReceipt({'logs': logs})

    event_filter = web3.eth.filter({'topics': topics})
    last_time = 0
    print(f"Voter history: {voter}\n")
    for event in events:
        event_time, user, gauge_address, weight = event.args.values()
        if event.address != gauge_controller and user != voter:
            continue
        if event_time != last_time:
            dt = datetime.utcfromtimestamp(event_time).strftime("%m/%d/%Y, %H:%M:%S")
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
    last_block_checked = chain.height
    first_run = True
    if first_run:
        last_block_checked = dola_gauge_creation_block

    while True == True:
        current_block = chain.height

        # Create log
        run_time = datetime.utcfromtimestamp(int( time.time() )).strftime("%m/%d/%Y, %H:%M:%S")
        print(f'Checking from block {last_block_checked} to {current_block} at {run_time}')
        
        topics = construct_event_topic_set(
            gauge_controller.events.VoteForGauge().abi, 
            web3.codec, 
            {
            }
        )
        
        logs = web3.eth.get_logs(
                {'topics': topics, 'fromBlock': last_block_checked, 'toBlock': current_block }
        )
        last_block_checked = current_block

        events = gauge_controller.events.VoteForGauge().processReceipt({'logs': logs})

        event_filter = web3.eth.filter({'topics': topics})
        last_time = 0
        
        for event in events:
            ts, user, gauge_address, weight = event.args.values()
            if gauge_address != dola_gauge:
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
            remaining_lock = (lock_end - current_time) / SECONDS_IN_A_YEAR
            txn_hash = event.transactionHash.hex()
            etherscan_link = f'https://etherscan.io/tx/{txn_hash}'
            print(
                f'User: {user}\n\
                Weigth: {"{:.1%}".format(weight/10_000)} weight\n\
                veCRV balance: {int(vecrv.balanceOf(user, block_identifier=event.blockNumber)/10**vecrv.decimals())}\n \
                Lock time remaining {"{:.2f}".format(remaining_lock)}'
            )
            msg = (
                f'User: {user}\nWeigth: {"{:.1%}".format(weight/10_000)} weight\nveCRV balance: {int(vecrv.balanceOf(user, block_identifier=event.blockNumber)/10**vecrv.decimals())}\nLock time remaining {"{:.2f}".format(remaining_lock)}\n\n{etherscan_link}'
            )
            print(msg)
            last_time = time
            encoded_message = urllib.parse.quote(msg)
            url = f"https://api.telegram.org/bot{telegram_bot_key}/sendMessage?chat_id={chat_id}&text={encoded_message}&disable_web_page_preview=true"
            urllib.request.urlopen(url)
        
        first_run = False
        time.sleep(60*60*10) # sleep 10 mins
        # time.sleep(10) # sleep 10 secs