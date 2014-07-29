import sys

def serve():
    from twisted.internet import reactor
    from twisted.web import server

    from butler import Butler

    b = Butler()
    # TODO: port and address
    reactor.listenTCP(6969, server.Site(b))
    reactor.run()
    return 0

def client():
    from twisted.internet import reactor, stdio

    from client import Client

    stdio.StandardIO(Client('http://127.0.0.1:6969/'))
    reactor.run()

def main(argv):
    if argv[1:] == ['--client']:
        return client()
    else:
        return serve()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
