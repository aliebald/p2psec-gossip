from threading import Thread
from modules.config import Config
from modules.gossip import Gossip


# Test Function that starts multiple peers with different configs
def test_mode():
    paths = ["./test_configs/config_1.ini",
             "./test_configs/config_2.ini",
             "./test_configs/config_3.ini"]

    for path in paths:
        print("Try to start", path)
        try:
            Thread(target=start_gossip, args=(path, )).start()
        except:
            print("Error: unable to start thread for {}".format(path))


# Reads the config from the given path and starts Gossip
def start_gossip(path):
    print("Starting gossip. Path: \"{}\"".format(path))
    config = Config(path)
    config.print_config()
    Gossip(config)


def main():
    # TODO read path from command line
    testmode = True

    if testmode:
        test_mode()
    else:
        start_gossip("./config.ini")


if __name__ == "__main__":
    main()
