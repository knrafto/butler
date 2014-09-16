var Q = require('q');
var _ = require('underscore');

var butler = require('../butler');

function serve(port, hostname) {
  var http = require('http').createServer();
  var server = require('socket.io')(http, { serveClient: false });
  http.listen(port, hostname);

  server.on('connect', function(socket) {
    socket.on('request', function(request) {
      handle(request).done(function(response) {
        socket.emit('response', response);
      });
    });
  });

  butler.on(function() {
    server.emit('event', {
      name: this.event,
      params: _.toArray(arguments)
    });
  });
}

function handle(request) {
  return Q['try'](function() {
    return butler.call.apply(butler, [request.method].concat(request.params));
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

module.exports = {
  name: 'server',

  start: function(config) {
    config = config || {};
    serve(config.port, config.hostname);
  }
};
