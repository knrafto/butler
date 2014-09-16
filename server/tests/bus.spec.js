var _ = require('underscore');

var Bus = require('../bus');

describe('Bus', function() {
  var bus;

  beforeEach(function() {
    bus = _.clone(Bus);
  });

  describe('.on([name], fn)', function() {
    it('should add listeners', function() {
      var one = jasmine.createSpy('one');
      var two = jasmine.createSpy('two');

      bus.on('foo', one);
      bus.on('foo', two);

      bus.emit('foo', 1);
      expect(one).toHaveBeenCalledWith(1);
      expect(two).toHaveBeenCalledWith(1);

      bus.emit('bar', 1);
      bus.emit('foo', 2);
      expect(one).toHaveBeenCalledWith(2);
      expect(two).toHaveBeenCalledWith(2);
    });

    it('should add listeners for all events', function() {
      var one = jasmine.createSpy('one');

      bus.on(one);

      bus.emit('foo', 1);
      expect(one).toHaveBeenCalledWith(1);
      bus.emit('bar', 2);
      expect(one).toHaveBeenCalledWith(2);
    });
  });

  describe('.off([name], fn)', function() {
    it('should remove listeners', function() {
      var one = jasmine.createSpy('one');
      var two = jasmine.createSpy('two');

      bus.on('foo', one);
      bus.on('foo', two);
      bus.off('foo', two);

      bus.emit('foo');
      expect(one).toHaveBeenCalledWith();
      expect(two).not.toHaveBeenCalled();
    });

    it('should remove listeners for all events', function() {
      var one = jasmine.createSpy('one');
      var two = jasmine.createSpy('two');

      bus.on(one);
      bus.on(two);
      bus.off(two);

      bus.emit('foo');
      expect(one).toHaveBeenCalledWith();
      expect(two).not.toHaveBeenCalled();
    });

    it('should work when called from an event', function() {
      var one = jasmine.createSpy('one');

      bus.on('foo', function() {
        bus.off('foo.bar', one);
      });
      bus.on('foo.bar', one);

      bus.emit('foo.bar');
      expect(one).toHaveBeenCalledWith();
      one.reset();
      bus.emit('foo.bar');
      expect(one).not.toHaveBeenCalled();
    });
  });

  describe('.emit(name, *args)', function() {
    it('should fire all listeners', function() {
      var one = jasmine.createSpy('one');
      var two = jasmine.createSpy('two');
      var three = jasmine.createSpy('three');
      var four = jasmine.createSpy('four');

      bus.on(one);
      bus.on('foo', two);
      bus.on('foo.bar', three);
      bus.on('foo.baz', four);

      bus.emit('foo.bar', 1);
      expect(one).toHaveBeenCalledWith(1);
      expect(two).toHaveBeenCalledWith(1);
      expect(three).toHaveBeenCalledWith(1);
      expect(four).not.toHaveBeenCalled();
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
      var one = jasmine.createSpy('one').andReturn('one');
      var two = jasmine.createSpy('two').andReturn('two');

      bus.register('foo', one);
      bus.register('foo', two);

      var result = bus.call('foo', 1);
      expect(result).toEqual('two');
      expect(one).not.toHaveBeenCalled();
      expect(two).toHaveBeenCalledWith(1);
    });

    it('should set a delegate for all methods', function() {
      bus.register(function() { return 'one'; });

      var results = [bus.call('foo', 1), bus.call('bar', 2)];
      expect(results).toEqual(['one', 'one']);
    });
  });

  describe('.unregister([name], fn)', function() {
    it('should remove a delegate', function() {
      bus.register('foo', function() {});
      bus.unregister('foo');

      expect(function() {
        bus.call('foo');
      }).toThrow(new Error('no delegate for method "foo"'));
    });

    it('should remove a delegate for all methods', function() {
      bus.register(function() {});
      bus.unregister();

      expect(function() {
        bus.call('foo');
      }).toThrow(new Error('no delegate for method "foo"'));
    });
  });

  describe('.call(name, *args)', function() {
    it('should fire the last delegate', function() {
      var one = jasmine.createSpy('one').andReturn('one');
      var two = jasmine.createSpy('two').andReturn('two');
      var three = jasmine.createSpy('three').andReturn('three');
      var four = jasmine.createSpy('four').andReturn('four');

      var results = [];

      bus.register(one);
      bus.register('foo', two);
      bus.register('foo.bar', three);
      bus.register('foo.baz', four);
      var results = [bus.call('foo', 1), bus.call('foo.bar.baz', 2)];

      expect(results).toEqual(['two', 'three']);
      expect(one).not.toHaveBeenCalled();
      expect(two).toHaveBeenCalledWith(1);
      expect(three).toHaveBeenCalledWith(2);
      expect(four).not.toHaveBeenCalled();
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
