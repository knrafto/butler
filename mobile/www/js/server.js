angular.module('server', ['butler', 'underscore'])

.constant('SERVER_URL', 'http://127.0.0.1:26532')

.factory('socket', function($window, SERVER_URL) {
  var io = $window.io || angular.noop;
  return io(SERVER_URL);
})

.run(function($rootScope, $q, socket, butler, _) {
  if (!socket) return;

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
    $rootScope.$apply(function() {
      var deferred = pendingRequests[response.id];
      if (deferred) {
        if (response.result) {
          deferred.resolve(response.result);
        } else {
          deferred.reject(response.error || 'unknown error');
        }
        delete pendingRequests[response.id];
      }
    });
  });

  socket.on('event', function(event) {
    $rootScope.$apply(function() {
      butler.emit.apply(butler, [event.event].concat(event.params));
    });
  });
});
