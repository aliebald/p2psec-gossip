import socket


class Peer_connection:
    """Peer_connection represents a connection to a single peer. """

    def __init__(self, connection):
        """
        Arguments:
            connection -- open socket connected to a peer
        """
        self.connection = connection

    # TODO implement required functionality


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
