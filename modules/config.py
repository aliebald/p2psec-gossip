from configparser import ConfigParser

# config blueprint.
# If a field is set to required, the key must exist in the config beeing parsed
# If required: False, a default value must (!) be given
config_config = {
    "gossip": {
        "cache_size": {
            "required": True
        },
        "degree": {
            "required": True
        },
        "max_connections": {
            "required": True
        },
        "search_cooldown": {
            "required": False,
            "default": 120000  # 2 minutes
        },
        "bootstrapper": {
            "required": True
        },
        "p2p_address": {
            "required": True
        },
        "api_address": {
            "required": True
        },
        "known_peers": {
            "required": False,
            "default": []
        },
    }
}


# The config class abstracts the parsing required to read config files
# and provides easy access to the variables inside the given configfile.
# If a required field is not found, a KeyError exception is raised.
class Config:
    def __init__(self, path):
        configparser = ConfigParser()
        configparser.read(path)
        self.__parse_config(configparser)

        # split known peers string into list, if a sring was loaded
        if len(self.known_peers) > 0:
            self.known_peers = self.known_peers.replace(" ", "").split(",")

    # Parses the whole config as specified in config_config
    def __parse_config(self, configparser):
        for section in config_config:
            for key in config_config[section]:
                self.__parse_key(configparser, section, key)

    # Parses a single key from the configparser into the attributes of this
    # class. Throws an KeyError if key or section does not exist.
    def __parse_key(self, configparser, section, key):
        if config_config[section][key]["required"]:
            self.__check_key_exists(configparser, section, key)
            setattr(self, key, configparser[section][key])
        elif self.__key_in_configparser(configparser, section, key):
            setattr(self, key, configparser[section][key])
        else:
            setattr(self, key, config_config[section][key]["default"])

    # Checks if the given section and key exists. Similar to __check_key_exists
    # but returns a boolean and does not throw an error. For non required keys.
    def __key_in_configparser(self, configparser, section, key):
        return (key in configparser[section] and
                len(configparser[section][key]) > 0)

    # Checks if the given section and key exists. Throws an KeyError if not.
    def __check_key_exists(self, configparser, section, key):
        if section not in configparser:
            error = ("The section \"{}\" is missing in the config. Please "
                     "refer to the README for information").format(section)
            raise KeyError(error)

        if key not in configparser[section]:
            error = ("\"{}\" is missing in the {} section of the "
                     "config. Please refer to the README for information."
                     ).format(key, section)
            raise KeyError(error)

    # Prints all available keys and theire values.
    def print_config(self):
        print("[gossip]:")
        for key in vars(self):
            print("{} = {}".format(key, vars(self)[key]))
