import api


class TreeContract(object):
    def __init__(self, web3, owner, addr):
        self.Web3 = web3
        self.address = addr
        self.tree_contract = web3.eth.contract(
            address=addr,
            abi=api.ContractApi.tree_contract_abi
        )
        self.owner = owner

    def generate_merkle_tree(self):
        try:
            owner = self.tree_contract.functions.owner().call()
            account = self.Web3.eth.account.privateKeyToAccount(self.owner)
            if owner != account.address:
                print("no permission")
                return
            self.Web3.eth.defaultAccount = account.address
            generated_tree_tx = self.tree_contract.functions.GenerateMerkleTree().buildTransaction(
                {'nonce': self.Web3.eth.getTransactionCount(self.Web3.eth.defaultAccount)})
            generated_tree_tx.update({'gas': 5000000})
            generated_tree_tx.update({'gasPrice': 20000000000})
            print("generate_merkle_tree_tx: ", generated_tree_tx)
            signed_generated_tx = self.Web3.eth.account.signTransaction(generated_tree_tx, private_key=self.owner)
            generated_tree_tx_id = self.Web3.eth.sendRawTransaction(signed_generated_tx.rawTransaction)
            print(" - signed_generated_tx: ", self.Web3.toHex(generated_tree_tx_id))
            return self.Web3.toHex(generated_tree_tx_id)
        except Exception as e:
            print("Merkle tree generation failed", e)

    def get_merkle_tree_path(self, index):
        path_info = self.tree_contract.functions.GenerateMerklePath(receiptId=index).call()
        assert isinstance(path_info, object)
        return path_info

    def receipt_count_in_tree(self):
        return self.tree_contract.functions.ReceiptCountInTree().call()

    def merkle_tree_count(self):
        return self.tree_contract.functions.MerkleTreeCount().call()

    def get_merkle_tree(self, index):
        return self.tree_contract.functions.GetMerkleTree(treeIndex=index).call()


