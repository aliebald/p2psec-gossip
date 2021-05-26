import time
from threading import Thread

from modules.peers.peer_connection import Peer_connection, peer_connection_factory
from modules.config import Config


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

        # TODO start APIConnectionHandler

    # Ensures that self.peers has at least self.config.degree many peers
    def __run_peer_control(self):
        search_cooldown = self.config.search_cooldown / 60000
        time.sleep(search_cooldown)

        while True:
            if len(self.peers) < self.config.degree:
                print("Looking for new Peers")
                # TODO Send PeerDiscovery

                # TODO Open a connection to new Peers

            time.sleep(search_cooldown)
