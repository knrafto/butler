var proxyquire = require('proxyquire');
var _ = require('underscore');

var butler = require('../butler');

describe('mopidy', function() {
  var mopidy, service;

  beforeEach(function() {
    mopidy = {
      emit: function() {
        var args = arguments;
        _.each(this._callbacks, function(fn) {
          fn.apply(null, args);
        });
      },

      on: function(fn) {
        this._callbacks || (this._callbacks = []);
        this._callbacks.push(fn);
      }
    }

    function Mopidy(config) {
      mopidy.config = config;
      return mopidy;
    }

    service = proxyquire('../services/mopidy', {
      mopidy: Mopidy
    });
  });

  afterEach(function() {
    butler.reset();
  });

  it('should connect to a websocket URL', function() {
    service.start({ url: 'ws://example.com' });
    expect(mopidy.config).toEqual({
      webSocketUrl: 'ws://example.com',
      callingConvention: 'by-position-or-by-name'
    });
  });

  it('should emit events', function() {
    var one = jasmine.createSpy('one');
    service.start();
    butler.on(one);
    mopidy.emit('websocket:connect');
    mopidy.emit('event:playbackStarted', 1, 2);
    expect(one.calls.all()).toEqual([
      {
        object: { event: 'mopidy.playbackStarted' },
        args: [1, 2]
      }
    ]);
  });

  it('should call methods', function() {
    var one = jasmine.createSpy('one').and.returnValue('one');
    service.start();
    mopidy.foo = {
      bar: one
    };
    var result = butler.call('mopidy.foo.bar', { baz: 'baz' });
    expect(one).toHaveBeenCalledWith({ baz: 'baz' });
    expect(result).toEqual('one');
  });
});
