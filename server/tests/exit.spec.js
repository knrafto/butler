var process = require('process');

var butler = require('../butler');
var start = require('../services/exit');

describe('exit', function() {
  var one;

  beforeEach(function() {
    one = jasmine.createSpy('one');
    spyOn(process, 'exit').and.callFake(function(code) {
      process.emit('exit', code);
    });
    start();
    butler.on('exit', one);
  });

  afterEach(function() {
    butler.reset();
  });

  it('should fire on exit', function() {
    process.exit(1);
    expect(one).toHaveBeenCalledWith(1);
  });

  it('should fire on SIGINT', function() {
    process.emit('SIGINT');
    expect(one).toHaveBeenCalledWith(0);
    expect(process.exit).toHaveBeenCalledWith(0);
  });

  it('should fire on SIGTERM', function() {
    process.emit('SIGTERM');
    expect(one).toHaveBeenCalledWith(0);
    expect(process.exit).toHaveBeenCalledWith(0);
  });
});
