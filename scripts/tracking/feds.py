import asyncio, json
from configparser import MAX_INTERPOLATION_DEPTH
from collections import defaultdict
from datetime import datetime
from brownie import chain, web3, Contract
from rich import print
from rich.progress import track
from rich.table import Table
from web3._utils.events import construct_event_topic_set
from yearn.utils import contract
from brownie.exceptions import ContractNotFound
import warnings
warnings.filterwarnings("ignore", ".*cannot be installed or is not supported by Brownie.*")

def main():
    feds = [
        '0x7eC0D931AFFBa01b77711C2cD07c76B970795CDd', # Stabilizer
        '0x6112818d0c0d75448551b76EC80F14de10F4E054', # Flashmint
        '0x4d7928e993125A9Cefe7ffa9aB637653654222E2', # xChain Fed
        '0x5E075E40D01c82B6Bf0B0ecdb4Eb1D6984357EF7',
        '0xe3277f1102C1ca248aD859407Ca0cBF128DB0664',
        '0x7765996dAe0Cf3eCb0E74c016fcdFf3F055A5Ad8',
        '0x5Fa92501106d7E4e8b4eF3c4d08112b6f306194C',
        '0xCBF33D02f4990BaBcba1974F1A5A8Aea21080E36',
    ]

    for f in feds:
        f = Contract(f)
        try:
            print(f.address, f.chair(), f.gov())
        except:
            pass