class Peers:
    def __init__(self):
        self.addresses_pub_keys = {}
        self.node_ids = {}

    def add_peer(self, address, node_id, pub_key):
        if node_id not in self.addresses_pub_keys.keys():
            self.addresses_pub_keys[node_id] = {'address': address, 'pub_key': pub_key}
            self.node_ids[address] = node_id
            return True

        return False

    def get_address(self, node_id):
        return self.addresses_pub_keys[node_id]['address']

    def get_pub_key(self, node_id):
        return self.addresses_pub_keys[node_id]['pub_key']

    @property
    def addresses(self):
        for peer in self.addresses_pub_keys.values():
            yield peer['address']
