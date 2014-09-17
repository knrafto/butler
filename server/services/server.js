var http = require('http');
var _ = require('underscore');

var butler = require('../butler');

exports.start = function(config) {
  config = config || {};
  var server = new http.Server;
  server.listen(config.port, config.hostname, function() {
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
};