import api


class TokenContract(object):
    def __init__(self, web3, addr, price):
        self.Web3 = web3
        self.address = addr
        self.gas_price = price
        self.token_contract = web3.eth.contract(
            address=addr,
            abi=api.ContractApi.token_contract_abi
        )

    def approve_token(self, private_key, address, allowance):
        account = self.Web3.eth.account.privateKeyToAccount(private_key)
        self.Web3.eth.defaultAccount = account.address
        print(f'approve token for {account.address}.. ')
        approve_tx = self.token_contract.functions.approve(address, allowance).buildTransaction(
            {'nonce': self.Web3.eth.getTransactionCount(self.Web3.eth.defaultAccount)})
        approve_tx.update({'gas': 500000})
        approve_tx.update({'gasPrice': self.gas_price})
        # print("approve_tx: ", approve_tx)
        signed_approve_tx = self.Web3.eth.account.signTransaction(approve_tx, private_key=private_key)
        signed_tx_id = self.Web3.eth.sendRawTransaction(signed_approve_tx.rawTransaction)
        print("signed_approve_tx_id: ", self.Web3.toHex(signed_tx_id))
        return self.Web3.toHex(signed_tx_id)

    def get_allowance(self, owner_private_key, address):
        account = self.Web3.eth.account.privateKeyToAccount(owner_private_key)
        return self.token_contract.functions.allowance(account.address, address).call()

    def get_balance(self, owner_private_key):
        account = self.Web3.eth.account.privateKeyToAccount(owner_private_key)
        return self.token_contract.functions.balanceOf(account.address).call()

    def process_finish_transfer_event(self, tx_receipt):
        event = self.token_contract.events.Transfer()
        logs = event.processReceipt(tx_receipt)
        amount = logs[0].args['value']
        return amount
