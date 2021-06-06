from threading import Thread
import argparse

from modules.config import Config
from modules.gossip import Gossip


def test_mode():
    """Test Function that starts multiple peers with different configs"""
    paths = ["./test_configs/config_1.ini",
             "./test_configs/config_2.ini",
             "./test_configs/config_3.ini"]

    for path in paths:
        print("Try to start", path)
        try:
            Thread(target=start_gossip, args=(path, )).start()
        except:
            print("Error: unable to start thread for {}".format(path))


def start_gossip(path):
    """Reads the config from the given path and starts Gossip"""
    print("Starting gossip. Path: \"{}\"".format(path))
    config = Config(path)
    config.print_config()
    Gossip(config)


def parse_arguments():
    """Parses command line arguments
    Returns:
       tuple with the following entries
       path to config, either from commandline or the default: "./config.ini".
    """
    description = (
        "This is the module responsible for spreading information in the "
        "network. Peers spread information that a user is online via this "
        "module. Other modules may base their functionality on this module "
        "a mockup version of this module is provided as part of the testing "
        "module"
    )
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-p", "--path", type=str,
                        help="Path to the desired config file")
    parser.add_argument("-t", "--testmode", action="store_true",
                        help=("start multiple gossip instances using test "
                              "configs (testmode)"))
    args = parser.parse_args()

    path = args.path if args.path else "./config.ini"
    testmode = args.testmode if args.testmode else False

    return (path, testmode)


def main():
    (path, testmode) = parse_arguments()
    if testmode:
        test_mode()
    else:
        start_gossip(path)


if __name__ == "__main__":
    main()
