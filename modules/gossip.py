"""
This module provides the gossip class.
TODO: Description of gossip functionality?
"""

import asyncio
import logging
from random import (randint, sample, shuffle)
from math import (floor, ceil)

from modules.util import SetQueue
from modules.api.api_connection import Api_connection
from modules.connection_handler import connection_handler
from modules.peers.peer_connection import (
    Peer_connection, peer_connection_factory)


class Gossip:
    """The Gossip class represents a single instance of Gossip. By
    instanciating it, gossip is started.

    Class variables:
    - config (Config) -- config object used for this instance of gossip
    - push_peers (Peer_connection List) -- Connected (active) push peers /
      peers that connected to us
    - pull_peers (Peer_connection List) -- Connected (active) pull peers / 
      peers we learned about from other peers and than connected to.
    - unverified_peers (Peer_connection List) -- peers that connected to us 
      that still need to be verified. After beeing verified, they will be moved 
      into push_peers.
    - max_push_peers (int) -- push_peers capacity
    - max_pull_peers (int) -- pull_peers capacity
    - apis (Api_connection List) -- connected APIs
    - datasubs (dictionary: int-[Api_connection]) -- Datatypes linking to all 
      theire subscribing APIs
    - peer_announce_ids (SetQueue) -- TODO document
    - announces_to_verify (dictionary: int - Tuple List) -- open 
      PEER_ANNOUNCES. PEER_ANNOUNCES Will be forwarded if/when all subscribers 
      verify the message. 
      Format: message-id : [(ttl, datatype, data, [datasubs])]
    """

    def __init__(self, config):
        """
        Arguments:
        - config (Config) -- config class object
        """
        self.config = config

        # TODO floor / ceil?
        self.max_push_peers = floor(self.config.max_connections / 2)
        self.max_pull_peers = ceil(self.config.max_connections / 2)

        self.push_peers = []  # Push peers that connected to us
        self.pull_peers = []  # Pull peers that we connected to
        self.unverified_peers = []  # unverified push peers
        self.apis = []

        #                          Key - Value
        # Subscriber list, Format: Int - List of Api_connections
        self.datasubs = {}
        self.peer_announce_ids = SetQueue(self.config.cache_size)
        # Dictionary of buffered PEER_ANNOUNCEs;
        # Key: int - Message ID
        # Value: [ int, int     , bytes, Peer_connection, [Peer_connection]]
        #        [(ttl, datatype, data , sender         , [datasubs])]
        self.announces_to_verify = {}

    async def run(self):
        """Starts this gossip instance.
        Tries to connect to all known peers or connect to bootstrapping
        service, if no peers where in the config.
        Starts peer controll (responsible for maintaining degree many peers),
        peers and waits for new incoming connections.
        """
        # connect to peers in config
        (_, p2p_listening_port) = self.config.p2p_address.split(":")
        num_known_peers = len(self.config.known_peers)
        if num_known_peers > 0:
            logging.debug(f"Connecting to {num_known_peers} known peers")
            self.pull_peers = await peer_connection_factory(
                self.config.known_peers, self, int(p2p_listening_port))

        # No known_peers in config or all where unreachable
        # -> Connect to bootstrapping node
        if len(self.pull_peers) == 0:
            logging.debug("Connecting to bootstrapping node")
            self.pull_peers = await peer_connection_factory(
                [self.config.bootstrapper], self, int(p2p_listening_port))

        # start API connection handler
        (api_host, api_port) = self.config.api_address.split(":")
        asyncio.create_task(connection_handler(
            api_host, int(api_port), self.__on_api_connection))
        logging.debug("[API] started API connection handler on {}:{}\r\n"
                      .format(api_host, api_port))

        asyncio.create_task(self.__run_peer_control())

        # Start active peers
        for peer in self.pull_peers:
            asyncio.create_task(peer.run())

        # start peer connection handler
        (host, port) = self.config.p2p_address.split(":")
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
        # Check if we have capacity for this new push peer
        if (len(self.push_peers) + len(self.unverified_peers)
                >= self.max_push_peers):
            logging.info("Reached max push peers, ignoring new incoming peer")
            writer.close()
            await writer.wait_closed()
            return

        new_peer = Peer_connection(reader, writer, self, is_validated=True)
        logging.info(f"New unverified peer connected: {new_peer}")

        self.unverified_peers.append(new_peer)
        asyncio.create_task(new_peer.run())

    def validate_peer(self, peer):
        """Removes the given peer from the unverified_peers list and adds it to
        push_peers"""
        if peer not in self.unverified_peers:
            logging.warning(
                "[validate_peer]: Peer not found in unverified_peers")

            self.__log_connected_peers()
            logging.info("Connected unverified peers: {} len: {}".format(
                self.get_peer_addresses(self.unverified_peers), len(self.unverified_peers)))
            return

        self.unverified_peers.remove(peer)
        self.push_peers.append(peer)

    async def handle_peer_offer(self, peer_addresses):
        """Offers peer_addresses to this gossip class. Gets called after a peer
        offer was received.

        Arguments:
        - peer_addresses (str List) -- addresses of potential peers, received
          from peer offer. format: host_ip:port
        """
        if (len(self.pull_peers) + len(self.unverified_peers)
                >= self.max_pull_peers):
            logging.debug(
                "Ignoring peer offer because max pull peers are reached")
            return

        logging.info(f"Offer contained: {peer_addresses}")
        # remove already connected peers
        all_peers = self.push_peers + self.pull_peers + self.unverified_peers
        connected = self.get_peer_addresses(all_peers)
        candidates = list(filter(lambda x: x not in connected, peer_addresses))

        if len(candidates) == 0:
            logging.info("No new peers found in offer")

        logging.info(f"Candidates: {candidates}")
        shuffle(candidates)
        (_, p2p_listening_port) = self.config.p2p_address.split(":")
        # missing_peers to reach max_pull_peers
        missing_peers = self.max_pull_peers - len(self.pull_peers)

        # Open connections to missing_peers new Peers. If a peer did not
        # respond / a connection attempt failed, repeat until we reach the
        # max_pull_peers or no candidates are left
        while missing_peers > 0 and len(candidates) > 0:
            connect_to = candidates[:min(missing_peers, len(candidates))]
            candidates = candidates[min(missing_peers, len(candidates)):]
            new_peers = await peer_connection_factory(
                connect_to, self, int(p2p_listening_port))
            self.pull_peers += new_peers
            missing_peers -= len(new_peers)
            # start new peers
            for peer in new_peers:
                asyncio.create_task(peer.run())

    def get_peer_addresses(self, peerlist=None):
        """Returns the p2p listening addresses of all known peers in a list

        Arguments:
        - peerlist: List containing Peer_connections, default = None. If this
          is not None, the addresses contained within the list will be returned
          If this is None, the addresses of push_peers and pull_peers will be 
          returned. 
          This can be used to exclusively get the addresses of pull or push peers.

        Returns:
            List of strings with format: <host_ip>:<port>
        """
        peers = (peerlist if peerlist != None
                 else self.push_peers + self.pull_peers)

        addresses = []
        for peer in peers:
            addresses.append(peer.get_peer_p2p_listening_address())
        return list(filter(lambda x: x is not None, addresses))

    async def close_peer(self, peer):
        """Removes a Peer_connection from gossip and calls close on the 
        Peer_connection.

        Arguments:
        - peer (Peer_connection) -- Peer_connection instance that should be
          closed
        """
        self.__log_connected_peers()
        if peer in self.push_peers:
            self.push_peers.remove(peer)
        elif peer in self.pull_peers:
            self.pull_peers.remove(peer)
        elif peer in self.unverified_peers:
            self.unverified_peers.remove(peer)
        else:
            # It can happen that the peer is not in any of the above lists, e.g.
            # when a connection is closed directly after establishing it in the
            # Peer_connection factory
            logging.debug("The Peer that should be closed was not found in"
                          "push_peers, pull_peers or unverified_peers")

        await peer.close()
        self.__log_connected_peers()

    async def __run_peer_control(self):
        """Ensures that self.push_peers has at least max_push_peers many peers
        """
        while True:
            search_new_peers = (
                len(self.push_peers) + len(self.unverified_peers)
                < self.max_push_peers
                and len(self.push_peers) + len(self.pull_peers)
                < self.config.min_connections
            )
            if search_new_peers:
                logging.info("- - - - - - - - - - -")
                logging.info("Looking for new Peers")
                # Send PeerDiscovery
                for peer in self.push_peers + self.pull_peers:
                    await peer.send_peer_discovery()
            self.__log_connected_peers()

            # Verify new peers
            if len(self.unverified_peers) > 0:
                # TODO handle case: more peers than excepted
                for peer in self.unverified_peers:
                    await peer.send_peer_challenge()

            await asyncio.sleep(self.config.search_cooldown)

    async def print_gossip_debug(self):
        # logging.debug(f"[PEER] connected peers: {self.peers}") # TODO fix
        logging.debug(f"[API] connected apis {self.apis}")
        logging.debug(f"[API] current subscribers {self.datasubs}")
        logging.debug("[API] current routing ids: " +
                      f"{list(self.peer_announce_ids.queue)}")
        logging.debug("[API] current announces to verify: " +
                      f"{self.announces_to_verify}\r\n")

    def __log_connected_peers(self):
        """Logs push and pull peers including capacities"""
        logging.info("Connected push peers: {}. {}/{}".format(
            self.get_peer_addresses(self.push_peers),
            len(self.push_peers), self.max_push_peers))
        logging.info("Connected pull peers: {}. {}/{}".format(
            self.get_peer_addresses(self.pull_peers),
            len(self.pull_peers), self.max_pull_peers))

    async def print_api_debug(self):
        print("[API] connected apis: " + str(self.apis))
        print("[API] current subscribers: " + str(self.datasubs))
        print("[API] current routing ids: " +
              str(list(self.peer_announce_ids.queue)))
        print("[API] current announces to verify: " +
              str(self.announces_to_verify))

    async def add_subscriber(self, datatype, api):
        """Adds an Api_connection to the Subscriber dict (datasubs)
           gets called after a GOSSIP_NOTIFY
        """
        if datatype in self.datasubs.keys():
            temp = self.datasubs[datatype]
            temp.append(api)
            self.datasubs[datatype] = temp
        else:
            self.datasubs[datatype] = [api]

        return

    async def __remove_subscriber(self, api):
        """Removes an Api_connection from the whole Subscriber dict (datasubs)
        """
        for key in self.datasubs:
            if api in self.datasubs[key]:
                self.datasubs[key].remove(api)
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
        if self.peer_announce_ids.full():
            self.peer_announce_ids.get()
        # duplicates wont be added as we use SetQueue
        self.peer_announce_ids.put(packet_id)

    async def handle_gossip_announce(self, ttl, dtype, data):
        """Gets called upon arrival of a GOSSIP_ANNOUNCE
           Performs several things:
              - generate a packet id
              - add it as a known id
              - send a PEER_ANNOUNCE to a sample of degree peers"""
        # Generate PEER_ANNOUNCE id
        packet_id = randint(0, 2**64-1)
        while self.peer_announce_ids.contains(packet_id):
            packet_id = randint(0, 2**64-1)
        # Save this id for routing loop prevention
        await self.__add_peer_announce_id(packet_id)

        # Choose degree peers randomly
        # TODO: if peers < degree, choose all peers
        try:
            peers = self.pull_peers + self.push_peers
            peer_sample = sample(peers, self.config.degree)
        except ValueError:
            peer_sample = []

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
        if self.peer_announce_ids.contains(packet_id):
            return

        await self.__add_peer_announce_id(packet_id)

        if ttl == 1:  # ends here, no forwarding
            if dtype in self.datasubs.keys():
                for sub in self.datasubs.get(dtype):
                    sub.send_gossip_notification(packet_id, dtype, data)
            return

        if ttl > 0:
            ttl -= 1

        if dtype in self.datasubs.keys():
            # save message and subs as tuple: (ttl, dtype, data, [datasubs])
            # and add to dictionary
            self.announces_to_verify[packet_id] = \
                (ttl, dtype, data, peer, self.datasubs.get(dtype).copy())
            for sub in self.datasubs.get(dtype):
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
            self.announces_to_verify.pop(msg_id, None)
            return

        if msg_id not in self.announces_to_verify.keys():
            logging.debug("[API] Message ID of GOSSIP VALIDATION is " +
                          "currently not being validated!")
            return
        if api not in self.announces_to_verify[msg_id][4]:
            logging.debug("[API] Sender {api} of GOSSIP VALIDATION is " +
                          "no validator!")
            return

        # remove this api from the validators of this message id
        self.announces_to_verify[msg_id][4].remove(api)

        # check if we are the last to verify
        # if yes send PEER_ANNOUNCE to peer sample
        if len(self.announces_to_verify[msg_id][4]) == 0:
            (ttl, dtype, data, peer, _) = \
                self.announces_to_verify.pop(msg_id, None)
            peer_sample = await self.__get_peer_announce_sample(
                msg_id, ttl, dtype, data)
            # remove original sender from sample
            if peer in peer_sample:
                peer_sample.remove(peer)

            # forward
            for peer in peer_sample:
                await peer.send_peer_announce(msg_id, ttl, dtype, data)
        return

    async def __get_peer_announce_sample(self, packet_id, ttl, dtype, data):
        """Gets called if you want to send a PEER_ANNOUNCE to a sample
           of currently connected peers."""
        peers = self.pull_peers + self.push_peers
        if len(peers) < self.config.degree:
            return peers
        return sample(peers, self.config.degree)
