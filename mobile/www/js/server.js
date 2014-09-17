angular.module('server', ['butler', 'underscore'])

.constant('SERVER_URL', 'http://127.0.0.1:26532')

.factory('socket', function($window, SERVER_URL) {
  return $window.io(SERVER_URL);
})

.run(function($rootScope, $q, socket, butler, _) {
  var nextId = 0;
  var pendingRequests = {};

  butler.register(function() {
    var requestId = nextId++;
    var deferred = $q.defer();
    socket.emit('request', {
      id: requestId,
      method: this.method,
      params: _.toArray(arguments)
    });
    pendingRequests[requestId] = deferred;
    return deferred.promise;
  });

  socket.on('response', function(response) {
    var deferred = pendingRequests[response.id];
    if (deferred) {
      if (response.result) {
        deferred.resolve(response.result);
      } else {
        deferred.reject(response.error || 'unknown error');
      }
      delete pendingRequests[response.id];
    }
    $rootScope.$apply();
  });

  socket.on('event', function(event) {
    butler.emit.apply(butler, [event.event].concat(event.params));
    $rootScope.$apply();
  });

  return butler;
});
