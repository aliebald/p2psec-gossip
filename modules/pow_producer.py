"""
This module provides functions to find nonces as proof of work for specific
packages
"""
import logging
import hashlib
import time


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
