import hashlib
import json
import time

from uuid import uuid4


class Bogchain:
    def __init__(self):
        self.chain = []
        self.current_transactions = []

        self.new_block(proof=100, previous_hash=1)

    def new_block(self, proof, previous_hash=None):
        """
        Create a new block

        :param proof: <int> proof of work
        :param previous_hash: hasj of previous block
        :return: <dict> new block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time.time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }

        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """
        Create a new transaction

        :param sender: <str> Sender address
        :param recipient: <str> Recipient address
        :param amount: <int> Amount
        :return: <int> Index of a block which will hold new transaction:
        """

        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        })

        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        """
        SHA-256 of a block

        :param block: <dict> Block
        :return: <str> sha-256 hash
        """

        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """
        Proof of work algorithm

        :param last_proof: <int> Last proof
        :return: <int> New proof
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Validates if hash of last proof concated with new proof contains 4 trailing zeroes

        :param last_proof: <int> Last proof
        :param proof: <int> New proof
        :return: <bool> True if Valid
        """

        return hashlib.sha256(f'{last_proof}{proof}'.encode()).hexdigest()[-4:] == '0000'
