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
from eth_utils import keccak


REGISTRY_ADDRESS = "0x702ff500f359a185fafbdef2fadad75b04e21a814abc5e6257e2e65ceffdf15"
KAKAROT_ADDRESS = "0xb5644ba96891f73151973d76f914ee6eea75479a1fe5fbe0098afa50027385"
COUNTER_STARKNET_ADDRESS = "0x62897A9E931BA1AE4721548BD963E3FE67126E0755AF0FF0173F919738F8373"
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

with open(Path(BUILD_PATH, "account_registry_abi.json")) as registry_file:
    registry_abi = json.load(registry_file)

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
    registry_contract = Contract(
        address=REGISTRY_ADDRESS, abi=registry_abi, client=client)
    call_registry = (await registry_contract.functions["get_evm_contract_address"].call(int(COUNTER_STARKNET_ADDRESS, 16)))
    counter_evm_address_from_registry = hex(getattr(
        call_registry, "evm_contract_address"))
    logging.info(counter_evm_address_from_registry)
    logging.info("Entering Execution of Counter Contract Increment")
    kakarot_contract = Contract(
        address=KAKAROT_ADDRESS, abi=kakarot_abi, client=client)
    logging.info("Kakarot contract loaded into memory. Invoking deploy...")
    selector = hex(int.from_bytes(keccak(text="inc()"),
                                  byteorder="little", signed=False))[:6]
    logging.info(selector)
    # count_selector = hex(int.from_bytes(
    # keccak(text="count()"), byteorder = "big", signed = False))[:6]
    # call = await kakarot_contract.functions["execute_at_address"].call(address=int(COUNTER_ADDRESS, 16), calldata=hex_string_to_bytes_array(count_selector), value=0, gas_limit=1_000_000_000)
    invocation = await kakarot_contract.functions["execute_at_address"].invoke(address=int(counter_evm_address_from_registry, 16), calldata=hex_string_to_bytes_array(selector), value=0, gas_limit=int(1e16), max_fee=MAX_FEE)
    logging.info(
        "Invoked execute_at_address entrypoint of Kakarot. Waiting for acceptance...")
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
