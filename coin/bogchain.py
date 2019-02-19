import requests
import json
import hashlib
import asyncio
import threading

from time import time, sleep

from coin.peers import Peers


class Bogchain:
    difficulty = 4

    def __init__(self, logger):
        self.chain = []
        self.awaiting_transactions = []
        self.new_block_transactions = []
        self.wake_transaction_handler = threading.Event()
        self.mining_task = None
        self.peers = Peers()
        self.logger = logger

    def new_block(self, proof, previous_hash=None):
        block = {
            'index': len(self.chain),
            'timestamp': time(),
            'transactions': self.new_block_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }

        self.new_block_transactions = []

        self.chain.append(block)
        return block

    def create_genesis_block(self, node_id):
        genesis_proof = self.proof_of_work(100)

        self.new_block_transactions.append({'sender': "mint",
                                            'recipient': node_id,
                                            'amount': 200})
        self.new_block(genesis_proof, 1)

    def new_transaction(self, sender, recipient, amount):
        self.awaiting_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        })

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

    async def handle_transactions(self, accumulation_period):
        while True:
            if len(self.awaiting_transactions) == 0:
                self.logger.info(f"No transcations pending beginning sleep")
                self.wake_transaction_handler.wait()
                self.logger.info(f"New transactions sleep ends")
                await asyncio.sleep(accumulation_period)  # todo sensownie czas oczekiwania
            else:
                self.new_block_transactions = self.awaiting_transactions[:]
                self.awaiting_transactions = []
                self.mining_task = asyncio.create_task(self.mine())
                try:
                    proof = await self.mining_task
                    self.new_block(proof)
                    self.awaiting_transactions.clear()
                    self.logger.info(f"Mined new block, chain length {len(self.chain)}")
                    #  todo rozgłoszenie
                except asyncio.CancelledError:
                    self.logger.info(f"Mining cancelled")
                    pass

                await asyncio.sleep(accumulation_period)  # todo sensownie czas oczekiwania

            self.wake_transaction_handler.clear()

    async def mine(self):
        last_proof = self.last_block['proof']
        return self.proof_of_work(last_proof)

    def update_chain(self, new_chain):
        replaced = False

        if self.valid_chain(new_chain) and len(new_chain) > len(self.chain):
            self.chain = new_chain
            replaced = True

        return replaced

    def update_peers(self, new_peers):
        for new_peer in new_peers.keys():
            if new_peer.key not in self.peers.addresses_pub_keys.keys():
                self.peers.add_peer(new_peer['address'], new_peer['node_id'], new_peer['pub_key'])
