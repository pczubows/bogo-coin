class Bogchain:

    def __init__(self):
        self.chain = []
        self.completed_transaction = []

    def new_block(self):
        pass

    def new_transaction(self):
        pass

    @staticmethod
    def hash(self):
        pass

    @property
    def last_block(self):
        return self.chain[-1]
