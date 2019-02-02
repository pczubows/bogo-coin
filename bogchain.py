import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4
from sys import argv

import requests
from flask import Flask, jsonify, request


class Bogchain:
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

        self.new_block(proof=100, previous_hash=1)

    def new_block(self, proof, previous_hash=None):
        """
        Create a new block

        :param proof: <int> proof of work
        :param previous_hash: hash of previous block
        :return: <dict> new block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
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

    def register_node(self, address):
        """
        add new node to the set of nodes
        :param address: <str> node url
        :return: None
        """
        self.nodes.add(urlparse(address))

    def valid_chain(self, chain):
        """
        check if passed chain is valid
        :param chain: <list> chain
        :return: <bool> True if valid
        """

        for i in range(1, len(chain) + 1):
            block = chain[i]
            prev_block = chain[i - 1]

            if block['previous_hash'] != self.hash(prev_block):
                return False

            if self.valid_proof(prev_block['proof'], block['proof']) is False:
                return False

        return True

    def resolve_conflicts(self):
        """
        Replace chain with longest one in network in case of conflict

        :return: <bool> True if replaced
        """
        longest_chain = self.chain
        replaced = False

        for node in self.nodes:
            r = requests.get(node + '/chain')

            if r.status_code == 200:
                chain = r.json()['chain']
                length = r.json()['length']
                if length > len(longest_chain) and self.valid_chain(chain):
                    longest_chain = chain
                    replaced = True

        if replaced:
            self.chain = longest_chain

        return replaced


app = Flask(__name__)

node_id = str(uuid4()).replace('-', '')

bogchain = Bogchain()


@app.route('/mine', methods=['GET'])
def mine():
    last_proof = bogchain.last_block['proof']
    proof = bogchain.proof_of_work(last_proof)
    block = bogchain.new_block(proof)

    bogchain.new_transaction(sender="0", recipient=node_id, amount=1)

    response = {
        'message': 'New block forged',
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }

    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    trans = request.get_json()

    required = ['sender', 'recipient', 'amount']
    if not all(key in trans for key in required):
        return "Missing required values", 400

    index = bogchain.new_transaction(sender=trans['sender'],
                             recipient=trans['recipient'],
                             amount=trans['amount'])

    response = f'Transaction will be added to block with index: {index}'

    return response, 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': bogchain.chain,
        'length': len(bogchain.chain)
    }

    return jsonify(response), 200


@app.route('/nodes', methods=['GET'])
def nodes():
    return jsonify(bogchain.nodes)


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    new_nodes = request.get_json()['nodes']

    if new_nodes is None:
        return "No nodes provided", 400

    for node in new_nodes:
        bogchain.register_node(node)

    response = {
        'message': 'Nodes added',
        'new_nodes': new_nodes
    }

    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def nodes_resolve():
    replaced = bogchain.resolve_conflicts()

    if replaced:
        response = {
            "message": "Chain replaced",
            "new_chain": bogchain.chain
        }
    else:
        response = {
            "message": "Our chain is valid"
        }

    return jsonify(response), 200


@app.route('/balance', methods=['GET'])
def balance():
    bogs = 0

    for block in bogchain.chain:
        for transaction in block['transactions']:
            if transaction['sender'] == node_id:
                bogs -= transaction['amount']
            elif transaction['recipient'] == node_id:
                bogs += transaction['amount']

    return jsonify({'balance': bogs}), 200


@app.route('/node_id', methods=['GET'])
def get_node_id():
    return jsonify({"node_id": node_id}), 200


if __name__ == '__main__':
    port = 5000 if len(argv) <= 1 else argv[1]
    app.run(host='0.0.0.0', port=port)



















