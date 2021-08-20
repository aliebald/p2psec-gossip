import os
import sys
import argparse
import asyncio
import logging

from modules.config import Config
from modules.gossip import Gossip


def parse_arguments():
    """Parses command line arguments
    Returns:
       tuple with the following entries:
       - path to config, either from commandline or the default: "./config.ini"
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
    args = parser.parse_args()

    path = args.path if args.path else "./config.ini"

    return (path,)


def setup_logger(level):
    """Initiates the logger
    Arguments:
        - level: Logging level. Must be a valid level.
                 See https://docs.python.org/3/howto/logging.html for more info
    """
    # Add ".%(msecs)03d" after the time for ms
    format = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=level,
                        format=format,
                        datefmt="%H:%M:%S")


async def main():
    # This script requires Python version 3.9 or newer to run
    if not sys.version_info >= (3, 9):
        raise EnvironmentError("Python version 3.9 or newer is required. "
                               f"(detected: {sys.version})")
    os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))

    # Setup Logger. Change logging level here!
    setup_logger(logging.DEBUG)

    (path,) = parse_arguments()
    logging.info(f"Starting Gossip. Config path: \"{path}\"")
    config = Config(path)
    logging.info(config)
    await Gossip(config).run()


if __name__ == "__main__":
    asyncio.run(main())
