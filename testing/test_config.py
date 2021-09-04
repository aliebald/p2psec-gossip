import unittest
from context import Config
import os


class Test_config(unittest.TestCase):
    def test_missing_degree(self):
        # Check if an KeyError is raised when degree is missing
        generate_test_config(degree=None)
        self.__check_raises_valid_exception(KeyError)

    def test_missing_p2p_address(self):
        # Check if an KeyError is raised when p2p_address is missing
        generate_test_config(p2p_address=None)
        self.__check_raises_valid_exception(KeyError)

    def test_missing_api_address(self):
        # Check if an KeyError is raised when api_address is missing
        generate_test_config(api_address=None)
        self.__check_raises_valid_exception(KeyError)

    def test_missing_max_connections(self):
        # Check if an KeyError is raised when max_connections is missing
        generate_test_config(max_connections=None)
        self.__check_raises_valid_exception(KeyError)

    def test_missing_min_connections(self):
        # Check if an KeyError is raised when min_connections is missing
        generate_test_config(min_connections=None)
        self.__check_raises_valid_exception(KeyError)

    def test_missing_bootstrapper(self):
        # Check if an KeyError is raised when bootstrapper is missing
        generate_test_config(bootstrapper=None)
        self.__check_raises_valid_exception(KeyError)

    def test_invalid_cache_size(self):
        # Check if an KeyError is raised when cache_size is negative
        generate_test_config(cache_size=-10)
        self.__check_raises_valid_exception(KeyError)

        # Check if an KeyError is raised when cache_size = 0
        generate_test_config(cache_size=0)
        self.__check_raises_valid_exception(KeyError)

    def test_invalid_degree(self):
        # Check if an KeyError is raised when degree is negative
        generate_test_config(degree=-10)
        self.__check_raises_valid_exception(KeyError)

        # Check if an KeyError is raised when degree = 0
        generate_test_config(degree=0)
        self.__check_raises_valid_exception(KeyError)

    def test_invalid_min_connections(self):
        # Check if an KeyError is raised when min_connections is negative
        generate_test_config(min_connections=-10)
        self.__check_raises_valid_exception(KeyError)

    def test_invalid_max_connections(self):
        # Check if an KeyError is raised when max_connections is negative
        generate_test_config(max_connections=-10)
        self.__check_raises_valid_exception(KeyError)

        # Check if an KeyError is raised when max_connections < min_connections
        generate_test_config(max_connections=10, min_connections=20)
        self.__check_raises_valid_exception(KeyError)

        # Check if an KeyError is raised when max_connections = 0
        generate_test_config(max_connections=0)
        self.__check_raises_valid_exception(KeyError)

    def test_invalid_bootstrapper(self):
        # Check if an KeyError is raised when the port is missing
        generate_test_config(bootstrapper="127.0.0.1")
        self.__check_raises_valid_exception(KeyError)

        # Check if an KeyError is raised when the ip is too large
        generate_test_config(bootstrapper="127.0.0.0.1:100")
        self.__check_raises_valid_exception(KeyError)

        # Check if an KeyError is raised when the bootstrapper is a single
        # space
        generate_test_config(bootstrapper=" ")
        self.__check_raises_valid_exception(KeyError)

        # Check if an KeyError is raised when the bootstrapper is just a number
        generate_test_config(bootstrapper="1234")
        self.__check_raises_valid_exception(KeyError)

    def test_invalid_p2p_address(self):
        # Check if an KeyError is raised when the port is missing
        generate_test_config(p2p_address="127.0.0.1")
        self.__check_raises_valid_exception(KeyError)

        # Check if an KeyError is raised when the ip is too large
        generate_test_config(p2p_address="127.0.0.0.1:100")
        self.__check_raises_valid_exception(KeyError)

        # Check if an KeyError is raised when the p2p_address is a single space
        generate_test_config(p2p_address=" ")
        self.__check_raises_valid_exception(KeyError)

        # Check if an KeyError is raised when the p2p_address is just a number
        generate_test_config(p2p_address="1234")
        self.__check_raises_valid_exception(KeyError)

    def test_invalid_api_address(self):
        # Check if an KeyError is raised when the port is missing
        generate_test_config(api_address="127.0.0.1")
        self.__check_raises_valid_exception(KeyError)

        # Check if an KeyError is raised when the ip is too large
        generate_test_config(api_address="127.0.0.0.1:100")
        self.__check_raises_valid_exception(KeyError)

        # Check if an KeyError is raised when the api_address is a single space
        generate_test_config(api_address=" ")
        self.__check_raises_valid_exception(KeyError)

        # Check if an KeyError is raised when the api_address is just a number
        generate_test_config(api_address="1234")
        self.__check_raises_valid_exception(KeyError)

    def test_invalid_known_peers(self):
        # Check if an KeyError is raised when the port is missing
        generate_test_config(known_peers="127.0.0.1")
        self.__check_raises_valid_exception(KeyError)

        # Check if an KeyError is raised when the ip is too large
        generate_test_config(known_peers="127.0.0.0.1:100")
        self.__check_raises_valid_exception(KeyError)

        # Check if an KeyError is raised when the known_peers is just a number
        generate_test_config(known_peers="127.0.0.1:100, 1234")
        self.__check_raises_valid_exception(KeyError)

        # Check if an KeyError is raised when the known_peers contains
        # duplicates
        generate_test_config(known_peers="127.0.0.1:1000, 127.0.0.1:1000")
        self.__check_raises_valid_exception(KeyError)

    def test_valid_known_peers(self):
        # Check if no Error is raised when the known_peers is a single space
        # -> is considert empty
        generate_test_config(known_peers=" ")
        self.__check_raises_no_exception()

        # Check if no Error is raised when the known_peers has one valid entry
        generate_test_config(known_peers="127.0.0.1:1000")
        self.__check_raises_no_exception()

        # Check if no Error is raised when the known_peers has two valid entry
        generate_test_config(known_peers="127.0.0.1:1000, 127.0.0.1:2000")
        self.__check_raises_no_exception()

        # Check if no Error is raised when the known_peers has tree valid entry
        generate_test_config(
            known_peers="127.0.0.1:1000, 127.0.0.1:2000, 127.0.0.1:3000")
        self.__check_raises_no_exception()

    def test_valid_no_except(self):
        generate_test_config()
        # Tests if a valid config is not raising an exception
        self.__check_raises_no_exception()

    def __check_raises_no_exception(self):
        """Asserts that the initialization for the generated Config 
        ("autogen_testconfig.ini") does not fail"""
        try:
            Config("autogen_testconfig.ini")
        except Exception as e:
            self.fail("Config raised an Exception unexpectedly")

    def __check_raises_valid_exception(self, exception):
        """Asserts that the initialization for the generated Config 
        ("autogen_testconfig.ini") fails and raises the given exception with a 
        message
        """
        with self.assertRaises(exception) as cm:
            Config("autogen_testconfig.ini")
        # Test if an error message exists
        self.assertTrue(len(str(cm.exception)) > 0)

    def tearDownClass():
        if os.path.exists("autogen_testconfig.ini"):
            os.remove("autogen_testconfig.ini")


