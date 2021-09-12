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


async def main():
    await test_gossip_announce()
    return


async def test_gossip_announce():
    """This test subscribes with 2 APIs to the datatype 1 and validates with
    both after the PEER_ANNOUNCE"""
    peer1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    api1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    api2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Api1 Setup
    api1.connect(('127.0.0.1', 7001))
    api1.sendall(struct.pack(pp.FORMAT_GOSSIP_NOTIFY, 8,
                             pp.GOSSIP_NOTIFY, 0, 1))

    # Api2 Setup
    api2.connect(('127.0.0.1', 7001))
    api2.sendall(struct.pack(pp.FORMAT_GOSSIP_NOTIFY, 8,
                             pp.GOSSIP_NOTIFY, 0, 1))

    # Connect peers, perform handshake
    print("Connecting peers, performing Handshake by waiting for intervall..")
    peer1.connect(('127.0.0.1', 6001))
    task_handshake1 = asyncio.create_task(perform_handshake(peer1, 6001))

    handshakes = asyncio.gather(task_handshake1)

    # Wait for the handshake to complete
    await handshakes
    print("[+] Handshake finished")

    # Send GOSSIP ANNOUNCE with Api1
    api1.sendall(struct.pack(pp.FORMAT_GOSSIP_ANNOUNCE+"H", 12,
                             pp.GOSSIP_ANNOUNCE, 2, 0, 1, 0))

    task_api2 = asyncio.create_task(api2_handler(api2))

    # Send PEER_ANNOUNCE with Peer1
    peer1.send(pp.pack_peer_announce(1, 2, 1, b''))
    print("Sent PEER ANNOUNCE with Peer1")

    await api_tasks

    close_all([api1, api2, peer1])
    return


async def perform_handshake(socket, port):
    # Send PEER INFO
    socket.sendall(pp.pack_peer_info(port))
    # Catch PEER CHALLENGE
    buf = await await_message(socket)
    challenge = pp.parse_peer_challenge(buf)
    # Generate Nonce
    nonce = util.produce_pow_peer_challenge(challenge)
    # Send PEER VERIFICATION
    socket.sendall(pp.pack_peer_verification(nonce))
    # Ignore PEER VALIDATION
    buf = await await_message(socket)
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


async def api1_handler(socket):
    buf = await await_message(socket)
    if buf is None:
        return
    mtype = pp.get_header_type(buf)
    if mtype == pp.GOSSIP_NOTIFICATION:
        print("[+] Received GOSSIP NOTIFICATION with Api1")
        socket.send(struct.pack(pp.FORMAT_GOSSIP_VALIDATION, 8,
                    pp.GOSSIP_VALIDATION, 1, 1))
    else:
        print("[-]: Did not receive GOSSIP NOTIFICATION with Api1")
    return


async def api2_handler(socket):
    buf = await await_message(socket)
    if buf is None:
        return
    mtype = pp.get_header_type(buf)
    if mtype == pp.GOSSIP_NOTIFICATION:
        print("[+] Received GOSSIP NOTIFICATION with Api2")
        socket.send(struct.pack(pp.FORMAT_GOSSIP_VALIDATION, 8,
                    pp.GOSSIP_VALIDATION, 1, 1))
    else:
        print("[-]: Did not receive GOSSIP NOTIFICATION with Api2")
    return


async def peer2_handler(socket):
    while True:
        buf = await await_message(socket)
        if buf is None:
            print("Peer2 - Opposing socket closed")
            break
        mtype = pp.get_header_type(buf)
        if mtype == pp.PEER_ANNOUNCE:
            print("[+]: Peer2 received PEER ANNOUNCE")
            break
        elif mtype == pp.PEER_DISCOVERY:
            print("[.] Peer2 received PEER DISCOVERY - ignoring")
            continue
        else:
            print("[-]: Peer2 did not receive PEER_ANNOUNCE")
            break
    return


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        exit()
