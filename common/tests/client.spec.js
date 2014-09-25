var _ = require('underscore');
require('ws');

describe('Client', function() {
  var WebSocket, socket, requests;
  var client;

  beforeEach(function() {
    WebSocket = spyOn(require.cache[require.resolve('ws')], 'exports');
    socket = {
      open: function() {
        socket.onopen();
      },

      close: function() {
        socket.onclose({ code: 1006, reason: 'reason' });
      },

      send: function(data) {
        requests.push(JSON.parse(data));
      },

      receive: function(data) {
        socket.onmessage({
          data: JSON.stringify(data)
        });
      }
    };
    requests = [];
    WebSocket.and.returnValue(socket);

    delete require.cache[require.resolve('../client')];
    var Client = require('../client');
    client = new Client();
  });

  describe('.open(url, [protocols])', function() {
    it('should attempt to open a new connection', function() {
      var url = 'ws://example.com';
      var protocols = ['protocol1', 'protocol2'];
      client.open(url, protocols);
      expect(WebSocket).toHaveBeenCalledWith(url, protocols);
    });

    it('should emit "open" on success', function(done) {
      client.open();
      client.on('open', done);
      socket.open();
    });

    it('should emit "close" on failure', function(done) {
      client.open();
      client.on('close', function(code, reason) {
        expect(code).toEqual(1006);
        expect(reason).toEqual('reason');
        done();
      });
      socket.close();
    });

    it('should close any previous connection', function(done) {
      client.open();
      socket.close = done;
      client.open();
    });

    it('should update "connected" property', function() {
      expect(client.connected).toBe(false);
      client.open();
      expect(client.connected).toBe(false);
      socket.open();
      expect(client.connected).toBe(true);
    });
  });

  describe('.close()', function() {
    it('should close the connection', function(done) {
      client.open();
      socket.close = done;
      client.close();
    });

    it('should emit "close"', function(done) {
      client.open();
      client.on('close', done);
      client.close();
    });

    it('should do nothing when not open', function() {
      client.on('close', function() {
        expect(true).toBe(false);
      });
      client.close();
    });

    it('should update "connected" property', function() {
      client.open();
      socket.open();
      expect(client.connected).toBe(true);
      socket.close();
      expect(client.connected).toBe(false);
    });
  });

  describe('.request(method, args, callback)', function() {
    it('should send numbered requests to the server', function() {
      client.open();
      socket.open();

      client.request('foo', [1, 2], _.noop);
      client.request('bar', {3: 4}, _.noop);
      expect(requests).toEqual([
        {
          jsonrpc: '2.0',
          id: 0,
          method: 'foo',
          params: [1, 2]
        },
        {
          jsonrpc: '2.0',
          id: 1,
          method: 'bar',
          params: {3: 4}
        }
      ]);
    });

    it('should throw when not open', function() {
      client.open();
      expect(function() {
        client.request('foo', [1, 2], _.noop);
      }).toThrow();
    });

    it('should call on success', function(done) {
      client.open();
      socket.open();

      client.request('foo', [1, 2], function(err, result) {
        expect(err).toBeFalsy();
        expect(result).toBe('result');
        done();
      });
      client.request('bar', {3: 4}, _.noop);

      socket.receive({
        id: 0,
        error: null,
        result: 'result'
      });
    });

    it('should call on error', function(done) {
      client.open();
      socket.open();

      client.request('foo', [1, 2], function(err, result) {
        expect(err).toEqual(new Error('oops'));
        expect(result).toBe(null);
        done();
      });
      client.request('bar', {3: 4}, _.noop);

      socket.receive({
        id: 0,
        error: {
          code: 0,
          message: 'oops'
        },
        result: null
      });
    });

    it('should call on close', function(done) {
      client.open();
      socket.open();

      client.request('foo', [1, 2], function(err, result) {
        expect(err).toBeTruthy();
        done();
      });
      client.request('bar', {3: 4}, _.noop);

      socket.close();
    });
  });

  it('should emit events', function(done) {
    client.open();
    socket.open();

    var data = {
      event: 'foo',
      params: [1, 2]
    };

    client.on('event', function(name, event) {
      expect(name).toEqual('foo');
      expect(event).toEqual(data);
      done();
    });

    socket.receive(data);
  });
});
