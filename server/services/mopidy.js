var Q = require('q');
var _ = require('underscore');

var butler = require('../butler');
var Client = require('../../common/client');

module.exports = function(config) {
  config = config || {};
  var client = new Client();

  var reconnectTimeout;

  function reconnect() {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = setTimeout(function() {
      client.open(config.url);
    }, 8000);
  }

  client.open(config.url);

  butler.register('mopidy', function() {
    var method = 'core.' + this.suffix;
    var args = _.toArray(arguments);
    var deferred = Q.defer();
    client.request(method, args, function(err, result) {
      err ? deferred.reject(err) : deferred.resolve(result);
    });
    return deferred.promise;
  });

  client.on('open', function() {
    clearTimeout(reconnectTimeout);
    butler.emit('mopidy.connect');
  });

  client.on('close', function(code, message) {
    butler.emit('mopidy.disconnect', code, message);
    reconnect();
  });

  client.on('error', function(errno) {
    butler.emit('log.error', 'mopidy', errno);
    reconnect();
  });

  client.on('event', function(event, data) {
    butler.emit('mopidy.' + event, data);
  });
};
