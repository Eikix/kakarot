import random

import pytest
import pytest_asyncio
from eth_account.account import Account
from starkware.starknet.testing.starknet import Starknet

from scripts.utils.starknet import int_to_uint256
from tests.utils.constants import TRANSACTIONS
from tests.utils.errors import cairo_error
from tests.utils.helpers import (
    generate_random_evm_address,
    generate_random_private_key,
    rlp_encode_tx,
)


@pytest_asyncio.fixture(scope="module")
async def eth_transaction(starknet: Starknet):
    class_hash = await starknet.deprecated_declare(
        source="./tests/src/utils/test_eth_transaction.cairo",
        cairo_path=["src"],
        disable_hint_validation=True,
    )
    return await starknet.deploy(class_hash=class_hash.class_hash)


@pytest.mark.asyncio
class TestEthTransaction:
    class TestValidate:
        @pytest.mark.parametrize("seed", (41, 42))
        @pytest.mark.parametrize("transaction", TRANSACTIONS)
        async def test_should_pass_all_transactions_types(
            self, eth_transaction, seed, transaction
        ):
            """
            Note: the seeds 41 and 42 have been manually selected after observing that some private keys
            were making the Counter deploy transaction failing because their signature parameters length (s and v)
            were not 32 bytes.
            """
            random.seed(seed)
            private_key = generate_random_private_key()
            address = private_key.public_key.to_checksum_address()
            signed = Account.sign_transaction(transaction, private_key)

            encoded_unsigned_tx = rlp_encode_tx(transaction)

            await eth_transaction.test__validate(
                int(address, 16),
                transaction["nonce"],
                (int_to_uint256(signed.r)["low"], int_to_uint256(signed.r)["high"]),
                (int_to_uint256(signed.s)["low"], int_to_uint256(signed.s)["high"]),
                signed["v"],
                list(encoded_unsigned_tx),
            ).call()

        @pytest.mark.parametrize("transaction", TRANSACTIONS)
        async def test_should_raise_with_wrong_chain_id(
            self, eth_transaction, transaction
        ):
            private_key = generate_random_private_key()
            address = private_key.public_key.to_checksum_address()
            transaction = {**transaction, "chainId": 1}
            signed = Account.sign_transaction(transaction, private_key)

            r = int_to_uint256(signed.r)
            s = int_to_uint256(signed.s)

            encoded_unsigned_tx = rlp_encode_tx(transaction)

            with cairo_error():
                await eth_transaction.test__validate(
                    int(address, 16),
                    transaction["nonce"],
                    (
                        r["low"],
                        r["high"],
                    ),
                    (
                        s["low"],
                        s["high"],
                    ),
                    signed["v"],
                    list(encoded_unsigned_tx),
                ).call()

        @pytest.mark.parametrize("transaction", TRANSACTIONS)
        async def test_should_raise_with_wrong_address(
            self, eth_transaction, transaction
        ):
            private_key = generate_random_private_key()
            address = int(generate_random_evm_address(), 16)
            signed = Account.sign_transaction(transaction, private_key)

            r = int_to_uint256(signed.r)
            s = int_to_uint256(signed.s)

            encoded_unsigned_tx = rlp_encode_tx(transaction)

            assert address != int(private_key.public_key.to_address(), 16)
            with cairo_error():
                await eth_transaction.test__validate(
                    address,
                    transaction["nonce"],
                    (
                        r["low"],
                        r["high"],
                    ),
                    (
                        s["low"],
                        s["high"],
                    ),
                    signed["v"],
                    list(encoded_unsigned_tx),
                ).call()

        @pytest.mark.parametrize("transaction", TRANSACTIONS)
        async def test_should_raise_with_wrong_nonce(
            self, eth_transaction, transaction
        ):
            private_key = generate_random_private_key()
            address = int(generate_random_evm_address(), 16)
            signed = Account.sign_transaction(transaction, private_key)

            r = int_to_uint256(signed.r)
            s = int_to_uint256(signed.s)

            encoded_unsigned_tx = rlp_encode_tx(transaction)

            assert address != int(private_key.public_key.to_address(), 16)
            with cairo_error():
                await eth_transaction.test__validate(
                    address,
                    transaction["nonce"] + 1,
                    (
                        r["low"],
                        r["high"],
                    ),
                    (
                        s["low"],
                        s["high"],
                    ),
                    signed["v"],
                    list(encoded_unsigned_tx),
                ).call()
