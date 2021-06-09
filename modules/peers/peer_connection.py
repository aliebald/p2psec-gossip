import socket
import time
from random import getrandbits

from modules.peers.peer_packet_parser import (
    PEER_DISCOVERY,
    PEER_OFFER,
    PEER_INFO,
    get_header_type,
    pack_peer_discovery,
    pack_peer_offer,
    pack_peer_info,
    parse_peer_discovery,
    parse_peer_offer,
    parse_peer_info
)


# Timeout for challenges in seconds. After this timeout, a challenge is invalid
CHALLENGE_TIMEOUT = 300


class Peer_connection:
    """Peer_connection represents a connection to a single peer. """

    def __init__(self, connection, gossip, peer_p2p_listening_port=None):
        """
        Arguments:
            connection -- open socket connected to a peer
            gossip -- gossip responsible for this peer
            peer_p2p_listening_port -- Optional: Port the connected peer
                                       accepts new peer connections at
        """
        self.gossip = gossip
        self.connection = connection
        self.peer_p2p_listening_port = peer_p2p_listening_port
        self.last_challenges = []

    def run(self):
        """Waits for incoming messages and handles them."""
        while True:
            buf = self.connection.recv(4096)  # TODO buffersize?
            self.__handle_incoming_message(buf)

    def get_peer_p2p_listening_address(self):
        """Returns the address the connected peer accepts new peer connections
        on.

        Returns:
            If known, p2p listening address of peer in the format host:port,
            otherwise None 

        See also:
        - get_own_address()
        - get_peer_address()
        """
        if self.peer_p2p_listening_port == None:
            return None
        (host, _) = self.connection.getpeername()
        address = "{}:{}".format(host, self.peer_p2p_listening_port)
        return address

    def get_peer_address(self):
        """Returns the address of this peer in the format host:port

        See also:
        - get_own_address()
        - get_peer_p2p_listening_address()
        """
        (host, port) = self.connection.getpeername()
        address = "{}:{}".format(host, port)
        return address

    def get_own_address(self):
        """Returns the address of this peer in the format host:port

        See also:
        - get_peer_address()
        - get_peer_p2p_listening_address()
        """
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
        target_address = self.get_peer_p2p_listening_address()
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
        if type == PEER_DISCOVERY:
            print("\r\nReceived PEER_DISCOVERY from", self.get_peer_address())
            self.__handle_peer_discovery(buf)
        elif type == PEER_OFFER:
            print("\r\nReceived PEER_OFFER from", self.get_peer_address())
            self.__handle_peer_offer(buf)
        elif type == PEER_INFO:
            print("\r\nReceived PEER_INFO from", self.get_peer_address())
            self.__handle_peer_info(buf)
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

    def __handle_peer_info(self, buf):
        """Handles a peer info message. Saves the received p2p_listening_port.

        Arguments:
            buf -- received message in byte format. The type must be 
                   PEER_INFO
        """
        msg = parse_peer_info(buf)
        if msg == None:
            return
        (size, type, port) = msg

        # check if we already know the p2p_listening_port of the other peer
        if self.peer_p2p_listening_port != None:
            warning = ("WARNING: received PEER INFO but already knew the"
                       "p2p_listening_port!\r\nOld port: {}, new Port: {}")
            print(warning.format(self.peer_p2p_listening_port, port))

        # save new port
        print("Saving p2p_listening_port", port)
        self.peer_p2p_listening_port = port


def peer_connection_factory(addresses, gossip, p2p_listening_port):
    """Connects to multiple addresses of peers.

    Arguments:
        addresses -- list containing addresses to other peers including port
        gossip -- gossip instance responsible for potential Peer_connection's
        p2p_listening_port -- Port this peer accepts new peer connections at
    Returns:
        List containing Peer_connection objects. Empty if no connection can
        be established
    """
    connections = []
    peers = []
    # TODO potentially use asyncio or multithreading here.
    for address in addresses:
        (ip, port) = address.split(":")
        connection = __connect_peer(ip, port, p2p_listening_port)
        # Create a Peer_connection if the connection was successfull
        if connection != None:
            peers.append(Peer_connection(connection, gossip, port))

    return peers


def __connect_peer(ip, port, p2p_listening_port):
    """Opens a connection to the given ip & port.

    Arguments:
       ip -- target ip address
       port -- target port
       p2p_listening_port -- Port this peer accepts new peer connections at

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

    __send_peer_info(connection, p2p_listening_port)
    print("Successfully connected to ip: {}, port: {}".format(ip, port))
    return connection


def __send_peer_info(connection, p2p_listening_port):
    """Sends a PEER INFO message with p2p_listening_port to the given 
    connection

    Arguments:
       connection -- socket connected to a new peer
       p2p_listening_port -- Port this peer accepts new peer connections at
    """
    info_packet = pack_peer_info(p2p_listening_port)
    print("Sending PEER INFO with p2p port {} to {}".format(
        p2p_listening_port, connection.getpeername()))
    connection.send(info_packet)
