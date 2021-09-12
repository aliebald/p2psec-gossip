""" This module handles everything packets.
    The goal is to provide one place for packet parsing safety
"""

import logging
from struct import pack, unpack, error

GOSSIP_ANNOUNCE = 500
GOSSIP_NOTIFY = 501
GOSSIP_NOTIFICATION = 502
GOSSIP_VALIDATION = 503

PEER_ANNOUNCE = 504
PEER_DISCOVERY = 505
PEER_OFFER = 506
PEER_INFO = 507
PEER_CHALLENGE = 508
PEER_VERIFICATION = 509
PEER_VALIDATION = 510

# struct formats for API packets
# !! no data is included as size is variable
FORMAT_GOSSIP_ANNOUNCE = "!HHBBH"
FORMAT_GOSSIP_NOTIFY = "!HHHH"
FORMAT_GOSSIP_NOTIFICATION = "!HHHH"
FORMAT_GOSSIP_VALIDATION = "!HHHH"

FORMAT_PEER_ANNOUNCE = "!HHQBBH"
FORMAT_PEER_DISCOVERY = "!HHQ"
FORMAT_PEER_OFFER = "!HHQQ"
FORMAT_PEER_INFO = "!HHHH"
FORMAT_PEER_CHALLENGE = "!HHQ"
FORMAT_PEER_VERIFICATION = "!HHQ"
FORMAT_PEER_VALIDATION = "!HHHH"


def __get_header_size(buf):
    """Returns the size in the packet header
    [!] no checks as this is module intern

    Arguments:
    - buf -- packet as byte-object

    Returns:
        header size (int)
    """
    return int.from_bytes(buf[:2], "big")


def get_header_type(buf):
    """Returns the type in the packet header

    Arguments:
    - buf -- packet as byte-object

    Returns: -1 if header too small, otherwise header type (int)
    """
    # this method can get called from modules, so check for header correctness
    if len(buf) < 4:
        return -1
    else:
        return int.from_bytes(buf[2:4], "big")


def __check_size(buf):
    """Compares the packet size to the size given in the header.

    Arguments:
    - buf -- packet as byte-object

    Returns: True if size in packet header is equal to packet size
    """
    return len(buf) == __get_header_size(buf)


#################
# API Messages
#################

def parse_gossip_announce(buf):
    """Checks the header, strips it and returns the body as a 3-tuple
    [!] Does not check for any correctness in the body fields!

    Arguments:
    - buf -- packet as byte-object

    Returns:
    - None if an error occurres
    - tuple (ttl, datatype, data )
      as    (int, int     , bytes)
    """
    # check header: size
    if not __check_size(buf):
        logging.debug(
            "[PARSER] Incorrect packet size in parse_gossip_announce")
        return None

    try:
        (_, type, ttl, _, datatype) = unpack(FORMAT_GOSSIP_ANNOUNCE, buf[:8])
    except error as e:
        logging.debug("[PARSER] Struct parsing error in parse_gossip_announce."
                      f" Error: {e}")
        return None

    if type != GOSSIP_ANNOUNCE:
        logging.debug(f"[PARSER] Expected type {GOSSIP_ANNOUNCE} but got "
                      f"{type} in parse_gossip_announce")
        return None

    data = (buf[8:],)
    return (ttl, datatype) + data


def parse_gossip_notify(buf):
    """Parses a GOSSIP NOTIFY to a human-readable 1-tuple
    [!] Does not check for any correctness in the body fields!

    Arguments:
    - buf -- packet as byte-object

    Returns: datatype (int) or None if an error occurred
    """
    if not __check_size(buf):
        logging.debug(
            "[PARSER] Incorrect packet size in parse_gossip_notification")
        return None

    # check: no data present
    if __get_header_size(buf) != 8:
        logging.debug("[PARSER] Gossip notify packet is missing data")
        return None

    try:
        (_, type, _, datatype) = unpack(FORMAT_GOSSIP_NOTIFY, buf)
    except error as e:
        logging.debug("[PARSER] Struct parsing error in parse_gossip_notify. "
                      f"Error: {e}")
        return None

    if type != GOSSIP_NOTIFY:
        logging.debug(f"[PARSER] Expected type {GOSSIP_NOTIFY} but got "
                      f"{type} in parse_gossip_notify")
        return None

    return datatype


def parse_gossip_notification(buf):
    """Parses a GOSSIP NOTIFICATION to a human-readable 6-tuple
    [!] Does not check for any correctness in the body fields!

    Arguments:
        buf -- packet as byte-object

    Returns:
    - None if an error occurres
    - tuple (msg_id, datatype, data )
         as (int   , int     , bytes)
    """
    # check header: size
    if not __check_size(buf):
        logging.debug(
            "[PARSER] Incorrect packet size in parse_gossip_notification")
        return None

    try:
        (_, type, id, datatype) = unpack(FORMAT_GOSSIP_NOTIFICATION, buf[:8])
    except error as e:
        logging.debug("[PARSER] Struct parsing error in "
                      f"parse_gossip_notification. Error: {e}")
        return None

    if type != GOSSIP_NOTIFICATION:
        logging.debug(f"[PARSER] Expected type {GOSSIP_NOTIFICATION} but got "
                      f"{type} in parse_gossip_notification")
        return None

    data = (buf[8:],)
    return (id, datatype) + data


