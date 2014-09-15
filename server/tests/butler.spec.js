var _ = require('underscore');

var Butler = require('../butler').Butler;

describe('Butler', function() {
  var butler, calls;

  function one() {
    calls.push(['one'].concat(_.toArray(arguments)));
    return 'one';
  }

  function two() {
    calls.push(['two'].concat(_.toArray(arguments)));
    return 'two';
  }

  beforeEach(function() {
    butler = _.clone(Butler);
    calls = [];
  });

  describe('.on([name], fn)', function() {
    it('should add listeners', function() {
      butler.on('foo', one);
      butler.on('foo', two);

      butler.emit('foo', 1);
      butler.emit('bar', 1);
      butler.emit('foo', 2);

      expect(calls).toEqual([['one', 1], ['two', 1], ['one', 2], ['two', 2]]);
    });

    it('should add listeners for all events', function() {
      butler.on(one);

      butler.emit('foo', 1);
      butler.emit('bar', 2);

      expect(calls).toEqual([['one', 1], ['one', 2]]);
    });
  });

  describe('.off([name], fn)', function() {
    it('should remove listeners', function() {
      butler.on('foo', one);
      butler.on('foo', two);
      butler.off('foo', two);

      butler.emit('foo');

      expect(calls).toEqual([['one']]);
    });

    it('should remove listeners for all events', function() {
      butler.on(one);
      butler.on(two);
      butler.off(two);

      butler.emit('foo');

      expect(calls).toEqual([['one']]);
    });

    it('should work when called from an event', function() {
      butler.on('foo', function() {
        butler.off('foo.bar', one);
      });
      butler.on('foo.bar', one);
      butler.emit('foo.bar');
      expect(calls).toEqual([['one']]);
      butler.emit('foo.bar');
      expect(calls).toEqual([['one']]);
    });
  });

  describe('.emit(name, *args)', function() {
    it('should fire all listeners', function() {
      butler.on(one);
      butler.on('foo', two);
      butler.on('foo.bar', one);
      butler.on('foo.baz', two);

      butler.emit('foo.bar', 1);

      expect(calls).toEqual([['one', 1], ['two', 1], ['one', 1]]);
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
      expect(calls).toEqual([['two', 1]]);
    });

    it('should set a delegate for all methods', function() {
      butler.register(one);

      var results = [butler.call('foo', 1), butler.call('bar', 2)];
      expect(results).toEqual(['one', 'one']);
      expect(calls).toEqual([['one', 1], ['one', 2]]);
    });
  });

  describe('.unregister([name], fn)', function() {
    it('should remove a delegate', function() {
      butler.register('foo', one);
      butler.unregister('foo');

      expect(function() {
        butler.call('foo');
      }).toThrow(new Error('no delegate for method "foo"'));
    });

    it('should remove a delegate for all methods', function() {
      butler.register(one);
      butler.unregister();

      expect(function() {
        butler.call('foo');
      }).toThrow(new Error('no delegate for method "foo"'));
    });
  });

  describe('.call(name, *args)', function() {
    it('should fire the first delegate', function() {
      var results = [];

      butler.register('foo.bar', one);
      butler.register('foo.baz', two);
      results.push(butler.call('foo.bar', 1));
      butler.register('foo', two);
      results.push(butler.call('foo.bar', 2));
      butler.register(one);
      results.push(butler.call('foo.bar', 3));

      expect(results).toEqual(['one', 'two', 'one']);
      expect(calls).toEqual([['one', 1], ['two', 2], ['one', 3]]);
    });

    it('should throw an Error if no delegate is found', function() {
      expect(function() {
        butler.call('foo');
      }).toThrow(new Error('no delegate for method "foo"'));
    });

    it('should set the listener context', function() {
      butler.register('foo', function() {
        expect(this.method).toBe('foo.bar');
      });

      butler.call('foo.bar');
    });
  });

});
