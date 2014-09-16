var EventEmitter = require('events').EventEmitter;
var proxyquire = require('proxyquire');
var Q = require('q');
var _ = require('underscore');

describe('server', function() {
  var httpServer, server, socket, butler, http, io, service;

  beforeEach(function() {
    httpServer = { listen: jasmine.createSpy('listen') };

    server = new EventEmitter;
    socket = new EventEmitter;

    butler = _.clone(require('../bus'));

    http = {
      createServer: jasmine.createSpy('createServer').andReturn(httpServer)
    };

    io = jasmine.createSpy().andReturn(server);

    service = proxyquire('../services/server', {
      '../butler': butler,
      'http': http,
      'socket.io': io
    });

    // for Q
    spyOn(require('process'), 'nextTick').andCallFake(function(fn) { fn(); });
  });

  it('should be named "server"', function() {
    expect(service.name).toBe('server');
  });

  it('should start an HTTP server', function() {
    service.start({
      hostname: 'www.example.com',
      port: 9876
    });

    expect(http.createServer).toHaveBeenCalledWith();
    expect(httpServer.listen).toHaveBeenCalledWith(9876, 'www.example.com');
    expect(io).toHaveBeenCalledWith(httpServer, { serveClient: false });
  });

  it('should send events', function() {
    var one = jasmine.createSpy('one');

    server.on('event', one);

    service.start();
    server.emit('connect', socket);
    butler.emit('foo', 1, 2)

    expect(one).toHaveBeenCalledWith({
      name: 'foo',
      params: [1, 2]
    });
  });

  it('should respond to requests', function() {
    var one = jasmine.createSpy('one');

    service.start();
    server.emit('connect', socket);
    socket.on('response', one);

    butler.register('foo', function() {
      return 'bar';
    });

    socket.emit('request', {
      method: 'foo',
      params: [1, 2],
      id: 10
    });

    expect(one).toHaveBeenCalledWith({
      result: 'bar',
      error: null,
      id: 10
    });
  });

  it('should handle errors', function() {
    var one = jasmine.createSpy('one');

    service.start();
    server.emit('connect', socket);
    socket.on('response', one);

    butler.register('foo', function() {
      throw new Error('boom');
    });

    socket.emit('request', {
      method: 'foo',
      params: [1, 2],
      id: 10
    });

    expect(one).toHaveBeenCalledWith({
      result: null,
      error: Error('boom'),
      id: 10
    });

    socket.emit('request', {
      method: 'bar',
      params: [1, 2],
      id: 10
    });

    expect(one).toHaveBeenCalledWith({
      result: null,
      error: Error('no delegate for method "bar"'),
      id: 10
    });
  });

  it('should resolve promises', function() {
    var one = jasmine.createSpy('one');

    service.start();
    server.emit('connect', socket);
    socket.on('response', one);

    butler.register('foo', function() {
      return Q('bar');
    });

    socket.emit('request', {
      method: 'foo',
      params: [1, 2],
      id: 10
    });

    expect(one).toHaveBeenCalledWith({
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

    expect(one).toHaveBeenCalledWith({
      result: null,
      error: Error('boom'),
      id: 10
    });
  });
});
