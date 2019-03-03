import json
import hashlib
import asyncio
import threading
import traceback

from time import time

from coin.peers import Peers


class Bogchain:
    difficulty = 4
    mining_bounty = 2

    def __init__(self, **kwargs):
        self.node_id = kwargs['node_id']
        self.gossip = kwargs['gossip']
        self.chain = []
        self.awaiting_transactions = []
        self.new_block_transactions = []
        self.wake_transaction_handler = threading.Event()
        self.mining_task = None
        self.peers = Peers()
        self.logger = kwargs['logger']

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

    @staticmethod
    def create_transaction(sender, recipient, amount):
        return {
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        }

    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    @property
    def current_state(self):
        return {
            'chain': self.chain,
            'peers': self.peers.addresses_pub_keys
                }

    def proof_of_work(self, last_proof):
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        return hashlib.sha256(f'{last_proof}{proof}'.encode()).hexdigest()[-Bogchain.difficulty:] == Bogchain.difficulty * '0'

    def valid_chain(self, chain):
        if len(chain) == 1:
            return True

        for i in range(1, len(chain)):
            block = chain[i]
            prev_block = chain[i - 1]

            if block['previous_hash'] != self.hash(prev_block):
                return False

            if self.valid_proof(prev_block['proof'], block['proof']) is False:
                return False

        return True

    async def handle_transactions(self, accumulation_period):
        while True:
            self.wake_transaction_handler.wait()
            print(f"Waiting {self.awaiting_transactions}")
            print(f"Block {self.new_block_transactions}")
            self.logger.info(f"New transactions sleep ends")

            await asyncio.sleep(accumulation_period)
            self.wake_transaction_handler.clear()

            self.new_block_transactions = self.awaiting_transactions[:]
            self.awaiting_transactions = []
            self.mining_task = asyncio.create_task(self.mine())

            try:
                proof = await self.mining_task
                self.new_block_transactions.append(
                    Bogchain.create_transaction("mint", self.node_id, Bogchain.mining_bounty)
                )
                self.new_block(proof)
                self.gossip.flood('/update', self.current_state, self.peers.addresses)
                self.logger.info(f"Mined new block, chain length {len(self.chain)}")

            except asyncio.CancelledError:
                self.mining_task = None
                self.logger.info(f"Mining cancelled")



    async def mine(self):
        throttled = True if 'throttle' in dir(self) else False

        if throttled:
            await asyncio.sleep(self.throttle)

        last_proof = self.last_block['proof']
        return self.proof_of_work(last_proof)

    def update_chain(self, new_chain):
        replaced = False

        if not self.valid_chain(new_chain):
            self.logger.info("Invalid received chain")
            return replaced

        elif len(self.chain) == len(new_chain):
            if new_chain[-1]['timestamp'] < self.chain[-1]['timestamp']:
                self.logger.info("Choosing older chain")
                replaced = True

        elif len(new_chain) > len(self.chain):
            self.logger.info("Choosing longer chain")
            replaced = True

        if replaced:
            self.chain = new_chain

        return replaced

    def update_peers(self, received_peers):
        new_peers = []

        for key, value in received_peers.items():
            if key not in [*self.peers.addresses_pub_keys.keys(), self.node_id]:
                self.peers.add_peer(value['address'], key, value['pub_key'])
                new_peers.append(value['address'])

        new_peers_number = len(new_peers)

        if new_peers_number != 0:
            self.logger.info(f"Updated peers, number of new peers {len(new_peers)}")

        return new_peers
