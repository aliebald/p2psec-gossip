"""
This module provides the Config class.
"""

from configparser import ConfigParser


def __check_cache_size(config):
    """Checks if the cache_size is greather than 0"""
    if config.cache_size <= 0:
        raise KeyError(f"cache_size ({config.cache_size}) must be greater than"
                       " 0")


def __check_min_connections(config):
    """Checks if min_connections >= 0"""
    if config.min_connections < 0:
        raise KeyError(f"min_connections ({config.min_connections}) must be "
                       "greater than or equal to 0")


def __check_max_connections(config):
    """Checks if 
    - max_connections > 0 
    - max_connections >= min_connections
    """
    if config.max_connections <= 0:
        raise KeyError(f"max_connections ({config.max_connections}) must be "
                       "greater than 0")

    if config.max_connections < config.min_connections:
        raise KeyError(f"max_connections ({config.max_connections}) must be "
                       "greater than 0 and greater than or equal to "
                       f"min_connections ({config.min_connections})")


def __check_degree(config):
    """Checks if 
    - degree <= max_connections
    - degree <= min_connections
    - degree > 0"""
    if config.degree > config.max_connections:
        raise KeyError(f"degree ({config.degree}) must be less than or equal "
                       f"to max_connections ({config.max_connections})")

    if config.degree > config.min_connections:
        raise KeyError(f"degree ({config.degree}) must be greater than or "
                       f"equal to min_connections ({config.min_connections})")

    if config.degree < 0:
        raise KeyError(f"degree ({config.degree}) must be greater than 0")


def __check_search_cooldown(config):
    """Checks if search_cooldown greater than 0"""
    if config.search_cooldown <= 0:
        raise KeyError(f"search_cooldown ({config.search_cooldown}) must be "
                       "greater than 0")


# config blueprint.
# If a field is set to required, the key must exist in the config beeing parsed
# If required: False, a default value must (!) be given
# If "type" is given, it will try to cast to that type
# If "checks" is given, it needs to provide a function that checks the value of
# this key. The function needs to accept a config object as parameter
config_config = {
    "gossip": {
        "cache_size": {
            "required": True,
            "type": int,
            "checks": __check_cache_size
        },
        "degree": {
            "required": True,
            "type": int,
            "checks": __check_degree
        },
        "min_connections": {
            "required": True,
            "type": int,
            "checks": __check_min_connections
        },
        "max_connections": {
            "required": True,
            "type": int,
            "checks": __check_max_connections
        },
        "search_cooldown": {
            "required": False,
            "default": 120000,  # 2 minutes
            "type": int,
            "checks": __check_search_cooldown
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

    Class variables:
    - cache_size: see readme
    - degree: see readme
    - min_connections: see readme
    - max_connections: see readme
    - search_cooldown: see readme
    - bootstrapper: see readme
    - p2p_address: see readme
    - api_address: see readme
    - known_peers: see readme
    """

    def __init__(self, path):
        configparser = ConfigParser()
        parsed = configparser.read(path)
        if len(parsed) != 1:
            raise IOError(f"No config found at \"{path}\"")

        self.__parse_config(configparser)
        self.__check_config()

        # split known peers string into list, if a string was loaded
        if len(self.known_peers) > 0:
            self.known_peers = self.known_peers.replace(" ", "").split(",")

    def __str__(self):
        """Returns this config as a string"""
        str = "[gossip]:\n"
        for key in vars(self):
            str += f"{key} = {vars(self)[key]}\n"
        return str

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

    def __check_config(self):
        """Executes all checks given in the config_config"""
        for section in config_config:
            for key in config_config[section]:
                self.__check_key(section, key)

    def __check_key(self, section, key):
        """Executes the checks given for this key in config_config, if
        one is provided. Passes this config as parameter"""
        if "checks" in config_config[section][key]:
            config_config[section][key]["checks"](self)
