from struct import unpack, error

PEER_DISCOVERY = 505
PEER_OFFER = 506


# struct formats for API packets
# !! no data is included as size is variable
FORMAT_PEER_DISCOVERY = "!HHQ"
FORMAT_PEER_OFFER = "!HHQQ"


##############################################################################
# The following functions are also declared in package parser.
# TODO avoid duplicate functions
##############################################################################

def __get_header_size(buf):
    """Returns the size in the packet header
    [!] no checks as this is module intern

    Arguments:
        buf -- packet as byte-object

    Returns:
        int"""
    return int.from_bytes(buf[:2], "big")


def get_header_type(buf):
    """Returns the type in the packet header

    Arguments:
        buf -- packet as byte-object

    Returns:
        500-503 :
        -1      : header too small!"""
    # this method can get called from modules, so check for header correctness
    if len(buf) < 4:
        return -1
    else:
        return int.from_bytes(buf[2:4], "big")


def __check_size(buf):
    """Compares the packet size to the size given in the header.

    Arguments:
        buf -- packet as byte-object

    Returns:
        bool
        """
    return len(buf) == __get_header_size(buf)

##############################################################################


def parse_peer_discovery(buf):
    """Parses a peer discovery message to a human-readable tuple
    [!] Does (currently) not check for any correctness in the body fields!

    Arguments:
        buf -- packet as byte-object

    Returns:
        None if an error occurred, otherwise:
        tuple (size, type, challenge)
        as    (int,  int,  int)
    """
    # check header: size
    if not __check_size(buf):
        print("Incorrect packet size in parse_peer_discovery!")
        return None

    try:
        package = unpack(FORMAT_PEER_DISCOVERY, buf)
        return package
    except error:
        print("Struct parsing error in parse_peer_discovery!")
        return None


def parse_peer_offer(buf):
    """Parses a peer offer message to a human-readable tuple
    [!] Does (currently) not check for any correctness in the body fields!

    Arguments:
        buf -- packet as byte-object

    Returns:
        None if an error occurred, otherwise:
        tuple (size, type, challenge, nonce, data)
        as    (int,  int,  int,       int,   str list)
    """
    # check header: size
    if not __check_size(buf):
        print("Incorrect packet size in parse_peer_offer!")
        return None

    try:
        packet_no_data = unpack(FORMAT_PEER_OFFER, buf[:20])
        data = (str(buf[20:]).split(","),)
        return packet_no_data + data
    except error:
        print("Struct parsing error in parse_peer_offer!")
        return None


def build_peer_discovery():
    pass


def build_peer_offer():
    pass
