import requests
import logging
import json
import readline
import code

from urllib.parse import urlparse
from subprocess import Popen


def check_if_running(func):
    """
    decorator preventing execution of decorated method when flask app is not running

    :param func:
    :return:
    """

    def wrapper(*args):
        if args[0].running is False:
            print('App is not running')
            return
        else:
            return func(*args)

    return wrapper


class VirtualUser:
    def __init__(self, url, log_level=logging.INFO):
        self.url = url = urlparse(url)
        self.host = url.hostname
        self.port = url.port
        self.app = None

        logging.basicConfig(level=log_level)

    @property
    def running(self):
        """
        Check if flask app is running

        :return:
        """

        if self.app is None:
            return False
        elif self.app.poll() is None:
            return True

        return False

    @property
    @check_if_running
    def node_id(self):
        r = requests.get(self.url + '/node_id')
        return r.json()['node_id']

    def run(self):
        """
        Run flask app

        :return:
        """

        self.app = Popen(['python', 'bogchain.py', self.host, str(self.port)])

    @check_if_running
    def stop(self):
        """
        Stop flask app

        :return:
        """

        self.app.terminate()

    @staticmethod
    def log_response(r):
        """
        Log response from the blockchain query

        :param r: <Response>
        :return:
        """

        if r.status_code == 200:
            logging.info(json.dumps(r.json()))
        else:
            logging.info(f'{r.url} {r.status_code}')

    @check_if_running
    def mine(self):
        """
        Send mine request to blockchain

        :return:
        """
        r = requests.get(self.url + '/mine')
        self.log_response(r)

    @check_if_running
    def send(self, recipient, amount):
        """
        Send new transaction request to blockchain

        :param recipient: <str> Recipient of transaction
        :param amount: <int> Amount of bog coins to be sent
        :return:
        """

        data = {
            'sender': self.node_id,
            'recipient': recipient,
            'amount': amount
        }

        r = requests.post(self.url + '/transactions/new', json=json.loads(data))
        self.log_response(r)


if __name__ == "__main__":
    user1 = VirtualUser('https://localhost:5001')
    user2 = VirtualUser('https://localhost:5002')

    variables = globals().copy()
    variables.update(locals())
    shell = code.InteractiveConsole(variables)
    shell.interact()
