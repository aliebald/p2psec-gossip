from modules.peers.peer_connection import Peer_connection, peer_connection_factory
from modules.config import Config


class Gossip:
    def __init__(self):
        self.config = config = Config("./config.ini")
        config.print_config()
        print()
        self.peers = []

        # connect to peers in config
        if len(config.known_peers) > 0:
            self.peers = peer_connection_factory(config.known_peers)

        # TODO Ask bootstrapping service for peers if no peers where in the
        #      config or all peers from config where unreachable.

        # TODO ask for information about other peers if required
        #      (until we have config.degree peers)

        # TODO Start a Thread for each active peer and start: Peers ->
        #      PeerConnection (or use async features instead of threads?)

        # TODO start APIConnectionHandler


if __name__ == "__main__":
    Gossip()
