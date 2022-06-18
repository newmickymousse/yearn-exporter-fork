import json, time, os
from dotenv import load_dotenv, find_dotenv
from datetime import datetime
import pprint
from brownie import (
    Contract,
    accounts,
    ZERO_ADDRESS,
    chain,
)
load_dotenv(find_dotenv())

oracle = Contract("0x83d95e0D5f402511dB06817Aff3f9eA88224B030")

def main():
    strats = [
        "0xa6D1C610B3000F143c18c75D84BaA0eC22681185", # DAI IB
        "0x0c8f62939Aeee6376f5FAc88f48a5A3F2Cf5dEbB", # USDC IB
        "0x960818b3F08dADca90b840298721FE7B419fBE12", # SSB USDC
        "0x034d775615d50D870D742caA1e539fC8d97955c2", # SSB DAI
        "0x0967aFe627C732d152e3dFCAdd6f9DBfecDE18c3", # STETH ACC
        "0xF9fDc2B5F60355A237deb8BD62CC117b1C907f7b", # SSC STETH
        # "0xb85413f6d07454828eAc7E62df7d847316475178", # SSC HBTC
        # "0x074620e389B5715f7ba51Fc062D8fFaf973c7E02", # SSB WBTC
        "0xB0F8b341951233BF08A5F15a838A1a85B016aEf9", # SSB WETH
        # "0xA558D4Aef61AACDEE8EF21c11B3164cd11B273Af", # SSB DOLA
    ]

    curve_pools = [
        "0xDC24316b9AE028F1497c275EB9192a3Ea0f67022", # STETH
        "0x2dded6Da1BF5DBdF597C45fcFaa3194e53EcfeAF", # IB
        # "", # FRAX
    ]
    balancer_pools = [
        0x06df3b2bbb68adc8b0e302443692037ed9f91b42000000000000000000000063,
        0xfeadd389a5c427952d8fdb8057d6c8ba1156cc56000000000000000000000066,
        0x32296969ef14eb0c6d29669c550d4a0449130230000200000000000000000080,
    ]

    vaults = ["0xA696a63cc78DfFa1a63E9E50587C197387FF6C7E"] # WBTC
    for s in strats:
        s = Contract(s)
        v = s.vault()
        if v not in vaults:
            vaults.append(v)

    vault_data = get_vault_data(vaults)
    curve_pool_data = get_curve_pool_data(curve_pools)
    balancer_pool_data = get_balancer_pool_data(balancer_pools)
    
    simulation_data = []
    for s in strats:
        stats = setup(s)
        simulation_data.append(stats)

    data = {}
    ts = chain.time()
    data["block"] = chain.height
    data["last_update"] = ts
    data["last_update_str"] = datetime.utcfromtimestamp(ts).strftime("%m/%d/%Y, %H:%M:%S")
    data["simulation_data"] = simulation_data
    data["curve_pool_data"] = curve_pool_data
    data["vault_data"] = vault_data
    data["balancer_pool_data"] = balancer_pool_data
    json_formatted_str = json.dumps(data, indent=4)
    print(json_formatted_str)
    path = os.environ.get('API_PATH')
    d = json.dumps(data, default=str)
    with open(f'{path}/position_monitor.json', 'w') as outfile:
        outfile.write(d)
        print("new postion monitor update published")

def setup(strat):
    if chain.id == 1:
        account = accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)
    if chain.id == 250:
        account = accounts.at("0x72a34AbafAB09b15E7191822A679f28E067C4a16", force=True)
    s = Contract(strat, owner=account)
    v = Contract(s.vault(), owner=account)
    pps1 = v.pricePerShare()
    
    actual_dr = int(v.strategies(s).dict()["totalDebt"] / v.totalAssets() * 10_000)
    target_dr = v.strategies(s).dict()["debtRatio"]
    starting_dr = actual_dr if  actual_dr > target_dr else target_dr 
    spare = actual_dr if  actual_dr < target_dr else target_dr 

    low, high = 0, starting_dr
    if starting_dr >= spare + (10_000 - v.debtRatio()):
        pass
        free_ratios(v, s)
    try:
        s.setParams(
            10_000,
            10_000,
            s.maxSingleDeposit()*10,
            0
        )
    except:
        pass
    chain.snapshot()
    last_best = 10_000
    stats = {
        "strategy_address": s.address,
        "strategy_name": s.name(),
        "vault_address": v.address,
        "vault_symbol": v.symbol(),
        "testing_ratio": 10_000,
        "success": False
    }
    best_stats = stats
    while high - low > 1:
        mid = (high + low) // 2
        harvest_stats = harvest(s, v, mid, pps1, stats)
        if harvest_stats["success"]:
            best_stats = harvest_stats
            last_best = mid
            high = mid
        else:
            low = mid
    print("➡➡ lowest ratio without loss:", last_best)
    if not best_stats["success"]:
        best_stats["max_no_loss_ratio"] = best_stats["testing_ratio"] + 1
    else:
        best_stats["max_no_loss_ratio"] = best_stats["testing_ratio"]
    del best_stats["testing_ratio"]
    if check_key(best_stats,"max_no_loss_ratio") and check_key(best_stats, "current_ratio"):
        best_stats["max_ratio_reduction"] = best_stats["current_ratio"] - best_stats["max_no_loss_ratio"]
        best_stats["success"] = True
    else:
        best_stats["success"] = False
    return best_stats

