import requests
import json

from time import sleep


class TestScheduler:
    allowed = [
        'register',
        'test',
        'transfer',
        'sleep'
    ]

    def __init__(self, schedule_file, **kwargs):
        self.schedule = schedule_file
        self.bogchain = kwargs['bogchain']
        self.pki = kwargs['pki']
        self.logger = kwargs['logger']
        self.url = kwargs['url']
        self.node_id = kwargs['node_id']

    async def execute(self):
        with open(self.schedule, 'r') as f:
            lines = f.readlines()

        for line in lines:
            command_args = line.split()

            if command_args[0] == '#':
                continue

            if command_args[1] in self.allowed:
                sleep(float(command_args[0]))
                method = getattr(self, command_args[1])
                method(*command_args[2:])
                self.log(command_args)

    def log(self, command_args):
        target = command_args[2] if len(command_args) > 2 else "self"
        self.logger.info(f"Executing {command_args[1]} on {target}")

    def get_headers(self, data):
        signature = self.pki.sign(json.dumps(data))
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

    def transfer(self, *args):
        pass  # todo wykonaj przelew

    def sleep(self):
        pass  # todo nie rób nic przez zadany czas
