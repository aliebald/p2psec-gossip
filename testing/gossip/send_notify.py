import socket
import struct
import time

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect(('127.0.0.1', 7001))
    s.sendall(struct.pack("!HHHH", 8, 501, 0, 1))
    while True:
        time.sleep(1)
