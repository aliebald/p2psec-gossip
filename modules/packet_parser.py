""" This module handles everything packets.
    The goal is to provide one place for packet parsing safety
"""

from struct import pack, unpack, error

GOSSIP_ANNOUNCE = 500
GOSSIP_NOTIFY = 501
GOSSIP_NOTIFICATION = 502
GOSSIP_VALIDATION = 503

# struct formats for API packets
# !! no data is included as size is variable
FORMAT_GOSSIP_ANNOUNCE = "!HHBBH"
FORMAT_GOSSIP_NOTIFY = "!HHHH"
FORMAT_GOSSIP_NOTIFICATION = "!HHHH"
FORMAT_GOSSIP_VALIDATION = "!HHHH"


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
    """ Compares the packet size to the size given in the header.

    Arguments:
        buf -- packet as byte-object

    Returns:
        bool"""
    return len(buf) == __get_header_size(buf)


def parse_gossip_announce(buf):
    """Parses a gossip_announce to a human-readable 6-tuple
       [!] Does not check for any correctness in the body fields!

       Arguments:
           buf -- packet as byte-object

       Returns:
           tuple (size, type, ttl, res, datatype, data )
           as    (int , int , int, int, int     , bytes)

           tuple (): Error"""
    # check header: size
    if not(__check_size(buf)):
        return ()

    try:
        packet_no_data = unpack(FORMAT_GOSSIP_ANNOUNCE, buf[:8])
        data = (buf[8:],)

        if packet_no_data[1] == GOSSIP_ANNOUNCE:
            return packet_no_data[2:] + data
        else:
            return ()
    except error:
        return ()


def parse_gossip_notify(buf):
    """Parses a GOSSIP NOTIFY to a human-readable 1-tuple
       [!] Does not check for any correctness in the body fields!

       Arguments:
           buf -- packet as byte-object

       Returns:
           datatype as int

           Error as tuple ()"""

    # check header: size
    if not(__check_size(buf)):
        return ()
    # check: no data present
    if __get_header_size(buf) != 8:
        return ()

    try:
        packet_tuple = unpack(FORMAT_GOSSIP_NOTIFY, buf)

        if packet_tuple[1] == GOSSIP_NOTIFY:
            # strip header
            datatype = packet_tuple[3]
            return datatype
        else:
            return ()
    except error:
        return ()


def parse_gossip_notification(buf):
    """Parses a GOSSIP NOTIFICATION to a human-readable 6-tuple
       [!] Does not check for any correctness in the body fields!

       Arguments:
           buf -- packet as byte-object

       Returns:
           body as tuple  (msg_id, datatype, data )
                          (int   , int     , bytes)

           Error as tuple ()"""
    # check header: size
    if not(__check_size(buf)):
        return ()

    try:
        packet_tuple_no_data = unpack(FORMAT_GOSSIP_NOTIFICATION, buf[:8])
        data = (buf[8:],)
        # check msg_type
        if packet_tuple_no_data[1] == GOSSIP_NOTIFICATION:
            # strip header
            stripped_packet = packet_tuple_no_data[2:]
            return stripped_packet + data
        else:
            return ()
    except error:
        return ()


def parse_gossip_validation(buf):
    """Parses a GOSSIP VALIDATION to a human-readable 6-tuple
       [!] Does not check for any correctness in the body fields!

       Arguments:
           buf -- packet as byte-object

       Returns:
           body as tuple  (msg_id, V   )
                          (int   , bool)

           Error as tuple ()"""
    # check header: size
    if not(__check_size(buf)):
        return ()

    try:
        packet_tuple = unpack(FORMAT_GOSSIP_VALIDATION, buf[:8])
        if packet_tuple[1] == GOSSIP_VALIDATION:
            # strip header
            # (msg_id, int)
            packet_tuple_stripped = packet_tuple[2:]
            if packet_tuple_stripped[1] > 1:
                return ()
            else:
                return (packet_tuple_stripped[0],
                        packet_tuple_stripped[1] == 1)
        else:
            return ()
    except error:
        return ()


def build_gossip_notification(msg_id, datatype, data):
    """Builds a GOSSIP_NOTIFICATION packet as a byte object from arguments

    Arguments:
        int   , int     , String
        msg_id, datatype, data

    Returns:
        message as byte-object b'...'
        or none if error"""

    if msg_id > 2**16 or msg_id < 0:
        return None
    elif datatype > 2**16 or msg_id < 0:
        return None

    data_bytes = bytes(data, 'utf-8')
    size = 8 + len(data_bytes)
    if size > 2**16:
        return None
    buf = pack(FORMAT_GOSSIP_NOTIFICATION, size, GOSSIP_NOTIFICATION,
               msg_id, datatype)
    buf += data_bytes
    return buf
