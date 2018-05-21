import hashlib


class ProofOfWork:
    @staticmethod
    def proof_of_work(transactions_hash, previous_block_hash):
        """
        Simple Proof of Work algorithm based on the hash of the transactions included in this block and the last block.
        Try a different nonce (brute-force search) until a valid hash is found.
        :param transactions_hash: <int> Hash of the transactions
        :param previous_block_hash: <str> Hash of the previous block
        :return: nonce: <int> Valid nonce
        """

        nonce = 0
        while ProofOfWork.valid_proof(transactions_hash, previous_block_hash, nonce) is False:
            nonce += 1

        return nonce

    @staticmethod
    def valid_proof(transactions_hash, previous_block_hash, nonce):
        """
        Validates the proof by requiring the hash to have at least 4 leading zeroes.
        :param transactions_hash: <int> Hash of the transactions
        :param previous_block_hash: <str> Hash of the previous block
        :param nonce: <int> Current nonce
        :return: <bool> True if correct, False if not.
        """

        encoded = f'{transactions_hash}{previous_block_hash}{nonce}'.encode()
        hashed = hashlib.sha256(encoded).hexdigest()
        return hashed[:4] == "0000"
