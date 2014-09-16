var _ = require('underscore');

var Bus = require('../bus');

describe('Bus', function() {
  var bus, calls;

  function one() {
    calls.push(['one'].concat(_.toArray(arguments)));
    return 'one';
  }

  function two() {
    calls.push(['two'].concat(_.toArray(arguments)));
    return 'two';
  }

  beforeEach(function() {
    bus = _.clone(Bus);
    calls = [];
  });

  describe('.on([name], fn)', function() {
    it('should add listeners', function() {
      bus.on('foo', one);
      bus.on('foo', two);

      bus.emit('foo', 1);
      bus.emit('bar', 1);
      bus.emit('foo', 2);

      expect(calls).toEqual([['one', 1], ['two', 1], ['one', 2], ['two', 2]]);
    });

    it('should add listeners for all events', function() {
      bus.on(one);

      bus.emit('foo', 1);
      bus.emit('bar', 2);

      expect(calls).toEqual([['one', 1], ['one', 2]]);
    });
  });

  describe('.off([name], fn)', function() {
    it('should remove listeners', function() {
      bus.on('foo', one);
      bus.on('foo', two);
      bus.off('foo', two);

      bus.emit('foo');

      expect(calls).toEqual([['one']]);
    });

    it('should remove listeners for all events', function() {
      bus.on(one);
      bus.on(two);
      bus.off(two);

      bus.emit('foo');

      expect(calls).toEqual([['one']]);
    });

    it('should work when called from an event', function() {
      bus.on('foo', function() {
        bus.off('foo.bar', one);
      });
      bus.on('foo.bar', one);
      bus.emit('foo.bar');
      expect(calls).toEqual([['one']]);
      bus.emit('foo.bar');
      expect(calls).toEqual([['one']]);
    });
  });

  describe('.emit(name, *args)', function() {
    it('should fire all listeners', function() {
      bus.on(one);
      bus.on('foo', two);
      bus.on('foo.bar', one);
      bus.on('foo.baz', two);

      bus.emit('foo.bar', 1);

      expect(calls).toEqual([['one', 1], ['two', 1], ['one', 1]]);
    });

    it('should set the listener context', function() {
      bus.on('foo', function() {
        expect(this.event).toBe('foo.bar');
      });

      bus.emit('foo.bar');
    });
  });

  describe('.register([name], fn)', function() {
    it('should set a delegate', function() {
      bus.register('foo', one);
      bus.register('foo', two);

      var result = bus.call('foo', 1);
      expect(result).toEqual('two');
      expect(calls).toEqual([['two', 1]]);
    });

    it('should set a delegate for all methods', function() {
      bus.register(one);

      var results = [bus.call('foo', 1), bus.call('bar', 2)];
      expect(results).toEqual(['one', 'one']);
      expect(calls).toEqual([['one', 1], ['one', 2]]);
    });
  });

  describe('.unregister([name], fn)', function() {
    it('should remove a delegate', function() {
      bus.register('foo', one);
      bus.unregister('foo');

      expect(function() {
        bus.call('foo');
      }).toThrow(new Error('no delegate for method "foo"'));
    });

    it('should remove a delegate for all methods', function() {
      bus.register(one);
      bus.unregister();

      expect(function() {
        bus.call('foo');
      }).toThrow(new Error('no delegate for method "foo"'));
    });
  });

  describe('.call(name, *args)', function() {
    it('should fire the first delegate', function() {
      var results = [];

      bus.register('foo.bar', one);
      bus.register('foo.baz', two);
      results.push(bus.call('foo.bar', 1));
      bus.register('foo', two);
      results.push(bus.call('foo.bar', 2));
      bus.register(one);
      results.push(bus.call('foo.bar', 3));

      expect(results).toEqual(['one', 'two', 'one']);
      expect(calls).toEqual([['one', 1], ['two', 2], ['one', 3]]);
    });

    it('should throw an Error if no delegate is found', function() {
      expect(function() {
        bus.call('foo');
      }).toThrow(new Error('no delegate for method "foo"'));
    });

    it('should set the listener context', function() {
      bus.register('foo', function() {
        expect(this.method).toBe('foo.bar');
      });

      bus.call('foo.bar');
    });
  });
});
