import requests
import json
import time
import random

from uuid import uuid4

# todo add parameters to each method


class TestScheduler:
    """Class responsible for automatic access to application endpoints
    and communication with other applications in the network.

    Class methods to be executed along with their timing and parameters are
    provided in formatted schedule file. Syntax as follows:

    [loop] [n] sleep_time method_name [target] [args ...]

    sleep_time: floating point value passed to time.sleep before command is executed
        put 0 for no sleep time
    method_name: method to be called by the scheduler
    target: url of another application

    Prepending line with loop n where n is the integer will cause method to be
    executed n times each time with the specified wait time

    Line can be escaped by placing '#' at its beginning.

    Attributes:
        app_kill_event (threading.Event): Event handle allowing for graceful exit
            from separate thread
        schedule_file (str): path of the file containing methods to be executed
        bogchain (coin.Bogchain): Bogchain object necessary for access to peers,
                                  logger and application id
        key_pair (coin.KeyPair): KeyPair object for signing requests
        url (str): url of the application using TestScheduler
        allowed (list): list of methods that can be called
        self_targeted (list): list of methods that are making request on app calling them
    """

    allowed = [
        'register',
        'test',
        'transfer',
        'dummy_transaction',
        'kill',
        'forge_chain',
        'sleep'
    ]

    self_targeted = ['dummy_transactios', 'transfer']

    def __init__(self, schedule_file, **kwargs):
        """Inits TestScheduler

        Parameters
            schedule_file (str): path of the file containing methods to be executed

        Keyword Arguments:
            app_kill_event (threading.Event): Event handle allowing for graceful exit
                from separate thread
            bogchain (coin.Bogchain): Bogchain object necessary for access to peers,
                                      logger and application id
            key_pair (coin.KeyPair): KeyPair object for signing requests
            url (str): url of the application using TestScheduler
        """
        self.schedule_file = schedule_file
        self.app_kill_event = kwargs['app_kill_event']
        self.bogchain = kwargs['bogchain']
        self.key_pair = kwargs['key_pair']
        self.url = kwargs['url']

    def execute(self):
        """Executes methods provided in schedule file"""
        with open(self.schedule_file, 'r') as f:
            lines = f.readlines()

        for line in lines:
            command_args = line.split()

            if command_args[0] == '#':
                continue

            loop_n_times = 1

            if command_args[0] == "loop":
                loop_n_times = int(command_args[1])
                command_args = command_args[2:]

            if command_args[1] in self.allowed:
                for _ in range(loop_n_times):
                    self.log(command_args)

                    sleep_time = float(command_args[0])

                    if sleep_time > 0:
                        time.sleep(sleep_time)

                    if command_args[1] == "sleep":
                        continue

                    method = getattr(self, command_args[1])
                    method(*command_args[2:])

    def log(self, command_args):
        target = command_args[2] if [] else "self"
        self.bogchain.logger.info(f"Executing {command_args[1]} on {target}")

    def get_headers(self, data):
        """create headers with signature and application id

        Parameters:
            data (dict): post body to be signed

        Returns:
            dict: dict with origin header and signature header
        """

        signature = self.key_pair.sign(json.dumps(data, sort_keys=True))
        return {'origin-id': self.bogchain.node_id, 'signature': signature}

    def register(self, *args):
        """registers application with remote remote application

        Usage:
            sleep_time register url_of_app
        """
        register_json = {
            'address': self.url,
            'node_id': self.bogchain.node_id,
            'pub_key': self.key_pair.pub_key}

        requests.post(f"http://{args[0]}/nodes/register", json=register_json)

    def test(self, *args):
        """access to the test endpoint

        Usage:
            sleep_time test url_of_app
        """
        test_json = {'dummy': "dummy"}

        requests.post(f"http://{args[0]}/test",
                      json=test_json,
                      headers=self.get_headers(test_json))

    def dummy_transaction(self, *args):
        """Creates fake transaction dict and immediately submits it for mining

        Usage:
            sleep_time dummy_transaction url_of_app sender recipient amount
        """
        transaction_json = {
            'sender': args[1],
            'recipient': args[2],
            'amount': args[3],
            'id': str(uuid4())
        }

        requests.post(f"http://{args[0]}/transactions/process",
                      json=transaction_json,
                      headers=self.get_headers(transaction_json))

    def transfer(self, *args):
        """Creates new valid transaction dict

        Usage:
            sleep_time transfer recipients_url amount
        """
        recipient = self.bogchain.peers.node_ids[f"http://{args[0]}"]
        amount = int(args[1])

        transaction_json = {
            'recipient': recipient,
            'amount': amount
        }

        requests.post(f"{self.url}/transactions/new", json=transaction_json, headers=self.get_headers(transaction_json))

    def forge_chain(self, *args):
        """Forge fake blockchain and submit it for update

        app will try to use real genesis block if possible

        Usage:
            sleep_time forge_chain length amount_to_forge_in_each_block
        """
        self.bogchain.evil = True

        if self.bogchain.mining_task is not None:
            self.bogchain.mining_task.cancel()

        fake_chain = []

        if len(self.bogchain.chain) == 0:
            genesis_transactions = [self.bogchain.create_transaction('mint',
                                                                     self.bogchain.node_id,
                                                                     self.bogchain.mining_bounty)]
            genesis_block = {
                'index': 0,
                'timestamp': time.time(),
                'transactions': genesis_transactions,
                'proof': 100,
                'previous_hash': 'gen'
            }

            fake_chain.append(genesis_block)
        else:
            fake_chain.append(self.bogchain.chain[0])

        fake_length = int(args[0])
        block_amount = int(args[1])

        for i in range(1, fake_length):
            fake_transactions = [self.bogchain.create_transaction(
                random.sample(self.bogchain.peers.addresses_pub_keys.keys(), 1),  # choose random peer as target
                self.bogchain.node_id,
                block_amount
            )]

            previous_block = fake_chain[i - 1]

            proof = self.bogchain.proof_of_work(previous_block['proof'])

            fake_block = {
                'index': len(fake_chain),
                'timestamp': time.time(),
                'transactions': fake_transactions,
                'proof': proof,
                'previous_hash': self.bogchain.hash(previous_block)
            }

            fake_chain.append(fake_block)

        self.bogchain.chain = fake_chain
        self.bogchain.gossip.flood('/update', self.bogchain.current_state, self.bogchain.peers.addresses)

    def kill(self):
        """Shutdown app

        Usage:
            sleep_time kill
        """
        self.app_kill_event.set()

