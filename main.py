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
        "The following options can be given when using this program. For a "
        "general project description, please see the endterm report in the "
        "docs folder."
    )
    path_desc = (
        "Path to the desired config file. This file must be in the Windows "
        "INI file format and comply with the requirements given in the "
        "documentation"
    )
    verbose_desc = (
        "If this flag is set, additional debug information will be "
        "displayed during execution. This Information can give a better and "
        "more detailed insight into the execution, but is not required for a "
        "overview over events during execution."
    )
    logfile_desc = (
        "With this option followed by a valid path, all logging will be "
        "written into the file at the end of the path. If the given file does "
        "not yet exist, it will be created. Otherwise, new logs will be "
        "appended to the current content. Note that the folder structure "
        "given in the path must already exist. If this option is not given, "
        "logging will happen in the console"
    )

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-p", "--path", type=str, help=path_desc)
    parser.add_argument("-v", "--verbose", action='store_true', dest="logging",
                        help=verbose_desc)
    parser.add_argument("-l", "--logfile", type=str, dest="logfile_path",
                        help=logfile_desc)
    args = parser.parse_args()

    path = args.path if args.path else "./config.ini"
    logfile = args.logfile_path if args.logfile_path else None

    log_level = logging.DEBUG if args.logging else logging.INFO

    return (path, log_level, logfile)


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

    try:
        # Setup Logger. Change logging level here!
        setup_logger(log_level, logfile)
    except FileNotFoundError:
        print("Invalid argument: the path given with -l or --logfile is "
              "invalid. Please make sure it exists.")
        return

    logging.info(f"Starting Gossip. Config path: \"{path}\"")
    config = Config(path)
    logging.info(config)
    await Gossip(config).run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        exit()
