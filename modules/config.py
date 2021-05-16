from configparser import ConfigParser

# The config class abstracts the parsing required to read config files
# and provides easy access to the variables inside the given configfile.
# If a required field is not found, a KeyError exception is raised.


class Config:
    def __init__(self, path):
        configparser = ConfigParser()
        configparser.read(path)
        self.__check_required_fields_exist(configparser)

        # Parse required Fields
        self.cache_size = configparser["gossip"]["cache_size"]
        self.max_connections = configparser["gossip"]["max_connections"]
        self.bootstrapper = configparser["gossip"]["bootstrapper"]
        self.p2p_address = configparser["gossip"]["p2p_address"]
        self.api_address = configparser["gossip"]["api_address"]

        # Parse non required fields
        # Parse known_peers. If none are set, use an empty list
        if ("known_peers" in configparser["gossip"] and
                len(configparser["gossip"]["known_peers"]) > 0):
            self.known_peers = (configparser["gossip"]["known_peers"]).replace(
                " ", "").split(",")
        else:
            self.known_peers = []

    # Prints all available keys and theire values.
    def print_config(self):
        print("[gossip]:")
        print("cache_size = {}".format(self.cache_size))
        print("max_connections = {}".format(self.max_connections))
        print("bootstrapper = {}".format(self.bootstrapper))
        print("p2p_address = {}".format(self.p2p_address))
        print("api_address = {}".format(self.api_address))
        print("known_peers = {}".format(self.known_peers))

    # Checks is all required sections and keys exists in the given ConfigParser
    # If a required field does not exist, a KeyError exception is raised
    def __check_required_fields_exist(self, configparser):
        required = ["cache_size", "max_connections", "bootstrapper",
                    "p2p_address", "api_address"]

        if "gossip" not in configparser:
            error = ("The section \"gossip\" is missing in the config. Please "
                     "refer to the README for information")
            raise KeyError(error)

        for key in required:
            if key not in configparser["gossip"]:
                error = ("\"{}\" is missing in the gossip section of the "
                         "config. Please refer to the README for information."
                         ).format(key)
                raise KeyError(error)
