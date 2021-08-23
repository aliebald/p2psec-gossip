"""This test subscribes with 2 APIs to the datatype 1 and validates with both
after the PEER_ANNOUNCE"""

import socket
import struct
from time import sleep
from context import packet_parser as pp

GOSSIP_NOTIFY = 501
GOSSIP_VALIDATION = 503
FORMAT_GOSSIP_NOTIFY = "!HHHH"
FORMAT_GOSSIP_VALIDATION = "!HHHH"

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as peer:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as api1:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as api2:
            # Connect with both apis
            api1.connect(('127.0.0.1', 7001))
            api2.connect(('127.0.0.1', 7001))
            # Subscribe to Datatype 1
            api1.sendall(struct.pack(FORMAT_GOSSIP_NOTIFY, 8, GOSSIP_NOTIFY,
                                     0, 1))
            api2.sendall(struct.pack(FORMAT_GOSSIP_NOTIFY, 8, GOSSIP_NOTIFY,
                                     0, 1))

            # Connect as peer
            peer.connect(('127.0.0.1', 6001))
            # Send PEER_ANNOUNCE
            peer.sendall(pp.pack_peer_announce(1, 2, 1, b''))

            sleep(5)

            # Send GOSSIP_VALIDATION
            api1.sendall(struct.pack(FORMAT_GOSSIP_VALIDATION, 8,
                                     GOSSIP_VALIDATION, 1, 1))
            api2.sendall(struct.pack(FORMAT_GOSSIP_VALIDATION, 8,
                                     GOSSIP_VALIDATION, 1, 1))

            # Idle
            while True:
                sleep(1)
