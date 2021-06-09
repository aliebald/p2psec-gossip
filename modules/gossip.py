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
        (_, p2p_listening_port) = self.config.p2p_address.split(":")
        if len(config.known_peers) > 0:
            self.peers = peer_connection_factory(
                config.known_peers, self, int(p2p_listening_port))

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
        print("New peer connected", new_peer.get_peer_address())
        self.peers.append(new_peer)
        Thread(target=new_peer.run).start()

    def offer_peers(self, peer_addresses):
        """Offers peer_addresses to this gossip class. Gets called after a peer
        offer was received.

        Arguments:
            peer_addresses -- List of strings with format: <host_ip>:<port>
        """
        # remove already connected peers
        connected = self.get_peer_addresses()
        candidates = list(filter(lambda x: x not in connected, peer_addresses))

        print("Offer contained:", peer_addresses)
        print("Connect to:", candidates)

        # Open a connection to new Peers
        if len(candidates) > 0:
            (_, p2p_listening_port) = self.config.p2p_address.split(":")
            new_peers = peer_connection_factory(
                candidates, self, int(p2p_listening_port))
            self.peers += new_peers
            # start new peers
            for peer in self.peers:
                Thread(target=peer.run()).start()

    def get_peer_addresses(self):
        """Returns the p2p listening addresses of all known peers in a list

        Returns:
            List of strings with format: <host_ip>:<port>
        """
        addresses = []
        for peer in self.peers:
            addresses.append(peer.get_peer_p2p_listening_address())
        return list(filter(lambda x: x != None, addresses))

    def __run_peer_control(self):
        """Ensures that self.peers has at least self.config.degree many peers
        """
        search_cooldown = self.config.search_cooldown / 1000
        time.sleep(search_cooldown)

        while True:
            if len(self.peers) < self.config.degree:
                print("\r\nLooking for new Peers")
                print("Connected peers: {}".format(self.get_peer_addresses()))
                # Send PeerDiscovery
                for peer in self.peers:
                    print("  sending peer discovery to",
                          peer.get_peer_address())
                    peer.send_peer_discovery()
            time.sleep(search_cooldown)
