class Peers:
    def __init__(self):
        self.addresses_keys = {}

    def add_peer(self, address, node_id, pub_key):
        if node_id not in self.addresses_keys.keys():
            self.addresses_keys[node_id] = address, pub_key
            return True

        return False

    def get_address(self, node_id):
        return self.addresses_keys[node_id][0]

    def get_pub_key(self, node_id):
        return self.addresses_keys[node_id][1]

    @property
    def addresses(self):
        yield from self.addresses_keys[0]
