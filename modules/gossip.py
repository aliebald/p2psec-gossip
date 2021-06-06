import time
from threading import Thread

from modules.peers.peer_connection import Peer_connection, peer_connection_factory
from modules.connection_handler import connection_handler


class Gossip:
    def __init__(self, config):
        print("gossip")
        self.config = config
        print()
        self.peers = []

        # connect to peers in config
        if len(config.known_peers) > 0:
            self.peers = peer_connection_factory(config.known_peers)

        # TODO Ask bootstrapping service for peers if no peers where in the
        #      config or all peers from config where unreachable.

        Thread(target=self.__run_peer_control).start()

        # TODO Start a Thread for each active peer and start: Peers ->
        #      PeerConnection (or use async features instead of threads?)

        # start APIConnectionHandler
        (host, port) = config.p2p_address.split(":")
        print("Opening Peer server at host: {}, port: {}".format(host, port))
        Thread(target=connection_handler, args=(
            host, int(port), self.__on_peer_connection)).start()

    def __on_peer_connection(self, socket):
        """Gets called when a new peer tries to connect to APIConnectionHandler
        Arguments:
            socket -- socket connected to the peer
        """
        print("New client connected", socket)
        # TODO implementation

    def __run_peer_control(self):
        """Ensures that self.peers has at least self.config.degree many peers
        """
        search_cooldown = self.config.search_cooldown / 1000
        print("search_cooldown = {} ({}), self.config.search_cooldown = {} ({})".format(
            search_cooldown, type(search_cooldown), self.config.search_cooldown, type(self.config.search_cooldown)))
        time.sleep(search_cooldown)

        while True:
            if len(self.peers) < self.config.degree:
                print("Looking for new Peers")
                # TODO Send PeerDiscovery

                # TODO Open a connection to new Peers

            time.sleep(search_cooldown)
