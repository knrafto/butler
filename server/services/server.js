var Q = require('q');
var Server = require('ws').Server
var _ = require('underscore');

var butler = require('../butler');

/**
 * Asynchronously handle a JSON-RPC request string using the butler.
 * @param {string} request The request string.
 * @return {Promise.<string>} A promised response string.
 */
function handle(request) {
  return Q.try(function() {
    request = JSON.parse(request);
    return butler.apply(request.method, request.params);
  })
  .then(function(result) {
    return {
      result: result,
      error: null,
      id: request.id
    };
  }, function(err) {
    return {
      result: null,
      error: {
        code: 0,
        message: err.message
      },
      id: request.id
    };
  })
  .then(JSON.stringify);
}

/**
 * @module server A service that responds to JSON-RPC requests and emits
 * events over a WebSocket.
 */
module.exports = function(config) {
  config = config || {};
  var connections = [];

  var server = new Server({
    host: config.hostname,
    port: config.port
  });

  server.on('error', function(err) {
    butler.emit('log.error', 'server', err);
  });

  server.on('connection', function(socket) {
    connections.push(socket);

    socket.on('close', function() {
      var i = connections.indexOf(socket);
      if (i > -1) connections.splice(i, 1);
    });

    socket.on('message', function(request) {
      butler.emit('log.debug', 'server', 'request', request);
      handle(request).done(function(response) {
        butler.emit('log.debug', 'server', 'response', response);
        socket.send(response);
      });
    });
  });

  butler.on('', function() {
    // don't send log events
    if (this.name.match(/^log\./)) return;
    var event = JSON.stringify({
      event: this.name,
      params: _.toArray(arguments)
    });
    butler.emit('log.debug', 'server', 'event', event);
    _.each(connections, function(socket) {
      socket.send(event);
    });
  });
};
