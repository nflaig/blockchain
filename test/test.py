from bitcoin import *
from unittest import TestCase
from time import time


from src.blockchain import Blockchain
from src.wallet import Wallet
from src.proof_of_work import ProofOfWork


class MainTestCase(TestCase):
    def setUp(self):
        self.blockchain = Blockchain()
        self.chain = self.blockchain.chain
        self.mempool = self.blockchain.mempool
        self.network = self.blockchain.network
        self.wallet = Wallet()
        self.initial_address = self.wallet.addresses[0]

    def test_initialize_blockchain(self):
        self.assertEqual(len(self.chain), 1)
        self.assertTrue(self.blockchain.valid_chain(self.chain))
        self.assertFalse(self.mempool.current_transactions)
        self.assertFalse(self.network.nodes)

    def test_initialize_wallet(self):
        self.assertEqual(len(self.wallet.addresses), 1)
        self.assertEqual(len(self.wallet.address_to_keys), 1)
        self.assertEqual(len(self.wallet.address_to_balance), 1)
        self.assertEqual(self.wallet.address_to_balance[self.initial_address], 0)
        self.assertEqual(self.wallet.total_balance(), 0)
        self.assertEqual(privtopub(self.wallet.address_to_keys[self.initial_address][0]),
                         self.wallet.address_to_keys[self.initial_address][1])
        self.assertEqual(pubtoaddr(self.wallet.address_to_keys[self.initial_address][1]),
                         self.initial_address)

    def test_wallet_generate_address(self):
        self.wallet.generate_address()
        new_address = self.wallet.addresses[1]
        self.assertEqual(len(self.wallet.addresses), 2)
        self.assertEqual(len(self.wallet.address_to_keys), 2)
        self.assertEqual(len(self.wallet.address_to_balance), 2)
        self.assertEqual(self.wallet.address_to_balance[new_address], 0)
        self.assertEqual(self.wallet.total_balance(), 0)
        self.assertEqual(privtopub(self.wallet.address_to_keys[new_address][0]),
                         self.wallet.address_to_keys[new_address][1])
        self.assertEqual(pubtoaddr(self.wallet.address_to_keys[new_address][1]),
                         new_address)

    def test_wallet_sign_transaction(self):
        signed_transaction = self.wallet.sign_transaction(self.initial_address,
                                                          '14peaf2JegQP5nmNQESAdpRGLbse8JqgJD', 0)
        signature = signed_transaction['signature']
        transaction_content = {
            'sender': self.initial_address,
            'recipient': '14peaf2JegQP5nmNQESAdpRGLbse8JqgJD',
            'amount': 0
        }
        transaction_encoded = json.dumps(transaction_content, sort_keys=True).encode()
        transaction_hash = hashlib.sha256(transaction_encoded).hexdigest()

        self.assertEqual(signature, ecdsa_sign(transaction_hash, self.wallet.address_to_keys[self.initial_address][0]))

    def test_proof_of_work(self):
        transactions_hash = self.mempool.hash([])
        previous_block_hash = self.blockchain.hash(self.blockchain.last_block)
        nonce = ProofOfWork.proof_of_work(transactions_hash, previous_block_hash)

        encoded = f'{transactions_hash}{previous_block_hash}{nonce}'.encode()
        hashed = hashlib.sha256(encoded).hexdigest()

        self.assertEqual(hashed[:4], '0000')
        self.assertTrue(ProofOfWork.valid_proof(transactions_hash, previous_block_hash, nonce))

    def test_proof_of_work_invalid_nonce(self):
        transactions_hash = self.mempool.hash([])
        previous_block_hash = self.blockchain.hash(self.blockchain.last_block)
        nonce = 12345

        self.assertFalse(ProofOfWork.valid_proof(transactions_hash, previous_block_hash, nonce))

    def test_mempool_add_valid_transaction(self):
        signed_transaction = self.wallet.sign_transaction(self.initial_address,
                                                          '14peaf2JegQP5nmNQESAdpRGLbse8JqgJD', 0)

        self.assertTrue(self.mempool.valid_transaction(signed_transaction, self.blockchain))
        self.assertTrue(self.mempool.add_transaction(signed_transaction, self.blockchain))
        self.assertEqual(len(self.mempool.current_transactions), 1)

    def test_mempool_add_invalid_transaction(self):
        # too high amount of coins
        invalid_transaction = self.wallet.sign_transaction(self.initial_address,
                                                           '14peaf2JegQP5nmNQESAdpRGLbse8JqgJD', 10)

        self.assertFalse(self.mempool.valid_transaction(invalid_transaction, self.blockchain))
        self.assertFalse(self.mempool.add_transaction(invalid_transaction, self.blockchain))
        self.assertEqual(len(self.mempool.current_transactions), 0)

        # negative amount of coins
        invalid_transaction = self.wallet.sign_transaction(self.initial_address,
                                                           '14peaf2JegQP5nmNQESAdpRGLbse8JqgJD', -1)

        self.assertFalse(self.mempool.valid_transaction(invalid_transaction, self.blockchain))
        self.assertFalse(self.mempool.add_transaction(invalid_transaction, self.blockchain))
        self.assertEqual(len(self.mempool.current_transactions), 0)

        # invalid signature
        invalid_transaction = {
            'sender': self.initial_address,
            'recipient': '14peaf2JegQP5nmNQESAdpRGLbse8JqgJD',
            'amount': 0,
            'signature': 'GwQr4EOfrRUicb34fgB9ix69PNa8nMjSXEgZfBRFha9tWQCvgaWco5v8JlIU89WDHLX6gTLHn9qIIEaV0mzxFoM='
        }

        self.assertFalse(self.mempool.valid_transaction(invalid_transaction, self.blockchain))
        self.assertFalse(self.mempool.add_transaction(invalid_transaction, self.blockchain))
        self.assertEqual(len(self.mempool.current_transactions), 0)

    def test_register_node(self):
        self.network.register_node('http://192.168.0.1:5000')

        self.assertIn('192.168.0.1:5000', self.network.nodes)
        self.assertEqual(len(self.network.nodes), 1)

    def test_register_duplicate_node(self):
        self.network.register_node('http://192.168.0.1:5000')
        self.network.register_node('http://192.168.0.1:5000')

        self.assertEqual(len(self.network.nodes), 1)

    def test_register_invalid_node(self):
        self.network.register_node('http//192.168.0.1:5000')
        self.assertNotIn('192.168.0.1:5000', self.network.nodes)
        self.assertEqual(len(self.network.nodes), 0)

    def test_create_block(self):
        signed_transaction = self.wallet.sign_transaction(self.initial_address,
                                                          '14peaf2JegQP5nmNQESAdpRGLbse8JqgJD', 0)
        self.mempool.add_transaction(signed_transaction, self.blockchain)
        transactions_hash = self.mempool.hash(self.mempool.current_transactions)
        previous_block_hash = self.blockchain.hash(self.blockchain.last_block)
        nonce = ProofOfWork.proof_of_work(transactions_hash, previous_block_hash)
        self.blockchain.create_block(nonce, previous_block_hash, self.mempool.current_transactions)
        created_block = self.blockchain.last_block

        self.assertEqual(len(self.blockchain.chain), 2)
        self.assertEqual(created_block, self.blockchain.chain[-1])
        self.assertEqual(created_block['index'], 2)
        self.assertIsNotNone(created_block['timestamp'])
        self.assertEqual(created_block['nonce'], nonce)
        self.assertEqual(created_block['transactions_hash'], transactions_hash)
        self.assertEqual(created_block['previous_block_hash'], previous_block_hash)
        self.assertEqual(created_block['transactions'], [signed_transaction])
        self.assertEqual(len(self.mempool.current_transactions), 0)

    def test_block_hash(self):
        signed_transaction = self.wallet.sign_transaction(self.initial_address,
                                                          '14peaf2JegQP5nmNQESAdpRGLbse8JqgJD', 0)
        self.mempool.add_transaction(signed_transaction, self.blockchain)
        transactions_hash = self.mempool.hash(self.mempool.current_transactions)
        previous_block_hash = self.blockchain.hash(self.blockchain.last_block)
        nonce = ProofOfWork.proof_of_work(transactions_hash, previous_block_hash)
        self.blockchain.create_block(nonce, previous_block_hash, self.mempool.current_transactions)
        created_block = self.blockchain.last_block

        block_encoded = json.dumps(created_block, sort_keys=True).encode()
        block_hash = hashlib.sha256(block_encoded).hexdigest()

        self.assertEqual(len(self.blockchain.hash(created_block)), 64)
        self.assertEqual(self.blockchain.hash(created_block), block_hash)

    def test_valid_chain(self):
        signed_transaction = self.wallet.sign_transaction(self.initial_address,
                                                          '14peaf2JegQP5nmNQESAdpRGLbse8JqgJD', 0)
        self.mempool.add_transaction(signed_transaction, self.blockchain)
        transactions_hash = self.mempool.hash(self.mempool.current_transactions)
        previous_block_hash = self.blockchain.hash(self.blockchain.last_block)
        nonce = ProofOfWork.proof_of_work(transactions_hash, previous_block_hash)
        self.blockchain.create_block(nonce, previous_block_hash, self.mempool.current_transactions)

        self.assertTrue(self.blockchain.valid_chain(self.blockchain.chain))

    def test_valid_chain_transactions(self):
        # Mine 10 coins to initial_address
        coinbase_transaction = {
            'sender': '0',
            'recipient': self.initial_address,
            'amount': 10
        }
        transactions_hash = self.mempool.hash([coinbase_transaction])
        previous_block_hash = self.blockchain.hash(self.blockchain.last_block)
        nonce = ProofOfWork.proof_of_work(transactions_hash, previous_block_hash)
        self.blockchain.create_block(nonce, previous_block_hash, [coinbase_transaction])

        # Spend the mined coins
        signed_transaction = self.wallet.sign_transaction(self.initial_address,
                                                          '14peaf2JegQP5nmNQESAdpRGLbse8JqgJD', 10)
        self.mempool.add_transaction(signed_transaction, self.blockchain)
        transactions_hash = self.mempool.hash(self.mempool.current_transactions)
        previous_block_hash = self.blockchain.hash(self.blockchain.last_block)
        nonce = ProofOfWork.proof_of_work(transactions_hash, previous_block_hash)
        self.blockchain.create_block(nonce, previous_block_hash, self.mempool.current_transactions)

        self.assertTrue(self.blockchain.valid_chain(self.blockchain.chain))

    def test_invalid_chain_prev_block_hash(self):
        signed_transaction = self.wallet.sign_transaction(self.initial_address,
                                                          '14peaf2JegQP5nmNQESAdpRGLbse8JqgJD', 0)
        transactions_hash = self.mempool.hash(self.mempool.current_transactions)
        previous_block_hash = self.blockchain.hash(self.blockchain.last_block)
        nonce = ProofOfWork.proof_of_work(transactions_hash, previous_block_hash)

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'nonce': nonce,
            'transactions_hash': transactions_hash,
            'previous_block_hash': '12345',
            'transactions': [signed_transaction]
        }

        self.blockchain.chain.append(block)

        self.assertFalse(self.blockchain.valid_chain(self.blockchain.chain))

    def test_invalid_chain_nonce(self):
        signed_transaction = self.wallet.sign_transaction(self.initial_address,
                                                          '14peaf2JegQP5nmNQESAdpRGLbse8JqgJD', 0)
        transactions_hash = self.mempool.hash(self.mempool.current_transactions)
        previous_block_hash = self.blockchain.hash(self.blockchain.last_block)

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'nonce': 12345,
            'transactions_hash': transactions_hash,
            'previous_block_hash': previous_block_hash,
            'transactions': [signed_transaction]
        }

        self.blockchain.chain.append(block)

        self.assertFalse(self.blockchain.valid_chain(self.blockchain.chain))

    def test_invalid_chain_coinbase_transaction_amount(self):
        coinbase_transaction = {
            'sender': '0',
            'recipient': self.initial_address,
            'amount': 100
        }
        transactions_hash = self.mempool.hash([coinbase_transaction])
        previous_block_hash = self.blockchain.hash(self.blockchain.last_block)
        nonce = ProofOfWork.proof_of_work(transactions_hash, previous_block_hash)

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'nonce': nonce,
            'transactions_hash': transactions_hash,
            'previous_block_hash': previous_block_hash,
            'transactions': [coinbase_transaction]
        }

        self.blockchain.chain.append(block)

        self.assertFalse(self.blockchain.valid_chain(self.blockchain.chain))

    def test_invalid_chain_coinbase_transaction_duplicate(self):
        coinbase_transaction = {
            'sender': '0',
            'recipient': self.initial_address,
            'amount': 10
        }
        transactions_hash = self.mempool.hash([coinbase_transaction, coinbase_transaction])
        previous_block_hash = self.blockchain.hash(self.blockchain.last_block)
        nonce = ProofOfWork.proof_of_work(transactions_hash, previous_block_hash)

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'nonce': nonce,
            'transactions_hash': transactions_hash,
            'previous_block_hash': previous_block_hash,
            'transactions': [coinbase_transaction, coinbase_transaction]
        }

        self.blockchain.chain.append(block)

        self.assertFalse(self.blockchain.valid_chain(self.blockchain.chain))

    def test_invalid_chain_transactions(self):
        # Mine 10 coins to initial_address
        coinbase_transaction = {
            'sender': '0',
            'recipient': self.initial_address,
            'amount': 10
        }
        transactions_hash = self.mempool.hash([coinbase_transaction])
        previous_block_hash = self.blockchain.hash(self.blockchain.last_block)
        nonce = ProofOfWork.proof_of_work(transactions_hash, previous_block_hash)
        self.blockchain.create_block(nonce, previous_block_hash, [coinbase_transaction])

        # Include a transaction in block with to much coins spent
        signed_transaction = self.wallet.sign_transaction(self.initial_address,
                                                          '14peaf2JegQP5nmNQESAdpRGLbse8JqgJD', 100)
        self.mempool.current_transactions.append(signed_transaction)
        transactions_hash = self.mempool.hash(self.mempool.current_transactions)
        previous_block_hash = self.blockchain.hash(self.blockchain.last_block)
        nonce = ProofOfWork.proof_of_work(transactions_hash, previous_block_hash)
        self.blockchain.create_block(nonce, previous_block_hash, self.mempool.current_transactions)

        self.assertFalse(self.blockchain.valid_chain(self.blockchain.chain))
