"""
This module provides the gossip class.
TODO: Description of gossip functionality?
"""

import asyncio
import logging
from random import (randint, sample, shuffle)
from math import (floor, ceil)
from time import time
from collections import deque

from modules.util import (Setqueue, parse_address)
from modules.api.api_connection import Api_connection
from modules.connection_handler import connection_handler
from modules.peers.peer_connection import (
    Peer_connection, peer_connection_factory)


class Gossip:
    """The Gossip class represents a single instance of Gossip. By
    instanciating it, gossip is started.

    Class variables:
    - config (Config) -- config object used for this instance of gossip
    - push_peers (Peer_connection deque) -- Connected (active) push peers /
      peers that connected to us. Limited to max_push_peers.
      -> corresponding lock: push_peers_lock
    - pull_peers (Peer_connection List) -- Connected (active) pull peers /
      peers we learned about from other peers and than connected to.
      -> corresponding lock: pull_peers_lock
    - unverified_peers (Peer_connection deque) -- peers that connected to us
      that still need to be verified. After beeing verified, they will be moved
      into push_peers. Limited to config.cache_size
      -> corresponding lock: unverified_peers_lock
    - max_push_peers (int) -- push_peers capacity
    - max_pull_peers (int) -- pull_peers capacity
    - apis (Api_connection List) -- connected APIs
    - datasubs (dictionary: int-[Api_connection]) -- Datatypes linking to all
      theire subscribing APIs
    - peer_announce_ids (Setqueue) -- TODO document
    - announces_to_verify (dictionary: int - Tuple List) -- open
      PEER_ANNOUNCES. PEER_ANNOUNCES Will be forwarded if/when all subscribers
      verify the message.
      Format: message-id : [(ttl, datatype, data, [datasubs])]

    The locks should be acquired in the following order:
    1) unverified_peers_lock
    2) pull_peers_lock
    3) push_peers_lock
    """

    def __init__(self, config):
        """
        Arguments:
        - config (Config) -- config class object
        """
        self.config = config

        self.__max_push_peers = floor(self.config.max_connections / 2)
        self.__max_pull_peers = ceil(self.config.max_connections / 2)

        # Push peers that connected to us
        self.__push_peers = deque(maxlen=self.__max_push_peers)
        self.__push_peers_lock = asyncio.Lock()

        # Pull peers that we connected to
        self.__pull_peers = []
        self.__pull_peers_lock = asyncio.Lock()

        # unverified push peers
        self.__unverified_peers = deque(maxlen=self.config.cache_size)
        self.__unverified_peers_lock = asyncio.Lock()

        self.apis = []

        #                          Key - Value
        # Subscriber list, Format: Int - List of Api_connections
        self.__datasubs = {}
        self.__peer_announce_ids = Setqueue(self.config.cache_size)
        # Dictionary of buffered PEER_ANNOUNCEs;
        # Key: int - Message ID
        # Value: [ int, int     , bytes, Peer_connection, [Peer_connection]]
        #        [(ttl, datatype, data , sender         , [datasubs])]
        self.__announces_to_verify = {}

    async def run(self):
        """Starts this gossip instance.
        Tries to connect to all known peers or connect to bootstrapping
        service, if no peers where in the config.
        Starts peer controll (responsible for maintaining degree many peers),
        peers and waits for new incoming connections.
        """
        # connect to peers in config
        (_, p2p_listening_port) = parse_address(self.config.p2p_address)
        num_known_peers = len(self.config.known_peers)
        if num_known_peers > 0:
            logging.debug(
                f"[PEER] Connecting to {num_known_peers} known peers")
            async with self.__pull_peers_lock:
                self.__pull_peers = await peer_connection_factory(
                    self.config.known_peers, self, int(p2p_listening_port))

        # No known_peers in config or all where unreachable
        # -> Connect to bootstrapping node
        async with self.__pull_peers_lock:
            if len(self.__pull_peers) == 0:
                logging.debug("[PEER] Connecting to bootstrapping node")
                self.__pull_peers = await peer_connection_factory(
                    [self.config.bootstrapper], self, int(p2p_listening_port))

        # Start active peers
        async with self.__pull_peers_lock:
            for peer in self.__pull_peers:
                asyncio.create_task(peer.run())

        asyncio.create_task(self.__run_peer_control())
        asyncio.create_task(self.__run_verifier())

        # start API connection handler
        (api_host, api_port) = parse_address(self.config.api_address)
        asyncio.create_task(connection_handler(
            api_host, int(api_port), self.__on_api_connection))
        logging.debug("[API] started API connection handler on {}:{}\r\n"
                      .format(api_host, api_port))

        # start peer connection handler
        (host, port) = parse_address(self.config.p2p_address)
        await connection_handler(host, int(port), self.__on_peer_connection)

    def __on_api_connection(self, reader, writer):
        new_api = Api_connection(reader, writer, self)
        logging.info(f"[API] New API connected: {new_api.get_api_address()}")
        self.apis.append(new_api)
        asyncio.create_task(new_api.run())

    async def __on_peer_connection(self, reader, writer):
        """Gets called when a new peer tries to connect.

        Arguments:
        - reader (StreamReader) -- asyncio StreamReader connected to a new peer
        - writer (StreamWriter) -- asyncio StreamWriter connected to a new peer
        """
        new_peer = Peer_connection(reader, writer, self, validated_us=True)
        logging.info(f"[PEER] New unverified peer connected: {new_peer}")

        # Dosconnect the oldest unverified peer if we reached cache_size
        async with self.__unverified_peers_lock:
            if len(self.__unverified_peers) >= self.config.cache_size:
                oldest_peer = self.__unverified_peers.pop()
                logging.debug(
                    f"Disconnecting {oldest_peer}, because capacity for "
                    f"unverified peers (cache_size: {self.config.cache_size}) "
                    "is reached")
                await self.close_peer(oldest_peer, True)
            self.__unverified_peers.appendleft(new_peer)

        asyncio.create_task(new_peer.run())

    async def validate_peer(self, peer):
        """Removes the given peer from the unverified_peers list and adds it to
        push_peers"""
        in_unverified = False
        async with self.__unverified_peers_lock:
            in_unverified = peer in self.__unverified_peers
            if in_unverified:
                self.__unverified_peers.remove(peer)

        # If the peer was removed from unverified, log connected, else warning
        if in_unverified:
            await self.__log_connected_peers()
        else:
            logging.warning("[PEER] Peer not found in unverified_peers")

        # Dosconnect the oldest push peer if we reached max_push_peers
        async with self.__push_peers_lock:
            if len(self.__push_peers) >= self.__max_push_peers:
                oldest_peer = self.__push_peers.pop()
                logging.debug(
                    f"Disconnecting {oldest_peer}, because max_push_peers "
                    f"({self.__max_push_peers}) is reached")
                await self.close_peer(oldest_peer, has_push_peers_lock=True)
            self.__push_peers.appendleft(peer)

    async def handle_peer_offer(self, peer_addresses):
        """Offers peer_addresses to this gossip class. Gets called after a peer
        offer was received.

        Arguments:
        - peer_addresses (str List) -- addresses of potential peers, received
          from peer offer. format: host_ip:port
        """
        async with self.__pull_peers_lock:
            if len(self.__pull_peers) > self.__max_pull_peers:
                logging.debug("[PEER] Ignoring peer offer because pull peers "
                              f"capacity is reached ({len(self.__pull_peers)}/"
                              f"{self.__max_pull_peers})")
                return
        logging.info(f"[PEER] Offer contained: {peer_addresses}")

        # get addresses of all peers and remove already connected peers
        async with self.__unverified_peers_lock:
            all_peers = list(self.__unverified_peers).copy()
        async with self.__pull_peers_lock:
            all_peers += self.__pull_peers
        async with self.__push_peers_lock:
            all_peers += list(self.__push_peers)
        connected = await self.get_peer_addresses(all_peers)
        candidates = list(filter(lambda x: x not in connected, peer_addresses))

        if len(candidates) == 0:
            logging.info("[PEER] No new peers found in offer")

        logging.debug(f"[PEER] Candidates: {candidates}")
        shuffle(candidates)
        (_, p2p_listening_port) = parse_address(self.config.p2p_address)

        async with self.__pull_peers_lock:
            # missing_peers to reach max_pull_peers
            missing_peers = self.__max_pull_peers - len(self.__pull_peers)

            # Open connections to missing_peers new Peers. If a peer did not
            # respond / a connection attempt failed, repeat until we reach the
            # max_pull_peers or no candidates are left
            while missing_peers > 0 and len(candidates) > 0:
                connect_to = candidates[:min(missing_peers, len(candidates))]
                candidates = candidates[min(missing_peers, len(candidates)):]
                new_peers = await peer_connection_factory(
                    connect_to, self, p2p_listening_port)
                self.__pull_peers += new_peers
                missing_peers -= len(new_peers)
                # start new peers
                for peer in new_peers:
                    asyncio.create_task(peer.run())

    async def get_peer_addresses(self, peerlist=None):
        """Returns the p2p listening addresses of all known peers in a list

        Arguments:
        - peerlist: List containing Peer_connections, default = None. If this
          is not None, the addresses contained within the list will be returned
          If this is None, the addresses of push_peers and pull_peers will be
          returned.
          This can be used to exclusively get the addresses of pull, push or
          unverified peers.
          If peerlist is None, pull_peers_lock and push_peers_lock are acquired

        Returns:
            List of strings with format: <host_ip>:<port>
        """
        if peerlist != None:
            peers = peerlist
        else:
            peers = []
            async with self.__pull_peers_lock:
                peers += self.__pull_peers
            async with self.__push_peers_lock:
                peers += list(self.__push_peers)

        addresses = []
        for peer in peers:
            addresses.append(peer.get_peer_p2p_listening_address())
        return list(filter(lambda x: x is not None, addresses))

    async def close_peer(self, peer, has_unverified_lock=False,
                         has_push_peers_lock=False, has_pull_peers_lock=False):
        """Removes a Peer_connection from gossip and calls close on the
        Peer_connection.

        Arguments:
        - peer (Peer_connection) -- Peer_connection instance that should be
          closed
        - has_unverified_lock (bool) -- (Default False) whether
          unverified_peers_lock is already acquired
        - has_push_peers_lock (bool) -- (Default False) whether
          push_peers_lock is already acquired
        - has_pull_peers_lock (bool) -- (Default False) whether
          pull_peers_lock is already acquired
        """
        async def __check_list(peer, list, lock, has_lock):
            """Checks if peer is in list. Uses the lock if has_lock is False.
            Returns True if the peer was found in list and closed"""
            # already has lock, check unverified_peers
            if has_lock and peer in list:
                list.remove(peer)
                await peer.close()
                return True
            # acquire lock and check unverified_peers
            if not has_lock:
                async with lock:
                    if peer in list:
                        list.remove(peer)
                        await peer.close()
                        return True
            return False

        # Check if the peer is in unverified_peers
        if await __check_list(peer, self.__unverified_peers,
                              self.__unverified_peers_lock,
                              has_unverified_lock):
            await self.__log_connected_peers()
            return

        # Check if the peer is in pull_peers
        if await __check_list(peer, self.__pull_peers,
                              self.__pull_peers_lock, has_pull_peers_lock):
            await self.__log_connected_peers()
            return

        # Check if the peer is in push_peers
        if await __check_list(peer, self.__push_peers,
                              self.__push_peers_lock, has_push_peers_lock):
            await self.__log_connected_peers()
            return

        # It can happen that the peer is not in any of the above lists, e.g.
        # when a connection is closed directly after establishing it in the
        # Peer_connection factory
        logging.debug("[PEER] The Peer that should be closed was not found"
                      " in push_peers, pull_peers or unverified_peers")
        await peer.close()
        await self.__log_connected_peers()

    async def __run_peer_control(self):
        """Searches for new pull peers by sending a peer discovery to all known
        peers every search_cooldown seconds, if: we can accept more pull pears,
        we are bellow min_connections (pull & push) or we have less than
        min_connections/2 pull peers.
        """
        while True:
            # True if we can accept more pull peers
            async with self.__pull_peers_lock:
                async with self.__push_peers_lock:
                    has_pull_peers_capacity = (
                        len(self.__pull_peers) < self.__max_pull_peers
                    )
                    # True if we have less than min_connections/2 pull peers
                    bellow_min_pull_connections = (
                        len(self.__pull_peers) < ceil(
                            self.config.min_connections / 2)
                    )
                    # True if we need more total peers ro reach min_connections
                    bellow_min_connections = (
                        len(self.__pull_peers) + len(self.__push_peers)
                        < self.config.min_connections
                    )
                    # Search for new pull peers if we have capacity and need
                    # more peer to reach min_connections or if we have less
                    # than min_connections/2 pull peers (to keep a minimum
                    # amount of pull peers and avoid only having push peers)
                    if((has_pull_peers_capacity and (
                        bellow_min_connections or bellow_min_pull_connections))
                       ):
                        logging.info("- - - - - - - - - - - - - -")
                        logging.info("[PEER] Looking for new Peers")
                        # Send PeerDiscovery to all validated peers
                        for peer in list(self.__push_peers)+self.__pull_peers:
                            if peer.is_fully_validated():
                                await peer.send_peer_discovery()

            await self.__log_connected_peers()
            await asyncio.sleep(self.config.search_cooldown)

    async def __run_verifier(self):
        """Sends out peer challenge to all unverified peers in a regular
        intervall"""
        while True:
            async with self.__unverified_peers_lock:
                if len(self.__unverified_peers) > 0:
                    for peer in self.__unverified_peers:
                        await peer.send_peer_challenge()

            await asyncio.sleep(self.config.challenge_cooldown)

    async def print_gossip_debug(self):
        """Prints all Gossip class variables.
        Acquires unverified_peers_lock
        """
        await self.__log_connected_peers()
        logging.debug(f"[API] connected apis {self.apis}")
        logging.debug(f"[API] current subscribers {self.__datasubs}")
        logging.debug("[API] current routing ids: " +
                      f"{list(self.__peer_announce_ids.queue)}")
        logging.debug("[API] current announces to verify: " +
                      f"{self.__announces_to_verify}\r\n")

    async def __log_connected_peers(self):
        """Logs push and pull peers including capacities.
        Acquires __push_peers_lock, __pull_peers_lock and unverified_peers_lock
        """
        async with self.__push_peers_lock:
            logging.info("[PEER] Connected push peers: {}. {}/{}".format(
                await self.get_peer_addresses(self.__push_peers),
                len(self.__push_peers), self.__max_push_peers))
        async with self.__pull_peers_lock:
            logging.info("[PEER] Connected pull peers: {}. {}/{}".format(
                await self.get_peer_addresses(self.__pull_peers),
                len(self.__pull_peers), self.__max_pull_peers))
        async with self.__unverified_peers_lock:
            logging.info("[PEER] Connected unverified peers: {}. {}/{}".format(
                await self.get_peer_addresses(self.__unverified_peers),
                len(self.__unverified_peers), self.config.cache_size
            ))

    def print_api_debug(self):
        """Prints all Gossip class variables for API functionality"""
        logging.debug(f"[API] connected apis {self.apis}")
        logging.debug(f"[API] current subscribers {self.__datasubs}")
        logging.debug("[API] current routing ids: " +
                      f"{list(self.__peer_announce_ids.queue)}")
        logging.debug("[API] current announces to verify: " +
                      f"{self.__announces_to_verify}\r\n")

    async def add_subscriber(self, datatype, api):
        """Adds an Api_connection to the Subscriber dict (datasubs)
           gets called after a GOSSIP_NOTIFY
        """
        if datatype in self.__datasubs.keys():
            temp = self.__datasubs[datatype]
            temp.append(api)
            self.__datasubs[datatype] = temp
        else:
            self.__datasubs[datatype] = [api]

        return

    async def __remove_subscriber(self, api):
        """Removes an Api_connection from the whole Subscriber dict (datasubs)
        """
        for key in self.__datasubs:
            if api in self.__datasubs[key]:
                self.__datasubs[key].remove(api)
        return

    async def close_api(self, api):
        """Removes an Api connection from:
            - apis
            - datasubs
           and closes the socket"""
        await self.__remove_subscriber(api)
        if api in self.apis:
            self.apis.remove(api)
        # Close the socket
        await api.close()
        return

    async def __add_peer_announce_id(self, packet_id):
        """Adds a packet/message id to the FIFO Queue to keep track of known
           IDs to prevent routing loops"""
        if self.__peer_announce_ids.full():
            self.__peer_announce_ids.get()
        # duplicates wont be added as we use SetQueue
        self.__peer_announce_ids.put(packet_id)

    async def handle_gossip_announce(self, ttl, dtype, data):
        """Gets called upon arrival of a GOSSIP_ANNOUNCE
           Performs several things:
              - generate a packet id
              - add it as a known id
              - send a PEER_ANNOUNCE to a sample of degree peers"""
        # Generate PEER_ANNOUNCE id
        packet_id = randint(0, 2**64-1)
        while self.__peer_announce_ids.contains(packet_id):
            packet_id = randint(0, 2**64-1)
        # Save this id for routing loop prevention
        await self.__add_peer_announce_id(packet_id)

        # Choose degree peers randomly
        peers = self.__get_verified_pull_push_peers()
        if len(peers) < self.config.degree:
            peer_sample = peers
        else:
            peer_sample = sample(peers, self.config.degree)

        # send PEER_ANNOUNCE on each Peer_connection
        for peer in peer_sample:
            await peer.send_peer_announce(packet_id, ttl, dtype, data)
        return

    async def handle_peer_announce(self, packet_id, ttl, dtype, data, peer):
        """Gets called upon arrival of a PEER_ANNOUNCE
           Performs several things:
              - drop if it is a known packet -> loop detected
              - else add it as a known id
              - act depending on the TTL: ends here, decrement ttl or infinite
              - send it to out subscribers of this datatype
              - if we want to forward it and all subs have to validate:
                add it to the dictionary of to-be validated announces
                'announces_to_verify'"""
        # routing loops: check if id is already in id list
        if self.__peer_announce_ids.contains(packet_id):
            return

        await self.__add_peer_announce_id(packet_id)

        if ttl == 1:  # ends here, no forwarding
            if dtype in self.__datasubs.keys():
                for sub in self.__datasubs.get(dtype):
                    sub.send_gossip_notification(packet_id, dtype, data)
            return

        if ttl > 0:
            ttl -= 1

        if dtype in self.__datasubs.keys():
            # save message and subs as tuple: (ttl, dtype, data, [datasubs])
            # and add to dictionary
            self.__announces_to_verify[packet_id] = (
                ttl, dtype, data, peer, self.__datasubs.get(dtype).copy())
            for sub in self.__datasubs.get(dtype):
                await sub.send_gossip_notification(packet_id, dtype, data)

        # no subscriber for this datatype
        # Spezification 4.2.2.: Do not propagate further.
        return

    async def handle_gossip_validation(self, msg_id, valid, api):
        """Gets called upon arrival of a GOSSIP_VALIDATION;
           - if the answer is negative, delete the announce packet from the
             queue, it will never be sent.
           - if the message ID is not in the to-be validated announces do
             nothing (APIs are honest)
           - delete this API from the validators
           - if it was the last: send a PEER_ANNOUNCE as all have positively
             validated
        """
        if not valid:
            # delete the whole entry
            self.__announces_to_verify.pop(msg_id, None)
            return

        if msg_id not in self.__announces_to_verify.keys():
            logging.debug("[API] Message ID of GOSSIP VALIDATION is " +
                          "currently not being validated!")
            return
        if api not in self.__announces_to_verify[msg_id][4]:
            logging.debug("[API] Sender {api} of GOSSIP VALIDATION is " +
                          "no validator!")
            return

        # remove this api from the validators of this message id
        self.__announces_to_verify[msg_id][4].remove(api)

        # check if we are the last to verify
        # if yes send PEER_ANNOUNCE to peer sample
        if len(self.__announces_to_verify[msg_id][4]) == 0:
            (ttl, dtype, data, peer, _) = self.__announces_to_verify.pop(msg_id, None)
            peer_sample = await self.__get_peer_sample()
            # remove original sender from sample
            if peer in peer_sample:
                peer_sample.remove(peer)

            # forward
            for peer in peer_sample:
                if peer.is_fully_validated():
                    await peer.send_peer_announce(msg_id, ttl, dtype, data)
        return

    async def __get_peer_sample(self):
        """Get a sample of the currently connected peers.

        Returns:
            - List of Peer_connections"""
        peers = self.__get_verified_pull_push_peers()
        if len(peers) < self.config.degree:
            return peers
        return sample(peers, self.config.degree)

    async def __get_verified_pull_push_peers(self):
        """Returns a list containing all verified pull and push peers. Acquires
        pull_peers_lock and push_peers_lock"""
        peers = []
        # Only take validated pull peers
        async with self.__pull_peers_lock:
            for peer in self.__pull_peers:
                if peer.is_fully_validated():
                    peers.append(peer)
        # push peers are assumed to be always verified (see unverified peers)
        async with self.__push_peers_lock:
            peers += list(self.__push_peers)
        return peers
