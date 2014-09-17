var EventEmitter = require('events').EventEmitter;
var proxyquire = require('proxyquire');
var Q = require('q');
var _ = require('underscore');

var butler = require('../butler')

describe('server', function() {
  var server, socket, service;

  beforeEach(function() {
    server = new EventEmitter;
    socket = new EventEmitter;
    service = proxyquire('../services/socket.io', {
      'socket.io': _.constant(server)
    });
    butler.register('server', _.noop);
  });

  afterEach(function() {
    butler.reset();
  });

  it('should be depend on "server"', function() {
    expect(service.depends).toEqual(['server']);
  });

  it('should send events', function(done) {
    service.start();
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
    service.start();
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
    service.start();
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
    service.start();
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
    service.start();
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
    service.start();
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
