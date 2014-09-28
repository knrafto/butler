angular.module('butler', ['ui.router', 'templates'])

// TODO
.constant('SERVER_URL', 'ws://localhost:26532')

.factory('butler', function($window, $rootScope, $timeout, $q, SERVER_URL) {
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
    try {
      var deferred = $q.defer();
      client.request(method, args, function(err, result) {
        $rootScope.$apply(function() {
          err ? deferred.reject(err) : deferred.resolve(result);
        });
      });
      return deferred.promise;
    } catch (err) {
      return $q.reject(err);
    }
  });

  butler.on('', function() {
    console.log(Date.now(), this.name, _.toArray(arguments));
  });

  return butler;
})

.factory('debounce', function($rootScope) {
  return function debounce(fn, wait, immediate) {
    return _.debounce(function() {
      $rootScope.$apply(fn)
    }, wait, immediate);
  };
});
