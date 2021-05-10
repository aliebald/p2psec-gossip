from modules.config import Config

if __name__ == "__main__":
    config = Config("./config.ini")
    config.print_config()
    # The following comments are based on our flow chart and may be outdated at a later point in time
    # TODO Peers in config

    # TODO Ask bootstrapping service for peers if not

    # TODO Build connection to known peers and ask for information
    #      about other peers if required (until we have config.degree peers)

    # TODO Start a Thread for each active peer and start: Peers -> PeerConnection (or use async features instead of threads?)
    # TODO start APIConnectionHandler
