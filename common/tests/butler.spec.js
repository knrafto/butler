var _ = require('underscore');

var Butler = require('../butler');

/* An Agency is where spies are created. */
function Agency() {
  this.spies = {};
  this.calls = [];
}

Agency.prototype.spy = function(name) {
  var spy = this.spies[name];
  if (!spy) {
    self = this;
    spy = this.spies[name] = function() {
      self.calls.push({
        spy: name,
        object: this,
        args: _.toArray(arguments)
      });
      return name;
    };
  }
  return spy;
};

function makeCall(spy, name, prefix, suffix, args) {
  return {
    spy: spy,
    object: {
      name: name,
      prefix: prefix,
      suffix: suffix
    },
    args: args
  };
}

describe('Butler', function() {
  var butler;
  var agency;

  beforeEach(function() {
    butler = new Butler();
    agency = new Agency();
  });

  it('.on(name, fn)', function() {
    it('should add listeners', function() {
      butler.on('foo', agency.spy('one'));
      butler.on('foo', agency.spy('two'));

      butler.emit('foo', 1);
      butler.emit('bar', 2);
      butler.emit('foo', 3);

      expect(agency.calls).toEqual([
        makeCall('one', 'foo', 'foo', '', [1]),
        makeCall('two', 'foo', 'foo', '', [1]),
        makeCall('one', 'foo', 'foo', '', [3]),
        makeCall('two', 'foo', 'foo', '', [3])
      ]);
    });
  });

  describe('.off(name, fn)', function() {
    it('should remove listeners', function() {
      butler.on('foo', agency.spy('one'));
      butler.on('foo', agency.spy('two'));
      butler.on('foo', agency.spy('three'));
      butler.off('foo', agency.spy('two'));

      butler.emit('foo');

      expect(agency.calls).toEqual([
        makeCall('one', 'foo', 'foo', '', []),
        makeCall('three', 'foo', 'foo', '', [])
      ]);
    });

    it('should work when called from an event', function() {
      butler.on('foo.bar', function() {
        butler.off('foo.bar', agency.spy('one'));
        butler.off('foo', agency.spy('two'));
      });
      butler.on('foo.bar', agency.spy('one'));
      butler.on('foo', agency.spy('two'));

      butler.emit('foo.bar');
      butler.emit('foo.bar');

      expect(agency.calls).toEqual([
        makeCall('one', 'foo.bar', 'foo.bar', '', []),
        makeCall('two', 'foo.bar', 'foo', 'bar', [])
      ]);
    });
  });

  describe('.emit(name, args...)', function() {
    it('should fire all listeners in order', function() {
      butler.on('', agency.spy('one'));
      butler.on('foo', agency.spy('two'));
      butler.on('foo.bar', agency.spy('three'));
      butler.on('foo.baz', agency.spy('four'));

      butler.emit('foo.bar', 1, 2);

      expect(agency.calls).toEqual([
        makeCall('three', 'foo.bar', 'foo.bar', '', [1, 2]),
        makeCall('two', 'foo.bar', 'foo', 'bar', [1, 2]),
        makeCall('one', 'foo.bar', '', 'foo.bar', [1, 2])
      ]);
    });
  });

  describe('.broadcast(name, args)', function() {
    it('should fire all listeners in order', function() {
      butler.on('', agency.spy('one'));
      butler.on('foo', agency.spy('two'));
      butler.on('foo.bar', agency.spy('three'));
      butler.on('foo.baz', agency.spy('four'));

      butler.broadcast('foo.bar', [1, 2]);

      expect(agency.calls).toEqual([
        makeCall('three', 'foo.bar', 'foo.bar', '', [1, 2]),
        makeCall('two', 'foo.bar', 'foo', 'bar', [1, 2]),
        makeCall('one', 'foo.bar', '', 'foo.bar', [1, 2])
      ]);
    });
  });

  describe('.register(name, fn)', function() {
    it('should set a delegate', function() {
      butler.register('foo', agency.spy('one'));
      butler.register('foo', agency.spy('two'));

      var result = butler.call('foo', 1);

      expect(result).toEqual('two');
      expect(agency.calls).toEqual([
        makeCall('two', 'foo', 'foo', '', [1])
      ]);
    });
  });

  describe('.unregister(name, fn)', function() {
    it('should remove a delegate', function() {
      butler.register('foo', agency.spy('one'));
      butler.register('foo', agency.spy('two'));
      butler.unregister('foo');

      var result = butler.call('foo');

      expect(result).toBeUndefined();
      expect(agency.calls).toEqual([]);
    });
  });

  describe('.call(name, args...)', function() {
    it('should fire the last delegate', function() {
      butler.register('', agency.spy('one'));
      butler.register('foo', agency.spy('two'));
      butler.register('foo.bar', agency.spy('three'));
      butler.register('foo.baz', agency.spy('four'));

      var results = [
        butler.call('baz', 1),
        butler.call('foo', 2),
        butler.call('foo.bar.baz', 3)
      ];

      expect(results).toEqual(['one', 'two', 'three']);
      expect(agency.calls).toEqual([
        makeCall('one', 'baz', '', 'baz', [1]),
        makeCall('two', 'foo', 'foo', '', [2]),
        makeCall('three', 'foo.bar.baz', 'foo.bar', 'baz', [3])
      ]);
    });
  });

  describe('.apply(name, args)', function() {
    it('should fire the last delegate', function() {
      butler.register('', agency.spy('one'));
      butler.register('foo', agency.spy('two'));
      butler.register('foo.bar', agency.spy('three'));
      butler.register('foo.baz', agency.spy('four'));

      var results = [
        butler.apply('baz', [1]),
        butler.apply('foo', [2]),
        butler.apply('foo.bar.baz', [3])
      ];

      expect(results).toEqual(['one', 'two', 'three']);
      expect(agency.calls).toEqual([
        makeCall('one', 'baz', '', 'baz', [1]),
        makeCall('two', 'foo', 'foo', '', [2]),
        makeCall('three', 'foo.bar.baz', 'foo.bar', 'baz', [3])
      ]);
    });
  });

  describe('.reset()', function() {
    it('should remove all handlers', function() {
      butler.on('foo', agency.spy('one'));
      butler.on('foo', agency.spy('two'));
      butler.on('bar', agency.spy('three'));
      butler.reset();

      butler.emit('foo');
      butler.emit('bar');

      expect(agency.calls).toEqual([]);
    });

    it('should remove all delegates', function() {
      butler.register('foo', agency.spy('one'));
      butler.register('foo', agency.spy('two'));
      butler.register('bar', agency.spy('three'));
      butler.reset();

      var results = [butler.call('foo'), butler.call('bar')];

      expect(results).toEqual([undefined, undefined]);
      expect(agency.calls).toEqual([]);
    });
  })
});
