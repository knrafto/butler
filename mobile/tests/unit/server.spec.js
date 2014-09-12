describe('EventEmitter', function() {
  var EventEmitter, emitter, calls;

  function one() {
    calls.push('one');
    angular.forEach(arguments, function(value) {
      calls.push(value);
    });
  }

  function two() {
    calls.push('two');
    angular.forEach(arguments, function(value) {
      calls.push(value);
    });
  }

  beforeEach(module('server'));

  beforeEach(inject(function(_EventEmitter_) {
    EventEmitter = _EventEmitter_;
    emitter = new EventEmitter;
    calls = [];
  }));

  describe('.on(event, fn)', function() {
    it('should add listeners', function() {
      emitter.on('foo', one);
      emitter.on('foo', two);

      emitter.emit('foo', 1);
      emitter.emit('bar', 1);
      emitter.emit('foo', 2);

      expect(calls).toEqual(['one', 1, 'two', 1, 'one', 2, 'two', 2]);
    });
  });

  describe('.off(event, fn)', function() {
    it('should remove a listener', function() {
      emitter.on('foo', one);
      emitter.on('foo', two);
      emitter.off('foo', two);

      emitter.emit('foo');

      expect(calls).toEqual(['one']);
    });

    it('should work when called from an event', function() {
      emitter.on('foo', function() {
        emitter.off('foo', one);
      });
      emitter.on('foo', one);
      emitter.emit('foo');
      expect(calls).toEqual(['one']);
      emitter.emit('foo');
      expect(calls).toEqual(['one']);
    });
  });

  describe('.listeners(event)', function() {
    describe('when handlers are present', function() {
      it('should return an array of callbacks', function() {
        emitter.on('foo', one);
        expect(emitter.listeners('foo')).toEqual([one]);
      });
    });

    describe('when no handlers are present', function() {
      it('should return an empty array', function() {
        expect(emitter.listeners('foo')).toEqual([]);
      });
    });
  });

  describe('.hasListeners(event)', function() {
    describe('when handlers are present', function() {
      it('should return true', function() {
        emitter.on('foo', one);
        expect(emitter.hasListeners('foo')).toBe(true);
      });
    });

    describe('when no handlers are present', function() {
      it('should return false', function() {
        expect(emitter.hasListeners('foo')).toBe(false);
      });
    });
  });

  describe('(obj)', function() {
    it('should mixin', function() {
      var obj = {};
      EventEmitter(obj);
      obj.on('foo', one);
      obj.emit('foo');
      expect(calls).toEqual(['one']);
    });
  });
});

describe('server', function() {
  var server_url = 'http://example.com:80',
      $rootScope, EventEmitter, calls, server, socket;

  function one() {
    calls.push('one');
    angular.forEach(arguments, function(value) {
      calls.push(value);
    });
  }

  function two() {
    calls.push('two');
    angular.forEach(arguments, function(value) {
      calls.push(value);
    });
  }

  beforeEach(module('server'));

  beforeEach(inject(function(_EventEmitter_, _server_, $window, _$rootScope_) {
    EventEmitter = _EventEmitter_;
    calls = [];

    socket = {};
    EventEmitter(socket);
    socket.receive = socket.emit;
    socket.emit = null;
    spyOn(socket, 'emit');

    $window.io = function(url) {
      expect(url).toEqual(server_url);
      return socket;
    };

    $rootScope = _$rootScope_;
    server = _server_(server_url);
  }));

  it('should use EventEmitter mixin', function() {
    angular.forEach(EventEmitter.prototype, function(value, key) {
      expect(server[key]).toBeDefined();
    });
  });

  describe('.send(event, [args], [kwds])', function() {
    it('should emit an event on the socket', function () {
      server.send('foo', [1, 2], {x: 3});
      expect(socket.emit).toHaveBeenCalledWith('event', {
        name: 'foo',
        args: [1, 2],
        kwds: {x: 3}
      });
    });

    it('should always send arguments', function () {
      server.send('foo');
      expect(socket.emit).toHaveBeenCalledWith('event', {
        name: 'foo',
        args: [],
        kwds: {}
      });
    });
  });

  describe('.post(method, [args], [kwds]', function () {
    it('should send numbered requests', function() {
      server.post('foo', [1, 2], {x: 3});
      expect(socket.emit).toHaveBeenCalledWith('request', {
        id: 0,
        method: 'foo',
        args: [1, 2],
        kwds: {x: 3}
      });

      server.post('bar');
      expect(socket.emit).toHaveBeenCalledWith('request', {
        id: 1,
        method: 'bar',
        args: [],
        kwds: {}
      });
    });

    it('should respond to requests', function() {
      server.post('foo').then(one, two);
      server.post('bar').then(one, two);
      server.post('baz').then(one, two);

      socket.receive('response', {
        id: 10,
        result: 'garply'
      });
      socket.receive('response', {
        id: 1,
        result: 'waldo'
      });
      socket.receive('response', {
        id: 2,
        result: 'fred'
      });
      socket.receive('response', {
        id: 0,
        result: 'plugh'
      });
      $rootScope.$apply();

      expect(calls).toEqual(['one', 'waldo', 'one', 'fred', 'one', 'plugh']);
    });

    it('should reject requests on error', function() {
      server.post('foo').then(one, two);
      server.post('bar').then(one, two);

      socket.receive('error', 'SomeError', 'bam');
      $rootScope.$apply();

      expect(calls).toEqual([
        'two', 'SomeError: bam', 'two', 'SomeError: bam'
      ]);
    });
  });

  describe('.on(event, fn)', function() {
    it('should subscribe to the server', function() {
      server.on('foo', one);
      expect(socket.emit).toHaveBeenCalledWith('subscribe', {
        name: 'foo'
      });
    });

    it('should subscribe only once', function() {
      server.on('foo', one);
      server.off('foo', one);
      socket.emit.reset();
      server.on('foo', one);
      expect(socket.emit).not.toHaveBeenCalled();
    });

    it('should register handers', function() {
      server.on('foo', one);
      server.emit('foo');
      expect(calls).toEqual(['one']);
    });
  });
});
