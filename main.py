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
       - log_level -- level for logging
       - logfile -- None or path to a file, where logging should be written to
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
    parser.add_argument("-l", "--logging", type=str, dest="logging",
                        help=("Logging level. Possible options: DEBUG, INFO, "
                              "WARNING, ERROR or CRITICAL (upper or lowercase)"
                              ))
    parser.add_argument("-f", "--logfile", type=str, dest="logfile_path",
                        help=("If this is specified, all logging will be "
                              "written into the file at the end of this path"))
    args = parser.parse_args()

    path = args.path if args.path else "./config.ini"
    logfile = args.logfile_path if args.logfile_path else None

    log_level = logging.INFO if args.logging == None else parse_log_level(
        args.logging.upper())

    return (path, log_level, logfile)


def parse_log_level(level):
    """Parses a log level from string to its logging counterpart. IF the given 
    level is invalid, a KeyError is raised.

    Arguments: 
    - level (str) -- must be one of the following: 
      DEBUG, INFO, WARNING, ERROR or CRITICAL
    """
    if level == "DEBUG":
        return logging.DEBUG
    elif level == "INFO":
        return logging.INFO
    elif level == "WARNING":
        return logging.WARNING
    elif level == "ERROR":
        return logging.ERROR
    elif level == "CRITICAL":
        return logging.CRITICAL
    else:
        raise KeyError(
            "If the logging parameter is given, it must be one of the "
            "following: DEBUG, INFO, WARNING, ERROR or CRITICAL.")


def setup_logger(level, logfile):
    """Initiates the logger
    Arguments:
    - level: Logging level. Must be a valid level.
      See https://docs.python.org/3/howto/logging.html for more info
    - logfile -- None or path to a file, where logging should be written to
    """
    # Parse log level
    # Add ".%(msecs)03d" after the time for ms
    format = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=level,
                        format=format,
                        datefmt="%H:%M:%S",
                        filename=logfile)


async def main():
    # This script requires Python version 3.9 or newer to run
    if not sys.version_info >= (3, 9):
        raise EnvironmentError("Python version 3.9 or newer is required. "
                               f"(detected: {sys.version})")
    os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))

    (path, log_level, logfile) = parse_arguments()

    # Setup Logger. Change logging level here!
    setup_logger(log_level, logfile)

    logging.info(f"Starting Gossip. Config path: \"{path}\"")
    config = Config(path)
    logging.info(config)
    await Gossip(config).run()


if __name__ == "__main__":
    asyncio.run(main())
