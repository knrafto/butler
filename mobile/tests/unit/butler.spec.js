describe('butler', function() {
  var $window, $rootScope, butler, socket;

  function callback(name) {
    return jasmine.createSpy(name).and.returnValue(name);
  }

  var one = callback('one');
  var two = callback('two');
  var three = callback('three');
  var four = callback('four');

  beforeEach(module('server', function($provide) {
    socket = {
      on: function(name, fn) {
        this._events || (this._events = {});
        var events = this._events[name] || (this._events[name] = []);
        events.push(fn);
        return this;
      },

      emit: jasmine.createSpy('emit'),

      receive: function(name, data) {
        if (!this._events) return;
        _.each(this._events[name], function(fn) {
          fn(data);
        });
      },

      receiveEvent: function(name) {
        var params = _.toArray(arguments).slice(1);
        this.receive('event', {
          event: name,
          params: params
        });
      },

      receiveResponse: function(requestId, err, result) {
        this.receive('response', {
          result: result,
          error: err,
          id: requestId
        });
      }
    };

    $provide.value('socket', socket);
  }));

  beforeEach(inject(function(_$window_, _$rootScope_, _butler_) {
    $window = _$window_;
    $rootScope = _$rootScope_;
    butler = _butler_;
  }));

  afterEach(function() {
    _.each([one, two, three, four], function(spy) {
      spy.calls.reset();
    });
  });

  describe('.on([name], fn)', function() {
    it('should add listeners', function() {
      butler.on('foo', one);
      butler.on('foo', two);

      socket.receiveEvent('foo', 1);
      expect(one).toHaveBeenCalledWith(1);
      expect(two).toHaveBeenCalledWith(1);

      socket.receiveEvent('bar', 1);
      socket.receiveEvent('foo', 2);
      expect(one).toHaveBeenCalledWith(2);
      expect(two).toHaveBeenCalledWith(2);
    });

    it('should add listeners for all events', function() {
      butler.on(one);

      socket.receiveEvent('foo', 1);
      expect(one).toHaveBeenCalledWith(1);
      socket.receiveEvent('bar', 2);
      expect(one).toHaveBeenCalledWith(2);
    });

    it('should fire all listeners', function() {
      butler.on(one);
      butler.on('foo', two);
      butler.on('foo.bar', three);
      butler.on('foo.baz', four);

      socket.receiveEvent('foo.bar', 1);
      expect(one).toHaveBeenCalledWith(1);
      expect(two).toHaveBeenCalledWith(1);
      expect(three).toHaveBeenCalledWith(1);
      expect(four).not.toHaveBeenCalled();
    });

    it('should set the listener context', function() {
      butler.on('foo', function() {
        expect(this.event).toBe('foo.bar');
      });

      socket.receiveEvent('foo.bar');
    });
  });

  describe('.off([name], fn)', function() {
    it('should remove listeners', function() {
      butler.on('foo', one);
      butler.on('foo', two);
      butler.off('foo', two);

      socket.receiveEvent('foo');
      expect(one).toHaveBeenCalledWith();
      expect(two).not.toHaveBeenCalled();
    });

    it('should remove listeners for all events', function() {
      butler.on(one);
      butler.on(two);
      butler.off(two);

      socket.receiveEvent('foo');
      expect(one).toHaveBeenCalledWith();
      expect(two).not.toHaveBeenCalled();
    });

    it('should work when called from an event', function() {
      butler.on('foo', function() {
        butler.off('foo.bar', one);
      });
      butler.on('foo.bar', one);

      socket.receiveEvent('foo.bar');
      expect(one).toHaveBeenCalledWith();
      one.calls.reset();
      socket.receiveEvent('foo.bar');
      expect(one).not.toHaveBeenCalled();
    });
  });

  describe('.call(event, *args)', function() {
    it('should send numbered requests', function() {
      butler.call('foo', 1, 2);
      expect(socket.emit).toHaveBeenCalledWith('request', {
        id: 0,
        method: 'foo',
        params: [1, 2]
      });

      butler.call('bar');
      expect(socket.emit).toHaveBeenCalledWith('request', {
        id: 1,
        method: 'bar',
        params: []
      });
    });

    it('should respond to requests', function() {
      butler.call('foo').then(one, two);
      butler.call('bar').then(one, two);
      butler.call('baz').then(one, two);

      socket.receiveResponse(10, null, 'garply');
      socket.receiveResponse(1, null, 'waldo');
      socket.receiveResponse(2, null, 'fred');
      socket.receiveResponse(0, null, 'plugh');
      $rootScope.$apply();

      expect(one.calls.all()).toEqual([
        { object: $window, args: ['waldo'] },
        { object: $window, args: ['fred'] },
        { object: $window, args: ['plugh'] }
      ]);
      expect(two).not.toHaveBeenCalled();
    });

    it('should reject requests on error', function() {
      butler.call('foo').then(one, two);
      butler.call('bar').then(one, two);

      socket.receiveResponse(1, new Error('boom'), null);
      socket.receiveResponse(0, new Error('bam'), null);
      $rootScope.$apply();

      expect(one).not.toHaveBeenCalled();
      expect(two.calls.all()).toEqual([
        { object: $window, args: [new Error('boom')] },
        { object: $window, args: [new Error('bam')] }
      ]);
    });
  });
});
