"""
This Module provides the Peer_connection class as well as a factory method for
it (peer_connection_factory())
"""

import asyncio
import time
from random import getrandbits

from modules.pow_producer import produce_pow_peer_offer, valid_nonce_peer_offer
from modules.peers.peer_packet_parser import (
    PEER_DISCOVERY,
    PEER_OFFER,
    PEER_INFO,
    get_header_type,
    pack_peer_announce,
    pack_peer_discovery,
    pack_peer_offer,
    pack_peer_info,
    parse_peer_discovery,
    parse_peer_offer,
    parse_peer_info
)


# Timeout for challenges in seconds. After this timeout, a challenge is invalid
CHALLENGE_TIMEOUT = 300


class Peer_connection:
    """A Peer_connection represents a connection to a single peer.

    Class variables:
    - gossip (Gossip) -- gossip responsible for this peer
    - reader (StreamReader) -- (private) asyncio StreamReader of connected peer
    - writer (StreamWriter) -- (private) asyncio StreamWriter of connected peer
    - peer_p2p_listening_port (int) -- p2p_listening_port of connected peer
    - last_challenges -- (private) list of send challenges combined with a
                         timeout. Format: [(challenge, timeout)]
                         When the current time is greater than timeout, the
                         challenge is no longer valid
    """

    def __init__(self, reader, writer, gossip, peer_p2p_listening_port=None):
        """
        Arguments:
        - reader (StreamReader) -- asyncio StreamReader of connected peer
        - writer (StreamWriter) -- asyncio StreamWriter of connected peer
        - gossip (Gossip) -- gossip responsible for this peer
        - peer_p2p_listening_port (int) -- (Optional, default: None) Port the
          connected peer accepts new peer connections at
        """
        self.gossip = gossip
        self.__reader = reader
        self.__writer = writer
        self.peer_p2p_listening_port = peer_p2p_listening_port
        self.__last_challenges = []

    async def run(self):
        """Waits for incoming messages and handles them. Runs until the
        connection is closed"""
        while True:
            try:
                buf = await self.__reader.read(4096)  # TODO buffersize?
            except ConnectionError:
                await self.gossip.close_peer(self)
                return
            await self.__handle_incoming_message(buf)

    async def close(self):
        """Closes the connection to the peer.
        Gossip.close_peer() should be called preferably, since it also removes 
        the peer from the peer list."""
        print("Connection to {} closed".format(self.get_debug_address()))
        try:
            self.__writer.close()
            await self.__writer.wait_closed()
        except:
            return

    def get_peer_p2p_listening_address(self):
        """Returns the address the connected peer accepts new peer connections
        on.

        Returns:
            If known, p2p listening address of peer in the format host:port,
            otherwise None 

        See also:
        - get_own_address()
        - get_peer_address()
        - get_debug_address() - for debug output
        """
        if self.peer_p2p_listening_port == None:
            return None
        (host, _) = self.__writer.get_extra_info('peername')
        address = "{}:{}".format(host, self.peer_p2p_listening_port)
        return address

    def get_peer_address(self):
        """Returns the address of this peer in the format host:port

        See also:
        - get_own_address()
        - get_peer_p2p_listening_address()
        - get_debug_address() - for debug output
        """
        # TODO returns None on error
        (host, port) = self.__writer.get_extra_info('peername')
        address = "{}:{}".format(host, port)
        return address

    def get_own_address(self):
        """Returns the address of this peer in the format host:port

        See also:
        - get_peer_address()
        - get_peer_p2p_listening_address()
        - get_debug_address() - for debug output
        """
        (host, port) = self.__writer.get_extra_info('sockname')
        address = "{}:{}".format(host, port)
        return address

    def get_debug_address(self):
        """Returns the name/address for debug output.
        Only use for debug output!

        Returns:
            If we know the p2p_listening_port, we will return the p2p listening
            address of the connected peer, otherwise ist address (with the
            random port instead of the p2p port and an added *)
        """
        addr = self.get_peer_p2p_listening_address()
        if addr == None:
            addr = self.get_peer_address() + "*"
        return addr

    async def send_peer_discovery(self):
        """Sends a peer discovery message."""
        message = pack_peer_discovery(self.__generate_challenge())
        await self.__send(message)

    async def send_peer_announce(self, id, ttl, data_type, data):
        """Sends a peer announce message. For documentation of parameters, see 
        the project documentation"""
        message = pack_peer_announce(id, ttl, data_type, data)
        await self.__send(message)

    async def __send_peer_offer(self, challenge):
        """Figures out a nonce and sends a peer offer.

        Arguments:
        - challenge (int) -- challenge received from original peer discovery
        """
        # Use target_address to filter the address of the target peer
        target_address = self.get_peer_p2p_listening_address()
        addresses = list(filter(lambda ip: ip != target_address,
                         self.gossip.get_peer_addresses()))

        # Abort if we do not know any other peers
        if len(addresses) == 0:
            print("No other peers connected, do not send peer offer.")
            return

        print("responding with peers: {}\r\n".format(addresses))
        # pack peer offer and figure out a valid nonce
        message = pack_peer_offer(challenge, 0, addresses)
        message = produce_pow_peer_offer(message)
        if message == None:
            print("WARNING: Failed to find valid nonce for peer offer!")
            return

        await self.__send(message)

    async def __send(self, message):
        """Sends a message to the connected peer. Should be awaited

        Arguments:
        - message (byte-object) -- message that should be send
        """
        self.__writer.write(message)
        await self.__writer.drain()

    def __generate_challenge(self):
        """Generates and saves a single use challenge"""
        challenge = getrandbits(64)
        timeout = time.time() + CHALLENGE_TIMEOUT
        self.__last_challenges.append((challenge, timeout))
        return challenge

    def __check_challenge(self, challenge):
        """Checks if the given challenge was send from this peer and has not
        yet expired. Also removes the challenge from the saved challenges.

        Arguments:
        - challenge (int) -- challenge to check

        Returns:
            True if the challenge is valid and has not expired.
        """
        for (saved_challenge, timeout) in self.__last_challenges:
            if saved_challenge == challenge:
                self.__last_challenges.remove((saved_challenge, timeout))
                return timeout >= time.time()
        return False

    async def __handle_incoming_message(self, buf):
        """Checks the type of an incoming message in byte format and calls the
        correct handler according the the type. 

        Arguments:
        - buf (byte-object) -- received message
        """
        type = get_header_type(buf)
        if type == PEER_DISCOVERY:
            print("\r\nReceived PEER_DISCOVERY from", self.get_debug_address())
            await self.__handle_peer_discovery(buf)
        elif type == PEER_OFFER:
            print("\r\nReceived PEER_OFFER from", self.get_debug_address())
            await self.__handle_peer_offer(buf)
        elif type == PEER_INFO:
            print("Received PEER_INFO from", self.get_debug_address())
            self.__handle_peer_info(buf)
        else:
            print("\r\nReceived message with unknown type {} from {}".format(
                type, self.get_debug_address()))

    async def __handle_peer_discovery(self, buf):
        """Handles a peer discovery message and calls __send_peer_offer() to
        send a response.

        Arguments:
        - buf (byte-object) -- received message in byte format. The type must 
          be PEER_DISCOVERY
        """
        msg = parse_peer_discovery(buf)
        if (msg == None):
            return

        (size, type, challenge) = msg
        await self.__send_peer_offer(challenge)

    async def __handle_peer_offer(self, buf):
        """Handles a peer offer message. 
        Calls offer_peers() of gossip if everything is ok.

        Arguments:
        - buf (byte-object) -- received message in byte format. The type must 
          be PEER_DISCOVERY
        """
        msg = parse_peer_offer(buf)
        if (msg == None):
            return
        (size, type, challenge, nonce, data) = msg
        # Check for invalid challenge
        if not self.__check_challenge(challenge):
            print("Received invalid challenge in peer offer")
            return

        # Check nonce
        if not valid_nonce_peer_offer(buf):
            print("Received invalid nonce in peer offer")
            return
        # check if the offer contains our own address
        p2p_address = self.gossip.config.p2p_address
        if p2p_address in data:
            print("WARNING: own p2p address found in peer offer!")
            data = list(filter(lambda ip: ip != p2p_address, data))

        # save data / pass it to gossip
        await self.gossip.offer_peers(data)

    def __handle_peer_info(self, buf):
        """Handles a peer info message. Saves the received p2p_listening_port.

        Arguments:
        - buf (byte-object) -- received message in byte format. The type must
          be PEER_INFO
        """
        msg = parse_peer_info(buf)
        if msg == None:
            return
        (size, type, port) = msg

        # check if we already know the p2p_listening_port of the other peer
        if self.peer_p2p_listening_port != None:
            warning = ("WARNING: received PEER INFO but already knew the"
                       "p2p_listening_port!\r\nOld port: {}, new Port: {}")
            print(warning.format(self.peer_p2p_listening_port, port))

        # save new port
        print("Saving p2p_listening_port", port)
        self.peer_p2p_listening_port = port


