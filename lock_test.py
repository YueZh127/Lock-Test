import api
import time


class LockContract(object):
    def __init__(self, web3, addr):
        self.Web3 = web3
        self.address = addr
        self.lock_contract = web3.eth.contract(
            address= addr,
            abi=api.ContractApi.lock_contract_abi
        )

    def create_receipt(self, private_key, target_address, amount):
        try:
            account = self.Web3.eth.account.privateKeyToAccount(private_key)
            self.Web3.eth.defaultAccount = account.address
            lock_tx = self.lock_contract.functions.createReceipt(amount, target_address).buildTransaction(
                {'nonce': self.Web3.eth.getTransactionCount(self.Web3.eth.defaultAccount)})
            lock_tx.update({'gas': 500000})
            lock_tx.update({'gasPrice': 20000000000})
            print("lock_tx: ", lock_tx)
            signed_lock_tx = self.Web3.eth.account.signTransaction(lock_tx, private_key=private_key)
            lock_tx_id = self.Web3.eth.sendRawTransaction(signed_lock_tx.rawTransaction)
            print(" - signed_lock_tx_id: ", self.Web3.toHex(lock_tx_id))
            return self.Web3.toHex(lock_tx_id)

        except Exception as e:
            print("Locking failed", e, private_key)

    def finish(self, private_key, index):
        try:
            account = self.Web3.eth.account.privateKeyToAccount(private_key)
            self.Web3.eth.defaultAccount = account.address
            receipt = self.lock_contract.functions.receipts(index).call()
            time_array = time.strptime(time.time(), "%Y-%m-%d %H:%M:%S")
            timestamp = time.mktime(time_array)
            if timestamp < receipt.endTime:
                print("Can't finish")
                return
            finish_tx = self.lock_contract.functions.finifinishReceipt(index).buildTransaction(
                {'nonce': self.Web3.eth.getTransactionCount(self.Web3.eth.defaultAccount)})
            finish_tx.update({'gas': 500000})
            finish_tx.update({'gasPrice': 20000000000})
            print("finish_tx: ", finish_tx)
            signed_finish_tx = self.Web3.eth.account.signTransaction(finish_tx, private_key=private_key)
            finish_tx_id = self.Web3.eth.sendRawTransaction(signed_finish_tx.rawTransaction)
            print(" - signed_lock_tx_id: ", self.Web3.toHex(finish_tx_id))
            return self.Web3.toHex(finish_tx_id)
        except Exception as e:
            print("Finish failed", e, private_key)

    def get_receipt_info(self, index):
        receipt_info = self.lock_contract.functions.getReceiptInfo(index).call()
        return receipt_info

    def get_user_receipts(self, private_key):
        account = self.Web3.eth.account.privateKeyToAccount(private_key)
        receipts = self.lock_contract.functions.getMyReceipts(account.address).call()
        return receipts

    def get_receipt_count(self):
        return self.lock_contract.functions.receiptCount().call()

    def get_lock_token(self, private_key):
        account = self.Web3.eth.account.privateKeyToAccount(private_key)
        return self.lock_contract.functions.getLockTokens(account.address).call()

    def process_newreceipt_event(self, tx_receipt):
        return self.lock_contract.events.NewReceipt().processReceipt(tx_receipt)[0].args['receiptId']