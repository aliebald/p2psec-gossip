import argparse
import asyncio

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


async def main():
    (path,) = parse_arguments()
    print("Starting gossip. Path: \"{}\"".format(path))
    config = Config(path)
    config.print_config()
    await Gossip(config).run()


if __name__ == "__main__":
    asyncio.run(main())