def generate_test_config(
    cache_size="50",
    degree="15",
    min_connections="15",
    max_connections="30",
    search_cooldown="30",
    bootstrapper="127.0.0.1:1000",
    p2p_address="127.0.0.1:6001",
    api_address="127.0.0.1:7001",
    known_peers="127.0.0.1:1000, 127.0.0.1:2000"
):
    """Generates a config file, autogen_testconfig.ini in the current directory
    , for testing. Set parameters to None to not include them in the config. If
    all default parameters are used, the config should be valid.
    Use delete_test_config() to delete the file after executing the tests
    """
    config = "[gossip]\n"
    if cache_size:
        config += f"cache_size = {cache_size}\n"
    if degree:
        config += f"degree = {degree}\n"
    if min_connections:
        config += f"min_connections = {min_connections}\n"
    if max_connections:
        config += f"max_connections = {max_connections}\n"
    if search_cooldown:
        config += f"search_cooldown = {search_cooldown}\n"
    if bootstrapper:
        config += f"bootstrapper = {bootstrapper}\n"
    if p2p_address:
        config += f"p2p_address = {p2p_address}\n"
    if api_address:
        config += f"api_address = {api_address}\n"
    if known_peers:
        config += f"known_peers = {known_peers}\n"

    f = open("autogen_testconfig.ini", "w")
    f.write(config)
    f.close()


def main():
    unittest.main()


if __name__ == "__main__":
    main()
