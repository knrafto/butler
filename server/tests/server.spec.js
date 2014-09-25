var EventEmitter = require('events').EventEmitter;
var Q = require('q');
var ws = require('ws');
var _ = require('underscore');

var butler = require('../butler');

describe('server', function() {
  var server;
  var start;

  function messages(socket) {
    return _.map(socket.send.calls.allArgs(), function(args) {
      expect(args.length).toEqual(1);
      return JSON.parse(args[0]);
    });
  }

  beforeEach(function() {
    server = new EventEmitter();
    spyOn(ws, 'Server').and.returnValue(server);
    delete require.cache[require.resolve('../services/server')];
    start = require('../services/server');
  });

  afterEach(function() {
    butler.reset();
  });

  it('should start a server', function() {
    var config = {
      hostname: 'localhost',
      port: 54010
    };
    start(config);
    expect(ws.Server).toHaveBeenCalledWith({
      host: 'localhost',
      port: 54010
    });
  });

  describe('events', function() {
    it('should be sent to all open connections', function() {
      start();
      var sockets = _.map(_.range(3), function() {
        var socket =  new EventEmitter();
        socket.send = jasmine.createSpy('send');
        server.emit('connection', socket);
        return socket;
      });

      butler.emit('foo', 1, 2);
      butler.emit('bar', 3, 4);

      _.each(sockets, function(socket) {
        expect(messages(socket)).toEqual([
          {
            event: 'foo',
            params: [1, 2]
          },
          {
            event: 'bar',
            params: [3, 4]
          }
        ]);
      });
    });

    it('should not be sent to closed connections', function() {
      start();
      _.times(3, function() {
        var socket =  new EventEmitter();
        socket.send = _.noop;
        server.emit('connection', socket);
      });

      var socket = new EventEmitter();
      socket.send = jasmine.createSpy('send');
      server.emit('connection', socket);

      butler.emit('foo', 1, 2);
      socket.emit('close');
      butler.emit('bar', 3, 4);

      expect(messages(socket)).toEqual([
        {
          event: 'foo',
          params: [1, 2]
        }
      ]);
    });
  });

  describe('requests', function() {
    it('should be responded to', function(done) {
      start();
      var socket = new EventEmitter();
      server.emit('connection', socket);

      butler.register('foo', function(a, b) {
        return a + b;
      });

      socket.emit('message', JSON.stringify({
        id: 10,
        method: 'foo',
        params: [1, 2]
      }));

      socket.send = function(message) {
        expect(JSON.parse(message)).toEqual({
          id: 10,
          error: null,
          result: 3
        });
        done();
      };
    });

    it('should handle errors', function(done) {
      start();
      var socket = new EventEmitter();
      server.emit('connection', socket);

      butler.register('foo', function() {
        throw new Error('bam');
      });

      socket.emit('message', JSON.stringify({
        id: 10,
        method: 'foo',
        params: [1, 2]
      }));

      socket.send = function(message) {
        expect(JSON.parse(message)).toEqual({
          id: 10,
          error: {
            code: 0,
            message: 'bam'
          },
          result: null
        });
        done();
      };
    });

    it('should wait for promises', function(done) {
      start();
      var socket = new EventEmitter();
      server.emit('connection', socket);

      butler.register('foo', function(a, b) {
        return Q(a + b);
      });

      socket.emit('message', JSON.stringify({
        id: 10,
        method: 'foo',
        params: [1, 2]
      }));

      socket.send = function(message) {
        expect(JSON.parse(message)).toEqual({
          id: 10,
          error: null,
          result: 3
        });
        done();
      };
    });

    it('should wait for promises with errors', function(done) {
      start();
      var socket = new EventEmitter();
      server.emit('connection', socket);

      butler.register('foo', function(a, b) {
        return Q.reject(new Error('bam'));
      });

      socket.emit('message', JSON.stringify({
        id: 10,
        method: 'foo',
        params: [1, 2]
      }));

      socket.send = function(message) {
        expect(JSON.parse(message)).toEqual({
          id: 10,
          error: {
            code: 0,
            message: 'bam'
          },
          result: null
        });
        done();
      };
    });
  });
});
