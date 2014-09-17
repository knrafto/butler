var http = require('http');
var _ = require('underscore');

var butler = require('../butler');

function serve(port, hostname) {
  var server = new http.Server;
  server.listen(port, hostname, function() {
    butler.on('exit', function() {
      server.close();
    });
  });

  butler.register('server', function() {
    return server;
  });

  server.on('error', function() {
    butler.emit('error', 'server', err);
  });
}

module.exports = {
  start: function(config) {
    config = config || {};
    serve(config.port, config.hostname);
  }
};
