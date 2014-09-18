describe('server', function() {
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

    butler.reset();
  });

  it('should fire listeners', function() {
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

  it('should apply scope after emitting', function() {
    spyOn($rootScope, '$apply');
    socket.receiveEvent('foo.bar', 1);
    expect($rootScope.$apply).toHaveBeenCalled();
  });

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

    expect(one).not.toHaveBeenCalled();
    expect(two.calls.all()).toEqual([
      { object: $window, args: [new Error('boom')] },
      { object: $window, args: [new Error('bam')] }
    ]);
  });
});
