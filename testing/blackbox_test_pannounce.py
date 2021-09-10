"""Black Box Testing of the central Gossip class.
HOWTO:
    1. Run the main.py
    2. Run this program
    3. Be patient (~10s)
"""

import socket
import struct
import asyncio
from context import packet_parser as pp
from context import util


# TODO: delete
GOSSIP_NOTIFY = 501
GOSSIP_NOTIFICATION = 502
GOSSIP_VALIDATION = 503
FORMAT_GOSSIP_NOTIFY = "!HHHH"
FORMAT_GOSSIP_NOTIFICATION = "!HHHH"
FORMAT_GOSSIP_VALIDATION = "!HHHH"

api1_correct = False
api2_correct = False
peer2_correct = True


async def main():
    await test_peer_announce()
    return


async def test_peer_announce():
    """This test subscribes with 2 APIs to the datatype 1 and validates with
    both after the PEER_ANNOUNCE"""
    print("[test_peer_announce] Starting Test")
    peer1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    peer2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    api1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    api2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect with both apis
    print("[test_peer_announce] Connecting APIs")
    api1.connect(('127.0.0.1', 7001))
    api2.connect(('127.0.0.1', 7001))
    # Subscribe to Datatype 1
    print("[test_peer_announce] Subscribing APIs to Datatype 1")
    api1.sendall(struct.pack(FORMAT_GOSSIP_NOTIFY, 8,
                             GOSSIP_NOTIFY, 0, 1))
    api2.sendall(struct.pack(FORMAT_GOSSIP_NOTIFY, 8,
                             GOSSIP_NOTIFY, 0, 1))

    # Connect peers, perform handshake
    print("[test_peer_announce] Connecting peers, performing Handshake")
    peer1.connect(('127.0.0.1', 6001))
    task_p1 = asyncio.create_task(perform_handshake(peer1))
    peer2.connect(('127.0.0.1', 6001))
    task_p2 = asyncio.create_task(perform_handshake(peer2))

    # Wait for the handshake to complete
    await task_p1
    await task_p2
    print("[test_peer_announce] Handshakes finished")

    # Let peers listen for messages
    # Peer1: should receive nothing as he sends the PEER ANNOUNCE.
    # Peer2: should receive a PEER ANNOUNCE after the APIs confirm it.
    task_p1 = asyncio.create_task(await_message(peer1))
    task_p2 = asyncio.create_task(pannounce_peer2_handler(peer2))

    # Let APIs listen for GOSSIP_NOTIFICATIONs
    task_a1 = asyncio.create_task(pannounce_api1_handler(api1))
    task_a2 = asyncio.create_task(pannounce_api2_handler(api2))

    # Send PEER_ANNOUNCE with Peer1
    print("[test_peer_announce] Sending PEER ANNOUNCE with Peer1")
    peer1.sendall(pp.pack_peer_announce(1, 2, 1, b''))

    # Await received GOSSIP NOTIFICATIONs on Api1 and Api2
    await task_a1
    await task_a2
    print("[test_peer_announce] Received GOSSIP NOTIFICATIONs with Api1 and " +
          "Api2")

    if api1_correct and api2_correct:
        print("[TEST 01]: GOSSIP_NOTIFICATIONs - correct")
    else:
        print("[TEST 01]: GOSSIP_NOTIFICATIONs - wrong")

    # Send GOSSIP_VALIDATION
    api1.sendall(struct.pack(FORMAT_GOSSIP_VALIDATION, 8,
                             GOSSIP_VALIDATION, 1, 1))
    api2.sendall(struct.pack(FORMAT_GOSSIP_VALIDATION, 8,
                             GOSSIP_VALIDATION, 1, 1))

    # await PEER ANNOUNCE at Peer2
    await task_p2

    # Check: Peer 2 got PEER_ANNOUNCE, Peer 1 should not
    if peer2_correct:
        print("[TEST 02]: PEER_ANNOUNCE - correct")

    close_all([api1, api2, peer1, peer2])
    return


async def perform_handshake(socket):
    # Send PEER INFO
    socket.sendall(pp.pack_peer_info(6001))
    # Catch PEER CHALLENGE
    buf = await await_message(socket)
    challenge = pp.parse_peer_challenge(buf)
    # Generate Nonce
    nonce = util.produce_pow_peer_challenge(challenge)
    # Send PEER VERIFICATION
    socket.sendall(pp.pack_peer_verification(nonce))
    # Ignore PEER VALIDATION
    buf = await_message(socket)
    return


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


async def pannounce_api1_handler(socket):
    buf = await await_message(socket)
    if buf is None:
        return
    mtype = pp.get_header_type(buf)
    if mtype == pp.GOSSIP_NOTIFICATION:
        global api1_correct
        api1_correct = True
    return


async def pannounce_api2_handler(socket):
    buf = await await_message(socket)
    if buf is None:
        return
    mtype = pp.get_header_type(buf)
    if mtype == pp.GOSSIP_NOTIFICATION:
        global api2_correct
        api2_correct = True
    return


async def pannounce_peer2_handler(socket):
    buf = await await_message(socket)
    if buf is None:
        return
    mtype = pp.get_header_type(buf)
    if mtype == pp.PEER_ANNOUNCE:
        global peer2_correct
        peer2_correct = False
    return


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        exit()
