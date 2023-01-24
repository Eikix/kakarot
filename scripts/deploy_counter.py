from dotenv import load_dotenv
import logging
import os
import json
from asyncio import run
from starknet_py.net.account.account_client import (AccountClient)
from starknet_py.net.signer.stark_curve_signer import KeyPair
from starknet_py.contract import Contract
from starknet_py.net.models import StarknetChainId
from starkware.crypto.signature.signature import private_to_stark_key
from starknet_py.net.gateway_client import GatewayClient
from pathlib import Path
from textwrap import wrap


COUNTER_BYTECODE = "0x608060405234801561001057600080fd5b506000805561023c806100246000396000f3fe608060405234801561001057600080fd5b50600436106100625760003560e01c806306661abd14610067578063371303c0146100825780637c507cbd1461008c578063b3bcfa8214610094578063d826f88f1461009c578063f0707ea9146100a5575b600080fd5b61007060005481565b60405190815260200160405180910390f35b61008a6100ad565b005b61008a6100c6565b61008a610106565b61008a60008055565b61008a610139565b60016000808282546100bf919061017c565b9091555050565b60008054116100f05760405162461bcd60e51b81526004016100e790610195565b60405180910390fd5b6000805490806100ff836101dc565b9190505550565b60008054116101275760405162461bcd60e51b81526004016100e790610195565b60016000808282546100bf91906101f3565b600080541161015a5760405162461bcd60e51b81526004016100e790610195565b60008054600019019055565b634e487b7160e01b600052601160045260246000fd5b8082018082111561018f5761018f610166565b92915050565b60208082526027908201527f636f756e742073686f756c64206265207374726963746c7920677265617465726040820152660207468616e20360cc1b606082015260800190565b6000816101eb576101eb610166565b506000190190565b8181038181111561018f5761018f61016656fea26469706673582212204679f681439140678d2a15a38b396bd4199590bc59fea21924b198e890e5c2dc64736f6c63430008110033"
KAKAROT_ADDRESS = "0xb5644ba96891f73151973d76f914ee6eea75479a1fe5fbe0098afa50027385"
# Address of the ETH token on mainnet,testnet1 and testnet2
ETH_ADDRESS = 2087021424722619777119509474943472645767659996348769578120564519014510906823
# Set a high max fee for the deployments
MAX_FEE = int(1e16)
BUILD_PATH = Path("build")

# Load compiled contracts
KAKAROT_COMPILED = Path(BUILD_PATH, "kakarot.json").read_text("utf-8")
# Get Kakarot ABI
with open(Path(BUILD_PATH, 'kakarot_abi.json')) as abi_file:
    kakarot_abi = json.load(abi_file)

# Loading .env file
load_dotenv()
logging.basicConfig(level=logging.INFO)

# Get env variables
private_key = int(os.environ.get("PRIVATE_KEY"))
account_address = int(os.environ.get("ACCOUNT_ADDRESS"), 16)
network = os.getenv('NETWORK')

# Current starknet.py version does not support testnet2 as a default network
if network == "testnet2":
    network = "https://alpha4-2.starknet.io"
elif network == "testnet":
    network = "https://alpha4.starknet.io"

# Configure Admin AccountClient
public_key = private_to_stark_key(private_key)
signer_key_pair = KeyPair(private_key, public_key)
client = AccountClient(address=account_address, client=GatewayClient(
    net=network), key_pair=signer_key_pair, chain=StarknetChainId.TESTNET, supported_tx_version=1)


async def main():
    logging.info("Entering Execution of Counter Contract deployment")
    kakarot_contract = Contract(
        address=KAKAROT_ADDRESS, abi=kakarot_abi, client=client)
    logging.info("Kakarot contract loaded into memory. Invoking deploy...")
    invocation = await kakarot_contract.functions["deploy"].invoke(hex_string_to_bytes_array(COUNTER_BYTECODE), max_fee=MAX_FEE)
    logging.info(
        "Invoked deploy entrypoint of Kakarot. Waiting for acceptance...")
    await invocation.wait_for_acceptance()
    receipt = await client.get_transaction_receipt(invocation.hash)
    logging.info(receipt)
    logging.info("Accepted on L2")
    logging.info(invocation)
    logging.info(invocation.invoke_transaction)
    logging.info(invocation.hash)


def hex_string_to_bytes_array(h: str):
    if len(h) % 2 != 0:
        raise ValueError(f"Provided string has an odd length {len(h)}")
    if h[:2] == "0x":
        h = h[2:]
    return [int(b, 16) for b in wrap(h, 2)]


if __name__ == "__main__":
    run(main())
