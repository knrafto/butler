var io = require('socket.io');
var Q = require('q');
var _ = require('underscore');

var butler = require('../butler');


exports.depends = ['server'];

exports.start = function() {
  var server = io(butler.call('server'), { serveClient: false });

  server.on('connection', function(socket) {
    socket.on('request', function(request) {
      handle(request).done(function(response) {
        socket.emit('response', response);
      });
    });
  });

  butler.on(function() {
    // TODO: ensure objects are serializable first
    server.emit('event', {
      name: this.event,
      params: _.toArray(arguments)
    });
  });
};

function handle(request) {
  return Q['try'](function() {
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
