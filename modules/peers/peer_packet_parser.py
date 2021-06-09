from struct import unpack, pack, error


PEER_DISCOVERY = 505
PEER_OFFER = 506
PEER_INFO = 507

# struct formats for peer packets
# data is not included in the formats, since its size is variable
FORMAT_PEER_DISCOVERY = "!HHQ"
FORMAT_PEER_OFFER = "!HHQQ"
FORMAT_PEER_INFO = "!HHHH"


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
        data = (buf[20:].decode("utf-8").split(","),)
        return packet_no_data + data
    except error:
        print("Struct parsing error in parse_peer_offer!")
        return None


def parse_peer_info(buf):
    """Parses a peer info message to a human-readable tuple
    [!] Does (currently) not check for any correctness in the body fields!

    Arguments:
        buf -- packet as byte-object

    Returns:
        None if an error occurred, otherwise:
        tuple (size, type, p2p_listening_port)
        as    (int,  int,  int,)
    """
    # check header: size
    if not __check_size(buf):
        print("Incorrect packet size in parse_peer_info!")
        return None

    try:
        (size, type, reserved, port) = unpack(FORMAT_PEER_INFO, buf)
        return (size, type, port)
    except error:
        print("Struct parsing error in parse_peer_offer!")
        return None


def pack_peer_discovery(challenge):
    """Packs a peer discovery message as byte-object.

    Arguments:
        challenge -- challenge for peer offer response.

    Returns:
        packet as byte-object
    """
    buf = pack(FORMAT_PEER_DISCOVERY, 12, PEER_DISCOVERY, challenge)
    return buf


def pack_peer_offer(challenge, nonce, data):
    """Packs a peer offer message as byte-object.

    Arguments:
        challenge -- challenge received from original peer discovery.
        nonce -- nonce according to documentation

    Returns:
        packet as byte-object
    """
    data_bytes = (",".join(data)).encode("utf-8")
    size = 20 + len(data_bytes)
    buf = pack(FORMAT_PEER_OFFER, size, PEER_OFFER, challenge, nonce)
    return buf + data_bytes


def pack_peer_info(p2p_listening_port):
    """Packs a peer info message as byte-object.

    Arguments:
        p2p_listening_port -- Port this peer accepts new peer connections at

    Returns:
        peer info packet as byte-object
    """
    buf = pack(FORMAT_PEER_INFO, 8, PEER_INFO, 0, p2p_listening_port)
    return buf
