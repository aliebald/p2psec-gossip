"""Black Box Testing of the central Gossip class.
HOWTO:
    1. Run the main.py
    2. Run this program
    3. Be patient (~10s)

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

api1_correct = False
api2_correct = False
peer2_correct = True


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
    # task_peer1 = asyncio.create_task(await_message(peer1))
    task_peer2 = asyncio.create_task(peer2_handler(peer2))
    # Send PEER_ANNOUNCE
    peer1.sendall(pp.pack_peer_announce(1, 2, 1, b''))

    # Check for received GOSSIP_NOTIFICATION
    asyncio.create_task(api1_handler(api1))
    asyncio.create_task(api2_handler(api2))

    await asyncio.sleep(1)

    if api1_correct and api2_correct:
        print("[TEST 01]: GOSSIP_NOTIFICATIONs - correct")
    else:
        print("[TEST 01]: GOSSIP_NOTIFICATIONs - wrong")

    # Send GOSSIP_VALIDATION
    api1.sendall(struct.pack(FORMAT_GOSSIP_VALIDATION, 8,
                             GOSSIP_VALIDATION, 1, 1))
    api2.sendall(struct.pack(FORMAT_GOSSIP_VALIDATION, 8,
                             GOSSIP_VALIDATION, 1, 1))

    await asyncio.sleep(1)

    # Check: Peer 2 got PEER_ANNOUNCE, Peer 1 should not
    if task_peer2.done() and peer2_correct:
        print("[TEST 02]: PEER_ANNOUNCE - correct")

    close_all([api1, api2, peer1, peer2])


def close_all(socket_list):
    for s in socket_list:
        s.close()


async def await_message(socket):
    try:
        size_bytes = socket.recv(2)
        size = int.from_bytes(size_bytes, "big")
        buf = size_bytes + socket.recv(size)
        return buf
    except OSError:
        return None


async def api1_handler(socket):
    buf = await await_message(socket)
    if buf is None:
        return
    mtype = pp.get_header_type(buf)
    if mtype == pp.GOSSIP_NOTIFICATION:
        global api1_correct
        api1_correct = True
    return


async def api2_handler(socket):
    buf = await await_message(socket)
    if buf is None:
        return
    mtype = pp.get_header_type(buf)
    if mtype == pp.GOSSIP_NOTIFICATION:
        global api2_correct
        api2_correct = True
    return


async def peer2_handler(socket):
    buf = await await_message(socket)
    if buf is None:
        return
    mtype = pp.get_header_type(buf)
    if mtype == pp.PEER_ANNOUNCE:
        global peer2_correct
        peer2_correct = False
    return


def test_gossip_announce(): pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