def parse_gossip_validation(buf):
    """Parses a GOSSIP VALIDATION to a human-readable 6-tuple

    Arguments:
        buf -- packet as byte-object

    Returns:
    - None if an error occurres
    - tuple (msg_id, valid)
      as    (int,    bool)
    """
    # check header: size
    if not __check_size(buf):
        logging.debug(
            "[PARSER] Incorrect packet size in parse_gossip_validation")
        return None

    try:
        (_, type, id, valid) = unpack(FORMAT_GOSSIP_VALIDATION, buf[:8])
    except error as e:
        logging.debug("[PARSER] Struct parsing error in "
                      f"parse_gossip_validation. Error: {e}")
        return None

    if type != GOSSIP_VALIDATION:
        logging.debug(f"[PARSER] Expected type {GOSSIP_VALIDATION} but got "
                      f"{type} in parse_gossip_validation")
        return None

    # valid: test if first bit is set
    return (id, valid & 1 != 0)


def build_gossip_notification(msg_id, datatype, data):
    """Builds a gossip notification packet as a byte object from arguments

    Arguments:
    - msg_id (int) -- message id
    - datatype (int)
    - data (byte-object)

    Returns:
    - None if an error occurres
    - message as byte-object
    """

    if msg_id >= 2**16 or msg_id < 0:
        return None
    elif datatype >= 2**16 or msg_id < 0:
        return None

    # data_bytes = bytes(data, 'utf-8')
    data_bytes = data
    size = 8 + len(data_bytes)
    if size >= 2**16:
        return None
    buf = pack(FORMAT_GOSSIP_NOTIFICATION, size, GOSSIP_NOTIFICATION,
               msg_id, datatype)
    buf += data_bytes
    return buf


#################
# PEER Messages
#################


def parse_peer_announce(buf):
    """Parses a peer announce message to a human-readable tuple
    [!] Does (currently) not check for any correctness in the body fields!
    Assumes that the message type is PEER_ANNOUNCE.

    Arguments:
    - buf (byte-object) -- packet

    Returns:
    - None if an error occurred, otherwise:
    - tuple (id,  ttl, data_type, data)
      as    (int, int, int,       byte-object)
    """
    # check header: size
    if not __check_size(buf):
        logging.debug("[PARSER] Incorrect packet size in parse_peer_announce")
        return None

    try:
        (_, _, id, ttl, _, data_type) = unpack(FORMAT_PEER_ANNOUNCE, buf[:16])
    except error as e:
        logging.debug("[PARSER] Struct parsing error in parse_peer_announce. "
                      f"Error: {e}")
        return None

    return (id, ttl, data_type, buf[16:])


def parse_peer_discovery(buf):
    """Parses a peer discovery message to a human-readable tuple
    [!] Does (currently) not check for any correctness in the body fields!
    Assumes that the message type is PEER_DISCOVERY.

    Arguments:
    - buf (byte-object) -- packet

    Returns: challenge (int) or None if an error occurred
    """
    # check header: size
    if not __check_size(buf):
        logging.debug(
            "[PARSER] Incorrect packet size in parse_peer_discovery")
        return None

    try:
        (_, _, challenge) = unpack(FORMAT_PEER_DISCOVERY, buf)
    except error as e:
        logging.debug("[PARSER] Struct parsing error in parse_peer_discovery. "
                      f"Error: {e}")
        return None

    return challenge


def parse_peer_offer(buf):
    """Parses a peer offer message to a human-readable tuple
    [!] Does (currently) not check for any correctness in the body fields!
    Assumes that the message type is PEER_OFFER.

    Arguments:
    - buf (byte-object) -- packet

    Returns:
    - None if an error occurred, otherwise:
    - tuple (challenge, nonce, data)
      as    (int,       int,   str list)
    """
    # check header: size
    if not __check_size(buf):
        logging.debug("[PARSER] Incorrect packet size in parse_peer_offer")
        return None

    try:
        (_, _, challenge, nonce) = unpack(FORMAT_PEER_OFFER, buf[:20])
    except error as e:
        logging.debug("[PARSER] Struct parsing error in parse_peer_offer. "
                      f"Error: {e}")
        return None

    data = (buf[20:].decode("utf-8").split(","),)
    return (challenge, nonce) + data


