import requests
import aiohttp
import asyncio
import json


class Gossip:
    def __init__(self, **kwargs):
        self.bogchain = kwargs['bogchain']
        self.pki = kwargs['pki']
        self.node_id = kwargs['node_id']
        self.local_url = None

    def get_headers(self, data):
        signature = self.pki.sign(json.dumps(data))
        return {'origin-id': self.node_id, 'signature': signature}

    def register_response(self, url):
        register_json = {
            'address': self.local_url,
            'node_id': self.node_id,
            'pub_key': self.pki.pub_key
        }

        url = url + "/nodes/register"

        self.bogchain.logger.info("Registering self with new peer")
        register_self_request = requests.post(url, json=register_json, headers={'registration-resp': '1'})

        if register_self_request.status_code == 201:
            update_request = requests.post(url, json=self.bogchain.current_state, headers=self.get_headers(register_json))
            self.bogchain.logger.info("Sending response with current node state")

            if update_request.status_code == 200:
                self.bogchain.logger.info("Posting node state to peer successful")
            else:
                self.bogchain.logger.info(f"Posting node state to peer failed status code: {update_request.status_code}")
        else:
            self.bogchain.logger.info(f"Registering with new peer failed status code: {register_self_request.status_code}")

    async def post(self, url, post_json):
        async with aiohttp.ClientSession() as session:
            await session.post(url, json=post_json, headers=self.get_headers)

    def flood(self, path, data, excluded=None):
        pending_requests = []

        for address in self.bogchain.peers.addresses:
            if address not in excluded:
                pending_requests.append(self.post(f"{address}{path}", data))

        asyncio.run(asyncio.wait(pending_requests))

