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
chat_id = "-1001566366160"


CHAIN_DATA = {
    1: {
        "DOLA": "0x865377367054516e17014CcdED1e7d814EDC9ce4",
        "FEDS": {
            "0x4d7928e993125A9Cefe7ffa9aB637653654222E2": "Fed Scream",
            "0x5E075E40D01c82B6Bf0B0ecdb4Eb1D6984357EF7": "Fed Anchor",
            "0xe3277f1102C1ca248aD859407Ca0cBF128DB0664": "Fed Fuse6",
            "0x7765996dAe0Cf3eCb0E74c016fcdFf3F055A5Ad8": "Fed Badger",
            "0x5Fa92501106d7E4e8b4eF3c4d08112b6f306194C": "Fed 0xb1",
            "0xCBF33D02f4990BaBcba1974F1A5A8Aea21080E36": "Fed Fuse24",
            "0xcc180262347F84544c3a4854b87C34117ACADf94": "Fed Yearn",
        }
    }
}

def main():
    last_contraction_block = 10_000_000
    last_expansion_block = 10_000_000
    last_profit_block = 10_000_000
    while True:
        run_time = datetime.utcfromtimestamp(int( time.time() )).strftime("%m/%d/%Y, %H:%M:%S")
        print(f'\nStarting ... {run_time}\n')
        with Session(engine) as session:
            query = select(FedActivity).where(
                FedActivity.action == "contraction"
            ).order_by(desc(FedActivity.block))
            try:
                last_contraction_block = session.exec(query).first().block
            except:
                pass
            query = select(FedActivity).where(
                FedActivity.action == "expansion"
            ).order_by(desc(FedActivity.block))
            try:
                last_expansion_block = session.exec(query).first().block
            except:
                pass
            query = select(FedActivity).where(
                FedActivity.action == "profit"
            ).order_by(desc(FedActivity.block))
            try:
                last_profit_block = session.exec(query).first().block
            except:
                pass
            query = select(GaugeVotes).order_by(desc(GaugeVotes.block))
            try:
                last_vote_block = session.exec(query).first().block
            except:
                pass
        fed_contractions(last_contraction_block + 1)
        fed_expansions(last_expansion_block + 1)
        fed_profit(last_profit_block + 1)
        gauge_votes(last_vote_block + 1)
        inverse_stats()

        time.sleep(60*5)
    

def fed_expansions(last_block_recorded):
    yearn_fed_address = "0xcc180262347F84544c3a4854b87C34117ACADf94"
    fed_data = CHAIN_DATA[chain.id]["FEDS"]
    feds = []
    for k in fed_data.keys():
        feds.append(k)
    fed_address = feds[1]
    start_block = 10647875
    fed = contract(fed_address)
    fed = web3.eth.contract(str(fed_address), abi=fed.abi)
    topics = construct_event_topic_set(
        fed.events.Expansion().abi, 
        web3.codec, 
        {}
    )
    logs = web3.eth.get_logs(
            { 'topics': topics, 'address': feds, 'fromBlock': last_block_recorded, 'toBlock': chain.height }
    )

    events = fed.events.Expansion().processReceipt({'logs': logs})

    for event in events:
        amount = event.args.get("amount")
        ts = chain[event.blockNumber].timestamp
        dt = datetime.utcfromtimestamp(ts).strftime("%m/%d/%Y, %H:%M:%S")
        txn_hash = event.transactionHash.hex()
        txn = web3.eth.getTransaction(txn_hash)
        a = FedActivity()
        a.txn_hash = txn_hash
        a.fed_address = event.address
        a.action = "expansion"
        a.amount = amount / 1e18
        a.current_timestamp = ts
        a.date_string = dt
        a.chain_id = chain.id
        a.block = event.blockNumber
        try:
            a.fed_name = CHAIN_DATA[chain.id]["FEDS"][a.fed_address]
        except:
            a.fed_name = ""
        # Insert to database
        with Session(engine) as session:
            try:
                session.add(a)
                session.commit()
                print(f'Fed expansion event found. {amount / 1e18} DOLA minted at transaction hash: {txn_hash} , block {event.blockNumber}')    
                msg = f'📈 Fed Expansion Detected!\n\n{a.fed_name}\nFed Address: {a.fed_address}\nAmount: ${"{:,.2f}".format(a.amount)}\n\nView transaction: https://etherscan.io/tx/{a.txn_hash}'
                send_alert(msg)
            except:
                print(f'Failed writing {a.action} at {txn_hash}')

