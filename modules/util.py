"""This module provides utility functions that don't fit elsewhere."""
# TODO: move PoW Generator here

import queue
import logging
import hashlib
import time


# FIFO Queue which will not add duplicates
# Source: https://stackoverflow.com/a/16506527
# Hint: To get the length: "qsize()" function.
class Setqueue(queue.Queue):
    def __str__(self):
        return str(list(self.queue))

    def __repr__(self):
        return str(list(self.queue))

    # Use a set as a basis to avoid duplicates
    def _init(self, maxsize):
        self.queue = set()

    def _put(self, item):
        self.queue.add(item)

    def _get(self):
        return self.queue.pop()

    def contains(self, item):
        with self.mutex:
            return item in self.queue


def produce_pow_peer_offer(data):
    """Attempts to find a valid nonce for a peer offer message.

    Arguments:
    - data (byte-object): peer offer package

    Returns:
        Copy of input data as byte-array with valid nonce if found or
        None if no nonce was found.
    """
    start = time.time()
    max = 2**64
    data_copy = bytearray(len(data))
    data_copy[:] = data
    logging.debug("searching for nonce")
    for nonce in range(max):
        data_copy[12:20] = nonce.to_bytes(8, 'big')
        if valid_nonce_peer_offer(data_copy):
            logging.debug(f"Found nonce after {time.time()-start} seconds")
            return data_copy
    logging.warning(f"Failed to find nonce after {time.time()-start} seconds")
    return None


def valid_nonce_peer_offer(data):
    """Checks if the given peer offer package has a valid nonce.

    Arguments:
    - data (byte-object): peer offer package

    Returns:
        True if the first 16 bits of the SHA256 hash value from the package are
        0.
    """
    hash = hashlib.sha256(data).hexdigest()
    return hash[:4] == '0000'


def valid_nonce_peer_challenge(challenge, nonce):
    """Checks if the given nonce produces a valid hash with the given challenge

    Arguments:
    - challenge (byte-object / int): challenge from peer challenge
    - nonce (byte-object / int): nonce for challenge

    Returns:
        True if the first 16 bits of the SHA256 hash value from the package are
        0.
    """
    if type(challenge) not in [bytes, bytearray]:
        challenge = int(challenge).to_bytes(8, 'big')
    if type(nonce) not in [bytes, bytearray]:
        nonce = int(nonce).to_bytes(8, 'big')

    hash = hashlib.sha256(challenge + nonce).hexdigest()
    return hash[:4] == '0000'


def produce_pow_peer_challenge(challenge):
    """Attempts to find a valid nonce for a peer challenge message.

    Arguments:
    - challenge (byte-object / int): challenge from peer challenge

    Returns:
        Valid nonce (int) if found or None if no nonce was found.
    """
    if type(challenge) not in [bytes, bytearray]:
        challenge = int(challenge).to_bytes(8, 'big')

    start = time.time()
    max = 2**64
    logging.debug("searching for nonce")
    for nonce in range(max):
        if valid_nonce_peer_challenge(challenge, nonce):
            logging.debug(f"Found nonce after {time.time()-start} seconds")
            return nonce
    logging.warning(f"Failed to find nonce after {time.time()-start} seconds")
    return None
