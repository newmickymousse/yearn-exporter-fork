import os

import matplotlib.pyplot as plt
import pandas as pd
import sentry_sdk
from datetime import datetime, timezone
from matplotlib import colors
from yearn.db.models import TokenData, Session, Snapshot, engine, select
from yearn.networks import Network
from yearn.utils import contract, contract_creation_block
from web3._utils.events import construct_event_topic_set

from yearn.utils import closest_block_after_timestamp
from brownie import chain, web3, Contract, ZERO_ADDRESS

sentry_sdk.set_tag('script','science')

def checker():
    deploy_block = 10724600
    a = ''
    c = Contract(a)
    c = web3.eth.contract(str(a), abi=c.abi)  
    topics = construct_event_topic_set(
        c.events.ApproveWallet().abi, 
        web3.codec, 
        {
        }
    )
    logs = web3.eth.get_logs(
            { 'address': a, 'topics': topics, 'fromBlock': deploy_block, 'toBlock': chain.height }
    )

    events = c.events.ApproveWallet().processReceipt({'logs': logs})
    c = Contract(a)
    for event in events:
        a = event.args.get('')
        ts = chain[event.blockNumber].timestamp
        dt = datetime.utcfromtimestamp(ts).strftime("%m/%d/%Y, %H:%M:%S")
        print(a,dt)


def export_data():
    spell = Contract("0x090185f2135308BaD17527004364eBcC2D37e5F6")
    inv = Contract("0x41D5D79431A913C4aE7d69a668ecdfE5fF9DFB68")
    yfi = Contract("0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e")
    crv = Contract("0xD533a949740bb3306d119CC777fa900bA034cd52")
    token = spell
    use_db = False
    decimals = token.decimals()
    symbol = token.symbol()
    create_block = contract_creation_block(token.address)
    starting_ts = chain[create_block].timestamp
    check_block = closest_block_after_timestamp(starting_ts)
    current_block = chain.height
    DAY = 60 * 60 * 24
    i = 1
    supplies = []
    timestamps = []
    supplies.append(0)
    timestamps.append(starting_ts - 1)

    while check_block < current_block:
        # total_supply_at_block = token.totalSupply(block_identifier=check_block) / 10**decimals
        # inaccessible = token.balanceOf(token, block_identifier=check_block) / 10**decimals
        # adjusted_total_supply_at_block = total_supply_at_block - inaccessible
        # print(check_block, total_supply_at_block)
        max_supply = token.MAX_SUPPLY()
        d = TokenData()
        d.total_supply = token.totalSupply(block_identifier=check_block)
        d.block = check_block
        d.chain_id = chain.id
        d.address = token.address
        d.timestamp = chain[check_block].timestamp
        d.date_string = dt = datetime.utcfromtimestamp(d.timestamp).strftime("%m/%d/%Y, %H:%M:%S")
        d.symbol = symbol
        remaining_supply = max_supply - d.total_supply
        
        if use_db:
            with Session(engine) as session:
                session.add(d)
                session.commit()
                # try:
                #     session.add(d)
                #     session.commit()
                # except:
                #     print(f"failed to write at block {check_block}")
                #     pass
        else:
            timestamps.append(int(d.timestamp))
            supplies.append(int(remaining_supply/1e18))
        i += 7
        try:
            check_block = closest_block_after_timestamp(starting_ts + (DAY * i))
            print(check_block)
        except:
            print("Next block is in future")
            break
    data = {"timestamp":timestamps, "remaining_supply":supplies}
    chart(use_db, token, data)

def chart(use_db, token, data):
    
    """
    Make yearn.science TVL chart
    """
    plt.rcParams['legend.frameon'] = False
    plt.rcParams['font.family'] = 'Adobe Garamond Pro'
    plt.rcParams['font.style'] = 'italic'
    if use_db:
        with Session(engine) as session:
            data = []
            timestamps = []
            supplies = []
            query = select(TokenData).where(
                    TokenData.address == token.address
                )
            query_results = session.exec(query)
            for r in query_results:
                r = r.as_dict()
                del r['id']
                del r['symbol']
                del r['chain_id']
                del r['address']
                del r['date_string']
                timestamps.append(int(r['timestamp']))
                supplies.append(int(r['adjusted_total_supply']))
                data.append(r)
            d = {'timestamp': timestamps, 'total_supply':supplies}
    else:
        d = data
    df = pd.DataFrame.from_dict(d)
    ax = plt.gca()
    df.plot(kind='line',x='timestamp',y='remaining_supply')
    plt.show()
    plt.savefig('chart.png')
    # # find the last date where all chains are indexed to avoid underreporting tvl
    # print('last_indexed', df.groupby('chain_id').snapshot.last(), '', sep='\n')
    # last_indexed = df.groupby('chain_id').snapshot.last().min()
    # print(df)
    # for key in ['product', 'chain_id', ['chain_id', 'product']]:
    #     pdf = pd.pivot_table(df, 'assets', 'snapshot', key, 'sum').sort_index()[:last_indexed]

    #     # match with the color scheme
    #     if key == 'product':
    #         order = [x for x in ['v2', 'v1', 'earn', 'ib', 'special'] if x in pdf.columns]
    #         pdf = pdf[order]
        
    #     yearn_colors = ['#0657F9', '#FABF06','#23D198', '#EF1E02', '#666666']
    #     cmap = colors.LinearSegmentedColormap.from_list('yearn', colors=yearn_colors)
    #     pdf.plot(stacked=True, kind='area', cmap=cmap, linewidth=0)
        
    #     plt.gca().set_axisbelow(True)
    #     plt.grid(linewidth=0.5)
    #     plt.xlabel('')
    #     plt.ylabel('dollaridoos')
    #     plt.xlim(xmin=pd.to_datetime('2020-07-17'), xmax=last_indexed)
    #     plt.ylim(ymin=0)
    #     total = pdf.iloc[-1].sum()
    #     print(pdf.index[-1])
    #     plt.title(f'Yearn TVL is ${total / 1e9:.3f} billion')
    #     plt.tight_layout()
    #     os.makedirs('static', exist_ok=True)
    #     text_key = '_'.join(key) if isinstance(key, list) else key
    #     plt.savefig(f'static/yearn_{text_key}.png', dpi=300)
