""" This module handles everything packets.
    The goal is to provide one place for packet parsing safety
"""

from struct import unpack, error

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
           tuple (size, type, ttl, res, datatype, data     )
           as    (int , int , int, int, int     , byte)

           tuple (): Error"""
    # check header: size
    if not(__check_size(buf)):
        # print("!! packet size incorrect")
        return ()

    try:
        # TODO: check header type
        # TODO: return stripped header
        packet_no_data = unpack(FORMAT_GOSSIP_ANNOUNCE, buf[:8])
        data = (buf[8:],)
        return packet_no_data + data
    except error:
        # print("!! Struct parsing error.")
        return ()


def parse_gossip_notify(buf):
    """Parses a GOSSIP NOTIFY to a human-readable 6-tuple
       [!] Does not check for any correctness in the body fields!

       Arguments:
           buf -- packet as byte-object

       Returns:
           body as tuple  (datatype)
                          (int     )

           Error as tuple ()"""

    # check header: size
    if not(__check_size(buf)):
        # print("!! packet size incorrect")
        return ()

    try:
        packet_tuple = unpack(FORMAT_GOSSIP_NOTIFY, buf)
        if packet_tuple[1] == GOSSIP_NOTIFY:
            # strip header
            stripped_packet = packet_tuple[2:4]
            return stripped_packet
        else:
            return ()
    except error:
        # print("!! Struct parsing error.")
        return ()


def parse_gossip_notification(buf):
    return


def parse_gossip_validation(buf):
    return
