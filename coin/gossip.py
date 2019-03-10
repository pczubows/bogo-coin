import requests
import json


class Gossip:
    """Set of methods for sharing application state with peers

    Attributes:
        logger (Flask.app.logger): flask app logger for debug
        key_pair (coin.KeyPair): rsa key pair
        node_id (str): app unique id
        local_url (str): app url
    """

    def __init__(self, **kwargs):
        """Inits Gossip

        Keyword Arguments:
            logger (Flask.app.logger): app logger for debug
            key_pair (coin.KeyPair): rsa key pair
            node_id (str): app unique id
        """
        self.logger = kwargs['logger']
        self.key_pair = kwargs['key_pair']
        self.node_id = kwargs['node_id']
        self.local_url = None

    def get_headers(self, data):
        """create headers with signature and application id

        Parameters:
            data (dict): post body to be signed

        Returns:
            dict: dict with origin header and signature header
        """
        signature = self.key_pair.sign(json.dumps(data, sort_keys=True))
        return {'origin-id': self.node_id, 'signature': signature}

    def register_response(self, url, node_state):
        """Send app state to a new peer

        Parameters:
            url (str): url of a new peer
            node_state (dict): current state of the app a dict containing
                dict with peers and blockchain

        Returns:
            bool: True if app state was posted successfully to new peer
        """
        register_json = {
            'address': self.local_url,
            'node_id': self.node_id,
            'pub_key': self.key_pair.pub_key
        }

        register_url = url + "/nodes/register"

        self.logger.info("Registering self with new peer")
        register_self_request = requests.post(register_url, json=register_json, headers={'Registration-Resp': '1'})

        if register_self_request.status_code == 201:
            update_url = url + "/update"
            update_request = requests.post(update_url, json=node_state, headers=self.get_headers(node_state))
            self.logger.info("Sending response with current node state")

            if update_request.status_code == 200:
                self.logger.info("Posting node state to peer successful")
                return True
            else:
                self.logger.info(f"Posting node state to peer failed status code: {update_request.status_code}")
                return False
        else:
            self.logger.info(f"Registering with new peer failed status code: {register_self_request.status_code}")
            return False

    def flood(self, path, data, addresses, excluded=None):
        """Send app state to all peers unless peers to be omitted are
        specified

        Parameters:
            path (str): another applications endpoint path
            data (dict): post body
            addresses (generator): a generator object that yields peer addresses
            excluded (list): List of peers to be excluded from app state update. Defaults to None
        """

        for address in addresses:
            if excluded is None or address not in excluded:
                post_request = requests.post(f"{address}{path}", json=data, headers=self.get_headers(data))
                self.logger.info(f"Node state sent to peer request status code: {post_request.status_code}")
