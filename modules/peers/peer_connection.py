import socket
import time
from random import getrandbits

from modules.peers.peer_packet_parser import (
    PEER_DISCOVERY,
    PEER_OFFER,
    get_header_type,
    pack_peer_discovery,
    pack_peer_offer,
    parse_peer_discovery,
    parse_peer_offer
)


# Timeout for challenges in seconds. After this timeout, a challenge is invalid
CHALLENGE_TIMEOUT = 300


class Peer_connection:
    """Peer_connection represents a connection to a single peer. """

    def __init__(self, connection, gossip):
        """
        Arguments:
            connection -- open socket connected to a peer
            gossip -- gossip responsible for this peer
        """
        self.gossip = gossip
        self.connection = connection
        self.last_challenges = []

    def run(self):
        """Waits for incoming messages and handles them."""
        while True:
            buf = self.connection.recv(4096)  # TODO buffersize?
            self.__handle_incoming_message(buf)

    def get_peer_address(self):
        """Returns the address of this peer in the format host:port"""
        (host, port) = self.connection.getpeername()
        address = "{}:{}".format(host, port)
        return address

    def get_own_address(self):
        """Returns the address of this peer in the format host:port"""
        (host, port) = self.connection.getsockname()
        address = "{}:{}".format(host, port)
        return address

    def send_peer_discovery(self):
        """Sends a peer discovery message."""
        message = pack_peer_discovery(self.__generate_challenge())
        self.connection.send(message)

    def __send_peer_offer(self, challenge):
        """Figures out a nonce and sends a peer offer.

        Arguments:
            challenge -- challenge received from original peer discovery
        """
        nonce = 0  # TODO find nonce
        # Use target_address to filter the address of the target peer
        target_address = self.get_peer_address()
        addresses = list(filter(lambda ip: ip != target_address,
                         self.gossip.get_peer_addresses()))
        # Abort if we do not know any other peers
        if len(addresses) == 0:
            print("No other peers connected, do not send peer offer.")
            return
        print("responding with peers: {}\r\n".format(addresses))
        message = pack_peer_offer(challenge, nonce, addresses)
        self.connection.send(message)

    def __generate_challenge(self):
        """Generates and saves a single use challenge"""
        challenge = getrandbits(64)
        timeout = time.time() + CHALLENGE_TIMEOUT
        self.last_challenges.append((challenge, timeout))
        return challenge

    def __check_challenge(self, challenge):
        """Checks if the given challenge was send from this peer and has not
        yet expired. Also removes the challenge from the saved challenges.

        Arguments:
            challenge -- challenge to check

        Returns:
            True if the challenge is valid and has not expired.
        """
        for (saved_challenge, timeout) in self.last_challenges:
            if saved_challenge == challenge:
                self.last_challenges.remove((saved_challenge, timeout))
                return timeout >= time.time()
        return False

    def __handle_incoming_message(self, buf):
        """Handles an incoming message in byte format from a peer

        Arguments:
            buf -- received message in byte format
        """
        type = get_header_type(buf)
        print(self.get_own_address(), "received:")
        if type == PEER_DISCOVERY:
            print("\r\nReceived PEER_DISCOVERY from", self.get_peer_address())
            self.__handle_peer_discovery(buf)
        elif type == PEER_OFFER:
            print("\r\nReceived PEER_OFFER from", self.get_peer_address())
            self.__handle_peer_offer(buf)
        else:
            print("\r\nReceived message with unknown type {} from {}".format(
                type, self.get_peer_address()))

    def __handle_peer_discovery(self, buf):
        """Handles a peer discovery message and calls __send_peer_offer() to
        send a response.

        Arguments:
            buf -- received message in byte format. The type must be 
                   PEER_DISCOVERY
        """
        msg = parse_peer_discovery(buf)
        if (msg == None):
            return

        (size, type, challenge) = msg
        self.__send_peer_offer(challenge)

    def __handle_peer_offer(self, buf):
        msg = parse_peer_offer(buf)
        if (msg == None):
            return
        (size, type, challenge, nonce, data) = msg
        # Check for invalid challenge
        if not self.__check_challenge(challenge):
            print("Received invalid challenge in peer offer")
            return

        # TODO check nonce

        # check if the offer contains our own address
        p2p_address = self.gossip.config.p2p_address
        if p2p_address in data:
            print("WARNING: own p2p address found in peer offer!")
            data = list(filter(lambda ip: ip != p2p_address, data))

        # save data / pass it to gossip
        self.gossip.offer_peers(data)


def peer_connection_factory(addresses, gossip):
    """Connects to multiple addresses of peers.

    Arguments:
        addresses -- list containing addresses to other peers including port
    Returns:
        List containing Peer_connection objects. Empty if no connection can
        be established
    """
    connections = []
    peers = []
    # TODO potentially use asyncio or multithreading here.
    for address in addresses:
        (ip, port) = address.split(":")
        connections.append(__connect_peer(ip, port))

    connections = list(filter(None, connections))
    for connection in connections:
        peers.append(Peer_connection(connection, gossip))

    return peers


def __connect_peer(ip, port):
    """Opens a connection to the given ip & port.

    Arguments:
       ip -- target ip address
       port -- target port

    Returns:
        None if failed to open the connection. Otherwise the socket with the
        connection.
    """
    # open socket
    print("connecting to ip: {}, port: {}".format(ip, port))
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        connection.connect((ip, int(port)))
    except ConnectionRefusedError:
        print("Failed to connect to ip: {}, port: {}".format(ip, port))
        print()
        return

    print("Successfully connected to ip: {}, port: {}".format(ip, port))
    return connection
