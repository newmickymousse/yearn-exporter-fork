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


SECONDS_IN_A_YEAR = 31536000
gnosis_implementation = Contract("0x655A9e6b044d6B62F393f9990ec3eA877e966e18")

def main():
    crv_address = "0xD533a949740bb3306d119CC777fa900bA034cd52"
    voter = "0xF147b8125d2ef93FB6965Db97D6746952a133934"
    yvecrv_related = [
        "0xc5bDdf9843308380375a611c18B50Fb9341f502A", 
        "0x5249dD8DB02EeFB08600C4A70110B0f6B9CDA3cA",
        "0xBf85BbC54E5107B47FE8c7eD8D8D9f4020fe706e",
        "0xc491C6F0D3092c468770C23032D44ad9dff41989",
        "0xdd5a1C148Ca114af2F4EBC639ce21fEd4730a608",
        "0x6D8fDcEC2f052807211f595fCF1ab87b67220726",
        "0xF27696C8BCa7D54D696189085Ae1283f59342fA6",
        "0x10A0847c2D170008dDCa7C3a688124f493630032",
        "0xF03fB12d80D617798DdF60e935426c47A1046567",
        "0x8e54FF42bfCE5Da59abA53b78dad3643Bf4937CA",
        "0x42D4e90Ff4068Abe7BC4EaB838c7dE1D2F5998A3",
        "0x0D6af0A4fcD387182ca106270794D81477F6dFFD",
        "0x05548D8A753e998DBa4727dA54C787ed7205f276",
        "0x92Be6ADB6a12Da0CA607F9d87DB2F9978cD6ec3E",
        "0x0385b3F162a0e001b60Ecb84D3CB06199d78f666",
        "0x381eCBB7A9232EE8F12000781EC19404d4a76C02", # Banteg arb contract
        "0x1fd6ADbA9FEe5c18338F134E31b4a323aFa06AD4", # Zap
        "0x560e8145ca9ea6995Cd0FdAa01D9F255049Bf25a",
    ]
    ychad = "0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52"
    crv = Contract(crv_address)
    deploy_block = 10720648 
    to_block = chain.height
    crv = web3.eth.contract(crv_address, abi=crv.abi)  
    topics = construct_event_topic_set(
        crv.events.Transfer().abi, 
        web3.codec, 
        {'_to': voter, '_from':ychad},
    )
    logs = web3.eth.get_logs(
        { 'address': crv_address, 'topics': topics, 'fromBlock': deploy_block, 'toBlock': to_block }
    )
    
    events = crv.events.Transfer().processReceipt({'logs': logs})
    keep_crv = 0
    keep_crv_list = [0]
    donations = 0
    donations_list = [0]
    backscratcher_locked = 0
    backscratcher_list = [0]
    blocks = [deploy_block]
    count = 0
    max = 100
    for event in events:
        count = count+1
        # if count % max == 0:
        #     print_status(backscratcher_locked,donations,keep_crv)

        src, dst, amount = event.args.values()
        if amount < 1:
            continue
        amount = amount / 1e18
        txn_hash = event.transactionHash.hex()
        txn = web3.eth.getTransaction(txn_hash)
        if src == ychad:
            print(txn_hash)
        else:
            continue
        if is_strategy(src) or is_strategy(txn.to):
            keep_crv = keep_crv + amount
            keep_crv_list.append(keep_crv)
            donations_list.append(donations)
            backscratcher_list.append(backscratcher_locked)
            blocks.append(int(event.blockNumber))
            continue
        if src == ZERO_ADDRESS or txn.to == "0x4F59818105abE05AE793a8cAeDB39FC2BeA7f03C": # ignore minted CRV
            continue
        if src == ychad:
            donations = donations + amount
            donations_list.append(donations)
            keep_crv_list.append(keep_crv)
            backscratcher_list.append(backscratcher_locked)
            blocks.append(int(event.blockNumber))
            continue
        if txn.to in yvecrv_related or src in yvecrv_related or is_gnosis_safe(txn.to):
            backscratcher_locked = backscratcher_locked + amount
            backscratcher_list.append(backscratcher_locked)
            donations_list.append(donations)
            keep_crv_list.append(keep_crv)
            blocks.append(int(event.blockNumber))
            continue
        print(f'Found event at txn hash {txn_hash}')
        print(f'{src} {txn.to} {is_contract(src)}\n')
            
        # percent_total_supply = amount / total_supply_sum
        # print(txn_hash, "{:.2%}".format(percent_total_supply))
        # blocks.append(int(event.blockNumber))
    print_status(backscratcher_locked,donations,keep_crv)
    d = {'blocks': blocks, 'backscratcher':backscratcher_list, 'donations':donations_list, 'keep_crv':keep_crv_list}
    df = pd.DataFrame.from_dict(d)
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