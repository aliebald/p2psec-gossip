"""
This module provides the gossip class.
TODO: Description of gossip functionality?
"""

import asyncio
import logging

from modules.peers.peer_connection import (
    Peer_connection, peer_connection_factory)
from modules.api.api_connection import Api_connection
from modules.connection_handler import connection_handler
from random import (randint, sample)
from modules.util import SetQueue


class Gossip:
    """The Gossip class represents a single instance of Gossip. By
    instanciating it, gossip is started.

    Class variables:
    - config (Config) -- config object used for this instance of gossip
    - peers (Peer_connection List) -- Connected (active) peers
    - apis (Api_connection List) -- connected APIs
    - datasubs (int-[Api_connection] Dictionary) -- APIs subscribed to each
                                                    datatype
    """

    def __init__(self, config):
        """
        Arguments:
        - config (Config) -- config class object
        """
        self.config = config
        self.peers = []
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
        # start API connection handler
        (api_host, api_port) = self.config.api_address.split(":")
        asyncio.create_task(connection_handler(
            api_host, int(api_port), self.__on_api_connection))
        logging.debug("[API] started API connection handler on {}:{}"
                      .format(api_host, api_port))

        # connect to peers in config
        (_, p2p_listening_port) = self.config.p2p_address.split(":")
        if len(self.config.known_peers) > 0:
            self.peers = await peer_connection_factory(
                self.config.known_peers, self, int(p2p_listening_port))

        # TODO Ask bootstrapping service for peers if no peers where in the
        #      config or all peers from config where unreachable.

        asyncio.create_task(self.__run_peer_control())

        # Start active peers
        for peer in self.peers:
            asyncio.create_task(peer.run())

        # start peer connection handler
        (host, port) = self.config.p2p_address.split(":")
        asyncio.create_task(await connection_handler(
            host, int(port), self.__on_peer_connection))

    def __on_api_connection(self, reader, writer):
        new_api = Api_connection(reader, writer, self)
        logging.info(f"[API] New API connected: {new_api.get_api_address()}")
        self.apis.append(new_api)
        asyncio.create_task(new_api.run())

    def __on_peer_connection(self, reader, writer):
        """Gets called when a new peer tries to connect.

        Arguments:
        - reader (StreamReader) -- asyncio StreamReader connected to a new peer
        - writer (StreamWriter) -- asyncio StreamWriter connected to a new peer
        """
        # TODO implement. The current implementation is rather rudimentary
        new_peer = Peer_connection(reader, writer, self)
        logging.info(f"New peer connected: {new_peer.get_debug_address()}")
        self.peers.append(new_peer)
        asyncio.create_task(new_peer.run())

    async def offer_peers(self, peer_addresses):
        """Offers peer_addresses to this gossip class. Gets called after a peer
        offer was received.

        Arguments:
        - peer_addresses (str List) -- addresses of potential peers, received
          from peer offer. format: host_ip:port
        """
        # remove already connected peers
        connected = self.get_peer_addresses()
        candidates = list(filter(lambda x: x not in connected, peer_addresses))

        logging.debug(f"[PEER] Offer contained: {peer_addresses}")
        logging.debug(f"[PEER] Connect to: {candidates}")

        # Open a connection to new Peers
        if len(candidates) > 0:
            (_, p2p_listening_port) = self.config.p2p_address.split(":")
            new_peers = await peer_connection_factory(
                candidates, self, int(p2p_listening_port))
            self.peers += new_peers
            # start new peers
            for peer in new_peers:
                asyncio.create_task(peer.run())

    def get_peer_addresses(self):
        """Returns the p2p listening addresses of all known peers in a list

        Returns:
            List of strings with format: <host_ip>:<port>
        """
        addresses = []
        for peer in self.peers:
            addresses.append(peer.get_peer_p2p_listening_address())
        return list(filter(lambda x: x is not None, addresses))

    async def close_peer(self, peer):
        """Removes a Peer_connection from the Peer_connection list and calls
        close on the Peer_connection.

        Arguments:
        - peer (Peer_connection) -- Peer_connection instance that should be
          closed
        """
        self.peers = list(filter(lambda p: p != peer, self.peers))
        await peer.close()

        logging.debug("[PEER] Connected peers: " +
                      f"{self.get_peer_addresses()}\r\n")

    async def __run_peer_control(self):
        """Ensures that self.peers has at least self.config.degree many peers
        """
        while True:
            if len(self.peers) < self.config.degree:
                logging.info("\r\nLooking for new Peers")
                logging.info(f"Connected peers: {self.get_peer_addresses()}")
                # Send PeerDiscovery
                for peer in self.peers:
                    logging.debug("  sending peer discovery to" +
                                  f"{peer.get_debug_address}")
                    await peer.send_peer_discovery()

            await asyncio.sleep(self.config.search_cooldown)

    async def print_gossip_debug(self):
        logging.debug(f"[PEER] connected peers: {self.peers}")
        logging.debug(f"[API] connected apis {self.apis}")
        logging.debug(f"[API] current subscribers {self.datasubs}")
        logging.debug("[API] current routing ids: " +
                      f"{list(self.peer_announce_ids.queue)}")
        logging.debug("[API] current announces to verify: " +
                      f"{self.announces_to_verify}\r\n")

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
            peer_sample = sample(self.peers, self.config.degree)
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
        if len(self.peers) < self.config.degree:
            peer_sample = self.peers
        else:
            peer_sample = sample(self.peers, self.config.degree)
        return peer_sample
