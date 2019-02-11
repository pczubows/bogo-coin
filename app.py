import logging
import json
import asyncio
import threading
import time

import requests

from uuid import uuid4
from flask import Flask, request, jsonify
from argparse import ArgumentParser
from functools import wraps

from coin.bogchain import Bogchain
from coin.pki import Pki
from coin.gossip import Gossip
from coin.test_scheduler import TestScheduler

app = Flask(__name__)

node_id = str(uuid4()).replace('-', '')

bogchain = Bogchain()
gossip = Gossip(bogchain)
pki = Pki()


def check_post_keys(required):
    def decorator(f):
        @wraps(f)
        def decorated_func(*args, **kwargs):
            pending_json = request.get_json()
            if not all(key in pending_json for key in required):
                return "Missing required values", 400
            return f(*args, **kwargs)
        return decorated_func
    return decorator


def verify_signature_foreign(f):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        signature = request.headers.get('signature')
        origin_id = request.headers.get('origin-id')

        if not any([signature, origin_id]):
            return "Invalid request", 400

        data = json.dumps(request.get_json())
        pub_key = bogchain.peers.get_pub_key(origin_id)

        if Pki.verify(signature, data, pub_key) is False:
            return "Invalid signature", 403
        return f(*args, **kwargs)
    return decorated_func


def verify_signature_local(f):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        signature = request.headers.get('signature')

        if not signature:
            return "Invalid request", 400

        data = json.dumps(request.get_json())
        pub_key = pki.pub_key

        if Pki.verify(signature, data, pub_key) is False:
            return "Invalid signature", 403
        return f(*args, **kwargs)
    return decorated_func


@app.route('/test', methods=['POST'])
@verify_signature_foreign
def test_post():
    return "OK", 200


@app.route('/mine', methods=['GET'])
def mine():
    last_proof = bogchain.last_block['proof']
    proof = bogchain.proof_of_work(last_proof)

    bogchain.new_transaction(sender="0", recipient=node_id, amount=1)

    block = bogchain.new_block(proof)

    response = {
        'message': 'New block forged',
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }

    return jsonify(response), 200


@app.route('/transactions/send', methods=['POST'])
@check_post_keys(['recipient', 'amount'])
@verify_signature_local
def flood_transaction():
    trans_json = request.get_json()
    trans_json['sender'] = node_id

    gossip.flood("/transactions/process", trans_json)

    response = f"Outgoing transaction {trans_json['amount']} to {trans_json['recipient']}"

    return response, 201


@app.route('/transactions/process')
@verify_signature_foreign
def process_transaction():
    trans_json = request.get_json()

    required = ['sender', 'recipient', 'amount']
    if not all(key in trans_json for key in required):
        return "Missing required values", 400

    bogchain.new_transaction(trans_json['sender'], trans_json['recipient'], trans_json['amount'])

    response = f"New transaction {trans_json['amount']} from {trans_json['sender']} to {trans_json['recipient']}"
    app.logger.debug(response)

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
    return jsonify(bogchain.peers.addresses_keys)


@app.route('/nodes/register', methods=['POST'])
@check_post_keys(['address', 'node_id', 'pub_key'])
def register_nodes():
    node = request.get_json()

    if node is None:
        return "No nodes provided", 400

    if bogchain.peers.add_peer(node['address'], node['node_id'], node['pub_key']):
        new_node_id = node['node_id']
        app.logger.debug(f"Registered new node {new_node_id}")
    else:
        app.logger.debug(f"Node already exists")

    response = {
        'message': 'Node added',
        'new_node': node
    }

    return jsonify(response), 201


@app.route('/update', methods=['POST'])
@check_post_keys(['chain', 'peers'])
@verify_signature_foreign
def update_state():
    update_json = request.get_json()


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


async def main(schedule_file):
    tasks = []

    if schedule_file is not None:
        test_schedule = TestScheduler(schedule_file,
                                      bogchain=bogchain,
                                      pki=pki,
                                      logger=app.logger,
                                      url=self_url,
                                      node_id=node_id)

        tasks.append(asyncio.create_task(test_schedule.execute()))

    # todo dodać pętle obsługi kopania

    await asyncio.gather(*tasks)


if __name__ == '__main__':
    arg_parser = ArgumentParser()
    arg_parser.add_argument('-p', '--port', default=5000, type=int, help="listening port")
    arg_parser.add_argument('-G', '--genesis', action="store_true", help="mines genesis block")
    arg_parser.add_argument('-v', '--verbose', action="store_true", help="display info level logs")
    arg_parser.add_argument('-s', '--schedule', default=None, type=str, help="test schedule file")
    cl_args = arg_parser.parse_args()
    port = cl_args.port
    verbose = cl_args.verbose
    genesis = cl_args.genesis
    schedule_file = cl_args.schedule

    if verbose:
        app.logger.setLevel(logging.DEBUG)

    if genesis:
        bogchain.create_genesis_block(node_id)

    self_url = f"http://localhost:{port}"

    app_thread = threading.Thread(target=app.run,
                                  kwargs={'host': "0.0.0.0", 'port': port},
                                  daemon=True)
    app_thread.start()

    asyncio.run(main(schedule_file))

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        exit(0)



