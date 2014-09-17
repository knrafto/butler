var _ = require('underscore');

var butler = require('../butler');

describe('butler', function() {
  function callback(name) {
    return jasmine.createSpy(name).and.returnValue(name);
  }

  var one = callback('one');
  var two = callback('two');
  var three = callback('three');
  var four = callback('four');

  var noFoo = new Error('no delegate for method "foo"');

  afterEach(function() {
    butler.reset();

    _.each([one, two, three, four], function(spy) {
      spy.calls.reset();
    });
  });

  describe('.on([name], fn)', function() {
    it('should add listeners', function() {
      butler.on('foo', one);
      butler.on('foo', two);

      butler.emit('foo', 1);
      expect(one).toHaveBeenCalledWith(1);
      expect(two).toHaveBeenCalledWith(1);

      butler.emit('bar', 1);
      butler.emit('foo', 2);
      expect(one).toHaveBeenCalledWith(2);
      expect(two).toHaveBeenCalledWith(2);
    });

    it('should add listeners for all events', function() {
      butler.on(one);

      butler.emit('foo', 1);
      expect(one).toHaveBeenCalledWith(1);
      butler.emit('bar', 2);
      expect(one).toHaveBeenCalledWith(2);
    });
  });

  describe('.off([name], fn)', function() {
    it('should remove listeners', function() {
      butler.on('foo', one);
      butler.on('foo', two);
      butler.off('foo', two);

      butler.emit('foo');
      expect(one).toHaveBeenCalledWith();
      expect(two).not.toHaveBeenCalled();
    });

    it('should remove listeners for all events', function() {
      butler.on(one);
      butler.on(two);
      butler.off(two);

      butler.emit('foo');
      expect(one).toHaveBeenCalledWith();
      expect(two).not.toHaveBeenCalled();
    });

    it('should work when called from an event', function() {
      butler.on('foo', function() {
        butler.off('foo.bar', one);
      });
      butler.on('foo.bar', one);

      butler.emit('foo.bar');
      expect(one).toHaveBeenCalledWith();
      one.calls.reset();
      butler.emit('foo.bar');
      expect(one).not.toHaveBeenCalled();
    });
  });

  describe('.emit(name, *args)', function() {
    it('should fire all listeners', function() {
      butler.on(one);
      butler.on('foo', two);
      butler.on('foo.bar', three);
      butler.on('foo.baz', four);

      butler.emit('foo.bar', 1);
      expect(one).toHaveBeenCalledWith(1);
      expect(two).toHaveBeenCalledWith(1);
      expect(three).toHaveBeenCalledWith(1);
      expect(four).not.toHaveBeenCalled();
    });

    it('should set the listener context', function() {
      butler.on('foo', function() {
        expect(this.event).toBe('foo.bar');
      });

      butler.emit('foo.bar');
    });
  });

  describe('.register([name], fn)', function() {
    it('should set a delegate', function() {
      butler.register('foo', one);
      butler.register('foo', two);

      var result = butler.call('foo', 1);
      expect(result).toEqual('two');
      expect(one).not.toHaveBeenCalled();
      expect(two).toHaveBeenCalledWith(1);
    });

    it('should set a delegate for all methods', function() {
      butler.register(one);

      var results = [butler.call('foo', 1), butler.call('bar', 2)];
      expect(results).toEqual(['one', 'one']);
    });
  });

  describe('.unregister([name], fn)', function() {
    it('should remove a delegate', function() {
      butler.register('foo', one);
      butler.unregister('foo');

      expect(function() {
        butler.call('foo');
      }).toThrow(noFoo);
    });

    it('should remove a delegate for all methods', function() {
      butler.register(one);
      butler.unregister();

      expect(function() {
        butler.call('foo');
      }).toThrow(noFoo);
    });
  });

  describe('.call(name, *args)', function() {
    it('should fire the last delegate', function() {
      butler.register(one);
      butler.register('foo', two);
      butler.register('foo.bar', three);
      butler.register('foo.baz', four);
      var results = [butler.call('foo', 1), butler.call('foo.bar.baz', 2)];

      expect(results).toEqual(['two', 'three']);
      expect(one).not.toHaveBeenCalled();
      expect(two).toHaveBeenCalledWith(1);
      expect(three).toHaveBeenCalledWith(2);
      expect(four).not.toHaveBeenCalled();
    });

    it('should throw an Error if no delegate is found', function() {
      expect(function() {
        butler.call('foo');
      }).toThrow(noFoo);
    });

    it('should set the listener context', function() {
      butler.register('foo', function() {
        expect(this.method).toBe('foo.bar');
      });

      butler.call('foo.bar');
    });
  });

  describe('.reset()', function() {
    it('should remove all listeners', function() {
      butler.on(one);
      butler.on('foo', two);
      butler.reset();
      butler.emit('foo');
      expect(one).not.toHaveBeenCalled();
      expect(two).not.toHaveBeenCalled();
    });

    it('should remove all delegates', function() {
      butler.register(one);
      butler.register('foo', two);
      butler.reset();
      expect(function() {
        butler.call('foo');
      }).toThrow(noFoo);
    });
  });
});
