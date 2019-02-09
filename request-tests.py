import requests
import json

from coin.pki import Pki


def test_verify(address):
    pki = Pki()
    origin_id = "fafafaf"

    register_json = {
        {'address': "bogo.com",
         'node_id': origin_id,
         'pub_key': pki.pub_key}}

    requests.post(f'{address}/nodes/register', json=register_json)

    test_json = {'dummy': "dummy"}

    signature = pki.sign(json.dumps(test_json))
    headers = {'origin-id': origin_id, 'signature': signature}

    requests.post(f'{address}/test', headers=headers, json=test_json)
    print(pki.pub_key)


if __name__ == "__main__":
    test_verify("http://localhost:5000")
