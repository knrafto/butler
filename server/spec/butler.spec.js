var Butler = require('../butler').Butler;

describe('Butler', function() {
  it('should inherit from EventEmitter', function() {
    var EventEmitter = require('events').EventEmitter;
    expect(butler instanceof EventEmitter).toBe(true);
  });

  describe('.hire(servant)', function() {
    it('should invoke the servant with new', function() {

    });

    it('should pass the butler and config as arguments', function() {
      var container = {
        Servant: null;
      };
      spyOn(container, 'Servant');
      butler.hire(container.Servant);
      expect(container.Servant).toHaveBeenCalledWith(butler, config);
    });
  });

  describe('.call(method, [args...])', function() {

  });
});
