"""
This Module provides the Peer_connection class as well as a factory method for
it (peer_connection_factory())
"""
import logging
import asyncio
import time
from random import getrandbits

from modules.pow_producer import (
    produce_pow_peer_challenge,
    produce_pow_peer_offer,
    valid_nonce_peer_challenge,
    valid_nonce_peer_offer)
from modules.packet_parser import (
    PEER_ANNOUNCE,
    PEER_CHALLENGE,
    PEER_DISCOVERY,
    PEER_OFFER,
    PEER_INFO,
    PEER_VALIDATION,
    PEER_VERIFICATION,
    get_header_type,
    pack_peer_announce,
    pack_peer_challenge,
    pack_peer_discovery,
    pack_peer_offer,
    pack_peer_info,
    pack_peer_validation,
    pack_peer_verification,
    parse_peer_announce,
    parse_peer_challenge,
    parse_peer_discovery,
    parse_peer_offer,
    parse_peer_info,
    parse_peer_validation,
    parse_peer_verification
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
      timeout. Format: [(challenge, timeout)] When the current time is greater
      than timeout, the challenge is no longer valid
    - peer_challenge (Tuple: int, int) -- challenge with timeout send to 
      connected node. None if none was send.
    - is_trustworthy (boolean) -- whether the connected node is considered 
      trustworthy. A node can proof itself trustworthy by geting validated by 
      us (push peers), see Documentation. Nodes we connect to should be set to 
      be trustworthy by default.
    - is_validated (boolean) -- whether this node is validated by the connected 
      node/peer. Gets updated upon receiving a peer validation.
    """

    def __init__(self, reader, writer, gossip, peer_p2p_listening_port=None,
                 is_validated=False, is_trustworthy=False):
        """
        Arguments:
        - reader (StreamReader) -- asyncio StreamReader of connected peer
        - writer (StreamWriter) -- asyncio StreamWriter of connected peer
        - gossip (Gossip) -- gossip responsible for this peer
        - peer_p2p_listening_port (int) -- (Optional, default: None) Port the
          connected peer accepts new peer connections at
        - is_validated (boolean) -- (Optional, default: False) whether this node
          is validated by the connected node/peer. Gets updated upon receiving
          a peer validation.
        - is_trustworthy (boolean) -- whether the connected node is considered 
          trustworthy. A node can proof itself trustworthy by geting validated
          by us (push peers), see Documentation. Nodes we connect to should be 
          set to be trustworthy.
        """
        self.gossip = gossip
        self.__reader = reader
        self.__writer = writer
        self.peer_p2p_listening_port = peer_p2p_listening_port
        self.__peer_challenge = None
        self.__last_challenges = []
        self.__is_trustworthy = is_trustworthy  # is the connected node trustworthy?
        self.__is_validated = is_validated  # are we validated?

    def __str__(self):
        """called by str(Api_connection). Uses the debug address"""
        return f"Peer<{self.get_debug_address()}>"

    def __repr__(self):
        """Uses the peer address instead of the (more readable but possibly
        less ambiguous) debug address.
        """
        return f"Peer<{self.get_peer_address()}>"

    def __str__(self):
        """called by str(Peer_connection)
           one object should be printed as:
               peer<ip:port>"""
        return "peer<"+self.get_peer_address()+">"

    def __repr__(self):
        """string representation
           one object should be printed as:
               peer<ip:port>"""
        return "peer<"+self.get_peer_address()+">"

    async def run(self):
        """Waits for incoming messages and handles them. Runs until the
        connection is closed"""
        while True:
            if self.__writer.is_closing():
                logging.debug(f"[Peer_connection]: writer is_closing {self}")
                break
            try:
                size_bytes = await self.__reader.read(2)
                size = int.from_bytes(size_bytes, "big")
                buf = size_bytes + await self.__reader.read(size-2)
            except ConnectionError:
                break
            await self.__handle_incoming_message(buf)
        await self.gossip.close_peer(self)

    async def close(self):
        """Closes the connection to the peer.
        Gossip.close_peer() should be called preferably, since it also removes
        the peer from the peer list."""
        logging.info(f"Connection to {self} closed")
        try:
            self.__writer.close()
            await self.__writer.wait_closed()
        except Exception:
            return

    def get_peer_p2p_listening_address(self):
        """Returns the address the connected peer accepts new peer connections
        on.

        Returns:
            If known, p2p listening address of peer in the format host:port,
            otherwise None

        See also:
        - get_own_address()
        - get_peer_address() or repr(Gossip)
        - get_debug_address() or str(Gossip) - for debug output
        """
        if self.peer_p2p_listening_port == None:
            return None
        (host, _) = self.__writer.get_extra_info("peername")
        address = "{}:{}".format(host, self.peer_p2p_listening_port)
        return address

    def get_peer_address(self):
        """Returns the address of this peer in the format host:port.
        This function gets called by repr(Gossip).

        See also:
        - get_own_address()
        - get_peer_p2p_listening_address()
        - get_debug_address() or str(Gossip) - for debug output
        """
        # TODO returns None on error
        (host, port) = self.__writer.get_extra_info("peername")
        address = "{}:{}".format(host, port)
        return address

    def get_own_address(self):
        """Returns the address of this peer in the format host:port

        See also:
        - get_peer_address()
        - get_peer_p2p_listening_address()
        - get_debug_address() - for debug output
        """
        (host, port) = self.__writer.get_extra_info("sockname")
        address = "{}:{}".format(host, port)
        return address

    def get_debug_address(self):
        """Returns the name/address for debug output.
        Only use for debug output!
        This function gets called by str(Gossip)

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
        if not self.__is_trustworthy:
            logging.debug(f"Not sending PEER DISCOVERY since {self} is not "
                          "trustworthy")
            return

        message = pack_peer_discovery(self.__generate_challenge())
        logging.info(f"Sending PEER DISCOVERY to: {self}")
        await self.__send(message)

    async def send_peer_announce(self, id, ttl, data_type, data):
        """Sends a peer announce message. For documentation of parameters, see
        the project documentation"""
        if not self.__is_trustworthy:
            logging.debug(f"Not sending PEER ANNOUNCE since {self} is not "
                          "trustworthy")
            return

        message = pack_peer_announce(id, ttl, data_type, data)
        logging.info(f"Sending PEER ANNOUNCE with id: {id}, ttl: {ttl} and "
                     f" data type: {data_type}, to: {self}")
        await self.__send(message)

    async def send_peer_challenge(self):
        """Sends a peer challenge message and saves the challenge with a 
        timeout in __peer_challenge. Should only be called once per peer and 
        only if we where not the initiator of the connection. 
        See Project Documentation - Push Gossip"""
        # Check if a peer challenge was already send
        if self.__peer_challenge != None:
            logging.warning("Trying to send a peer challenge, even tough a"
                            "challenge has already been send")
            self.__is_trustworthy = False
            await self.gossip.close_peer(self)
            return

        challenge = getrandbits(64)
        self.__peer_challenge = (challenge, time.time() + CHALLENGE_TIMEOUT)
        message = pack_peer_challenge(challenge)
        logging.info(f"Sending PEER CHALLENGE to: {self}")
        await self.__send(message)

    async def __send_peer_validation(self, valid):
        """Sends a peer validation message
        Arguments:
        - valid (bool) -- Valid bit - See project documentation
        """
        message = pack_peer_validation(valid)
        logging.info(f"Sending PEER VALIDATION with valid: {valid}, to: {self}"
                     )
        await self.__send(message)
        # Tell gossip that this peer is now validated, if valid
        if valid:
            self.gossip.validate_peer(self)

    async def __send_peer_verification(self, nonce):
        """Sends a peer verification message.
        Arguments:
        - nonce (int) -- Nonce for challenge received in peer challenge - See 
          project documentation
        """
        message = pack_peer_verification(nonce)
        # TODO handle message = None
        logging.info(f"Sending PEER VERIFICATION to {self}")
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
            logging.debug("[PEER] No other peers connected, do not send " +
                          "PEER OFFER.")
            return

        # pack peer offer and figure out a valid nonce
        message = pack_peer_offer(challenge, 0, addresses)
        message = produce_pow_peer_offer(message)
        if message == None:
            logging.warning("[PEER] Failed to find valid nonce for " +
                            "PEER OFFER!")
            return

        logging.info(f"Sending PEER OFFER to {self} with peers: {addresses}")
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
        if type == PEER_ANNOUNCE:
            logging.info(f"Received PEER_ANNOUNCE from {self}")
            await self.__handle_peer_announce(buf)
        elif type == PEER_DISCOVERY:
            logging.info(f"Received PEER_DISCOVERY from {self}")
            await self.__handle_peer_discovery(buf)
        elif type == PEER_OFFER:
            logging.info(f"Received PEER_OFFER from {self}")
            await self.__handle_peer_offer(buf)
        elif type == PEER_INFO:
            logging.info(f"Received PEER_INFO from {self}")
            self.__handle_peer_info(buf)
        elif type == PEER_CHALLENGE:
            logging.info(f"Received PEER_CHALLENGE from {self}")
            await self.__handle_peer_challenge(buf)
        elif type == PEER_VERIFICATION:
            logging.info(f"Received PEER_VERIFICATION from {self}")
            await self.__handle_peer_verification(buf)
        elif type == PEER_VALIDATION:
            logging.info(f"Received PEER_VALIDATION from {self}")
            self.__handle_peer_validation(buf)
        else:
            logging.info(f"Received message with unknown type {type} from "
                         f"{self}")
            self.__is_trustworthy = False
            await self.gossip.close_peer(self)

    async def __handle_peer_announce(self, buf):
        """Handles a peer announce message and calls __send_peer_offer() to
        send a response.

        Arguments:
        - buf (byte-object) -- received message in byte format. The type must
          be PEER_ANNOUNCE
        """
        msg = parse_peer_announce(buf)
        if msg == None:
            return

        (size, type, id, ttl, data_type, data) = msg
        await self.gossip.handle_peer_announce(id, ttl, data_type, data, self)

    async def __handle_peer_discovery(self, buf):
        """Handles a peer discovery message and calls __send_peer_offer() to
        send a response.

        Arguments:
        - buf (byte-object) -- received message in byte format. The type must
          be PEER_DISCOVERY
        """
        if not self.__is_trustworthy:
            logging.debug(
                "Ignoring PEER DISCOVERY since peer is not trustworthy")
            return

        msg = parse_peer_discovery(buf)
        if (msg == None):
            return

        (size, type, challenge) = msg
        await self.__send_peer_offer(challenge)

    async def __handle_peer_offer(self, buf):
        """Handles a peer offer message. 
        Calls handle_peer_offer() of gossip if everything is ok.

        Arguments:
        - buf (byte-object) -- received message in byte format. The type must 
          be PEER_DISCOVERY
        """
        if not self.__is_trustworthy:
            logging.debug("Ignoring PEER OFFER since peer is not trustworthy")
            return

        msg = parse_peer_offer(buf)
        if (msg == None):
            return
        (size, type, challenge, nonce, data) = msg
        # Check for invalid challenge
        if not self.__check_challenge(challenge):
            logging.warning("[PEER] Received invalid challenge in peer offer")
            return

        # Check nonce
        if not valid_nonce_peer_offer(buf):
            logging.warning("[PEER] Received invalid nonce in peer offer")
            return
        # check if the offer contains our own address
        p2p_address = self.gossip.config.p2p_address
        if p2p_address in data:
            logging.warning("[PEER] Own p2p address found in peer offer!")
            data = list(filter(lambda ip: ip != p2p_address, data))

        # save data / pass it to gossip
        await self.gossip.handle_peer_offer(data)

    async def __handle_peer_challenge(self, buf):
        """Handles a peer challenge message.

        Arguments:
        - buf (byte-object) -- received message in byte format. The type must
          be PEER_CHALLENGE
        """
        challenge = parse_peer_challenge(buf)
        if challenge == None:
            return
        # solve the challenge
        nonce = produce_pow_peer_challenge(challenge)
        if nonce == None:
            return
        await self.__send_peer_verification(nonce)

    async def __handle_peer_verification(self, buf):
        nonce = parse_peer_verification(buf)
        if nonce == None:
            return

        # Check if we send a peer challenge, otherwise we do not except an
        # verification
        if self.__peer_challenge == None:
            logging.warning("Received PEER VERIFICATION but no PEER CHALLENGE "
                            "was send. Disconnecting peer")
            self.__is_trustworthy = False
            await self.gossip.close_peer(self)

        (challenge, timeout) = self.__peer_challenge
        if timeout < time.time():
            logging.info("Received PEER VERIFICATION after timeout for "
                         "challenge expired")
            self.__is_trustworthy = False
            await self.__send_peer_validation(False)

        # Check if nonce is not valid
        if not valid_nonce_peer_challenge(challenge, nonce):
            logging.info("Received PEER VERIFICATION with invalid nonce")
            self.__is_trustworthy = False
            await self.__send_peer_validation(False)

        # received valid verification, this peer is now trustworthy
        self.__is_trustworthy = True
        await self.__send_peer_validation(True)

    def __handle_peer_validation(self, buf):
        """Handles a peer validation message.

        Arguments:
        - buf (byte-object) -- received message in byte format. The type must
          be PEER_CHALLENGE
        """
        valid = parse_peer_validation(buf)
        if valid == None:
            return

        assert type(valid) is bool
        logging.info(f"Received validation with valid = {valid}")
        self.__is_validated = valid
        # TODO what if we where verified but received and invalid validation

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
            warning = ("[PEER] WARNING: received PEER INFO but already knew"
                       "the p2p_listening_port!\nOld port: {}, new Port: {}")
            logging.warning(warning.format(self.peer_p2p_listening_port, port))

        # save new port
        logging.debug(f"[PEER] Saving p2p_listening_port {port}")
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
    """Opens a connection to the given ip & port and creates a Peer_connection
    and send a peer info message.

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
    logging.info("[PEER] Connecting to ip: {}, port: {}".format(ip, port))
    try:
        reader, writer = await asyncio.open_connection(ip, int(port))
    except ConnectionRefusedError:
        logging.info("Failed to connect to ip: {}, port: {}".format(ip, port))
        return None

    await __send_peer_info(writer, p2p_listening_port)
    return Peer_connection(reader, writer, gossip, port, is_trustworthy=True)


async def __send_peer_info(writer, p2p_listening_port):
    """Sends a PEER INFO message with p2p_listening_port to the given 
    StreamWriter

    Arguments:
    - writer (StreamWriter) -- StreamWriter connected to a new peer
    - p2p_listening_port (int) -- Port this peer accepts new peer connections
      at
    """
    info_packet = pack_peer_info(p2p_listening_port)
    logging.info("[PEER] Sending PEER INFO with p2p port {} to {}".format(
        p2p_listening_port, writer.get_extra_info("peername")))
    writer.write(info_packet)
    await writer.drain()
