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
        node = self.addresses_pub_keys.get(node_id)

        if node is not None:
            return node['address']
        else:
            return None

    def get_pub_key(self, node_id):
        node = self.addresses_pub_keys.get(node_id)

        if node is not None:
            return node['pub_key']
        else:
            return None

    @property
    def addresses(self):
        for peer in self.addresses_pub_keys.values():
            yield peer['address']
