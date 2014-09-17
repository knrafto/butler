var butler = require('../butler')
var service = require('../services/server');

describe('server', function() {
  afterEach(function() {
    butler.reset();
  });

  it('should start and close an HTTP server', function(done) {
    var config = {
      hostname: 'localhost',
      port: 54010
    };
    service.start(config);
    var server = butler.call('server');
    server.on('listening', function() {
      expect(server.address()).toEqual({
        port: 54010,
        family: 'IPv4',
        address: '127.0.0.1'
      });
      butler.emit('exit', 0);
      server.on('close', done);
    });
  });
});
