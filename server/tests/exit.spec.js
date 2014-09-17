var process = require('process');

var butler = require('../butler');
var service = require('../services/exit');

describe('exit', function() {
  var one;

  beforeEach(function() {
    one = jasmine.createSpy('one');
    spyOn(process, 'exit').and.callFake(function(code) {
      process.emit('exit', code);
    });
    service.start();
    butler.on('exit', one);
  });

  afterEach(function() {
    butler.reset();
  });

  it('should fire on exit', function() {
    process.emit('exit', 1);
    expect(one).toHaveBeenCalledWith(1);
  });

  it('should fire on uncaught expection', function() {
    process.emit('uncaughtException', new Error());
    expect(one).toHaveBeenCalledWith(1);
    expect(process.exit).toHaveBeenCalledWith(1);
  });

  it('should fire on SIGINT', function() {
    process.emit('SIGINT');
    expect(one).toHaveBeenCalledWith(0);
    expect(process.exit).toHaveBeenCalledWith(0);
  });
});
