from configparser import ConfigParser

# config blueprint.
# If a field is set to required, the key must exist in the config beeing parsed
# If required: False, a default value must (!) be given
# If "type" is given, it will try to cast to that type
config_config = {
    "gossip": {
        "cache_size": {
            "required": True,
            "type": int
        },
        "degree": {
            "required": True,
            "type": int
        },
        "max_connections": {
            "required": True,
            "type": int
        },
        "search_cooldown": {
            "required": False,
            "default": 120000,  # 2 minutes
            "type": int
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


class Config:
    """The config class abstracts the parsing required to read config files
    and provides easy access to the variables inside the given configfile.
    If a required field is not found, a KeyError exception is raised.
    """

    def __init__(self, path):
        configparser = ConfigParser()
        configparser.read(path)
        self.__parse_config(configparser)

        # split known peers string into list, if a string was loaded
        if len(self.known_peers) > 0:
            self.known_peers = self.known_peers.replace(" ", "").split(",")

    def __parse_config(self, configparser):
        """Parses the whole config as specified in config_config"""
        for section in config_config:
            for key in config_config[section]:
                self.__parse_key(configparser, section, key)

    def __parse_key(self, configparser, section, key):
        """Parses a single key from the configparser into the attributes of
        this class. Throws an KeyError if key or section does not exist.
        """
        self.__check_section_exists(configparser, section)
        if config_config[section][key]["required"]:
            self.__check_key_exists(configparser, section, key)
            setattr(self, key, configparser[section][key])
        elif self.__key_in_configparser(configparser, section, key):
            setattr(self, key, configparser[section][key])
        else:
            setattr(self, key, config_config[section][key]["default"])

        # Cast if type is defined in config_config
        if "type" in config_config[section][key]:
            _type = config_config[section][key]["type"]
            setattr(self, key, (_type)(vars(self)[key]))

    def __key_in_configparser(self, configparser, section, key):
        """Checks if the given section and key exists. Similar to 
        __check_key_exists but returns a boolean and does not throw an error. 
        For non required keys.
        """
        return (key in configparser[section] and
                len(configparser[section][key]) > 0)

    def __check_section_exists(self, configparser, section):
        """Checks if the given section exists. Throws an KeyError if not."""
        if section not in configparser:
            error = ("The section \"{}\" is missing in the config. Please "
                     "refer to the README for information").format(section)
            raise KeyError(error)

    def __check_key_exists(self, configparser, section, key):
        """Checks if the given key exists. Throws an KeyError if not.
        Assumes that the section exists. Use __check_section_exists to check if
        a section exists
        """
        if key not in configparser[section]:
            error = ("\"{}\" is missing in the {} section of the "
                     "config. Please refer to the README for information."
                     ).format(key, section)
            raise KeyError(error)

    def print_config(self):
        """Prints all available keys and theire values."""
        print("[gossip]:")
        for key in vars(self):
            print("{} = {}".format(key, vars(self)[key]))
