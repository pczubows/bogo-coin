import json
import hashlib
import asyncio
import threading
import time

from uuid import uuid4

from coin.peers import Peers


class Bogchain:
    """Blockchain along with transaction processing loop

    Attributes:
        node_id (str): unique app id
        gossip (coin.Gossip): object responsible for sending updates to app peers
        chain (list): Blockchain, list of blocks represented as dicts
        peers (coin.Peers): Object containing app peers
        awaiting_transactions (list): list of transaction dicts waiting to be mined into a new block
        new_block_transactions (list): list of transactions that are being mined into a new block
        wake_transaction_handler (threading.Event()): event object responsible for waking transaction loop
            when new transaction was received
        mining_task (asyncio.Task): asyncio task handling mining of a new block
        throttle (float): delay for each iteration inside of mining task, specified only when -T --throttle option
            was used when launching app, used for testing purposes
        logger (Flask.app.logger): flask app logger for debug
        recently_updated (bool): flag preventing from double mining when another node finished mining during
            while this app waits.
        evil (bool): flag True when app is forging blockchain, will prevent app from
            from processing further transactions
        difficulty (int): number of leading zeroes for computing block proof of work
        mining_bounty (int): amount of bogo coins received for completing block
        founder_bounty (int): amount of bogo coins received for founding blockchain

    """

    difficulty = 5
    mining_bounty = 2
    founder_bounty = 200

    def __init__(self, **kwargs):
        """Init bogchain

        Keyword Arguments:
            node_id (str): unique app id
            gossip (coin.Gossip): object responsible for sending updates to app peers
            logger (Flask.app.logger): flask app logger for debug
        """
        self.node_id = kwargs['node_id']
        self.gossip = kwargs['gossip']
        self.chain = []
        self.peers = Peers()
        self.awaiting_transactions = []
        self.new_block_transactions = []
        self.wake_transaction_handler = threading.Event()
        self.mining_task = None
        self.throttle = None
        self.logger = kwargs['logger']
        self.recently_updated = False
        self.evil = False

    def new_block(self, proof, previous_hash=None):
        """create new block dict and append it to the blockchain

        Parameters:
            proof (int): proof of work
            previous_hash (str): hash of a previous block

        Returns:
            dict: new block
        """
        block = {
            'index': len(self.chain),
            'timestamp': time.time(),
            'transactions': self.new_block_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }
        self.new_block_transactions = []

        self.chain.append(block)
        return block

    def create_genesis_block(self):
        """create the first block and transfer set amount of coins to founder

        Returns:
            dict: genesis_block
        """
        self.new_block_transactions.append(Bogchain.create_transaction("mint", self.node_id, Bogchain.founder_bounty))

        return self.new_block(100, "gen")

    @staticmethod
    def create_transaction(sender, recipient, amount):
        """create transaction dict"""
        transaction_dict = {'sender': sender,
                            'recipient': recipient,
                            'amount': amount,
                            'id': str(uuid4())}

        return transaction_dict

    @staticmethod
    def hash(block):
        """calculate hash of a block

        Parameters:
            block (dict)

        Returns:
            str: sha-256 digest of a block
        """
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        """return lst block from blockchain"""
        return self.chain[-1]

    @property
    def current_state(self):
        """get dict containing blockchain and peers"""
        return {
            'chain': self.chain,
            'peers': self.peers.addresses_pub_keys
                }

    def proof_of_work(self, last_proof):
        """calculate proof of work using hashcash like algorithm

        Increase proof value by one in each iteration until resulting
        proof of work is valid

        Parameters:
            last_proof (int): proof of previous block

        Returns:
            int: proof of work
        """
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """Check if proof od work is valid

        Proof of work used is similar to hashcash. Valid if sha-256 of
        last_proof concatenated with new proof has 4 leading zeroes.

        Parameters:
            last_proof (int): previous block proof of work
            proof (int): proof of work to be verified

        Returns:
            bool: True if proof is valid
        """
        return hashlib.sha256(f'{last_proof}{proof}'.encode()).hexdigest()[-Bogchain.difficulty:] == Bogchain.difficulty * '0'

    def valid_chain(self, chain):
        """Check if blockchain is valid

        Iterate over blockchain validating hashes of previous blocks.
        Chains with single block are assumed to be genesis blocks and
        are valid by default.

        Parameters:
            chain (dict): blockchain to be validated

        Returns:
            bool: True if valid chain
        """

        # todo check if genesis block or duplicate genesis block.
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

    def run_transaction_handler(self, accumulation_period):
        """Run transaction handler using asyncio

        Parameters:
            accumulation_period (float): time until transactions will be mined into new block
        """
        asyncio.run(self.handle_transactions(accumulation_period))

    async def handle_transactions(self, accumulation_period):
        """Loop handling incoming transaction

        App waits for a new transaction to process, then begins specified
        wait time until mining begins. Mining will be interrupted if app receives
        blockchain update with longer chain. Otherwise update with new chain will be sent
        to all peers.

        Parameters:
            accumulation_period (float): time until transactions will be mined into new block
        """

        while True:
            if self.evil:
                break

            self.wake_transaction_handler.wait()
            self.logger.info(f"New transactions sleep ends")
            self.recently_updated = False

            await asyncio.sleep(accumulation_period)
            self.wake_transaction_handler.clear()

            self.new_block_transactions = self.awaiting_transactions[:]
            self.awaiting_transactions = []
            self.mining_task = asyncio.create_task(self.mine())

            try:
                if not self.recently_updated:
                    self.logger.info(f"Beginning of mining {len(self.new_block_transactions)} transactions to be mined")
                    proof = await self.mining_task
                    self.new_block_transactions.append(
                        Bogchain.create_transaction("mint", self.node_id, Bogchain.mining_bounty)
                    )
                    self.new_block(proof)
                    self.logger.info(f"Mined new block, chain length {len(self.chain)}")
                    self.gossip.flood('/update', self.current_state, self.peers.addresses)

            except asyncio.CancelledError:
                self.mining_task = None

                received_block_transactions_ids = [transaction['id'] for transaction in self.last_block['transactions']]

                for transaction in self.new_block_transactions:
                    if transaction['id'] not in received_block_transactions_ids:
                        self.awaiting_transactions.append(transaction)
                        self.logger.info("Leftover new transaction back to awaiting transactions")
                        self.wake_transaction_handler.set()
                self.logger.info(f"Mining cancelled")

    async def mine(self):
        """asyncio task performing proof of work calculation"""
        start_time = time.time()
        if self.throttle is not None:
            await asyncio.sleep(self.throttle)

        last_proof = self.last_block['proof']
        proof = self.proof_of_work(last_proof)

        time_elapsed = round((time.time() - start_time) * 1e3)
        self.logger.info(f"Finished mining proof: {proof}, time elapsed: {time_elapsed} ms")
        return proof

    def update_chain(self, new_chain):
        """verify chain received from peer and update

        New chain is accepted if block hashes are valid and its longer
        than current chain. In case two chains are of the same lengths
        the one with older last block is chosen as valid.

        Parameters:
             new_chain (dict): Chain received from peer

        Returns:
            bool: True if chain replaced
        """
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
            self.recently_updated = True

        return replaced

    def update_peers(self, received_peers):
        """Add new peers from peer update

        Parameters:
            received_peers (dict): dict containing peers from update

        Returns:
            list: list of new peers added
        """
        new_peers = []

        for key, value in received_peers.items():
            if key not in [*self.peers.addresses_pub_keys.keys(), self.node_id]:
                self.peers.add_peer(value['address'], key, value['pub_key'])
                new_peers.append(value['address'])

        new_peers_number = len(new_peers)

        if new_peers_number != 0:
            self.logger.info(f"Updated peers, number of new peers {len(new_peers)}")

        return new_peers
