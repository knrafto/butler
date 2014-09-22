var http = require('http');
var io = require('socket.io');
var Q = require('q');
var _ = require('underscore');

var butler = require('../butler');

function handle(request) {
  return Q.try(function() {
    var args = [request.method].concat(request.params)
    return butler.call.apply(butler, args);
  }).then(function(result) {
    return {
      result: result,
      error: null,
      id: request.id
    };
  }, function(err) {
    return {
      result: null,
      error: err,
      id: request.id
    };
  });
}

module.exports = function(config) {
  config = config || {};
  var httpServer = new http.Server();
  httpServer.listen(config.port, config.hostname);

  httpServer.on('error', function(err) {
    butler.emit('log.error', 'server', err);
  });

  var server = io(httpServer, { serveClient: false });

  server.on('connection', function(socket) {
    socket.on('request', function(request) {
      butler.emit('log.debug', 'server', 'request', request);
      handle(request).done(function(response) {
        butler.emit('log.debug', 'server', 'response', response);
        socket.emit('response', response);
      });
    });
  });

  butler.on(function() {
    // don't send log events
    if (this.event.match(/^log\./)) return;
    var event = {
      event: this.event,
      params: _.toArray(arguments)
    };
    butler.emit('log.debug', 'server', 'event', event);
    server.emit('event', event);
  });
};
