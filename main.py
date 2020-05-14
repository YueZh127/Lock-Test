import json

from web3 import Web3
from lock_test import LockContract
from tree_test import TreeContract
from token_test import TokenContract

import time
import random
import argparse

def get_receipt(web3, tx_id):
    return web3.eth.getTransactionReceipt(tx_id)


def get_transaction(web3, tx_id):
    return web3.eth.getTransaction(tx_id)


def wait_receipt(web3, tx_id):
    try:
        return web3.eth.waitForTransactionReceipt(tx_id, timeout=120)
    except Exception as e:
        time.sleep(60)
        print(e)
        wait_receipt(web3, tx_id)

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

        random_lock_amount = vars['random_lock_amount']
        maximal_lock_amount = vars['maximal_lock_amount']

        token_contract_address = vars['token_contract']
        merkletree_contract_address = vars['merkletree_contract']
        lock_contract = vars['lock_contract']

        gas_price = vars['gas_price']

        http_provider = vars['http_provider']

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

    print(f"receipt_count_minimal : {receipt_count_minimal}")
    print(f"receipt_count_maximal : {receipt_count_maximal}")

    # w3 = Web3(Web3.HTTPProvider("https://ropsten.infura.io/v3/cc8d19ee21984baeafffa1713b390016"))
    w3 = Web3(Web3.HTTPProvider(http_provider))
    lock = LockContract(w3, lock_contract, gas_price)
    tree = TreeContract(w3, owner_key, merkletree_contract_address, gas_price)
    token = TokenContract(w3, token_contract_address, gas_price)

    receipt_count_in_tree = tree.receipt_count_in_tree()
    receipt_count_for_lock = lock.get_receipt_count()

    print(f"receipt_count_in_tree : {receipt_count_in_tree}")
    print(f"receipt_count_for_lock : {receipt_count_for_lock}")

    if receipt_count_in_tree < receipt_count_for_lock:
        tree_generation_tx_id = tree.generate_merkle_tree()
        wait_receipt(w3, tree_generation_tx_id)

    for i in range(receipt_count_minimal, receipt_count_maximal + 1):
        print("Tree :", i, "receipt count:", i)
        origin = lock.get_receipt_count()

        # receipt_created_count = 0
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
                if result.blockNumber is None:  # if pending
                    # slow down request
                    time.sleep(10)
                    continue
                else:
                    approve_tx_id_pending_list[private_key_index] = ""

            # check allowance
            allowance = token.get_allowance(private_key, lock.address)
            if allowance < minimum_allowance:
                approve_id = token.approve_token(private_key, lock.address, maximum_allowance)
                approve_tx_id_pending_list[private_key_index] = approve_id
                continue

            if receipt_tx_id_pending_list[private_key_index] != "":  # if already exists
                result = get_transaction(w3, receipt_tx_id_pending_list[private_key_index])
                if result.blockNumber is None:  # if pending
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
            amount = random.randint(minimum_allowance, min(maximal_lock_amount, balance))
            receipt_tx_id = lock.create_receipt(private_key,
                                                target_addresses[j % len(target_addresses)], amount)
            if receipt_tx_id is not None:
                receipt_tx_id_pending_list[private_key_index] = receipt_tx_id

        origin_tree_count = tree.merkle_tree_count()
        tree_generation_tx_id = tree.generate_merkle_tree()
        # result = w3.eth.getTransaction(tree_tx_id)
        # while result.blockNumber is None:
        #     time.sleep(10)
        #     result = w3.eth.getTransaction(tree_tx_id)
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
            print(f"Get receipt {receipt_id}")
            receipt_info = lock.get_receipt_info(receipt_id)
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
                "amount": receipt_info[2],
                "isFinished": receipt_info[3],
                "merkle_path": merkle_path
            }
            receipt_array.append(receipt_data)

        info = {"merkle_root": merkle_root, "tree_index": tree_index,
                "receipt_counts": merkle_receipt_counts, "receipts": receipt_array}
        # write to file
        with open(f"{output_path}/{i}" + ".json", "w+") as f:
            f.write(json.dumps(info))
