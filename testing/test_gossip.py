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
from context import gossip
import hashlib


# TODO: delete
GOSSIP_NOTIFY = 501
GOSSIP_NOTIFICATION = 502
GOSSIP_VALIDATION = 503
FORMAT_GOSSIP_NOTIFY = "!HHHH"
FORMAT_GOSSIP_NOTIFICATION = "!HHHH"
FORMAT_GOSSIP_VALIDATION = "!HHHH"


async def main():
    await test_handshake()
    # await test_peer_announce()
    # await test_gossip_announce()
    return


async def test_handshake():
    print("[test_handshake] Starting Test...")
    peer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("[test_handshake] Connecting mock peer to our program")
    peer.connect(('127.0.0.1', 6001))
    print("[test_handshake] Sending mock peers PEER INFO")
    peer.send(pp.pack_peer_info(6300))
    peer.flush()
    buf = await await_message(peer)
    print("[test_handshake] Received PEER CHALLENGE")
    if len(buf) == int.from_bytes(buf[:2], "big"):
        print("[test_handshake] PEER CHALLENGE size field is correct")
    else:
        print("[test_handshake] ERROR - PEER CHALLENGE size \
               field is not correct")
    if int.from_bytes(buf[2:4], "big") == pp.PEER_CHALLENGE:
        print("[test_handshake] PEER CHALLENGE message type is correct")
    else:
        print("[test_handshake] ERROR - PEER CHALLENGE message \
               type is not correct")
    challenge = buf[4:]
    nonce = 0
    while nonce < (2**64)-1:
        hash_val = \
            hashlib.sha256(nonce.to_bytes(8, "big") + challenge).hexdigest()
        if hash_val[:4] == '0000':
            break
        nonce += 1
    # Send PEER VERIFICATION
    peer.send(pp.pack_peer_verification(nonce))
    peer.flush()
    # buf = await_message(peer)
    peer.close()
    return


async def test_peer_announce():
    """This test subscribes with 2 APIs to the datatype 1 and validates with
    both after the PEER_ANNOUNCE"""
    print("[test_peer_announce] Starting Test")
    api1_correct = False
    api2_correct = False
    peer2_correct = True
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
    # Connect peers
    print("[test_peer_announce] Connecting peers, performing Handshake")
    peer1.connect(('127.0.0.1', 6001))
    asyncio.create_task(handshake_handler(peer1))
    peer2.connect(('127.0.0.1', 6001))
    asyncio.create_task(handshake_handler(peer1))

    # task_peer1 = asyncio.create_task(await_message(peer1))
    task_peer2 = asyncio.create_task(pannounce_peer2_handler(peer2))
    # Send PEER_ANNOUNCE
    peer1.sendall(pp.pack_peer_announce(1, 2, 1, b''))

    # Check for received GOSSIP_NOTIFICATION
    asyncio.create_task(pannounce_api1_handler(api1))
    asyncio.create_task(pannounce_api2_handler(api2))

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
    return


async def handshake_handler(socket):
    # Send PEER INFO
    socket.sendall(pp.pack_peer_info(10000))
    # Catch PEER CHALLENGE
    buf = await await_message(socket)
    challenge = buf[4:]
    # Generate Nonce
    nonce = 0
    while nonce < (2**64)-1:
        hash_val = \
            hashlib.sha256(nonce.to_bytes(8, "big") + challenge).hexdigest()
        if hash_val[:4] == '0000':
            break
        nonce += 1
    # Send PEER VERIFICATION
    socket.sendall(pp.pack_peer_verification(nonce))
    # Ignore PEER VALIDATION
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


async def test_gossip_announce():
    """Test GOSSIP ANNOUNCE functionality by:
    1. Subscribing with 2 API mocks
    2. Add a peer mock
    3. Sending a GOSSIP ANNOUNCE with one API
    4. Checking if we receive it with the second
    5. Checking if we got a PEER ANNOUNCE at the peer mock
    """
    print("[test_gossip_announce] Starting Test")
    api2_correct = False
    peer_correct = False

    peer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    api1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    api2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 1. Connect with both apis
    print("[test_gossip_announce] Connecting with APIs")
    api1.connect(('127.0.0.1', 7001))
    api2.connect(('127.0.0.1', 7001))
    # Subscribe to Datatype 1
    print("[test_gossip_announce] Subscribing with APIs to Datatype 1")
    api1.sendall(struct.pack(FORMAT_GOSSIP_NOTIFY, 8,
                             GOSSIP_NOTIFY, 0, 1))
    api2.sendall(struct.pack(FORMAT_GOSSIP_NOTIFY, 8,
                             GOSSIP_NOTIFY, 0, 1))
    # 2. Connect peer
    print("[test_gossip_announce] Connecting with Peer")
    peer.connect(('127.0.0.1', 6001))

    # TODO Handshake

    # Start Listeners
    task_api2 = asyncio.create_task(gannounce_api2_handler(api2))
    asyncio.create_task(gannounce_peer_handler(peer))
    # 3. Send GOSSIP ANNOUNCE with api1
    print("[test_gossip_announce] Send GOSSIP ANNOUNCE with API 1")
    api1.sendall(struct.pack(pp.FORMAT_GOSSIP_ANNOUNCE, 8, pp.GOSSIP_ANNOUNCE,
                             2, 0, 1) + b'')

    await asyncio.sleep(1)

    # 4. Check if api2 got GOSSIP ANNOUNCE
    if task_api2.done() and api2_correct:
        print("[test_gossip_announce][TEST 01]: GOSSIP NOTIFICATIONs - \
               correct, received GOSSIP ANNOUNCE at API 2")
    else:
        print("[test_gossip_announce][TEST 01]: GOSSIP NOTIFICATIONs - \
               wrong, did NOT receive GOSSIP ANNOUNCE at API 2")
    # 5. Check if peer2 got peer announce
    if peer_correct:
        print("[test_gossip_announce][TEST 02]: PEER ANNOUNCE - \
               correct, received PEER ANNOUNCE at Peer")
    else:
        print("[test_gossip_announce][TEST 01]: PEER ANNOUNCE - \
               wrong, did not receive PEER ANNOUNCE at Peer")
    close_all([peer, api1, api2])
    return


async def gannounce_api2_handler(socket):
    buf = await await_message(socket)
    if buf is None:
        return
    mtype = pp.get_header_type(buf)
    if mtype == pp.GOSSIP_NOTIFICATION:
        global api2_correct
        api2_correct = True
    return


async def gannounce_peer_handler(socket):
    buf = await await_message(socket)
    if buf is None:
        return
    mtype = pp.get_header_type(buf)
    if mtype == pp.PEER_ANNOUNCE:
        global peer_correct
        peer_correct = True
    return


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        exit()