async def peer_connection_factory(addresses, gossip, p2p_listening_port):
    """Connects to multiple addresses of peers.

    Arguments:
    - addresses (str List) -- list containing addresses to other peers. 
      Format: host_ip:port
    - gossip (Gossip) -- gossip instance responsible for potential 
      Peer_connection's
    - p2p_listening_port (int) -- Port this peer accepts new peer connections 
      at

    Returns:
        List containing Peer_connection objects. Empty if no connection can
        be established
    """
    async def helper(addr, gossip, p2p_listening_port, peers):
        peers.append(await __connect_peer(addr, gossip, p2p_listening_port))

    peers = []
    # concurrently connect to all addresses
    tasks = [asyncio.create_task(
        helper(addr, gossip, p2p_listening_port, peers)) for addr in addresses]
    await asyncio.gather(*tasks)

    # Filter failed connections (None values)
    peers = list(filter(lambda peer: peer != None, peers))
    return peers


async def __connect_peer(address, gossip, p2p_listening_port):
    """Opens a connection to the given ip & port and creates a Peer_connection.

    Arguments:
    - ip (str) -- target ip address
    - port (int) -- target port
    - p2p_listening_port (int) -- Port this peer accepts new peer connections 
      at

    Returns:
        None if failed to open the connection. 
        Otherwise a new Peer_connection instance.
    """
    (ip, port) = address.split(":")
    print("connecting to ip: {}, port: {}".format(ip, port))
    try:
        reader, writer = await asyncio.open_connection(ip, int(port))
    except ConnectionRefusedError:
        print("Failed to connect to ip: {}, port: {}\r\n".format(ip, port))
        return None

    await __send_peer_info(writer, p2p_listening_port)
    return Peer_connection(reader, writer, gossip, port)


async def __send_peer_info(writer, p2p_listening_port):
    """Sends a PEER INFO message with p2p_listening_port to the given 
    StreamWriter

    Arguments:
    - writer (StreamWriter) -- StreamWriter connected to a new peer
    - p2p_listening_port (int) -- Port this peer accepts new peer connections
      at
    """
    info_packet = pack_peer_info(p2p_listening_port)
    print("Sending PEER INFO with p2p port {} to {}".format(
        p2p_listening_port, writer.get_extra_info('peername')))
    writer.write(info_packet)
    await writer.drain()
