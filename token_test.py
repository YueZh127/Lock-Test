import api

class TokenContract(object):
    def __init__(self, web3, addr):
        self.Web3 = web3
        self.address = addr
        self.token_contract = web3.eth.contract(
            address=addr,
            abi=api.ContractApi.token_contract_abi
        )

    def approve_token(self, private_key, address):
        account = self.Web3.eth.account.privateKeyToAccount(private_key)
        self.Web3.eth.defaultAccount = account.address
        print(f'approve token for {account.address}.. ')
        approve_tx = self.token_contract.functions.approve(address,
                                                           10000000000000000000000000).buildTransaction(
            {'nonce': self.Web3.eth.getTransactionCount(self.Web3.eth.defaultAccount)})
        # print("approve_tx: ", approve_tx)
        signed_approve_tx = self.Web3.eth.account.signTransaction(approve_tx, private_key=private_key)
        signed_tx_id = self.Web3.eth.sendRawTransaction(signed_approve_tx.rawTransaction)
        print("signed_approve_tx_id: ", self.Web3.toHex(signed_tx_id))
        return self.Web3.toHex(signed_tx_id)

    def get_allowance(self, owner_private_key, address):
        account = self.Web3.eth.account.privateKeyToAccount(owner_private_key)
        return self.token_contract.functions.allowance(account.address, address).call()
