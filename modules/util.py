"""This module provides utility functions that don't fit elsewhere.
Contains Setqueue class / datastructure and proof of work (pow) functions for
peer challenge.

The parse_address function provided in this module can be used to
parse IPv4 or IPv6 addresses with port into a tuple (See parse_address).
To validate ip addresses, is_valid_address can be used
"""

import queue
import logging
import hashlib
import time
import ipaddress


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


def parse_address(address):
    """Parses an IPv4 or IPv6 followed by a port (format: <ip>:<port>, can
    contain '[' or ']').
    Returns a tuple with (address -- str, port -- int).

    Throws an ValueError if the given address is invalid.
    """
    address = address.replace("[", "").replace("]", "")
    split_at = address.rindex(':')
    return (address[:split_at], int(address[split_at+1:]))


def is_valid_address(address):
    """Checks if the given ip is in a valid format for the config.
    Format: <ip_address>:<port> (can contain '[' or ']').
    """
    def __is_valid_port(port):
        if len(str(port)) == 0:
            return False
        try:
            int(port)
        except ValueError:
            return False
        return int(port) <= 2**16-1

    try:
        ip, port = parse_address(address)
        ipaddress.ip_address(ip)
    except ValueError:
        return False

    return __is_valid_port(port)


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
    return hash[:6] == '000000'


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
