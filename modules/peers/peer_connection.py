import socket
from random import getrandbits

from modules.peers.peer_package_parser import (
    PEER_DISCOVERY,
    PEER_OFFER,
    get_header_type,
    pack_peer_discovery
)


class Peer_connection:
    """Peer_connection represents a connection to a single peer. """

    def __init__(self, connection):
        """
        Arguments:
            connection -- open socket connected to a peer
        """
        self.connection = connection

    def run(self):
        """Waits for incoming messages and handles them."""
        while True:
            msg = self.connection.recv(4096)  # TODO buffersize?
            self.__handle_incoming_msg(msg)

    def send_peer_discovery(self):
        """Sends a peer discovery message."""
        # TODO Save challenge to check it in response
        challenge = getrandbits(64)
        message = pack_peer_discovery(challenge)
        self.connection.send(message)

    def __handle_incoming_msg(self, msg):
        """Handles an incoming message from a peer

        Arguments:
            msg -- received message
        """
        type = get_header_type(msg)
        if type == PEER_DISCOVERY:
            print("Received PEER_DISCOVERY")
            self.__handle_peer_discovery(msg)
        elif type == PEER_OFFER:
            print("Received PEER_OFFER")
            self.__handle_peer_offer(msg)
        else:
            print("Received message with unknown type", type)

    def __handle_peer_discovery(self, msg):
        # TODO implement
        pass

    def __handle_peer_offer(self, msg):
        # TODO implement
        pass


def peer_connection_factory(addresses):
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
        peers.append(Peer_connection(connection))

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
