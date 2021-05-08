""" This module handles everything packets.
    The goal is to provide one place for packet parsing safety
"""

from struct import pack, unpack

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


def get_header_size(buf):
    """Returns the body size in the packet header
       Input:  packet as byte-object
       Return: boolean"""
    return int.from_bytes(buf[:2], "big")


def get_header_type(buf):
    """Returns the message type in the packet header
       Input: packet as byte-object
       Return: boolean"""
    return int.from_bytes(buf[2:4], "big")


def parse_gossip_announce(buf):
    """Parses a gossip_announce to a human-readable 6-tuple or null
       [!] Does not check for correct subscriber datatype

       Input: packet as byte-object
       Return: tuple  
               as    (int,int,int,int,int,string)
       Error: return Null
    """
    # TODO: try catch mit unpack format fehler
    # TODO: falscher type?
    # TODO: 
    packet_no_data = unpack(FORMAT_GOSSIP_ANNOUNCE, buf[:8])
    data = (bytes.decode(buf[8:]),)
    return packet_no_data + data
