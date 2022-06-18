import json, time, os
from dotenv import load_dotenv, find_dotenv
from datetime import datetime
import pprint
from brownie import (
    Contract,
    accounts,
    web3,
    ZERO_ADDRESS,
    chain,
)

def main():
    oracle = Contract("0x83d95e0D5f402511dB06817Aff3f9eA88224B030")
    sscs = [
        "0x65A8efC842D2Ba536d3F781F504A1940f61124b4",
        "0x92c212F4d6A8Ad964ACAe745e1B45309B470Af6E",
        "0x0c8f62939Aeee6376f5FAc88f48a5A3F2Cf5dEbB",
        "0xa6D1C610B3000F143c18c75D84BaA0eC22681185",
        "0x494A7255C8df1f8d6064971707dB18dd1627d835",
        "0xBEDDD783bE73805FEbda2C40a2BF3881F04Fd7Cc",
        "0xb85413f6d07454828eAc7E62df7d847316475178",
        "0x4b254EbBbb8FDb9D3E848501784692b2726b310c",
        "0x29367915508e47c631d220caEbA855901c13a3dE",
        "0x64B2a32f030D9210E51ed8884C0D58b89137Ca81",
        "0x74b3E5408B1c29E571BbFCd94B09D516A4d81f36",
        "0x8784889b0d48a223c3F48312651643Edd8526bbD",
        "0x8c44Cc5c0f5CD2f7f17B9Aca85d456df25a61Ae8",
        "0xCdC3d3A18c9d83Ee6E10E91B48b1fcb5268C97B5",
        "0xF9fDc2B5F60355A237deb8BD62CC117b1C907f7b",
        "0xc57A4D3FBEF85e675f6C3656498beEfe6F9DcB55",
        "0xA558D4Aef61AACDEE8EF21c11B3164cd11B273Af",
        "0x034d775615d50D870D742caA1e539fC8d97955c2",
        "0xe614f717b3e8273f38Ed7e0536DfBA60AD021c85",
        "0x960818b3F08dADca90b840298721FE7B419fBE12",
        "0x074620e389B5715f7ba51Fc062D8fFaf973c7E02",
        "0xB0F8b341951233BF08A5F15a838A1a85B016aEf9"
    ]

    current_ts = int(time.time())
    DAY = 60 * 60 * 24
    for i in range(30,-1,-6):
        ts_to_test = current_ts - (DAY * i)
        try:
            block = closest_block_after_timestamp(ts_to_test)
        except:
            block = closest_block_after_timestamp(ts_to_test - 100)
        print(f'--- {i} DAYS AGO ---')
        total = 0
    
        for s in sscs:
            s = Contract(s)
            v = Contract(s.vault())
            decimals = 10**v.decimals()
            price = oracle.getPriceUsdcRecommended(v.token(), block_identifier=block) / 10**6
            tvl = v.strategies(s, block_identifier=block).dict()["totalDebt"] / decimals
            tvl_usd = price * tvl
            tvl_usd_fmt = "${:,.2f}". format(tvl_usd)
            total = total + tvl_usd
            print(s.name(), tvl_usd_fmt)
        print(f'Total: {"${:,.2f}". format(total)}\n')
        

def closest_block_after_timestamp(timestamp):
    if timestamp > time.time():
        return chain.height - 5
    height = chain.height
    lo, hi = 0, height

    while hi - lo > 1:
        mid = lo + (hi - lo) // 2
        if get_block_timestamp(mid) > timestamp:
            hi = mid
        else:
            lo = mid

    if get_block_timestamp(hi) < timestamp:
        raise IndexError('timestamp is in the future')

    return hi

def get_block_timestamp(height):
    """
    An optimized variant of `chain[height].timestamp`
    """
    if chain.id == 1:
        header = web3.manager.request_blocking(f"erigon_getHeaderByNumber", [height])
        return int(header.timestamp, 16)
    else:
        return chain[height].timestamp