def fed_contractions(last_block_recorded):
    yearn_fed_address = "0xcc180262347F84544c3a4854b87C34117ACADf94"
    fed_data = CHAIN_DATA[chain.id]["FEDS"]
    feds = []
    for k in fed_data.keys():
        feds.append(k)
    fed_address = feds[1]
    fed = contract(fed_address)
    fed = web3.eth.contract(str(fed_address), abi=fed.abi)
    topics = construct_event_topic_set(
        fed.events.Contraction().abi, 
        web3.codec, 
        {}
    )
    logs = web3.eth.get_logs(
            { 'topics': topics, 'address': feds, 'fromBlock': last_block_recorded, 'toBlock': chain.height }
    )
    events = fed.events.Contraction().processReceipt({'logs': logs})

    for event in events:
        amount = event.args.get("amount")
        ts = chain[event.blockNumber].timestamp
        dt = datetime.utcfromtimestamp(ts).strftime("%m/%d/%Y, %H:%M:%S")
        txn_hash = event.transactionHash.hex()
        txn = web3.eth.getTransaction(txn_hash)
        a = FedActivity()
        a.txn_hash = txn_hash
        a.fed_address = event.address
        a.action = "contraction"
        a.amount = amount / 1e18
        a.current_timestamp = ts
        a.date_string = dt
        a.chain_id = chain.id
        a.block = event.blockNumber
        try:
            a.fed_name = CHAIN_DATA[chain.id]["FEDS"][a.fed_address]
        except:
            a.fed_name = ""
        # Insert to database
        with Session(engine) as session:
            insert_success = False
            try:
                session.add(a)
                session.commit()
                print(f'Fed contraction event found. {amount / 1e18} DOLA burned at transaction hash: {txn_hash} , block {event.blockNumber}')    
                msg = f'📉 Fed Contraction Detected!\n\n{a.fed_name}\nFed Address: {a.fed_address}\nAmount: ${"{:,.2f}".format(a.amount)}\n\nView transaction: https://etherscan.io/tx/{a.txn_hash}'
                send_alert(msg)
            except:
                print(f'Failed writing {a.action} at {txn_hash}')

def fed_profit(last_block_recorded):
    yearn_fed_address = "0xcc180262347F84544c3a4854b87C34117ACADf94"
    fed_data = CHAIN_DATA[chain.id]["FEDS"]
    feds = []
    for k in fed_data.keys():
        feds.append(k)
    fed_address = feds[1]
    fed = contract(fed_address)
    gov_address = fed.gov()
    dola_address = fed.underlying()
    dola = contract(dola_address)
    dola = web3.eth.contract(str(dola_address), abi=dola.abi)
    topics = construct_event_topic_set(
        dola.events.Transfer().abi, 
        web3.codec, 
        {
            'from': feds,
            'to': gov_address
        }
    )
    logs = web3.eth.get_logs(
            { 'topics': topics, 'address': dola_address, 'fromBlock': last_block_recorded, 'toBlock': chain.height }
    )

    events = dola.events.Transfer().processReceipt({'logs': logs})

    for event in events:
        # if event
        sender, receiver, amount = event.args.values()
        ts = chain[event.blockNumber].timestamp
        dt = datetime.utcfromtimestamp(ts).strftime("%m/%d/%Y, %H:%M:%S")
        txn_hash = event.transactionHash.hex()
        txn = web3.eth.getTransaction(txn_hash)
        a = FedActivity()
        a.txn_hash = txn_hash
        a.fed_address = sender
        a.action = "profit"
        a.amount = amount / 1e18
        a.current_timestamp = ts
        a.date_string = dt
        a.chain_id = chain.id
        a.block = event.blockNumber
        try:
            a.fed_name = CHAIN_DATA[chain.id]["FEDS"][a.fed_address]
        except:
            a.fed_name = ""
        # Insert to database
        with Session(engine) as session:
            try:
                session.add(a)
                session.commit()
                print(f'Fed profit event found. {amount / 1e18} DOLA taken as profit at transaction hash: {txn_hash} , block {event.blockNumber}')
                # if a.fed_address == yearn_fed_address:
                msg = f'💰 New Fed Profit Collected!\n\n{a.fed_name}\nFed Address: {a.fed_address}\nAmount: ${"{:,.2f}".format(a.amount)}\n\nView transaction: https://etherscan.io/tx/{a.txn_hash}'
                send_alert(msg)
            except:
                print(f'Failed writing {a.action} at {txn_hash}')

