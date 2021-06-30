"""
This Module provides the Api_connection class
"""
from modules.packet_parser import (
        GOSSIP_ANNOUNCE,
        GOSSIP_NOTIFY,
        GOSSIP_VALIDATION,
        get_header_type,
        # parse_gossip_announce,
        parse_gossip_notify,
        # parse_gossip_validation
)


class Api_connection:
    """An Api_connection represents a connection to a single API user.

    Class variables:
    - gossip (Gossip) -- gossip responsible for this peer
    - reader (StreamReader) -- (private) asyncio StreamReader of connected peer
    - writer (StreamWriter) -- (private) asyncio StreamWriter of connected peer
    """

    def __init__(self, reader, writer, gossip):
        """
        Arguments:
        - reader (StreamReader) -- asyncio StreamReader of connected peer
        - writer (StreamWriter) -- asyncio StreamWriter of connected peer
        - gossip (Gossip) -- gossip responsible for this peer
        """
        self.gossip = gossip
        self.__reader = reader
        self.__writer = writer

    async def run(self):
        """Waits for incoming messages and handles them. Runs until the
        connection is closed"""
        while True:
            try:
                # TODO: correct?
                size = await self.__reader.read(2)
                buf = size + await self.__reader.read(size-2)
                await self.__reader.read()  # read trash/too long packet
            except ConnectionError:
                await self.gossip.close_api(self)
                return
            await self.__handle_incoming_message(buf)

    async def close(self):
        """Closes the connection to the API user.
        Gossip.close_api() should be called preferably, since it also removes
        the API from the API list and datatype dictionary."""
        print("Connection to {} closed".format(self.get_api_address()))
        try:
            self.__writer.close()
            await self.__writer.wait_closed()
        except:
            return

    def get_api_address(self):
        """Returns the address of this API user in the format host:port

        See also:
        - get_own_address()
        """
        # TODO returns None on error
        (host, port) = self.__writer.get_extra_info('peername')
        address = "{}:{}".format(host, port)
        return address

    def get_own_address(self):
        """Returns the address of this API user in the format host:port

        See also:
        - get_api_address()
        """
        (host, port) = self.__writer.get_extra_info('sockname')
        address = "{}:{}".format(host, port)
        return address

    async def __handle_gossip_announce(self, buf):
        return

    async def __handle_gossip_notify(self, buf):
        """adds the API user to our Subscriber dictionary
        """
        (datatype) = parse_gossip_notify(buf)
        self.gossip.add_subscriber(datatype, self)
        return

    async def __handle_gossip_validation(self, buf):
        return

    async def __handle_incoming_message(self, buf):
        """Checks the type of an incoming message in byte format and calls the
        correct handler according the the type.

        Arguments:
        - buf (byte-object) -- received message
        """
        type = get_header_type(buf)
        if type == GOSSIP_ANNOUNCE:
            print("\r\nReceived GOSSIP_ANNOUNCE from",
                  self.get_api_address())
            await self.__handle_gossip_announce(buf)
        elif type == GOSSIP_NOTIFY:
            print("\r\nReceived GOSSIP_NOTIFY from", self.get_api_address())
            await self.__handle_gossip_notify(buf)
        elif type == GOSSIP_VALIDATION:
            print("Received GOSSIP_VALIDATION from", self.get_api_address())
            self.__handle_gossip_validation(buf)
        else:
            print("\r\nReceived message with unknown type {} from {}".format(
                type, self.get_api_address()))
