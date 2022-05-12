import logging
import time, os
import telebot
from discordwebhook import Discord
from dotenv import load_dotenv
from scripts.collect_reports import last_harvest_block
from yearn.cache import memory
import pandas as pd
from datetime import datetime, timezone
from brownie import chain, web3, Contract, ZERO_ADDRESS
from web3._utils.events import construct_event_topic_set
from yearn.utils import contract, contract_creation_block
from yearn.prices import magic, constants
from yearn.db.models import Reports, Event, Transactions, Session, engine, select
from sqlalchemy import desc, asc
from yearn.networks import Network
from yearn.events import decode_logs
import warnings
warnings.filterwarnings("ignore", ".*Class SelectOfScalar will not make use of SQL compilation caching.*")
warnings.filterwarnings("ignore", ".*Locally compiled and on-chain*")
warnings.filterwarnings("ignore", ".*It has been discarded*")
with Session(engine) as session:
    # SELECT MOST RECENT HARVEST TIMESTAMP
    select max(timestamp), strategy_address from reports 
    group by strategy_address 
    # GET ALL HARVEST DATA FROM STARTEGY TABLE
    select * from strategy

    strategies = []
    last_harvest_times = []
    for index, s in enumerate(strategies):
        for l in last_harvest_times:
            if s.strategy_address == l.address:
                if s.timestamp != l.last_report:
                    #LOOKUP DATA
                    refresh_data(s.address)
                last_harvest_times.pop(index)
                

def refresh_data(address):

    query = select(Reports).where(
        Reports.chain_id == chain.id, Reports.strategy_address == r.strategy_address
    ).order_by(desc(Reports.block))
    previous_report = session.exec(query).first()
    if previous_report != None:
        previous_report_id = previous_report.id
        r.previous_report_id = previous_report_id
        r.rough_apr_pre_fee, r.rough_apr_post_fee = compute_apr(r, previous_report)