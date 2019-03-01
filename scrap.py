import asyncio
import aiohttp
import traceback


async def cancel_me():
    await asyncio.sleep(4)
    return "oops"


async def post(url, post_json):
    async with aiohttp.ClientSession() as session:
        try:
            print(url)
            async with session.post(url, json=post_json) as response:
                response = await response.read()
                print(response)
        except Exception:
            print(traceback.format_exc())


async def main():
    pass


loop = asyncio.get_event_loop()
loop.run_until_complete(post("http://httpbin.org/post", {"Wyjątki": 'Niejasne'}))
