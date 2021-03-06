"""
This Module provides the Peer_connection class as well as a factory method for
it (peer_connection_factory())
"""
import logging
import asyncio
import time
from random import getrandbits

from modules.util import (
    parse_address,
    is_valid_address,
    produce_pow_peer_challenge,
    valid_nonce_peer_challenge
)
from modules.packet_parser import (
    PEER_ANNOUNCE,
    PEER_CHALLENGE,
    PEER_DISCOVERY,
    PEER_OFFER,
    PEER_INFO,
    PEER_VALIDATION,
    PEER_VERIFICATION,
    check_peer_discovery,
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
    parse_peer_offer,
    parse_peer_info,
    parse_peer_validation,
    parse_peer_verification
)


# Timeout for challenges in seconds. After this timeout, a challenge is invalid
CHALLENGE_TIMEOUT = 300

# Timeout for peer offers. After sending a peer discovery, a peer offer is only
# handled if it was send within this timeframe
PEER_OFFER_TIMEOUT = 300


class Peer_connection:
    """A Peer_connection represents a connection to a single peer.

    Class variables:
    - gossip (Gossip) -- gossip responsible for this peer
    - reader (StreamReader) -- (private) asyncio StreamReader of connected peer
    - writer (StreamWriter) -- (private) asyncio StreamWriter of connected peer
    - peer_p2p_listening_port (int) -- p2p_listening_port of connected peer
    - peer_challenge (Tuple: int, int) -- challenge with timeout send to
      connected node. None if none was send.
    - validated_them (boolean) -- Whether the connected node is validated /
      considered trustworthy. A node can prove itself trustworthy by getting 
      validated by us (push peers), see Documentation. Nodes we connect to
      should be set to be validated_them by default.
    - validated_us (boolean) -- whether this node is validated by the connected
      node/peer. Gets updated upon receiving a peer validation. If we receive a
      new incoming connection, we assume that this peer trusts us.
    - last_peer_discovery_send (float) -- time (in seconds since the epoch)
      when last peer discovery was send. None if none was send or a peer offer
      was already received. Used to avoid receiving more offers than we request
      by sending peer discoveries
    """

    def __init__(self, reader, writer, gossip, peer_p2p_listening_port=None,
                 validated_us=False, validated_them=False):
        """
        Arguments:
        - reader (StreamReader) -- asyncio StreamReader of connected peer
        - writer (StreamWriter) -- asyncio StreamWriter of connected peer
        - gossip (Gossip) -- gossip responsible for this peer
        - peer_p2p_listening_port (int) -- (Optional, default: None) Port the
          connected peer accepts new peer connections at
        - validated_us (boolean) -- (Optional, default: False) whether this
          node is validated by the connected node/peer. Gets updated upon
          receiving a peer validation.
        - validated_them (boolean) -- whether the connected node is considered
          trustworthy. A node can prove itself trustworthy by getting validated
          by us (push peers), see Documentation. Nodes we connect to should be
          set to be trustworthy.
        """
        self.gossip = gossip
        self.__reader = reader
        self.__writer = writer
        self.peer_p2p_listening_port = peer_p2p_listening_port
        self.__peer_challenge = None
        self.__validated_them = validated_them
        self.__validated_us = validated_us
        self.__last_peer_discovery_send = None

    def __str__(self):
        """Called by str(Peer_connection). Uses the debug address"""
        return f"Peer<{self.get_debug_address()}>"

    def __repr__(self):
        """Uses the peer address instead of the (more readable but possibly
        less ambiguous) debug address.
        """
        return f"Peer<{self.get_peer_address()}>"

    async def run(self):
        """Waits for incoming messages and handles them. Runs until the
        connection is closed"""
        while True:
            if self.__writer.is_closing():
                logging.debug(f"[PEER]: writer is_closing {self}")
                break
            try:
                if self.__writer.is_closing():
                    break
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
        logging.info(f"[PEER] Connection to {self} closed")
        try:
            self.__writer.close()
            await self.__writer.wait_closed()
            return
        except Exception:
            return

    def get_peer_challenge(self):
        """Returns the peer challenge send to the connected peer together with
        its timeout, or None if none was send"""
        return self.__peer_challenge

    def is_fully_validated(self):
        """Returns true if the connection validated, meaning validated_them
        and validated_us"""
        return self.__validated_them and self.__validated_us

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
        host = self.__writer.get_extra_info("peername")[0]
        if host == None:
            return ""
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
        address = self.__writer.get_extra_info("peername")
        if address == None:
            return ""
        address = "{}:{}".format(address[0], address[1])
        return address

    def get_own_address(self):
        """Returns the address of this peer in the format host:port

        See also:
        - get_peer_address()
        - get_peer_p2p_listening_address()
        - get_debug_address() - for debug output
        """
        address = self.__writer.get_extra_info("sockname")
        if address == None:
            return ""
        address = "{}:{}".format(address[0], address[1])
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
        """Sends a peer discovery message. Assumes that the connection is
        validated by both sides. Use is_fully_validated to check."""
        message = pack_peer_discovery()
        self.__last_peer_discovery_send = time.time()
        logging.info(f"[PEER] Sending PEER DISCOVERY to: {self}")
        await self.__send(message)

    async def send_peer_announce(self, id, ttl, data_type, data):
        """Sends a peer announce message. For documentation of parameters, see
        the project documentation.
        Assumes that the connection is validated by both sides. Use
        is_fully_validated to check."""
        message = pack_peer_announce(id, ttl, data_type, data)
        logging.info(f"[PEER] Sending PEER ANNOUNCE with id: {id}, ttl: {ttl} "
                     f" and data type: {data_type}, to: {self}")
        await self.__send(message)

    async def send_peer_challenge(self):
        """Sends a peer challenge message and saves the challenge with a
        timeout in __peer_challenge, if no challenge was send before.
        If this is called an a challenge was already send, the no new challenge
        will be send, but the peer will be closed if the challenge timeout ran
        out.

        Should only be called if we where not the initiator of the connection.
        See Project Documentation - Push Gossip
        """
        # Check if a peer challenge was already send
        if self.__peer_challenge != None:
            # Disconnect it the challenge expired
            if self.__peer_challenge[1] < time.time():
                logging.warning(
                    f"[PEER] PEER CHALLENGE timeout for {self} expired "
                    f"{time.time() - self.__peer_challenge[1]}s ago")
                await self.gossip.close_peer(self)
            return

        challenge = getrandbits(64)
        self.__peer_challenge = (challenge, time.time() + CHALLENGE_TIMEOUT)
        message = pack_peer_challenge(challenge)
        logging.info(f"[PEER] Sending PEER CHALLENGE to: {self}")
        await self.__send(message)

    async def __send_peer_validation(self, valid):
        """Sends a peer validation message, updates validated_them and tells
        gossip that the connected peer is now considered valid.

        Arguments:
        - valid (bool) -- Valid bit - See project documentation
        """
        self.__validated_them = valid
        message = pack_peer_validation(valid)
        logging.info(f"[PEER] Sending PEER VALIDATION with valid: {valid}, to:"
                     f" {self}")
        await self.__send(message)
        # Tell gossip that this peer is now validated, if valid
        if valid:
            await self.gossip.validate_peer(self)

    async def __send_peer_verification(self, nonce):
        """Sends a peer verification message.
        Arguments:
        - nonce (int) -- Nonce for challenge received in peer challenge - See
          project documentation
        """
        message = pack_peer_verification(nonce)
        logging.info(f"[PEER] Sending PEER VERIFICATION to {self}")
        await self.__send(message)

    async def __send_peer_offer(self):
        """Sends a peer offer. Should only be called if the connection is
        validated by both sides.
        """
        # Use target_address to filter the address of the target peer
        target_address = self.get_peer_p2p_listening_address()
        addresses = list(filter(lambda ip: ip != target_address,
                         await self.gossip.get_peer_addresses()))

        # Abort if we do not know any other peers
        if len(addresses) == 0:
            logging.debug("[PEER] No other peers connected, do not send "
                          "PEER OFFER.")
            return

        message = pack_peer_offer(addresses)
        logging.info(
            f"[PEER] Sending PEER OFFER to {self} with peers: {addresses}")
        await self.__send(message)

    async def __send(self, message):
        """Sends a message to the connected peer. Should be awaited

        Arguments:
        - message (byte-object) -- message that should be send
        """
        try:
            self.__writer.write(message)
            await self.__writer.drain()
        except ConnectionResetError:
            # Will already close if run was called
            return

    async def __handle_incoming_message(self, buf):
        """Checks the type of an incoming message in byte format and calls the
        correct handler according the the type.

        Arguments:
        - buf (byte-object) -- received message
        """
        type = get_header_type(buf)

        # Close the connection if we do not allow this message type in the
        # current state (regarding validated_us and validated_them)
        if (not self.__handle_type(type)):
            logging.debug(f"[PEER] Did not expect message of type {type} from "
                          f"{self}. State: validated_us: {self.__validated_us}"
                          f", validated_them: {self.__validated_them}")
            await self.gossip.close_peer(self)
            return

        if type == PEER_ANNOUNCE:
            logging.info(f"[PEER] Received PEER_ANNOUNCE from {self}")
            await self.__handle_peer_announce(buf)
        elif type == PEER_DISCOVERY:
            logging.info(f"[PEER] Received PEER_DISCOVERY from {self}")
            await self.__handle_peer_discovery(buf)
        elif type == PEER_OFFER:
            logging.info(f"[PEER] Received PEER_OFFER from {self}")
            await self.__handle_peer_offer(buf)
        elif type == PEER_INFO:
            logging.info(f"[PEER] Received PEER_INFO from {self}")
            await self.__handle_peer_info(buf)
        elif type == PEER_CHALLENGE:
            logging.info(f"[PEER] Received PEER_CHALLENGE from {self}")
            await self.__handle_peer_challenge(buf)
        elif type == PEER_VERIFICATION:
            logging.info(f"[PEER] Received PEER_VERIFICATION from {self}")
            await self.__handle_peer_verification(buf)
        elif type == PEER_VALIDATION:
            logging.info(f"[PEER] Received PEER_VALIDATION from {self}")
            await self.__handle_peer_validation(buf)
        else:
            logging.info(f"[PEER] Received message with unknown type {type} "
                         f"from {self}")
            self.__validated_them = False
            await self.gossip.close_peer(self)

    def __handle_type(self, type):
        """Checks if the given type should be handled at the moment.

        If the connected node is not validated (not validated_them), only allow
        PEER VERIFICATION and PEER INFO.

        If we are not validated by the connected node (not validated_us), only
        allow PEER CHALLENGE and PEER VALIDATION

        If both sides are validated, allow all messages
        """
        case_not_validated_them = not self.__validated_them and type in [
            PEER_VERIFICATION, PEER_INFO]
        case_not_validated_us = not self.__validated_us and type in [
            PEER_CHALLENGE, PEER_VALIDATION]

        return ((self.__validated_them and self.__validated_us)
                or case_not_validated_them or case_not_validated_us)

    async def __handle_peer_announce(self, buf):
        """Handles a peer announce message. Executes basic checks and then
        forwards it to gossip. Assumes that the connection is validated by both
        sides.

        Arguments:
        - buf (byte-object) -- received message in byte format. The type must
          be PEER_ANNOUNCE
        """
        msg = parse_peer_announce(buf)
        if msg == None:
            logging.info(f"[PEER] Closing {self} because an malformed PEER "
                         "ANNOUNCE message was received")
            await self.gossip.close_peer(self)
            return

        (id, ttl, data_type, data) = msg
        await self.gossip.handle_peer_announce(id, ttl, data_type, data, self)

    async def __handle_peer_discovery(self, buf):
        """Handles a peer discovery message and calls __send_peer_offer() to
        send a response. Assumes that the connection is validated by both sides
        .

        Arguments:
        - buf (byte-object) -- received message in byte format. The type must
          be PEER_DISCOVERY
        """
        if not check_peer_discovery(buf):
            logging.debug(
                f"[PEER] PEER DISCOVERY has incorrect length {len(buf)}")
            return

        await self.__send_peer_offer()

    async def __handle_peer_offer(self, buf):
        """Handles a peer offer message.
        Calls handle_peer_offer() of gossip if everything is ok. Assumes that
        the connection is validated by both sides.

        Arguments:
        - buf (byte-object) -- received message in byte format. The type must
          be PEER_DISCOVERY
        """
        data = parse_peer_offer(buf)
        if data == None:
            logging.info(f"[PEER] Closing {self} because an malformed PEER "
                         "OFFER message was received")
            await self.gossip.close_peer(self)
            return

        # Close the connection if the offer contained no data
        if data == ['']:
            logging.info(f"[PEER] Closing {self} because a empty peer offer "
                         "was received.")
            await self.gossip.close_peer(self)
            return

        for address in data:
            if not is_valid_address(address):
                logging.info(
                    f"[PEER] Closing {self} because peer offer contained "
                    f"invalid address: {address}, data: {data}.")
                await self.gossip.close_peer(self)
                return

        # Close the peer if we did not send a peer discovery
        # / not request a peer offer
        if self.__last_peer_discovery_send == None:
            logging.info(f"[PEER] Closing {self} because a peer offer was "
                         "received but no peer discovery was send")
            await self.gossip.close_peer(self)
            return

        # Ignore offer if it was not send within a specific timeframe
        if self.__last_peer_discovery_send + PEER_OFFER_TIMEOUT < time.time():
            logging.debug(f"[PEER] ignoring peer offer from {self} because "
                          "timeout ran out.")
            self.__last_peer_discovery_send = None
            return

        # check if the offer contains our own address
        p2p_address = self.gossip.config.p2p_address
        if p2p_address in data:
            logging.warning("[PEER] Own p2p address found in peer offer")
            await self.gossip.close_peer(self)
            return

        # save data / pass it to gossip
        self.__last_peer_discovery_send = None
        await self.gossip.handle_peer_offer(data)

    async def __handle_peer_challenge(self, buf):
        """Handles a peer challenge message.

        Arguments:
        - buf (byte-object) -- received message in byte format. The type must
          be PEER_CHALLENGE
        """
        challenge = parse_peer_challenge(buf)
        if challenge == None:
            logging.info(f"[PEER] Closing {self} because an malformed PEER "
                         "CHALLENGE message was received")
            await self.gossip.close_peer(self)
            return
        # solve the challenge
        nonce = produce_pow_peer_challenge(challenge)
        if nonce == None:
            return
        await self.__send_peer_verification(nonce)

    async def __handle_peer_verification(self, buf):
        nonce = parse_peer_verification(buf)
        if nonce == None:
            logging.info(f"[PEER] Closing {self} because an malformed PEER "
                         "VERIFICATION message was received")
            await self.gossip.close_peer(self)
            return

        # Check if we send a peer challenge, otherwise we do not except an
        # verification
        if self.__peer_challenge == None:
            logging.warning("[PEER] Received PEER VERIFICATION but no PEER "
                            f"CHALLENGE was send. Disconnecting {self}")
            await self.gossip.close_peer(self)
            return

        (challenge, timeout) = self.__peer_challenge
        if timeout < time.time():
            logging.info("[PEER] Received PEER VERIFICATION after timeout for "
                         "challenge expired")
            await self.gossip.close_peer(self)
            return

        # Check if nonce is not valid
        if not valid_nonce_peer_challenge(challenge, nonce):
            logging.info("[PEER] PEER VERIFICATION contained invalid nonce")
            await self.gossip.close_peer(self)
            return

        # received valid verification, this peer is now trustworthy
        await self.__send_peer_validation(True)

    async def __handle_peer_validation(self, buf):
        """Handles a peer validation message.

        Arguments:
        - buf (byte-object) -- received message in byte format. The type must
          be PEER_CHALLENGE
        """
        valid = parse_peer_validation(buf)
        if valid == None:
            logging.info(f"[PEER] Closing {self} because an malformed PEER "
                         "VALIDATION message was received")
            await self.gossip.close_peer(self)
            return

        assert type(valid) is bool
        logging.info(f"[PEER] Received validation with valid = {valid}")
        self.__validated_us = valid
        if not valid:
            logging.info(f"[PEER] Closing {self} because PEER VALIDATION "
                         "contained invalid")
            await self.gossip.close_peer(self)

    async def __handle_peer_info(self, buf):
        """Handles a peer info message. Saves the received p2p_listening_port.

        Arguments:
        - buf (byte-object) -- received message in byte format. The type must
          be PEER_INFO
        """
        port = parse_peer_info(buf)
        if port == None:
            logging.info(f"[PEER] Closing {self} because an malformed PEER "
                         "INFO message was received")
            await self.gossip.close_peer(self)
            return

        # check if we already know the p2p_listening_port of the other peer
        if self.peer_p2p_listening_port != None:
            warning = ("[PEER] received PEER INFO but already knew the "
                       "p2p_listening_port!\nOld port: {}, new Port: {}")
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
    (ip, port) = parse_address(address)
    logging.info("[PEER] Connecting to ip: {}, port: {}".format(ip, port))
    try:
        reader, writer = await asyncio.open_connection(ip, port)
    except ConnectionRefusedError:
        logging.info(f"[PEER] Failed to connect to ip: {ip}, port: {port}")
        return None

    await __send_peer_info(writer, p2p_listening_port)
    return Peer_connection(reader, writer, gossip, port, validated_them=True)


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