def harvest(s, v, target_dr, pps1, stats):
    dr = v.strategies(s).dict()["debtRatio"]
    before_debt = v.strategies(s).dict()["totalDebt"]
    print(s.address, s.name())
    print("Current Debt Ratio is",dr)
    print("Testing Debt Ratio of",target_dr, "...")
    v.updateStrategyDebtRatio(s, target_dr)
    try:
        b_vault = Contract(s.balancerVault())
        amount_in_pool = b_vault.getPoolTokenInfo(s.balancerPoolId(), s.want())[0]
        if amount_in_pool * .95 < v.debtOutstanding(s):
            print(f'🚨🚨 Harvest fails due to debtoutstanding > pooled tokens {s.address} {s.name()}.')
            stats["success"] = False
            return stats
    except:
        pass
    try:
        s.setDoHealthCheck(False)
    except:
        pass
    try:
        s.updateMaxSingleTrade(s.estimatedTotalAssets())
    except:
        pass
    try:
        s.updateSlippageProtectionOut(10_000)
    except:
        pass
    try:
        tx = s.harvest()
    except:
        print("🚨 harvest failed")
        stats["success"] = False
        return stats

    stats["testing_ratio"] = target_dr
    stats["profit"] = tx.events["Harvested"]["profit"]/10**v.decimals()
    stats["loss"] = tx.events["Harvested"]["loss"]/10**v.decimals()
    stats["debt_payment"] = tx.events["Harvested"]["debtPayment"]/10**v.decimals()
    price = oracle.getPriceUsdcRecommended(v.token()) / 10**6
    stats["debt_payment_usd"] = price * stats["debt_payment"]
    stats["strategy_debt_before"] = int(before_debt/10**v.decimals())
    stats["strategy_debt_before_usd"] = int(before_debt/10**v.decimals()*price)
    print(tx.events["Harvested"])
    d = v.strategies(s).dict()["totalDebt"]
    stats["strategy_debt_after"] = int(d/10**v.decimals())
    stats["strategy_debt_after_usd"] = int(d/10**v.decimals() * price)
    stats["success"] =  False

    if stats["loss"] > 0:
        print("🚨")
        stats["success"] =  False
    else:
        print("✅")
        stats["success"] =  True
    chain.revert()
    stats["current_ratio"] = dr
    print("-----------")
    return stats

def free_ratios(vault, strategy):
    for i in range(0,20):
        s = vault.withdrawalQueue(i)
        if s == strategy.address:
            continue
        if s == ZERO_ADDRESS:
            break
        vault.updateStrategyDebtRatio(s, 0)

def get_vault_data(vaults):
    data = []
    for v in vaults:
        d = {}
        v = Contract(v)
        d["address"] = v.address
        d["symbol"] = v.symbol()
        decimals = v.decimals()
        d["decimals"] = decimals
        d["total_assets"] = v.totalAssets() / 10**decimals
        d["underlying"] = v.token()
        d["underlying_symbol"] = Contract(v.token()).symbol()
        d["available_reserves"] = Contract(d["underlying"]).balanceOf(v) / 10**decimals
        data.append(d)
    return data

def get_balancer_pool_data(pool_ids):
    vault = Contract("0xBA12222222228d8Ba445958a75a0704d566BF2C8")
    
    data = []
    for p in pool_ids:
        tokens = list(vault.getPoolTokens(p).dict()["tokens"])
        balances = list(vault.getPoolTokens(p).dict()["balances"])
        d = {}
        token_list = []
        total_assets = 0
        pool = Contract(vault.getPool(p)[0])
        d["name"] = pool.name()
        d["pid"] = p
        d["address"] = pool.address
        d["total_assets"] = 0
        for i, t in enumerate(tokens):
            t = Contract(t)
            token = {}
            token["address"] = t.address
            token["symbol"] = t.symbol()
            token["decimals"] = t.decimals()
            token["balance"] = int(balances[i] / 10**token["decimals"])
            total_assets += token["balance"]
            token_list.append(token)
        d["tokens"] = token_list
        d["total_assets"] = int(total_assets)
        data.append(d)
    print(data)
    json_formatted_str = json.dumps(data, indent=4)
    print(json_formatted_str)
    return data

def get_curve_pool_data(pools):
    data = []
    for p in pools:
        p = Contract(p)
        d = {}
        token_list = []
        total_assets = 0
        for i in range(0,5): # Token iterate
            token = {}
            try:
                if "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE" == p.coins(i):
                    token["address"] = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
                    token["symbol"] = "ETH"
                    token["decimals"] = 18
                    token["balance"] = int(p.balances(i) / 10**token["decimals"])
                    total_assets += token["balance"]
                    token_list.append(token)
                else:
                    t = Contract(p.coins(i))
                    try:
                        # IronBank pool
                        x_rate = t.exchangeRateStored()
                        underlying = Contract(t.underlying())
                        token["address"] = underlying.address
                        token["symbol"] = underlying.symbol()
                        token["decimals"] = underlying.decimals()
                        dec = 10**t.decimals()
                        bal = p.balances(i) / dec
                        token["balance"] = int(x_rate / 10**token["decimals"] / dec * bal / 100)
                    except:
                        # All other pools
                        token["address"] = t.address
                        token["symbol"] = t.symbol()
                        token["decimals"] = t.decimals()
                        token["balance"] = int(p.balances(i) / 10**token["decimals"])
                    total_assets += token["balance"]
                    token_list.append(token)
            except:
                break
        d["total_assets"] = int(total_assets)
        d["address"] = p.address
        try:
            d["name"] = p.name()
        except:
            if p.address == "0xDC24316b9AE028F1497c275EB9192a3Ea0f67022":
                d["name"] = "StETH"
            if p.address == "0x2dded6Da1BF5DBdF597C45fcFaa3194e53EcfeAF":
                d["name"] = "IronBank"
        d["tokens"] = token_list
        data.append(d)
    return data

def check_key(dict, key):
    if key in dict:
        return True
    else:
        return False