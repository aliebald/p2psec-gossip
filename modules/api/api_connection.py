"""
This Module provides the Api_connection class
"""
import hexdump
from modules.packet_parser import (
        GOSSIP_ANNOUNCE,
        GOSSIP_NOTIFY,
        GOSSIP_VALIDATION,
        get_header_type,
        parse_gossip_announce,
        parse_gossip_notify,
        parse_gossip_validation,
        build_gossip_notification
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

    def __str__(self):
        """called by str(Api_connection)
           one object should be printed as:
               api<ip:port>
           with infos of the connecting API"""
        return "api<"+self.get_api_address()+">"

    def __repr__(self):
        """string representation
           one object should be printed as:
               api<ip:port>
           with infos of the connecting API"""
        return "api<"+self.get_api_address()+">"

    async def run(self):
        """Waits for incoming messages and handles them. Runs until the
        connection is closed"""
        while True:
            try:
                if self.__writer.is_closing():
                    break
                size_bytes = await self.__reader.read(2)
                size = int.from_bytes(size_bytes, "big")
                buf = size_bytes + await self.__reader.read(size-2)

                # Note: Too long packets would be read incorrectly next loop
                #       and the API user will be disconnected

                # Debug
                print("size field: "+str(size)+" Bytes")
                print("Whole packet: ")
                hexdump.hexdump(buf)
            except ConnectionError:
                await self.gossip.close_api(self)
                return
            # TODO: async
            await self.__handle_incoming_message(buf)

    async def close(self):
        """Closes the connection to the API user.
        Gossip.close_api() should be called preferably, since it also removes
        the API from the API list and datatype dictionary."""
        # TODO: Exception handling
        print("[API] Connection to {} closed".format(self.get_api_address()))
        self.__writer.close()
        await self.__writer.wait_closed()
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
        """Returns the listening address of ourselves locally in the format
            host:port

        See also:
        - get_api_address()
        """
        (host, port) = self.__writer.get_extra_info('sockname')
        address = "{}:{}".format(host, port)
        return address

    async def __handle_gossip_announce(self, buf):
        tmp = parse_gossip_announce(buf)
        if tmp == ():
            print("[API] Disconnecting API user " + str(self) +
                  ", GOSSIP_ANNOUNCE malformed")
            await self.gossip.close_api(self)

        (ttl, dtype, data) = tmp

        await self.gossip.handle_gossip_announce(ttl, dtype, data)
        return

    async def __handle_gossip_notify(self, buf):
        """adds the API user to our Subscriber dictionary
        """
        (datatype) = parse_gossip_notify(buf)
        await self.gossip.add_subscriber(datatype, self)

        print("[API] "+str(self)+" subscribed to datatype "+str(datatype))
        return

    async def __handle_gossip_validation(self, buf):
        """after a GOSSIP_ANNOUNCE to an API user we receive a
        GOSSIP_VALIDATION; if its negative we do not spread further.
        """
        (msg_id, valid) = parse_gossip_validation(buf)
        await self.gossip.handle_gossip_validation(msg_id, valid, self)
        return

    async def __handle_incoming_message(self, buf):
        """Checks the type of an incoming message in byte format and calls the
        correct handler according the the type.

        Arguments:
        - buf (byte-object) -- received message
        """
        type = get_header_type(buf)
        if type == GOSSIP_ANNOUNCE:
            print("\r\n[API] Received GOSSIP_ANNOUNCE from",
                  self.get_api_address())
            await self.__handle_gossip_announce(buf)
        elif type == GOSSIP_NOTIFY:
            print("\r\n[API] Received GOSSIP_NOTIFY from",
                  self.get_api_address())
            await self.__handle_gossip_notify(buf)
        elif type == GOSSIP_VALIDATION:
            print("\r\n[API] Received GOSSIP_VALIDATION from",
                  self.get_api_address())
            await self.__handle_gossip_validation(buf)
        else:
            print("\r\nReceived message with unknown type {} from {}".format(
                type, self.get_api_address()))
            print("[API] Disconnecting API user, wrong message")
            await self.gossip.close_api(self)
        # Debug
        await self.gossip.print_api_debug()
        return

    async def send_gossip_notification(self, msg_id, dtype, data):
        buf = build_gossip_notification(msg_id, dtype, data)
        self.writer.write(buf)
