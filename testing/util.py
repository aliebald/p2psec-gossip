import os


def generate_test_config(
    filename="autogen_testconfig.ini",
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
    """Generates a config file in the current directory, for testing.
    Set parameters to None to not include them in the config.
    If all default parameters are used, the config should be valid.
    Use delete_test_config() to delete the file after executing the tests

    Arguments:
    - filename (str) -- default "autogen_testconfig.ini" Filename for config
    - cache_size (str) -- default: "50"
    - degree (str) -- default: "15"
    - min_connections (str) -- default: "15"
    - max_connections (str) -- default: "30"
    - search_cooldown (str) -- default: "30"
    - bootstrapper (str) -- default: "127.0.0.1:1000"
    - p2p_address (str) -- default: "127.0.0.1:6001"
    - api_address (str) -- default: "127.0.0.1:7001"
    - known_peers (str) -- default: "127.0.0.1:1000, 127.0.0.1:2000"
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

    f = open(filename, "w")
    f.write(config)
    f.close()


def delete_file(filename="autogen_testconfig.ini"):
    """Tests if a file with the given name/path exists and removes it.

    Arguments:
    - filename (str) -- default "autogen_testconfig.ini"
    """
    if os.path.exists(filename):
        os.remove(filename)
