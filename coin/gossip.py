import requests
import aiohttp
import asyncio


class Gossip:
    def __init__(self, bogchain):
        self.bogchain = bogchain

    def register_response(self):
        pass

    async def bogchain_advert(self):
        pass  # todo pojedyncze zapytanie z blockchainem w środku

    def receive_advert(self):
        pass  # todo obsłużenie rozgłoszenia

    @staticmethod
    async def post(url, post_json):
        async with aiohttp.ClientSession() as session:
            await session.post(url, json=post_json)

    def flood(self, path, data, excluded=None):
        requests = []

        for address in self.bogchain.peers.addresses:
            if address not in excluded:
                requests.append(Gossip.post(f"{address}{path}", data))

        asyncio.run(asyncio.wait(requests))

