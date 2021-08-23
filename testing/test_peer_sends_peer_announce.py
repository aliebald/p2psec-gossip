# https://stackoverflow.com/questions/42890302/relative-paths-for-modules-in-python
import socket
from time import sleep
from context import packet_parser as pp

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    # Connect as peer
    s.connect(('127.0.0.1', 6001))
    # Send PEER_ANNOUNCE
    s.sendall(pp.pack_peer_announce(1, 2, 1, b''))
    # Wait
    while True:
        sleep(1)
