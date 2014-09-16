var EventEmitter = require('events').EventEmitter;
var proxyquire = require('proxyquire');
var Q = require('q');
var _ = require('underscore');

describe('server', function() {
  var butler, httpServer, server, socket, http, service, callbacks;

  beforeEach(function() {
    butler = _.clone(require('../bus'));

    httpServer = {
      listen: _.noop
    };

    server = new EventEmitter;
    socket = new EventEmitter;

    http = {
      createServer: _.constant(httpServer)
    };

    function io(srv, opts) {
      expect(srv).toBe(httpServer);
      expect(opts).toEqual({ serveClient: false });
      return server;
    };

    service = proxyquire('../services/server', {
      '../butler': butler,
      'http': http,
      'socket.io': io
    });

    callbacks = { f: null };
    spyOn(callbacks, 'f');

    // for Q
    spyOn(require('process'), 'nextTick').andCallFake(function(fn) { fn(); });
  });

  it('should have the name "server"', function() {
    expect(service.name).toBe('server');
  });

  it('should start an HTTP server', function() {
    spyOn(httpServer, 'listen');

    service.start({
      hostname: 'www.example.com',
      port: 9876
    });

    expect(httpServer.listen).toHaveBeenCalledWith(9876, 'www.example.com');
  });

  it('should send events', function() {
    server.on('event', callbacks.f);

    service.start();
    server.emit('connection', socket);
    butler.emit('foo', 1, 2)

    expect(callbacks.f).toHaveBeenCalledWith({
      name: 'foo',
      params: [1, 2]
    });
  });

  it('should respond to requests', function() {
    service.start();
    server.emit('connection', socket);
    socket.on('response', callbacks.f);

    butler.register('foo', function() {
      return 'bar';
    });

    socket.emit('request', {
      method: 'foo',
      params: [1, 2],
      id: 10
    });

    expect(callbacks.f).toHaveBeenCalledWith({
      result: 'bar',
      error: null,
      id: 10
    });
  });

  it('should handle errors', function() {
    service.start();
    server.emit('connection', socket);
    socket.on('response', callbacks.f);

    butler.register('foo', function() {
      throw new Error('boom');
    });

    socket.emit('request', {
      method: 'foo',
      params: [1, 2],
      id: 10
    });

    expect(callbacks.f).toHaveBeenCalledWith({
      result: null,
      error: Error('boom'),
      id: 10
    });

    socket.emit('request', {
      method: 'bar',
      params: [1, 2],
      id: 10
    });

    expect(callbacks.f).toHaveBeenCalledWith({
      result: null,
      error: Error('no delegate for method "bar"'),
      id: 10
    });
  });

  it('should resolve promises', function() {
    service.start();
    server.emit('connection', socket);
    socket.on('response', callbacks.f);

    butler.register('foo', function() {
      return Q('bar');
    });

    socket.emit('request', {
      method: 'foo',
      params: [1, 2],
      id: 10
    });

    expect(callbacks.f).toHaveBeenCalledWith({
      result: 'bar',
      error: null,
      id: 10
    });

    butler.register('foo', function() {
      return Q.reject(new Error('boom'));
    });

    socket.emit('request', {
      method: 'foo',
      params: [1, 2],
      id: 10
    });

    expect(callbacks.f).toHaveBeenCalledWith({
      result: null,
      error: Error('boom'),
      id: 10
    });
  });
});