def gauge_votes(last_block_recorded):
    dola_gauge = "0x8Fa728F393588E8D8dD1ca397E9a710E53fA553a"
    current_block = chain.height
    gauge_controller_addr = "0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB"
    gauge_controller = contract(gauge_controller_addr)
    gauge_controller = web3.eth.contract(str(gauge_controller_addr), abi=gauge_controller.abi)
    topics = construct_event_topic_set(
        gauge_controller.events.VoteForGauge().abi, 
        web3.codec, 
        {
        }
    )
    
    logs = web3.eth.get_logs(
            {'address': gauge_controller_addr, 'topics': topics, 'fromBlock': last_block_recorded, 'toBlock': chain.height }
    )

    events = gauge_controller.events.VoteForGauge().processReceipt({'logs': logs})

    last_time = 0
    
    for event in events:
        if event.address != gauge_controller_addr:
            continue
        ts, user, gauge_address, weight = event.args.values()
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

        v = GaugeVotes()
        v.user_lock_time_remaining = remaining_lock
        v.current_timestamp = current_time
        v.block = event.blockNumber
        v.txn_hash = txn_hash
        v.date_string = dt
        v.chain_id = chain.id
        v.weight = weight
        v.user = user
        v.gauge = gauge_address
        v.user_lock_expire = lock_end
        v.gauge_name = name
        v.user_vecrv_balance = vecrv.balanceOf(user, block_identifier=event.blockNumber) / 1e18
        # Insert to database
        with Session(engine) as session:
            insert_success = False
            session.add(v)
            session.commit()
            print(f"vote added. {v.user}. {v.weight} for {v.gauge}. txn hash {v.txn_hash}. sync {v.block} / {chain.height}.")
            if v.gauge == dola_gauge:
                msg = f'🗳 New DOLA gauge vote detected!\n\nUser: {v.user}\nGauge: {v.gauge}\nWeight: {v.weight}\nnveCRV balance: {"{:,.2f}".format(v.user_vecrv_balance)}\nLock time remaining (yrs): {"{:.2f}".format(v.user_lock_time_remaining)}\n\nView transaction: https://etherscan.io/tx/{v.txn_hash}'
                send_alert(msg)

