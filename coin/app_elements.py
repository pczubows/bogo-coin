class AppElements:
    def __init__(self, **kwargs):
        self.bogchain = None
        self.pki = None
        self.logger = kwargs['logger']
        self.node_id = kwargs['node_id']
