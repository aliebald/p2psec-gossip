from modules.config import Config
from modules.gossip import Gossip


# TODO Test Function that starts multiple peers with different configs

def main():
    # TODO read path from command line
    config = Config("./config.ini")
    config.print_config()
    gossip = Gossip(config)


if __name__ == "__main__":
    main()
