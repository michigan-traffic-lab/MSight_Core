import socketserver


class ThreadedUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    pass

class MyUDPHandler(socketserver.BaseRequestHandler):
    """
    This class works similar to the TCP handler class, except that
    self.request consists of a pair of data and client socket, and since
    there is no connection the client address must be given explicitly
    when sending data back via sendto().
    """

    def handle(self):
        data = self.request[0].strip()
        print(f'{self.client_address[0]} wrote:')
        print(data)


if __name__ == "__main__":
    # HOST, PORT = "0.0.0.0", 9000
    HOST, PORT = "127.0.0.1", 12345


    with ThreadedUDPServer((HOST, PORT), MyUDPHandler) as server:
        print(f'starting server at {HOST}:{PORT}')
        server.serve_forever()

