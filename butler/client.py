import json
from twisted.protocols.basic import LineReceiver
from txjsonrpc.web.jsonrpc import Proxy

class Client(LineReceiver):
    from os import linesep as delimiter

    def __init__(self, url):
        self._proxy = Proxy(url)

    def connectionMade(self):
        self.transport.write('>>> ')

    def lineReceived(self, line):
        if line.strip() == 'quit':
            from twisted.internet import reactor
            reactor.stop()
            return
        try:
            command = line.split()
            if command:
                method = command[0]
                args = [json.loads(s) for s in command[1:]]
                d = self._proxy.callRemote(method, *args)
                d.addCallbacks(self._printValue, self._printError)
        except ValueError:
            self.transport.write('Error: could not decode request.\n')
        finally:
            self.transport.write('>>> ')

    def _printValue(self, value):
        self.transport.write('Result: %s\n' % str(value))
        self.transport.write('>>> ')

    def _printError(self, error):
        fault = error.value
        self.transport.write('Error %i: %s\n' %
            (fault.faultCode, str(fault.faultString)))
        self.transport.write('>>> ')
