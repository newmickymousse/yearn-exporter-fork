import asyncio, json
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



def anwbtc_borrows():  
    anwbtc_addess = "0x17786f3813E6bA35343211bd8Fe18EC4de14F28b"
    anwbtc = contract(anwbtc_addess)
    attacker = "0xeA0c959BBb7476DDD6cD4204bDee82b790AA1562"
    outstanding_borrows = 0
    deploy_block = 12167889
    anwbtc = web3.eth.contract(str(anwbtc.address), abi=anwbtc.abi)  
    topics = construct_event_topic_set(
        anwbtc.events.Borrow().abi, 
        web3.codec, 
        {
        }
    )
    logs = web3.eth.get_logs(
            { 'address': anwbtc.address, 'topics': topics, 'fromBlock': deploy_block, 'toBlock': chain.height }
    )

    events = anwbtc.events.Borrow().processReceipt({'logs': logs})

    event_filter = web3.eth.filter({'topics': topics})
    last_time = 0
    anwbtc = Contract(anwbtc_addess)
    borrowers = []
    for event in events:
        borrower, borrow_amount, account_borrows, total_borrows = event.args.values()
        if event.address != anwbtc.address:
            continue
        # if ts != last_time:
        #     dt = datetime.utcfromtimestamp(time).strftime("%m/%d/%Y, %H:%M:%S")
        #     print()
        #     print(f"--- {dt} ---")
        # print(event.transactionHash.hex(), borrower, borrow_amount, account_borrows, total_borrows)
        
        amt = anwbtc.borrowBalanceStored(borrower)
        if borrower not in borrowers and amt > 1e6 and borrower != attacker:
            borrowers.append(borrower)
    
    for b in borrowers:
        print(b, anwbtc.borrowBalanceStored(b)/1e8)

    print("total borrows",total_borrows/1e8)

def anyfi_borrows():  
    anyfi_addess = "0xde2af899040536884e062D3a334F2dD36F34b4a4"
    anyfi = contract(anyfi_addess)
    attacker = "0xeA0c959BBb7476DDD6cD4204bDee82b790AA1562"
    outstanding_borrows = 0
    deploy_block = 12167889
    anyfi = web3.eth.contract(str(anyfi_addess), abi=anyfi.abi)  
    topics = construct_event_topic_set(
        anyfi.events.Borrow().abi, 
        web3.codec, 
        {
        }
    )
    logs = web3.eth.get_logs(
            { 'address': anyfi.address, 'topics': topics, 'fromBlock': deploy_block, 'toBlock': chain.height }
    )

    events = anyfi.events.Borrow().processReceipt({'logs': logs})

    event_filter = web3.eth.filter({'topics': topics})
    last_time = 0
    anyfi = Contract(anyfi_addess)
    borrowers = []
    for event in events:
        borrower, borrow_amount, account_borrows, total_borrows = event.args.values()
        if event.address != anyfi.address:
            continue
        # if ts != last_time:
        #     dt = datetime.utcfromtimestamp(time).strftime("%m/%d/%Y, %H:%M:%S")
        #     print()
        #     print(f"--- {dt} ---")
        # print(event.transactionHash.hex(), borrower, borrow_amount, account_borrows, total_borrows)
        
        amt = anyfi.borrowBalanceStored(borrower)
        if borrower not in borrowers and amt > 1e15 and borrower != attacker:
            borrowers.append(borrower)
    
    for b in borrowers:
        print(b, anyfi.borrowBalanceStored(b)/1e18)

    print("\ntotal borrows",total_borrows/1e18)

def aneth_borrows():  
    aneth_addess = "0x697b4acAa24430F254224eB794d2a85ba1Fa1FB8"
    aneth = contract(aneth_addess)
    attacker = "0xeA0c959BBb7476DDD6cD4204bDee82b790AA1562"
    outstanding_borrows = 0
    deploy_block = 12167889
    aneth = web3.eth.contract(str(aneth_addess), abi=aneth.abi)  
    topics = construct_event_topic_set(
        aneth.events.Borrow().abi, 
        web3.codec, 
        {
        }
    )
    logs = web3.eth.get_logs(
            { 'address': aneth.address, 'topics': topics, 'fromBlock': deploy_block, 'toBlock': chain.height }
    )

    events = aneth.events.Borrow().processReceipt({'logs': logs})

    event_filter = web3.eth.filter({'topics': topics})
    last_time = 0
    aneth = Contract(aneth_addess)
    borrowers = []
    for event in events:
        borrower, borrow_amount, account_borrows, total_borrows = event.args.values()
        if event.address != aneth.address:
            continue
        # if ts != last_time:
        #     dt = datetime.utcfromtimestamp(time).strftime("%m/%d/%Y, %H:%M:%S")
        #     print()
        #     print(f"--- {dt} ---")
        # print(event.transactionHash.hex(), borrower, borrow_amount, account_borrows, total_borrows)
        
        amt = aneth.borrowBalanceStored(borrower)
        if borrower not in borrowers and amt > 1e15 and borrower != attacker:
            borrowers.append(borrower)
    
    for b in borrowers:
        print(b, aneth.borrowBalanceStored(b)/1e18)

    print("\ntotal borrows",total_borrows/1e18)