"""Black Box Testing of the central Gossip class.
HOWTO:
    1. Run the main.py on the default port.
    2. Run this program
    3. Be patient after PEER INFO, we have to wait for the interval (see doc)

This program is a mock peer that tries to perform the handshake.
"""

import socket
import asyncio
from context import packet_parser as pp
from context import util as util
import hashlib


async def main():
    await test_handshake()
    return


async def test_handshake():
    peer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("[test_handshake] Connecting mock peer to our program")
    peer.connect(('127.0.0.1', 6001))
    print("[test_handshake] Sending mock peers PEER INFO")
    peer.send(pp.pack_peer_info(6300))
    print("[test_handshake] Waiting for the PEER CHALLENGE at the end of the "
          +
          "receivers interval...")
    buf = await await_message(peer)
    print("[test_handshake] Received PEER CHALLENGE")
    if len(buf) == int.from_bytes(buf[:2], "big"):
        print("[test_handshake] PEER CHALLENGE size field is correct")
    else:
        print("[test_handshake] ERROR - PEER CHALLENGE size " +
              "field is not correct")
    if int.from_bytes(buf[2:4], "big") == pp.PEER_CHALLENGE:
        print("[test_handshake] PEER CHALLENGE message type is correct")
    else:
        print("[test_handshake] ERROR - PEER CHALLENGE message " +
              "type is not correct")
    challenge = pp.parse_peer_challenge(buf)
    # TODO check for None
    nonce = util.produce_pow_peer_challenge(challenge)
    # Send PEER VERIFICATION
    print("[test_handshake] Sending PEER VERIFICATION after calculating nonce")
    peer.send(pp.pack_peer_verification(nonce))

    buf = await await_message(peer)
    if pp.get_header_type(buf) == pp.PEER_VALIDATION:
        print("[test_handshake] PEER VALIDATION message received!")

    peer.close()
    print("[test_handshake] Test complete")
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

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        exit()
