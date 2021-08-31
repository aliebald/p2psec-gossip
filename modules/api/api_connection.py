"""
This Module provides the Api_connection class
"""
import logging
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
                # Note: Too long packets would be read incorrectly next loop
                #       and the API user will be disconnected
                size_bytes = await self.__reader.read(2)
                size = int.from_bytes(size_bytes, "big")
                buf = size_bytes + await self.__reader.read(size-2)
                logging.debug("[API] Packet arrived:\n       " +
                              f"{hexdump.dump(buf)}")
            except ConnectionError:
                await self.gossip.close_api(self)
                return
            await self.__handle_incoming_message(buf)

    async def close(self):
        """Closes the connection to the API user.
        Gossip.close_api() should be called preferably, since it also removes
        the API from the API list and datatype dictionary."""

        logging.info(f"[API] Connection to {self.get_api_address()} closed")
        try:
            self.__writer.close()
            await self.__writer.wait_closed()
            return
        except Exception:
            return

    def get_api_address(self):
        """Returns the address of this API user in the format host:port

        See also:
        - get_own_address()
        """
        # TODO returns None on error
        (host, port) = self.__writer.get_extra_info("peername")
        address = "{}:{}".format(host, port)
        return address

    def get_own_address(self):
        """Returns the listening address of ourselves locally in the format
            host:port

        See also:
        - get_api_address()
        """
        (host, port) = self.__writer.get_extra_info("sockname")
        address = "{}:{}".format(host, port)
        return address

    async def __handle_gossip_announce(self, buf):
        tmp = parse_gossip_announce(buf)
        if tmp == ():
            logging.info(f"[API] Disconnecting API user {self} -" +
                         "GOSSIP_ANNOUNCE malformed")
            await self.gossip.close_api(self)

        (ttl, dtype, data) = tmp

        await self.gossip.handle_gossip_announce(ttl, dtype, data)
        return

    async def __handle_gossip_notify(self, buf):
        """adds the API user to our Subscriber dictionary
        """
        (datatype) = parse_gossip_notify(buf)
        await self.gossip.add_subscriber(datatype, self)

        logging.debug(f"[API] {self} subscribed to datatype {datatype}")
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
        mtype = get_header_type(buf)
        if mtype == GOSSIP_ANNOUNCE:
            logging.info("[API] Received GOSSIP_ANNOUNCE from " +
                         f"{self.get_api_address()}")
            await self.__handle_gossip_announce(buf)
        elif mtype == GOSSIP_NOTIFY:
            logging.info("[API] Received GOSSIP_NOTIFY from " +
                         f"{self.get_api_address()}")
            await self.__handle_gossip_notify(buf)
        elif mtype == GOSSIP_VALIDATION:
            logging.info("[API] Received GOSSIP_VALIDATION from " +
                         f"{self.get_api_address()}")
            await self.__handle_gossip_validation(buf)
        else:
            logging.info(f"[API] Received message with unknown type {mtype} " +
                         f"from {self.get_api_address()}\n" +
                         "[API] Disconnecting API user, wrong message")
            await self.gossip.close_api(self)
        # Debug
        await self.gossip.print_gossip_debug()
        return

    async def send_gossip_notification(self, msg_id, dtype, data):
        buf = build_gossip_notification(msg_id, dtype, data)
        logging.info(f"[API] Sending GOSSIP_NOTIFICATION to {self}")
        self.__writer.write(buf)
