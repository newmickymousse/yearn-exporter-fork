import os

import matplotlib.pyplot as plt
import pandas as pd
import sentry_sdk
from datetime import datetime, timezone
from matplotlib import colors
from yearn.db.models import TokenData, Session, Snapshot, engine, select
from yearn.networks import Network
from yearn.utils import contract, contract_creation_block
from yearn.utils import closest_block_after_timestamp
from brownie import chain, web3, Contract, ZERO_ADDRESS

sentry_sdk.set_tag('script','science')

def export_data():
    steth = Contract("0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84")
    pool = Contract("0xDC24316b9AE028F1497c275EB9192a3Ea0f67022")
    token = steth
    bal = pool.balances(0)/1e18
    balances = []
    balances.append(bal)
    decimals = token.decimals()
    symbol = token.symbol()
    create_block = contract_creation_block(pool.address)
    DAY = 60 * 60 * 24
    starting_ts = chain[create_block].timestamp + (DAY * 25)
    check_block = closest_block_after_timestamp(starting_ts)
    current_block = chain.height
    
    i = 1
    timestamps = []
    timestamps.append(starting_ts - 1)
    ratios = []
    ratios.append(.50)
    while check_block < current_block:
        eth_bal = pool.balances(0,block_identifier=check_block) / 1e18
        steth_bal = pool.balances(1,block_identifier=check_block) / 1e18
        total_balance = eth_bal + steth_bal
        ratio = 0 if total_balance == 0 else  steth_bal/total_balance
        print(steth_bal, eth_bal, total_balance)
        timestamp = chain[check_block].timestamp
        # date_string = dt = datetime.utcfromtimestamp(d.timestamp).strftime("%m/%d/%Y, %H:%M:%S")
       
        timestamps.append(int(timestamp))
        balances.append(int(steth_bal))
        ratios.append(ratio)
        i += 1
        dt = datetime.utcfromtimestamp(timestamp).strftime("%m/%d/%Y, %H:%M:%S")
        print(dt)
        try:
            check_block = closest_block_after_timestamp(starting_ts + (DAY * i))
        except:
            print("Next block is in future")
            break

    data = {"timestamp":timestamps, "ratios": ratios}
    chart(False, token, data)

def chart(use_db, token, data):
    
    """
    Make yearn.science TVL chart
    """
    plt.rcParams['legend.frameon'] = False
    plt.rcParams['font.family'] = 'Adobe Garamond Pro'
    plt.rcParams['font.style'] = 'italic'
    df = pd.DataFrame.from_dict(data)
    ax = plt.gca()
    df.plot(kind='line',x='timestamp',y='ratios')
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
