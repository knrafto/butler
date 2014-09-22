var EventEmitter = require('events').EventEmitter;
var proxyquire = require('proxyquire');
var Q = require('q');
var _ = require('underscore');

var butler = require('../butler');

describe('server', function() {
  var httpServer, server, socket, start;

  beforeEach(function() {
    httpServer = new EventEmitter();
    httpServer.listen = jasmine.createSpy('listen');
    server = new EventEmitter();
    socket = new EventEmitter();
    start = proxyquire('../services/server', {
      'http': {
        Server: _.constant(httpServer)
      },
      'socket.io': _.constant(server)
    });
  });

  afterEach(function() {
    butler.reset();
  });

  it('should start and close an HTTP server', function() {
    var config = {
      hostname: 'localhost',
      port: 54010
    };
    start(config);
    expect(httpServer.listen).toHaveBeenCalledWith(54010, 'localhost');
  });

  it('should send events', function(done) {
    start();
    server.on('event', function(event) {
      expect(event).toEqual({
        event: 'foo',
        params: [1, 2]
      });
      done();
    });
    butler.emit('foo', 1, 2);
  });

  it('should respond to requests', function(done) {
    start();
    server.emit('connection', socket);

    butler.register('foo', function() {
      return 'bar';
    });

    socket.emit('request', {
      method: 'foo',
      params: [1, 2],
      id: 10
    });

    socket.on('response', function(response) {
      expect(response).toEqual({
        result: 'bar',
        error: null,
        id: 10
      });
      done();
    });
  });

  it('should handle general errors', function(done) {
    start();
    server.emit('connection', socket);

    butler.register('foo', function() {
      throw new Error('boom');
    });

    socket.emit('request', {
      method: 'foo',
      params: [1, 2],
      id: 10
    });

    socket.on('response', function(response) {
      expect(response).toEqual({
        result: null,
        error: Error('boom'),
        id: 10
      });
      done();
    });
  });

  it('should handle lookup errors', function(done) {
    start();
    server.emit('connection', socket);

    socket.emit('request', {
      method: 'bar',
      params: [1, 2],
      id: 10
    });

    socket.on('response', function(response) {
      expect(response).toEqual({
        result: null,
        error: Error('no delegate for method "bar"'),
        id: 10
      });
      done();
    });
  });

  it('should wait for promises', function(done) {
    start();
    server.emit('connection', socket);

    butler.register('foo', function() {
      return Q('bar');
    });

    socket.emit('request', {
      method: 'foo',
      params: [1, 2],
      id: 10
    });

    socket.on('response', function(response) {
      expect(response).toEqual({
        result: 'bar',
        error: null,
        id: 10
      });
      done();
    });
  });

  it('should wait for promises with errors', function(done) {
    start();
    server.emit('connection', socket);

    butler.register('foo', function() {
      return Q.reject(new Error('boom'));
    });

    socket.emit('request', {
      method: 'foo',
      params: [1, 2],
      id: 10
    });

    socket.on('response', function(response) {
      expect(response).toEqual({
        result: null,
        error: Error('boom'),
        id: 10
      });
      done();
    });
  });
});
