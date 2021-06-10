import asyncio


async def connection_handler(host, port, on_connection_fnc):
    """Opens a socket server others can connect to and calls on_connection_fnc
    when a new client connects.
    Note that this function keeps waiting for new clients, therefore toes not
    return / exit.

    Arguments:
       host -- host address for server
       port -- port for server
       on_connection_fnc -- function that gets called when a client is 
                            connected. 
                            Will pass the clientsocket as an argument.
    """

    print("Opening Peer server at host: {}, port: {}".format(host, port))
    server = await asyncio.start_server(on_connection_fnc, host, port)

    async with server:
        await server.serve_forever()
