var _ = require('underscore');

var Butler = require('../butler');

describe('Butler', function() {
  var butler;
  var spy;

  function makeCall(name, prefix, suffix, args) {
    return {
      object: {
        name: name,
        prefix: prefix,
        suffix: suffix
      },
      args: args
    };
  }

  beforeEach(function() {
    butler = new Butler();
    spy = jasmine.createSpy('spy').and.callFake(_.identity);
  });

  it('.on(name, fn)', function() {
    it('should add listeners', function() {
      butler.on('foo', spy);
      butler.on('foo', spy);

      butler.emit('foo', 1);
      butler.emit('bar', 2);
      butler.emit('foo', 3);

      var context = {
        name: 'foo',
        prefix: 'foo',
        suffix: ''
      };
      expect(spy.calls.all()).toEqual([
        makeCall('foo', 'foo', '', [1]),
        makeCall('foo', 'foo', '', [1]),
        makeCall('foo', 'foo', '', [3]),
        makeCall('foo', 'foo', '', [3])
      ]);
    });
  });

  describe('.off(name, fn)', function() {
    it('should remove listeners', function() {
      butler.on('foo', spy);
      butler.on('foo', spy);
      butler.off('foo', spy);

      butler.emit('foo');

      var context = {
        name: 'foo',
        prefix: 'foo',
        suffix: ''
      };
      expect(spy.calls.all()).toEqual([
        makeCall('foo', 'foo', '', [])
      ]);
    });

    it('should work when called from an event', function() {
      butler.on('foo.bar', function() {
        butler.off('foo', spy);
      });
      butler.on('foo', spy);

      butler.emit('foo.bar');
      butler.emit('foo.bar');

      expect(spy.calls.all()).toEqual([
        makeCall('foo.bar', 'foo', 'bar', [])
      ]);
    });
  });

  describe('.emit(name, args...)', function() {
    it('should fire all listeners', function() {
      butler.on('', spy);
      butler.on('foo', spy);
      butler.on('foo.bar', spy);
      butler.on('foo.baz', spy);

      butler.emit('foo.bar', 1, 2);

      expect(spy.calls.all()).toEqual([
        makeCall('foo.bar', 'foo.bar', '', [1, 2]),
        makeCall('foo.bar', 'foo', 'bar', [1, 2]),
        makeCall('foo.bar', '', 'foo.bar', [1, 2])
      ]);
    });
  });

  describe('.broadcast(name, args)', function() {
    it('should fire all listeners', function() {
      butler.on('', spy);
      butler.on('foo', spy);
      butler.on('foo.bar', spy);
      butler.on('foo.baz', spy);

      butler.broadcast('foo.bar', [1, 2]);

      expect(spy.calls.all()).toEqual([
        makeCall('foo.bar', 'foo.bar', '', [1, 2]),
        makeCall('foo.bar', 'foo', 'bar', [1, 2]),
        makeCall('foo.bar', '', 'foo.bar', [1, 2])
      ]);
    });
  });

  describe('.register(name, fn)', function() {
    it('should set a delegate', function() {
      butler.register('foo', spy);
      butler.register('foo', spy);

      var result = butler.call('foo', 1);

      expect(result).toEqual(1);
      expect(spy.calls.all()).toEqual([
        makeCall('foo', 'foo', '', [1])
      ]);
    });
  });

  describe('.unregister(name, fn)', function() {
    it('should remove a delegate', function() {
      butler.register('foo', spy);
      butler.unregister('foo');

      var result = butler.call('foo');

      expect(result).toBeUndefined();
      expect(spy.calls.all()).toEqual([]);
    });
  });

  describe('.call(name, args...)', function() {
    it('should fire the last delegate', function() {
      butler.register(spy);
      butler.register('foo', spy);
      butler.register('foo.bar', spy);
      butler.register('foo.baz', spy);

      var results = [butler.call('foo', 1), butler.call('foo.bar.baz', 2)];

      expect(results).toEqual([1, 2]);
      expect(spy.calls.all()).toEqual([
       makeCall('foo', 'foo', '', [1]),
       makeCall('foo.bar.baz', 'foo.bar', 'baz', [2])
      ]);
    });
  });

  describe('.apply(name, args)', function() {
    it('should fire the last delegate', function() {
      butler.register(spy);
      butler.register('foo', spy);
      butler.register('foo.bar', spy);
      butler.register('foo.baz', spy);

      var results = [butler.apply('foo', [1]), butler.apply('foo.bar.baz', [2])];

      expect(results).toEqual([1, 2]);
      expect(spy.calls.all()).toEqual([
       makeCall('foo', 'foo', '', [1]),
       makeCall('foo.bar.baz', 'foo.bar', 'baz', [2])
      ]);
    });
  });

  describe('.reset()', function() {
    it('should remove all handlers', function() {
      butler.on('foo', spy);
      butler.on('foo', spy);
      butler.on('bar', spy);
      butler.reset();

      butler.emit('foo');
      butler.emit('bar');

      expect(spy.calls.all()).toEqual([]);
    });

    it('should remove all delegates', function() {
      butler.register('foo', spy);
      butler.register('foo', spy);
      butler.register('bar', spy);
      butler.reset();

      butler.call('foo');
      butler.call('bar');

      expect(spy.calls.all()).toEqual([]);
    });
  })
});
