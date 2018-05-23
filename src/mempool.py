import hashlib
import json


class Mempool:
    def __init__(self):
        self.current_transactions = []

    def add_transaction(self, signed_transaction, blockchain):
        """
        Add a valid, signed transaction to the mempool.
        :param signed_transaction: <dict> Signed transaction
        :param blockchain: <object> Blockchain object
        :return: <bool> True if the transaction is added to the mempool, False if not
        """

        if self.valid_transaction(signed_transaction, blockchain):
            self.current_transactions.append(signed_transaction)
            return True
        else:
            return False

    @staticmethod
    def hash(transactions):
        """
        Calculate a SHA-256 hash of all transactions in the mempool.
        :param transactions: <list> Transactions
        :return: <str> Hash of the transactions
        """

        # Order the transactions to avoid inconsistent hashes
        block_encoded = json.dumps(transactions, sort_keys=True).encode()
        return hashlib.sha256(block_encoded).hexdigest()

    def valid_transaction(self, signed_transaction, blockchain):
        """
        Validate the transaction by first checking the mempool for transactions of the sender then the
        signature of the transaction is verified and finally it is checked if the sender has enough funds.
        :param signed_transaction: <dict> Signed transaciton
        :param blockchain: <object> Blockchain object
        :return: <bool> True if the transaction is valid, False if not
        """

        # Check if the amount of coins to send is negative
        amount = signed_transaction['amount']

        if amount < 0:
            return False

        sender = signed_transaction['sender']

        # Check if a transaction of the sender already exists in the mempool
        for current_transaction in self.current_transactions:
            # Reject if a transaction from the sender already exists
            if current_transaction['sender'] == sender:
                return False

        # Validate the signature of the transaction and check if the sender has enough funds
        if not blockchain.valid_transaction(signed_transaction, blockchain.chain, blockchain.last_block['index']):
            return False
        else:
            return True