def inverse_stats():
    ts = int(time.time())
    vaults = [
        "0xD4108Bb1185A5c30eA3f4264Fd7783473018Ce17", # dola vault
        "0x67B9F46BCbA2DF84ECd41cC6511ca33507c9f4E9", # crv dola vault
    ]
    data = {}
    data["last_update_str"] = datetime.utcfromtimestamp(ts).strftime("%m/%d/%Y, %H:%M:%S")
    data["last_update"] = ts
    data["yearn"] = {}
    data["yearn"]["vaults"] = []
    strats = []
    for vault in vaults:
        d = {}
        a = vault
        vault = Contract(vault)
        d["symbol"] = vault.symbol()
        d["name"] = vault.name()
        d["want_symbol"] = Contract(vault.token()).symbol()
        d["want_address"] = vault.token()
        strats.append(vault.withdrawalQueue(0))
        decimals = vault.decimals()
        d["decimals"] = decimals
        d["type"] = "vault"
        d["address"] = a
        d["price_per_share"] = vault.pricePerShare() / 10**decimals
        d["deposit_limit"] = vault.depositLimit() / 10**decimals
        d["vault_performance_fee"] = vault.performanceFee()
        d["management_fee"] = vault.managementFee()
        data["yearn"]["vaults"].append(d)

    data["yearn"]["strategies"] = []
    for strat in strats:
        d = {}
        d["type"] = "strategy"
        d["address"] = strat
        strat = Contract(strat)
        vault_address = strat.vault()
        v = Contract(vault_address)
        d["vault_address"] = vault_address
        d["name"] = v.name()
        d["want_symbol"] = Contract(v.token()).symbol()
        d["want_address"] = v.token()
        decimals = v.decimals()
        d["decimals"] = decimals
        d["total_gain"] = v.strategies(strat).dict()["totalGain"] / 10**decimals
        virtual_price = 1
        if strat.vault() == "0x67B9F46BCbA2DF84ECd41cC6511ca33507c9f4E9":
            pool = Contract("0xAA5A67c256e27A5d80712c51971408db3370927D")
            virtual_price = pool.get_virtual_price() / 1e18
        d["total_gain_usd"] = d["total_gain"] * virtual_price
        d["total_loss"] = v.strategies(strat).dict()["totalLoss"] / 10**decimals
        d["total_loss_usd"] = d["total_loss"] * virtual_price
        d["last_report"] = v.strategies(strat).dict()["lastReport"]
        d["total_assets"] = v.totalAssets() / 10**decimals
        d["strat_performance_fee"] = v.strategies(strat).dict()["performanceFee"]
        try:
            d["max_slippage_in"] = strat.slippageProtectionIn()
            d["max_slippage_out"] = strat.slippageProtectionOut()
        except:
            d["max_slippage_in"] = 0
            d["max_slippage_out"] = 0
        d["estimated_total_assets"] = strat.estimatedTotalAssets() 
        reports = []
        with Session(engine) as session:
            reports = []
            query = select(Reports).where(
                Reports.strategy_address == strat.address
            )
            query_results = session.exec(query)
            for r in query_results:
                r = r.as_dict()
                reports.append(r)
        d["reports"] = reports
        data["yearn"]["strategies"].append(d)

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
        coin = {}
        tvl = tvl + pool.balances(c) / 10**decimals
        coin["token_address"] = token_address
        coin["name"] = token.name()
        coin["symbol"] = token.symbol()
        decimals = token.decimals()
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
    # Inverse Fed Data
    yearn_fed = Contract("0xcc180262347F84544c3a4854b87C34117ACADf94")
    data["inverse"] = {}
    data["inverse"]["yearn_fed"] = {}
    fed = data["inverse"]["yearn_fed"]
    fed["address"] = yearn_fed.address
    fed["chair"] = yearn_fed.chair()
    fed["gov"] = yearn_fed.gov()
    fed["supply"] = yearn_fed.supply() / 1e18
    vault_address = yearn_fed.vault()
    fed["vault_address"] = vault_address
    vault = Contract(vault_address)
    yvtoken_balance = vault.balanceOf(yearn_fed.address)
    decimals = 10**vault.decimals()
    fed["yvtoken_balance"] = yvtoken_balance / decimals
    fed["pending_profit"] = (yvtoken_balance / decimals) * (vault.pricePerShare() / decimals)
    fed["actions"] = []
    with Session(engine) as session:
        actions = []
        query = select(FedActivity).where(
            FedActivity.fed_address == yearn_fed.address
            # FedActivity.fed_address == "0x5Fa92501106d7E4e8b4eF3c4d08112b6f306194C"
        ).order_by(desc(FedActivity.block))
        query_results = session.exec(query)
        for a in query_results:
            a = a.as_dict()
            del a["id"]
            del a["chain_id"]
            actions.append(a)
    fed["actions"] = actions

    # Gauge Vote Data
    data["curve"]["gauge_votes"] = []
    dola_gauge_address = "0x8Fa728F393588E8D8dD1ca397E9a710E53fA553a"
    votes = []
    with Session(engine) as session:
            query = select(GaugeVotes).where(
                GaugeVotes.gauge == dola_gauge_address
            )
            query_results = session.exec(query)
            for v in query_results:
                v = v.as_dict()
                del v["id"]
                del v["chain_id"]
                votes.append(v)
    data["curve"]["gauge_votes"] = votes
    # pp = pprint.PrettyPrinter(indent=4)
    # pp.pprint(json.dumps(data, default=default))
    # pp.pprint(data["curve"]["pool"])
    d = json.dumps(data, default=default)
    with open('../inverse-api/data.json', 'w') as outfile:
        outfile.write(d)

def default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError("Object of type '%s' is not JSON serializable" % type(obj).__name__)

def send_alert(msg):
    encoded_message = urllib.parse.quote(msg)
    url = f"https://api.telegram.org/bot{telegram_bot_key}/sendMessage?chat_id={chat_id}&text={encoded_message}&disable_web_page_preview=true"
    print(url)
    urllib.request.urlopen(url)
    print(msg)