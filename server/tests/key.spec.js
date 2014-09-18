var butler = require('../butler');
var service = require('../services/key');

describe('key', function() {
  afterEach(function() {
    butler.reset();
  });

  it('should return keys', function() {
    service.start({
      'foo': 'bar',
      'key.key': 42,
    });
    expect(butler.call('key.foo')).toBe('bar');
    expect(butler.call('key.key.key')).toBe(42);
    expect(butler.call('key.bar')).toBeUndefined();
  });
});
