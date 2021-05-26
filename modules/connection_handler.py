import socket


# Opens a socket others can connect to and calls on_connection_fnc when a new
# client connects.
# Note that this function keeps waiting for new clients, therefore toes not
# return / exit.
#
# Arguments:
#    host -- host address for server
#    port -- port for server
#    on_connection_fnc -- function that gets called when a client is connected.
#                         Will pass the clientsocket as an argument.
def connection_handler(host, port, on_connection_fnc):
    print("Opening Peer server at host: {} ({}), port: {} ({})".format(
        host, type(host), port, type(port)))
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.bind((host, port))
    serversocket.listen()

    while True:
        (clientsocket, address) = serversocket.accept()
        on_connection_fnc(clientsocket)