def parse_peer_info(buf):
    """Parses a peer info message to a human-readable tuple
    [!] Does (currently) not check for any correctness in the body fields!
    Assumes that the message type is PEER_INFO.

    Arguments:
    - buf (byte-object) -- packet

    Returns: port (int) or None if an error occurred
    """
    # check header: size
    if not __check_size(buf):
        logging.debug("[PARSER] Incorrect packet size in parse_peer_info")
        return None

    try:
        (_, _, _, port) = unpack(FORMAT_PEER_INFO, buf)
    except error as e:
        logging.debug("[PARSER] Struct parsing error in parse_peer_info. "
                      f"Error: {e}")
        return None

    return port


def parse_peer_challenge(buf):
    """Reads a PEER_CHALLENGE by checking the header and returning the
    challenge
    Assumes that the message type is PEER_CHALLENGE.

    Arguments:
    - buf (byte-object) -- packet

    Returns: challenge (int) or None if an error occurred
    """
    if not __check_size(buf):
        logging.debug("[PARSER] Incorrect packet size in parse_peer_challenge")
        return None

    (_, _, challenge) = unpack(FORMAT_PEER_CHALLENGE, buf)
    return challenge


def parse_peer_verification(buf):
    """Reads a PEER_VERIFICATION by checking the header and returning the
    nonce. Assumes that the message type is PEER_VERIFICATION.

    Arguments:
    - buf (byte-object) -- packet

    Returns: nonce (byte-object) or None if an error occurred
    """
    if not __check_size(buf):
        logging.debug(
            "[PARSER] Incorrect packet size in parse_peer_verification")
        return None

    (_, _, nonce) = unpack(FORMAT_PEER_VERIFICATION, buf)
    return nonce


def parse_peer_validation(buf):
    """Reads a PEER_VALIDATION by checking the header and returning the
    bit field as a boolean. Assumes that the message type is PEER_VALIDATION.

    Arguments:
    - buf (byte-object) -- packet

    Returns: valid (boolean) or None if an error occurred
    """
    if not __check_size(buf):
        logging.debug(
            "[PARSER] Incorrect packet size in parse_peer_validation")
        return None

    (_, _, _, valid) = unpack(FORMAT_PEER_VALIDATION, buf)
    # valid: test if first bit is set
    return valid & 1 != 0


def pack_peer_announce(id, ttl, data_type, data):
    """Packs a peer announce message as byte-object.

    Arguments:
    - id (int) -- unique message id for this message, stays the same when
                  forwarding
    - ttl (int) -- Time to live. 0 for infinite
    - data_type (int)
    - data (byte-object)

    Returns:
      packet as byte-object
    """
    size = 16 + len(data)
    buf = pack(FORMAT_PEER_ANNOUNCE, size, PEER_ANNOUNCE,
               id, ttl, 0, data_type) + data
    return buf


def pack_peer_discovery(challenge):
    """Packs a peer discovery message as byte-object.

    Arguments:
    - challenge (int) -- challenge for peer offer response.

    Returns: packet as byte-object
    """
    buf = pack(FORMAT_PEER_DISCOVERY, 12, PEER_DISCOVERY, challenge)
    return buf


def pack_peer_offer(challenge, nonce, data):
    """Packs a peer offer message as byte-object.

    Arguments:
    - challenge (int) -- challenge received from original peer discovery.
    - nonce (int) -- nonce according to documentation

    Returns: packet as byte-object
    """
    data_bytes = (",".join(data)).encode("utf-8")
    size = 20 + len(data_bytes)
    buf = pack(FORMAT_PEER_OFFER, size, PEER_OFFER, challenge, nonce)
    return buf + data_bytes


def pack_peer_info(p2p_listening_port):
    """Packs a peer info message as byte-object.

    Arguments:
    - p2p_listening_port (int) -- Port this peer accepts new peer connections
      at

    Returns: peer info packet as byte-object
    """
    buf = pack(FORMAT_PEER_INFO, 8, PEER_INFO, 0, p2p_listening_port)
    return buf


def pack_peer_challenge(challenge):
    """Builds a PEER_CHALLENGE packet.

    Arguments:
    - challenge (int)

    Returns: buffer (byte-object)
    """
    return pack(FORMAT_PEER_CHALLENGE, 12, PEER_CHALLENGE, challenge)


def pack_peer_verification(nonce):
    """Builds a PEER_VERIFICATION packet.

    Arguments:
    - nonce (int)

    Returns: buffer (byte-object)
    """
    return pack(FORMAT_PEER_VERIFICATION, 12, PEER_VERIFICATION, nonce)


def pack_peer_validation(valid):
    """Builds a PEER_VALIDATION packet.

    Arguments:
    - valid (boolean)

    Returns: buffer (byte-object b'...')"""
    if valid:
        bit = 1
    else:
        bit = 0
    return pack(FORMAT_PEER_VALIDATION, 8, PEER_VALIDATION, 0, bit)
