import requests
import json
import hashlib

from time import time
from urllib.parse import urlparse

from coin.peers import Peers


class Bogchain:
    difficulty = 4

    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.peers = Peers()

    def new_block(self, proof, previous_hash=None):
        block = {
            'index': len(self.chain),
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }

        self.current_transactions = []

        self.chain.append(block)
        return block

    def create_genesis_block(self, node_id):
        genesis_proof = self.proof_of_work(100)

        self.new_transaction("mint", node_id, 200, genesis=True)
        self.new_block(genesis_proof, 1)

    def new_transaction(self, sender, recipient, amount, genesis=False):
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        })

        return self.last_block['index'] + 1 if genesis is False else 0

    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        return hashlib.sha256(f'{last_proof}{proof}'.encode()).hexdigest()[-4:] == Bogchain.difficulty * '0'

    def valid_chain(self, chain):

        for i in range(1, len(chain) + 1):
            block = chain[i]
            prev_block = chain[i - 1]

            if block['previous_hash'] != self.hash(prev_block):
                return False

            if self.valid_proof(prev_block['proof'], block['proof']) is False:
                return False

        return True

    async def mine(self):
        pass  # todo kopanie nowych transakcji

    async def receive_transaction(self):
        pass  # todo obsługa nowej transakcji


"""    def resolve_conflicts(self):
        longest_chain = self.chain
        replaced = False

        for node in self.peers.addresses_keys.values()[0]:
            r = requests.get(node + '/chain')

            if r.status_code == 200:
                chain = r.json()['chain']
                length = r.json()['length']
                if length > len(longest_chain) and self.valid_chain(chain):
                    longest_chain = chain
                    replaced = True

        if replaced:
            self.chain = longest_chain

        return replaced """
