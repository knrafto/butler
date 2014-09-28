angular.module('butler', ['underscore'])

// TODO
.constant('SERVER_URL', 'ws://localhost:26532')

.factory('butler', function($window, $rootScope, $timeout, $q, SERVER_URL, _) {
  var butler = new $window.common.Butler();
  var client = new $window.common.Client();

  var reconnectTimeout;

  function reconnect() {
    $timeout.cancel(reconnectTimeout);
    reconnectTimeout = $timeout(function() {
      client.open(SERVER_URL);
    }, 8000);
  }

  client.open(SERVER_URL);

  client.on('open', function() {
    $timeout.cancel(reconnectTimeout);
    butler.emit('open');
  });

  client.on('close', function(code, reason) {
    butler.emit('close', code, reason);
    reconnect();
  });

  client.on('error', function(errno) {
    butler.emit('error', errno);
    reconnect();
  });

  client.on('event', function(name, event) {
    $rootScope.$apply(function() {
      butler.broadcast(name, event.params);
    });
  });

  butler.register('', function() {
    var method = this.name;
    var args = _.toArray(arguments);
    var deferred = $q.defer();
    client.request(method, args, function(err, result) {
      err ? deferred.reject(err) : deferred.resolve(result);
    });
    return deferred.promise;
  });

  butler.on('', function() {
    console.log(this.name, _.toArray(arguments));
  });

  return butler;
});
