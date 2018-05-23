from flask import Flask, jsonify, request
from urllib.parse import urlparse

from src.blockchain import Blockchain
from src.proof_of_work import ProofOfWork
from src.wallet import Wallet

# Instantiate Node
node = Flask(__name__)

# Instantiate the blockchain
blockchain = Blockchain()

# Instantiate wallet
wallet = Wallet()


@node.route('/wallet/check_balance', defaults={'address': None}, methods=['GET'])
@node.route('/wallet/check_balance/<address>', methods=['GET'])
def balance(address):
    # Update the balance of our wallet
    wallet.update_balances(blockchain.chain)

    if address:
        # Return the balance of a specific address
        if address in wallet.addresses:
            response = {
                'balance': wallet.address_to_balance[address]
            }
            return jsonify(response), 200
        else:
            return 'Invalid address', 400
    else:
        # Return the total balance of the wallet
        response = {
            'balances': wallet.address_to_balance,
            'total_balance': wallet.total_balance()
        }
        return jsonify(response), 200


@node.route('/wallet/new', methods=['GET'])
def new_address():
    # Generate a new address
    response = {
        'new_address': wallet.generate_address()
    }
    return jsonify(response), 200


@node.route('/wallet', defaults={'address': None}, methods=['GET'])
@node.route('/wallet/<address>', methods=['GET'])
def address_key_pair(address):
    if address:
        # Return the key pair for a specific address
        if address in wallet.addresses:
            response = {
                'private_key': wallet.address_to_keys[address][0],
                'public_key': wallet.address_to_keys[address][1]
            }
            return jsonify(response), 200
        else:
            return 'Invalid address!', 400
    else:
        # Return the key pairs for all existing addresses
        response = {
            'addresses_with_key_pairs': wallet.address_to_keys
        }
        return jsonify(response), 200


@node.route('/transaction/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check if the data of the POST request is valid
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values!', 400

    signed_transaction = wallet.sign_transaction(values['sender'], values['recipient'], values['amount'])

    if not signed_transaction:
        return 'Unable to sign the transaction!', 400

    if not blockchain.mempool.add_transaction(signed_transaction, blockchain):
        return 'Transaction is invalid!', 400

    response = {
        'message': "Transaction was added to the mempool and will be included in the next block",
        'transaction': signed_transaction
    }
    return jsonify(response), 201


@node.route('/mine', methods=['GET'])
def mine():
    # Create a coinbase transaction to collect the block reward (10 coins) the address of the sender has to be "0"
    coinbase_transaction = {
        'sender': '0',
        'recipient': wallet.addresses[0],
        'amount': 10,
        'signature': 'coinbase transaction'
    }

    # Include all transactions of the mempool in the next block including the coinbase transaction
    transactions_of_block = blockchain.mempool.current_transactions
    transactions_of_block.append(coinbase_transaction)

    # Run the Proof of Work algorithm to find a valid nonce for the block
    previous_block = blockchain.last_block
    previous_block_hash = blockchain.hash(previous_block)
    transactions_hash = blockchain.mempool.hash(transactions_of_block)
    nonce = ProofOfWork.proof_of_work(transactions_hash, previous_block_hash)

    # Create the new block
    block = blockchain.create_block(nonce, previous_block_hash, transactions_of_block)

    response = {
        'message': "New block added to the chain",
        'index': block['index'],
        'timestamp': block['timestamp'],
        'nonce': block['nonce'],
        'transactions_hash': block['transactions_hash'],
        'previous_block_hash': block['previous_block_hash'],
        'transactions': block['transactions']
    }
    return jsonify(response), 200


@node.route('/explorer/<address>', methods=['GET'])
def explorer_address(address):
    last_block_index = len(blockchain.chain)

    balance_of_address = blockchain.address_balance_at_block_index(address, blockchain.chain, last_block_index)
    number, send, received = blockchain.address_transactions_at_block_index(address, blockchain.chain, last_block_index)

    response = {
        'balance': balance_of_address,
        'number_of_transactions': number,
        'send_transactions': send,
        'received_transactions': received
    }
    return jsonify(response), 200


@node.route('/mempool', methods=['GET'])
def mempool():
    response = {
        'mempool': blockchain.mempool.current_transactions,
        'size': len(blockchain.mempool.current_transactions)
    }
    return jsonify(response), 200


@node.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200


@node.route('/node/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')

    new_nodes = []

    if nodes is None:
        return "Invalid list of nodes!", 400

    for current_node in nodes:
        if urlparse(current_node).netloc not in blockchain.network.nodes:
            blockchain.network.register_node(current_node)
            new_nodes.append(urlparse(current_node).netloc)

    if new_nodes:
        response = {
            'message': "New nodes have been registered",
            'new_nodes': new_nodes,
            'total_nodes': list(blockchain.network.nodes)
        }
    else:
        response = {
            'message': "All nodes are already registered",
            'total_nodes': list(blockchain.network.nodes)
        }

    return jsonify(response), 201


@node.route('/node/consensus', methods=['GET'])
def consensus():
    if blockchain.reach_consensus():
        response = {
            'message': f"Chain was replaced by a longer chain with {len(blockchain.chain)} blocks",
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': f"Chain is the currently the longest chain with {len(blockchain.chain)} blocks",
            'chain': blockchain.chain
        }

    return jsonify(response), 200


if __name__ == '__main__':
    port = int(input("Port: "))
    node.run(host='0.0.0.0', port=port)
