from brownie import chain, web3, Contract, accounts
import warnings
warnings.filterwarnings("ignore", ".*cannot be installed or is not supported by Brownie.*")


def main():
    nour = accounts.at("0x16EC2AeA80863C1FB4e13440778D0c9967fC51cb", force=True)
    rando = accounts.at("0x88017d9449681d2db852B0311670182929151080", force=True)
    treasury = accounts.at("0xbB6ef0B93792E4E98C6E6062EB1a9638D82E500f", force=True)
    dola_gauge = Contract("0x8Fa728F393588E8D8dD1ca397E9a710E53fA553a")
    bribev2 = Contract("0x7893bbb46613d7a4FbcC31Dab4C9b823FfeE1026")
    inv = Contract("0x41D5D79431A913C4aE7d69a668ecdfE5fF9DFB68")

    nour_before = inv.balanceOf(nour) / 1e18
    rando_before = inv.balanceOf(rando) / 1e18
    # rando_before = inv.balanceOf(rando) / 1e18
    # print("claimable nour",bribev2.claimable(nour,dola_gauge,inv) / 1e18)
    # bribev2.claim_reward(dola_gauge,inv,{'from':nour})

    # nour_gain =  (inv.balanceOf(nour) / 1e18) - nour_before
    # print("nour_gain1",nour_gain)

    bribev2.claim_reward(dola_gauge,inv,{'from':nour})

    # inv.approve(bribev2, 2**256-1, {'from': treasury})
    # bribev2.add_reward_amount(dola_gauge, inv, 40e18, {'from': treasury})

    # bribev2.claim_reward(dola_gauge,inv,{'from':nour})
    # nour_gain =  (inv.balanceOf(nour) / 1e18) - nour_before
    # print("nour_gain1",nour_gain)

    # bribev2.claim_reward(dola_gauge,inv,{'from':rando})
    # rando_gain =  (inv.balanceOf(rando) / 1e18) - rando_before
    # print("rando_gain1",rando_gain)

    # print("claimable nour",bribev2.claimable(nour,dola_gauge,inv) / 1e18)
    # print("claimable rando",bribev2.claimable(rando,dola_gauge,inv) / 1e18)

    # nour_before = inv.balanceOf(nour) / 1e18
    # bribev2.claim_reward(dola_gauge,inv,{'from':rando})
    # bribev2.claim_reward(dola_gauge,inv,{'from':nour})
    # nour_gain =  (inv.balanceOf(nour) / 1e18) - nour_before
    # print("nour_gain2",nour_gain)


    # rando_after =  inv.balanceOf(rando) / 1e18
    # rando_net = rando_after - rando_before
    nour_after =  inv.balanceOf(nour) / 1e18

    # inv.balanceOf(bribev2)



def spell():

    # TIMESTAMPS
    # 1649289600 = April 7 00:00 UTC

    # BLOCKS
    # 14536480 = First block after April 7 00:00 UTC
    spell = Contract("0x090185f2135308BaD17527004364eBcC2D37e5F6")
    spell_whale = accounts.at("0x2eE555C9006A9DC4674f01E0d4Dfc58e013708f0", force=True)
    spell_gauge = "0xd8b712d29381748dB89c36BCa0138d7c75866ddF" 
    voter = accounts.at("0xF147b8125d2ef93FB6965Db97D6746952a133934", force=True)
    bribev2 = Contract("0x7893bbb46613d7a4FbcC31Dab4C9b823FfeE1026")
    gc = Contract("0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB")


    spell.approve(bribev2, 2**256-1, {'from': spell_whale})
    chain.snapshot()

    # CLAIM FIRST
    print("--- TRYING WITH CLAIM FIRST ---")
    bribev2.claim_reward(spell_gauge,spell,{'from':voter})
    print("SPELL CLAIMED", spell.balanceOf(voter)/1e18)

    chain.revert()

    # ADD FIRST
    print("\n--- RETRYING WITH ADD FIRST ---")
    bribev2.claim_reward(spell_gauge,spell,{'from':spell_whale})
    bribev2.add_reward_amount(spell_gauge, spell, 50_000_000e18, {'from': spell_whale})
    bribev2.claim_reward(spell_gauge,spell,{'from':voter})
    print("SPELL CLAIMED", spell.balanceOf(voter)/1e18)
