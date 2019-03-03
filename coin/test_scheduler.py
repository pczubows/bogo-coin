import requests
import json
import traceback
import time


class TestScheduler:
    allowed = [
        'register',
        'test',
        'transfer',
        'sleep',
        'dummy_transaction'
    ]

    def __init__(self, schedule_file, **kwargs):
        self.schedule = schedule_file
        self.bogchain = kwargs['bogchain']
        self.pki = kwargs['pki']
        self.url = kwargs['url']
        self.node_id = kwargs['node_id']

    def execute(self):
        with open(self.schedule, 'r') as f:
            lines = f.readlines()

        for line in lines:
            command_args = line.split()

            if command_args[0] == '#':
                continue

            if command_args[1] in self.allowed:
                time.sleep(float(command_args[0]))
                method = getattr(self, command_args[1])
                method(*command_args[2:])
                self.log(command_args)

    def log(self, command_args):
        target = command_args[2] if len(command_args) > 2 else "self"
        self.bogchain.logger.info(f"Executing {command_args[1]} on {target}")

    def get_headers(self, data):
        signature = self.pki.sign(json.dumps(data, sort_keys=True))
        return {'origin-id': self.node_id, 'signature': signature}

    def register(self, *args):
        register_json = {
            'address': self.url,
            'node_id': self.node_id,
            'pub_key': self.pki.pub_key}

        requests.post(f"http://{args[0]}/nodes/register", json=register_json)

    def test(self, *args):
        test_json = {'dummy': "dummy"}

        requests.post(f"http://{args[0]}/test",
                      json=test_json,
                      headers=self.get_headers(test_json))

    def dummy_transaction(self, *args):
        transaction_json = {
            'sender': args[1],
            'recipient': args[2],
            'amount': args[3]
        }

        requests.post(f"http://{args[0]}/transactions/process",
                      json=transaction_json,
                      headers=self.get_headers(transaction_json))

    def transfer(self, *args):
        recipient = self.bogchain.peers.node_ids[f"http://{args[0]}"]
        amount = int(args[1])

        transaction_json = {
            'recipient': recipient,
            'amount': amount
        }

        requests.post(f"{self.url}/transactions/new", json=transaction_json, headers=self.get_headers(transaction_json))
