var _ = require('underscore');
require('ws');

var socket;

function WebSocket(url, protocols) {
  this.url = url;
  this.sent = [];
  this.closed = false;

  socket = this;
}

_.each(['CONNECTING', 'OPEN', 'CLOSING', 'CLOSED'], function(state, index) {
  WebSocket.prototype[state] = WebSocket[state] = index;
});

WebSocket.prototype.open = function() {
  (this.onopen || _.noop)();
};

WebSocket.prototype.close = function(code, reason) {
  this.closed = true;
  (this.onclose || _.noop)({ code: code, reason: reason });
};

WebSocket.prototype.send = function(data) {
  this.sent.push(JSON.parse(data));
};

WebSocket.prototype.receive = function(data) {
  (this.onmessage || _.noop)({ data: JSON.stringify(data) });
};

WebSocket.prototype.error = function() {
  (this.onerror || _.noop)({});
};

require.cache[require.resolve('ws')].exports = WebSocket;
var Client = require('../client');
delete require.cache[require.resolve('ws')];
delete require.cache[require.resolve('../client')];

describe('Client', function() {
  var client;
  var url = 'ws://example.com';

  beforeEach(function() {
    client = new Client();
  });

  describe('.open(url)', function() {
    it('should attempt to open a new connection', function() {
      client.open(url);
      expect(socket.url).toEqual(url);
    });

    it('should emit "open" on success', function(done) {
      client.open(url);
      client.on('open', done);
      socket.open();
    });

    it('should emit "error" on error before opening', function(done) {
      client.open();
      client.on('error', done);
      socket.error();
    });

    it('should emit "error" on error after opening', function(done) {
      client.open();
      socket.open();
      client.on('error', done);
      socket.error();
    });

    it('should emit "close" on failure before opening', function(done) {
      client.open();
      client.on('close', function(code, reason) {
        expect(code).toEqual(1006);
        expect(reason).toEqual('reason');
        done();
      });
      socket.close(1006, 'reason');
    });

    it('should emit "close" on failure after opening', function(done) {
      client.open();
      socket.open();
      client.on('close', function(code, reason) {
        expect(code).toEqual(1006);
        expect(reason).toEqual('reason');
        done();
      });
      socket.close(1006, 'reason');
    });

    it('should close any previous connection before opening', function(done) {
      client.open();
      client.on('close', done);
      client.open();
    });

    it('should close any previous connection after opening', function(done) {
      client.open();
      socket.open();
      client.on('close', done);
      client.open();
    });
  });

  describe('.close()', function() {
    it('should close the connection', function() {
      client.open();
      client.close();
      expect(socket.closed).toBe(true);

      client.open();
      socket.open();
      client.close();
      expect(socket.closed).toBe(true);
    });

    it('should emit "close" before opening', function(done) {
      client.open();
      client.on('close', done);
      client.close();
    });

    it('should emit "close" after opening', function(done) {
      client.open();
      socket.open();
      client.on('close', done);
      client.close();
    });

    it('should do nothing when not open', function() {
      client.on('close', function() {
        expect(true).toBe(false);
      });
      client.close();
    });

    it('should do nothing when closing', function() {
      client.open();
      socket.open();
      client.close();
      client.on('close', function() {
        expect(true).toBe(false);
      });
      client.close();
    });
  });

  describe('.request(method, args, callback)', function() {
    it('should send numbered requests to the server', function() {
      client.open();
      socket.open();

      client.request('foo', [1, 2], _.noop);
      client.request('bar', {3: 4}, _.noop);
      expect(socket.sent).toEqual([
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

    it('should call the callback on success', function(done) {
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

    it('should call the callback on error', function(done) {
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

    it('should call the callback on close', function(done) {
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
