"""Black Box Testing of the central Gossip class.
HOWTO:
    1. Run the main.py
    2. Run this program

We send messages and await a certain correct answer.
Otherwise the test fails.
"""

import socket
import struct
import asyncio
from context import packet_parser as pp

GOSSIP_NOTIFY = 501
GOSSIP_NOTIFICATION = 502
GOSSIP_VALIDATION = 503
FORMAT_GOSSIP_NOTIFY = "!HHHH"
FORMAT_GOSSIP_NOTIFICATION = "!HHHH"
FORMAT_GOSSIP_VALIDATION = "!HHHH"


def main():
    asyncio.run(test_peer_announce())
    test_gossip_announce()


async def test_peer_announce():
    """This test subscribes with 2 APIs to the datatype 1 and validates with
    both after the PEER_ANNOUNCE"""
    peer1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    peer2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    api1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    api2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect with both apis
    api1.connect(('127.0.0.1', 7001))
    api2.connect(('127.0.0.1', 7001))
    # Subscribe to Datatype 1
    api1.sendall(struct.pack(FORMAT_GOSSIP_NOTIFY, 8,
                             GOSSIP_NOTIFY, 0, 1))
    api2.sendall(struct.pack(FORMAT_GOSSIP_NOTIFY, 8,
                             GOSSIP_NOTIFY, 0, 1))
    # Connect peers
    peer1.connect(('127.0.0.1', 6001))
    peer2.connect(('127.0.0.1', 6001))
    # Send PEER_ANNOUNCE
    peer1.sendall(pp.pack_peer_announce(1, 2, 1, b''))
    peer1_buf = await asyncio.create_task(await_message(peer1))
    peer2_buf = await asyncio.create_task(await_message(peer2))

    # Check for received GOSSIP_NOTIFICATION
    api1_buf = asyncio.create_task(await await_message(api1))
    api2_buf = asyncio.create_task(await await_message(api2))
    (api1_msg_id, api1_dtype, api1_data) = \
        pp.parse_gossip_notification(api1_buf)
    (api2_msg_id, api2_dtype, api2_data) = \
        pp.parse_gossip_notification(api2_buf)
    if (api1_msg_id == 1 and api1_dtype == 1 and api1_data == b'')\
       and \
       (api2_msg_id == 1 and api2_dtype == 1 and api2_data == b''):
        print("[TEST 01]: GOSSIP_NOTIFICATIONs - correct")
    else:
        print("[TEST 01]: GOSSIP_NOTIFICATIONs - wrong")

    # Send GOSSIP_VALIDATION
    api1.sendall(struct.pack(FORMAT_GOSSIP_VALIDATION, 8,
                             GOSSIP_VALIDATION, 1, 1))
    api2.sendall(struct.pack(FORMAT_GOSSIP_VALIDATION, 8,
                             GOSSIP_VALIDATION, 1, 1))

    # Check: Peer 2 got PEER_ANNOUNCE, Peer 1 should not
    (_, _, peer_id, peer_ttl, peer_dtype, peer_data) = \
        pp.parse_peer_announce(peer2_buf)
    if((not peer1_buf.done()) and peer_id == 1 and peer_ttl == 1 and
       peer_dtype == 1 and peer_data == b''):
        print("[TEST 02]: PEER_ANNOUNCE - correct")
    else:
        print("[TEST 02]: PEER_ANNOUNCE - wrong")

    api1.close()
    api2.close()
    peer1.close()
    peer2.close()


async def await_message(socket):
    size_bytes = socket.recv(2)
    size = int.from_bytes(size_bytes, "big")
    buf = size_bytes + socket.recv(size)
    return buf


def test_gossip_announce(): pass


if __name__ == "__main__":
    main()
