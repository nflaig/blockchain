from bitcoin import *
import hashlib

from src.blockchain import Blockchain


class Wallet:
    def __init__(self):
        self.addresses = []
        self.address_to_keys = {}
        self.address_to_balance = {}

        # Initialize wallet with one address and corresponding key pair
        private_key = random_key()
        public_key = privtopub(private_key)
        address = pubtoaddr(public_key)

        self.addresses.append(address)
        self.address_to_keys[address] = [private_key, public_key]
        self.address_to_balance[address] = 0

    def total_balance(self):
        """
        Returns the total balance of the wallet by adding up the balance of each address.
        :return: total_balance: <int> Total balance
        """
        total_balance = 0

        for address in self.address_to_balance:
            total_balance += self.address_to_balance[address]

        return total_balance

    def update_balances(self, chain):
        """
        Update the balance for each address.
        :param chain: <list> The blockchain
        :return: None
        """

        last_block_index = len(chain)

        for address in self.address_to_balance:
            balance = Blockchain.address_balance_at_block_index(address, chain, last_block_index)
            self.address_to_balance[address] = balance

    def generate_address(self):
        """
        Generate a new key pair and return the address.
        :return: address: <int> New address
        """
        private_key = random_key()
        public_key = privtopub(private_key)
        address = pubtoaddr(public_key)

        self.addresses.append(address)
        self.address_to_keys[address] = [private_key, public_key]
        self.address_to_balance[address] = 0

        return address

    def sign_transaction(self, sender, recipient, amount):
        """
        Create a valid digital signature and return the signed transaction.
        :param sender: <str> Sender of the transaction
        :param recipient: <str> Recipient of the transaction
        :param amount: <int> Amount of coins
        :return: signed_transaction: <dict> Signed transaction
        """

        # Check if the wallet has a private key corresponding to the address
        if sender in self.address_to_keys:
            # Get the private key
            private_key = self.address_to_keys.get(sender)[0]
        else:
            return None

        transaction_content = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        }

        # Order the transaction to avoid inconsistent hashes
        transaction_encoded = json.dumps(transaction_content, sort_keys=True).encode()
        transaction_hash = hashlib.sha256(transaction_encoded).hexdigest()

        # Create a valid digital signature for the transaction by using the Elliptic Curve Digital Signature Algorithm
        signature = ecdsa_sign(transaction_hash, private_key)

        # Create a transaction with a valid digital signature
        signed_transaction = {
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
            'signature': signature
        }

        return signed_transaction
