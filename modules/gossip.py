"""
This module provides the gossip class.
TODO: Description of gossip functionality?
"""

import asyncio

from modules.peers.peer_connection import (
    Peer_connection, peer_connection_factory)
from modules.api.api_connection import Api_connection
from modules.connection_handler import connection_handler


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
        print("gossip\r\n")
        self.config = config
        self.peers = []
        self.apis = []
        #                          Key - Value
        # Subscriber list, Format: Int - List of Api_connections
        self.datasubs = {}

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
        print("[API] started API connection handler on {}:{}"
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
        print("New API connected", new_api.get_api_address())
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
        print("New peer connected", new_peer.get_debug_address())
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

        print("Offer contained:", peer_addresses)
        print("Connect to:", candidates)

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
        return list(filter(lambda x: x != None, addresses))

    async def close_peer(self, peer):
        """Removes a Peer_connection from the Peer_connection list and calls
        close on the Peer_connection.

        Arguments:
        - peer (Peer_connection) -- Peer_connection instance that should be
          closed
        """
        self.peers = list(filter(lambda p: p != peer, self.peers))
        await peer.close()

        print("Connected peers: {}\r\n".format(self.get_peer_addresses()))

    async def __run_peer_control(self):
        """Ensures that self.peers has at least self.config.degree many peers
        """
        while True:
            if len(self.peers) < self.config.degree:
                print("\r\nLooking for new Peers")
                print("Connected peers: {}".format(self.get_peer_addresses()))
                # Send PeerDiscovery
                for peer in self.peers:
                    print("  sending peer discovery to",
                          peer.get_debug_address())
                    await peer.send_peer_discovery()

            await asyncio.sleep(self.config.search_cooldown)

    async def print_api_debug(self):
        print("[API] connected apis: " + str(self.apis))
        print("[API] current subscribers: " + str(self.datasubs))

    async def add_subscriber(self, datatype, api):
        """Adds an Api_connection to the Subscriber dict (datasubs)
        """
        if datatype in self.datasubs:
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
