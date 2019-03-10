"""Bogo coin node

Flask app that simulates node of a fake cryptocurrency bogo-coin.
It includes simplified blockchain, very simple request verification,
gossip-like protocol for communication with other nodes in the network
and scheduler allowing for automated tests of the network.

"""

import logging
import json
import asyncio
import threading
import time

from uuid import uuid4
from flask import Flask, request, jsonify
from argparse import ArgumentParser
from functools import wraps

from coin.bogchain import Bogchain
from coin.key_pair import KeyPair
from coin.gossip import Gossip
from coin.test_scheduler import TestScheduler


# todo sprawdzanie Genesis
# todo sprawdzanie timestampów
# todo integracja z Dockerem

app = Flask(__name__)

node_id = str(uuid4()).replace('-', '')

key_pair = KeyPair()
gossip = Gossip(logger=app.logger, key_pair=key_pair, node_id=node_id)
bogchain = Bogchain(node_id=node_id, logger=app.logger, gossip=gossip)


def check_post_keys(required):
    """verify if post request contains necessary keys"""
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
    """verify signature of a request coming from different app"""
    @wraps(f)
    def decorated_func(*args, **kwargs):
        signature = request.headers.get('signature')
        origin_id = request.headers.get('origin-id')

        if not any([signature, origin_id]):
            return "Invalid request", 400

        data = json.dumps(request.get_json(), sort_keys=True)
        pub_key = bogchain.peers.get_pub_key(origin_id)

        if pub_key is None:
            return "Node not registered", 403

        if KeyPair.verify(signature, data, pub_key) is False:
            return "Invalid signature", 403
        return f(*args, **kwargs)
    return decorated_func


def verify_signature_local(f):
    """verify request signed with apps own private key"""
    @wraps(f)
    def decorated_func(*args, **kwargs):
        signature = request.headers.get('signature')

        if not signature:
            return "Invalid request", 400

        data = json.dumps(request.get_json(), sort_keys=True)
        pub_key = key_pair.pub_key

        if KeyPair.verify(signature, data, pub_key) is False:
            return "Invalid signature", 403
        return f(*args, **kwargs)
    return decorated_func


@app.route('/test', methods=['POST'])
@verify_signature_foreign
def test_post():
    """test endpoint for verification debugging"""
    return "OK", 200


@app.route('/transactions/new', methods=['POST'])
@check_post_keys(['recipient', 'amount'])
@verify_signature_local
def create_transaction():
    """Endpoint for creating new transaction, new transaction is then
    broadcasted to app peers"""
    trans_json = request.get_json()
    trans_json['sender'] = node_id

    gossip.flood("/transactions/process", trans_json, bogchain.peers.addresses)

    response = f"Outgoing transaction {trans_json['amount']} to {trans_json['recipient']}"

    return response, 201


@app.route('/transactions/process', methods=['POST'])
@check_post_keys(['sender', 'recipient', 'amount'])
@verify_signature_foreign
def process_transaction():
    """Endpoint for processing new transactions received from peer apps"""
    trans_json = request.get_json()

    bogchain.awaiting_transactions.append(
        Bogchain.create_transaction(trans_json['sender'], trans_json['recipient'], trans_json['amount']))
    if not bogchain.wake_transaction_handler.is_set():
        bogchain.wake_transaction_handler.set()

    response = f"New transaction {trans_json['amount']} from {trans_json['sender']} to {trans_json['recipient']}"
    app.logger.debug(response)

    return response, 201


@app.route('/chain', methods=['GET'])
def full_chain():
    """return blockchain in json format"""
    response = {
        'chain': bogchain.chain,
        'length': len(bogchain.chain)
    }

    return jsonify(response), 200


@app.route('/peers', methods=['GET'])
def nodes():
    """return app peers in json format"""
    return jsonify(bogchain.peers.node_ids)


@app.route('/nodes/register', methods=['POST'])
@check_post_keys(['address', 'node_id', 'pub_key'])
def register_nodes():
    """Endpoint for registering new peer

    New peer accesses this endpoint, then if request had valid keys app
    registers itself with new peer. If registration was successful
    response with current blockchain state and already registered peers is
    sent. Then ff response was received by new peer, app broadcasts
    new peer list to all its old peers excluding new peer
    """
    node = request.get_json()

    if node is None:
        return "No nodes provided", 400

    if bogchain.peers.add_peer(node['address'], node['node_id'], node['pub_key']):
        new_node_id = node['node_id']
        app.logger.debug(f"Registered new node {new_node_id}")

        if "Registration-Resp" not in request.headers:
            register_resp_success = gossip.register_response(node['address'], bogchain.current_state)
            if register_resp_success:
                gossip.flood("/update", bogchain.current_state, bogchain.peers.addresses, [node['address']])
    else:
        message = f"Node {node['node_id']} already exists"
        app.logger.debug(message)

        return jsonify({'message': message}), 409

    response = {
        'message': 'Node added',
        'new_node': node
    }

    return jsonify(response), 201


@app.route('/update', methods=['POST'])
@check_post_keys(['chain', 'peers'])
@verify_signature_foreign
def update_state():
    """Endpoint for receiving updates from peer apps"""
    update_json = request.get_json()

    updated = bogchain.update_chain(update_json['chain'])

    if updated and bogchain.mining_task is not None:
        bogchain.mining_task.cancel()
        app.logger.info("Recieved new update cancelling mining task")

    new_peers = bogchain.update_peers(update_json['peers'])

    response = {
        'new_peers': new_peers,
        'updated': updated
    }

    return jsonify(response), 200


@app.route('/balance', methods=['GET'])
def balance():
    """Endpoint returning current bogo coin balance"""
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
    """Endpont returning app unique id"""
    return jsonify({"node_id": node_id}), 200


if __name__ == '__main__':
    arg_parser = ArgumentParser()
    arg_parser.add_argument('-p', '--port', default=5000, type=int, help="listening port")
    arg_parser.add_argument('-G', '--genesis', action="store_true", help="mines genesis block")
    arg_parser.add_argument('-v', '--verbose', action="store_true", help="display info level logs")
    arg_parser.add_argument('-s', '--schedule', default=None, type=str, help="test schedule file")
    arg_parser.add_argument('-a', '--accumulation', default=3, type=float,
                            help="time until transactions are mined into block")
    arg_parser.add_argument('-T', '--throttle', default=None, type=float)

    cl_args = arg_parser.parse_args()
    port = cl_args.port
    verbose = cl_args.verbose
    genesis = cl_args.genesis
    schedule_file = cl_args.schedule
    accumulation_period = cl_args.accumulation
    throttle = cl_args.throttle

    if verbose:
        app.logger.setLevel(logging.DEBUG)

    if genesis:
        bogchain.create_genesis_block()

    if throttle:
        bogchain.throttle = throttle

    gossip.local_url = f"http://127.0.0.1:{port}"

    test_schedule = TestScheduler(schedule_file,
                                  bogchain=bogchain,
                                  key_pair=key_pair,
                                  url=gossip.local_url,
                                  node_id=node_id)

    app_thread = threading.Thread(target=app.run,
                                  kwargs={'host': "0.0.0.0", 'port': port},
                                  daemon=True)

    scheduler_thread = threading.Thread(target=test_schedule.execute, daemon=True)

    app_thread.start()
    scheduler_thread.start()

    asyncio.run(bogchain.handle_transactions(accumulation_period))

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        exit(0)
