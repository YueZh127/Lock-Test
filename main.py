import json
from web3.exceptions import TransactionNotFound
from logger import logger
from web3 import Web3
from lock_test import LockContract
from tree_test import TreeContract
from token_test import TokenContract

import time
import random
import argparse


def get_receipt(web3, tx_id):
    try:
        return web3.eth.getTransactionReceipt(tx_id)
    except TransactionNotFound:
        logger.warning(f"Transaction not found: {tx_id}")
        return get_receipt(web3, tx_id)


def get_transaction(web3, tx_id):
    try:
        return web3.eth.getTransaction(tx_id)
    except Exception as e:
        logger.error(e)
        return None

def wait_receipt(web3, tx_id):
    try:
        return web3.eth.waitForTransactionReceipt(tx_id, timeout=120)
    except Exception as e:
        time.sleep(60)
        logger.error(e)
        wait_receipt(web3, tx_id)


def create_receipts():
    receipt_tx_id_pending_list = [""] * len(private_keys)
    approve_tx_id_pending_list = [""] * len(private_keys)
    tx_receipt_list = []
    j = 0
    while True:
        private_key_index = j % min(i, len(private_keys))
        j += 1
        private_key = private_keys[private_key_index]

        if approve_tx_id_pending_list[private_key_index] != "":
            result = get_transaction(w3, approve_tx_id_pending_list[private_key_index])
            if result is not None and result.blockNumber is None: # if tx found but pending
                # slow down request
                time.sleep(10)
                continue
            approve_tx_id_pending_list[private_key_index] = ""

        # check allowance
        allowance = token.get_allowance(private_key, lock.address)
        if allowance < minimum_allowance:
            approve_id = token.approve_token(private_key, lock.address, maximum_allowance)
            approve_tx_id_pending_list[private_key_index] = approve_id
            continue

        if receipt_tx_id_pending_list[private_key_index] != "":  # if already exists
            result = get_transaction(w3, receipt_tx_id_pending_list[private_key_index])
            if result is not None and result.blockNumber is None: # if tx not found but pending
                # slow down request
                time.sleep(10)
                continue

            # it is tx to create script
            tx_receipt = get_receipt(w3, receipt_tx_id_pending_list[private_key_index])
            receipt_id = lock.process_newreceipt_event(tx_receipt)
            tx_receipt_list.append(receipt_id)
            receipt_tx_id_pending_list[private_key_index] = ""  # reset

            if len(tx_receipt_list) == i:
                break

        # count lock tx
        pending_count = sum(1 for id in receipt_tx_id_pending_list if id is not "")
        if pending_count + len(tx_receipt_list) >= i:
            continue

        balance = token.get_balance(private_key)
        if balance < 0:
            continue

        amount = random.randint(minimum_allowance, min(allowance, maximal_lock_amount, balance))
        logger.info(f'Attempt lock {amount}')
        receipt_tx_id = lock.create_receipt(private_key,
                                            target_addresses[j % len(target_addresses)], amount)
        if receipt_tx_id is not None:
            receipt_tx_id_pending_list[private_key_index] = receipt_tx_id

    tree_generation_tx_id = None
    while tree_generation_tx_id is None:
        tree_generation_tx_id = tree.generate_merkle_tree()

    wait_receipt(w3, tree_generation_tx_id)
    after_tree_count = tree.merkle_tree_count()

    # get tree info
    tree_index = after_tree_count - 1
    merkle_info = tree.get_merkle_tree(tree_index)
    merkle_root = w3.toHex(merkle_info[0])
    merkle_first_receipt = merkle_info[1]
    merkle_receipt_counts = merkle_info[2]
    # get receipt info
    receipt_array = []

    for receipt_id in sorted(tx_receipt_list):
        # receipt_id = lock.process_newreceipt_event(tx_receipt)
        receipt_info = lock.get_receipt_info(receipt_id)
        amount = receipt_info[2]
        owner = lock.get_receipt(receipt_id)[1]
        logger.info(f"Get receipt {receipt_id}, owner: {owner}, amount: {amount}")

        merkle_path_data = tree.get_merkle_tree_path(receipt_id)

        merkle_path = {
            "path_length": merkle_path_data[1],
            "nodes": [w3.toHex(node) for node in merkle_path_data[2]][0:merkle_path_data[1]],
            "positions": [is_left for is_left in merkle_path_data[3]][0:merkle_path_data[1]]
        }

        receipt_data = {
            "receipt_id": receipt_id,
            "uid": w3.toHex(receipt_info[0]),
            "targetAddress": receipt_info[1],
            "amount": amount,
            "isFinished": receipt_info[3],
            "merkle_path": merkle_path
        }
        receipt_array.append(receipt_data)

    info = {"merkle_root": merkle_root, "tree_index": tree_index,
            "receipt_counts": merkle_receipt_counts, "receipts": receipt_array}
    # write to file
    with open(f"{output_path}/{i}" + ".json", "w+") as f:
        f.write(json.dumps(info))


