from bitcoin import *
import hashlib
import json
from time import time
import requests

from src.proof_of_work import ProofOfWork
from src.mempool import Mempool
from src.network import Network


class Blockchain:
    def __init__(self):
        self.chain = []

        # Instantiate mempool
        self.mempool = Mempool()

        # Instantiate the network of nodes which are connected to his node
        self.network = Network()

        # Create the genesis block
        self.create_block(
            nonce=0,
            previous_block_hash='86a4be451d0e4ae83bcd72e1eb5308b19a4b270f95c25d752927341f7632a1cc'
        )

    def create_block(self, nonce, previous_block_hash=None, transactions_of_block=None):
        """
        Create a new block and append it to the chain.
        :param nonce: <int> The nonce calculated by the Proof of Work algorithm
        :param previous_block_hash: (Optional) <str> Hash of previous block
        :param transactions_of_block: <list> Transactions included in the block
        :return: block: <dict> Created and appended block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'nonce': nonce,
            'transactions_hash': self.mempool.hash(transactions_of_block),
            'previous_block_hash': previous_block_hash or self.hash(self.chain[-1]),
            'transactions': transactions_of_block
        }

        # Add the new block to the end of the chain
        self.chain.append(block)

        return block

    @staticmethod
    def hash(block):
        """
        Calculate a SHA-256 hash of a block.
        :param block: <dict> Block
        :return: <str> Hash of the block
        """

        # Order the block to avoid inconsistent hashes
        block_encoded = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_encoded).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def reach_consensus(self):
        """
        Algorithm used to reach consensus in the network.
        The current chain of the node will be replaced if
        a longer valid chain exists in the network.
        :return: <bool> True if chain was replaced, False if not
        """

        neighbour_nodes = self.network.nodes

        longest_chain_length = len(self.chain)
        longer_chain = None

        # Query all the nodes in the network and request their chain
        for node in neighbour_nodes:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the chain is longer and valid
                if length > longest_chain_length and self.valid_chain(chain):
                    longest_chain_length = length
                    longer_chain = chain

        # Replace the chain if there is a longer and valid chain in the network
        if longer_chain:
            self.chain = longer_chain
            return True

        return False

    def valid_chain(self, chain):
        """
        Validate a given blockchain by checking the hash, the Proof of Work and the transactions for each block.
        :param chain: <list> The blockchain
        :return: <bool> True if valid, False if not
        """

        previous_block = chain[0]
        block_index = 1

        while block_index < len(chain):
            current_block = chain[block_index]

            # Validate the hash of the block
            if current_block['previous_block_hash'] != self.hash(previous_block):
                return False

            # Validate the Proof of Work
            if not ProofOfWork.valid_proof(current_block['transactions_hash'],
                                           self.hash(previous_block),
                                           current_block['nonce']):
                return False

            # Validate the transactions of the block
            if current_block['transactions']:
                coinbase_transactions = 0
                for current_transaction in current_block['transactions']:
                    # Count the amount of coinbase transactions in the block
                    if current_transaction['sender'] == "0":
                        coinbase_transactions += 1
                    if not self.valid_transaction(current_transaction, chain, block_index):
                        return False
                # If the block contains more than one coinbase transaction return False
                if coinbase_transactions > 1:
                    return False

            previous_block = current_block
            block_index += 1

        return True

    def valid_transaction(self, signed_transaction, chain, block_index):
        """
        Validate the transaction on the blockchain.
        First the signature of the transaction is verified then it is
        checked if the sender had enough funds at the time of the transaction.
        :param signed_transaction: <dict> Signed transaction
        :param chain: <list> The blockchain
        :param block_index: <int> Index of a block
        :return: <bool> True if the transaction is valid, False if not
        """

        sender = signed_transaction['sender']
        amount = signed_transaction['amount']

        # Check if the miner rewarded himself more than 10 coins
        if sender == "0":
            if amount < 0 or amount > 10:
                return False
            else:
                return True
        else:
            # Verify the signature of the transaction
            if self.valid_signature(signed_transaction):

                # The transaction is invalid if the amount is negative
                if amount < 0:
                    return False

                # Get the balance of the sender
                balance = self.address_balance_at_block_index(sender, chain, block_index)

                if amount <= balance:
                    return True
                else:
                    return False
            else:
                return False

    @staticmethod
    def valid_signature(signed_transaction):
        """
        Verify the signature of a signed transaction.
        :param signed_transaction: <dict> Signed transaction contains sender, recipient, amount and signature
        :return: <bool> True if the signature is valid, False if not
        """

        transaction_content = {
            'sender': signed_transaction['sender'],
            'recipient': signed_transaction['recipient'],
            'amount': signed_transaction['amount']
        }

        # Order the transaction to avoid inconsistent hashes
        transaction_encoded = json.dumps(transaction_content, sort_keys=True).encode()
        transaction_hash = hashlib.sha256(transaction_encoded).hexdigest()

        signature = signed_transaction['signature']

        # Get the public key of the sender which is needed for the verification
        public_key_sender = ecdsa_recover(transaction_hash, signature)

        return ecdsa_verify(transaction_hash, signature, public_key_sender)

    @staticmethod
    def address_balance_at_block_index(address, chain, block_index):
        """
        Calculate the balance of an address up to a certain block
        index by adding inputs to the balance and subtracting outputs.
        :param address: <str> Address
        :param chain: <list> The blockchain
        :param block_index: <int> The index of a block
        :return: balance: <int> Balance of an address
        """

        index = 1
        balance = 0

        while index < block_index:
            current_block = chain[index]
            if current_block['transactions']:
                transactions = current_block['transactions']
                for current_transaction in transactions:
                    if current_transaction['sender'] == address:
                        balance -= current_transaction['amount']
                    if current_transaction['recipient'] == address:
                        balance += current_transaction['amount']

            index += 1

        return balance

    @staticmethod
    def address_transactions_at_block_index(address, chain, block_index):
        """
        Get the send and received transactions of an address up to a
        certain block index and calculate the number of transactions
        :param address: <str> Address
        :param chain: <list> The blockchain
        :param block_index: <int> The index of a block
        :return: number_of_transactions: <int> Total number of transactions,
        send_transactions: <list> List of send transactions,
        received_transactions: <list> List of received transactions
        """
        index = 1
        number_of_transactions = 0
        send_transactions = []
        received_transactions = []

        while index < block_index:
            current_block = chain[index]
            if current_block['transactions']:
                transactions = current_block['transactions']
                for current_transaction in transactions:
                    if current_transaction['sender'] == address:
                        send_transactions.append(current_transaction)
                        number_of_transactions += 1
                    elif current_transaction['recipient'] == address:
                        received_transactions.append(current_transaction)
                        number_of_transactions += 1

            index += 1

        return number_of_transactions, send_transactions, received_transactions
