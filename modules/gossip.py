import time
from threading import Thread

from modules.peers.peer_connection import (
    Peer_connection, peer_connection_factory)
from modules.connection_handler import connection_handler


class Gossip:
    def __init__(self, config):
        print("gossip")
        self.config = config
        print()
        self.peers = []

        # connect to peers in config
        if len(config.known_peers) > 0:
            self.peers = peer_connection_factory(config.known_peers, self)

        # TODO Ask bootstrapping service for peers if no peers where in the
        #      config or all peers from config where unreachable.

        Thread(target=self.__run_peer_control).start()

        # Start a Thread for each active peer and start: Peers ->
        # PeerConnection (or use async features instead of threads?)
        for peer in self.peers:
            Thread(target=peer.run).start()

        # start PeerConnectionHandler
        (host, port) = config.p2p_address.split(":")
        Thread(target=connection_handler, args=(
            host, int(port), self.__on_peer_connection)).start()

    def __on_peer_connection(self, socket):
        """Gets called when a new peer tries to connect.

        Arguments:
            socket -- socket connected to the peer
        """
        # TODO implement. The current implementation is rather rudimentary
        new_peer = Peer_connection(socket, self)
        print("New peer connected", new_peer.get_address(), "\r\n")
        self.peers.append(new_peer)
        Thread(target=new_peer.run()).start()

    def offer_peers(self, peer_addresses):
        """Offers peer_addresses to this gossip class. Gets called after a peer
        offer was received.

        Arguments:
            peer_addresses -- List of strings with format: <host_ip>:<port>
        """
        # remove already connected peers
        connected = self.get_peer_addresses()
        candidates = list(filter(lambda x: x not in connected, peer_addresses))

        # Open a connection to new Peers
        if len(candidates) > 0:
            new_peers = peer_connection_factory(self.config.known_peers, self)
            self.peers += new_peers
            # start new peers
            for peer in self.peers:
                Thread(target=peer.run()).start()

    def get_peer_addresses(self):
        """Returns the addresses of all known peers in a list

        Returns:
            List of strings with format: <host_ip>:<port>
        """
        addresses = []
        for peer in self.peers:
            addresses.append(peer.get_address())
        return addresses

    def __run_peer_control(self):
        """Ensures that self.peers has at least self.config.degree many peers
        """
        search_cooldown = self.config.search_cooldown / 1000
        time.sleep(search_cooldown)

        while True:
            if len(self.peers) < self.config.degree:
                print("\r\nLooking for new Peers")
                # Send PeerDiscovery
                for peer in self.peers:
                    print("  sending peer discovery to", peer.get_address())
                    peer.send_peer_discovery()
            print("\r\nConnected peers: {}\r\n".format(
                self.get_peer_addresses()))
            time.sleep(search_cooldown)