def reclaim(finish_index, count):
    receipt_count = lock.get_receipt_count()
    finished_count = 0
    to_be_finished = {}
    finish_tx_id_pending = {}
    start_index = finish_index
    end_index = start_index
    for receipt_id in range(finish_index, receipt_count):
        end_index = receipt_id
        receipt_info = lock.get_receipt(receipt_id)
        receipt_end_time = receipt_info[5]
        is_finished = receipt_info[6]
        time_array = time.time()
        timestamp = int(time_array)
        if is_finished is True:
            continue
        if timestamp < receipt_end_time:
            continue

        to_be_finished[receipt_id] = receipt_info
        if len(to_be_finished) == count:
            break

    if len(to_be_finished) is 0:
        return end_index

    t = 0
    while True:
        index = t % len(to_be_finished)
        t += 1
        receipt_id = list(to_be_finished.keys())[index]
        if to_be_finished.get(receipt_id) is None:
            continue

        receipt_info = to_be_finished[receipt_id]
        owner = receipt_info[1]

        if finish_tx_id_pending.get(owner) is not None:
            result = get_transaction(w3, finish_tx_id_pending[owner]['tx_id'])
            if result is not None and result.blockNumber is None: # if tx found but pending
                # slow down request
                time.sleep(10)
                continue
            finish_tx_id = finish_tx_id_pending[owner]['tx_id']
            finished_receipt_id = finish_tx_id_pending[owner]['receipt_id']
            finish_tx_id_pending.pop(owner)
            tx_receipt = get_receipt(w3, finish_tx_id)
            event_amount = token.process_finish_transfer_event(tx_receipt)
            finished_receipt_info = lock.get_receipt(finished_receipt_id)
            is_finished = finished_receipt_info[6]

            after_balance = token.get_balance(address_to_private_key[owner])
            after_lock_token = lock.get_lock_token(address_to_private_key[owner])

            origin_balance = token.get_balance(address_to_private_key[owner], result.blockNumber - 1)
            origin_lock_token = lock.get_lock_token(address_to_private_key[owner], result.blockNumber - 1)

            reclaimed_amount = finished_receipt_info[3]
            if is_finished is True and reclaimed_amount == event_amount and after_balance == origin_balance + reclaimed_amount and after_lock_token == origin_lock_token - reclaimed_amount:
                logger.info(f"Finish succeed. receipt id: {finished_receipt_id}, Amount: {reclaimed_amount}, Owner: {owner})")
                finished_count += 1
                to_be_finished.pop(finished_receipt_id)
                if finished_count == count:
                    return end_index
            else:
                logger.info(f"Finish failed. receipt id: {finished_receipt_id}, Owner: {owner}, Amount: {reclaimed_amount},"
                      f"Event amount: {event_amount}, balance: {origin_balance}, {after_balance}, lock token: {origin_lock_token}, {after_lock_token})")
                raise Exception("Failed reclaim.")

        # attempt reclaim

        already_finished = lock.get_receipt(receipt_id)[6]
        if already_finished is True:
            continue

        finish_tx_id = lock.finish(address_to_private_key[owner], receipt_id)
        if finish_tx_id is not None:
            finish_tx_id_pending[owner] = {'tx_id': finish_tx_id, 'receipt_id': receipt_id}


if __name__ == '__main__':

    with open('vars.json', ) as f:
        vars = json.load(f)
        output_path = vars['output_path']
        receipt_count_minimal = vars['start_receipt_count']
        receipt_count_maximal = vars['end_receipt_count']
        private_keys = vars['private_keys']
        target_addresses = vars['target_addresses']
        owner_key = vars['owner_key']
        minimum_allowance = vars['minimum_allowance']
        maximum_allowance = vars['maximum_allowance']
        maximal_lock_amount = vars['maximal_lock_amount']

        token_contract_address = vars['token_contract']
        merkletree_contract_address = vars['merkletree_contract']
        lock_contract = vars['lock_contract']

        gas_price = vars['gas_price']
        http_provider = vars['http_provider']
        next_finish_index = vars['finish_start_index']

        new_receipt = vars['new_receipt']
        finish_receipt = vars['finish_receipt']

    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int)
    parser.add_argument("--end", type=int)
    args = parser.parse_args()

    if args.start is not None:
        receipt_count_minimal = args.start

    if args.end is not None:
        receipt_count_maximal = args.end

    if output_path == "" or receipt_count_maximal == 0 or receipt_count_minimal == 0:
        raise Exception("Exit with invalid options.")

    logger.info(f"receipt_count_minimal : {receipt_count_minimal}")
    logger.info(f"receipt_count_maximal : {receipt_count_maximal}")

    w3 = Web3(Web3.HTTPProvider(http_provider))
    lock = LockContract(w3, lock_contract, gas_price)
    tree = TreeContract(w3, owner_key, merkletree_contract_address, gas_price)
    token = TokenContract(w3, token_contract_address, gas_price)

    address_to_private_key = {}
    for private_key in private_keys:
        account = w3.eth.account.privateKeyToAccount(private_key).address
        address_to_private_key[account] = private_key

    receipt_count_in_tree = tree.receipt_count_in_tree()
    receipt_count_for_lock = lock.get_receipt_count()

    logger.info(f"receipt_count_in_tree : {receipt_count_in_tree}")
    logger.info(f"receipt_count_for_lock : {receipt_count_for_lock}")

    if receipt_count_in_tree < receipt_count_for_lock:
        tree_generation_tx_id = tree.generate_merkle_tree()
        wait_receipt(w3, tree_generation_tx_id)

    for i in range(receipt_count_minimal, receipt_count_maximal + 1):
        if new_receipt:
            logger.info(f"Tree : {i}")
            create_receipts()
        if finish_receipt:
            next_finish_index = reclaim(next_finish_index, i) + 1
