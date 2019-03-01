import requests
import json
import traceback


class Gossip:
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.pki = kwargs['pki']
        self.node_id = kwargs['node_id']
        self.local_url = None

    def get_headers(self, data):
        signature = self.pki.sign(json.dumps(data, sort_keys=True))
        return {'origin-id': self.node_id, 'signature': signature}

    def register_response(self, url, node_state):
        register_json = {
            'address': self.local_url,
            'node_id': self.node_id,
            'pub_key': self.pki.pub_key
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
            else:
                self.logger.info(f"Posting node state to peer failed status code: {update_request.status_code}")
        else:
            self.logger.info(f"Registering with new peer failed status code: {register_self_request.status_code}")

    def flood(self, path, data, addresses, excluded=[]):
        for address in addresses:
            if address not in excluded:
                post_request = requests.post(f"{address}{path}", json=data, headers=self.get_headers(data))
                self.logger.info(f"Node state sent to peer request status code: {post_request.status_code}")
